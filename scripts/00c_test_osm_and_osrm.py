import requests

# Test OSRM real road routing in Medan (Polrestabes Medan Jl HM Said -> Jl Gatot Subroto -> Jl Sriwijaya -> Polsek Medan Baru)
osrm_url = "https://router.project-osrm.org/route/v1/driving/98.6852,3.5990;98.6458,3.5912;98.6619,3.5802;98.6604,3.5750?overview=full&geometries=geojson"
try:
    r = requests.get(osrm_url, headers={"User-Agent": "MedanSIG/1.0"}, timeout=10)
    print("OSRM:", r.status_code, len(r.json()["routes"][0]["geometry"]["coordinates"]) if r.status_code == 200 else r.text[:100])
except Exception as e:
    print("OSRM ERR:", e)

# Test OSM Nominatim search for Police Stations in Medan
nom_url = "https://nominatim.openstreetmap.org/search"
for q in ["Polrestabes Medan", "Polsek Medan Baru", "Polsek Medan Petisah", "Polsek Medan Sunggal", "Polsek Medan Kota", "Polsek Medan Barat", "Polsek Medan Timur", "Polsek Medan Area", "Polsek Medan Helvetia", "Polsek Delitua", "Polsek Medan Labuhan"]:
    try:
        r = requests.get(nom_url, params={"q": q + ", Medan, Indonesia", "format": "json", "limit": 1}, headers={"User-Agent": "MedanSIG/1.0"}, timeout=10)
        res = r.json()
        print("Nominatim:", q, "->", (res[0]["lat"], res[0]["lon"], res[0]["display_name"][:60]) if res else "NOT FOUND")
    except Exception as e:
        print("Nominatim ERR:", q, e)
