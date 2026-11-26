import json
import os
import time
import requests

os.makedirs(r"M:\Kuliah\Semester 5\SIG\Project Akhir\data\raw_osm", exist_ok=True)
cache_path = r"M:\Kuliah\Semester 5\SIG\Project Akhir\data\raw_osm\nominatim_waypoints.json"

queries = {
    # Police stations
    "pol_polrestabes": "Polrestabes Medan, Jalan H.M. Said, Medan",
    "pol_medan_baru": "Polsek Medan Baru, Jalan Nibung Utama, Medan",
    "pol_medan_kota": "Polsek Medan Kota, Teladan Barat, Medan",
    "pol_medan_barat": "Polsek Medan Barat, Jalan Budi Pembangunan, Medan",
    "pol_medan_timur": "Polsek Medan Timur, Jalan Jawa, Medan",
    "pol_medan_area": "Polsek Medan Area, Medan",
    "pol_medan_labuhan": "Polsek Medan Labuhan, Medan",
    "pol_belawan": "Polsek Belawan, Medan",
    "pol_percut": "Polsek Percut Sei Tuan, Jalan Letda Sujono, Deli Serdang",
    "pol_pancur_batu": "Polsek Pancur Batu, Jalan Jamin Ginting",
    "pol_sunggal": "Jalan TB Simatupang, Sunggal, Medan",
    "pol_helvetia": "Jalan Matahari Raya, Helvetia Tengah, Medan",
    "pol_johor": "Jalan Karya Jaya, Medan Johor, Medan",
    "pol_delitua": "Jalan Besar Delitua, Deli Serdang",
    "pol_patumbak": "Jalan Pertahanan, Patumbak, Deli Serdang",

    # Corridor endpoints (real streets from Polrestabes Medan crime mapping release)
    "gatot_east": "Bundaran SIB, Jalan Gatot Subroto, Medan",
    "gatot_mid": "Plaza Medan Fair, Jalan Gatot Subroto, Medan",
    "gatot_west": "Simpang Manhattan, Jalan Gatot Subroto, Medan",
    "sriwijaya_n": "Jalan Sriwijaya, Petisah Hulu, Medan Baru",
    "sriwijaya_s": "Jalan Abdullah Lubis, Medan Baru",
    "sei_serayu_w": "Jalan Sei Serayu, Tanjung Rejo, Medan Sunggal",
    "sei_serayu_e": "Jalan Darussalam, Medan Baru",
    "gajah_mada_n": "Jalan Gajah Mada, Petisah Tengah, Medan Petisah",
    "gajah_mada_s": "Jalan Pattimura, Medan Baru",
    "sparman_n": "Jalan S. Parman, Petisah Hulu, Medan",
    "sparman_s": "Bundaran Sudirman, Jalan S. Parman, Medan",
    "jamin_n": "Jalan Jamin Ginting, Padang Bulan, Medan Baru",
    "jamin_s": "Simpang Pos, Jalan Jamin Ginting, Medan",
    "mansyur_e": "Pintu 1 USU, Jalan Dr. Mansyur, Medan",
    "mansyur_w": "Jalan Dr. Mansyur, Padang Bulan Selayang I, Medan",
    "iskandar_n": "Jalan Iskandar Muda, Medan Petisah",
    "iskandar_s": "Jalan Iskandar Muda, Babura, Medan Baru",
    "sudirman_n": "Taman Beringin, Jalan Jenderal Sudirman, Medan",
    "sudirman_s": "Jalan Jenderal Sudirman, Madras Hulu, Medan Polonia",
    "ringroad_n": "Jalan Gagak Hitam, Sunggal, Medan",
    "ringroad_s": "Simpang Pemda, Jalan Ngumban Surbakti, Medan",
    "yossudarso_s": "Jalan Yos Sudarso, Glugur Kota, Medan Barat",
    "yossudarso_n": "Jalan Yos Sudarso, Pulo Brayan Kota, Medan Barat",
    "sutrisno_w": "Jalan Sutrisno, Medan Area",
    "sutrisno_e": "Jalan A.R. Hakim, Medan Area",
    "perintis_w": "Jalan Perintis Kemerdekaan, Medan Timur",
    "perintis_e": "Jalan Perintis Kemerdekaan, Medan Perjuangan",
    "hmyamin_w": "Jalan Prof. H.M. Yamin, Medan Timur",
    "hmyamin_e": "Jalan Prof. H.M. Yamin, Sidodadi, Medan Timur",
    "nasution_w": "Asrama Haji, Jalan A.H. Nasution, Medan Johor",
    "nasution_e": "Simpang Tritura, Jalan A.H. Nasution, Medan Amplas",
}

results = {}
if os.path.exists(cache_path):
    results = json.load(open(cache_path, encoding="utf-8"))

for key, q in queries.items():
    if key in results and results[key]:
        continue
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 1, "viewbox": "98.55,3.82,98.78,3.45", "bounded": 1},
            headers={"User-Agent": "MedanDarkZoneSIG/1.0 (student project)"},
            timeout=10,
        )
        data = r.json()
        if not data:
            r2 = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 1},
                headers={"User-Agent": "MedanDarkZoneSIG/1.0 (student project)"},
                timeout=10,
            )
            data = r2.json()
        if data:
            results[key] = {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"]), "display_name": data[0]["display_name"]}
        else:
            results[key] = None
        print(key, "->", results[key]["lat"] if results[key] else "MISS", results[key]["lon"] if results[key] else "")
    except Exception as e:
        print(key, "ERR", e)
        results[key] = None
    time.sleep(0.35)

with open(cache_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("Saved", len(results), "entries to", cache_path)
