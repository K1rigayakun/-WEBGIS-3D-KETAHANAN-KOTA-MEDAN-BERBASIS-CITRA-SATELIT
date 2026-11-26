import requests

mirrors = [
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
q = '[out:json][timeout:15];way["highway"~"trunk|primary|secondary"](3.48,98.59,3.80,98.75);out geom;'
for u in mirrors:
    try:
        r = requests.post(u, data={"data": q}, headers={"User-Agent": "MedanSIG/1.0"}, timeout=15)
        print(u, r.status_code, len(r.json().get("elements", [])) if r.status_code == 200 else r.text[:100])
    except Exception as e:
        print(u, "ERR", type(e).__name__, str(e)[:80])
