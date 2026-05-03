[![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/d4db126d4690cabce9824f110f4fcce270c0fd92/geo.jpg)](https://vimeo.com/1139364574?fl=ip&fe=ec "DAR clic para ver Video")
# :world_map: Georreferenciar foto DJI Mini 3 a 48 MP
Georreferenciación de fotos de DJI Mini 3 con metadatos gps de exif. Es necesario solo las coordenadas del centroide de la foto para generar la georreferenciacion aproximada con un script de Python. Script de procesamiento automatizado para georreferenciar fotografías aéreas, generando GeoTIFFs e índices de vegetación listos para análisis en QGIS.

Archivos de ejemplo en la siguiente carpeta [Carpeta ejemplo](https://drive.google.com/drive/folders/1V3cBZyV1fmi-PAEcXbXMzmQ8Y6Ll3bVL?usp=drive_link) Se incluye script python `fullorthorect.py`
## 1. Introducción
Este proyecto automatiza la conversion de archivos DNG a JPG, además la generación de archivos de puntos de control (.points), un resumen de cálculos (resumen_calculos.csv), archivos TIFF georreferenciados y calculos de indices GLI y VARI; a partir de fotografías tomadas con un dron DJI Mini 3 Pro. El objetivo es facilitar la georreferenciación de imágenes para utilizar en cualquier GIS mediante un proceso reproducible y preciso.
________________________________________
## 2. Requisitos previos
### 1. Hardware

•	Dron DJI Mini 3 Pro (o similar con GPS integrado). <img width="30" height="30" src="https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/b344385361357150692c1e50d95ac187eb3aaf4c/drone-icon.png" />

•	Computadora con Python 3.9+ instalado. :computer:

### 2. Software

•	Python 3.9 o superior. <img width="20" height="20" alt="Python-logo-notext svg" src="https://github.com/user-attachments/assets/8e07cc75-0360-475c-9416-54fbdaef812a" />


•	QGIS 3.22+. <img width="20" height="20" alt="QGIS_logo_new svg" src="https://github.com/user-attachments/assets/ada37092-202a-4d03-82f5-d40bb2e19037" /> o software GIS de su preferencia (ArcGis-ESRI, MapInfo, GoogleEarth, Global Mapper, etc)


•	ExifTool (para copiar metadatos GPS) <img width="20" height="20" alt="exiftool" src="https://github.com/user-attachments/assets/1b123e49-0efe-4a35-acb5-2d9d040e2007" /> 
[Pagina instalacion](https://exiftool.org/install.html)

•	Librerías de Python:
```bash
pip install exifread pyproj Pillow rawpy numpy rasterio attrs click cligj
```

| Biblioteca | Función |
|---|---|
| `exifread` | Lectura de metadatos EXIF/GPS de las imágenes |
| `pyproj` | Transformación de coordenadas WGS84 → CRTM05 |
| `Pillow` | Manipulación y conversión de imágenes |
| `rawpy` | Decodificación de archivos DNG (RAW) |
| `numpy` | Operaciones matriciales y cálculo de índices |
| `rasterio` | Generación de GeoTIFFs georreferenciados |

________________________________________
## 3. Captura de imágenes con el dron
### 1.	Configuración del vuelo:

•	Activar el registro de coordenadas GPS en la cámara.

•	Mantener la cámara en modo nadiral (vertical).


•	Configurar la resolución máxima (8064×6048 px). Formato DNG 48MP<img width="800" height="360" alt="Screenshot_20251122-102110_DJI Fly" src="https://github.com/user-attachments/assets/d5653f58-4544-43a5-b3f6-6aa35c1ee415" />
 <img width="800" height="360" alt="Screenshot_20251122-102212_DJI Fly" src="https://github.com/user-attachments/assets/cafdd9fa-6b5b-493f-964b-ef05d2861f54" />


•	Desactivar filtros automáticos de exposición o HDR.

### 2.	Secuencia de captura:

•	Tomar una primera foto en el punto de referencia (suelo). Esta imagen debe tener en su nombre el sufijo 001 (por ejemplo, DJI_001.DNG). Esperar que el dron tenga la mayor cantidad de satélites gps a disposición, no apresurar el despegue de la nave. La precisión vertical con buena señal es +- 0.1 m en mini 3.

•	Continuar tomando las demás fotos a diferentes alturas o posiciones. Orientar dron al NORTE con pantallas de navegación.
Esto con el fin que la foto quede orientada en georreferenciación, en formato RAW el disparo de la cámara es tardado :stopwatch: , tener paciencia. Si la diferencia de altura es muy grande desde el punto de referencia (suelo) y puntos donde se toman el resto de fotos disminuye la precisión de georeferenciación, debe ser menos de 2 metros para obtener resultados aceptables. Por lo tanto en terreno quebrado es poco recomendable aplicar script. Además entre mas alto se vuele el dron el margen de error dismininuye.

### 3.	Formato de archivo:

•	Guardar las imágenes en formato RAW (.DNG) para conservar metadatos completos.
<img width="1365" height="725" alt="image" src="https://github.com/user-attachments/assets/cbf98386-dda7-421b-b153-6483670a9604" />

________________________________________
## 4. Estructura de archivos
Colocar todos los archivos .DNG y el script `fullorthorect.py` en una misma carpeta:

📂 Carpeta ejemplo
 ├── fullorthorect.py
 ├── DJI_001.DNG
 ├── DJI_002.DNG
 ├── DJI_003.DNG
 └── ...
________________________________________
## 5. Ejecución del script y Parámetros Configurables

### 1.	Abrir una terminal en la carpeta del proyecto.
### 2.	Ejecutar:
```bash
python fullorthorect.py
```
### 3.	El script realizará automáticamente 3 pasos secuenciales:

**Paso 1 — Conversión DNG → JPG**
•	Conversión de .DNG → .JPG (máxima calidad sin submuestreo) usando `rawpy`.
•	Copia de metadatos GPS/EXIF con exiftool.

**Paso 2 — Generación de Puntos de Control (GCPs)**
•	Lectura de coordenadas GPS (lat, lon, alt) y ángulos de actitud (pitch, roll, yaw) desde metadatos.
La función `get_exif_data()` retorna 6 valores:
```python
# Antes:
lat, lon, alt = get_exif_data(image)

# Ahora:
lat, lon, alt, pitch, roll, yaw = get_exif_data(image)
```
•	Transformación de coordenadas WGS84 (EPSG:4326) a CRTM05 (EPSG:8908).
•	Cálculo de altura relativa (usando la foto 001 como referencia).
•	Generación de archivos .points (para QGIS) aplicando corrección de actitud si hay inclinación y cálculo de footprint basado en dimensiones del sensor y FOV.
•	Creación del archivo `resumen_calculos.csv` con todos los datos.
![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/8b89e2bcf076a030578b21a05d682183da7b2681/dos.jpg)

**Paso 3 — GeoTIFFs e Índices de Vegetación**
• Calculado GLI y VARI índices para cada imagen.

| Índice | Fórmula | Uso |
|---|---|---|
| **GLI** (Green Leaf Index) | `((G-R) + (G-B)) / (2G + R + B)` | Detección de vegetación verde |
| **VARI** (Visible Atmospherically Resistant Index) | `(G-R) / (G + R - B)` | Vigor vegetal, resistente a variación atmosférica |

• Guardado el resultados como GeoTIFF mediante transformación afín.

### 4. Parámetros Configurables en `fullorthorect.py`

**Cámara DJI Mini 3 Pro**
```python
SENSOR_WIDTH_MM = 9.6       # Ancho del sensor en mm
SENSOR_HEIGHT_MM = 7.2      # Alto del sensor en mm
FOCAL_LENGTH_MM = 6.7       # Distancia focal en mm
IMAGE_WIDTH_PX = 8064       # Resolución horizontal (48MP)
IMAGE_HEIGHT_PX = 6048      # Resolución vertical (48MP)
```

**Corrección de Offset GPS**
El GPS del DJI Mini 3 Pro tiene una precisión típica de 1–20 metros. Este offset compensa el error sistemático por sesión de vuelo.
```python
OFFSET_X_M = -7.6   # Corrección Este  (metros)
OFFSET_Y_M = -27.8  # Corrección Norte (metros)
```

________________________________________
## 6. Archivos generados

| Archivo | Descripción |
|---|---|
| `*.jpg` | Imagenes convertidas desde el archivo RAW. |
| `*.points` | Archivos de puntos de control para QGIS. |
| `*_georef.tif` | GeoTIFF georreferenciado en CRTM05 (ej. `DJI_0001_georef.tif`). |
| `*_georef_GLI.tif` | Índice GLI (Green Leaf Index). |
| `*_georef_VARI.tif` | Índice VARI (Visible Atmospherically Resistant Index). |
| `resumen_calculos.csv` | Tabla con coordenadas, alturas y dimensiones calculadas. |

Ejemplo de `resumen_calculos.csv`:

<img width="700" height="302" alt="image" src="https://github.com/user-attachments/assets/512e5aa4-4f61-44af-ac57-d5b5629dbc68" />

El archivo `resumen_calculos.csv` ahora incluye columnas adicionales:
- `pitch_deg`: Ángulo de cabeceo
- `roll_deg`: Ángulo de alabeo  
- `yaw_deg`: Ángulo de guiñada

________________________________________
## 7. Como utilizar y Calibrar

### 1.	Asegurar que todos los archivos con extension DNG se encuentran en la carpeta correspondientes

### 2.	Copie en la misma carpeta el archivo `fullorthorect.py` y ejecutar con comando `python fullorthorect.py` en consola de comandos para ejecutar flujo completo de trabajo.

#### Flujo de Trabajo Completo:
```text
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Fotos DNG  │────▶│  Conversión  │────▶│   Fotos JPG   │
│  del drone  │     │  DNG → JPG   │     │  con GPS EXIF │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                 │
                    ┌──────────────┐             │
                    │  Lectura GPS │◀────────────┘
                    │  + Actitud   │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │  Transformación WGS84   │
              │  → CRTM05 + Offset GPS  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Cálculo de Footprint   │
              │  + Corrección Actitud   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Archivos .points       │
              │  + resumen_calculos.csv │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  GeoTIFF Georreferenciado│
              │  (*_georef.tif)         │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  Índices de Vegetación  │
              │  GLI + VARI             │
              └─────────────────────────┘
```

### 3. Calibrar el offset GPS:
El offset cambia con cada sesión de vuelo, por lo que debe recalibrarse para cada lote de fotos:
1. Ejecutar el script con `OFFSET_X_M = 0` y `OFFSET_Y_M = 0`
2. Cargar el GeoTIFF resultante en QGIS sobre un basemap (preferiblemente ortofotos del SNIT).
3. Identificar un punto reconocible (esquina de edificio, intersección de calles)
4. Con la herramienta **Medir**, medir la distancia en X e Y desde la posición en la **foto del drone** hasta la posición real en el **basemap**
5. Si la foto está desplazada al **NE**, usar valores **negativos**; si está al **SO**, usar valores **positivos**
6. Re-ejecutar el script con los nuevos valores

> ⚠️ **Importante:** La corrección de georreferenciación debe realizarse utilizando las **ortofotos actualizadas del SNIT Costa Rica** como capa base de referencia. No se recomienda utilizar mapas base comerciales (como Google Satellite) ya que suelen presentar desplazamientos espaciales significativos respecto a la cartografía oficial.

### 4.	Abrir los archivos TIFF generados con sotfware QGIS o GIS de preferrencia, para verificar alineación y visualización índices.
<img width="1353" height="707" alt="image" src="https://github.com/user-attachments/assets/19a0475e-3410-435b-9283-26d4d1910576" />

________________________________________
## 8. Validación de resultados

### •	Revisar el archivo resumen_calculos.csv para verificar:

#### -	Alturas relativas correctas.

#### -	Dimensiones del terreno (ancho_m, alto_m).

#### -	Coordenadas proyectadas (x_crtm05, y_crtm05). EPSG:8908 :costa_rica:

### •	En QGIS o GIS de preferencia, comprobar que las imágenes se alineen correctamente con la base cartográfica.
________________________________________
## 9. Notas Técnicas y Solución de problemas

### Notas Técnicas
- **FOV**: El DJI Mini 3 Pro reporta FOV diagonal de 82.1°. El script calcula los FOV horizontal (71.2°) y vertical (56.5°) a partir de las dimensiones físicas del sensor y la distancia focal, evitando errores de escala en el footprint.
- **Actitud**: La corrección por pitch/roll/yaw utiliza matrices de rotación 3D con orden ZYX (Yaw → Pitch → Roll), proyectando las esquinas rotadas de vuelta al plano del suelo.
- **PROJ_LIB**: El script desactiva la variable de entorno `PROJ_LIB` al inicio para evitar conflictos con instalaciones de PostgreSQL/PostGIS que puedan tener otra versión de PROJ.

### Solución de problemas
| Problema | Causa | Solución |
|---|---|---|
| **PermissionError:** `resumen_calculos.csv` | Archivo abierto en Excel | Cerrar el archivo o dejar que el script cree una nueva versión. |
| **KeyError:** `'GPS GPSLatitude'` | Falta de metadatos GPS | Asegurarse de que el dron tenga GPS activo y que exiftool copie los metadatos. |
| **Imágenes desplazadas en QGIS** | Altura de referencia incorrecta | Verificar que la foto 001 sea la tomada en el suelo. Además asegurarse de calibrar el offset usando ortofotos del SNIT. |

________________________________________
## 10. Créditos y mantenimiento

• Desarrollado por el equipo de ingeniería de Basdonax AI y ABC Geomática Agrícola SRL, especializado en soluciones de georreferenciación y sistemas RAG estructurados. :dollar: $ 0.49 en tokens con modelo <img width="42" height="16" alt="chatgpt-5-logo-3000-20001" src="https://github.com/user-attachments/assets/90a49351-1ec5-4e2d-bfce-d09fcc52c65f" />

• Desarrollo completado con Antigravity <img width="120" height="72" alt="image" src="https://github.com/user-attachments/assets/0845b0b1-8134-46b1-90f4-10dec1a08274"/> modelo Gemini 3.0 <img width="60" height="36" alt="image" src="https://github.com/user-attachments/assets/c0abfbc8-cdd9-4cea-877c-a8ea3205a145"/>



• Autor técnico: Alejandro Soto Barquero Versión: 2.0 — Noviembre 2025.

[![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/7237d9762a361f088f93db0684754c2e755e4fff/qgis.jpg)](https://vimeo.com/1139745299?fl=ip&fe=ec "DAR clic para ver Video")

P.D. En la primera y última imagen del README.md hay un video de VIMEO vinculado a cada imagen
