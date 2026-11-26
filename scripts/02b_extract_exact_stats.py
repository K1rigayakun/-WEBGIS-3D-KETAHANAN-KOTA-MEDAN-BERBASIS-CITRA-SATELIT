import json
from pathlib import Path
import numpy as np

DATA = Path(r"M:\Kuliah\Semester 5\SIG\Project Akhir\data")

kec = json.loads((DATA / "batas_kecamatan_medan.geojson").read_text(encoding="utf-8"))["features"]
hex_f = json.loads((DATA / "hex_viirs_medan_500m.geojson").read_text(encoding="utf-8"))["features"]
bld = json.loads((DATA / "bangunan_fokus_3d.geojson").read_text(encoding="utf-8"))["features"]
kor = json.loads((DATA / "koridor_rawan_begal.geojson").read_text(encoding="utf-8"))["features"]
pju = json.loads((DATA / "solusi_pju_cctv.geojson").read_text(encoding="utf-8"))["features"]
pat = json.loads((DATA / "solusi_rute_patroli.geojson").read_text(encoding="utf-8"))["features"]
pol = json.loads((DATA / "polisi_eksisting.geojson").read_text(encoding="utf-8"))["features"]

print("=== KECAMATAN STATS ===")
for f in sorted(kec, key=lambda x: x["properties"]["avg_risk_score"], reverse=True):
    p = f["properties"]
    print(f"{p['nama_kec']:20s} | Luas={p['luas_km2']:5.2f} | Pop25={p['penduduk_2025']:6d} | VIIRS={p['viirs_mean']:5.2f} | Hex={p['hex_total']:3d} | Kritis={p['hex_kritis']:3d} | Risk={p['avg_risk_score']:4.1f} | PJU={p['jumlah_pju_solusi']}")

print("\n=== HEXAGON CLASSES ===")
from collections import Counter
print(Counter(f["properties"]["kelas_risiko"] for f in hex_f))
print("Hex VIIRS mean/min/max:", round(float(np.mean([f["properties"]["viirs_mean"] for f in hex_f])), 2), min(f["properties"]["viirs_min"] for f in hex_f), max(f["properties"]["viirs_max"] for f in hex_f))

print("\n=== BUILDINGS STATS ===")
print("Total:", len(bld))
print("By Kecamatan:", Counter(f["properties"]["kecamatan"] for f in bld))
print("By Status:", Counter(f["properties"]["status_rawan"] for f in bld))
print("By HeightSrc:", Counter(f["properties"]["height_src"] for f in bld))
print("High-risk protected by PJU:", sum(1 for f in bld if f["properties"]["status_rawan"] == "Tinggi" and f["properties"]["terlindungi_solusi"] == 1))
print("All protected by PJU:", sum(1 for f in bld if f["properties"]["terlindungi_solusi"] == 1))

print("\n=== CORRIDORS ===")
for f in kor:
    p = f["properties"]
    print(f"{p['nama_jalan']:28s} | {p['kecamatan']:28s} | {p['panjang_km']:5.2f} km | VIIRS_min={p['viirs_min']} mean={p['viirs_mean']} | {p['tingkat_bahaya']}")

print("\n=== PJU SOLUTIONS BY TYPE & PRIORITY ===")
print(Counter(f["properties"]["jenis_solusi"] for f in pju))
print(Counter(f["properties"]["prioritas"] for f in pju))

print("\n=== PATROL ROUTES ===")
for f in pat:
    p = f["properties"]
    print(f"{p['nama_rute']} | {p['panjang_km']} km | {p['jam_patroli']}")

print("\n=== POLICE STATIONS ===")
print("Total police:", len(pol))
