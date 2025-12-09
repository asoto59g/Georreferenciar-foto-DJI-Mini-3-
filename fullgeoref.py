import os
import sys
# Unset PROJ_LIB to avoid conflicts with other installations
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
import urllib.request
import urllib.error
import json
import time

# -------------------------------
# CONSTANTS & CONFIGURATION
# -------------------------------
SENSOR_WIDTH_MM = 9.6
SENSOR_HEIGHT_MM = 7.2
FOCAL_LENGTH_MM = 6.7
IMAGE_WIDTH_PX = 8064
IMAGE_HEIGHT_PX = 6048
FOV_H = 82.1
FOV_V = 66.9

transformer = Transformer.from_crs("EPSG:4326", "EPSG:8908", always_xy=True)

CSV_FILENAME = "resumen_calculos_auto.csv"

# -------------------------------
# PART 1: DNG PROCESSING & METADATA
# -------------------------------

def convert_dng_to_jpg(dng_path):
    """Convierte un archivo DNG a JPG manteniendo máxima calidad y copia los metadatos GPS."""
    jpg_path = os.path.splitext(dng_path)[0] + ".jpg"
    if os.path.exists(jpg_path):
        return jpg_path

    try:
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

        copy_gps_metadata_exiftool(dng_path, jpg_path)
        return jpg_path
    except Exception as e:
        print(f"Error al convertir {dng_path}: {e}")
        return None


def convert_all_dng_to_jpg():
    dng_files = glob.glob("*.dng")
    if not dng_files:
        print("No se encontraron archivos DNG.")
        return
    for dng in dng_files:
        convert_dng_to_jpg(dng)


def copy_gps_metadata_exiftool(dng_path, jpg_path):
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            exiftool_path = os.path.join(base_path, "exiftool.exe")
            cwd = base_path
        else:
            exiftool_path = "exiftool"
            cwd = None

        abs_dng_path = os.path.abspath(dng_path)
        abs_jpg_path = os.path.abspath(jpg_path)

        subprocess.run(
            [exiftool_path, "-overwrite_original", "-TagsFromFile", abs_dng_path, "-gps:all", "-exif:all", "-xmp:all", abs_jpg_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd
        )
    except FileNotFoundError:
        print("Error: exiftool no está instalado.")
    except subprocess.CalledProcessError as e:
        print(f"Error al copiar metadatos con exiftool: {e.stderr.decode()}")


def get_exif_data(image_path):
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f, details=True)

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

    pitch_tag = _get_if_exist(tags, 'MakerNote Pitch')
    roll_tag = _get_if_exist(tags, 'MakerNote Roll')
    yaw_tag = _get_if_exist(tags, 'MakerNote Yaw')

    def _extract_angle(tag):
        if not tag:
            return 0.0
        try:
            if hasattr(tag, 'values'):
                if len(tag.values) > 0:
                    val = tag.values[0]
                    if isinstance(val, tuple) and len(val) > 0:
                        return float(val[0])
                    elif hasattr(val, 'num') and hasattr(val, 'den'):
                        return float(val.num) / float(val.den)
                    else:
                        return float(val)
            return float(str(tag))
        except:
            return 0.0

    pitch = _extract_angle(pitch_tag)
    roll = _extract_angle(roll_tag)
    yaw = _extract_angle(yaw_tag)

    return lat, lon, alt, pitch, roll, yaw


# -------------------------------
# PART 2: AUTOMATED ELEVATION API
# -------------------------------

def get_elevations_from_api(locations):
    """
    Obtiene elevaciones para una lista de coordenadas usando Open-Elevation API.
    locations: lista de dicts {'latitude': float, 'longitude': float}
    Returns: lista de elevaciones (float) en el mismo orden
    """
    # La API pública tiene límites, procesamos en lotes pequeños si es necesario
    # Pero para ~100 fotos suele aguantar un solo request
    
    url = "https://api.open-elevation.com/api/v1/lookup"
    payload = {"locations": locations}
    
    print(f"Consultando Open-Elevation API para {len(locations)} puntos...")
    
    try:
        # Preparar request con urllib (estándar de Python, sin dependencias extra)
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                response_body = response.read().decode('utf-8')
                result_json = json.loads(response_body)
                results = result_json.get('results', [])
                elevations = [item['elevation'] for item in results]
                print("Datos de elevación recibidos correctamente.")
                return elevations
            else:
                print(f"Error en API: Status {response.status}")
                return None

    except Exception as e:
        print(f"Excepción al conectar con API de elevación: {e}")
        return None


def init_and_process_data(images):
    """Extrae metadatos, obtiene elevaciones automáticamente y prepara los datos."""
    data = []
    locations_for_api = []
    
    print("Extrayendo metadatos de imágenes...")
    for img in images:
        try:
            lat, lon, alt, pitch, roll, yaw = get_exif_data(img)
            x, y = transformer.transform(lon, lat)
            
            data.append({
                'imagen': img,
                'latitud': lat,
                'longitud': lon,
                'altitud_m': round(alt, 3),
                'x_crtm05': round(x, 3),
                'y_crtm05': round(y, 3),
                'pitch_deg': round(pitch, 2),
                'roll_deg': round(roll, 2),
                'yaw_deg': round(yaw, 2)
            })
            
            locations_for_api.append({"latitude": lat, "longitude": lon})
            
        except Exception as e:
            print(f"Error leyendo {img}: {e}")

    if not data:
        return []

    # Obtener elevaciones automáticamente
    elevations = get_elevations_from_api(locations_for_api)
    
    if elevations and len(elevations) == len(data):
        for i, elev in enumerate(elevations):
            data[i]['elevacion_terreno_m'] = float(elev)
    else:
        print("ADVERTENCIA: No se pudieron obtener las elevaciones automáticamente.")
        print("Se usará 0 como elevación por defecto (o el proceso fallará si se requiere precisión).")
        for row in data:
            row['elevacion_terreno_m'] = 0.0

    return data


def save_csv(data):
    if not data:
        return
    
    # Asegurar que todos los campos estén presentes
    fieldnames = [
        'imagen', 'latitud', 'longitud', 'altitud_m', 
        'elevacion_terreno_m', 'diferencia_elevacion_m', 'altitud_relativa_m',
        'x_crtm05', 'y_crtm05', 'ancho_m', 'alto_m',
        'pitch_deg', 'roll_deg', 'yaw_deg'
    ]
    
    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            # Filtrar solo las claves que están en fieldnames para evitar errores
            filtered_row = {k: row.get(k, '') for k in fieldnames}
            writer.writerow(filtered_row)
            
    print(f"CSV generado: {CSV_FILENAME}")


# -------------------------------
# PART 3: CALCULATIONS & GEOREFERENCING
# -------------------------------

def calculate_ground_dimensions(alt_relative):
    if alt_relative <= 0:
        alt_relative = 1
    width = 2 * alt_relative * math.tan(math.radians(FOV_V / 2))
    height = width * IMAGE_HEIGHT_PX / IMAGE_WIDTH_PX
    return width, height


def create_rotation_matrix(pitch, roll, yaw):
    pitch_rad = math.radians(pitch)
    roll_rad = math.radians(roll)
    yaw_rad = math.radians(-yaw) # Inverted sign as requested
    
    Rz = np.array([
        [math.cos(yaw_rad), -math.sin(yaw_rad), 0],
        [math.sin(yaw_rad),  math.cos(yaw_rad), 0],
        [0,                  0,                 1]
    ])
    
    Ry = np.array([
        [math.cos(pitch_rad),  0, math.sin(pitch_rad)],
        [0,                    1, 0],
        [-math.sin(pitch_rad), 0, math.cos(pitch_rad)]
    ])
    
    Rx = np.array([
        [1, 0,                   0],
        [0, math.cos(roll_rad), -math.sin(roll_rad)],
        [0, math.sin(roll_rad),  math.cos(roll_rad)]
    ])
    
    return Rz @ Ry @ Rx


def apply_attitude_correction(x_center, y_center, width, height, altitude, pitch, roll, yaw):
    if abs(pitch) < 0.5 and abs(roll) < 0.5:
        return calculate_corners_simple(x_center, y_center, width, height)
    
    R = create_rotation_matrix(pitch, roll, yaw)
    
    dx = width / 2
    dy = height / 2
    
    corners_local = np.array([
        [-dx,  dy, -altitude],
        [ dx,  dy, -altitude],
        [-dx, -dy, -altitude],
        [ dx, -dy, -altitude]
    ])
    
    corners_rotated = np.array([R @ corner for corner in corners_local])
    
    corners_ground = []
    for corner in corners_rotated:
        scale = 1.0
        if corner[2] < 0:
            scale = -altitude / corner[2]
        
        x_ground = x_center + corner[0] * scale
        y_ground = y_center + corner[1] * scale
        corners_ground.append((x_ground, y_ground))
    
    pixel_coords = [
        (0, 0),
        (IMAGE_WIDTH_PX, 0),
        (0, IMAGE_HEIGHT_PX),
        (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX)
    ]
    
    result = []
    for (x, y), (px, py) in zip(corners_ground, pixel_coords):
        result.append((x, y, px, py))
    
    return result


def calculate_corners_simple(x_center, y_center, width, height):
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
    points_filename = os.path.splitext(image_name)[0] + ".points"
    with open(points_filename, "w") as f:
        f.write("# mapX,mapY,pixelX,pixelY,enable\n")
        for (mapX, mapY, px, py) in corners:
            f.write(f"{mapX:.3f},{mapY:.3f},{px},{py},1\n")


def parse_points_file(points_path):
    gcps = []
    try:
        with open(points_path, 'r') as f:
            reader = csv.reader(f)
            for line in reader:
                if not line or line[0].startswith('#'):
                    continue
                try:
                    mapX, mapY, pixelX, pixelY, enable = float(line[0]), float(line[1]), float(line[2]), float(line[3]), int(line[4])
                    if enable:
                        gcps.append(GroundControlPoint(row=pixelY, col=pixelX, x=mapX, y=mapY, z=0))
                except:
                    continue
    except:
        pass
    return gcps


def georeference_image(jpg_path, points_path):
    output_path = os.path.splitext(jpg_path)[0] + "_georef.tif"
    gcps = parse_points_file(points_path)
    if not gcps:
        return

    try:
        transform = from_gcps(gcps)
        with rasterio.open(jpg_path) as src:
            kwargs = src.meta.copy()
            kwargs.update({
                'driver': 'GTiff',
                'crs': 'EPSG:8908',
                'transform': transform,
                'count': 3,
                'compress': 'lzw'
            })
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                dst.write(src.read())
        print(f"Georreferenciado: {output_path}")
        
        calculate_indices(output_path)
        
    except Exception as e:
        print(f"Error georreferenciando {jpg_path}: {e}")


def calculate_indices(tif_path):
    try:
        with rasterio.open(tif_path) as src:
            red = src.read(1).astype('float32')
            green = src.read(2).astype('float32')
            blue = src.read(3).astype('float32')
            
            gli_denom = (2 * green) + red + blue
            gli_denom[gli_denom == 0] = np.nan 
            gli = ((green - red) + (green - blue)) / gli_denom
            
            vari_denom = green + red - blue
            vari_denom[vari_denom == 0] = np.nan
            vari = (green - red) / vari_denom
            
            profile = src.profile.copy()
            profile.update(dtype=rasterio.float32, count=1, compress='lzw')
            
            base_name = os.path.splitext(tif_path)[0]
            
            with rasterio.open(f"{base_name}_GLI.tif", 'w', **profile) as dst:
                dst.write(gli, 1)
                
            with rasterio.open(f"{base_name}_VARI.tif", 'w', **profile) as dst:
                dst.write(vari, 1)
                
    except Exception as e:
        print(f"Error índices {tif_path}: {e}")


# -------------------------------
# MAIN EXECUTION
# -------------------------------

def main():
    print("=== GEORREFERENCIACIÓN AUTOMÁTICA CON ELEVACIÓN (OPEN-ELEVATION) ===")
    print("Nota: Se utiliza Open-Elevation API en lugar de Google Earth Pro para automatización.")
    
    # 1. Conversión DNG -> JPG
    print("\n--- Paso 1: Verificando imágenes ---")
    convert_all_dng_to_jpg()
    
    images = sorted(glob.glob("*.jpg"))
    if not images:
        print("No hay imágenes JPG.")
        return

    # 2. Obtener datos y elevaciones
    print("\n--- Paso 2: Obteniendo elevaciones del terreno ---")
    data = init_and_process_data(images)
    
    if not data:
        print("Error al procesar datos.")
        return

    # 3. Procesar correcciones
    print("\n--- Paso 3: Calculando correcciones y georreferenciando ---")
    
    # Buscar referencia (001)
    ref_row = next((row for row in data if "001" in row['imagen']), None)
    if not ref_row:
        print("Error: No se encuentra imagen 001 para referencia.")
        return
        
    elev_ref = float(ref_row['elevacion_terreno_m'])
    alt_exif_ref = float(ref_row['altitud_m'])
    
    print(f"Referencia (001): Elevación Terreno = {elev_ref} m, Altitud Vuelo = {alt_exif_ref} m")
    
    for row in data:
        img_name = row['imagen']
        try:
            elev_terreno = float(row['elevacion_terreno_m'])
            alt_exif = float(row['altitud_m'])
            
            # Cálculo de corrección
            diff_elev = elev_ref - elev_terreno
            row['diferencia_elevacion_m'] = round(diff_elev, 3)
            
            alt_rel_exif = alt_exif - alt_exif_ref
            alt_rel_corrected = alt_rel_exif + diff_elev
            row['altitud_relativa_m'] = round(alt_rel_corrected, 3)
            
            # Footprint y esquinas
            width, height = calculate_ground_dimensions(alt_rel_corrected)
            row['ancho_m'] = round(width, 3)
            row['alto_m'] = round(height, 3)
            
            pitch = float(row['pitch_deg'])
            roll = float(row['roll_deg'])
            yaw = float(row['yaw_deg'])
            x_crtm = float(row['x_crtm05'])
            y_crtm = float(row['y_crtm05'])
            
            corners = apply_attitude_correction(x_crtm, y_crtm, width, height, alt_rel_corrected, pitch, roll, yaw)
            create_points_file(img_name, corners)
            
            georeference_image(img_name, os.path.splitext(img_name)[0] + ".points")
            
        except Exception as e:
            print(f"Error procesando {img_name}: {e}")
            continue
            
    save_csv(data)
    print("\n=== PROCESO COMPLETADO EXITOSAMENTE ===")

if __name__ == "__main__":
    main()
