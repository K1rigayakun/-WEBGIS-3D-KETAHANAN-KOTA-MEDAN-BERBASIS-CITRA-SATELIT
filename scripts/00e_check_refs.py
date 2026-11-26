import requests, zipfile, xml.etree.ElementTree as ET

# 1. Zenodo metadata for VIIRS scaling
z = requests.get("https://zenodo.org/api/records/17294744", timeout=10).json()
print("Zenodo Title:", z.get("metadata", {}).get("title"))
desc = z.get("metadata", {}).get("description", "")
print("Zenodo Desc snippet:", desc[:700])

# 2. Check existing Pertemuan 11 .qgz layout/layers
qgz_path = r"M:\Kuliah\Semester 5\SIG\Pertemuan 11\Persebaran Mall di kota medan.qgz"
with zipfile.ZipFile(qgz_path) as zf:
    qgs_name = [n for n in zf.namelist() if n.endswith(".qgs")][0]
    root = ET.fromstring(zf.read(qgs_name))
    print("\nQGS layers:", [e.text for e in root.findall(".//maplayer/layername")])
    print("QGS layouts:", [l.attrib.get("name") for l in root.findall(".//Layouts/Layout")])
