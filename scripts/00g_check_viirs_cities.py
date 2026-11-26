from osgeo import gdal
import numpy as np

vsi_url = "/vsicurl/https://zenodo.org/api/records/17294744/files/nightlights.average_viirs.v21_m_500m_s_20240101_20241231_go_epsg4326_v20250904.tif/content"
ds = gdal.Open(vsi_url)
gt = ds.GetGeoTransform()
band = ds.GetRasterBand(1)

for name, lon, lat in [("Medan Center", 98.678, 3.589), ("Jakarta Center", 106.827, -6.175), ("Singapore", 103.851, 1.289)]:
    xoff = int((lon - gt[0]) / gt[1]) - 5
    yoff = int((lat - gt[3]) / gt[5]) - 5
    arr = band.ReadAsArray(xoff, yoff, 11, 11)
    print(name, "raw min/max/mean:", arr.min(), arr.max(), round(float(arr.mean()), 2))
