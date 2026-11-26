import json
import os
from osgeo import gdal, ogr

print("=== 1. Check Medan Kecamatan GeoJSON ===")
medan_path = r"M:\Kuliah\Semester 5\SIG\Pertemuan 12\WADM_KC_Sumatera_Utara_Kota_Medan.geojson"
ds = ogr.Open(medan_path)
lyr = ds.GetLayer()
print("Medan features:", lyr.GetFeatureCount(), "Extent:", lyr.GetExtent(), "SRS:", lyr.GetSpatialRef().ExportToProj4())

print("=== 2. Check BIG 25K Shapefiles ===")
for name in ["JALAN_LN_25K.shp", "SUNGAI_LN_25K.shp", "PEMUKIMAN_AR_25K.shp"]:
    p = os.path.join(r"M:\Kuliah\Semester 5\SIG\Dari Download\DATA VEKTOR", name)
    vds = ogr.Open(p)
    if vds:
        vlyr = vds.GetLayer()
        fields = [vlyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(vlyr.GetLayerDefn().GetFieldCount())]
        print(name, "Count:", vlyr.GetFeatureCount(), "Extent:", vlyr.GetExtent(), "Fields:", fields[:8])
        for i in range(min(3, vlyr.GetFeatureCount())):
            f = vlyr.GetNextFeature()
            print("  sample:", {k: f.GetField(k) for k in fields[:5]})

print("=== 3. Check DEM SRTM 30M SUMUT ===")
dem_path = r"M:\Kuliah\Semester 5\SIG\Dari Download\DEM SRTM 30M SUMUT.tif"
rds = gdal.Open(dem_path)
if rds:
    gt = rds.GetGeoTransform()
    print("DEM:", rds.RasterXSize, rds.RasterYSize, "GT:", gt, "Proj:", rds.GetProjection()[:60])
