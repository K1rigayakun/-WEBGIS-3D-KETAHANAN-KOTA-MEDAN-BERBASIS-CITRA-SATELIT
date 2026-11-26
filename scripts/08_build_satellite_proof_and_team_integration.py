import base64
import json
import os
import shutil
from typing import Any, Dict, List, Tuple

import numpy as np
from matplotlib.path import Path as MplPath
from osgeo import gdal
from PIL import Image
from pyproj import Transformer
from shapely import STRtree
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import transform, unary_union

gdal.UseExceptions()

BASE_DIR = r"M:\Kuliah\Semester 5\SIG\Project Akhir"
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DATA_DIR = os.path.join(BASE_DIR, "web-peta-interaktif", "data")
TEAM_DIR = os.path.join(DATA_DIR, "integrasi_tim")
WEB_TEAM_DIR = os.path.join(WEB_DATA_DIR, "integrasi_tim")

os.makedirs(TEAM_DIR, exist_ok=True)
os.makedirs(WEB_TEAM_DIR, exist_ok=True)

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32647", always_xy=True).transform
TO_WGS = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True).transform


def log(msg: str) -> None:
    print(f"[08_INTEGRATE] {msg}", flush=True)


def save_geojson(path: str, features: List[Dict[str, Any]], precision: int = 6) -> None:
    def round_coords(coords):
        if not coords:
            return coords
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], precision), round(coords[1], precision)]
        return [round_coords(c) for c in coords]

    clean_features = []
    for f in features:
        geom = f["geometry"]
        if geom and geom.get("coordinates"):
            geom = {"type": geom["type"], "coordinates": round_coords(geom["coordinates"])}
        clean_features.append({"type": "Feature", "properties": f["properties"], "geometry": geom})

    fc = {"type": "FeatureCollection", "features": clean_features}
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(fc, fp, separators=(",", ":"), ensure_ascii=False)
    log(f"Saved {len(clean_features)} features -> {os.path.relpath(path, BASE_DIR)}")


def build_medan_mask(gt: Tuple[float, ...], w: int, h: int, medan_geom) -> np.ndarray:
    xs = gt[0] + (np.arange(w) + 0.5) * gt[1]
    ys = gt[3] + (np.arange(h) + 0.5) * gt[5]
    polys = list(medan_geom.geoms) if isinstance(medan_geom, MultiPolygon) else [medan_geom]
    xx, yy = np.meshgrid(xs, ys)
    pts = np.column_stack([xx.ravel(), yy.ravel()])
    inside = np.zeros(len(pts), dtype=bool)
    for poly in polys:
        ext_path = MplPath(np.asarray(poly.exterior.coords))
        m = ext_path.contains_points(pts)
        for hole in poly.interiors:
            m &= ~MplPath(np.asarray(hole.coords)).contains_points(pts)
        inside |= m
    return inside.reshape(h, w)


def generate_satellite_darkness_assets(medan_union, hex_fc: Dict[str, Any]) -> Dict[str, Any]:
    # Load existing ra_overlays_bundle stats/DEM or build fresh cleanly
    viirs_tif = os.path.join(DATA_DIR, "viirs_medan_2024.tif")
    ds = gdal.Open(viirs_tif)
    gt = ds.GetGeoTransform()
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    nodata = ds.GetRasterBand(1).GetNoDataValue()
    ds = None

    h, w = arr.shape
    mask = build_medan_mask(gt, w, h, medan_union)
    valid = arr if nodata is None else np.where(arr == nodata, 0.0, arr)
    medan_vals = valid[mask]

    # 1. Bicubic upscaled float array (16x -> 720x1376) for smooth satellite overlay
    scale = 16
    hi_w, hi_h = w * scale, h * scale
    gt_hi = (gt[0], gt[1] / scale, gt[2], gt[3], gt[4], gt[5] / scale)
    mask_hi = build_medan_mask(gt_hi, hi_w, hi_h, medan_union)
    hi_img = Image.fromarray(np.clip(valid, 0.0, 120.0).astype(np.float32), mode="F").resize(
        (hi_w, hi_h), Image.Resampling.BICUBIC
    )
    hi_val = np.clip(np.asarray(hi_img, dtype=np.float64), 0.0, 110.0)

    # Smooth VIIRS heatmap PNG (viirs_2024_raw.png, strict palette stops)
    stops = np.array([0.0, 22.0, 50.0, 85.0, 110.0])
    r_vals = np.array([7, 22, 185, 255, 255], dtype=np.float64)
    g_vals = np.array([27, 125, 228, 220, 201], dtype=np.float64)
    b_vals = np.array([43, 141, 232, 120, 77], dtype=np.float64)

    rr_hm = np.interp(hi_val, stops, r_vals).astype(np.uint8)
    gg_hm = np.interp(hi_val, stops, g_vals).astype(np.uint8)
    bb_hm = np.interp(hi_val, stops, b_vals).astype(np.uint8)
    aa_hm = np.where(mask_hi, 210, 0).astype(np.uint8)
    viirs_raw_png = os.path.join(WEB_DATA_DIR, "viirs_2024_raw.png")
    Image.fromarray(np.dstack([rr_hm, gg_hm, bb_hm, aa_hm]), mode="RGBA").resize(
        (w * 8, h * 8), Image.Resampling.BICUBIC
    ).save(viirs_raw_png, optimize=True, compress_level=9)

    # 2. Uncolored Genuine Night-Sensor Radiance Overlay (viirs_night_darkness.png)
    # Casts real uncolored night shadow (#071B2B) strictly matching 0..28 DN VIIRS voids
    # without synthetic cyan/teal tinting, fading completely clear over bright city cores.
    d_stops = np.array([0.0, 16.0, 28.0, 48.0, 75.0, 110.0])
    dr = np.array([7, 7, 7, 7, 255, 255], dtype=np.float64)
    dg = np.array([27, 27, 27, 27, 255, 201], dtype=np.float64)
    db = np.array([43, 43, 43, 43, 255, 77], dtype=np.float64)
    da = np.array([218, 195, 138, 12, 0, 28], dtype=np.float64)

    n_r = np.interp(hi_val, d_stops, dr).astype(np.uint8)
    n_g = np.interp(hi_val, d_stops, dg).astype(np.uint8)
    n_b = np.interp(hi_val, d_stops, db).astype(np.uint8)
    n_a = np.where(mask_hi, np.interp(hi_val, d_stops, da), 0).astype(np.uint8)

    night_png = os.path.join(WEB_DATA_DIR, "viirs_night_darkness.png")
    Image.fromarray(np.dstack([n_r, n_g, n_b, n_a]), mode="RGBA").resize(
        (w * 8, h * 8), Image.Resampling.BICUBIC
    ).save(night_png, optimize=True, compress_level=9)

    ulx, uly = gt[0], gt[3]
    lrx, lry = gt[0] + w * gt[1], gt[3] + h * gt[5]

    # 3. DEM stats preserved cleanly
    dem_tif = os.path.join(DATA_DIR, "dem_medan_srtm.tif")
    dds = gdal.Open(dem_tif)
    dgt = dds.GetGeoTransform()
    darr = dds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    dnodata = dds.GetRasterBand(1).GetNoDataValue()
    dds = None
    dh, dw = darr.shape
    dmask = build_medan_mask(dgt, dw, dh, medan_union)
    dvalid = np.where((darr == dnodata) | (darr < -10), 0.0, darr) if dnodata is not None else np.maximum(darr, 0.0)
    dem_medan_vals = dvalid[dmask]
    dulx, duly = dgt[0], dgt[3]
    dlrx, dlry = dgt[0] + dw * dgt[1], dgt[3] + dh * dgt[5]
    dem_png = os.path.join(WEB_DATA_DIR, "dem_srtm_raw.png")

    # 4. VIIRS Iso-Radiance Contours (viirs_kontur_gelap.geojson)
    gelap_polys = []
    redup_polys = []
    terang_polys = []
    for f in hex_fc["features"]:
        v = float(f["properties"].get("viirs_mean", 0))
        g = shape(f["geometry"])
        if v < 25.0:
            gelap_polys.append(g)
        elif v < 50.0:
            redup_polys.append(g)
        else:
            terang_polys.append(g)

    zone_features = []
    zone_defs = [
        ("GELAP_KRITIS", "Zona Gelap Satelit VIIRS (< 25 DN)", "GELAP SATELIT (<25 DN)", gelap_polys, 15.0),
        ("REDUP_SEDANG", "Zona Redup Satelit VIIRS (25-49 DN)", "ZONA REDUP (25-49 DN)", redup_polys, 37.0),
        ("TERANG_KOTA", "Pusat Terang Satelit VIIRS (>= 50 DN)", "PUSAT TERANG (>=50 DN)", terang_polys, 68.0),
    ]
    for zcode, ztitle, zshort, plist, zval in zone_defs:
        if not plist:
            continue
        merged = unary_union(plist).buffer(0.00005).buffer(-0.00005)
        geoms = list(merged.geoms) if isinstance(merged, MultiPolygon) else [merged]
        geoms.sort(key=lambda pg: pg.area, reverse=True)
        for idx, pg in enumerate(geoms):
            if pg.is_empty or pg.area < 1e-6:
                continue
            zone_features.append({
                "type": "Feature",
                "properties": {
                    "feature_type": "zone_poly",
                    "zona_jenis": zcode,
                    "nama_zona": ztitle,
                    "label_singkat": zshort,
                    "viirs_ref_dn": zval,
                },
                "geometry": mapping(pg),
            })
            if idx < 4 and zcode != "REDUP_SEDANG":
                rp = pg.representative_point()
                zone_features.append({
                    "type": "Feature",
                    "properties": {
                        "feature_type": "zone_label",
                        "zona_jenis": zcode,
                        "label_singkat": zshort,
                    },
                    "geometry": mapping(rp),
                })

    viirs_zones_path = os.path.join(DATA_DIR, "viirs_kontur_gelap.geojson")
    save_geojson(viirs_zones_path, zone_features, precision=5)
    shutil.copy2(viirs_zones_path, os.path.join(WEB_DATA_DIR, "viirs_kontur_gelap.geojson"))

    zones_fc = json.load(open(viirs_zones_path, encoding="utf-8"))

    overlays = {
        "viirs": {
            "bounds": [[round(ulx, 6), round(uly, 6)], [round(lrx, 6), round(uly, 6)], [round(lrx, 6), round(lry, 6)], [round(ulx, 6), round(lry, 6)]],
            "dataUri": "data:image/png;base64," + base64.b64encode(open(viirs_raw_png, "rb").read()).decode("ascii"),
            "nightDataUri": "data:image/png;base64," + base64.b64encode(open(night_png, "rb").read()).decode("ascii"),
            "gt": [round(x, 8) for x in gt],
            "matrix": [[round(float(valid[r, c]), 1) for c in range(w)] for r in range(h)],
            "medanMax": round(float(np.max(medan_vals)), 1),
            "stats": {
                "width": w,
                "height": h,
                "pixel_res_m": "~460 m",
                "min": round(float(np.min(medan_vals)), 2),
                "max": round(float(np.max(medan_vals)), 2),
                "mean": round(float(np.mean(medan_vals)), 2),
                "p50": round(float(np.percentile(medan_vals, 50)), 2),
                "p90": round(float(np.percentile(medan_vals, 90)), 2),
                "source": "EOG / OpenGeoHub Annual VIIRS V2.1 (2024) - Zenodo DOI:10.5281/zenodo.17294744",
            },
        },
        "dem": {
            "bounds": [[round(dulx, 6), round(duly, 6)], [round(dlrx, 6), round(duly, 6)], [round(dlrx, 6), round(dlry, 6)], [round(dulx, 6), round(dlry, 6)]],
            "dataUri": "data:image/png;base64," + base64.b64encode(open(dem_png, "rb").read()).decode("ascii"),
            "stats": {
                "width": dw,
                "height": dh,
                "pixel_res_m": "30 m",
                "min_m": round(float(np.min(dem_medan_vals)), 1),
                "max_m": round(float(np.max(dem_medan_vals)), 1),
                "mean_m": round(float(np.mean(dem_medan_vals)), 1),
                "source": "DEM SRTM 30m Sumatera Utara (USGS / BIG)",
            },
        },
        "viirsZones": zones_fc,
    }

    bundle_out = os.path.join(WEB_DATA_DIR, "ra_overlays_bundle.js")
    with open(bundle_out, "w", encoding="utf-8") as fp:
        fp.write("window.MEDAN_RASTER_OVERLAYS = ")
        json.dump(overlays, fp, separators=(",", ":"))
        fp.write(";\n")
    log(f"Updated {os.path.relpath(bundle_out, BASE_DIR)} ({os.path.getsize(bundle_out) // 1024} KB)")
    return overlays


def generate_team_integration_data(kec_fc, hex_fc, bld_fc, water_fc, roads_fc):
    # Precompute UTM geometries for authentic deterministic metrics
    hex_feats = hex_fc["features"]
    hex_utm = [transform(TO_UTM, shape(f["geometry"])) for f in hex_feats]
    hex_centroids_utm = [g.centroid for g in hex_utm]
    hex_tree = STRtree(hex_utm)

    # Count real OSM buildings inside each hexagon
    bld_counts = [0] * len(hex_feats)
    for bf in bld_fc["features"]:
        p = bf["properties"]
        pt_utm = Point(*TO_UTM(float(p["lon"]), float(p["lat"])))
        cands = hex_tree.query(pt_utm)
        for idx in cands:
            if hex_utm[idx].contains(pt_utm):
                bld_counts[idx] += 1
                break

    water_utm = [transform(TO_UTM, shape(f["geometry"])) for f in water_fc["features"]]
    water_tree = STRtree(water_utm)

    primary_roads_utm = []
    primary_roads_wgs = []
    # Orang 1 solusi: shade-tree corridors from real arterial OSM roads
    for rf in roads_fc["features"]:
        hw = str(rf["properties"].get("highway", ""))
        if hw in ("primary", "trunk", "secondary"):
            g = shape(rf["geometry"])
            rname = str(rf["properties"].get("nama_jalan", "") or "").strip()
            primary_roads_wgs.append((rname or f"Koridor Arteri #{len(primary_roads_wgs)+1}", g))
            primary_roads_utm.append(transform(TO_UTM, g))
    road_tree = STRtree(primary_roads_utm)

    # Save master templates with locked join keys (hex_id + id_kec)
    master_hex_features = []
    orang1_masalah, orang2_masalah, orang3_masalah, orang4_masalah = [], [], [], []
    orang1_solusi, orang2_solusi, orang3_solusi, orang4_solusi = [], [], [], []

    used_road_names = set()
    elevated_hex = [
        (i, float(f["properties"].get("elev_mean", 0)), hex_centroids_utm[i], shape(f["geometry"]).representative_point())
        for i, f in enumerate(hex_feats)
        if float(f["properties"].get("elev_mean", 0)) >= 22.0
    ]

    for i, hf in enumerate(hex_feats):
        hp = hf["properties"]
        hx_id = hp["hex_id"]
        kec = hp["kecamatan"]
        id_kec = hp["id_kec"]
        pop = float(hp.get("penduduk_2025", 90000))
        viirs = float(hp.get("viirs_mean", 20.0))
        elev = float(hp.get("elev_mean", 20.0))
        bcount = bld_counts[i]

        ct_utm = hex_centroids_utm[i]
        w_idx = water_tree.nearest(ct_utm)
        dist_river_m = round(float(ct_utm.distance(water_utm[w_idx])), 0) if w_idx is not None else 2500.0
        r_idx = road_tree.nearest(ct_utm)
        dist_arteri_m = round(float(ct_utm.distance(primary_roads_utm[r_idx])), 0) if r_idx is not None else 1200.0

        # Real heuristic scores from spatial geometry (for starter integration schemas)
        pop_norm = min(1.0, pop / 190000.0)
        bld_norm = min(1.0, bcount / 350.0)
        elev_low_norm = max(0.0, min(1.0, (24.0 - elev) / 24.0))
        river_norm = max(0.0, min(1.0, 1.0 - dist_river_m / 1800.0))

        # Orang 1 (Micro-UHI): urban density + high nighttime radiance + low elevation
        uhi_score = round(100.0 * (0.45 * bld_norm + 0.35 * min(1.0, viirs / 65.0) + 0.20 * pop_norm), 1)
        est_temp = round(29.8 + (uhi_score / 100.0) * 6.2, 1)

        # Orang 2 (Defisit RTH): dense residential settlement vs green buffer
        rth_score = round(100.0 * (0.50 * pop_norm + 0.35 * bld_norm + 0.15 * min(1.0, viirs / 60.0)), 1)

        # Orang 3 (Cekungan Banjir): low SRTM elevation + proximity to Sungai Deli/Babura
        flood_score = round(100.0 * (0.55 * elev_low_norm + 0.45 * river_norm), 1)

        # Orang 4 (Damkar Blindspot): far from wide arterial road + dense settlement
        damkar_score = round(100.0 * (0.60 * min(1.0, dist_arteri_m / 1400.0) + 0.40 * max(bld_norm, pop_norm * 0.6)), 1)

        master_hex_features.append({
            "type": "Feature",
            "properties": {
                "hex_id": hx_id,
                "id_kec": id_kec,
                "kecamatan": kec,
                "viirs_mean": viirs,
                "elev_mean": elev,
                "gedung_osm_count": bcount,
                "orang1_uhi_skor": uhi_score,
                "orang2_rth_skor": rth_score,
                "orang3_banjir_skor": flood_score,
                "orang4_damkar_skor": damkar_score,
            },
            "geometry": hf["geometry"],
        })

        geom_wgs = shape(hf["geometry"])
        rep_pt = geom_wgs.representative_point()

        if uhi_score >= 52.0:
            orang1_masalah.append({
                "type": "Feature",
                "properties": {
                    "hex_id": hx_id, "id_kec": id_kec, "kecamatan": kec, "tim": "Orang 1",
                    "tema": "Micro-UHI & Panas Ekstrem",
                    "skor_masalah": uhi_score,
                    "kelas_masalah": "Kritis" if uhi_score >= 70 else "Tinggi",
                    "indikator_utama": f"Estimasi {est_temp} C ({bcount} gedung/hex)",
                    "status_tim": "Baseline Integrasi Siap Setor Landsat LST",
                },
                "geometry": hf["geometry"],
            })

        if rth_score >= 58.0:
            orang2_masalah.append({
                "type": "Feature",
                "properties": {
                    "hex_id": hx_id, "id_kec": id_kec, "kecamatan": kec, "tim": "Orang 2",
                    "tema": "Defisit Ruang Terbuka Hijau (RTH)",
                    "skor_masalah": rth_score,
                    "kelas_masalah": "Kritis" if rth_score >= 74 else "Tinggi",
                    "indikator_utama": f"Defisit RTH {rth_score:.0f}% ({int(pop):,} warga)",
                    "status_tim": "Baseline Integrasi Siap Setor Sentinel NDVI",
                },
                "geometry": hf["geometry"],
            })
            if len(orang2_solusi) < 28 and rth_score >= 66.0:
                orang2_solusi.append({
                    "type": "Feature",
                    "properties": {
                        "hex_id": hx_id, "kecamatan": kec, "tim": "Orang 2",
                        "nama_solusi": f"Taman Lingkungan Kelurahan #{len(orang2_solusi)+1}",
                        "kategori_solusi": "RTH Baru & Kantong Vegetasi",
                        "indikator_utama": f"Prioritas penanaman di {kec}",
                    },
                    "geometry": mapping(rep_pt),
                })

        if flood_score >= 58.0:
            orang3_masalah.append({
                "type": "Feature",
                "properties": {
                    "hex_id": hx_id, "id_kec": id_kec, "kecamatan": kec, "tim": "Orang 3",
                    "tema": "Cekungan Rawan Banjir Sungai",
                    "skor_masalah": flood_score,
                    "kelas_masalah": "Kritis" if flood_score >= 75 else "Tinggi",
                    "indikator_utama": f"Elev SRTM {elev} mdpl · Jarak sungai {int(dist_river_m)} m",
                    "status_tim": "Data Elevasi SRTM 30m + Sungai OSM",
                },
                "geometry": hf["geometry"],
            })
            if len(orang3_solusi) < 24 and flood_score >= 76.0 and elevated_hex:
                # Find nearest high-elevation shelter candidate
                best_el = min(elevated_hex, key=lambda t: t[2].distance(ct_utm))
                orang3_solusi.append({
                    "type": "Feature",
                    "properties": {
                        "hex_id": best_el[0] if isinstance(best_el[0], str) else hex_feats[best_el[0]]["properties"]["hex_id"],
                        "kecamatan": kec, "tim": "Orang 3",
                        "nama_solusi": f"Posko Evakuasi Banjir #{len(orang3_solusi)+1} (Tanah Tinggi)",
                        "kategori_solusi": "Posko Evakuasi Elevasi >22m",
                        "indikator_utama": f"Elevasi aman {best_el[1]} mdpl",
                    },
                    "geometry": mapping(best_el[3]),
                })

        if damkar_score >= 58.0:
            orang4_masalah.append({
                "type": "Feature",
                "properties": {
                    "hex_id": hx_id, "id_kec": id_kec, "kecamatan": kec, "tim": "Orang 4",
                    "tema": "Blindspot Pemadam Kebakaran",
                    "skor_masalah": damkar_score,
                    "kelas_masalah": "Kritis" if damkar_score >= 74 else "Tinggi",
                    "indikator_utama": f"Jarak arteri lebar {int(dist_arteri_m)} m",
                    "status_tim": "Baseline Integrasi Siap Setor ORS Isochrone",
                },
                "geometry": hf["geometry"],
            })
            if len(orang4_solusi) < 30 and damkar_score >= 66.0 and bcount > 10:
                orang4_solusi.append({
                    "type": "Feature",
                    "properties": {
                        "hex_id": hx_id, "kecamatan": kec, "tim": "Orang 4",
                        "nama_solusi": f"Hidran Umum Lingkungan #{len(orang4_solusi)+1}",
                        "kategori_solusi": "Hidran & Tandon Mulut Gang",
                        "indikator_utama": f"Menutup blindspot {bcount} bangunan",
                    },
                    "geometry": mapping(rep_pt),
                })

    # Orang 1 solusi: shade-tree corridors from real arterial OSM roads
    for rname, rgeom in primary_roads_wgs:
        if rname and rname not in used_road_names and len(orang1_solusi) < 20:
            used_road_names.add(rname)
            orang1_solusi.append({
                "type": "Feature",
                "properties": {
                    "kecamatan": "Koridor Arteri Medan", "tim": "Orang 1",
                    "nama_solusi": f"Jalur Peneduh Trembesi — {rname}",
                    "kategori_solusi": "Koridor Pohon Peneduh & Halte Teduh",
                    "indikator_utama": "Reduksi suhu permukaan koridor UHI",
                },
                "geometry": mapping(rgeom),
            })

    # Master 21 kecamatan template
    kec_template = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id_kec": f["properties"]["id_kec"],
                    "kode_kec": f["properties"].get("kode_kec", ""),
                    "nama_kec": f["properties"]["nama_kec"],
                    "luas_km2": f["properties"]["luas_km2"],
                    "penduduk_2025": f["properties"]["penduduk_2025"],
                    "viirs_mean": f["properties"]["viirs_mean"],
                    "orang5_avg_risk": f["properties"]["avg_risk_score"],
                },
                "geometry": f["geometry"],
            }
            for f in kec_fc["features"]
        ],
    }

    with open(os.path.join(TEAM_DIR, "master_21_kecamatan_template.geojson"), "w", encoding="utf-8") as fp:
        json.dump(kec_template, fp, separators=(",", ":"), ensure_ascii=False)
    save_geojson(os.path.join(TEAM_DIR, "master_hex_500m_template.geojson"), master_hex_features)

    outputs = {
        "orang1_masalah": ("orang1_masalah_uhi.geojson", orang1_masalah),
        "orang1_solusi": ("orang1_solusi_peneduh.geojson", orang1_solusi),
        "orang2_masalah": ("orang2_masalah_rth.geojson", orang2_masalah),
        "orang2_solusi": ("orang2_solusi_taman.geojson", orang2_solusi),
        "orang3_masalah": ("orang3_masalah_banjir.geojson", orang3_masalah),
        "orang3_solusi": ("orang3_solusi_evakuasi.geojson", orang3_solusi),
        "orang4_masalah": ("orang4_masalah_damkar.geojson", orang4_masalah),
        "orang4_solusi": ("orang4_solusi_hidran.geojson", orang4_solusi),
    }

    bundle = {}
    for key, (fname, feats) in outputs.items():
        fpath = os.path.join(TEAM_DIR, fname)
        save_geojson(fpath, feats)
        shutil.copy2(fpath, os.path.join(WEB_TEAM_DIR, fname))
        bundle[key] = json.load(open(fpath, encoding="utf-8"))

    shutil.copy2(os.path.join(TEAM_DIR, "master_hex_500m_template.geojson"), os.path.join(WEB_TEAM_DIR, "master_hex_500m_template.geojson"))

    bundle_js = os.path.join(WEB_DATA_DIR, "team_layers_bundle.js")
    with open(bundle_js, "w", encoding="utf-8") as fp:
        fp.write("window.MEDAN_TEAM_LAYERS = ")
        json.dump(bundle, fp, separators=(",", ":"), ensure_ascii=False)
        fp.write(";\n")
    log(f"Created {os.path.relpath(bundle_js, BASE_DIR)} ({os.path.getsize(bundle_js) // 1024} KB)")

    contract_md = """# Kontrak Skema Integrasi 5 Anggota Tim — WebGIS Medan Tangguh (Kota Medan)

Seluruh anggota tim bekerja di QGIS pada **21 Kecamatan Kota Medan (`EPSG:4326`)** menggunakan kunci gabungan (*join key*) yang sama dari berkas `master_hex_500m_template.geojson` (`hex_id`: `HEX-0001`..`HEX-1470`) dan `master_21_kecamatan_template.geojson` (`id_kec`: `1`..`21`, `nama_kec`).

| Anggota | Tema Layer | Berkas Masalah (Polygon/Hex) | Berkas Solusi Akar Masalah (Point/Line/Polygon) | Atribut Wajib |
|---|---|---|---|---|
| **Orang 1** | Micro-UHI / Suhu Panas Ekstrem | `orang1_masalah_uhi.geojson` | `orang1_solusi_peneduh.geojson` | `hex_id`, `kecamatan`, `skor_masalah` (0-100), `indikator_utama`, `nama_solusi`, `kategori_solusi` |
| **Orang 2** | Defisit RTH / Krisis Vegetasi | `orang2_masalah_rth.geojson` | `orang2_solusi_taman.geojson` | `hex_id`, `kecamatan`, `skor_masalah` (0-100), `indikator_utama`, `nama_solusi`, `kategori_solusi` |
| **Orang 3** | Cekungan Rawan Banjir & Evakuasi | `orang3_masalah_banjir.geojson` | `orang3_solusi_evakuasi.geojson` | `hex_id`, `kecamatan`, `skor_masalah` (0-100), `indikator_utama`, `nama_solusi`, `kategori_solusi` |
| **Orang 4** | Blindspot Damkar 10 Menit & Hidran | `orang4_masalah_damkar.geojson` | `orang4_solusi_hidran.geojson` | `hex_id`, `kecamatan`, `skor_masalah` (0-100), `indikator_utama`, `nama_solusi`, `kategori_solusi` |
| **Orang 5** *(Aktif)* | 3D Dark-Zone Begal & PJU Pintar + Web Integrator | `hex_viirs_medan_500m.geojson` + `bangunan_fokus_3d.geojson` + `koridor_rawan_begal.geojson` | `solusi_pju_cctv.geojson` + `solusi_rute_patroli.geojson` | `hex_id`, `vuln_score`, `risk_score`, `viirs_rad`, `id_unit`, `radius_terang_m` |

## Cara Menggabungkan Data Final Anggota 1–4 ke WebGIS
1. **Cara 1 (Live Impor di Browser)**: Buka WebGIS -> scroll panel kiri ke bagian **Integrasi 5 Data Tim (Orang 1-5)** -> pilih slot (mis. `Orang 1 - Masalah` atau `Orang 3 - Solusi`) -> klik **Impor .GeoJSON Teman**. Data langsung ter-render menjadi layer interaktif 3D/2D.
2. **Cara 2 (Timpa Berkas Permanen)**: Timpa berkas `.geojson` di `data/integrasi_tim/`, lalu jalankan ulang script penyatu ke `web-peta-interaktif/data/team_layers_bundle.js`.
"""
    with open(os.path.join(TEAM_DIR, "KONTRAK_INTEGRASI_5_ORANG.md"), "w", encoding="utf-8") as fp:
        fp.write(contract_md)
    log("Wrote KONTRAK_INTEGRASI_5_ORANG.md")


def main() -> None:
    kec_fc = json.load(open(os.path.join(DATA_DIR, "batas_kecamatan_medan.geojson"), encoding="utf-8"))
    hex_fc = json.load(open(os.path.join(DATA_DIR, "hex_viirs_medan_500m.geojson"), encoding="utf-8"))
    bld_fc = json.load(open(os.path.join(DATA_DIR, "bangunan_fokus_3d.geojson"), encoding="utf-8"))
    water_fc = json.load(open(os.path.join(DATA_DIR, "sungai_fokus_osm.geojson"), encoding="utf-8"))
    roads_fc = json.load(open(os.path.join(DATA_DIR, "jalan_fokus_osm.geojson"), encoding="utf-8"))

    medan_union = unary_union([shape(f["geometry"]) for f in kec_fc["features"]])
    generate_satellite_darkness_assets(medan_union, hex_fc)
    generate_team_integration_data(kec_fc, hex_fc, bld_fc, water_fc, roads_fc)
    log("ALL SATELLITE NIGHT PROOF & 5-MEMBER TEAM ASSETS GENERATED!")


if __name__ == "__main__":
    main()
