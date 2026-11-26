from osgeo import gdal
vsi_url = "/vsicurl/https://zenodo.org/api/records/17294744/files/nightlights.average_viirs.v21_m_500m_s_20240101_20241231_go_epsg4326_v20250904.tif/content"
ds = gdal.Open(vsi_url)
gt = ds.GetGeoTransform()
band = ds.GetRasterBand(1)
xoff = int((103.60 - gt[0]) / gt[1])
yoff = int((1.47 - gt[3]) / gt[5])
xsize = int((104.05 - 103.60) / gt[1])
ysize = int((1.20 - 1.47) / gt[5])
arr = band.ReadAsArray(xoff, yoff, xsize, ysize)
print("Full Singapore raw min/max/p95/mean:", int(arr.min()), int(arr.max()), float(arr.mean()))
