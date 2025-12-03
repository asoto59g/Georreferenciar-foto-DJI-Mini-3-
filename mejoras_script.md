# Script Mejorado de Georreferenciación con Corrección de Actitud

## 📋 Resumen de Mejoras

El nuevo script `fullgeorect.py` incluye mejoras significativas para aumentar la precisión de la georreferenciación de fotos aéreas del DJI Mini 3 Pro.

## 🎯 Principales Mejoras Implementadas

### 1. **Corrección de Actitud de Vuelo**

El script ahora extrae y utiliza los ángulos de actitud del drone desde los metadatos EXIF:

- **FlightPitchDegree**: Inclinación hacia adelante/atrás de la cámara
- **FlightRollDegree**: Inclinación lateral izquierda/derecha
- **FlightYawDegree**: Rotación/orientación de la cámara

#### Impacto
Cuando el drone toma fotos con la cámara inclinada (no en vista nadir perfecta), el footprint en el suelo cambia. La corrección de actitud calcula las coordenadas reales de las esquinas considerando esta inclinación.

### 2. **Matrices de Rotación 3D**

Se implementaron funciones matemáticas para aplicar transformaciones 3D:

```python
create_rotation_matrix(pitch, roll, yaw)
apply_attitude_correction(x, y, width, height, altitude, pitch, roll, yaw)
```

**Proceso:**
1. Calcula el footprint base (asumiendo vista nadir)
2. Convierte las esquinas 2D a coordenadas 3D
3. Aplica rotaciones usando matrices de Euler (orden: Yaw → Pitch → Roll)
4. Proyecta las esquinas rotadas de vuelta al plano del suelo
5. Obtiene coordenadas corregidas en 2D

### 3. **Extracción Mejorada de Metadatos EXIF**

La función `get_exif_data()` ahora retorna 6 valores en lugar de 3:

```python
# Antes:
lat, lon, alt = get_exif_data(image)

# Ahora:
lat, lon, alt, pitch, roll, yaw = get_exif_data(image)
```

Incluye múltiples métodos de extracción para compatibilidad con diferentes formatos de metadatos DJI.

### 4. **CSV de Resumen Ampliado**

El archivo `resumen_calculos.csv` ahora incluye columnas adicionales:
- `pitch_deg`: Ángulo de cabeceo
- `roll_deg`: Ángulo de alabeo  
- `yaw_deg`: Ángulo de guiñada

Esto permite analizar la actitud de cada foto y verificar la calidad de los datos.

### 5. **Transformación de Coordenadas Verificada**

Se mantiene la transformación EPSG:4326 → EPSG:8908 (CR-SIRGAS/CRTM05), con documentación clara:

```python
# EPSG:8908 = CR-SIRGAS / CRTM05 (basado en ITRF2008@2014.59)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:8908", always_xy=True)
```

**Nota sobre el offset de ~20 metros:**
- CR-SIRGAS está vinculado a ITRF2008 (época 2014.59)
- El GPS del drone reporta WGS84 (equivalente a ITRF actual)
- La diferencia puede deberse a la época del datum o movimientos tectónicos
- Se recomienda verificar con puntos de control conocidos

## 📊 Comparación: Script Original vs. Mejorado

| Característica | Original | Mejorado |
|---|---|---|
| Corrección de actitud | ❌ No | ✅ Sí (pitch, roll, yaw) |
| Rotación 3D | ❌ No | ✅ Sí (matrices de Euler) |
| Precisión en fotos inclinadas | ⚠️ Baja | ✅ Alta |
| Metadatos de actitud en CSV | ❌ No | ✅ Sí |
| Extracción EXIF robusta | ⚠️ Básica | ✅ Múltiples métodos |
| Compatibilidad con vista nadir | ✅ Sí | ✅ Sí (optimizado) |

## 🔧 Uso del Script Mejorado

### Requisitos
Los mismos que el script original:
- Python 3.x
- Bibliotecas: `rasterio`, `pyproj`, `exifread`, `rawpy`, `PIL`, `numpy`
- ExifTool instalado en el sistema

### Ejecución

```bash
cd "ruta/a/carpeta/con/archivos/DNG"
python full_georeference_enhanced.py
```

### Salida
El script genera los mismos archivos que antes, más información adicional:

1. **Archivos JPG** convertidos desde DNG
2. **Archivos .points** con GCPs corregidos por actitud
3. **Archivos _georef.tif** georreferenciados
4. **Archivos _GLI.tif y _VARI.tif** con índices de vegetación
5. **resumen_calculos.csv** con datos de actitud incluidos

### Mensajes de Consola

El script ahora muestra información de actitud:

```
Referencia: DJI_0001.jpg
  Altura base: 50.23 m
  Actitud: Pitch=-15.30°, Roll=2.10°, Yaw=87.45°

Procesado: DJI_0002.jpg - Pitch=-14.80°, Roll=1.95°, Yaw=88.12°
```

## ⚠️ Consideraciones Importantes

### Cuando la Corrección de Actitud es Crítica

La corrección de actitud es más importante cuando:
- El drone vuela con la cámara inclinada (no nadir)
- Se requiere alta precisión (< 1 metro)
- Las fotos se toman en modo oblicuo o con gimbal inclinado

### Cuando la Corrección es Menos Crítica

Para fotos con:
- Pitch y Roll < 5° (casi nadir)
- Aplicaciones de baja precisión
- Alturas de vuelo muy bajas (< 10 metros)

El script automáticamente usa cálculo simple si `|pitch| < 0.5°` y `|roll| < 0.5°`.

## 🐛 Solución de Problemas

### Si los ángulos de actitud son todos 0°

Posibles causas:
1. Los metadatos XMP no se copiaron correctamente
2. El formato DJI es diferente al esperado
3. ExifTool necesita actualización

**Solución:** Verificar que ExifTool copie metadatos XMP:
```python
# Línea 101 del script incluye "-xmp:all"
[exiftool_path, "-overwrite_original", "-TagsFromFile", abs_dng_path, 
 "-gps:all", "-exif:all", "-xmp:all", abs_jpg_path]
```

### Si el offset de 20m persiste

1. Verificar que se está usando EPSG:8908 (no EPSG:5367)
2. Considerar aplicar transformación de datum con parámetros específicos
3. Validar con puntos de control terrestres conocidos
4. Revisar si hay actualizaciones de pyproj/PROJ

## 📚 Referencias Técnicas

- **EPSG:8908**: CR-SIRGAS / CRTM05 (Costa Rica)
- **Datum**: CR-SIRGAS vinculado a ITRF2008 época 2014.59
- **Elipsoide**: GRS80 (prácticamente idéntico a WGS84)
- **Rotaciones de Euler**: Orden ZYX (Yaw-Pitch-Roll)

## 🎓 Próximos Pasos Recomendados

1. **Probar el script** con un conjunto de fotos DJI Mini 3 Pro
2. **Verificar la extracción** de ángulos de actitud en el CSV
3. **Comparar resultados** con el script original
4. **Validar precisión** con puntos de control conocidos
5. **Ajustar parámetros** si es necesario según los resultados
