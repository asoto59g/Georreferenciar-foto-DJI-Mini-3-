
[![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/d4db126d4690cabce9824f110f4fcce270c0fd92/geo.jpg)](https://vimeo.com/1139364574?fl=ip&fe=ec "DAR clic para ver Video")
# :world_map: Georreferenciar foto DJI Mini 3 a 48 MP
Georreferenciación de fotos de DJI Mini 3 con metadatos gps de exif en Qgis. Es necesario solo las coordenadas del centroide de la foto para generar la georreferenciacion aproximada con un script de Python

Archivos de ejemplo en la siguiente carpeta [Carpeta ejemplo](https://drive.google.com/drive/folders/1V3cBZyV1fmi-PAEcXbXMzmQ8Y6Ll3bVL?usp=drive_link)
## 1. Introducción
Este proyecto automatiza la generación de archivos de puntos de control (.points) y un resumen de cálculos (resumen_calculos.csv) a partir de fotografías tomadas con un dron DJI Mini 3 Pro. El objetivo es facilitar la georreferenciación de imágenes en QGIS mediante un proceso reproducible y preciso.
________________________________________
## 2. Requisitos previos
### 1. Hardware

•	Dron DJI Mini 3 Pro (o similar con GPS integrado).

•	Computadora con Python 3.9+ instalado. :computer:

### 2. Software

•	Python 3.9 o superior

•	QGIS 3.22+

•	ExifTool (para copiar metadatos GPS) [Pagina instalacion](https://exiftool.org/install.html)

•	Librerías de Python:
pip install rawpy pillow exifread pyproj numpy
________________________________________
## 3. Captura de imágenes con el dron
### 1.	Configuración del vuelo:

•	Activar el registro de coordenadas GPS en la cámara.

•	Mantener la cámara en modo nadiral (vertical).


•	Configurar la resolución máxima (8064×6048 px). Formato DNG 48MP

•	Desactivar filtros automáticos de exposición o HDR.

### 2.	Secuencia de captura:

•	Tomar una primera foto en el punto de referencia (suelo). Esta imagen debe tener en su nombre el sufijo 001 (por ejemplo, DJI_001.DNG).

•	Continuar tomando las demás fotos a diferentes alturas o posiciones. Orientar dron al NORTE con pantallas de navegacion.
Esto con el fin que la foto quede orientada en georreferenciacion, en formato RAW el disparo de la camara es tardado :stopwatch: , tener paciencia.

### 3.	Formato de archivo:

•	Guardar las imágenes en formato RAW (.DNG) para conservar metadatos completos.
![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/a3d0347772fd488974b06191f69bbea946477c28/carpetaejemplo.jpg)
________________________________________
## 4. Estructura de archivos
Colocar todos los archivos .DNG y el script georefraw.py en una misma carpeta:

📂 Proyecto_Georreferenciacion
 ├── georefraw.py
 ├── DJI_001.DNG
 ├── DJI_002.DNG
 ├── DJI_003.DNG
 └── ...
________________________________________
## 5. Ejecución del script
### 1.	Abrir una terminal en la carpeta del proyecto.
### 2.	Ejecutar:
python georefraw.py
### 3.	El script realizará automáticamente:

•	Conversión de .DNG → .JPG (máxima calidad).

•	Copia de metadatos GPS con exiftool.

•	Cálculo de altura relativa (usando la foto 001 como referencia).

•	Generación de archivos .points (para QGIS).

•	Creación del archivo resumen_calculos.csv con todos los datos.
![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/8b89e2bcf076a030578b21a05d682183da7b2681/dos.jpg)
________________________________________
## 6. Archivos generados
Tipo	Descripción

.jpg	Imagen convertida desde el archivo RAW.

.points	Archivo de puntos de control para QGIS.

resumen_calculos.csv	Tabla con coordenadas, alturas y dimensiones calculadas.

Ejemplo de resumen_calculos.csv:

<img width="718" height="61" alt="image" src="https://github.com/user-attachments/assets/4dea7824-47e1-4794-96d0-d69510a4cac2" />

________________________________________
## 7. Carga en QGIS
### 1.	Abrir QGIS.
### 2.	Ir a Raster → Georreferenciador.
### 3.	Cargar la imagen .jpg correspondiente.
### 4.	En el menú del georreferenciador, seleccionar:
•	Archivo → Cargar puntos de control desde archivo...
•	Elegir el archivo .points generado por el script.
### 5.	Verificar que los puntos se carguen correctamente.
### 6.	Configurar el sistema de referencia:
•	CRTM05 (EPSG:8908) para Costa Rica. :costa_rica:
### 7.	Ejecutar la georreferenciación:
•	Método de transformación: Polinomial 1 o Helmert.
•	Resampling: Bilineal o Cúbico.
### 8.	Guardar el raster georreferenciado.
![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/5723a0837717304a04bd9ef63a9139bd404ad1a2/gcp.jpg)

![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/ce13a4700370aacde91091de0f278e40b2776f36/georeferenciador.jpg)
________________________________________
## 8. Validación de resultados

### •	Revisar el archivo resumen_calculos.csv para verificar:

#### -	Alturas relativas correctas.

#### -	Dimensiones del terreno (ancho_m, alto_m).

#### -	Coordenadas proyectadas (x_crtm05, y_crtm05).
![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/bfd3d37ede065de1876cabbd650bbb76a66d754a/ejecutado.jpg)

### •	En QGIS, comprobar que las imágenes se alineen correctamente con la base cartográfica.
________________________________________
## 9. Solución de problemas
Problema	Causa	Solución

• PermissionError: resumen_calculos.csv	Archivo abierto en Excel	Cerrar el archivo o dejar que el script cree una nueva versión (resumen_calculos_1.csv).

• KeyError: 'GPS GPSLatitude'	Falta de metadatos GPS	Asegurarse de que el dron tenga GPS activo y que exiftool copie los metadatos.

• Imágenes desplazadas en QGIS	Altura de referencia incorrecta	Verificar que la foto 001 sea la tomada en el suelo.
________________________________________
## 10. Créditos y mantenimiento

• Desarrollado por el equipo de ingeniería de Basdonax AI, especializado en soluciones de georreferenciación y sistemas RAG estructurados. $ 0.49 en tokens

• Autor técnico: Alejandro Soto Barquero Versión: 1.0 — Noviembre 2025.

![Captura de pantalla](https://github.com/asoto59g/Georreferenciar-foto-DJI-Mini-3-/blob/7237d9762a361f088f93db0684754c2e755e4fff/qgis.jpg)


