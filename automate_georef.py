import os
# Unset PROJ_LIB to avoid conflicts with other installations (like PostgreSQL/PostGIS)
if 'PROJ_LIB' in os.environ:
    del os.environ['PROJ_LIB']

import glob
import csv
import rasterio
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps
from rasterio.warp import calculate_default_transform, reproject, Resampling

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
                
                # Format: mapX, mapY, pixelX, pixelY, enable
                # Note: pixelX is column (x), pixelY is row (y)
                # rasterio GCP(row, col, x, y, z)
                # row = pixelY, col = pixelX
                # x = mapX, y = mapY
                
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

from rasterio.vrt import WarpedVRT

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

def main():
    # Find all .jpg files that have a corresponding .points file
    jpg_files = glob.glob("*.jpg")
    
    for jpg_path in jpg_files:
        points_path = os.path.splitext(jpg_path)[0] + ".points"
        if os.path.exists(points_path):
            print(f"Processing {jpg_path}...")
            georeference_image(jpg_path, points_path)
        else:
            # Skip files without points (like generated thumbnails or unrelated jpgs)
            pass

if __name__ == "__main__":
    main()
