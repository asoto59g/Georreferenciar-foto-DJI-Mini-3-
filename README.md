[![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/d4db126d4690cabce9824f110f4fcce270c0fd92/geo.jpg)](https://vimeo.com/1139364574?fl=ip&fe=ec "DAR clic para ver Video")
# :world_map: Georreferenciar foto DJI Mini 3 a 48 MP
Georreferenciación de fotos de DJI Mini 3 con metadatos gps de exif. Es necesario solo las coordenadas del centroide de la foto para generar la georreferenciacion aproximada con un script de Python

Archivos de ejemplo en la siguiente carpeta [Carpeta ejemplo](https://drive.google.com/drive/folders/1V3cBZyV1fmi-PAEcXbXMzmQ8Y6Ll3bVL?usp=drive_link)
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
pip install rawpy pillow exifread pyproj numpy

• Instalado adicional dependencias para automatización : rasterio , attrs , clic , complementos de clic , cligj
________________________________________
## 3. Captura de imágenes con el dron
### 1.	Configuración del vuelo:

•	Activar el registro de coordenadas GPS en la cámara.

•	Mantener la cámara en modo nadiral (vertical).


•	Configurar la resolución máxima (8064×6048 px). Formato DNG 48MP<img width="800" height="360" alt="Screenshot_20251122-102110_DJI Fly" src="https://github.com/user-attachments/assets/d5653f58-4544-43a5-b3f6-6aa35c1ee415" />
 <img width="800" height="360" alt="Screenshot_20251122-102212_DJI Fly" src="https://github.com/user-attachments/assets/cafdd9fa-6b5b-493f-964b-ef05d2861f54" />


•	Desactivar filtros automáticos de exposición o HDR.

### 2.	Secuencia de captura:

•	Tomar una primera foto en el punto de referencia (suelo). Esta imagen debe tener en su nombre el sufijo 001 (por ejemplo, DJI_001.DNG).

•	Continuar tomando las demás fotos a diferentes alturas o posiciones. Orientar dron al NORTE con pantallas de navegacion.
Esto con el fin que la foto quede orientada en georreferenciacion, en formato RAW el disparo de la camara es tardado :stopwatch: , tener paciencia.

### 3.	Formato de archivo:

•	Guardar las imágenes en formato RAW (.DNG) para conservar metadatos completos.
<img width="1365" height="725" alt="image" src="https://github.com/user-attachments/assets/cbf98386-dda7-421b-b153-6483670a9604" />

________________________________________
## 4. Estructura de archivos
Colocar todos los archivos .DNG y el script fullgeoref.py en una misma carpeta:

📂 Carpeta ejemplo
 ├── fullgeoref.py
 ├── DJI_001.DNG
 ├── DJI_002.DNG
 ├── DJI_003.DNG
 └── ...
________________________________________
## 5. Ejecución del script
### 1.	Abrir una terminal en la carpeta del proyecto.
### 2.	Ejecutar:
python fullgeoref.py
### 3.	El script realizará automáticamente:

•	Conversión de .DNG → .JPG (máxima calidad).

•	Copia de metadatos GPS con exiftool.

•	Cálculo de altura relativa (usando la foto 001 como referencia).

•	Generación de archivos .points (para QGIS).

•	Creación del archivo resumen_calculos.csv con todos los datos.
![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/8b89e2bcf076a030578b21a05d682183da7b2681/dos.jpg)

• Calculado GLI y VARI índices para cada imagen .

• Guardado el resultados como GeoTIFF .


________________________________________
## 6. Archivos generados
Tipo	Descripción

### 1. *.jpg
Imagenes convertidas desde el archivo RAW.

### 2. *.points	
Archivos de puntos de control para QGIS.

### 3. resumen_calculos.csv
Tabla con coordenadas, alturas y dimensiones calculadas.

Ejemplo de resumen_calculos.csv:

<img width="700" height="302" alt="image" src="https://github.com/user-attachments/assets/512e5aa4-4f61-44af-ac57-d5b5629dbc68" />

### 4. Archivos generados :

DJI_0001_georef.tif a DJI_0014_georef.tif.

DJI_0001_georef_GLI.tif a DJI_0014_georef_GLI.tif.

DJI_0001_georef_VARI.tif a DJI_0014_georef_VARI.tif.

________________________________________
## 7. Como utilizar


### 1.	Asegurar que todos los archivos con extension DNG se encuentran en la carpeta correspondientes

### 2.	Copie en la misma carpeta el archivo "fullgeoref.py"  y ejecutar con comando python fullgeoref.py en consola de comandos para ejecutar flujo completo de trabajo.

#### • Convertir DNG -> JPG
#### • Copiar metadatos con Exiftool
#### • Generar GCP
#### • Georreferenciación -> _ georef.tif
#### • Calcular Índices -> _ GLI.tif , _ VARI.tif

### 3	Abrir los archivos TIFF generados con sotfware QGIS o GIS de preferrencia, para verificar alineación y visualización índices.
<img width="1353" height="707" alt="image" src="https://github.com/user-attachments/assets/19a0475e-3410-435b-9283-26d4d1910576" />

________________________________________
## 8. Validación de resultados

### •	Revisar el archivo resumen_calculos.csv para verificar:

#### -	Alturas relativas correctas.

#### -	Dimensiones del terreno (ancho_m, alto_m).

#### -	Coordenadas proyectadas (x_crtm05, y_crtm05).
![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/bfd3d37ede065de1876cabbd650bbb76a66d754a/ejecutado.jpg)

### •	En QGIS o GIS de preferencia, comprobar que las imágenes se alineen correctamente con la base cartográfica.
________________________________________
## 9. Solución de problemas
Problema	Causa	Solución

### • PermissionError:
  resumen_calculos.csv	Archivo abierto en Excel	Cerrar el archivo o dejar que el script cree una nueva versión (resumen_calculos_1.csv).

### • KeyError:
'GPS GPSLatitude'	Falta de metadatos GPS	Asegurarse de que el dron tenga GPS activo y que exiftool copie los metadatos.

### • Imágenes desplazadas
en QGIS	Altura de referencia incorrecta	Verificar que la foto 001 sea la tomada en el suelo.
________________________________________
## 10. Créditos y mantenimiento

• Desarrollado por el equipo de ingeniería de Basdonax AI, especializado en soluciones de georreferenciación y sistemas RAG estructurados. :dollar: $ 0.49 en tokens con modelo <img width="42" height="16" alt="chatgpt-5-logo-3000-20001" src="https://github.com/user-attachments/assets/90a49351-1ec5-4e2d-bfce-d09fcc52c65f" />

• Desarrollo completado con Antigravity <img width="120" height="72" alt="image" src="https://github.com/user-attachments/assets/0845b0b1-8134-46b1-90f4-10dec1a08274"/> modelo Gemini 3.0 <img width="60" height="36" alt="image" src="https://github.com/user-attachments/assets/c0abfbc8-cdd9-4cea-877c-a8ea3205a145"/>



• Autor técnico: Alejandro Soto Barquero Versión: 1.0 — Noviembre 2025.

[![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/7237d9762a361f088f93db0684754c2e755e4fff/qgis.jpg)](https://vimeo.com/1139745299?fl=ip&fe=ec "DAR clic para ver Video")

P.D. En la primera y última imagen del README.md hay un video de VIMEO vinculado a cada imagen
