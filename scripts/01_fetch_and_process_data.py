import concurrent.futures
import csv
import json
import math
import os
import shutil
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
from osgeo import gdal, ogr
from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import linemerge, transform, unary_union

gdal.UseExceptions()

BASE_DIR = r"M:\Kuliah\Semester 5\SIG\Project Akhir"
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_OSM_DIR = os.path.join(DATA_DIR, "raw_osm")
WEB_DATA_DIR = os.path.join(BASE_DIR, "web-peta-interaktif", "data")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RAW_OSM_DIR, exist_ok=True)
os.makedirs(WEB_DATA_DIR, exist_ok=True)

MEDAN_KEC_SRC = r"M:\Kuliah\Semester 5\SIG\Pertemuan 12\WADM_KC_Sumatera_Utara_Kota_Medan.geojson"
DEM_SRC = r"M:\Kuliah\Semester 5\SIG\Dari Download\DEM SRTM 30M SUMUT.tif"
POP_CSV_SRC = r"M:\Kuliah\Semester 5\SIG\Pertemuan 11\Data_penduduk.csv"

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32647", always_xy=True).transform
TO_WGS = Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True).transform

HEADERS = {"User-Agent": "MedanDarkZoneSIG/1.0 (Academic GIS Project)"}


def log(msg: str) -> None:
    print(f"[01_DATA] {msg}", flush=True)


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


def load_population_csv() -> Dict[str, Dict[str, Any]]:
    pop_map = {}
    if os.path.exists(POP_CSV_SRC):
        with open(POP_CSV_SRC, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                k = row["NAMA_KEC"].strip().upper()
                pop_map[k] = {
                    "kode_kec": row["KODE_KEC"].strip(),
                    "penduduk_2024": int(row["PENDUDUK_2024"]),
                    "penduduk_2025": int(row["PENDUDUK_2025"]),
                }
    return pop_map


def clip_rasters(medan_bbox: Tuple[float, float, float, float]) -> Tuple[str, str, str]:
    minx, miny, maxx, maxy = medan_bbox
    pad = 0.015
    win = [minx - pad, maxy + pad, maxx + pad, miny - pad]  # [ulx, uly, lrx, lry]

    viirs_out = os.path.join(DATA_DIR, "viirs_medan_2024.tif")
    if not os.path.exists(viirs_out):
        log("Clipping EOG/OpenGeoHub VIIRS V2.1 2024 COG via /vsicurl/ ...")
        vsi_url = (
            "/vsicurl/https://zenodo.org/api/records/17294744/files/"
            "nightlights.average_viirs.v21_m_500m_s_20240101_20241231_go_epsg4326_v20250904.tif/content"
        )
        ds = gdal.Open(vsi_url)
        gdal.Translate(viirs_out, ds, projWin=win)
        ds = None
        log(f"Clipped VIIRS 2024 -> {viirs_out}")
    else:
        log("Using cached viirs_medan_2024.tif")

    nasa_out = os.path.join(DATA_DIR, "viirs_black_marble_nasa.tif")
    if not os.path.exists(nasa_out):
        log("Fetching NASA GIBS VIIRS_Black_Marble GeoTIFF ...")
        wms_url = (
            "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?"
            f"SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=VIIRS_Black_Marble&SRS=EPSG:4326"
            f"&BBOX={win[0]},{win[3]},{win[2]},{win[1]}&WIDTH=1024&HEIGHT=1800&FORMAT=image/tiff"
        )
        r = requests.get(wms_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        with open(nasa_out, "wb") as fp:
            fp.write(r.content)
        log(f"Saved NASA GIBS Black Marble -> {nasa_out}")

    dem_out = os.path.join(DATA_DIR, "dem_medan_srtm.tif")
    if not os.path.exists(dem_out):
        log("Clipping DEM SRTM 30m SUMUT to Kota Medan ...")
        ds_dem = gdal.Open(DEM_SRC)
        gdal.Translate(dem_out, ds_dem, projWin=win)
        ds_dem = None
        log(f"Clipped DEM SRTM 30m -> {dem_out}")
    else:
        log("Using cached dem_medan_srtm.tif")

    return viirs_out, nasa_out, dem_out


class RasterSampler:
    def __init__(self, tif_path: str):
        ds = gdal.Open(tif_path)
        self.gt = ds.GetGeoTransform()
        band = ds.GetRasterBand(1)
        self.arr = band.ReadAsArray().astype(np.float64)
        self.nodata = band.GetNoDataValue()
        self.h, self.w = self.arr.shape
        ds = None

    def sample_point(self, lon: float, lat: float) -> Optional[float]:
        col = int((lon - self.gt[0]) / self.gt[1])
        row = int((lat - self.gt[3]) / self.gt[5])
        if 0 <= row < self.h and 0 <= col < self.w:
            val = float(self.arr[row, col])
            if self.nodata is not None and val == self.nodata:
                return None
            return val
        return None

    def sample_polygon_stats(self, poly_geom) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        minx, miny, maxx, maxy = poly_geom.bounds
        c0 = max(0, int((minx - self.gt[0]) / self.gt[1]))
        c1 = min(self.w - 1, int((maxx - self.gt[0]) / self.gt[1]))
        r0 = max(0, int((maxy - self.gt[3]) / self.gt[5]))
        r1 = min(self.h - 1, int((miny - self.gt[3]) / self.gt[5]))
        vals = []
        for r in range(r0, r1 + 1):
            cy = self.gt[3] + (r + 0.5) * self.gt[5]
            for c in range(c0, c1 + 1):
                cx = self.gt[0] + (c + 0.5) * self.gt[1]
                if poly_geom.contains(Point(cx, cy)):
                    v = float(self.arr[r, c])
                    if self.nodata is None or v != self.nodata:
                        vals.append(v)
        if not vals:
            cent = poly_geom.centroid
            v = self.sample_point(cent.x, cent.y)
            if v is not None:
                vals = [v]
        if not vals:
            return None, None, None
        return float(np.mean(vals)), float(np.min(vals)), float(np.max(vals))


def fetch_osm_tile(args):
    idx, minx, miny, maxx, maxy = args
    out_file = os.path.join(RAW_OSM_DIR, f"osm_tile_{idx}.json")
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
            log(f"Tile {idx} HTTP {r.status_code}, retrying...")
        except Exception as e:
            log(f"Tile {idx} error {e}, retrying...")
        time.sleep(1.5 * (attempt + 1))
    return {"elements": []}


def download_focus_osm_tiles(focus_union) -> Tuple[Dict[int, Tuple[float, float]], Dict[int, Dict], Dict[int, Dict]]:
    # Cover Medan Baru + Medan Petisah + Polrestabes Medan corridor + USU
    # Tile size 0.008 deg (~890m) stays well under OSM 50,000 node limit per bbox
    minx, miny, maxx, maxy = focus_union.bounds
    step = 0.008
    tiles = []
    idx = 0
    x = minx - 0.002
    while x < maxx + 0.002:
        y = miny - 0.002
        while y < maxy + 0.002:
            tile_poly = Polygon([(x, y), (x + step, y), (x + step, y + step), (x, y + step)])
            if tile_poly.intersects(focus_union.buffer(0.004)):
                tiles.append((idx, x, y, x + step, y + step))
                idx += 1
            y += step
        x += step

    # Add explicit small tiles for Polrestabes Medan & Polsek Medan Baru/Petisah if outside
    extra_pts = [(98.6839, 3.6003), (98.6653, 3.5902)]
    for ex, ey in extra_pts:
        p = Point(ex, ey)
        if not any(Polygon([(t[1], t[2]), (t[3], t[2]), (t[3], t[4]), (t[1], t[4])]).contains(p) for t in tiles):
            tiles.append((idx, ex - 0.004, ey - 0.004, ex + 0.004, ey + 0.004))
            idx += 1

    log(f"Fetching/loading {len(tiles)} OSM API v0.6 tiles covering Medan Baru, Medan Petisah & Polrestabes ...")
    nodes: Dict[int, Tuple[float, float]] = {}
    node_tags: Dict[int, Dict[str, Any]] = {}
    ways: Dict[int, Dict[str, Any]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for data in pool.map(fetch_osm_tile, tiles):
            for el in data.get("elements", []):
                t = el.get("type")
                if t == "node":
                    nodes[el["id"]] = (el["lon"], el["lat"])
                    if "tags" in el:
                        node_tags[el["id"]] = el["tags"]
                elif t == "way":
                    ways[el["id"]] = el

    log(f"OSM merged cache: {len(nodes)} nodes, {len(ways)} ways")
    return nodes, node_tags, ways


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

    # Residential / yes fallback scaled deterministically by real footprint area
    if area_m2 >= 1500:
        return 24.0, "fallback_area_large"
    if area_m2 >= 450:
        return 12.0, "fallback_area_medium"
    if area_m2 >= 180:
        return 8.0, "fallback_area_ruko"
    return 6.0, "fallback_area_house"


def geocode_nominatim(query: str, cache: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if query in cache:
        return cache[query]
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "limit": 1,
                "viewbox": "98.55,3.82,98.78,3.45",
                "bounded": 1,
                "polygon_geojson": 1,
            },
            headers=HEADERS,
            timeout=12,
        )
        arr = r.json()
        if not arr:
            r2 = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1, "polygon_geojson": 1},
                headers=HEADERS,
                timeout=12,
            )
            arr = r2.json()
        res = arr[0] if arr else None
    except Exception:
        res = None
    cache[query] = res
    time.sleep(0.4)
    return res


def osrm_route(coords: List[Tuple[float, float]]) -> Optional[List[List[float]]]:
    coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in coords)
    url = f"https://router.project-osrm.org/route/v1/driving/{coord_str}?overview=full&geometries=geojson"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                j = r.json()
                if j.get("routes"):
                    return j["routes"][0]["geometry"]["coordinates"]
        except Exception:
            pass
        time.sleep(1.0)
    return None


def main() -> None:
    log("Starting real spatial data acquisition & processing for Orang 5 ...")

    # 1. Load 21 Kecamatan Kota Medan
    with open(MEDAN_KEC_SRC, encoding="utf-8") as fp:
        medan_raw = json.load(fp)

    pop_map = load_population_csv()
    kec_features = []
    kec_shapes = []
    medan_baru_poly = None
    medan_petisah_poly = None

    for idx, feat in enumerate(medan_raw["features"], start=1):
        geom = shape(feat["geometry"])
        name = feat["properties"]["WADMKC"]
        kec_shapes.append((idx, name, geom))
        if name == "Medan Baru":
            medan_baru_poly = geom
        elif name == "Medan Petisah":
            medan_petisah_poly = geom

        pop_info = pop_map.get(name.upper(), {})
        props = {
            "id_kec": idx,
            "nama_kec": name,
            "kode_kec": pop_info.get("kode_kec", f"MDN{idx:02d}"),
            "penduduk_2024": pop_info.get("penduduk_2024", 0),
            "penduduk_2025": pop_info.get("penduduk_2025", 0),
            "luas_km2": round(transform(TO_UTM, geom).area / 1e6, 2),
        }
        kec_features.append({"type": "Feature", "properties": props, "geometry": feat["geometry"]})

    medan_union = unary_union([g for _, _, g in kec_shapes])
    viirs_tif, nasa_tif, dem_tif = clip_rasters(medan_union.bounds)

    viirs_sampler = RasterSampler(viirs_tif)
    dem_sampler = RasterSampler(dem_tif)

    # 2. Download OSM tiles for Focus Area (Medan Baru + Medan Petisah + Polrestabes Medan)
    focus_union = unary_union([medan_baru_poly, medan_petisah_poly, Point(98.6839, 3.6003).buffer(0.003)])
    nodes, node_tags, ways = download_focus_osm_tiles(focus_union)

    # 3. Build Real Police Stations Layer across Kota Medan
    nom_cache_path = os.path.join(RAW_OSM_DIR, "nominatim_roads_cache.json")
    nom_cache = json.load(open(nom_cache_path, encoding="utf-8")) if os.path.exists(nom_cache_path) else {}

    police_queries = [
        ("Polrestabes Medan", "Polrestabes Medan, Jalan H.M. Said, Medan", "Polrestabes"),
        ("Polsek Medan Baru", "Polsek Medan Baru, Jalan Ibus Raya, Medan", "Polsek"),
        ("Polsek Medan Kota", "Polsek Medan Kota, Teladan Barat, Medan", "Polsek"),
        ("Polsek Medan Barat", "Polsek Medan Barat, Jalan Budi Pembangunan, Medan", "Polsek"),
        ("Polsek Medan Timur", "Polsek Medan Timur, Jalan Jawa, Medan", "Polsek"),
        ("Polsek Medan Area", "Polsek Medan Area, Jalan Semeru, Medan", "Polsek"),
        ("Polsek Medan Labuhan", "Polsek Medan Labuhan, Martubung, Medan", "Polsek"),
        ("Polsek Kota Belawan", "Polsek Belawan, Jalan Veteran, Medan", "Polsek"),
        ("Polsek Percut Sei Tuan", "Polsek Percut Sei Tuan, Jalan Letda Sujono, Deli Serdang", "Polsek"),
        ("Polsek Sunggal", "Polsek Sunggal, Jalan TB Simatupang, Medan", "Polsek"),
        ("Polsek Medan Helvetia", "Polsek Helvetia, Jalan Matahari Raya, Medan", "Polsek"),
        ("Polsek Pancur Batu", "Polsek Pancur Batu, Jalan Jamin Ginting", "Polsek"),
        ("Polsek Patumbak", "Jalan Pertahanan, Patumbak, Deli Serdang", "Pos/Polsek Sekitar"),
    ]

    police_pts: List[Dict[str, Any]] = []
    seen_coords = []

    def add_police_point(name: str, lon: float, lat: float, jenis: str, sumber: str, alamat: str = ""):
        pt = Point(lon, lat)
        pt_utm = transform(TO_UTM, pt)
        for ex in seen_coords:
            if pt_utm.distance(ex) < 120.0:
                return
        seen_coords.append(pt_utm)
        kec_name = "Sekitar Kota Medan"
        for _, kn, kg in kec_shapes:
            if kg.contains(pt):
                kec_name = kn
                break
        police_pts.append({
            "type": "Feature",
            "properties": {
                "nama": name,
                "jenis": jenis,
                "kecamatan": kec_name,
                "alamat": alamat[:120],
                "sumber": sumber,
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })

    # First extract OSM amenity=police nodes & ways
    for nid, tags in node_tags.items():
        if tags.get("amenity") == "police" and nid in nodes:
            lon, lat = nodes[nid]
            add_police_point(tags.get("name", "Pos Polisi OSM"), lon, lat, "Kantor/Pos Polisi", "OpenStreetMap API v0.6", tags.get("addr:street", ""))

    for wid, w in ways.items():
        tags = w.get("tags", {})
        if tags.get("amenity") == "police":
            coords = [nodes[n] for n in w.get("nodes", []) if n in nodes]
            if len(coords) >= 3:
                c = Polygon(coords).centroid if coords[0] == coords[-1] else LineString(coords).centroid
                add_police_point(tags.get("name", "Kantor Polisi OSM"), c.x, c.y, "Kantor/Pos Polisi", "OpenStreetMap API v0.6", tags.get("addr:street", ""))

    # Supplement with Nominatim official stations
    for label, q, jenis in police_queries:
        res = geocode_nominatim(q, nom_cache)
        if res:
            add_police_point(label, float(res["lon"]), float(res["lat"]), jenis, "Nominatim OpenStreetMap", res.get("display_name", ""))

    with open(nom_cache_path, "w", encoding="utf-8") as fp:
        json.dump(nom_cache, fp, indent=2, ensure_ascii=False)

    save_geojson(os.path.join(DATA_DIR, "polisi_eksisting.geojson"), police_pts)
    police_utm_geoms = [transform(TO_UTM, shape(f["geometry"])) for f in police_pts]

    # 4. Extract OSM Roads & Waterways in Focus Area
    road_features = []
    water_features = []
    osm_named_roads: Dict[str, List[LineString]] = {}

    for wid, w in ways.items():
        tags = w.get("tags", {})
        nds = w.get("nodes", [])
        coords = [nodes[n] for n in nds if n in nodes]
        if len(coords) < 2:
            continue
        ls = LineString(coords)
        if not ls.intersects(focus_union):
            continue

        hw = tags.get("highway")
        if hw in {"trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "trunk_link", "primary_link", "secondary_link"}:
            rname = tags.get("name", "")
            road_features.append({
                "type": "Feature",
                "properties": {"osm_id": wid, "nama_jalan": rname, "highway": hw, "oneway": tags.get("oneway", "no")},
                "geometry": mapping(ls),
            })
            if rname:
                osm_named_roads.setdefault(rname.lower(), []).append(ls)

        ww = tags.get("waterway")
        if ww in {"river", "stream", "canal"}:
            water_features.append({
                "type": "Feature",
                "properties": {"osm_id": wid, "nama": tags.get("name", "Alur Sungai"), "waterway": ww},
                "geometry": mapping(ls),
            })

    save_geojson(os.path.join(DATA_DIR, "jalan_fokus_osm.geojson"), road_features)
    save_geojson(os.path.join(DATA_DIR, "sungai_fokus_osm.geojson"), water_features)

    # 5. Build Official Polrestabes Medan Crime Hotspot Corridors (Real OSM + OSRM Road Geometries)
    corridor_specs = [
        ("Jl. Gatot Subroto", "Jalan Gatot Subroto, Medan", ["Jalan Gatot Subroto, Medan Petisah", "Jalan Gatot Subroto, Medan Sunggal"], "Medan Petisah / Medan Sunggal", "Curas (Begal) & Minim PJU Segmen", "Sangat Tinggi"),
        ("Jl. Sriwijaya", "Jalan Sriwijaya, Medan Baru", ["Jalan Sriwijaya, Medan Baru"], "Medan Baru", "Rawan Begal Malam Hari (Rilis Polrestabes)", "Sangat Tinggi"),
        ("Jl. Sei Serayu", "Jalan Sei Serayu, Medan Baru", ["Jalan Sei Serayu, Medan Baru"], "Medan Baru", "Koridor Sepi Minim Penerangan Malam", "Tinggi"),
        ("Jl. Gajah Mada", "Jalan Gajah Mada, Medan", ["Jalan Gajah Mada, Medan Petisah"], "Medan Baru / Medan Petisah", "Titik Gelap & Kerawanan Jalanan", "Tinggi"),
        ("Jl. S. Parman", "Jalan S. Parman, Medan", ["Jalan S. Parman, Medan Baru"], "Medan Baru / Medan Petisah", "Koridor Protokol Rawan Malam", "Tinggi"),
        ("Jl. Iskandar Muda", "Jalan Iskandar Muda, Medan", ["Jalan Iskandar Muda, Medan Baru"], "Medan Baru / Medan Petisah", "Aktivitas Malam & Titik Blindspot", "Sedang-Tinggi"),
        ("Jl. Jamin Ginting", "Jalan Jamin Ginting, Padang Bulan, Medan", ["Jalan Jamin Ginting, Padang Bulan, Medan", "Simpang Pos, Medan"], "Medan Baru / Medan Selayang", "Koridor Kampus & Arteri Padat Malam", "Tinggi"),
        ("Jl. Dr. Mansyur", "Jalan Dr. Mansyur, Medan", ["Jalan Dr. Mansyur, Medan Baru"], "Medan Baru / Medan Selayang", "Kawasan Mahasiswa & Rawan Curas", "Tinggi"),
        ("Jl. Jend. Sudirman", "Jalan Jenderal Sudirman, Medan", ["Jalan Jenderal Sudirman, Medan Polonia"], "Medan Polonia / Medan Baru", "Koridor Taman Beringin - Sudirman (Rilis Polrestabes)", "Tinggi"),
        ("Jl. Gagak Hitam (Ring Road)", "Jalan Gagak Hitam, Medan", ["Jalan Gagak Hitam, Sunggal, Medan"], "Medan Sunggal / Medan Selayang", "Arteri Ring Road Minim PJU & Rawan Begal", "Sangat Tinggi"),
        ("Jl. Ngumban Surbakti", "Jalan Ngumban Surbakti, Medan", ["Jalan Ngumban Surbakti, Medan Selayang"], "Medan Selayang / Medan Johor", "Arteri Ring Road Selatan Rawan Malam", "Tinggi"),
        ("Jl. Yos Sudarso", "Jalan Kolonel Yos Sudarso, Medan Barat", ["Jalan Yos Sudarso, Medan Barat"], "Medan Barat", "Koridor Utara Rawan Begal (Rilis Polrestabes)", "Tinggi"),
        ("Jl. Sutrisno", "Jalan Sutrisno, Medan Area", ["Jalan Sutrisno, Medan Area"], "Medan Area", "Rawan Curas & Curat (Rilis Polrestabes)", "Tinggi"),
        ("Jl. Perintis Kemerdekaan", "Jalan Perintis Kemerdekaan, Medan", ["Jalan Perintis Kemerdekaan, Medan Timur"], "Medan Perjuangan / Medan Timur", "Koridor Rawan Kejahatan Malam (Rilis Polrestabes)", "Tinggi"),
        ("Jl. Prof. H.M. Yamin", "Jalan Prof. H.M. Yamin, Medan", ["Jalan Prof. H.M. Yamin, Medan Timur"], "Medan Timur / Medan Perjuangan", "Koridor Rawan Kejahatan Malam (Rilis Polrestabes)", "Sedang-Tinggi"),
        ("Jl. A.H. Nasution", "Jalan A.H. Nasution, Medan", ["Jalan A.H. Nasution, Medan Johor"], "Medan Johor", "Arteri Selatan Rawan Begal Malam", "Tinggi"),
    ]

    corridor_features = []
    corridor_utm_geoms = []

    for cname, osm_key, nom_queries, kec_lbl, jenis_krw, bahaya in corridor_specs:
        lines: List[LineString] = []
        # Check OSM ways first
        key_l = osm_key.split(",")[0].lower()
        for rn, rlist in osm_named_roads.items():
            if key_l in rn:
                lines.extend(rlist)

        # If not inside focus OSM tiles or sparse, fetch real geometry from Nominatim polygon_geojson=1
        if not lines:
            for nq in nom_queries:
                res = geocode_nominatim(nq, nom_cache)
                if res and "geojson" in res:
                    g = shape(res["geojson"])
                    if isinstance(g, LineString):
                        lines.append(g)
                    elif isinstance(g, MultiLineString):
                        lines.extend(list(g.geoms))

        if not lines:
            continue

        merged = linemerge(lines) if len(lines) > 1 else lines[0]
        if isinstance(merged, LineString):
            geom_final = merged
        elif isinstance(merged, MultiLineString):
            geom_final = merged
        else:
            geom_final = MultiLineString(lines)

        # Sample VIIRS along corridor vertices
        sample_pts = []
        geoms_iter = [geom_final] if isinstance(geom_final, LineString) else list(geom_final.geoms)
        for seg in geoms_iter:
            for pt in seg.coords[::max(1, len(seg.coords) // 8)]:
                v = viirs_sampler.sample_point(pt[0], pt[1])
                if v is not None:
                    sample_pts.append(v)

        v_mean = round(float(np.mean(sample_pts)), 2) if sample_pts else 0.0
        v_min = round(float(np.min(sample_pts)), 2) if sample_pts else 0.0
        utm_g = transform(TO_UTM, geom_final)
        len_km = round(utm_g.length / 1000.0, 2)
        corridor_utm_geoms.append(utm_g)

        corridor_features.append({
            "type": "Feature",
            "properties": {
                "nama_jalan": cname,
                "kecamatan": kec_lbl,
                "jenis_kerawanan": jenis_krw,
                "tingkat_bahaya": bahaya,
                "viirs_mean": v_mean,
                "viirs_min": v_min,
                "panjang_km": len_km,
                "sumber_data": "Rilis Pemetaan Polrestabes Medan & Analisis VIIRS V2.1 2024",
            },
            "geometry": mapping(geom_final),
        })

    with open(nom_cache_path, "w", encoding="utf-8") as fp:
        json.dump(nom_cache, fp, indent=2, ensure_ascii=False)
    save_geojson(os.path.join(DATA_DIR, "koridor_rawan_begal.geojson"), corridor_features)

    # 6. Build 500m Hexagonal Grid across ALL 21 Kecamatan in UTM 47N (EPSG:32647)
    log("Generating 500m hexagonal grid across 21 Kecamatan Kota Medan ...")
    medan_utm = transform(TO_UTM, medan_union)
    uminx, uminy, umaxx, umaxy = medan_utm.bounds
    radius = 500.0 / math.sqrt(3.0)  # flat-top hex with 500m flat-to-flat height (~500m spacing)
    dx = 1.5 * radius
    dy = math.sqrt(3.0) * radius

    hex_features = []
    kec_utm_list = [(idx, name, transform(TO_UTM, geom)) for idx, name, geom in kec_shapes]
    all_corridors_utm = unary_union(corridor_utm_geoms) if corridor_utm_geoms else None

    col = 0
    x = uminx - radius
    hex_id = 1
    raw_hex_rows = []

    while x <= umaxx + radius:
        y = uminy - radius + (0.5 * dy if col % 2 == 1 else 0.0)
        while y <= umaxy + radius:
            verts = [
                (x + radius * math.cos(math.radians(60 * k)), y + radius * math.sin(math.radians(60 * k)))
                for k in range(6)
            ]
            hpoly_utm = Polygon(verts)
            if hpoly_utm.intersects(medan_utm):
                clipped_utm = hpoly_utm.intersection(medan_utm)
                if clipped_utm.area > 5000.0:  # exclude tiny sliver border fragments < 0.5 ha
                    hpoly_wgs = transform(TO_WGS, clipped_utm)
                    cent_utm = clipped_utm.centroid

                    # Find primary kecamatan by max intersection
                    best_kec = ("Kota Medan", 0)
                    for kidx, kname, kg_utm in kec_utm_list:
                        if kg_utm.intersects(cent_utm):
                            best_kec = (kname, kidx)
                            break
                    if best_kec[1] == 0:
                        best_area = 0.0
                        for kidx, kname, kg_utm in kec_utm_list:
                            ia = kg_utm.intersection(clipped_utm).area
                            if ia > best_area:
                                best_area = ia
                                best_kec = (kname, kidx)

                    v_mean, v_min, v_max = viirs_sampler.sample_polygon_stats(hpoly_wgs)
                    e_mean, _, _ = dem_sampler.sample_polygon_stats(hpoly_wgs)
                    dist_pol = min(cent_utm.distance(pg) for pg in police_utm_geoms)
                    dist_kor = cent_utm.distance(all_corridors_utm) if all_corridors_utm else 5000.0

                    raw_hex_rows.append({
                        "hex_id": f"HEX-{hex_id:04d}",
                        "id_kec": best_kec[1],
                        "kecamatan": best_kec[0],
                        "viirs_mean": round(v_mean or 0.0, 2),
                        "viirs_min": round(v_min or 0.0, 2),
                        "viirs_max": round(v_max or 0.0, 2),
                        "elev_mean": round(e_mean or 0.0, 1),
                        "dist_polisi_m": round(dist_pol, 0),
                        "dist_koridor_m": round(dist_kor, 0),
                        "geom_wgs": hpoly_wgs,
                    })
                    hex_id += 1
            y += dy
        x += dx
        col += 1

    # Compute normalized Dark-Zone Crime Risk Score (0-100) from real VIIRS, police gap, & corridor proximity
    v_vals = np.array([r["viirs_mean"] for r in raw_hex_rows], dtype=float)
    v_p90 = float(np.percentile(v_vals, 90)) if len(v_vals) else 50.0

    for r in raw_hex_rows:
        # Low VIIRS radiance relative to urban activity creates dark-zone vulnerability
        darkness_norm = max(0.0, min(1.0, (v_p90 - r["viirs_mean"]) / max(v_p90, 1.0)))
        police_gap = max(0.0, min(1.0, r["dist_polisi_m"] / 4500.0))
        corridor_prox = max(0.0, min(1.0, 1.0 - (r["dist_koridor_m"] / 1500.0)))
        # Urban corridors with lighting gaps or blindspots far from police posts score highest
        score = round(100.0 * (0.42 * darkness_norm + 0.33 * police_gap + 0.25 * corridor_prox), 1)
        if score >= 68.0 or (r["dist_koridor_m"] <= 350.0 and r["viirs_mean"] < 28.0):
            kelas = "Kritis (Dark-Zone)"
        elif score >= 50.0:
            kelas = "Tinggi"
        elif score >= 34.0:
            kelas = "Sedang"
        else:
            kelas = "Rendah"

        pop_info = pop_map.get(r["kecamatan"].upper(), {})
        hex_features.append({
            "type": "Feature",
            "properties": {
                "hex_id": r["hex_id"],
                "id_kec": r["id_kec"],
                "kecamatan": r["kecamatan"],
                "penduduk_2025": pop_info.get("penduduk_2025", 0),
                "viirs_mean": r["viirs_mean"],
                "viirs_min": r["viirs_min"],
                "viirs_max": r["viirs_max"],
                "elev_mean": r["elev_mean"],
                "dist_polisi_m": r["dist_polisi_m"],
                "dist_koridor_m": r["dist_koridor_m"],
                "risk_score": score,
                "kelas_risiko": kelas,
            },
            "geometry": mapping(r["geom_wgs"]),
        })

    save_geojson(os.path.join(DATA_DIR, "hex_viirs_medan_500m.geojson"), hex_features)

    # 7. Extract 3D Buildings in Focus Area (Medan Baru & Medan Petisah)
    log("Processing 3D OSM buildings in Medan Baru & Medan Petisah ...")
    focus_kec_union = unary_union([medan_baru_poly, medan_petisah_poly])
    medan_baru_utm = transform(TO_UTM, medan_baru_poly)
    medan_petisah_utm = transform(TO_UTM, medan_petisah_poly)

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
        if not focus_kec_union.contains(cent):
            continue

        poly_utm = transform(TO_UTM, poly)
        area_m2 = poly_utm.area
        if area_m2 < 16.0:  # skip tiny noise structures < 4x4m
            continue

        cent_utm = poly_utm.centroid
        kec_b = "Medan Baru" if medan_baru_utm.contains(cent_utm) else "Medan Petisah"
        height_m, h_source = smart_building_height(tags, area_m2)

        v_val = viirs_sampler.sample_point(cent.x, cent.y) or 0.0
        e_val = dem_sampler.sample_point(cent.x, cent.y) or 0.0
        dist_pol = min(cent_utm.distance(pg) for pg in police_utm_geoms)
        dist_kor = cent_utm.distance(all_corridors_utm) if all_corridors_utm else 5000.0

        buildings_raw.append({
            "osm_id": wid,
            "nama": tags.get("name", ""),
            "building": str(tags.get("building", "yes")),
            "amenity": str(tags.get("amenity", "")),
            "kecamatan": kec_b,
            "area_m2": round(area_m2, 1),
            "height_m": height_m,
            "height_src": h_source,
            "viirs_rad": round(v_val, 2),
            "elev_m": round(e_val, 1),
            "dist_polisi_m": round(dist_pol, 0),
            "dist_koridor_m": round(dist_kor, 0),
            "poly_wgs": poly,
            "cent_utm": cent_utm,
        })

    # Classify building dark-zone vulnerability using actual distribution in Medan Baru & Petisah
    b_viirs = np.array([b["viirs_rad"] for b in buildings_raw], dtype=float)
    v_med = float(np.median(b_viirs)) if len(b_viirs) else 30.0
    v_q30 = float(np.percentile(b_viirs, 30)) if len(b_viirs) else 20.0
    log(f"Focus buildings: {len(buildings_raw)} polygons | VIIRS Q30={v_q30:.1f}, Median={v_med:.1f}")

    # 8. Root-Cause Solution 1: Smart PJU & CCTV Analytics Points (Derived from dark corridors & dark building clusters)
    log("Placing Smart PJU & CCTV solutions algorithmically along dark corridors ...")
    pju_solutions = []
    pju_utm_points = []
    pju_idx = 1

    def add_pju_solution(lon: float, lat: float, nama_lokasi: str, kec: str, v_awal: float, dist_pol: float, is_focus: bool):
        nonlocal pju_idx
        pt_utm = transform(TO_UTM, Point(lon, lat))
        for ex in pju_utm_points:
            if pt_utm.distance(ex) < (240.0 if is_focus else 420.0):
                return
        if dist_pol > 1200.0 and pju_idx % 4 == 1:
            jenis = "Pos Pantau & Panic Button + CCTV"
            radius_m = 210
            prioritas = "Prioritas 1 - Kritis"
        elif v_awal <= v_q30 or pju_idx % 2 == 0:
            jenis = "CCTV Analitik + PJU Pintar Terpadu"
            radius_m = 180
            prioritas = "Prioritas 1 - Kritis"
        else:
            jenis = "PJU Pintar LED Solar + Sensor Gerak"
            radius_m = 160
            prioritas = "Prioritas 2 - Tinggi"

        pju_utm_points.append((pt_utm, radius_m, f"PJU-{pju_idx:03d}"))
        pju_solutions.append({
            "type": "Feature",
            "properties": {
                "id_unit": f"PJU-{pju_idx:03d}",
                "jenis_solusi": jenis,
                "nama_lokasi": nama_lokasi,
                "kecamatan": kec,
                "viirs_awal": round(v_awal, 2),
                "radius_terang_m": radius_m,
                "prioritas": prioritas,
                "gedung_terlindungi": 0,  # populated below by spatial count
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })
        pju_idx += 1

    # First place high-density Smart PJU along focus corridors & dark pockets in Medan Baru & Medan Petisah
    for cf in corridor_features:
        cname = cf["properties"]["nama_jalan"]
        geom = shape(cf["geometry"])
        segs = [geom] if isinstance(geom, LineString) else list(geom.geoms)
        for seg in segs:
            seg_utm = transform(TO_UTM, seg)
            is_focus_seg = seg.intersects(focus_kec_union)
            step_m = 250.0 if is_focus_seg else 550.0
            d = 80.0
            while d < seg_utm.length:
                pt_u = seg_utm.interpolate(d)
                pt_w = transform(TO_WGS, pt_u)
                v_here = viirs_sampler.sample_point(pt_w.x, pt_w.y) or 0.0
                d_pol = min(pt_u.distance(pg) for pg in police_utm_geoms)
                in_medan = medan_union.contains(pt_w)
                if in_medan and (is_focus_seg or v_here <= 38.0 or d_pol > 1100.0):
                    kec_lbl = cf["properties"]["kecamatan"]
                    for _, kn, kg in kec_shapes:
                        if kg.contains(pt_w):
                            kec_lbl = kn
                            break
                    # Avoid placing duplicate list items as tuple vs Point
                    # Check distance safely against existing points
                    too_close = any(pt_u.distance(p_u) < (240.0 if is_focus_seg else 450.0) for p_u, _, _ in pju_utm_points)
                    if not too_close:
                        if d_pol > 1250.0 and pju_idx % 4 == 1:
                            jenis = "Pos Pantau & Panic Button + CCTV"
                            radius_m = 210
                            prioritas = "Prioritas 1 - Kritis"
                        elif v_here <= v_q30 or pju_idx % 2 == 0:
                            jenis = "CCTV Analitik + PJU Pintar Terpadu"
                            radius_m = 185
                            prioritas = "Prioritas 1 - Kritis"
                        else:
                            jenis = "PJU Pintar LED Solar + Sensor Gerak"
                            radius_m = 165
                            prioritas = "Prioritas 2 - Tinggi"

                        pju_utm_points.append((pt_u, radius_m, f"PJU-{pju_idx:03d}"))
                        pju_solutions.append({
                            "type": "Feature",
                            "properties": {
                                "id_unit": f"PJU-{pju_idx:03d}",
                                "jenis_solusi": jenis,
                                "nama_lokasi": f"Segmen {cname}",
                                "kecamatan": kec_lbl,
                                "viirs_awal": round(v_here, 2),
                                "radius_terang_m": radius_m,
                                "prioritas": prioritas,
                                "gedung_terlindungi": 0,
                            },
                            "geometry": {"type": "Point", "coordinates": [pt_w.x, pt_w.y]},
                        })
                        pju_idx += 1
                d += step_m

    # Also place PJU solutions on darkest interior residential streets in Medan Baru & Medan Petisah
    for rf in road_features:
        if rf["properties"]["highway"] not in {"secondary", "tertiary", "residential"}:
            continue
        rname = rf["properties"]["nama_jalan"] or "Jalan Lingkungan"
        ls = shape(rf["geometry"])
        cent_w = ls.centroid
        if not focus_kec_union.contains(cent_w):
            continue
        v_here = viirs_sampler.sample_point(cent_w.x, cent_w.y) or 0.0
        if v_here <= v_med:
            pt_u = transform(TO_UTM, cent_w)
            too_close = any(pt_u.distance(p_u) < 280.0 for p_u, _, _ in pju_utm_points)
            if not too_close:
                kec_lbl = "Medan Baru" if medan_baru_poly.contains(cent_w) else "Medan Petisah"
                pju_utm_points.append((pt_u, 170, f"PJU-{pju_idx:03d}"))
                pju_solutions.append({
                    "type": "Feature",
                    "properties": {
                        "id_unit": f"PJU-{pju_idx:03d}",
                        "jenis_solusi": "PJU Pintar LED Solar + Sensor Gerak",
                        "nama_lokasi": rname,
                        "kecamatan": kec_lbl,
                        "viirs_awal": round(v_here, 2),
                        "radius_terang_m": 170,
                        "prioritas": "Prioritas 2 - Tinggi",
                        "gedung_terlindungi": 0,
                    },
                    "geometry": {"type": "Point", "coordinates": [cent_w.x, cent_w.y]},
                })
                pju_idx += 1

    # Link buildings with vulnerability & Smart PJU solution coverage
    pju_counts = {pid: 0 for _, _, pid in pju_utm_points}
    building_features = []

    for b in buildings_raw:
        # Compute building dark-zone vulnerability score (0-100)
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

        # Check if within illumination radius of proposed Smart PJU / CCTV
        terlindungi = False
        nearest_pid = ""
        best_dist = 1e9
        for pt_u, rad_m, pid in pju_utm_points:
            d = b["cent_utm"].distance(pt_u)
            if d < best_dist:
                best_dist = d
                nearest_pid = pid
            if d <= rad_m:
                terlindungi = True
                pju_counts[pid] += 1

        building_features.append({
            "type": "Feature",
            "properties": {
                "osm_id": b["osm_id"],
                "nama": b["nama"],
                "building": b["building"],
                "kecamatan": b["kecamatan"],
                "area_m2": b["area_m2"],
                "height_m": b["height_m"],
                "height_src": b["height_src"],
                "viirs_rad": b["viirs_rad"],
                "elev_m": b["elev_m"],
                "dist_polisi_m": b["dist_polisi_m"],
                "dist_koridor_m": b["dist_koridor_m"],
                "vuln_score": v_score,
                "status_rawan": status,
                "terlindungi_solusi": 1 if terlindungi else 0,
                "nearest_pju_id": nearest_pid,
                "dist_pju_m": round(best_dist, 0),
            },
            "geometry": mapping(b["poly_wgs"]),
        })

    for pf in pju_solutions:
        pid = pf["properties"]["id_unit"]
        pf["properties"]["gedung_terlindungi"] = pju_counts.get(pid, 0)

    save_geojson(os.path.join(DATA_DIR, "bangunan_fokus_3d.geojson"), building_features)
    save_geojson(os.path.join(DATA_DIR, "solusi_pju_cctv.geojson"), pju_solutions)

    # 9. Root-Cause Solution 2: Real OSRM Police Night Patrol Loops (KRYD / Satgas Anti-Begal)
    log("Generating real OSRM road-network patrol routes ...")
    pol_lookup = {f["properties"]["nama"]: tuple(f["geometry"]["coordinates"]) for f in police_pts}

    def get_coord(name, fallback):
        return pol_lookup.get(name, fallback)

    patrol_defs = [
        {
            "nama_rute": "Rute Patroli A — Koridor Inti Medan Baru & Medan Petisah",
            "unit_pelaksana": "Tim URC Polsek Medan Baru & Satgas Anti-Begal",
            "jam_patroli": "22:00 - 05:00 WIB (Interval 45 Menit)",
            "koridor_dilalui": "Jl. Ibus Raya - Jl. Gatot Subroto - Jl. Sei Serayu - Jl. Dr. Mansyur - Jl. Jamin Ginting - Jl. Sriwijaya - Jl. Gajah Mada",
            "waypoints": [
                get_coord("Polsek Medan Baru", (98.6653, 3.5902)),
                (98.6520, 3.5919),  # Jl. Gatot Subroto
                (98.6455, 3.5778),  # Jl. Sei Serayu
                (98.6545, 3.5635),  # Jl. Dr. Mansyur / USU
                (98.6617, 3.5598),  # Jl. Jamin Ginting
                (98.6615, 3.5795),  # Jl. Sriwijaya
                (98.6644, 3.5844),  # Jl. Gajah Mada
                get_coord("Polsek Medan Baru", (98.6653, 3.5902)),
            ],
        },
        {
            "nama_rute": "Rute Patroli B — Poros Tengah Polrestabes, Sudirman & Medan Area",
            "unit_pelaksana": "Satgas KRYD Polrestabes Medan & Polsek Medan Timur/Kota/Area",
            "jam_patroli": "21:30 - 04:30 WIB (Interval 60 Menit)",
            "koridor_dilalui": "Polrestabes (Jl. HM Said) - Jl. Perintis Kemerdekaan - Jl. HM Yamin - Jl. Sutrisno - Jl. Sudirman - Jl. S. Parman",
            "waypoints": [
                get_coord("Polrestabes Medan", (98.6839, 3.6003)),
                (98.6855, 3.5988),  # Jl. Perintis Kemerdekaan
                (98.6972, 3.5819),  # Jl. Sutrisno
                get_coord("Polsek Medan Kota", (98.6931, 3.5653)),
                (98.6725, 3.5758),  # Jl. Sudirman
                (98.6672, 3.5784),  # Jl. S. Parman
                get_coord("Polrestabes Medan", (98.6839, 3.6003)),
            ],
        },
        {
            "nama_rute": "Rute Patroli C — Koridor Barat & Ring Road (Sunggal - Helvetia - Barat)",
            "unit_pelaksana": "Patroli Gabungan Polsek Sunggal, Helvetia & Medan Barat",
            "jam_patroli": "22:00 - 05:00 WIB (Interval 60 Menit)",
            "koridor_dilalui": "Polsek Medan Barat - Jl. Yos Sudarso - Jl. Gatot Subroto - Jl. Gagak Hitam (Ring Road) - Jl. Ngumban Surbakti",
            "waypoints": [
                get_coord("Polsek Medan Barat", (98.6712, 3.6223)),
                (98.6694, 3.6286),  # Jl. Yos Sudarso
                get_coord("Polsek Medan Helvetia", (98.6349, 3.6104)),
                (98.6270, 3.5880),  # Jl. Gagak Hitam / Ring Road
                (98.6345, 3.5530),  # Jl. Ngumban Surbakti
                (98.6617, 3.5598),  # Jl. Jamin Ginting
                get_coord("Polsek Medan Baru", (98.6653, 3.5902)),
            ],
        },
    ]

    patrol_features = []
    for pdef in patrol_defs:
        coords = osrm_route(pdef["waypoints"])
        if not coords:
            continue
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

    # 10. Aggregate Real Stats back onto 21 Kecamatan Polygons
    for kf in kec_features:
        kname = kf["properties"]["nama_kec"]
        k_hex = [h["properties"] for h in hex_features if h["properties"]["kecamatan"] == kname]
        kf["properties"]["viirs_mean"] = round(float(np.mean([h["viirs_mean"] for h in k_hex])), 2) if k_hex else 0.0
        kf["properties"]["viirs_min"] = round(float(np.min([h["viirs_min"] for h in k_hex])), 2) if k_hex else 0.0
        kf["properties"]["elev_mean_m"] = round(float(np.mean([h["elev_mean"] for h in k_hex])), 1) if k_hex else 0.0
        kf["properties"]["hex_total"] = len(k_hex)
        kf["properties"]["hex_kritis"] = sum(1 for h in k_hex if h["kelas_risiko"] in {"Kritis (Dark-Zone)", "Tinggi"})
        kf["properties"]["avg_risk_score"] = round(float(np.mean([h["risk_score"] for h in k_hex])), 1) if k_hex else 0.0
        kf["properties"]["jumlah_pju_solusi"] = sum(1 for p in pju_solutions if p["properties"]["kecamatan"] == kname)

    save_geojson(os.path.join(DATA_DIR, "batas_kecamatan_medan.geojson"), kec_features)

    # 11. Export Compact Bundle for WebGIS (Works over file:// and HTTP)
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
        key = fname.replace(".geojson", "")
        with open(src, encoding="utf-8") as fp:
            bundle[key] = json.load(fp)

    bundle_js = os.path.join(WEB_DATA_DIR, "spatial_bundle.js")
    with open(bundle_js, "w", encoding="utf-8") as fp:
        fp.write("window.MEDAN_SPATIAL_DATA = ")
        json.dump(bundle, fp, separators=(",", ":"), ensure_ascii=False)
        fp.write(";\n")
    log(f"Exported WebGIS bundle -> {os.path.relpath(bundle_js, BASE_DIR)} ({os.path.getsize(bundle_js) // 1024} KB)")

    # Print summary telemetry
    total_b = len(building_features)
    high_b = sum(1 for b in building_features if b["properties"]["status_rawan"] == "Tinggi")
    prot_high_b = sum(1 for b in building_features if b["properties"]["status_rawan"] == "Tinggi" and b["properties"]["terlindungi_solusi"] == 1)
    log(f"SUMMARY: {len(hex_features)} hex cells | {total_b} 3D buildings ({high_b} Tinggi, {prot_high_b} protected by PJU solution) | {len(corridor_features)} crime corridors | {len(pju_solutions)} PJU/CCTV solutions | {len(patrol_features)} patrol routes | {len(police_pts)} police stations")


if __name__ == "__main__":
    main()
