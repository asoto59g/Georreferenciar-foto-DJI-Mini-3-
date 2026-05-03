import os
import sys
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
# FOV calculado desde sensor y focal (82.1° es el FOV DIAGONAL según DJI, no horizontal)
FOV_H = 2 * math.degrees(math.atan(SENSOR_WIDTH_MM / (2 * FOCAL_LENGTH_MM)))   # ~71.2°
FOV_V = 2 * math.degrees(math.atan(SENSOR_HEIGHT_MM / (2 * FOCAL_LENGTH_MM)))   # ~56.5°

# Corrección de offset GPS (en metros, sistema CRTM05)
# Medir en QGIS desde un punto reconocible en la foto del drone
# hasta el mismo punto en el basemap. Ingresar los deltas aquí.
OFFSET_X_M = -7.6   # Corrección Este  (positivo = mover foto al Este)
OFFSET_Y_M = -27.8   # Corrección Norte (positivo = mover foto al Norte)

# Configuración de proyección (WGS84 -> CRTM05)
# EPSG:8908 = CR-SIRGAS / CRTM05 (basado en ITRF2008@2014.59)
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
        # Determine path to exiftool
        if getattr(sys, 'frozen', False):
            # If running as a bundled executable
            base_path = sys._MEIPASS
            exiftool_path = os.path.join(base_path, "exiftool.exe")
            cwd = base_path
        else:
            # If running as a script
            exiftool_path = "exiftool"
            cwd = None

        # Use absolute paths for files because we might change cwd
        abs_dng_path = os.path.abspath(dng_path)
        abs_jpg_path = os.path.abspath(jpg_path)

        subprocess.run(
            [exiftool_path, "-overwrite_original", "-TagsFromFile", abs_dng_path, "-gps:all", "-exif:all", "-xmp:all", abs_jpg_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd # Set CWD so exiftool finds its files
        )
        print(f"Metadatos GPS copiados correctamente de {dng_path} a {jpg_path}")
    except FileNotFoundError:
        print("Error: exiftool no está instalado o no se encuentra en el PATH.")
        print("Instalalo desde https://exiftool.org/ o con 'choco install exiftool' en Windows.")
    except subprocess.CalledProcessError as e:
        print(f"Error al copiar metadatos con exiftool: {e.stderr.decode()}")


def get_exif_data(image_path):
    """Lee coordenadas GPS, altitud y ángulos de actitud desde los metadatos EXIF.
    
    Returns:
        tuple: (lat, lon, alt, pitch, roll, yaw) donde los ángulos están en grados
    """
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f, details=True)

    def _get_if_exist(data, key):
        return data[key] if key in data else None

    # Coordenadas GPS
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

    # Ángulos de actitud del vuelo (Flight Attitude)
    # Estos están en los metadatos MakerNote de DJI
    pitch_tag = _get_if_exist(tags, 'MakerNote Pitch')
    roll_tag = _get_if_exist(tags, 'MakerNote Roll')
    yaw_tag = _get_if_exist(tags, 'MakerNote Yaw')

    def _extract_angle(tag):
        """Extrae el valor del ángulo del tag EXIF."""
        if not tag:
            return 0.0
        try:
            # Intentar convertir directamente
            if hasattr(tag, 'values'):
                if len(tag.values) > 0:
                    val = tag.values[0]
                    # MakerNote values come as tuples, e.g., (-2.099,)
                    if isinstance(val, tuple) and len(val) > 0:
                        return float(val[0])
                    elif hasattr(val, 'num') and hasattr(val, 'den'):
                        return float(val.num) / float(val.den)
                    else:
                        return float(val)
            # Si es un string, convertir
            return float(str(tag))
        except:
            return 0.0

    pitch = _extract_angle(pitch_tag)
    roll = _extract_angle(roll_tag)
    yaw = _extract_angle(yaw_tag)

    return lat, lon, alt, pitch, roll, yaw


def calculate_ground_dimensions(alt_relative):
    """Calcula el ancho y alto del terreno cubierto por la foto según la altura relativa.
    
    Esta función asume vista nadir (cámara apuntando directamente hacia abajo).
    Para fotos con inclinación, se debe aplicar corrección de actitud después.
    """
    if alt_relative <= 0:
        alt_relative = 1  # Evita valores negativos o cero
    width = 2 * alt_relative * math.tan(math.radians(FOV_H / 2))
    height = 2 * alt_relative * math.tan(math.radians(FOV_V / 2))
    return width, height


def create_rotation_matrix(pitch, roll, yaw):
    """Crea una matriz de rotación 3D combinada a partir de los ángulos de Euler.
    
    Args:
        pitch: Ángulo de cabeceo en grados (rotación alrededor del eje Y)
        roll: Ángulo de alabeo en grados (rotación alrededor del eje X)
        yaw: Ángulo de guiñada en grados (rotación alrededor del eje Z)
    
    Returns:
        numpy.ndarray: Matriz de rotación 3x3
    
    Nota: El orden de rotación es Yaw -> Pitch -> Roll (ZYX)
    """
    # Convertir grados a radianes
    pitch_rad = math.radians(pitch)
    roll_rad = math.radians(roll)
    yaw_rad = math.radians(yaw)
    
    # Matriz de rotación alrededor del eje Z (Yaw)
    Rz = np.array([
        [math.cos(yaw_rad), -math.sin(yaw_rad), 0],
        [math.sin(yaw_rad),  math.cos(yaw_rad), 0],
        [0,                  0,                 1]
    ])
    
    # Matriz de rotación alrededor del eje Y (Pitch)
    Ry = np.array([
        [math.cos(pitch_rad),  0, math.sin(pitch_rad)],
        [0,                    1, 0],
        [-math.sin(pitch_rad), 0, math.cos(pitch_rad)]
    ])
    
    # Matriz de rotación alrededor del eje X (Roll)
    Rx = np.array([
        [1, 0,                   0],
        [0, math.cos(roll_rad), -math.sin(roll_rad)],
        [0, math.sin(roll_rad),  math.cos(roll_rad)]
    ])
    
    # Rotación combinada: R = Rz * Ry * Rx
    R = Rz @ Ry @ Rx
    
    return R


def apply_attitude_correction(x_center, y_center, width, height, altitude, pitch, roll, yaw):
    """Aplica corrección de actitud a las coordenadas de las esquinas de la foto.
    
    Args:
        x_center, y_center: Coordenadas del centro de la foto (CRTM05)
        width, height: Dimensiones del footprint en metros (asumiendo nadir)
        altitude: Altura relativa del drone en metros
        pitch, roll, yaw: Ángulos de actitud en grados
    
    Returns:
        list: Lista de tuplas (x, y, px, py) con las coordenadas corregidas
    """
    # Si no hay inclinación significativa, usar cálculo simple
    if abs(pitch) < 0.5 and abs(roll) < 0.5:
        return calculate_corners_simple(x_center, y_center, width, height)
    
    # Crear matriz de rotación
    R = create_rotation_matrix(pitch, roll, yaw)
    
    # Definir las esquinas en el sistema de coordenadas de la cámara
    # Asumimos que la cámara está en el origen mirando hacia abajo (-Z)
    # Las esquinas están en el plano Z = -altitude
    dx = width / 2
    dy = height / 2
    
    # Esquinas en coordenadas locales (relativas al centro de la foto)
    # Orden: TL, TR, BL, BR (Top-Left, Top-Right, Bottom-Left, Bottom-Right)
    corners_local = np.array([
        [-dx,  dy, -altitude],  # Top-Left
        [ dx,  dy, -altitude],  # Top-Right
        [-dx, -dy, -altitude],  # Bottom-Left
        [ dx, -dy, -altitude]   # Bottom-Right
    ])
    
    # Aplicar rotación a cada esquina
    corners_rotated = np.array([R @ corner for corner in corners_local])
    
    # Proyectar de vuelta al plano del suelo (Z = 0)
    # Usando proyección perspectiva simple
    corners_ground = []
    for corner in corners_rotated:
        if corner[2] >= 0:  # Evitar división por cero o valores inválidos
            # Si el punto está por encima del drone, usar proyección simple
            scale = 1.0
        else:
            # Escalar según la altura
            scale = -altitude / corner[2]
        
        x_ground = x_center + corner[0] * scale
        y_ground = y_center + corner[1] * scale
        corners_ground.append((x_ground, y_ground))
    
    # Mapear a coordenadas de píxeles
    # Orden: TL, TR, BL, BR
    pixel_coords = [
        (0, 0),                           # Top-Left
        (IMAGE_WIDTH_PX, 0),              # Top-Right
        (0, IMAGE_HEIGHT_PX),             # Bottom-Left
        (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX) # Bottom-Right
    ]
    
    result = []
    for (x, y), (px, py) in zip(corners_ground, pixel_coords):
        result.append((x, y, px, py))
    
    return result


def calculate_corners_simple(x_center, y_center, width, height):
    """Calcula las coordenadas de las 4 esquinas de la foto (sin corrección de actitud)."""
    dx = width / 2
    dy = height / 2
    corners = [
        (x_center - dx, y_center + dy, 0, 0),                           # Top-Left
        (x_center + dx, y_center + dy, IMAGE_WIDTH_PX, 0),              # Top-Right
        (x_center - dx, y_center - dy, 0, IMAGE_HEIGHT_PX),             # Bottom-Left
        (x_center + dx, y_center - dy, IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX) # Bottom-Right
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
            "x_crtm05", "y_crtm05", "ancho_m", "alto_m",
            "pitch_deg", "roll_deg", "yaw_deg"
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
    print("=== INICIANDO PROCESO DE GEORREFERENCIACIÓN MEJORADO ===")
    print("Versión con corrección de actitud (pitch, roll, yaw)")
    print()
    
    # 1. Convertir DNG a JPG (máxima calidad)
    print("\n--- Paso 1: Conversión DNG a JPG ---")
    convert_all_dng_to_jpg()

    # 2. Procesar imágenes JPG para generar puntos y CSV
    print("\n--- Paso 2: Generación de Puntos de Control con Corrección de Actitud ---")
    images = sorted(glob.glob("*.jpg"))
    if not images:
        print("No se encontraron imágenes JPG en el directorio.")
        return

    # Buscar imagen de referencia (terminada en 001)
    ref_image = next((img for img in images if "001" in img), None)
    if not ref_image:
        print("No se encontró imagen de referencia (terminada en 001).")
        return

    ref_lat, ref_lon, ref_alt, ref_pitch, ref_roll, ref_yaw = get_exif_data(ref_image)
    print(f"Referencia: {ref_image}")
    print(f"  Altura base: {ref_alt:.2f} m")
    print(f"  Actitud: Pitch={ref_pitch:.2f}°, Roll={ref_roll:.2f}°, Yaw={ref_yaw:.2f}°")

    summary_data = []

    # Procesar todas las imágenes
    for img in images:
        try:
            lat, lon, alt, pitch, roll, yaw = get_exif_data(img)
            x, y = transformer.transform(lon, lat)
            # Aplicar corrección de offset GPS
            x += OFFSET_X_M
            y += OFFSET_Y_M
            alt_rel = alt - ref_alt  # Altura relativa
            
            # Calcular dimensiones base (asumiendo nadir)
            width, height = calculate_ground_dimensions(alt_rel)
            
            # Aplicar corrección de actitud para obtener esquinas corregidas
            corners = apply_attitude_correction(x, y, width, height, alt_rel, pitch, roll, yaw)
            
            # Crear archivo de puntos
            create_points_file(img, corners)

            # Agregar datos al resumen
            summary_data.append([
                img, lat, lon, round(alt, 3), round(alt_rel, 3),
                round(x, 3), round(y, 3), round(width, 3), round(height, 3),
                round(pitch, 2), round(roll, 2), round(yaw, 2)
            ])
            
            print(f"Procesado: {img} - Pitch={pitch:.2f}°, Roll={roll:.2f}°, Yaw={yaw:.2f}°")
            
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
            georef_path = os.path.splitext(img)[0] + "_georef.tif"
            if os.path.exists(georef_path):
                calculate_indices(georef_path)
        else:
            print(f"Saltando {img} (sin archivo .points)")

    print("\n=== PROCESO COMPLETADO ===")
    print("\nMejoras implementadas:")
    print("  ✓ Corrección de actitud usando pitch, roll y yaw")
    print("  ✓ Transformación mejorada EPSG:4326 -> EPSG:8908 (CR-SIRGAS/CRTM05)")
    print("  ✓ Cálculo de footprint corregido para cámaras inclinadas")

if __name__ == "__main__":
    main()
