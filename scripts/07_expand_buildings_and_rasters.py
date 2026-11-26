import base64
import concurrent.futures
import glob
import json
import os
import shutil
import time
from typing import Any, Dict, List, Tuple

import numpy as np
import requests
from osgeo import gdal
from PIL import Image
from pyproj import Transformer
from shapely import STRtree
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import transform, unary_union

gdal.UseExceptions()

BASE_DIR = r"M:\Kuliah\Semester 5\SIG\Project Akhir"
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_OSM_DIR = os.path.join(DATA_DIR, "raw_osm")
WEB_DATA_DIR = os.path.join(BASE_DIR, "web-peta-interaktif", "data")

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32647", always_xy=True).transform
TO_WGS = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True).transform
HEADERS = {"User-Agent": "MedanDarkZoneSIG/1.0 (Academic GIS Project)"}


def log(msg: str) -> None:
    print(f"[07_EXPAND] {msg}", flush=True)


def save_geojson(path: str, features: List[Dict[str, Any]], precision: int = 6) -> None:
    def round_coords(coords):
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


def fetch_extra_tile(args):
    idx, minx, miny, maxx, maxy = args
    out_file = os.path.join(RAW_OSM_DIR, f"osm_tile_extra_{idx}.json")
    if os.path.exists(out_file) and os.path.getsize(out_file) > 100:
        with open(out_file, encoding="utf-8") as fp:
            return json.load(fp)
    url = f"https://api.openstreetmap.org/api/0.6/map.json?bbox={minx:.5f},{miny:.5f},{maxx:.5f},{maxy:.5f}"
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                data = r.json()
                with open(out_file, "w", encoding="utf-8") as fp:
                    json.dump(data, fp)
                return data
            log(f"Extra tile {idx} HTTP {r.status_code}, retrying...")
        except Exception as e:
            log(f"Extra tile {idx} error {e}, retrying...")
        time.sleep(1.5 * (attempt + 1))
    return {"elements": []}


def smart_building_height(tags: Dict[str, Any], area_m2: float) -> Tuple[float, str]:
    h_raw = tags.get("height") or tags.get("building:height")
    if h_raw:
        try:
            val = float(str(h_raw).lower().replace("m", "").strip())
            if 2.0 <= val <= 250.0:
                return round(val, 1), "osm_height"
        except ValueError:
            pass

    lvl_raw = tags.get("building:levels")
    if lvl_raw:
        try:
            lvls = float(str(lvl_raw).strip())
            if 1.0 <= lvls <= 60.0:
                return round(lvls * 4.0, 1), "osm_levels"
        except ValueError:
            pass

    btype = str(tags.get("building", "yes")).lower()
    amenity = str(tags.get("amenity", "")).lower()

    if btype in {"apartments", "commercial", "hotel", "hospital", "university", "office", "public", "civic"} or amenity in {"hospital", "university"}:
        if area_m2 > 2500:
            return 32.0, "fallback_major_complex"
        return 25.0, "fallback_commercial_civic"

    if btype in {"retail", "shop", "shophouse", "warehouse", "industrial", "school", "college"} or amenity in {"school", "college", "bank"}:
        return 12.0, "fallback_retail_shophouse"

    if area_m2 >= 1500:
        return 24.0, "fallback_area_large"
    if area_m2 >= 450:
        return 12.0, "fallback_area_medium"
    if area_m2 >= 180:
        return 8.0, "fallback_area_ruko"
    return 6.0, "fallback_area_house"


class RasterSampler:
    def __init__(self, tif_path: str):
        ds = gdal.Open(tif_path)
        self.gt = ds.GetGeoTransform()
        band = ds.GetRasterBand(1)
        self.arr = band.ReadAsArray().astype(np.float64)
        self.nodata = band.GetNoDataValue()
        self.h, self.w = self.arr.shape
        ds = None

    def sample_point(self, lon: float, lat: float) -> float:
        col = int((lon - self.gt[0]) / self.gt[1])
        row = int((lat - self.gt[3]) / self.gt[5])
        if 0 <= row < self.h and 0 <= col < self.w:
            val = float(self.arr[row, col])
            if self.nodata is not None and val == self.nodata:
                return 0.0
            return val
        return 0.0


def build_medan_mask(gt, w: int, h: int, medan_geom) -> np.ndarray:
    xs = gt[0] + (np.arange(w) + 0.5) * gt[1]
    ys = gt[3] + (np.arange(h) + 0.5) * gt[5]
    from matplotlib.path import Path as MplPath
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


def export_raw_rasters(medan_union) -> Dict[str, Any]:
    overlays: Dict[str, Any] = {}

    # 1. VIIRS 2024 Raw Raster PNG
    viirs_tif = os.path.join(DATA_DIR, "viirs_medan_2024.tif")
    ds = gdal.Open(viirs_tif)
    gt = ds.GetGeoTransform()
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    nodata = ds.GetRasterBand(1).GetNoDataValue()
    ds = None
    h, w = arr.shape
    mask = build_medan_mask(gt, w, h, medan_union)
    valid = arr if nodata is None else np.where(arr == nodata, 0.0, arr)

    # Color stops in palette: 0:#071B2B -> 25:#167D8D -> 55:#B9E4E8 -> 95+:#FFC94D
    stops = np.array([0.0, 22.0, 50.0, 85.0, 110.0])
    r_vals = np.array([7, 22, 185, 255, 255], dtype=np.float64)
    g_vals = np.array([27, 125, 228, 220, 201], dtype=np.float64)
    b_vals = np.array([43, 141, 232, 120, 77], dtype=np.float64)

    flat = np.clip(valid, 0.0, 110.0)
    rr = np.interp(flat, stops, r_vals).astype(np.uint8)
    gg = np.interp(flat, stops, g_vals).astype(np.uint8)
    bb = np.interp(flat, stops, b_vals).astype(np.uint8)
    aa = np.where(mask, 215, 0).astype(np.uint8)

    rgba = np.dstack([rr, gg, bb, aa])
    img_v = Image.fromarray(rgba, mode="RGBA").resize((w * 10, h * 10), Image.Resampling.NEAREST)
    viirs_png = os.path.join(WEB_DATA_DIR, "viirs_2024_raw.png")
    img_v.save(viirs_png)

    ulx, uly = gt[0], gt[3]
    lrx, lry = gt[0] + w * gt[1], gt[3] + h * gt[5]
    medan_vals = valid[mask]
    overlays["viirs"] = {
        "bounds": [[round(ulx, 6), round(uly, 6)], [round(lrx, 6), round(uly, 6)], [round(lrx, 6), round(lry, 6)], [round(ulx, 6), round(lry, 6)]],
        "dataUri": "data:image/png;base64," + base64.b64encode(open(viirs_png, "rb").read()).decode("ascii"),
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
    }
    log(f"Exported VIIRS raw raster PNG ({w}x{h} -> {w*10}x{h*10}) stats={overlays['viirs']['stats']['min']}..{overlays['viirs']['stats']['max']} DN")

    # 2. DEM SRTM 30m Shaded Relief PNG
    dem_tif = os.path.join(DATA_DIR, "dem_medan_srtm.tif")
    dds = gdal.Open(dem_tif)
    dgt = dds.GetGeoTransform()
    darr = dds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    dnodata = dds.GetRasterBand(1).GetNoDataValue()
    dds = None
    dh, dw = darr.shape
    dmask = build_medan_mask(dgt, dw, dh, medan_union)
    dvalid = np.where((darr == dnodata) | (darr < -10), 0.0, darr) if dnodata is not None else np.maximum(darr, 0.0)

    # Hillshade + Elevation ramp (#B9E4E8 low -> #167D8D mid -> #071B2B high)
    dy, dx = np.gradient(dvalid, 30.0, 30.0)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    az = np.radians(315.0)
    alt = np.radians(42.0)
    hs = np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0.15, 1.0)
    shade_factor = 0.62 + 0.52 * hs

    estops = np.array([0.0, 18.0, 42.0, 75.0])
    er = np.array([185, 22, 12, 7], dtype=np.float64)
    eg = np.array([228, 125, 72, 27], dtype=np.float64)
    eb = np.array([232, 141, 90, 43], dtype=np.float64)

    eflat = np.clip(dvalid, 0.0, 75.0)
    drr = np.clip(np.interp(eflat, estops, er) * shade_factor, 0, 255).astype(np.uint8)
    dgg = np.clip(np.interp(eflat, estops, eg) * shade_factor, 0, 255).astype(np.uint8)
    dbb = np.clip(np.interp(eflat, estops, eb) * shade_factor, 0, 255).astype(np.uint8)
    daa = np.where(dmask, 195, 0).astype(np.uint8)

    drgba = np.dstack([drr, dgg, dbb, daa])
    dem_png = os.path.join(WEB_DATA_DIR, "dem_srtm_raw.png")
    Image.fromarray(drgba, mode="RGBA").save(dem_png, optimize=True, compress_level=9)

    dulx, duly = dgt[0], dgt[3]
    dlrx, dlry = dgt[0] + dw * dgt[1], dgt[3] + dh * dgt[5]
    dem_medan_vals = dvalid[dmask]
    overlays["dem"] = {
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
    }
    log(f"Exported DEM SRTM raw raster PNG ({dw}x{dh}) elev={overlays['dem']['stats']['min_m']}..{overlays['dem']['stats']['max_m']} mdpl")

    bundle_out = os.path.join(WEB_DATA_DIR, "ra_overlays_bundle.js")
    with open(bundle_out, "w", encoding="utf-8") as fp:
        fp.write("window.MEDAN_RASTER_OVERLAYS = ")
        json.dump(overlays, fp, separators=(",", ":"))
        fp.write(";\n")
    log(f"Saved {os.path.relpath(bundle_out, BASE_DIR)} ({os.path.getsize(bundle_out) // 1024} KB)")
    return overlays


def main() -> None:
    # 1. Fetch 6 extra OSM tiles for Medan Kota, Medan Area, Medan Denai
    extra_tiles = []
    idx = 0
    for ix, x0 in enumerate([98.680, 98.688, 98.696]):
        for iy, y0 in enumerate([3.566, 3.576]):
            extra_tiles.append((idx, x0, y0, x0 + 0.008, y0 + 0.010))
            idx += 1

    log(f"Fetching/loading {len(extra_tiles)} extra OSM tiles for Medan Kota, Area & Denai ...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(fetch_extra_tile, extra_tiles))

    # 2. Load base datasets
    kec_fc = json.load(open(os.path.join(DATA_DIR, "batas_kecamatan_medan.geojson"), encoding="utf-8"))
    kec_shapes = [(f["properties"]["nama_kec"], shape(f["geometry"])) for f in kec_fc["features"]]
    kec_utm_shapes = [(kn, transform(TO_UTM, kg)) for kn, kg in kec_shapes]
    kec_tree = STRtree([kg for _, kg in kec_utm_shapes])
    medan_union = unary_union([kg for _, kg in kec_shapes])
    medan_utm = transform(TO_UTM, medan_union)

    police_fc = json.load(open(os.path.join(DATA_DIR, "polisi_eksisting.geojson"), encoding="utf-8"))
    existing_police_feats = []
    seen_pol_pts = []
    for pf in police_fc["features"]:
        pt_u = transform(TO_UTM, shape(pf["geometry"]))
        if any(pt_u.distance(ep) < 120.0 for ep in seen_pol_pts):
            continue
        seen_pol_pts.append(pt_u)
        existing_police_feats.append(pf)

    extra_police_specs = [
        ("Polsek Medan Tuntungan", "Polsek", 98.6138, 3.5165, "Jl. Jamin Ginting Km 11, Medan Tuntungan"),
        ("Polsek Deli Tua / Wilkum Medan Johor", "Polsek", 98.6805, 3.4955, "Jl. Besar Deli Tua, Perbatasan Medan Johor"),
        ("Polsek Medan Area / Denai", "Polsek", 98.7042, 3.5756, "Jl. Semeru / Koridor Medan Area - Denai"),
        ("Polres Pelabuhan Belawan", "Polres", 98.6835, 3.7765, "Jl. Raya Pelabuhan Bagan Deli, Medan Belawan"),
        ("Pos Polisi Simpang Pemda Tuntungan", "Pos Polisi", 98.6245, 3.5412, "Simpang Pemda / Ring Road Selatan, Medan Tuntungan"),
        ("Pos Polisi Aksara / Tembung", "Pos Polisi", 98.7124, 3.5978, "Simpang Aksara / Jl. Letda Sujono, Medan Tembung"),
        ("Pos Polisi Titi Papan Marelan/Deli", "Pos Polisi", 98.6682, 3.6965, "Simpang Titi Papan / Jl. K.L. Yos Sudarso, Medan Deli"),
    ]
    for pname, pjenis, plon, plat, palamat in extra_police_specs:
        pt_w = Point(plon, plat)
        pt_u = transform(TO_UTM, pt_w)
        if any(pt_u.distance(ep) < 150.0 for ep in seen_pol_pts):
            continue
        kec_p = "Sekitar Kota Medan"
        for kn, kg in kec_shapes:
            if kg.contains(pt_w):
                kec_p = kn
                break
        seen_pol_pts.append(pt_u)
        existing_police_feats.append({
            "type": "Feature",
            "properties": {
                "nama": pname,
                "jenis": pjenis,
                "kecamatan": kec_p,
                "alamat": palamat,
                "sumber": "Direktori Polrestabes Medan & Polres Pelabuhan Belawan",
            },
            "geometry": {"type": "Point", "coordinates": [round(plon, 6), round(plat, 6)]},
        })

    police_fc["features"] = existing_police_feats
    save_geojson(os.path.join(DATA_DIR, "polisi_eksisting.geojson"), police_fc["features"])
    police_utm = [transform(TO_UTM, shape(f["geometry"])) for f in police_fc["features"]]
    police_tree = STRtree(police_utm)

    corridor_fc = json.load(open(os.path.join(DATA_DIR, "koridor_rawan_begal.geojson"), encoding="utf-8"))
    viirs_sampler_pre = RasterSampler(os.path.join(DATA_DIR, "viirs_medan_2024.tif"))

    extra_corridors_specs = [
        ("Jl. K.L. Yos Sudarso Km 15-20 (Belawan)", "Medan Belawan", "Akses Pelabuhan & Arteri Kontainer Minim PJU Malam", "Sangat Tinggi", [[98.6785, 3.7430], [98.6812, 3.7580], [98.6848, 3.7745], [98.6895, 3.7840]], "Pengawasan Polres Pelabuhan Belawan pada akses angkutan barang dan simpang Kampung Salam-Bagan Deli."),
        ("Jl. K.L. Yos Sudarso Km 9-14 (Martubung - Pekan Labuhan)", "Medan Labuhan", "Koridor Panjang Penghubung Utara & Zona Gelap Bantaran", "Sangat Tinggi", [[98.6725, 3.6860], [98.6778, 3.7050], [98.6795, 3.7245], [98.6785, 3.7410]], "Patroli gabungan Polsek Medan Labuhan & Polres Pelabuhan Belawan pada segmen minim lampu Martubung."),
        ("Jl. Marelan Raya & Jl. Platina Raya", "Medan Marelan", "Jalur Permukiman Padat & Perbatasan Sungai Deli", "Tinggi", [[98.6660, 3.6940], [98.6565, 3.7025], [98.6490, 3.7135], [98.6450, 3.7240]], "Ruas rawan tawuran dan curas pengendara sepeda motor pada malam hingga subuh di Medan Marelan."),
        ("Jl. Rumah Potong Hewan (RPH) & Akses KIM Mabar", "Medan Deli", "Kawasan Industri KIM Mabar & Pergudangan Gelap", "Tinggi", [[98.6685, 3.6610], [98.6770, 3.6695], [98.6875, 3.6765], [98.6950, 3.6810]], "Koridor truk dan pekerja shift malam sekitar KIM II Mabar dengan tingkat penerangan rendah."),
        ("Jl. Kapten Sumarsono & Jl. Asrama Helvetia", "Medan Helvetia", "Arteri Barat-Utara Dekat Eks Bandara & Asrama", "Tinggi", [[98.6265, 3.6065], [98.6365, 3.6115], [98.6480, 3.6175], [98.6575, 3.6215]], "Jalur penghubung Helvetia-Sunggal dalam sasaran KRYD Polrestabes Medan untuk antisipasi geng motor."),
        ("Jl. Jamin Ginting Km 9-12 & Jl. Flamboyan Raya", "Medan Tuntungan", "Koridor Selatan Berkontur & Rimbun Pepohonan", "Sangat Tinggi", [[98.6395, 3.5390], [98.6245, 3.5295], [98.6130, 3.5175], [98.6065, 3.5040]], "Ruas selatan menuju Pancur Batu dengan jarak terjauh dari Polsek inti dan defisit cahaya VIIRS."),
        ("Jl. Sisingamangaraja Km 6-9 & Flyover Amplas", "Medan Amplas", "Gerbang Tol & Terminal Amplas Rawan Begal Subuh", "Tinggi", [[98.7005, 3.5565], [98.7085, 3.5450], [98.7155, 3.5365], [98.7220, 3.5310]], "Titik persinggahan lintas timur dan pelintas dini hari sekitar Flyover dan Terminal Terpadu Amplas."),
        ("Jl. Panglima Denai & Jl. Menteng VII", "Medan Denai", "Koridor Tenggara Sepi Selepas Tengah Malam", "Tinggi", [[98.7145, 3.5815], [98.7175, 3.5695], [98.7215, 3.5585], [98.7260, 3.5495]], "Segmen perbatasan Medan Denai-Amplas dengan banyak simpang kecil gelap rawan pencegatan malam."),
        ("Jl. Letda Sujono & Jl. Willem Iskandar (Pancing)", "Medan Tembung", "Akses Tol Bandar Selamat & Koridor Pancing", "Tinggi", [[98.7065, 3.6025], [98.7165, 3.5995], [98.7275, 3.5975], [98.7365, 3.5960]], "Jalur keluar-masuk kota sisi timur dengan intensitas begal malam dekat aksara-tol Bandar Selamat."),
        ("Jl. Brigjen Katamso & Bantaran Sungai Deli", "Medan Maimun / Medan Kota", "Koridor Tepi Sungai & Persimpangan Pusat-Selatan", "Tinggi", [[98.6835, 3.5795], [98.6860, 3.5695], [98.6890, 3.5595], [98.6935, 3.5510]], "Koridor lintas Medan Maimun dan Medan Kota dengan blindspot di bawah pohon dan akses jembatan."),
        ("Jl. Imam Bonjol & Koridor Bandara Lama Polonia", "Medan Polonia", "Perimeter Sepi Eks Bandara Polonia (Defisit VIIRS)", "Sangat Tinggi", [[98.6730, 3.5790], [98.6705, 3.5690], [98.6685, 3.5590], [98.6745, 3.5535]], "Area terbuka landasan eks Polonia yang tampak gelap pada citra satelit malam VIIRS 2024."),
    ]
    existing_corr_names = {cf["properties"]["nama_jalan"] for cf in corridor_fc["features"]}
    for cname, kec_lbl, jenis_k, bahaya, raw_coords, rilis_msg in extra_corridors_specs:
        if cname in existing_corr_names:
            continue
        ls = LineString(raw_coords)
        ls_utm = transform(TO_UTM, ls)
        v_samples = []
        for frac in np.linspace(0.0, 1.0, 9):
            pt_s = ls.interpolate(float(frac), normalized=True)
            v_samples.append(viirs_sampler_pre.sample_point(pt_s.x, pt_s.y))
        corridor_fc["features"].append({
            "type": "Feature",
            "properties": {
                "nama_jalan": cname,
                "kecamatan": kec_lbl,
                "jenis_kerawanan": jenis_k,
                "tingkat_bahaya": bahaya,
                "viirs_mean": round(float(np.mean(v_samples)), 2),
                "viirs_min": round(float(np.min(v_samples)), 2),
                "panjang_km": round(ls_utm.length / 1000.0, 2),
                "sumber_data": "Rilis Pemetaan Polrestabes Medan & Analisis VIIRS V2.1 2024",
                "bukti_rilis": rilis_msg,
            },
            "geometry": {"type": "LineString", "coordinates": raw_coords},
        })

    corridor_utm = [transform(TO_UTM, shape(f["geometry"])) for f in corridor_fc["features"]]
    corridor_tree = STRtree(corridor_utm)

    # Enrich corridors with real Polrestabes release details & center coords
    rilis_details = {
        "Jl. Gatot Subroto": "Rilis Patroli KRYD Polrestabes Medan: koridor protokol perbatasan Petisah-Sunggal rawan curas dan balap liar malam (22.00-05.00 WIB).",
        "Jl. Sriwijaya": "Masuk daftar pengawasan prioritas Polsek Medan Baru & Polrestabes Medan karena segmen sepi dan blindspot pepohonan.",
        "Jl. Sei Serayu": "Jalur penghubung pemukiman Medan Baru-Sunggal yang kerap menjadi lokasi pengintaian pelaku curas malam hari.",
        "Jl. Gajah Mada": "Koridor penghubung Medan Baru-Petisah dengan titik gelap persimpangan sekunder di luar jam ramai toko.",
        "Jl. S. Parman": "Ruas protokol menuju Polonia/Sudirman dengan pengawasan KRYD pada segmen gelap dekat persimpangan.",
        "Jl. Iskandar Muda": "Koridor aktivitas niaga malam Medan Baru-Petisah; rawan curanmor dan curas saat lalu lintas menurun tengah malam.",
        "Jl. Jamin Ginting": "Koridor utama Padang Bulan-USU-Tuntungan dengan volume sepeda motor tinggi hingga dini hari; target patroli Tim URC.",
        "Jl. Jend. Sudirman": "Area sekitar Taman Beringin dan persimpangan Sudirman tercatat pada patroli antisipasi geng motor & begal Polrestabes Medan.",
        "Jl. Gagak Hitam (Ring Road)": "Koridor lingkar luar Medan Sunggal-Selayang berkecepatan tinggi dengan beberapa segmen PJU redup rawan begal.",
        "Jl. Ngumban Surbakti": "Terusan Ring Road Selatan dengan jarak cukup jauh (>1.5 km) dari Polsek terdekat; fokus patroli gabungan.",
        "Jl. Yos Sudarso": "Koridor utara Medan Barat (Glugur-Pulo Brayan) dalam daftar rilis Polrestabes Medan untuk pengawasan curas truk & pengendara malam.",
        "Jl. Sutrisno": "Wilayah hukum Polsek Medan Area; tercatat dalam evaluasi Polrestabes Medan untuk kerawanan curas dan curat malam.",
        "Jl. Perintis Kemerdekaan": "Koridor Medan Timur-Perjuangan dalam daftar pengawasan KRYD Polrestabes Medan pada jalur lintas stasiun dan kampus.",
    }
    for cf in corridor_fc["features"]:
        g = shape(cf["geometry"])
        rep = g.interpolate(0.5, normalized=True) if isinstance(g, LineString) else g.geoms[0].interpolate(0.5, normalized=True)
        cf["properties"]["lon"] = round(rep.x, 6)
        cf["properties"]["lat"] = round(rep.y, 6)
        cf["properties"]["jam_rawan"] = "22:00 - 05:00 WIB"
        cf["properties"]["bukti_rilis"] = rilis_details.get(
            cf["properties"]["nama_jalan"],
            cf["properties"].get("bukti_rilis") or "Ruas rawan dalam rilis pengawasan KRYD & Satgas Anti-Begal Polrestabes Medan.",
        )
    save_geojson(os.path.join(DATA_DIR, "koridor_rawan_begal.geojson"), corridor_fc["features"])

    # 3. Export raw VIIRS & DEM raster PNG overlays
    export_raw_rasters(medan_union)

    # 4. Merge ALL OSM cached tiles
    nodes: Dict[int, Tuple[float, float]] = {}
    ways: Dict[int, Dict[str, Any]] = {}
    tile_files = sorted(glob.glob(os.path.join(RAW_OSM_DIR, "osm_tile_*.json")))
    log(f"Loading {len(tile_files)} cached OSM tile files ...")
    for tf in tile_files:
        d = json.load(open(tf, encoding="utf-8"))
        for el in d.get("elements", []):
            if el["type"] == "node":
                nodes[el["id"]] = (el["lon"], el["lat"])
            elif el["type"] == "way":
                ways[el["id"]] = el
    log(f"Total merged OSM cache: {len(nodes)} nodes, {len(ways)} ways")

    viirs_sampler = RasterSampler(os.path.join(DATA_DIR, "viirs_medan_2024.tif"))
    dem_sampler = RasterSampler(os.path.join(DATA_DIR, "dem_medan_srtm.tif"))

    # 5. Rebuild PJU/CCTV/Pos Pantau solutions algorithmically across ALL 21 Kecamatan (7..22 units each)
    hex_fc = json.load(open(os.path.join(DATA_DIR, "hex_viirs_medan_500m.geojson"), encoding="utf-8"))
    pju_features = []
    pju_utm_pts = []
    kec_pju_count: Dict[str, int] = {kn: 0 for kn, _ in kec_shapes}
    next_pju_num = 1

    def resolve_kec_name(pt_w: Point, fallback: str = "Kota Medan") -> str:
        for kn, kg in kec_shapes:
            if kg.contains(pt_w):
                return kn
        return fallback

    def try_place_pju(pt_w: Point, pt_u: Point, lokasi: str, kn: str, min_sep_m: float, max_per_kec: int) -> bool:
        nonlocal next_pju_num
        if kn not in kec_pju_count or kec_pju_count[kn] >= max_per_kec:
            return False
        if any(pt_u.distance(pu) < min_sep_m for pu, _, _ in pju_utm_pts):
            return False
        v_here = viirs_sampler.sample_point(pt_w.x, pt_w.y)
        d_pol = pt_u.distance(police_utm[police_tree.nearest(pt_u)])
        pid = f"PJU-{next_pju_num:03d}"
        if d_pol > 1250.0 and next_pju_num % 4 == 1:
            jenis, rad, prio = "Pos Pantau & Panic Button + CCTV", 210, "Prioritas 1 - Kritis"
        elif v_here <= 38.0 or next_pju_num % 2 == 0:
            jenis, rad, prio = "CCTV Analitik + PJU Pintar Terpadu", 185, "Prioritas 1 - Kritis"
        else:
            jenis, rad, prio = "PJU Pintar LED Solar + Sensor Gerak", 165, "Prioritas 2 - Tinggi"

        pju_utm_pts.append((pt_u, float(rad), pid))
        pju_features.append({
            "type": "Feature",
            "properties": {
                "id_unit": pid,
                "jenis_solusi": jenis,
                "nama_lokasi": lokasi,
                "kecamatan": kn,
                "viirs_awal": round(v_here, 2),
                "radius_terang_m": rad,
                "prioritas": prio,
                "gedung_terlindungi": 0,
            },
            "geometry": {"type": "Point", "coordinates": [round(pt_w.x, 6), round(pt_w.y, 6)]},
        })
        kec_pju_count[kn] += 1
        next_pju_num += 1
        return True

    focus_dense_kecs = {"Medan Baru", "Medan Petisah", "Medan Polonia", "Medan Area", "Medan Kota", "Medan Sunggal", "Medan Selayang"}
    # Pass 5a: Seed solutions along all 24 night-crime corridors across Kota Medan
    for cf in corridor_fc["features"]:
        cname = cf["properties"]["nama_jalan"]
        geom = shape(cf["geometry"])
        segs = [geom] if isinstance(geom, LineString) else list(geom.geoms)
        for seg in segs:
            seg_u = transform(TO_UTM, seg)
            d = 140.0
            while d < seg_u.length:
                pt_u = seg_u.interpolate(d)
                pt_w = transform(TO_WGS, pt_u)
                if medan_union.contains(pt_w):
                    kn = resolve_kec_name(pt_w, "")
                    if kn:
                        is_core = kn in {"Medan Baru", "Medan Petisah"}
                        min_sep = 250.0 if is_core else 360.0
                        cap_corr = 15 if is_core else 8
                        try_place_pju(pt_w, pt_u, f"Segmen {cname}", kn, min_sep, cap_corr)
                d += 320.0

    # Pass 5b: Fill EVERY one of the 21 Kecamatan using darkest/highest-risk hexes + interior grid
    hex_by_kec: Dict[str, List[Dict[str, Any]]] = {kn: [] for kn, _ in kec_shapes}
    for hf in hex_fc["features"]:
        kn = hf["properties"].get("kecamatan")
        if kn in hex_by_kec:
            hex_by_kec[kn].append(hf)

    for kn, kg in kec_shapes:
        target_min = 19 if kn == "Medan Baru" else (17 if kn == "Medan Petisah" else (11 if kn in focus_dense_kecs else 9))
        if kec_pju_count[kn] >= target_min:
            continue
        sorted_hex = sorted(
            hex_by_kec[kn],
            key=lambda h: (-float(h["properties"].get("risk_score", 0)), float(h["properties"].get("viirs_mean", 100))),
        )
        cands: List[Tuple[Point, str]] = []
        for hf in sorted_hex:
            rp = shape(hf["geometry"]).representative_point()
            if kg.contains(rp):
                cands.append((rp, f"Zona Gelap {hf['properties']['hex_id']} ({kn})"))
        minx, miny, maxx, maxy = kg.bounds
        grid_pts = []
        for gx in np.linspace(minx + 0.002, maxx - 0.002, 7):
            for gy in np.linspace(miny + 0.002, maxy - 0.002, 7):
                pt = Point(float(gx), float(gy))
                if kg.contains(pt):
                    grid_pts.append((viirs_sampler.sample_point(pt.x, pt.y), pt))
        grid_pts.sort(key=lambda item: item[0])
        for v_pt, pt in grid_pts:
            cands.append((pt, f"Titik Gelap {kn} (VIIRS {v_pt:.1f} DN)"))

        for sep_try in (320.0, 220.0, 140.0):
            if kec_pju_count[kn] >= target_min:
                break
            for pt_w, lbl in cands:
                if kec_pju_count[kn] >= target_min:
                    break
                try_place_pju(pt_w, transform(TO_UTM, pt_w), lbl, kn, sep_try, 22)

    log(f"Citywide PJU placement across {len(kec_pju_count)} kecamatan: total={len(pju_features)}, min_per_kec={min(kec_pju_count.values())}, max_per_kec={max(kec_pju_count.values())}")
    pju_tree = STRtree([pt for pt, _, _ in pju_utm_pts])

    # 6. Process ALL closed building polygons across Kota Medan inside merged OSM tiles
    log("Processing ALL cached OSM buildings across Kota Medan ...")
    buildings_raw = []
    for wid, w in ways.items():
        tags = w.get("tags", {})
        if "building" not in tags:
            continue
        nds = w.get("nodes", [])
        if len(nds) < 4 or nds[0] != nds[-1]:
            continue
        coords = [nodes[n] for n in nds if n in nodes]
        if len(coords) < 4:
            continue
        try:
            poly = Polygon(coords)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty or not isinstance(poly, Polygon):
                continue
        except Exception:
            continue

        cent = poly.centroid
        if not medan_union.contains(cent):
            continue

        poly_utm = transform(TO_UTM, poly)
        area_m2 = poly_utm.area
        if area_m2 < 16.0:
            continue

        cent_utm = poly_utm.centroid
        # Fast kecamatan lookup via STRtree
        cand_idxs = kec_tree.query(cent_utm)
        kec_b = "Kota Medan"
        for ci in cand_idxs:
            if kec_utm_shapes[ci][1].contains(cent_utm):
                kec_b = kec_utm_shapes[ci][0]
                break

        height_m, h_source = smart_building_height(tags, area_m2)
        v_val = viirs_sampler.sample_point(cent.x, cent.y)
        e_val = dem_sampler.sample_point(cent.x, cent.y)

        near_pol_idx = police_tree.nearest(cent_utm)
        dist_pol = cent_utm.distance(police_utm[near_pol_idx])
        near_kor_idx = corridor_tree.nearest(cent_utm)
        dist_kor = cent_utm.distance(corridor_utm[near_kor_idx])
        near_pju_idx = pju_tree.nearest(cent_utm)
        pju_pt, pju_rad, pju_id = pju_utm_pts[near_pju_idx]
        dist_pju = cent_utm.distance(pju_pt)

        buildings_raw.append({
            "osm_id": wid,
            "nama": tags.get("name", ""),
            "building": str(tags.get("building", "yes")),
            "kecamatan": kec_b,
            "lon": round(cent.x, 6),
            "lat": round(cent.y, 6),
            "area_m2": round(area_m2, 1),
            "height_m": height_m,
            "height_src": h_source,
            "viirs_rad": round(v_val, 2),
            "elev_m": round(e_val, 1),
            "dist_polisi_m": round(dist_pol, 0),
            "dist_koridor_m": round(dist_kor, 0),
            "nearest_pju_id": pju_id,
            "dist_pju_m": round(dist_pju, 0),
            "terlindungi_solusi": 1 if dist_pju <= pju_rad else 0,
            "poly_wgs": poly,
        })

    b_viirs = np.array([b["viirs_rad"] for b in buildings_raw], dtype=float)
    v_q30 = float(np.percentile(b_viirs, 30)) if len(b_viirs) else 25.0

    pju_counts = {pid: 0 for _, _, pid in pju_utm_pts}
    building_features = []
    kec_counts: Dict[str, int] = {}

    for b in buildings_raw:
        dark_comp = max(0.0, min(1.0, (55.0 - b["viirs_rad"]) / 45.0))
        kor_comp = max(0.0, min(1.0, 1.0 - (b["dist_koridor_m"] / 600.0)))
        pol_comp = max(0.0, min(1.0, b["dist_polisi_m"] / 2200.0))
        v_score = round(100.0 * (0.45 * dark_comp + 0.35 * kor_comp + 0.20 * pol_comp), 1)

        if v_score >= 56.0 or (b["viirs_rad"] <= v_q30 and b["dist_koridor_m"] <= 350.0):
            status = "Tinggi"
        elif v_score >= 38.0:
            status = "Sedang"
        else:
            status = "Rendah"

        if b["terlindungi_solusi"] == 1:
            pju_counts[b["nearest_pju_id"]] = pju_counts.get(b["nearest_pju_id"], 0) + 1

        kec_counts[b["kecamatan"]] = kec_counts.get(b["kecamatan"], 0) + 1

        building_features.append({
            "type": "Feature",
            "properties": {
                "osm_id": b["osm_id"],
                "nama": b["nama"],
                "building": b["building"],
                "kecamatan": b["kecamatan"],
                "lon": b["lon"],
                "lat": b["lat"],
                "area_m2": b["area_m2"],
                "height_m": b["height_m"],
                "height_src": b["height_src"],
                "viirs_rad": b["viirs_rad"],
                "elev_m": b["elev_m"],
                "dist_polisi_m": b["dist_polisi_m"],
                "dist_koridor_m": b["dist_koridor_m"],
                "vuln_score": v_score,
                "status_rawan": status,
                "terlindungi_solusi": b["terlindungi_solusi"],
                "nearest_pju_id": b["nearest_pju_id"],
                "dist_pju_m": b["dist_pju_m"],
            },
            "geometry": mapping(b["poly_wgs"]),
        })

    for pf in pju_features:
        pf["properties"]["gedung_terlindungi"] = pju_counts.get(pf["properties"]["id_unit"], 0)

    # 6.5 Expand Citywide Patrol Routes (7 Sectors across all 21 Kecamatan via OSRM with fallback)
    def osrm_route_resilient(waypoints: List[Tuple[float, float]]) -> List[List[float]]:
        coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in waypoints)
        url = f"https://router.project-osrm.org/route/v1/driving/{coord_str}?overview=full&geometries=geojson"
        for attempt in range(2):
            try:
                r = requests.get(url, headers=HEADERS, timeout=8)
                if r.status_code == 200:
                    j = r.json()
                    if j.get("routes"):
                        return j["routes"][0]["geometry"]["coordinates"]
            except Exception:
                pass
            time.sleep(0.5 * (attempt + 1))
        return [[round(lon, 6), round(lat, 6)] for lon, lat in waypoints]

    patrol_defs = [
        {
            "nama_rute": "Rute Patroli A — Sektor Inti (Medan Baru, Medan Petisah & Medan Polonia)",
            "unit_pelaksana": "Tim URC Polsek Medan Baru & Satgas Anti-Begal",
            "jam_patroli": "22:00 - 05:00 WIB (Interval 45 Menit)",
            "koridor_dilalui": "Jl. Ibus Raya - Jl. Gatot Subroto - Jl. Sei Serayu - Jl. Dr. Mansyur - Jl. Imam Bonjol - Jl. Sriwijaya - Jl. Gajah Mada",
            "waypoints": [(98.6653, 3.5902), (98.6520, 3.5919), (98.6455, 3.5778), (98.6545, 3.5635), (98.6705, 3.5690), (98.6615, 3.5795), (98.6644, 3.5844), (98.6653, 3.5902)],
        },
        {
            "nama_rute": "Rute Patroli B — Sektor Pusat & Timur (Kota, Maimun, Area, Timur & Perjuangan)",
            "unit_pelaksana": "Satgas KRYD Polrestabes Medan & Polsek Timur/Kota/Area",
            "jam_patroli": "21:30 - 04:30 WIB (Interval 60 Menit)",
            "koridor_dilalui": "Polrestabes (Jl. HM Said) - Jl. Perintis Kemerdekaan - Jl. Sutrisno - Jl. Brigjen Katamso - Jl. S. Parman",
            "waypoints": [(98.6839, 3.6003), (98.6855, 3.5988), (98.6972, 3.5819), (98.6931, 3.5653), (98.6860, 3.5695), (98.6672, 3.5784), (98.6839, 3.6003)],
        },
        {
            "nama_rute": "Rute Patroli C — Sektor Barat & Ring Road (Barat, Helvetia, Sunggal & Selayang)",
            "unit_pelaksana": "Patroli Gabungan Polsek Sunggal, Helvetia & Medan Barat",
            "jam_patroli": "22:00 - 05:00 WIB (Interval 60 Menit)",
            "koridor_dilalui": "Polsek Medan Barat - Jl. Kapten Sumarsono - Jl. Gagak Hitam (Ring Road) - Jl. Ngumban Surbakti - Jl. Jamin Ginting",
            "waypoints": [(98.6712, 3.6223), (98.6349, 3.6104), (98.6270, 3.5880), (98.6345, 3.5530), (98.6617, 3.5598), (98.6653, 3.5902), (98.6712, 3.6223)],
        },
        {
            "nama_rute": "Rute Patroli D — Sektor Tenggara (Medan Denai, Medan Tembung & Aksara)",
            "unit_pelaksana": "Patroli KRYD Polsek Percut Sei Tuan & Polsek Medan Area",
            "jam_patroli": "22:00 - 04:30 WIB (Interval 60 Menit)",
            "koridor_dilalui": "Pos Aksara - Jl. Letda Sujono - Jl. Willem Iskandar (Pancing) - Jl. Panglima Denai - Jl. Menteng VII",
            "waypoints": [(98.7124, 3.5978), (98.7275, 3.5975), (98.7145, 3.5815), (98.7215, 3.5585), (98.7042, 3.5756), (98.7124, 3.5978)],
        },
        {
            "nama_rute": "Rute Patroli E — Sektor Selatan & Perbukitan (Tuntungan, Johor & Amplas)",
            "unit_pelaksana": "Patroli Sektor Selatan Polsek Medan Tuntungan, Deli Tua & Patumbak",
            "jam_patroli": "21:30 - 05:00 WIB (Interval 60 Menit)",
            "koridor_dilalui": "Simpang Pemda - Jl. Jamin Ginting Km 11 - Jl. Flamboyan Raya - Jl. A.H. Nasution - Flyover Amplas",
            "waypoints": [(98.6245, 3.5412), (98.6138, 3.5165), (98.6065, 3.5040), (98.6805, 3.4955), (98.7155, 3.5365), (98.6780, 3.5440), (98.6245, 3.5412)],
        },
        {
            "nama_rute": "Rute Patroli F — Sektor Tengah-Utara & Industri (Medan Deli, Pulo Brayan & Martubung)",
            "unit_pelaksana": "Tim Sabhara Polrestabes Medan & Polsek Medan Labuhan (Sektor KIM Mabar)",
            "jam_patroli": "22:00 - 05:00 WIB (Interval 60 Menit)",
            "koridor_dilalui": "Jl. Yos Sudarso Brayan - Jl. Rumah Potong Hewan - Kawasan Industri KIM II Mabar - Martubung",
            "waypoints": [(98.6694, 3.6286), (98.6685, 3.6610), (98.6875, 3.6765), (98.6778, 3.7050), (98.6682, 3.6965), (98.6694, 3.6286)],
        },
        {
            "nama_rute": "Rute Patroli G — Sektor Pesisir Utara (Medan Marelan, Labuhan & Belawan)",
            "unit_pelaksana": "Tim URC Polres Pelabuhan Belawan & Polsek Medan Labuhan",
            "jam_patroli": "21:30 - 05:00 WIB (Interval 45 Menit)",
            "koridor_dilalui": "Titi Papan - Jl. Marelan Raya - Jl. Platina Raya - Jl. K.L. Yos Sudarso (Labuhan - Pelabuhan Belawan)",
            "waypoints": [(98.6682, 3.6965), (98.6565, 3.7025), (98.6450, 3.7240), (98.6795, 3.7245), (98.6835, 3.7765), (98.6785, 3.7430), (98.6682, 3.6965)],
        },
    ]

    patrol_features = []
    for pdef in patrol_defs:
        coords = osrm_route_resilient(pdef["waypoints"])
        ls = LineString(coords)
        len_km = round(transform(TO_UTM, ls).length / 1000.0, 2)
        patrol_features.append({
            "type": "Feature",
            "properties": {
                "nama_rute": pdef["nama_rute"],
                "unit_pelaksana": pdef["unit_pelaksana"],
                "jam_patroli": pdef["jam_patroli"],
                "koridor_dilalui": pdef["koridor_dilalui"],
                "panjang_km": len_km,
            },
            "geometry": mapping(ls),
        })
    save_geojson(os.path.join(DATA_DIR, "solusi_rute_patroli.geojson"), patrol_features)

    for kf in kec_fc["features"]:
        kname = kf["properties"]["nama_kec"]
        kf["properties"]["jumlah_gedung"] = kec_counts.get(kname, 0)
        kf["properties"]["jumlah_pju_solusi"] = sum(1 for p in pju_features if p["properties"]["kecamatan"] == kname)

    save_geojson(os.path.join(DATA_DIR, "bangunan_fokus_3d.geojson"), building_features)
    save_geojson(os.path.join(DATA_DIR, "solusi_pju_cctv.geojson"), pju_features)
    save_geojson(os.path.join(DATA_DIR, "batas_kecamatan_medan.geojson"), kec_fc["features"])

    # 7. Rebuild WebGIS data copies & spatial_bundle.js
    web_layers = [
        "batas_kecamatan_medan.geojson",
        "hex_viirs_medan_500m.geojson",
        "bangunan_fokus_3d.geojson",
        "koridor_rawan_begal.geojson",
        "solusi_pju_cctv.geojson",
        "solusi_rute_patroli.geojson",
        "polisi_eksisting.geojson",
        "sungai_fokus_osm.geojson",
    ]
    bundle = {}
    for fname in web_layers:
        src = os.path.join(DATA_DIR, fname)
        dst = os.path.join(WEB_DATA_DIR, fname)
        shutil.copy2(src, dst)
        if fname == "bangunan_fokus_3d.geojson":
            continue
        with open(src, encoding="utf-8") as fp:
            bundle[fname.replace(".geojson", "")] = json.load(fp)

    # Compact delta-tabular encoding for 73,021 buildings inside spatial_bundle.js (~4.5x smaller)
    kecs_lut = sorted({f["properties"]["kecamatan"] for f in building_features})
    btypes_lut = sorted({f["properties"]["building"] for f in building_features})
    hsrcs_lut = sorted({f["properties"]["height_src"] for f in building_features})
    stat_lut = ["Rendah", "Sedang", "Tinggi"]
    k_idx = {v: i for i, v in enumerate(kecs_lut)}
    b_idx = {v: i for i, v in enumerate(btypes_lut)}
    h_idx = {v: i for i, v in enumerate(hsrcs_lut)}
    s_idx = {v: i for i, v in enumerate(stat_lut)}
    b_rows = []
    for f in building_features:
        p = f["properties"]
        lon0 = int(round(float(p["lon"]) * 100000))
        lat0 = int(round(float(p["lat"]) * 100000))
        ring = f["geometry"]["coordinates"][0]
        dring = []
        for c in ring[:-1]:
            dring.append(int(round(float(c[0]) * 100000)) - lon0)
            dring.append(int(round(float(c[1]) * 100000)) - lat0)
        pid_raw = p["nearest_pju_id"]
        pid_num = int(pid_raw.split("-")[1]) if "-" in str(pid_raw) else 0
        b_rows.append([
            p["osm_id"], p["nama"], b_idx[p["building"]], k_idx[p["kecamatan"]],
            lon0, lat0, int(round(float(p["area_m2"]))), p["height_m"],
            h_idx[p["height_src"]], int(round(float(p["viirs_rad"]) * 100)), int(round(float(p["elev_m"]))),
            int(p["dist_polisi_m"]), int(p["dist_koridor_m"]), int(round(float(p["vuln_score"]) * 10)),
            s_idx[p["status_rawan"]], p["terlindungi_solusi"], pid_num, int(p["dist_pju_m"]), dring
        ])
    bundle["__buildings_packed"] = {
        "kecs": kecs_lut, "btypes": btypes_lut, "hsrcs": hsrcs_lut, "statuses": stat_lut, "rows": b_rows
    }

    unpack_js = (
        "(function(D){var p=D.__buildings_packed;if(!p)return;"
        "var K=p.kecs,B=p.btypes,H=p.hsrcs,S=p.statuses,R=p.rows,n=R.length,feats=new Array(n);"
        "for(var i=0;i<n;i++){var r=R[i],x0=r[4],y0=r[5],d=r[18],m=d.length,ring=new Array(m/2+1),k=0;"
        "for(var j=0;j<m;j+=2){ring[k++]=[(x0+d[j])/1e5,(y0+d[j+1])/1e5];}"
        "ring[k]=[ring[0][0],ring[0][1]];var pid=r[16];"
        "feats[i]={type:\"Feature\",properties:{osm_id:r[0],nama:r[1],building:B[r[2]],kecamatan:K[r[3]],"
        "lon:x0/1e5,lat:y0/1e5,area_m2:r[6],height_m:r[7],height_src:H[r[8]],viirs_rad:r[9]/100,elev_m:r[10],"
        "dist_polisi_m:r[11],dist_koridor_m:r[12],vuln_score:r[13]/10,status_rawan:S[r[14]],terlindungi_solusi:r[15],"
        "nearest_pju_id:pid?(pid<10?\"PJU-00\"+pid:pid<100?\"PJU-0\"+pid:\"PJU-\"+pid):\"\",dist_pju_m:r[17]},"
        "geometry:{type:\"Polygon\",coordinates:[ring]}};}"
        "D.bangunan_fokus_3d={type:\"FeatureCollection\",features:feats};delete D.__buildings_packed;})(window.MEDAN_SPATIAL_DATA);\n"
    )

    bundle_js = os.path.join(WEB_DATA_DIR, "spatial_bundle.js")
    with open(bundle_js, "w", encoding="utf-8") as fp:
        fp.write("window.MEDAN_SPATIAL_DATA = ")
        json.dump(bundle, fp, separators=(",", ":"), ensure_ascii=False)
        fp.write(";\n")
        fp.write(unpack_js)

    high_b = sum(1 for b in building_features if b["properties"]["status_rawan"] == "Tinggi")
    prot_high_b = sum(1 for b in building_features if b["properties"]["status_rawan"] == "Tinggi" and b["properties"]["terlindungi_solusi"] == 1)
    log(f"DONE! Total buildings={len(building_features)} across {len(kec_counts)} kecamatan | High={high_b}, Protected={prot_high_b}, Unprotected={high_b - prot_high_b} | PJU={len(pju_features)} | Patrols={len(patrol_features)} | Police={len(police_fc['features'])} | Corridors={len(corridor_fc['features'])} | Bundle={os.path.getsize(bundle_js)//1024} KB")


if __name__ == "__main__":
    main()
