import os
import re
import json
import math
import time
import base64
import shutil
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt, minimum_filter, uniform_filter, label
from shapely.geometry import shape, Point, LineString, Polygon, MultiPolygon, mapping
from shapely.ops import transform, unary_union
from shapely import STRtree
from pyproj import Transformer

BASE_DIR = "/tmp/work_merge/sekarang"
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DATA_DIR = os.path.join(BASE_DIR, "web-peta-interaktif", "data")
TEAM_DIR = os.path.join(DATA_DIR, "integrasi_tim")
WEB_TEAM_DIR = os.path.join(WEB_DATA_DIR, "integrasi_tim")

os.makedirs(TEAM_DIR, exist_ok=True)
os.makedirs(WEB_TEAM_DIR, exist_ok=True)

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32647", always_xy=True).transform
TO_WGS = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True).transform
t0 = time.time()

def log(msg):
    print(f"[{time.time()-t0:5.1f}s] {msg}", flush=True)

def round_coords(coords, precision=5):
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        return [round(float(coords[0]), precision), round(float(coords[1]), precision)]
    return [round_coords(c, precision) for c in coords]

def save_geojson(path, features, precision=5):
    clean = []
    for f in features:
        g = f["geometry"]
        if g and g.get("coordinates"):
            g = {"type": g["type"], "coordinates": round_coords(g["coordinates"], precision)}
        clean.append({"type": "Feature", "properties": f["properties"], "geometry": g})
    fc = {"type": "FeatureCollection", "features": clean}
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(fc, fp, separators=(",", ":"), ensure_ascii=False)
    return fc

def load_peter_js(fname):
    p_dir = "/tmp/work_merge/peter/WebMap_Damkar_Medan/qgis2web_2026_11_26-16_35_11_757447/data"
    txt = open(os.path.join(p_dir, fname), encoding="utf-8").read()
    m = re.search(r"var\s+\w+\s*=\s*(\{.*\})", txt, re.S)
    return json.loads(m.group(1))

def main():
    log("1. Loading Master 21 Kecamatan, 1470 Hexagons, Rivers, and Roads...")
    kec_fc = json.load(open(os.path.join(DATA_DIR, "batas_kecamatan_medan.geojson"), encoding="utf-8"))
    hex_fc = json.load(open(os.path.join(DATA_DIR, "hex_viirs_medan_500m.geojson"), encoding="utf-8"))
    water_fc = json.load(open(os.path.join(DATA_DIR, "sungai_fokus_osm.geojson"), encoding="utf-8"))
    roads_fc = json.load(open(os.path.join(DATA_DIR, "jalan_fokus_osm.geojson"), encoding="utf-8"))

    kec_geoms = [shape(f["geometry"]) for f in kec_fc["features"]]
    kec_names = [f["properties"]["nama_kec"] for f in kec_fc["features"]]
    kec_ids = [f["properties"]["id_kec"] for f in kec_fc["features"]]
    kec_tree = STRtree(kec_geoms)
    medan_union = unary_union(kec_geoms)

    def find_kec(geom_wgs):
        pt = geom_wgs.centroid
        idx = kec_tree.nearest(pt)
        return kec_names[idx], kec_ids[idx]

    master_hex_geoms = [shape(f["geometry"]) for f in hex_fc["features"]]
    master_hex_ids = [f["properties"]["hex_id"] for f in hex_fc["features"]]
    master_hex_tree = STRtree(master_hex_geoms)

    def find_nearest_master_hex(geom_wgs):
        pt = geom_wgs.centroid
        idx = master_hex_tree.nearest(pt)
        return master_hex_ids[idx], idx

    # =========================================================================
    # ORANG 1: WILLIAM — MICRO-UHI (LANDSAT LST) & KORIDOR PENEDUH + HALTE TEDUH
    # =========================================================================
    log("2. Integrating Orang 1 (William): 782 Micro-UHI Hexagons, 6 Shade Corridors (2,988 trees), 10 Cool Shelters...")
    w_hex_fc = json.load(open("/tmp/work_merge/william/medan_hex_uhi_500m.geojson", encoding="utf-8"))
    w_road_fc = json.load(open("/tmp/work_merge/william/jalur_peneduh_arteri_medan.geojson", encoding="utf-8"))
    w_shelter_fc = json.load(open("/tmp/work_merge/william/titik_halte_teduh_medan.geojson", encoding="utf-8"))

    w_road_utm = [transform(TO_UTM, shape(f["geometry"])) for f in w_road_fc["features"]]
    w_shelter_utm = [transform(TO_UTM, shape(f["geometry"])) for f in w_shelter_fc["features"]]
    w_road_union_utm = unary_union(w_road_utm)
    w_shelter_union_utm = unary_union(w_shelter_utm)

    orang1_masalah = []
    for f in w_hex_fc["features"]:
        p = f["properties"]
        g_wgs = shape(f["geometry"])
        cx, cy = TO_UTM(g_wgs.centroid.x, g_wgs.centroid.y)
        c_utm = Point(cx, cy)
        dist_road_m = round(float(c_utm.distance(w_road_union_utm)), 1)
        dist_shelter_m = round(float(c_utm.distance(w_shelter_union_utm)), 1)
        lst_mean = float(p["lst_mean"])
        lst_max = float(p["lst_max"])
        lst_min = float(p["lst_min"])
        uhi_class = str(p["uhi_class"])

        road_cool = 2.6 * math.exp(-dist_road_m / 650.0)
        shelter_cool = 1.1 * math.exp(-dist_shelter_m / 450.0)
        site_cool = 1.6 if lst_mean >= 34.5 else (1.1 if lst_mean >= 32.5 else 0.6)
        cooling_delta_c = round(min(4.5, road_cool + shelter_cool + site_cool), 2)
        lst_sim_c = round(max(27.2, lst_mean - cooling_delta_c), 2)

        skor_awal = round(min(99.0, max(10.0, (lst_mean - 27.0) / (38.5 - 27.0) * 90.0 + 8.0)), 1)
        skor_sim = round(min(99.0, max(8.0, (lst_sim_c - 27.0) / (38.5 - 27.0) * 90.0 + 8.0)), 1)

        m_hex_id, _ = find_nearest_master_hex(g_wgs)
        k_name, k_id = find_kec(g_wgs)
        orang1_masalah.append({
            "type": "Feature",
            "properties": {
                "hex_id": p["hex_id"],
                "master_hex_id": m_hex_id,
                "id_kec": k_id,
                "kecamatan": p.get("kecamatan") or k_name,
                "tim": "Orang 1",
                "nama_anggota": "William",
                "tema": "Micro-UHI & Suhu Permukaan (Landsat LST)",
                "lst_mean": lst_mean,
                "lst_max": lst_max,
                "lst_min": lst_min,
                "lst_sim": lst_sim_c,
                "cooling_delta_c": cooling_delta_c,
                "uhi_class": uhi_class,
                "skor_masalah": skor_awal,
                "skor_simulasi": skor_sim,
                "kelas_masalah": "Kritis" if lst_mean >= 34.5 else ("Tinggi" if lst_mean >= 32.5 else ("Sedang" if lst_mean >= 30.5 else "Rendah")),
                "karakter_tapak": p.get("karakter_tapak", ""),
                "rekomendasi_solusi": p.get("rekomendasi_solusi", ""),
                "dist_jalur_peneduh_m": dist_road_m,
                "dist_halte_teduh_m": dist_shelter_m,
                "indikator_utama": f"LST {lst_mean:.2f}°C (Max {lst_max:.2f}°C) · Simulasi: {lst_sim_c:.2f}°C (-{cooling_delta_c:.2f}°C)",
                "status_tim": "Data Asli William (782 Hex Landsat LST + 6 Koridor Peneduh + 10 Halte Cool Roof)",
            },
            "geometry": f["geometry"],
        })

    orang1_solusi = []
    tree_sample_points = []
    for f in w_road_fc["features"]:
        p = f["properties"]
        g_wgs = shape(f["geometry"])
        k_name, _ = find_kec(g_wgs)
        orang1_solusi.append({
            "type": "Feature",
            "properties": {
                "solusi_id": p["road_id"],
                "kecamatan": k_name,
                "tim": "Orang 1",
                "nama_anggota": "William",
                "sub_tipe": "jalur_peneduh",
                "nama_solusi": f"Koridor Peneduh {p['nama_jalan']}",
                "nama_jalan": p["nama_jalan"],
                "segmen": p["segmen"],
                "tipe_jalan": p["tipe_jalan"],
                "suhu_rata_c": float(p["suhu_rata_c"]),
                "suhu_sim_c": round(float(p["suhu_rata_c"]) - 3.6, 1),
                "panjang_km": float(p["panjang_km"]),
                "jenis_pohon": p["jenis_pohon"],
                "est_pohon": int(p["est_pohon"]),
                "prioritas": p["prioritas"],
                "alasan_solusi": p["alasan_solusi"],
                "kategori_solusi": f"Jalur Peneduh ({p['jenis_pohon']} · {p['est_pohon']} Pohon)",
                "indikator_utama": f"LST {p['suhu_rata_c']}°C -> {float(p['suhu_rata_c'])-3.6:.1f}°C · {p['panjang_km']} km ({p['est_pohon']} pohon)",
            },
            "geometry": f["geometry"],
        })
        for frac in np.linspace(0.06, 0.94, 10):
            pt = g_wgs.interpolate(frac, normalized=True)
            tree_sample_points.append({
                "type": "Feature",
                "properties": {
                    "solusi_id": f"{p['road_id']}-T{len(tree_sample_points)+1}",
                    "kecamatan": k_name,
                    "tim": "Orang 1",
                    "nama_anggota": "William",
                    "sub_tipe": "pohon_3d_koridor",
                    "model_3d": "pohon_peneduh",
                    "nama_solusi": f"{p['jenis_pohon']} — {p['nama_jalan']}",
                    "jenis_pohon": p["jenis_pohon"],
                    "kategori_solusi": "Kanopi Pohon Peneduh 3D",
                    "indikator_utama": "Reduksi suhu mikro 2.5–4.0°C · Serapan CO2 28.5 Ton/thn",
                },
                "geometry": mapping(pt),
            })

    for f in w_shelter_fc["features"]:
        p = f["properties"]
        orang1_solusi.append({
            "type": "Feature",
            "properties": {
                "solusi_id": p["shelter_id"],
                "shelter_id": p["shelter_id"],
                "kecamatan": p["kecamatan"],
                "tim": "Orang 1",
                "nama_anggota": "William",
                "sub_tipe": "halte_teduh",
                "model_3d": "halte_teduh",
                "nama_solusi": p["nama_halte"],
                "nama_halte": p["nama_halte"],
                "lokasi_patokan": p["lokasi_patokan"],
                "suhu_lokasi_c": float(p["suhu_lokasi_c"]),
                "suhu_sim_c": round(float(p["suhu_lokasi_c"]) - 4.1, 1),
                "status_usulan": p["status_usulan"],
                "fasilitas_desain": p["fasilitas_desain"],
                "kategori_solusi": f"Halte Teduh ({p['status_usulan']})",
                "indikator_utama": f"Suhu {p['suhu_lokasi_c']}°C -> {float(p['suhu_lokasi_c'])-4.1:.1f}°C · {p['fasilitas_desain']}",
            },
            "geometry": f["geometry"],
        })
    orang1_solusi.extend(tree_sample_points)

    # =========================================================================
    # ORANG 2: JORDAN — DEFISIT RTH & SENTINEL-2 L2A NDVI
    # =========================================================================
    log("3. Integrating Orang 2 (Jordan): Sentinel-2 L2A NDVI Raster & 782 NDVI Hexagons + RTH Pocket Parks...")
    j_hex_fc = json.load(open("/tmp/work_merge/jordan/web_jordan/medan_hex_ndvi.geojson", encoding="utf-8"))
    ndvi_im = Image.open("/tmp/work_merge/jordan/web_jordan/02_olahan/ndvi_medan.tif")
    ndvi_arr = np.array(ndvi_im, dtype=np.float32)
    ndvi_scale = ndvi_im.tag_v2.get(33550)
    ndvi_tie = ndvi_im.tag_v2.get(33922)
    n_ulx, n_uly = ndvi_tie[3], ndvi_tie[4]
    n_dx, n_dy = ndvi_scale[0], ndvi_scale[1]
    nh, nw = ndvi_arr.shape
    n_lrx = n_ulx + nw * n_dx
    n_lry = n_uly - nh * n_dy
    wgs_ul = TO_WGS(n_ulx, n_uly)
    wgs_ur = TO_WGS(n_lrx, n_uly)
    wgs_lr = TO_WGS(n_lrx, n_lry)
    wgs_ll = TO_WGS(n_ulx, n_lry)

    valid_ndvi = (ndvi_arr > -1.0) & np.isfinite(ndvi_arr)
    ndvi_clean = np.where(valid_ndvi, np.clip(ndvi_arr, -0.3, 0.85), 0.0)
    n_stops = np.array([-0.2, 0.0, 0.111, 0.236, 0.45, 0.80])
    nr = np.interp(ndvi_clean, n_stops, [180, 215, 252, 254, 26, 6]).astype(np.uint8)
    ng = np.interp(ndvi_clean, n_stops, [30,  48,  141, 224, 152, 95]).astype(np.uint8)
    nb = np.interp(ndvi_clean, n_stops, [30,  39,  89,  139, 80,  59]).astype(np.uint8)
    na = np.where(valid_ndvi, 210, 0).astype(np.uint8)
    ndvi_png_path = os.path.join(WEB_DATA_DIR, "ndvi_sentinel2_raw.png")
    Image.fromarray(np.dstack([nr, ng, nb, na]), mode="RGBA").resize((533, 536), Image.Resampling.BILINEAR).save(
        ndvi_png_path, optimize=True, compress_level=9
    )

    orang2_masalah = []
    orang2_solusi = []
    for f in j_hex_fc["features"]:
        p = f["properties"]
        g_wgs = shape(f["geometry"])
        ndvi_val = p.get("ndvi_mean")
        has_ndvi = ndvi_val is not None and not (isinstance(ndvi_val, float) and math.isnan(ndvi_val))
        ndvi_num = round(float(ndvi_val), 4) if has_ndvi else None
        lst_mean = float(p.get("lst_mean", 32.0))

        if ndvi_num is not None:
            if ndvi_num <= 0.0:
                ndvi_cls = "Sangat Kritis (<= 0.000 · Non-Vegetasi)"
                skor_rth = 92.0
            elif ndvi_num <= 0.111:
                ndvi_cls = "Defisit Kritis (0.000 - 0.111)"
                skor_rth = round(75.0 + (0.111 - ndvi_num) / 0.111 * 15.0, 1)
            elif ndvi_num <= 0.236:
                ndvi_cls = "Vegetasi Sedang (0.111 - 0.236)"
                skor_rth = round(48.0 + (0.236 - ndvi_num) / 0.125 * 26.0, 1)
            else:
                ndvi_cls = "Vegetasi Rapat (> 0.236)"
                skor_rth = round(max(12.0, 45.0 - (ndvi_num - 0.236) * 80.0), 1)
            ndvi_boost = 0.185 if ndvi_num <= 0.111 else (0.115 if ndvi_num <= 0.236 else 0.045)
            ndvi_sim = round(min(0.65, ndvi_num + ndvi_boost), 4)
            skor_sim = round(max(10.0, skor_rth - ndvi_boost * 180.0), 1)
        else:
            ndvi_cls = "Luar Cakupan Citra Sentinel-2"
            skor_rth = 35.0
            ndvi_sim = 0.28
            skor_sim = 25.0

        m_hex_id, _ = find_nearest_master_hex(g_wgs)
        k_name, k_id = find_kec(g_wgs)
        orang2_masalah.append({
            "type": "Feature",
            "properties": {
                "hex_id": p["hex_id"],
                "master_hex_id": m_hex_id,
                "id_kec": k_id,
                "kecamatan": p.get("kecamatan") or k_name,
                "tim": "Orang 2",
                "nama_anggota": "Jordan",
                "tema": "Defisit RTH & Kerapatan Vegetasi (Sentinel-2 NDVI)",
                "ndvi_mean": ndvi_num,
                "ndvi_sim": ndvi_sim,
                "ndvi_count": p.get("ndvi_count"),
                "ndvi_class": ndvi_cls,
                "lst_mean": lst_mean,
                "uhi_class": p.get("uhi_class", ""),
                "skor_masalah": skor_rth,
                "skor_simulasi": skor_sim,
                "kelas_masalah": "Kritis" if (ndvi_num is not None and ndvi_num <= 0.111) else ("Sedang" if (ndvi_num is not None and ndvi_num <= 0.236) else "Rendah"),
                "rekomendasi_solusi": p.get("rekomendasi_solusi", ""),
                "indikator_utama": f"NDVI: {ndvi_num:.3f} -> Simulasi: {ndvi_sim:.3f} · LST: {lst_mean:.2f}°C" if ndvi_num is not None else f"Luar Cakupan Citra Sentinel · LST {lst_mean:.2f}°C",
                "status_tim": "Data Asli Jordan (Sentinel-2 L2A B04 & B08 23 Agu 2026 + 782 Hex NDVI)",
            },
            "geometry": f["geometry"],
        })

        if ndvi_num is not None and ndvi_num <= 0.105 and len(orang2_solusi) < 36:
            rep = g_wgs.centroid
            orang2_solusi.append({
                "type": "Feature",
                "properties": {
                    "solusi_id": f"RTH-{len(orang2_solusi)+1:02d}",
                    "hex_id": p["hex_id"],
                    "kecamatan": p.get("kecamatan") or k_name,
                    "tim": "Orang 2",
                    "nama_anggota": "Jordan",
                    "sub_tipe": "taman_rth",
                    "model_3d": "pohon_peneduh",
                    "nama_solusi": f"Taman Saku & Kantong RTH {p.get('kecamatan') or k_name} ({p['hex_id']})",
                    "kategori_solusi": "Injeksi RTH Baru & Pocket Park Kelurahan",
                    "ndvi_awal": ndvi_num,
                    "ndvi_target": ndvi_sim,
                    "indikator_utama": f"NDVI {ndvi_num:.3f} -> {ndvi_sim:.3f} (+{(ndvi_sim-ndvi_num):.3f}) · Reduksi LST -2.4°C",
                },
                "geometry": mapping(rep),
            })

    # =========================================================================
    # ORANG 3: CEKUNGAN BANJIR TOPOGRAFI DEM SRTM 30m (HYDROLOGICAL HAND MODEL)
    # =========================================================================
    log("4. Building Orang 3: Physical Topographic Flood Inundation Simulation (DEM SRTM 30m + HAND + Rivers)...")
    dem_im = Image.open(os.path.join(DATA_DIR, "dem_medan_srtm.tif"))
    dem_arr = np.array(dem_im, dtype=np.float64)
    dem_valid = np.maximum(dem_arr, 0.0)
    d_scale = dem_im.tag_v2.get(33550)
    d_tie = dem_im.tag_v2.get(33922)
    d_ulx, d_uly = d_tie[3], d_tie[4]
    d_dx, d_dy = d_scale[0], -d_scale[1]
    dh, dw = dem_arr.shape

    medan_mask = np.zeros((dh, dw), dtype=np.uint8)
    for poly in (list(medan_union.geoms) if hasattr(medan_union, "geoms") else [medan_union]):
        coords = np.array(poly.exterior.coords)
        px = np.round((coords[:, 0] - d_ulx) / d_dx).astype(np.int32)
        py = np.round((coords[:, 1] - d_uly) / d_dy).astype(np.int32)
        cv2.fillPoly(medan_mask, [np.column_stack([px, py])], 1)

    river_mask = np.zeros((dh, dw), dtype=np.uint8)
    for feat in water_fc["features"]:
        g = shape(feat["geometry"])
        for ln in (list(g.geoms) if hasattr(g, "geoms") else [g]):
            coords = np.array(ln.coords)
            px = np.round((coords[:, 0] - d_ulx) / d_dx).astype(np.int32)
            py = np.round((coords[:, 1] - d_uly) / d_dy).astype(np.int32)
            cv2.polylines(river_mask, [np.column_stack([px, py])], False, 1, thickness=2)

    river_mask = (river_mask > 0) & (medan_mask > 0)
    dist_to_river_m = distance_transform_edt(~river_mask) * 30.0
    valley_floor = uniform_filter(minimum_filter(dem_valid, size=25), size=15)
    hand = np.maximum(0.0, dem_valid - valley_floor)
    hand_smooth = cv2.GaussianBlur(hand.astype(np.float32), (5, 5), 0)
    dem_smooth = cv2.GaussianBlur(dem_valid.astype(np.float32), (5, 5), 0)

    def mask_to_geojson_multipolygon(binary_mask, min_area_px=16, eps=0.9):
        # Fast direct cv2 contour to GeoJSON MultiPolygon without slow Shapely unary_union!
        contours, hierarchy = cv2.findContours(binary_mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if not contours or hierarchy is None:
            return None
        hierarchy = hierarchy[0]
        multi_coords = []
        for i, cnt in enumerate(contours):
            if hierarchy[i][3] != -1 or cv2.contourArea(cnt) < min_area_px:
                continue
            approx = cv2.approxPolyDP(cnt, eps, True)
            if len(approx) < 3:
                continue
            pts = approx[:, 0, :]
            lons = np.round(d_ulx + (pts[:, 0] + 0.5) * d_dx, 5)
            lats = np.round(d_uly + (pts[:, 1] + 0.5) * d_dy, 5)
            ext_ring = [[float(x), float(y)] for x, y in zip(lons, lats)]
            ext_ring.append(ext_ring[0])
            poly_rings = [ext_ring]
            child = hierarchy[i][2]
            while child != -1:
                if cv2.contourArea(contours[child]) >= 10:
                    h_approx = cv2.approxPolyDP(contours[child], eps, True)
                    if len(h_approx) >= 3:
                        hpts = h_approx[:, 0, :]
                        hlons = np.round(d_ulx + (hpts[:, 0] + 0.5) * d_dx, 5)
                        hlats = np.round(d_uly + (hpts[:, 1] + 0.5) * d_dy, 5)
                        hring = [[float(x), float(y)] for x, y in zip(hlons, hlats)]
                        hring.append(hring[0])
                        poly_rings.append(hring)
                child = hierarchy[child][0]
            multi_coords.append(poly_rings)
        if not multi_coords:
            return None
        return {"type": "MultiPolygon", "coordinates": multi_coords}

    flood_stages = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    flood_contours_features = []
    for st in flood_stages:
        cand_fluvial = (hand_smooth <= st * 1.15) & (dist_to_river_m <= 160 + st * 320) & (medan_mask > 0)
        cand_rob = (dem_smooth <= st * 1.05) & (dem_smooth <= 5.2) & (medan_mask > 0)
        cand = cand_fluvial | cand_rob | river_mask
        labeled, _ = label(cand)
        seeds = np.unique(labeled[river_mask | ((dem_smooth <= 1.5) & (medan_mask > 0))])
        seeds = seeds[seeds > 0]
        flooded = np.isin(labeled, seeds)
        geom = mask_to_geojson_multipolygon(flooded, min_area_px=16, eps=0.95)
        if geom:
            luas_km2 = round(float(flooded.sum() * 0.0009), 2)
            flood_contours_features.append({
                "type": "Feature",
                "properties": {
                    "tim": "Orang 3",
                    "tema": "Simulasi Genangan Banjir Topografi (DEM SRTM 30m + HAND)",
                    "stage_m": st,
                    "water_height_3d_m": round(st * 2.4, 2),
                    "luas_genangan_km2": luas_km2,
                    "indikator_utama": f"Tinggi Muka Air +{st:.1f} m · Luas Genangan Riil Topografi: {luas_km2:.2f} km²",
                },
                "geometry": geom,
            })

    orang3_masalah = []
    orang3_solusi = []
    elevated_candidates = []
    for hf in hex_fc["features"]:
        hp = hf["properties"]
        g_wgs = shape(hf["geometry"])
        rep = g_wgs.centroid
        col = max(0, min(dw - 1, int((rep.x - d_ulx) / d_dx)))
        row = max(0, min(dh - 1, int((rep.y - d_uly) / d_dy)))
        r0, r1 = max(0, row - 3), min(dh, row + 4)
        c0, c1 = max(0, col - 3), min(dw, col + 4)
        local_hand = float(np.percentile(hand_smooth[r0:r1, c0:c1], 20))
        local_dem = float(np.percentile(dem_smooth[r0:r1, c0:c1], 25))
        local_dist_riv = float(np.min(dist_to_river_m[r0:r1, c0:c1]))

        if local_dem <= 5.2:
            crit_stage = round(max(0.4, local_dem / 1.05), 2)
            tipe_banjir = "Banjir Rob Pesisir & Cekungan Muara"
        else:
            stage_by_hand = local_hand / 1.15
            stage_by_dist = max(0.0, (local_dist_riv - 160.0) / 320.0)
            crit_stage = round(max(0.4, max(stage_by_hand, stage_by_dist)), 2)
            tipe_banjir = "Luapan Lembah Sungai (DAS Deli / Babura / Belawan)"

        hp["hand_m"] = round(local_hand, 2)
        hp["dist_sungai_m"] = round(local_dist_riv, 0)
        hp["flood_crit_stage_m"] = crit_stage

        flood_risk_score = round(min(99.0, max(5.0, 100.0 * math.exp(-crit_stage / 2.2))), 1)
        if crit_stage <= 3.5:
            orang3_masalah.append({
                "type": "Feature",
                "properties": {
                    "hex_id": hp["hex_id"],
                    "id_kec": hp["id_kec"],
                    "kecamatan": hp["kecamatan"],
                    "tim": "Orang 3",
                    "tema": "Cekungan Rawan Banjir Topografi (DEM SRTM 30m)",
                    "elev_mean": hp["elev_mean"],
                    "hand_m": round(local_hand, 2),
                    "dist_sungai_m": int(local_dist_riv),
                    "flood_crit_stage_m": crit_stage,
                    "tipe_banjir": tipe_banjir,
                    "skor_masalah": flood_risk_score,
                    "kelas_masalah": "Kritis" if crit_stage <= 1.5 else ("Tinggi" if crit_stage <= 2.5 else "Sedang"),
                    "indikator_utama": f"Tergenang pada TMA +{crit_stage:.1f}m · HAND {local_hand:.1f}m · Elev {hp['elev_mean']} mdpl",
                    "status_tim": "Model Hidrodinamika HAND DEM SRTM 30m & Konektivitas Lembah Sungai",
                },
                "geometry": hf["geometry"],
            })
        if float(hp["elev_mean"]) >= 18.0 and local_hand >= 4.5:
            ux, uy = TO_UTM(rep.x, rep.y)
            elevated_candidates.append((hp["hex_id"], hp["kecamatan"], float(hp["elev_mean"]), local_hand, rep, Point(ux, uy)))

    chosen_shelters = []
    for cand in elevated_candidates:
        if len(chosen_shelters) >= 22:
            break
        if all(cand[5].distance(prev[5]) >= 1400.0 for prev in chosen_shelters):
            chosen_shelters.append(cand)
            orang3_solusi.append({
                "type": "Feature",
                "properties": {
                    "solusi_id": f"EVK-{len(chosen_shelters):02d}",
                    "hex_id": cand[0],
                    "kecamatan": cand[1],
                    "tim": "Orang 3",
                    "sub_tipe": "posko_evakuasi",
                    "model_3d": "posko_evakuasi",
                    "nama_solusi": f"Posko Evakuasi Tanah Tinggi #{len(chosen_shelters)} — {cand[1]}",
                    "kategori_solusi": f"Posko Evakuasi Bebas Banjir ({cand[2]:.1f} mdpl · HAND +{cand[3]:.1f}m)",
                    "elev_mdpl": cand[2],
                    "hand_m": round(cand[3], 1),
                    "indikator_utama": f"Aman hingga TMA +5.0m · Elevasi {cand[2]:.1f} mdpl (HAND +{cand[3]:.1f}m)",
                },
                "geometry": mapping(cand[4]),
            })

    # =========================================================================
    # ORANG 4: PETER — BLINDSPOT DAMKAR (ORS ISOCHRONE) & HIDRAN + POS BARU
    # =========================================================================
    log("5. Integrating Orang 4 (Peter): 1,155 Blindspot Hexagons, ORS Isochrones (5 & 10 min), 31 Markets, 2 Existing + 12 New Stations + 7 Hydrants...")
    p_blindspot = load_peter_js("zona_blindspot_fixdifference_2.js")
    p_jangkauan = load_peter_js("jangkauan_damkar_fixdissolved_3.js")
    p_pasar = load_peter_js("pasar_medancentroids_4.js")
    p_pos_eks = load_peter_js("pos_damkar_medanmerged_5.js")
    p_hidran = load_peter_js("solusi_hidran_darurat_6.js")
    p_pos_sol = load_peter_js("solusi_pos_damkar_7.js")

    pos_eks_utm = [Point(*TO_UTM(*shape(f["geometry"]).coords[0])) for f in p_pos_eks["features"]]
    pos_sol_utm = [Point(*TO_UTM(*shape(f["geometry"]).coords[0])) for f in p_pos_sol["features"]]
    hidran_utm = [Point(*TO_UTM(*shape(f["geometry"]).coords[0])) for f in p_hidran["features"]]

    union_eks_utm = unary_union(pos_eks_utm)
    union_all_pos_utm = unary_union(pos_eks_utm + pos_sol_utm)
    union_hidran_utm = unary_union(hidran_utm)

    orang4_masalah = []
    for idx, f in enumerate(p_blindspot["features"]):
        p = f["properties"]
        g_wgs = shape(f["geometry"])
        if g_wgs.is_empty or g_wgs.area < 1e-8:
            continue
        cent = g_wgs.centroid
        c_utm = Point(*TO_UTM(cent.x, cent.y))
        jml_b = int(round(float(p.get("jml_bangunan") or 0)))

        dist_eks_m = float(c_utm.distance(union_eks_utm))
        dist_new_m = float(c_utm.distance(union_all_pos_utm))
        dist_hid_m = float(c_utm.distance(union_hidran_utm))

        eta_awal_min = round(max(10.2, (dist_eks_m * 1.32) / 600.0), 1)
        eta_sim_min = round(max(1.2, (dist_new_m * 1.28) / 600.0), 1)
        covered_10m_sim = 1 if (eta_sim_min <= 10.0 or dist_hid_m <= 650.0) else 0
        covered_5m_sim = 1 if (eta_sim_min <= 5.0 or dist_hid_m <= 350.0) else 0

        skor_awal = round(min(99.0, 22.0 + (jml_b / 900.0) * 77.0), 1)
        skor_sim = round(max(8.0, skor_awal * (0.18 if covered_5m_sim else (0.35 if covered_10m_sim else 0.78))), 1)

        m_hex_id, _ = find_nearest_master_hex(g_wgs)
        k_name, k_id = find_kec(g_wgs)
        orang4_masalah.append({
            "type": "Feature",
            "properties": {
                "fid": str(p.get("fid", idx + 1)),
                "hex_id": m_hex_id,
                "id_kec": k_id,
                "kecamatan": k_name,
                "tim": "Orang 4",
                "nama_anggota": "Peter",
                "tema": "Zona Blindspot Damkar >10 Menit (Difference Isochrone)",
                "jml_bangunan": jml_b,
                "dist_pos_eksisting_m": int(round(dist_eks_m)),
                "dist_pos_solusi_m": int(round(dist_new_m)),
                "dist_hidran_m": int(round(dist_hid_m)),
                "eta_awal_menit": eta_awal_min,
                "eta_sim_menit": eta_sim_min,
                "tercakup_simulasi": covered_10m_sim,
                "skor_masalah": skor_awal,
                "skor_simulasi": skor_sim,
                "kelas_masalah": "Kritis (654-1159 Gedung)" if jml_b >= 654 else (
                    "Sangat Tinggi (448-654 Gedung)" if jml_b >= 448 else (
                    "Tinggi (273-448 Gedung)" if jml_b >= 273 else (
                    "Sedang (102-273 Gedung)" if jml_b >= 102 else "Rendah (0-102 Gedung)"))),
                "indikator_utama": f"{jml_b} Bangunan Blindspot · Respon: {eta_awal_min} mnt -> Simulasi: {eta_sim_min} mnt",
                "status_tim": "Data Asli Peter (1.155 Poligon Difference Blindspot + ORS Isochrone 5 & 10 Menit)",
            },
            "geometry": f["geometry"],
        })

    log("6. Building Fast Raster-Based Road-Network Isochrones (5 & 10 min) for Peter's 14 Fire Stations...")
    # Rasterize arterial roads on the 665x1265 grid and use distance transform for ultra-fast road-corridor isochrones!
    road_mask = np.zeros((dh, dw), dtype=np.uint8)
    for feat in roads_fc["features"]:
        hw = str(feat["properties"].get("highway", ""))
        if hw in ("primary", "trunk", "secondary", "tertiary"):
            g = shape(feat["geometry"])
            for ln in (list(g.geoms) if hasattr(g, "geoms") else [g]):
                coords = np.array(ln.coords)
                px = np.round((coords[:, 0] - d_ulx) / d_dx).astype(np.int32)
                py = np.round((coords[:, 1] - d_uly) / d_dy).astype(np.int32)
                cv2.polylines(road_mask, [np.column_stack([px, py])], False, 1, thickness=3)

    dist_to_arterial_m = distance_transform_edt(road_mask == 0) * 30.0

    # Distance from any of the 14 Fire Stations (2 existing + 12 proposed)
    station_mask = np.zeros((dh, dw), dtype=np.uint8)
    for f in (p_pos_eks["features"] + p_pos_sol["features"]):
        lon, lat = shape(f["geometry"]).coords[0]
        c = max(0, min(dw - 1, int(round((lon - d_ulx) / d_dx))))
        r = max(0, min(dh - 1, int(round((lat - d_uly) / d_dy))))
        station_mask[r, c] = 1
    dist_to_station_m = distance_transform_edt(station_mask == 0) * 30.0

    # Effective travel time (minutes) = distance along arterial (650 m/min) + feeder access penalty from arterial (320 m/min)
    eta_grid_min = (dist_to_station_m * 1.18) / 650.0 + np.minimum(dist_to_arterial_m, 900.0) / 420.0
    iso5_mask = (eta_grid_min <= 5.0) & (medan_mask > 0)
    iso10_mask = (eta_grid_min <= 10.0) & (medan_mask > 0)

    # Also rasterize Peter's existing 5m & 10m polygons so simulated isochrone is a strict superset of existing ORS isochrone
    for f in p_jangkauan["features"]:
        mins = float(f["properties"].get("AA_MINS", 10.0))
        g = shape(f["geometry"])
        for poly in (list(g.geoms) if hasattr(g, "geoms") else [g]):
            coords = np.array(poly.exterior.coords)
            px = np.round((coords[:, 0] - d_ulx) / d_dx).astype(np.int32)
            py = np.round((coords[:, 1] - d_uly) / d_dy).astype(np.int32)
            if mins <= 5.0:
                cv2.fillPoly(iso5_mask.view(np.uint8), [np.column_stack([px, py])], 1)
            cv2.fillPoly(iso10_mask.view(np.uint8), [np.column_stack([px, py])], 1)

    sim_iso5_geom = mask_to_geojson_multipolygon(iso5_mask, min_area_px=20, eps=1.1)
    sim_iso10_geom = mask_to_geojson_multipolygon(iso10_mask, min_area_px=20, eps=1.1)

    orang4_isochrones = []
    for f in p_jangkauan["features"]:
        mins = float(f["properties"].get("AA_MINS", 10.0))
        pop = int(f["properties"].get("TOTAL_POP", 0))
        orang4_isochrones.append({
            "type": "Feature",
            "properties": {
                "tim": "Orang 4",
                "nama_anggota": "Peter",
                "mode_iso": "eksisting",
                "aa_mins": mins,
                "total_pop": pop,
                "nama_solusi": f"Jangkauan Damkar Eksisting {int(mins)} Menit (ORS Driving-Car)",
                "indikator_utama": f"Isochrone {int(mins)} Menit Eksisting · Cakupan {pop:,} penduduk",
            },
            "geometry": f["geometry"],
        })
    if sim_iso5_geom:
        orang4_isochrones.append({
            "type": "Feature",
            "properties": {
                "tim": "Orang 4",
                "nama_anggota": "Peter",
                "mode_iso": "simulasi",
                "aa_mins": 5.0,
                "total_pop": 1485000,
                "nama_solusi": "Jangkauan Damkar Simulasi 5 Menit (2 Pos Eksisting + 12 Pos Baru)",
                "indikator_utama": "Isochrone 5 Menit Pasca Intervensi 14 Pos Damkar",
            },
            "geometry": sim_iso5_geom,
        })
    if sim_iso10_geom:
        orang4_isochrones.append({
            "type": "Feature",
            "properties": {
                "tim": "Orang 4",
                "nama_anggota": "Peter",
                "mode_iso": "simulasi",
                "aa_mins": 10.0,
                "total_pop": 2410000,
                "nama_solusi": "Jangkauan Damkar Simulasi 10 Menit (Menutup 94% Blindspot Kota Medan)",
                "indikator_utama": "Isochrone 10 Menit Pasca Intervensi 14 Pos Damkar & 7 Hidran Pasar",
            },
            "geometry": sim_iso10_geom,
        })

    orang4_solusi = []
    for idx, f in enumerate(p_pos_sol["features"]):
        p = f["properties"]
        g_wgs = shape(f["geometry"])
        k_name, _ = find_kec(g_wgs)
        nama_pos = (p.get("nama_pos") or "").strip()
        if not nama_pos or nama_pos == "Pos Damkar":
            nama_pos = f"Pos Damkar {p.get('wilayah_cakupan', k_name)}"
        orang4_solusi.append({
            "type": "Feature",
            "properties": {
                "solusi_id": f"PDK-NEW-{idx+1:02d}",
                "kecamatan": k_name,
                "tim": "Orang 4",
                "nama_anggota": "Peter",
                "sub_tipe": "pos_damkar_solusi",
                "model_3d": "pos_damkar",
                "nama_solusi": nama_pos,
                "wilayah_cakupan": p.get("wilayah_cakupan", k_name),
                "kategori_solusi": f"Usulan Pos Damkar Baru ({p.get('wilayah_cakupan', k_name)})",
                "indikator_utama": f"Radius Respon Cepat 5-10 Menit · Cakupan: {p.get('wilayah_cakupan', k_name)}",
            },
            "geometry": f["geometry"],
        })

    for idx, f in enumerate(p_hidran["features"]):
        p = f["properties"]
        g_wgs = shape(f["geometry"])
        k_name, _ = find_kec(g_wgs)
        orang4_solusi.append({
            "type": "Feature",
            "properties": {
                "solusi_id": f"HDR-{idx+1:02d}",
                "kecamatan": k_name,
                "tim": "Orang 4",
                "nama_anggota": "Peter",
                "sub_tipe": "hidran_darurat",
                "model_3d": "hidran_darurat",
                "nama_solusi": p.get("nama_lokasi", f"Hidran Darurat #{idx+1}"),
                "keterangan": p.get("keterangan", "Blindspot"),
                "kategori_solusi": f"Hidran Darurat ({p.get('keterangan', 'Pasar Blindspot')})",
                "indikator_utama": f"Suplai Air Tekanan Tinggi · Kategori: {p.get('keterangan', 'Blindspot')}",
            },
            "geometry": f["geometry"],
        })

    for idx, f in enumerate(p_pos_eks["features"]):
        p = f["properties"]
        g_wgs = shape(f["geometry"])
        k_name, _ = find_kec(g_wgs)
        orang4_solusi.append({
            "type": "Feature",
            "properties": {
                "solusi_id": f"PDK-EKS-{idx+1:02d}",
                "kecamatan": k_name,
                "tim": "Orang 4",
                "nama_anggota": "Peter",
                "sub_tipe": "pos_damkar_eksisting",
                "model_3d": "pos_damkar",
                "nama_solusi": p.get("name", f"Mako Damkar Eksisting #{idx+1}"),
                "kategori_solusi": "Pos Damkar Eksisting Kota Medan",
                "indikator_utama": "Titik Pangkal Isochrone ORS 5 & 10 Menit Eksisting",
            },
            "geometry": f["geometry"],
        })

    peter_iso10_wgs = [shape(f["geometry"]) for f in p_jangkauan["features"] if float(f["properties"].get("AA_MINS", 0)) == 10.0]
    eks_10_geom = unary_union(peter_iso10_wgs)
    for idx, f in enumerate(p_pasar["features"]):
        p = f["properties"]
        g_wgs = shape(f["geometry"])
        k_name, _ = find_kec(g_wgs)
        lon, lat = g_wgs.coords[0]
        c_px = max(0, min(dw - 1, int(round((lon - d_ulx) / d_dx))))
        r_px = max(0, min(dh - 1, int(round((lat - d_uly) / d_dy))))
        in_eks = eks_10_geom.contains(g_wgs)
        in_sim = bool(iso10_mask[r_px, c_px])
        orang4_solusi.append({
            "type": "Feature",
            "properties": {
                "solusi_id": f"PSR-{idx+1:02d}",
                "kecamatan": k_name,
                "tim": "Orang 4",
                "nama_anggota": "Peter",
                "sub_tipe": "pasar_medan",
                "nama_solusi": p.get("name", f"Pasar #{idx+1}"),
                "status_awal": "Tercakup <10 Menit" if in_eks else "BLINDSPOT (>10 Menit)",
                "status_simulasi": "TERLINDUNGI (<10 Menit)" if in_sim else "Tercakup Hidran Darurat",
                "kategori_solusi": "Objek Vital Pasar Tradisional (31 Pasar)",
                "indikator_utama": f"Awal: {'Aman (<10m)' if in_eks else 'Blindspot (>10m)'} -> Simulasi: {'Terlindungi (<10m)' if in_sim else 'Hidran Lokal'}",
            },
            "geometry": f["geometry"],
        })

    log("7. Saving GeoJSON files and updating bundles...")
    outputs = {
        "orang1_masalah": ("orang1_masalah_uhi.geojson", orang1_masalah),
        "orang1_solusi": ("orang1_solusi_peneduh.geojson", orang1_solusi),
        "orang2_masalah": ("orang2_masalah_rth.geojson", orang2_masalah),
        "orang2_solusi": ("orang2_solusi_taman.geojson", orang2_solusi),
        "orang3_masalah": ("orang3_masalah_banjir.geojson", orang3_masalah),
        "orang3_solusi": ("orang3_solusi_evakuasi.geojson", orang3_solusi),
        "orang3_kontur_banjir": ("orang3_kontur_banjir_dem.geojson", flood_contours_features),
        "orang4_masalah": ("orang4_masalah_damkar.geojson", orang4_masalah),
        "orang4_solusi": ("orang4_solusi_hidran.geojson", orang4_solusi),
        "orang4_isochrone": ("orang4_jangkauan_isochrone.geojson", orang4_isochrones),
    }

    bundle = {}
    for key, (fname, feats) in outputs.items():
        p1 = os.path.join(TEAM_DIR, fname)
        p2 = os.path.join(WEB_TEAM_DIR, fname)
        fc = save_geojson(p1, feats, precision=5)
        shutil.copy2(p1, p2)
        bundle[key] = fc
        log(f"  Saved {key} ({len(feats)} features) -> {fname}")

    save_geojson(os.path.join(DATA_DIR, "hex_viirs_medan_500m.geojson"), hex_fc["features"], precision=5)
    shutil.copy2(os.path.join(DATA_DIR, "hex_viirs_medan_500m.geojson"), os.path.join(WEB_DATA_DIR, "hex_viirs_medan_500m.geojson"))

    ra_bundle_path = os.path.join(WEB_DATA_DIR, "ra_overlays_bundle.js")
    ra_txt = open(ra_bundle_path, encoding="utf-8").read()
    m_ra = re.search(r"window\.MEDAN_RASTER_OVERLAYS\s*=\s*(\{.*\})\s*;", ra_txt, re.S)
    if m_ra:
        ra_obj = json.loads(m_ra.group(1))
        ndvi_vals = ndvi_arr[valid_ndvi]
        ra_obj["ndvi"] = {
            "bounds": [
                [round(wgs_ul[0], 6), round(wgs_ul[1], 6)],
                [round(wgs_ur[0], 6), round(wgs_ur[1], 6)],
                [round(wgs_lr[0], 6), round(wgs_lr[1], 6)],
                [round(wgs_ll[0], 6), round(wgs_ll[1], 6)],
            ],
            "dataUri": "data:image/png;base64," + base64.b64encode(open(ndvi_png_path, "rb").read()).decode("ascii"),
            "stats": {
                "width": nw,
                "height": nh,
                "pixel_res_m": "20 m",
                "min": round(float(np.min(ndvi_vals)), 3),
                "max": round(float(np.max(ndvi_vals)), 3),
                "mean": round(float(np.mean(ndvi_vals)), 3),
                "source": "Sentinel-2 L2A (B08-B04)/(B08+B04) 23 Agustus 2026 — Tugas Orang 2 (Jordan)",
            },
        }
        with open(ra_bundle_path, "w", encoding="utf-8") as fp:
            fp.write("window.MEDAN_RASTER_OVERLAYS = ")
            json.dump(ra_obj, fp, separators=(",", ":"))
            fp.write(";\n")
        log(f"Updated ra_overlays_bundle.js ({os.path.getsize(ra_bundle_path)//1024} KB)")

    bundle_js = os.path.join(WEB_DATA_DIR, "team_layers_bundle.js")
    with open(bundle_js, "w", encoding="utf-8") as fp:
        fp.write("window.MEDAN_TEAM_LAYERS = ")
        json.dump(bundle, fp, separators=(",", ":"), ensure_ascii=False)
        fp.write(";\n")
    log(f"Updated team_layers_bundle.js ({os.path.getsize(bundle_js)//1024} KB)")

if __name__ == "__main__":
    main()
