import os
import zipfile
import xml.etree.ElementTree as ET

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase, QPainter
from qgis.core import (
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsColorRampShader,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsGraduatedSymbolRenderer,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemMapOverview,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutMeasurement,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLegendStyle,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPrintLayout,
    QgsProject,
    QgsProperty,
    QgsRasterLayer,
    QgsRasterShader,
    QgsRectangle,
    QgsRendererCategory,
    QgsRendererRange,
    QgsSimpleFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSingleBandPseudoColorRenderer,
    QgsSingleSymbolRenderer,
    QgsSymbolLayer,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

BASE_DIR = r"M:\Kuliah\Semester 5\SIG\Project Akhir"
QGZ_PATH = os.path.join(BASE_DIR, "Medan_DarkZone_Crime_Orang5.qgz")
LAYOUT_PNG = os.path.join(BASE_DIR, "Layout_Peta_Orang5.png")
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

PAL = {
    "ink": "#071B2B",
    "teal": "#167D8D",
    "ice": "#B9E4E8",
    "paper": "#EEEEEE",
    "white": "#FFFFFF",
    "lamp": "#FFC94D",
}

FONT_DISPLAY = "Segoe UI"
FONT_BODY = "Segoe UI"


def log(msg: str) -> None:
    print(f"[02_QGIS] {msg}", flush=True)


def load_project_fonts() -> None:
    global FONT_DISPLAY, FONT_BODY
    fredoka_path = os.path.join(FONTS_DIR, "Fredoka.ttf")
    nunito_path = os.path.join(FONTS_DIR, "Nunito.ttf")

    if os.path.exists(fredoka_path):
        fid = QFontDatabase.addApplicationFont(fredoka_path)
        if fid != -1:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                FONT_DISPLAY = fams[0]
                log(f"Loaded font display: {FONT_DISPLAY}")

    if os.path.exists(nunito_path):
        nid = QFontDatabase.addApplicationFont(nunito_path)
        if nid != -1:
            fams = QFontDatabase.applicationFontFamilies(nid)
            if fams:
                FONT_BODY = fams[0]
                log(f"Loaded font body: {FONT_BODY}")


def make_font(family: str, size_pt: float, bold: bool = False) -> QFont:
    f = QFont(family)
    f.setPointSizeF(size_pt)
    f.setBold(bold)
    return f


def make_text_format(size_pt: float, color_hex: str = PAL["ink"], bold: bool = False, buffer_hex: str = PAL["white"], family: str = None) -> QgsTextFormat:
    fmt = QgsTextFormat()
    f = make_font(family or FONT_BODY, size_pt, bold=bold)
    fmt.setFont(f)
    fmt.setSize(size_pt)
    fmt.setColor(QColor(color_hex))
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(0.8)
    buf.setColor(QColor(buffer_hex))
    fmt.setBuffer(buf)
    return fmt


def style_kecamatan(layer: QgsVectorLayer) -> None:
    sym = QgsFillSymbol.createSimple({
        "color": "255,255,255,120",
        "outline_color": PAL["ink"],
        "outline_width": "0.35",
        "outline_style": "dash",
    })
    layer.setRenderer(QgsSingleSymbolRenderer(sym))

    pal = QgsPalLayerSettings()
    pal.fieldName = "nama_kec"
    pal.enabled = True
    pal.setFormat(make_text_format(7.2, PAL["ink"], bold=True, buffer_hex=PAL["white"], family=FONT_BODY))
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))


def style_viirs_raster(layer: QgsRasterLayer) -> None:
    shader = QgsRasterShader()
    ramp = QgsColorRampShader()
    ramp.setColorRampType(QgsColorRampShader.Interpolated)
    items = [
        QgsColorRampShader.ColorRampItem(0, QColor(7, 27, 43, 230), "0 (Gelap)"),
        QgsColorRampShader.ColorRampItem(15, QColor(15, 76, 92, 205), "15 (Redup)"),
        QgsColorRampShader.ColorRampItem(30, QColor(22, 125, 141, 185), "30 (Sedang)"),
        QgsColorRampShader.ColorRampItem(55, QColor(185, 228, 232, 140), "55 (Terang)"),
        QgsColorRampShader.ColorRampItem(95, QColor(255, 255, 255, 80), "95+ (Pusat)"),
    ]
    ramp.setColorRampItemList(items)
    shader.setRasterShaderFunction(ramp)
    renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
    layer.setRenderer(renderer)
    layer.setOpacity(0.55)


def style_hex_grid(layer: QgsVectorLayer) -> None:
    ranges = [
        ("Kritis (68 - 100)", 68.0, 100.1, QColor(7, 27, 43, 190), QColor(7, 27, 43, 90)),
        ("Tinggi (50 - 68)", 50.0, 68.0, QColor(15, 76, 92, 150), QColor(7, 27, 43, 90)),
        ("Sedang (34 - 50)", 34.0, 50.0, QColor(22, 125, 141, 120), QColor(7, 27, 43, 90)),
        ("Rendah (0 - 34)", 0.0, 34.0, QColor(185, 228, 232, 110), QColor(7, 27, 43, 90)),
    ]
    renderer_ranges = []
    for label, lo, hi, fill_c, out_c in ranges:
        sym = QgsFillSymbol()
        sl = QgsSimpleFillSymbolLayer(fill_c, Qt.SolidPattern, out_c, Qt.SolidLine, 0.15)
        sym.changeSymbolLayer(0, sl)
        renderer_ranges.append(QgsRendererRange(lo, hi, sym, label))

    renderer = QgsGraduatedSymbolRenderer("risk_score", renderer_ranges)
    layer.setRenderer(renderer)
    layer.setBlendMode(QPainter.CompositionMode_SourceOver)


def style_buildings_25d(layer: QgsVectorLayer) -> None:
    cats = [
        ("Tinggi", "Zona Gelap Rawan Tinggi", QColor(PAL["ink"]), QColor(7, 27, 43, 235)),
        ("Sedang", "Zona Waspada Sedang", QColor(PAL["teal"]), QColor(7, 27, 43, 200)),
        ("Rendah", "Zona Terang / Aman", QColor(PAL["ice"]), QColor(22, 125, 141, 160)),
    ]
    renderer_cats = []
    for val, label, roof_col, wall_col in cats:
        sym = QgsFillSymbol()
        base_sl = QgsSimpleFillSymbolLayer(wall_col, Qt.SolidPattern, QColor(PAL["ink"]), Qt.SolidLine, 0.08)
        sym.changeSymbolLayer(0, base_sl)

        roof_sl = QgsSimpleFillSymbolLayer(roof_col, Qt.SolidPattern, QColor(255, 255, 255, 90), Qt.SolidLine, 0.06)
        roof_sl.setDataDefinedProperty(
            QgsSymbolLayer.PropertyOffset,
            QgsProperty.fromExpression("array(-min(height_m, 35) * 0.035, -min(height_m, 35) * 0.05)"),
        )
        sym.appendSymbolLayer(roof_sl)
        renderer_cats.append(QgsRendererCategory(val, sym, label))

    layer.setRenderer(QgsCategorizedSymbolRenderer("status_rawan", renderer_cats))


def style_water(layer: QgsVectorLayer) -> None:
    sym = QgsLineSymbol.createSimple({"color": PAL["teal"], "width": "0.6"})
    layer.setRenderer(QgsSingleSymbolRenderer(sym))


def style_roads(layer: QgsVectorLayer) -> None:
    sym = QgsLineSymbol()
    sl = QgsSimpleLineSymbolLayer(QColor(7, 27, 43, 60), 0.2)
    sym.changeSymbolLayer(0, sl)
    layer.setRenderer(QgsSingleSymbolRenderer(sym))


def style_crime_corridors(layer: QgsVectorLayer) -> None:
    sym = QgsLineSymbol()
    casing = QgsSimpleLineSymbolLayer(QColor(PAL["white"]), 1.6)
    casing.setPenCapStyle(Qt.RoundCap)
    core = QgsSimpleLineSymbolLayer(QColor(PAL["ink"]), 0.7)
    core.setPenCapStyle(Qt.RoundCap)
    sym.changeSymbolLayer(0, casing)
    sym.appendSymbolLayer(core)
    layer.setRenderer(QgsSingleSymbolRenderer(sym))

    pal = QgsPalLayerSettings()
    pal.fieldName = "nama_jalan"
    pal.placement = QgsPalLayerSettings.Line
    pal.enabled = True
    pal.setFormat(make_text_format(6.0, PAL["ink"], bold=True, buffer_hex=PAL["white"], family=FONT_BODY))
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))


def style_patrol_routes(layer: QgsVectorLayer) -> None:
    sym = QgsLineSymbol()
    casing = QgsSimpleLineSymbolLayer(QColor(PAL["white"]), 1.3)
    dash = QgsSimpleLineSymbolLayer(QColor(PAL["teal"]), 0.6)
    dash.setUseCustomDashPattern(True)
    dash.setCustomDashVector([3.0, 1.8])
    sym.changeSymbolLayer(0, casing)
    sym.appendSymbolLayer(dash)
    layer.setRenderer(QgsSingleSymbolRenderer(sym))


def style_police(layer: QgsVectorLayer) -> None:
    sym = QgsMarkerSymbol()
    halo = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Circle, 4.4)
    halo.setColor(QColor(PAL["ice"]))
    halo.setStrokeColor(QColor(PAL["ink"]))
    halo.setStrokeWidth(0.35)
    core = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Diamond, 2.9)
    core.setColor(QColor(PAL["teal"]))
    core.setStrokeColor(QColor(PAL["ink"]))
    core.setStrokeWidth(0.35)
    sym.changeSymbolLayer(0, halo)
    sym.appendSymbolLayer(core)
    layer.setRenderer(QgsSingleSymbolRenderer(sym))

    pal = QgsPalLayerSettings()
    pal.fieldName = "nama"
    pal.enabled = True
    pal.dist = 1.6
    pal.setFormat(make_text_format(5.8, PAL["ink"], bold=True, buffer_hex=PAL["white"], family=FONT_BODY))
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))


def style_pju_solutions(layer: QgsVectorLayer) -> None:
    specs = [
        ("Pos Pantau & Panic Button + CCTV", "Pos Pantau & Panic Button", 3.5, False),
        ("CCTV Analitik + PJU Pintar Terpadu", "CCTV Analitik + PJU Pintar", 2.9, True),
        ("PJU Pintar LED Solar + Sensor Gerak", "PJU Pintar LED Solar", 2.6, False),
    ]
    cats = []
    for val, label, sz, is_cctv in specs:
        sym = QgsMarkerSymbol()
        halo = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Circle, sz + 1.8)
        halo.setColor(QColor(255, 201, 77, 70))
        if is_cctv:
            halo.setStrokeColor(QColor(PAL["teal"]))
            halo.setStrokeWidth(0.35)
        else:
            halo.setStrokeStyle(Qt.NoPen)
        core = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Star, sz)
        core.setColor(QColor(PAL["lamp"]))
        core.setStrokeColor(QColor(PAL["ink"]))
        core.setStrokeWidth(0.25)
        sym.changeSymbolLayer(0, halo)
        sym.appendSymbolLayer(core)
        cats.append(QgsRendererCategory(val, sym, label))

    layer.setRenderer(QgsCategorizedSymbolRenderer("jenis_solusi", cats))


def add_box(layout: QgsPrintLayout, x: float, y: float, w: float, h: float, fill: str, border: str, bw: float = 0.35, radius: float = 0.0) -> QgsLayoutItemShape:
    shape_item = QgsLayoutItemShape(layout)
    shape_item.setShapeType(QgsLayoutItemShape.Rectangle)
    shape_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    shape_item.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
    if radius > 0:
        shape_item.setCornerRadius(QgsLayoutMeasurement(radius, QgsUnitTypes.LayoutMillimeters))
    props = {"color": fill}
    if bw <= 0:
        props["outline_style"] = "no"
    else:
        props["outline_color"] = border
        props["outline_width"] = str(bw)
    shape_item.setSymbol(QgsFillSymbol.createSimple(props))
    layout.addLayoutItem(shape_item)
    return shape_item


def add_brutal_card(layout: QgsPrintLayout, x: float, y: float, w: float, h: float, fill: str = PAL["white"], border: str = PAL["ink"], bw: float = 0.8, shadow_offset: float = 1.6, radius: float = 4.0) -> None:
    add_box(layout, x + shadow_offset, y + shadow_offset, w, h, fill=PAL["ink"], border=PAL["ink"], bw=0.0, radius=radius)
    add_box(layout, x, y, w, h, fill=fill, border=border, bw=bw, radius=radius)


def add_label(layout: QgsPrintLayout, text: str, x: float, y: float, w: float, h: float, size_pt: float, color: str = PAL["ink"], bold: bool = False, align=Qt.AlignLeft | Qt.AlignTop, family: str = None) -> QgsLayoutItemLabel:
    lbl = QgsLayoutItemLabel(layout)
    lbl.setText(text)
    lbl.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    lbl.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
    lbl.setFont(make_font(family or FONT_BODY, size_pt, bold=bold))
    lbl.setFontColor(QColor(color))
    lbl.setHAlign(Qt.AlignCenter if (align & Qt.AlignHCenter) else Qt.AlignLeft)
    lbl.setVAlign(Qt.AlignVCenter if (align & Qt.AlignVCenter) else Qt.AlignTop)
    lbl.setMarginX(1.5)
    lbl.setMarginY(1.0)
    layout.addLayoutItem(lbl)
    return lbl


def build_layout(project: QgsProject, layers_dict: dict) -> None:
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Layout Peta Dark-Zone Crime & Solusi PJU Kota Medan")

    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

    # Page background #EEEEEE
    add_box(layout, 0, 0, 420, 297, fill=PAL["paper"], border=PAL["ink"], bw=0.0)

    # ---- 1. MAIN OVERVIEW MAP CARD (LEFT) ----
    add_brutal_card(layout, 6, 6, 204, 283, fill=PAL["white"], border=PAL["ink"], bw=0.8, shadow_offset=1.6, radius=4.0)
    add_box(layout, 10, 9.5, 196, 8.5, fill=PAL["ice"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_label(
        layout,
        "PETA UTAMA: ANALISIS ZONA GELAP VIIRS (HEKSAGON 500M) & RUTE PATROLI KOTA MEDAN",
        12, 9.5, 192, 8.5, 9.0, PAL["ink"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY,
    )

    main_map = QgsLayoutItemMap(layout)
    main_map.attemptMove(QgsLayoutPoint(16, 22, QgsUnitTypes.LayoutMillimeters))
    main_map.attemptResize(QgsLayoutSize(186, 258, QgsUnitTypes.LayoutMillimeters))
    main_map.setBackgroundEnabled(True)
    main_map.setBackgroundColor(QColor(PAL["paper"]))
    main_map.setFrameEnabled(True)
    main_map.setFrameStrokeColor(QColor(PAL["ink"]))
    main_map.setFrameStrokeWidth(QgsLayoutMeasurement(0.55, QgsUnitTypes.LayoutMillimeters))

    main_map.zoomToExtent(QgsRectangle(98.555, 3.455, 98.785, 3.825))
    main_map.setLayers([
        layers_dict["pju"],
        layers_dict["police"],
        layers_dict["patrol"],
        layers_dict["corridors"],
        layers_dict["water"],
        layers_dict["hex"],
        layers_dict["kec"],
        layers_dict["viirs"],
    ])

    grid = QgsLayoutItemMapGrid("Grid_WGS84", main_map)
    grid.setEnabled(True)
    grid.setStyle(QgsLayoutItemMapGrid.Solid)
    grid.setIntervalX(0.05)
    grid.setIntervalY(0.05)
    grid.setGridLineColor(QColor(7, 27, 43, 30))
    grid.setGridLineWidth(0.15)
    grid.setAnnotationEnabled(True)
    grid.setAnnotationPrecision(2)
    grid.setAnnotationFont(make_font(FONT_BODY, 6.0))
    grid.setAnnotationFontColor(QColor(PAL["ink"]))
    grid.setFrameStyle(QgsLayoutItemMapGrid.Zebra)
    grid.setFrameWidth(1.4)
    grid.setFrameFillColor1(QColor(PAL["ink"]))
    grid.setFrameFillColor2(QColor(PAL["white"]))
    main_map.grids().addGrid(grid)
    layout.addLayoutItem(main_map)

    sb_main = QgsLayoutItemScaleBar(layout)
    sb_main.setStyle("Single Box")
    sb_main.setLinkedMap(main_map)
    sb_main.setUnits(QgsUnitTypes.DistanceKilometers)
    sb_main.setNumberOfSegments(4)
    sb_main.setUnitsPerSegment(2.0)
    sb_main.setUnitLabel("km")
    sb_main.setFont(make_font(FONT_BODY, 7.0, bold=True))
    sb_main.setFontColor(QColor(PAL["ink"]))
    sb_main.setFillColor(QColor(PAL["ink"]))
    sb_main.setFillColor2(QColor(PAL["white"]))
    sb_main.setLineColor(QColor(PAL["ink"]))
    sb_main.attemptMove(QgsLayoutPoint(20, 267, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(sb_main)

    # North Arrow badge
    add_brutal_card(layout, 184, 25, 13, 14, fill=PAL["ice"], border=PAL["ink"], bw=0.6, shadow_offset=0.9, radius=2.5)
    add_label(layout, "U\n▲", 184, 25.3, 13, 13.5, 9.5, PAL["ink"], bold=True, align=Qt.AlignHCenter | Qt.AlignVCenter, family=FONT_DISPLAY)

    # ---- 2. DETAIL ZOOM CARD (MIDDLE TOP) ----
    add_brutal_card(layout, 214, 6, 102, 166, fill=PAL["white"], border=PAL["ink"], bw=0.8, shadow_offset=1.6, radius=4.0)
    add_box(layout, 217.5, 9.5, 95, 8.0, fill=PAL["ice"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_label(
        layout,
        "DETAIL FOKUS 2.5D: 12 KECAMATAN (73.021 GEDUNG)",
        219, 9.5, 92, 8.0, 8.2, PAL["ink"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY,
    )

    detail_map = QgsLayoutItemMap(layout)
    detail_map.attemptMove(QgsLayoutPoint(218, 20, QgsUnitTypes.LayoutMillimeters))
    detail_map.attemptResize(QgsLayoutSize(94, 140, QgsUnitTypes.LayoutMillimeters))
    detail_map.setBackgroundEnabled(True)
    detail_map.setBackgroundColor(QColor(PAL["paper"]))
    detail_map.setFrameEnabled(True)
    detail_map.setFrameStrokeColor(QColor(PAL["ink"]))
    detail_map.setFrameStrokeWidth(QgsLayoutMeasurement(0.55, QgsUnitTypes.LayoutMillimeters))
    detail_map.setExtent(QgsRectangle(98.643, 3.553, 98.678, 3.602))
    detail_map.setLayers([
        layers_dict["pju"],
        layers_dict["police"],
        layers_dict["patrol"],
        layers_dict["corridors"],
        layers_dict["buildings"],
        layers_dict["roads"],
        layers_dict["water"],
        layers_dict["kec"],
    ])
    layout.addLayoutItem(detail_map)

    sb_det = QgsLayoutItemScaleBar(layout)
    sb_det.setStyle("Line Ticks Up")
    sb_det.setLinkedMap(detail_map)
    sb_det.setUnits(QgsUnitTypes.DistanceMeters)
    sb_det.setNumberOfSegments(2)
    sb_det.setUnitsPerSegment(500)
    sb_det.setUnitLabel("m")
    sb_det.setFont(make_font(FONT_BODY, 6.5, bold=True))
    sb_det.setFontColor(QColor(PAL["ink"]))
    sb_det.setLineColor(QColor(PAL["ink"]))
    sb_det.attemptMove(QgsLayoutPoint(220, 161, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(sb_det)

    ov = QgsLayoutItemMapOverview("Fokus_MedanBaru_Petisah", main_map)
    ov.setLinkedMap(detail_map)
    ov.setFrameSymbol(QgsFillSymbol.createSimple({
        "color": "22,125,141,28",
        "outline_color": PAL["teal"],
        "outline_width": "0.65",
    }))
    main_map.overviews().addOverview(ov)

    # ---- 3. MIDDLE BOTTOM CARD: METADATA & SUMBER DATA ----
    add_brutal_card(layout, 214, 176, 102, 113, fill=PAL["white"], border=PAL["ink"], bw=0.8, shadow_offset=1.6, radius=4.0)
    add_box(layout, 217.5, 179.5, 95, 7.5, fill=PAL["ice"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_label(layout, "IDENTITAS, REFERENSI & SUMBER DATA", 219, 179.5, 92, 7.5, 7.8, PAL["ink"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY)

    meta_text = (
        "PROGRAM STUDI: DIII - TEKNIK INFORMATIKA\n"
        "MATA KULIAH  : PRAKTIKUM SIG TA.2026/2027\n"
        "DOSEN        : Dr. Syahriol Sitorus, S.Si., M.Si.\n"
        "ASISTEN LAB  : Bernita Agustien P Habeahan & Andri Wiguna\n"
        "PENYUSUN (ORANG 5): Michael Deryl Aaron Matthew (241712042 / KOM A2)\n"
        "PERAN        : 3D Dark-Zone Crime & Building Vulnerability + Web Integrator\n\n"
        "SISTEM REFERENSI & KOORDINAT:\n"
        "• Proyeksi Peta: Geografis WGS 84 (EPSG:4326) & Metrik UTM 47N (EPSG:32647)\n"
        "• Resolusi Grid: Heksagon 500 Meter (Seluruh 21 Kecamatan Kota Medan)\n\n"
        "SUMBER DATA RESMI:\n"
        "1. Cahaya Malam: EOG / OpenGeoHub VIIRS V2.1 2024 (Zenodo DOI:10.5281/zenodo.17294744)\n"
        "2. Batas Wilayah: Peta RBI 1:50.000 Badan Informasi Geospasial (BIG)\n"
        "3. Gedung, Jalan, Sungai & Pos Polisi: OpenStreetMap API v0.6 & Nominatim\n"
        "4. Elevasi Lahan: DEM SRTM 30m (USGS) | Jaringan Patroli: OSRM Driving API\n"
        "5. Titik Rawan Kejahatan: Rilis Pemetaan Kriminalitas Polrestabes Medan"
    )
    add_label(layout, meta_text, 217.5, 189, 95, 97, 6.2, PAL["ink"], bold=False, family=FONT_BODY)

    # ---- 4. RIGHT SIDEBAR CARD: TITLE, LEGEND & SOLUTIONS ----
    add_brutal_card(layout, 320, 6, 94, 283, fill=PAL["white"], border=PAL["ink"], bw=0.8, shadow_offset=1.6, radius=4.0)
    add_box(layout, 323.5, 9.5, 87, 21, fill=PAL["ice"], border=PAL["ink"], bw=0.7, radius=3.5)
    add_label(
        layout,
        "PETA TEMATIK KERENTANAN ZONA GELAP RAWAN BEGAL & SOLUSI PJU PINTAR KOTA MEDAN",
        325, 10.5, 84, 19, 8.8, PAL["ink"], bold=True, align=Qt.AlignHCenter | Qt.AlignVCenter, family=FONT_DISPLAY,
    )

    # Legend inner frame
    add_box(layout, 323.5, 33, 87, 128, fill=PAL["paper"], border=PAL["ink"], bw=0.5, radius=3.0)
    legend = QgsLayoutItemLegend(layout)
    legend.setTitle("LEGENDA PETA")
    legend.setLinkedMap(main_map)
    legend.setAutoUpdateModel(False)
    legend.model().rootGroup().removeLayer(layers_dict["viirs"])
    legend.setBackgroundEnabled(False)
    legend.setStyleFont(QgsLegendStyle.Title, make_font(FONT_DISPLAY, 7.8, bold=True))
    legend.setStyleFont(QgsLegendStyle.Subgroup, make_font(FONT_BODY, 6.3, bold=True))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, make_font(FONT_BODY, 5.8))
    legend.setFontColor(QColor(PAL["ink"]))
    legend.setSymbolWidth(4.5)
    legend.setSymbolHeight(2.5)
    legend.setBoxSpace(1.2)
    legend.setStyleMargin(QgsLegendStyle.Subgroup, 1.3)
    legend.setStyleMargin(QgsLegendStyle.Symbol, 0.7)
    legend.setResizeToContents(False)
    legend.setColumnCount(2)
    legend.setSplitLayer(True)
    legend.attemptMove(QgsLayoutPoint(324.5, 34, QgsUnitTypes.LayoutMillimeters))
    legend.attemptResize(QgsLayoutSize(85, 125, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(legend)

    # Box: Analisis Masalah (Header Ink text white, Body White)
    add_box(layout, 323.5, 164, 87, 56, fill=PAL["white"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_box(layout, 323.5, 164, 87, 7.5, fill=PAL["ink"], border=PAL["ink"], bw=0.6, radius=2.0)
    add_label(layout, "ANALISIS MASALAH & LOKASI RAWAN", 325, 164.2, 84, 7, 7.2, PAL["white"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY)

    n_corr = layers_dict["corridors"].featureCount()
    n_pju_total = layers_dict["pju"].featureCount()
    pju_feats = list(layers_dict["pju"].getFeatures())
    n_solar = sum(1 for f in pju_feats if "Solar" in str(f["jenis_solusi"]))
    n_cctv = sum(1 for f in pju_feats if "CCTV Analitik" in str(f["jenis_solusi"]))
    n_pos = sum(1 for f in pju_feats if "Pos Pantau" in str(f["jenis_solusi"]))
    n_pat = layers_dict["patrol"].featureCount()
    pat_km = sum(float(f["panjang_km"] or 0.0) for f in layers_dict["patrol"].getFeatures())

    masalah_txt = (
        f"• Sebaran Kota (21 Kecamatan): Terpetakan {n_corr} koridor rawan curas/begal dari pusat kota "
        "(Medan Baru, Petisah, Polonia, Kota, Area) hingga Utara (Belawan, Labuhan, Marelan, Deli) & Selatan.\n"
        "• Ruas Rawan Kritis: Jl. Gatot Subroto, Jl. Sriwijaya, Jl. Jamin Ginting, Ring Road, "
        "Jl. K.L. Yos Sudarso (Belawan-Labuhan), Jl. Letda Sujono & Eks Polonia.\n"
        "• Akar Masalah: Defisit cahaya malam VIIRS (<28 DN) pada kawasan padat dengan jarak pos polisi > 1,2 km."
    )
    add_label(layout, masalah_txt, 325, 173, 84, 45, 6.0, PAL["ink"], family=FONT_BODY)

    # Box: Upaya & Solusi (Header Teal text white, Body Ice)
    add_box(layout, 323.5, 223, 87, 62, fill=PAL["ice"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_box(layout, 323.5, 223, 87, 7.5, fill=PAL["teal"], border=PAL["ink"], bw=0.6, radius=2.0)
    add_label(layout, "UPAYA & SOLUSI AKAR MASALAH", 325, 223.2, 84, 7, 7.2, PAL["white"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY)
    solusi_txt = (
        f"1. Penempatan {n_pju_total} titik solusi merata di seluruh 21 Kecamatan: {n_solar} PJU Pintar LED Solar, "
        f"{n_cctv} CCTV Analitik + PJU, dan {n_pos} Pos Pantau Panic Button (radius 165-210 m).\n"
        f"2. Optimalisasi {n_pat} Rute Patroli Malam KRYD ({pat_km:.1f} km) pukul 21.30-05.00 WIB dari Utara ke Selatan.\n"
        "3. Kontak Darurat Satgas Anti-Begal: 110 / 0812-6262-0110 (WA: 0859-3518-7563)."
    )
    add_label(layout, solusi_txt, 325, 232, 84, 51, 6.1, PAL["ink"], family=FONT_BODY)

    project.layoutManager().addLayout(layout)

    log(f"Exporting 300 DPI Print Layout -> {LAYOUT_PNG} ...")
    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = 300
    res = exporter.exportToImage(LAYOUT_PNG, settings)
    if res != QgsLayoutExporter.Success:
        raise RuntimeError(f"QgsLayoutExporter failed with code {res}")
    log("Print Layout PNG exported successfully!")


def main() -> None:
    os.chdir(BASE_DIR)
    QgsApplication.setPrefixPath(r"M:\QGIS\apps\qgis-ltr", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    load_project_fonts()

    try:
        project = QgsProject.instance()
        project.clear()
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        project.setBackgroundColor(QColor(PAL["paper"]))
        project.setFileName(QGZ_PATH)
        project.writeEntryBool("Paths", "/Absolute", False)

        viirs = QgsRasterLayer("./data/viirs_medan_2024.tif", "Citra Cahaya Malam VIIRS 2024 (EOG/Zenodo)")
        kec = QgsVectorLayer("./data/batas_kecamatan_medan.geojson", "Batas 21 Kecamatan Kota Medan (BIG)", "ogr")
        hex_l = QgsVectorLayer("./data/hex_viirs_medan_500m.geojson", "Grid Heksagon 500m — Risiko Zona Gelap", "ogr")
        water = QgsVectorLayer("./data/sungai_fokus_osm.geojson", "Sungai Babura & Deli (OSM)", "ogr")
        roads = QgsVectorLayer("./data/jalan_fokus_osm.geojson", "Jaringan Jalan Fokus (OSM)", "ogr")
        buildings = QgsVectorLayer("./data/bangunan_fokus_3d.geojson", "Bangunan 2.5D Fokus — Kerentanan Gelap", "ogr")
        corridors = QgsVectorLayer("./data/koridor_rawan_begal.geojson", "Koridor Rawan Begal", "ogr")
        patrol = QgsVectorLayer("./data/solusi_rute_patroli.geojson", "Rute Patroli Malam KRYD", "ogr")
        police = QgsVectorLayer("./data/polisi_eksisting.geojson", "Kantor / Pos Polisi (OSM)", "ogr")
        pju = QgsVectorLayer("./data/solusi_pju_cctv.geojson", "Solusi: PJU Pintar & CCTV", "ogr")

        layers_dict = {
            "viirs": viirs,
            "kec": kec,
            "hex": hex_l,
            "water": water,
            "roads": roads,
            "buildings": buildings,
            "corridors": corridors,
            "patrol": patrol,
            "police": police,
            "pju": pju,
        }

        for k, lyr in layers_dict.items():
            if not lyr.isValid():
                raise RuntimeError(f"Invalid layer {k}: {lyr.source()}")

        style_viirs_raster(viirs)
        style_kecamatan(kec)
        style_hex_grid(hex_l)
        style_water(water)
        style_roads(roads)
        style_buildings_25d(buildings)
        style_crime_corridors(corridors)
        style_patrol_routes(patrol)
        style_police(police)
        style_pju_solutions(pju)

        for key in ["pju", "police", "patrol", "corridors", "buildings", "roads", "water", "hex", "kec", "viirs"]:
            project.addMapLayer(layers_dict[key])

        build_layout(project, layers_dict)

        if not project.write(QGZ_PATH):
            raise RuntimeError("Failed to write QGZ project")
        log(f"Saved QGIS project -> {QGZ_PATH}")

        with zipfile.ZipFile(QGZ_PATH) as zf:
            qgs_name = [n for n in zf.namelist() if n.endswith(".qgs")][0]
            root = ET.fromstring(zf.read(qgs_name))
            ds_list = [e.text for e in root.findall(".//maplayer/datasource") if e.text]
            assert all("M:" not in d for d in ds_list), f"Absolute path leak: {ds_list}"
            log(f"Confirmed 100% relative paths across {len(ds_list)} QGZ layers!")

    finally:
        qgs.exitQgis()


if __name__ == "__main__":
    main()
