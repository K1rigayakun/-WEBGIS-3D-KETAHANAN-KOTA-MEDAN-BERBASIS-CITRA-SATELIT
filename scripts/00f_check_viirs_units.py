import requests, zipfile, xml.etree.ElementTree as ET

r = requests.get("https://zenodo.org/api/records/17294744/files/annual_lights.night_500m.R/content", timeout=10)
print("=== annual_lights.night_500m.R ===")
print(r.text[:1500])

z = requests.get("https://zenodo.org/api/records/17294744", timeout=10).json()
print("\n=== Zenodo Description ===")
print(z.get("metadata", {}).get("description", ""))
