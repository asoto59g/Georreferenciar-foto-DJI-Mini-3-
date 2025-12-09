# Documentación del Script de Georreferenciación Automática
**Archivo:** `full_georeference_auto_elevation.py`

Este documento detalla el funcionamiento, requisitos y estructura del script de georreferenciación automatizada para imágenes de drone (DJI Mini 3 Pro), incorporando corrección de elevación del terreno mediante API y corrección de actitud (Pitch, Roll, Yaw).

## 1. Descripción General

El script automatiza el flujo de trabajo completo para procesar imágenes aéreas, desde el revelado de archivos RAW (DNG) hasta la generación de ortofotos georreferenciadas (GeoTIFF) y mapas de índices de vegetación (GLI, VARI).

**Características principales:**
*   **Conversión DNG a JPG:** Revelado de alta calidad usando `rawpy`.
*   **Extracción de Metadatos:** Lectura de GPS y ángulos de actitud (Pitch, Roll, Yaw) desde EXIF/XMP.
*   **Corrección de Elevación Automática:** Consulta la API gratuita **Open-Elevation** para obtener la altitud del terreno en cada punto de captura, eliminando la necesidad de entrada manual.
*   **Corrección de Actitud:** Aplica una matriz de rotación 3D para proyectar correctamente el "footprint" de la foto en el suelo, compensando la inclinación del drone.
*   **Georreferenciación:** Genera archivos `.points` (GCPs) y utiliza `rasterio` para transformar las imágenes al sistema de coordenadas **CRTM05 (EPSG:8908)**.
*   **Índices de Vegetación:** Calcula automáticamente índices GLI y VARI.

## 2. Requisitos y Dependencias

### Librerías de Python
El script requiere las siguientes librerías externas. Pueden instalarse vía `pip`:

```bash
pip install rasterio rawpy exifread pyproj numpy Pillow
```

*   **`os`, `sys`, `glob`, `math`, `subprocess`, `csv`, `json`, `time`, `urllib`**: Librerías estándar de Python (no requieren instalación).
*   **`rasterio`**: Para manipulación de datos geoespaciales y creación de GeoTIFFs.
*   **`rawpy`**: Para el procesamiento y conversión de imágenes RAW (DNG).
*   **`exifread`**: Para leer metadatos EXIF de las imágenes.
*   **`pyproj`**: Para transformación de coordenadas (WGS84 a CRTM05).
*   **`numpy`**: Para cálculos matriciales (matrices de rotación).
*   **`Pillow` (PIL)**: Para manejo y guardado de imágenes JPG.

### Herramientas Externas
*   **`exiftool`**: Debe estar instalado en el sistema y accesible en el PATH (o junto al ejecutable/script). Se utiliza para copiar metadatos complejos del DNG al JPG que `Pillow` podría perder.
    *   Windows: `choco install exiftool` o descargar de [exiftool.org](https://exiftool.org/).

## 3. Procedimiento Paso a Paso

El script ejecuta la función `main()` que orquesta los siguientes pasos:

### Paso 1: Verificación y Conversión de Imágenes
*   Busca archivos `.dng` en el directorio actual.
*   Si existen, los convierte a `.jpg` usando `rawpy` para el revelado (balance de blancos cámara, sin auto-brillo, algoritmo AHD) y `exiftool` para transferir todos los metadatos originales.

### Paso 2: Obtención de Datos y Elevaciones
*   Lee los metadatos de cada imagen JPG (Latitud, Longitud, Altitud, Pitch, Roll, Yaw).
*   Transforma las coordenadas WGS84 (Lat/Lon) a CRTM05 (X/Y) usando `pyproj`.
*   **Consulta API:** Envía las coordenadas (Lat/Lon) a la API de Open-Elevation (`https://api.open-elevation.com/api/v1/lookup`) usando `urllib`.
*   Recibe la elevación del terreno (en metros) para cada foto.

### Paso 3: Cálculos y Georreferenciación
*   **Cálculo de Corrección:**
    *   Toma la imagen `...001.jpg` como referencia (punto de despegue).
    *   Calcula la diferencia de elevación del terreno: `Diff = Elev_Ref - Elev_Terreno_Actual`.
    *   Ajusta la altura relativa de vuelo: `Alt_Relativa_Corregida = Alt_Relativa_Barometrica + Diff`.
*   **Proyección del Footprint:**
    *   Calcula el ancho y alto del terreno cubierto por la foto basándose en la altura corregida y el FOV de la cámara.
    *   **Matriz de Rotación:** Construye una matriz 3D usando los ángulos Pitch, Roll y Yaw (con signos ajustados según pruebas: Yaw invertido).
    *   Proyecta las 4 esquinas de la imagen desde el sistema de cámara al sistema de coordenadas del suelo (CRTM05).
*   **Generación de Archivos:**
    *   Crea un archivo `.points` para cada imagen con los 4 Puntos de Control Terrestre (GCPs) calculados.
    *   Genera un archivo CSV `resumen_calculos_auto.csv` con todos los datos.
*   **Creación de GeoTIFF:**
    *   Usa `rasterio` y los GCPs para transformar la imagen JPG a un GeoTIFF georreferenciado en CRTM05.
*   **Cálculo de Índices:**
    *   A partir del GeoTIFF, genera dos archivos adicionales: `_GLI.tif` y `_VARI.tif`.

## 4. Detalle de Funciones Clave

### `get_elevations_from_api(locations)`
Maneja la comunicación con la API de Open-Elevation.
*   **Entrada:** Lista de diccionarios `{'latitude': ..., 'longitude': ...}`.
*   **Proceso:** Serializa los datos a JSON, hace un POST request usando `urllib.request` (para evitar dependencia de `requests`), y parsea la respuesta.
*   **Salida:** Lista de valores de elevación (float).

### `create_rotation_matrix(pitch, roll, yaw)`
Construye la matriz de rotación para corregir la perspectiva.
*   **Nota Importante:** Actualmente configurada con **Yaw invertido** (`-yaw`) basado en pruebas empíricas de alineación. Pitch y Roll se usan con signo positivo.
*   **Orden de Rotación:** Se aplica en orden Z-Y-X (Yaw -> Pitch -> Roll).

### `apply_attitude_correction(...)`
El núcleo matemático de la corrección geométrica.
1.  Define las esquinas de la imagen en un plano 3D relativo a la cámara.
2.  Rota estos puntos usando la matriz de rotación.
3.  Proyecta los puntos rotados sobre el plano del suelo (Z=0) usando geometría proyectiva.
4.  Devuelve las coordenadas (Este, Norte) reales de las 4 esquinas.

## 5. Archivos de Salida

1.  **`*_georef.tif`**: La imagen original georreferenciada.
2.  **`*_georef_GLI.tif`**: Índice Green Leaf Index.
3.  **`*_georef_VARI.tif`**: Índice Visible Atmospherically Resistant Index.
4.  **`resumen_calculos_auto.csv`**: Tabla con Lat, Lon, Alturas, Elevaciones del terreno, Ángulos y Coordenadas CRTM05 calculadas.
5.  **`*.points`**: Archivos de texto con los GCPs usados por QGIS/Rasterio.

---
**Autor:** Generado por Asistente de IA (Antigravity)
**Fecha:** 08/12/2025
