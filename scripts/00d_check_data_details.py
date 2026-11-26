import csv
import os
import requests
from osgeo import gdal

print("=== 1. Inspect Zenodo VIIRS 2024 COG Pixel Values over Medan ===")
vsi_url = "/vsicurl/https://zenodo.org/api/records/17294744/files/nightlights.average_viirs.v21_m_500m_s_20240101_20241231_go_epsg4326_v20250904.tif/content"
ds = gdal.Open(vsi_url)
if ds:
    band = ds.GetRasterBand(1)
    print("Band dtype:", gdal.GetDataTypeName(band.DataType), "NoData:", band.GetNoDataValue(), "Scale/Offset:", band.GetScale(), band.GetOffset())
    print("Metadata:", ds.GetMetadata())
    # Clip small test array around Medan [98.58, 3.47, 98.76, 3.81]
    gt = ds.GetGeoTransform()
    xoff = int((98.58 - gt[0]) / gt[1])
    yoff = int((3.81 - gt[3]) / gt[5])
    xsize = int((98.76 - 98.58) / gt[1]) + 1
    ysize = int((3.47 - 3.81) / gt[5]) + 1
    arr = band.ReadAsArray(xoff, yoff, xsize, ysize)
    print("Medan test array shape:", arr.shape, "min:", arr.min(), "max:", arr.max(), "mean:", float(arr.mean()))

print("\n=== 2. Inspect Pertemuan 11/Data_penduduk.csv ===")
csv_path = r"M:\Kuliah\Semester 5\SIG\Pertemuan 11\Data_penduduk.csv"
if os.path.exists(csv_path):
    with open(csv_path, encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f):
            if idx < 10:
                print(" ", line.strip())

print("\n=== 3. Geocode additional Medan Police Stations ===")
queries = [
    ("Polsek Sunggal", "Polsek Sunggal, Medan"),
    ("Polsek Medan Helvetia", "Polsek Helvetia, Medan"),
    ("Polsek Delitua", "Polsek Delitua, Sumatera Utara"),
    ("Polsek Medan Tuntungan", "Polsek Medan Tuntungan, Medan"),
    ("Polsek Percut Sei Tuan", "Polsek Percut Sei Tuan, Sumatera Utara"),
    ("Polsek Patumbak", "Polsek Patumbak, Sumatera Utara"),
    ("Polsek Medan Belawan", "Polsek Belawan, Medan"),
    ("Polda Sumatera Utara", "Polda Sumatera Utara, Medan"),
]
for label, q in queries:
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "json", "limit": 1}, headers={"User-Agent": "MedanSIG/1.0"}, timeout=8).json()
        print(" ", label, "->", (r[0]["lat"], r[0]["lon"], r[0]["display_name"][:55]) if r else "NONE")
    except Exception as e:
        print(" ", label, "ERR", e)
