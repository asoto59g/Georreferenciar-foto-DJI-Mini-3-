import os
import glob
import exifread
from pyproj import Transformer
import math
from PIL import Image
import rawpy
import numpy as np
import subprocess
import csv

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
# CONVERSIÓN DNG → JPG (máxima calidad)
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


# -------------------------------
# COPIAR METADATOS GPS CON EXIFTOOL
# -------------------------------
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


# -------------------------------
# LECTURA ROBUSTA DE EXIF
# -------------------------------
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


# -------------------------------
# CÁLCULOS GEOMÉTRICOS
# -------------------------------
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


# -------------------------------
# CREAR ARCHIVO .points
# -------------------------------
def create_points_file(image_name, corners):
    """Genera el archivo .points compatible con QGIS."""
    points_filename = os.path.splitext(image_name)[0] + ".points"
    with open(points_filename, "w") as f:
        f.write("# mapX,mapY,pixelX,pixelY,enable\n")
        for (mapX, mapY, px, py) in corners:
            f.write(f"{mapX:.3f},{mapY:.3f},{px},{py},1\n")
    print(f"Archivo generado: {points_filename}")


# -------------------------------
# CREAR ARCHIVO CSV DE RESUMEN
# -------------------------------
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
# MAIN
# -------------------------------
def main():
    # 1. Convertir DNG a JPG (máxima calidad)
    convert_all_dng_to_jpg()

    # 2. Procesar imágenes JPG
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


if __name__ == "__main__":
    main()