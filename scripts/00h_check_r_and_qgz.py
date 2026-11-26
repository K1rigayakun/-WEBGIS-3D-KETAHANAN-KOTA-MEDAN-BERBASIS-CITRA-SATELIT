import requests, zipfile, xml.etree.ElementTree as ET

r = requests.get("https://zenodo.org/api/records/17294744/files/annual_lights.night_500m.R/content", timeout=10)
print("=== annual_lights.night_500m.R (lines 30-120) ===")
print("\n".join(r.text.splitlines()[30:120]))

qgz_path = r"M:\Kuliah\Semester 5\SIG\Pertemuan 11\Persebaran Mall di kota medan.qgz"
with zipfile.ZipFile(qgz_path) as zf:
    qgs_name = [n for n in zf.namelist() if n.endswith(".qgs")][0]
    root = ET.fromstring(zf.read(qgs_name))
    labels = [el.attrib.get("labelText", "") for el in root.findall(".//LayoutItem") if el.attrib.get("labelText")]
    print("\nQGS Layout labels:", labels)
