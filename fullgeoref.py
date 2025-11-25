import os
# Unset PROJ_LIB to avoid conflicts with other installations (like PostgreSQL/PostGIS)
# This must be done before importing rasterio or pyproj
if 'PROJ_LIB' in os.environ:
    del os.environ['PROJ_LIB']

import glob
import exifread
from pyproj import Transformer
import math
from PIL import Image
import rawpy
import numpy as np
import subprocess
import csv
import rasterio
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps

# -------------------------------
# CONSTANTS & CONFIGURATION
# -------------------------------
# Parámetros de la cámara DJI Mini 3 Pro
SENSOR_WIDTH_MM = 9.6
SENSOR_HEIGHT_MM = 7.2
FOCAL_LENGTH_MM = 6.7
IMAGE_WIDTH_PX = 8064
IMAGE_HEIGHT_PX = 6048
FOV_H = 82.1  # grados
FOV_V = 66.9  # grados

# Configuración de proyección (WGS84 -> CRTM05)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:8908", always_xy=True)

# -------------------------------
# PART 1: DNG PROCESSING & METADATA
# -------------------------------

def convert_dng_to_jpg(dng_path):
    """Convierte un archivo DNG a JPG manteniendo máxima calidad y copia los metadatos GPS."""
    jpg_path = os.path.splitext(dng_path)[0] + ".jpg"
    if os.path.exists(jpg_path):
        print(f"Ya existe {jpg_path}, se omite conversión.")
        return jpg_path

    try:
        # 1. Convertir DNG a JPG con rawpy (máxima calidad)
        with rawpy.imread(dng_path) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=True,
                output_bps=16,
                gamma=(1, 1),
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD
            )

        rgb_8bit = np.clip(rgb / 256, 0, 255).astype('uint8')
        img = Image.fromarray(rgb_8bit)
        img.save(jpg_path, "JPEG", quality=100, subsampling=0)
        print(f"Convertido (alta calidad): {dng_path} -> {jpg_path}")

        # 2. Copiar metadatos GPS con exiftool
        copy_gps_metadata_exiftool(dng_path, jpg_path)

        return jpg_path
    except Exception as e:
        print(f"Error al convertir {dng_path}: {e}")
        return None


def convert_all_dng_to_jpg():
    """Convierte todos los archivos DNG del directorio a JPG."""
    dng_files = glob.glob("*.dng")
    if not dng_files:
        print("No se encontraron archivos DNG.")
        return
    for dng in dng_files:
        convert_dng_to_jpg(dng)


def copy_gps_metadata_exiftool(dng_path, jpg_path):
    """Copia todos los metadatos EXIF (incluyendo GPS) del DNG al JPG usando exiftool."""
    try:
        subprocess.run(
            ["exiftool", "-overwrite_original", "-TagsFromFile", dng_path, "-gps:all", "-exif:all", jpg_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"Metadatos GPS copiados correctamente de {dng_path} a {jpg_path}")
    except FileNotFoundError:
        print("Error: exiftool no está instalado o no se encuentra en el PATH.")
        print("Instalalo desde https://exiftool.org/ o con 'choco install exiftool' en Windows.")
    except subprocess.CalledProcessError as e:
        print(f"Error al copiar metadatos con exiftool: {e.stderr.decode()}")


def get_exif_data(image_path):
    """Lee coordenadas GPS y altitud desde los metadatos EXIF."""
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f, details=False)

    def _get_if_exist(data, key):
        return data[key] if key in data else None

    lat_tag = _get_if_exist(tags, 'GPS GPSLatitude')
    lon_tag = _get_if_exist(tags, 'GPS GPSLongitude')
    alt_tag = _get_if_exist(tags, 'GPS GPSAltitude')
    lat_ref = _get_if_exist(tags, 'GPS GPSLatitudeRef')
    lon_ref = _get_if_exist(tags, 'GPS GPSLongitudeRef')

    if not lat_tag or not lon_tag:
        raise ValueError(f"No se encontraron coordenadas GPS en {image_path}")

    def _convert_to_degrees(value):
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        return d + (m / 60.0) + (s / 3600.0)

    lat = _convert_to_degrees(lat_tag)
    lon = _convert_to_degrees(lon_tag)

    if lat_ref and lat_ref.values[0] in ['S', 's']:
        lat = -lat
    if lon_ref and lon_ref.values[0] in ['W', 'w']:
        lon = -lon

    alt = float(alt_tag.values[0].num) / float(alt_tag.values[0].den) if alt_tag else 0.0

    return lat, lon, alt


def calculate_ground_dimensions(alt_relative):
    """Calcula el ancho y alto del terreno cubierto por la foto según la altura relativa."""
    if alt_relative <= 0:
        alt_relative = 1  # Evita valores negativos o cero
    width = 2 * alt_relative * math.tan(math.radians(FOV_V / 2))
    height = width * 6048 /8064
    return width, height


def calculate_corners(x_center, y_center, width, height):
    """Calcula las coordenadas de las 4 esquinas de la foto."""
    dx = width / 2
    dy = height / 2
    corners = [
        (x_center - dx, y_center + dy, 0, 0),
        (x_center + dx, y_center + dy, IMAGE_WIDTH_PX, 0),
        (x_center - dx, y_center - dy, 0, IMAGE_HEIGHT_PX),
        (x_center + dx, y_center - dy, IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX)
    ]
    return corners


def create_points_file(image_name, corners):
    """Genera el archivo .points compatible con QGIS."""
    points_filename = os.path.splitext(image_name)[0] + ".points"
    with open(points_filename, "w") as f:
        f.write("# mapX,mapY,pixelX,pixelY,enable\n")
        for (mapX, mapY, px, py) in corners:
            f.write(f"{mapX:.3f},{mapY:.3f},{px},{py},1\n")
    print(f"Archivo generado: {points_filename}")


def create_summary_csv(data_rows):
    """Genera un archivo CSV con los datos calculados de cada imagen."""
    csv_filename = "resumen_calculos.csv"
    with open(csv_filename, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "imagen", "latitud", "longitud", "altitud_m", "altitud_relativa_m",
            "x_crtm05", "y_crtm05", "ancho_m", "alto_m"
        ])
        writer.writerows(data_rows)
    print(f"Archivo resumen generado: {csv_filename}")


# -------------------------------
# PART 2: AUTOMATED GEOREFERENCING
# -------------------------------

def parse_points_file(points_path):
    """Parses the .points file to extract GCPs."""
    gcps = []
    try:
        with open(points_path, 'r') as f:
            reader = csv.reader(f)
            for line in reader:
                # Skip comments or empty lines
                if not line or line[0].startswith('#'):
                    continue
                
                try:
                    mapX = float(line[0])
                    mapY = float(line[1])
                    pixelX = float(line[2])
                    pixelY = float(line[3])
                    enable = int(line[4])
                    
                    if enable:
                        # GCP(row, col, x, y, z=0)
                        gcps.append(GroundControlPoint(row=pixelY, col=pixelX, x=mapX, y=mapY, z=0))
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        print(f"Error parsing {points_path}: {e}")
    return gcps


def georeference_image(jpg_path, points_path):
    """Georeferences the image using GCPs and saves as GeoTIFF."""
    output_path = os.path.splitext(jpg_path)[0] + "_georef.tif"
    
    gcps = parse_points_file(points_path)
    if not gcps:
        print(f"No valid GCPs found for {jpg_path}")
        return

    try:
        # Calculate Affine transform from GCPs
        # Since the points form a rectangle, this should be accurate
        transform = from_gcps(gcps)
        
        with rasterio.open(jpg_path) as src:
            # Define the CRS (CRTM05 - EPSG:8908)
            crs = 'EPSG:8908'
            
            # Prepare metadata for GeoTIFF
            kwargs = src.meta.copy()
            kwargs.update({
                'driver': 'GTiff',
                'crs': crs,
                'transform': transform,
                'count': 3, # Ensure 3 bands
                'compress': 'lzw'
            })
            
            # Write the file with the new transform and CRS
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                dst.write(src.read())
        
        print(f"Georeferenced: {output_path}")

    except Exception as e:
        print(f"Error georeferencing {jpg_path}: {e}")


# -------------------------------
# PART 3: VEGETATION INDICES
# -------------------------------

def calculate_indices(tif_path):
    """Calculates GLI and VARI indices and saves them as new GeoTIFFs."""
    try:
        with rasterio.open(tif_path) as src:
            # Read bands (assuming RGB order: 1=Red, 2=Green, 3=Blue)
            # We use float32 for calculations
            red = src.read(1).astype('float32')
            green = src.read(2).astype('float32')
            blue = src.read(3).astype('float32')
            
            # --- GLI Calculation ---
            # Formula: ((GREEN - RED) + (GREEN - BLUE)) / ((2 * GREEN) + RED + BLUE)
            gli_denom = (2 * green) + red + blue
            # Handle division by zero
            gli_denom[gli_denom == 0] = np.nan 
            
            gli_num = (green - red) + (green - blue)
            gli = gli_num / gli_denom
            
            # --- VARI Calculation ---
            # Formula: (GREEN - RED) / (GREEN + RED - BLUE)
            vari_denom = green + red - blue
            # Handle division by zero
            vari_denom[vari_denom == 0] = np.nan
            
            vari_num = green - red
            vari = vari_num / vari_denom
            
            # Prepare profile for single-band output
            profile = src.profile.copy()
            profile.update(dtype=rasterio.float32, count=1, compress='lzw')
            
            # Save GLI
            # Naming convention: DJI_0001_GLI.tif (removing _georef if present to keep it clean, or appending)
            # Let's append to keep lineage clear: DJI_0001_georef_GLI.tif
            base_name = os.path.splitext(tif_path)[0]
            gli_path = f"{base_name}_GLI.tif"
            
            with rasterio.open(gli_path, 'w', **profile) as dst:
                dst.write(gli, 1)
            print(f"Generated GLI: {gli_path}")
            
            # Save VARI
            vari_path = f"{base_name}_VARI.tif"
            with rasterio.open(vari_path, 'w', **profile) as dst:
                dst.write(vari, 1)
            print(f"Generated VARI: {vari_path}")
            
    except Exception as e:
        print(f"Error calculating indices for {tif_path}: {e}")


# -------------------------------
# MAIN EXECUTION
# -------------------------------

def main():
    print("=== INICIANDO PROCESO DE GEORREFERENCIACIÓN ===")
    
    # 1. Convertir DNG a JPG (máxima calidad)
    print("\n--- Paso 1: Conversión DNG a JPG ---")
    convert_all_dng_to_jpg()

    # 2. Procesar imágenes JPG para generar puntos y CSV
    print("\n--- Paso 2: Generación de Puntos de Control ---")
    images = sorted(glob.glob("*.jpg"))
    if not images:
        print("No se encontraron imágenes JPG en el directorio.")
        return

    # Buscar imagen de referencia (terminada en 001)
    ref_image = next((img for img in images if "001" in img), None)
    if not ref_image:
        print("No se encontró imagen de referencia (terminada en 001).")
        return

    ref_lat, ref_lon, ref_alt = get_exif_data(ref_image)
    print(f"Referencia: {ref_image} -> Altura base {ref_alt:.2f} m")

    summary_data = []

    # Procesar todas las imágenes
    for img in images:
        try:
            lat, lon, alt = get_exif_data(img)
            x, y = transformer.transform(lon, lat)
            alt_rel = alt - ref_alt  # Altura relativa
            width, height = calculate_ground_dimensions(alt_rel)
            corners = calculate_corners(x, y, width, height)
            create_points_file(img, corners)

            # Agregar datos al resumen
            summary_data.append([
                img, lat, lon, round(alt, 3), round(alt_rel, 3),
                round(x, 3), round(y, 3), round(width, 3), round(height, 3)
            ])
        except Exception as e:
            print(f"Error procesando {img}: {e}")

    # Crear archivo CSV resumen
    if summary_data:
        create_summary_csv(summary_data)

    # 3. Georreferenciación Automática (Rasterio)
    print("\n--- Paso 3: Generación de GeoTIFFs e Índices ---")
    for img in images:
        points_path = os.path.splitext(img)[0] + ".points"
        if os.path.exists(points_path):
            print(f"Procesando {img}...")
            # Georeference
            georeference_image(img, points_path)
            
            # Calculate Indices
            # Assuming georeference_image creates a file with _georef.tif suffix
            georef_path = os.path.splitext(img)[0] + "_georef.tif"
            if os.path.exists(georef_path):
                calculate_indices(georef_path)
        else:
            print(f"Saltando {img} (sin archivo .points)")

    print("\n=== PROCESO COMPLETADO ===")

if __name__ == "__main__":
    main()
