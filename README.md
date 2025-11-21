# Georreferenciar foto DJI Mini 3
Georreferenciación de fotos de DJI Mini 3 con metadatos gps de exif en Qgis. Es necesario solo las coordenadas del centroide de la foto para generar la georreferenciacion aproximada con un script de Python
## 1. Introducción
Este proyecto automatiza la generación de archivos de puntos de control (.points) y un resumen de cálculos (resumen_calculos.csv) a partir de fotografías tomadas con un dron DJI Mini 3 Pro. El objetivo es facilitar la georreferenciación de imágenes en QGIS mediante un proceso reproducible y preciso.
________________________________________
## 2. Requisitos previos
Hardware
•	Dron DJI Mini 3 Pro (o similar con GPS integrado).
•	Computadora con Python 3.9+ instalado.
Software
•	Python 3.9 o superior
•	QGIS 3.22+
•	ExifTool (para copiar metadatos GPS)
•	Librerías de Python:
pip install rawpy pillow exifread pyproj numpy
________________________________________
## 3. Captura de imágenes con el dron
1.	Configuración del vuelo:
o	Activar el registro de coordenadas GPS en la cámara.
o	Mantener la cámara en modo nadiral (vertical).
o	Configurar la resolución máxima (8064×6048 px).
o	Desactivar filtros automáticos de exposición o HDR.
2.	Secuencia de captura:
o	Tomar una primera foto en el punto de referencia (suelo). Esta imagen debe tener en su nombre el sufijo 001 (por ejemplo, DJI_001.DNG).
o	Continuar tomando las demás fotos a diferentes alturas o posiciones.
3.	Formato de archivo:
o	Guardar las imágenes en formato RAW (.DNG) para conservar metadatos completos.
________________________________________
## 4. Estructura de archivos
Colocar todos los archivos .DNG y el script generar_points.py en una misma carpeta:
📂 Proyecto_Georreferenciacion
 ├── generar_points.py
 ├── DJI_001.DNG
 ├── DJI_002.DNG
 ├── DJI_003.DNG
 └── ...
________________________________________
## 5. Ejecución del script
1.	Abrir una terminal en la carpeta del proyecto.
2.	Ejecutar:
python georefraw.py
3.	El script realizará automáticamente:
o	Conversión de .DNG → .JPG (máxima calidad).
o	Copia de metadatos GPS con exiftool.
o	Cálculo de altura relativa (usando la foto 001 como referencia).
o	Generación de archivos .points (para QGIS).
o	Creación del archivo resumen_calculos.csv con todos los datos.
________________________________________
## 6. Archivos generados
Tipo	Descripción
.jpg	Imagen convertida desde el archivo RAW.
.points	Archivo de puntos de control para QGIS.
resumen_calculos.csv	Tabla con coordenadas, alturas y dimensiones calculadas.
Ejemplo de resumen_calculos.csv:
imagen	latitud	longitud	altitud_m	altitud_relativa_m	x_crtm05	y_crtm05	ancho_m	alto_m	dx_m	dy_m
DJI_001.JPG	9.9345	-84.0912	120.5	0.0	500000.123	1100000.456	0.0	0.0	0.0	0.0
DJI_002.JPG	9.9346	-84.0913	130.8	10.3	500010.789	1100010.234	18.5	15.2	9.25	7.6
________________________________________
## 7. Carga en QGIS
1.	Abrir QGIS.
2.	Ir a Raster → Georreferenciador.
3.	Cargar la imagen .jpg correspondiente.
4.	En el menú del georreferenciador, seleccionar:
o	Archivo → Cargar puntos de control desde archivo...
o	Elegir el archivo .points generado por el script.
5.	Verificar que los puntos se carguen correctamente.
6.	Configurar el sistema de referencia:
o	CRTM05 (EPSG:8908) para Costa Rica.
7.	Ejecutar la georreferenciación:
o	Método de transformación: Polinomial 1 o Helmert.
o	Resampling: Bilineal o Cúbico.
8.	Guardar el raster georreferenciado.
________________________________________
## 8. Validación de resultados
•	Revisar el archivo resumen_calculos.csv para verificar:
o	Alturas relativas correctas.
o	Dimensiones del terreno (ancho_m, alto_m).
o	Coordenadas proyectadas (x_crtm05, y_crtm05).
•	En QGIS, comprobar que las imágenes se alineen correctamente con la base cartográfica.
________________________________________
## 9. Solución de problemas
Problema	Causa	Solución
PermissionError: resumen_calculos.csv	Archivo abierto en Excel	Cerrar el archivo o dejar que el script cree una nueva versión (resumen_calculos_1.csv).
KeyError: 'GPS GPSLatitude'	Falta de metadatos GPS	Asegurarse de que el dron tenga GPS activo y que exiftool copie los metadatos.
Imágenes desplazadas en QGIS	Altura de referencia incorrecta	Verificar que la foto 001 sea la tomada en el suelo.
________________________________________
## 10. Créditos y mantenimiento
Desarrollado por el equipo de ingeniería de Basdonax AI, especializado en soluciones de georreferenciación y sistemas RAG estructurados.
Autor técnico: Alejandro Soto Barquero Versión: 1.0 — Noviembre 2025


