import os
import json
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

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

PAL = {
    "ink": "#071B2B",
    "teal": "#167D8D",
    "ice": "#B9E4E8",
    "paper": "#EEEEEE",
    "white": "#FFFFFF",
    "lamp": "#FFC94D",
    "red": "#D7191C",
    "orange": "#FDAE61",
    "green": "#1A9850",
    "green_bright": "#22C55E",
    "blue": "#0284C7",
    "blue_dark": "#0369A1",
}

FONT_DISPLAY = "Segoe UI"
FONT_BODY = "Segoe UI"


def log(msg: str) -> None:
    print(f"[11_LAYOUTS] {msg}", flush=True)


def load_project_fonts() -> None:
    global FONT_DISPLAY, FONT_BODY
    fredoka_path = os.path.join(FONTS_DIR, "Fredoka.ttf")
    nunito_path = os.path.join(FONTS_DIR, "Nunito.ttf")
    if os.path.exists(fredoka_path):
        fid = QFontDatabase.addApplicationFont(fredoka_path)
        if fid != -1 and QFontDatabase.applicationFontFamilies(fid):
            FONT_DISPLAY = QFontDatabase.applicationFontFamilies(fid)[0]
    if os.path.exists(nunito_path):
        nid = QFontDatabase.addApplicationFont(nunito_path)
        if nid != -1 and QFontDatabase.applicationFontFamilies(nid):
            FONT_BODY = QFontDatabase.applicationFontFamilies(nid)[0]


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
    buf.setSize(0.75)
    buf.setColor(QColor(buffer_hex))
    fmt.setBuffer(buf)
    return fmt


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


def style_kecamatan(layer: QgsVectorLayer, label_size=6.8) -> None:
    sym = QgsFillSymbol.createSimple({
        "color": "255,255,255,95",
        "outline_color": PAL["ink"],
        "outline_width": "0.35",
        "outline_style": "dash",
    })
    layer.setRenderer(QgsSingleSymbolRenderer(sym))
    pal = QgsPalLayerSettings()
    pal.fieldName = "nama_kec"
    pal.enabled = True
    pal.setFormat(make_text_format(label_size, PAL["ink"], bold=True, buffer_hex=PAL["white"], family=FONT_BODY))
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))


def style_water(layer: QgsVectorLayer, width="0.65") -> None:
    sym = QgsLineSymbol.createSimple({"color": PAL["blue"], "width": width})
    layer.setRenderer(QgsSingleSymbolRenderer(sym))


def style_roads(layer: QgsVectorLayer) -> None:
    sym = QgsLineSymbol()
    sl = QgsSimpleLineSymbolLayer(QColor(7, 27, 43, 55), 0.18)
    sym.changeSymbolLayer(0, sl)
    layer.setRenderer(QgsSingleSymbolRenderer(sym))


def style_buildings_neutral(layer: QgsVectorLayer) -> None:
    sym = QgsFillSymbol()
    sl = QgsSimpleFillSymbolLayer(QColor(200, 214, 224, 170), Qt.SolidPattern, QColor(7, 27, 43, 95), Qt.SolidLine, 0.08)
    sym.changeSymbolLayer(0, sl)
    layer.setRenderer(QgsSingleSymbolRenderer(sym))


def make_marker_layer(layer: QgsVectorLayer, shape_type, size, fill_rgba, stroke_rgba, stroke_w=0.35, label_field=None):
    sym = QgsMarkerSymbol()
    m = QgsSimpleMarkerSymbolLayer(shape_type, size)
    m.setColor(fill_rgba)
    m.setStrokeColor(stroke_rgba)
    m.setStrokeWidth(stroke_w)
    sym.changeSymbolLayer(0, m)
    layer.setRenderer(QgsSingleSymbolRenderer(sym))
    if label_field:
        pal = QgsPalLayerSettings()
        pal.fieldName = label_field
        pal.enabled = True
        pal.dist = 1.3
        pal.setFormat(make_text_format(5.4, PAL["ink"], bold=True, buffer_hex=PAL["white"], family=FONT_BODY))
        layer.setLabelsEnabled(True)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))


def build_common_frame(
    project: QgsProject,
    layout_name: str,
    main_title: str,
    detail_title: str,
    sidebar_title: str,
    main_layers: list,
    detail_layers: list,
    detail_extent: QgsRectangle,
    legend_exclude_layers: list,
    meta_text: str,
    masalah_txt: str,
    solusi_txt: str,
    out_png: str,
    out_qgz: str,
    overview_name: str,
) -> None:
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layout_name)

    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

    add_box(layout, 0, 0, 420, 297, fill=PAL["paper"], border=PAL["ink"], bw=0.0)

    # 1. MAIN OVERVIEW MAP CARD (LEFT)
    add_brutal_card(layout, 6, 6, 204, 283, fill=PAL["white"], border=PAL["ink"], bw=0.8, shadow_offset=1.6, radius=4.0)
    add_box(layout, 10, 9.5, 196, 8.5, fill=PAL["ice"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_label(layout, main_title, 12, 9.5, 192, 8.5, 8.5, PAL["ink"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY)

    main_map = QgsLayoutItemMap(layout)
    main_map.attemptMove(QgsLayoutPoint(16, 22, QgsUnitTypes.LayoutMillimeters))
    main_map.attemptResize(QgsLayoutSize(186, 258, QgsUnitTypes.LayoutMillimeters))
    main_map.setBackgroundEnabled(True)
    main_map.setBackgroundColor(QColor(PAL["paper"]))
    main_map.setFrameEnabled(True)
    main_map.setFrameStrokeColor(QColor(PAL["ink"]))
    main_map.setFrameStrokeWidth(QgsLayoutMeasurement(0.55, QgsUnitTypes.LayoutMillimeters))
    main_map.zoomToExtent(QgsRectangle(98.555, 3.455, 98.785, 3.825))
    main_map.setLayers(main_layers)

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

    add_brutal_card(layout, 184, 25, 13, 14, fill=PAL["ice"], border=PAL["ink"], bw=0.6, shadow_offset=0.9, radius=2.5)
    add_label(layout, "U\n▲", 184, 25.3, 13, 13.5, 9.5, PAL["ink"], bold=True, align=Qt.AlignHCenter | Qt.AlignVCenter, family=FONT_DISPLAY)

    # 2. DETAIL ZOOM CARD (MIDDLE TOP)
    add_brutal_card(layout, 214, 6, 102, 166, fill=PAL["white"], border=PAL["ink"], bw=0.8, shadow_offset=1.6, radius=4.0)
    add_box(layout, 217.5, 9.5, 95, 8.0, fill=PAL["ice"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_label(layout, detail_title, 219, 9.5, 92, 8.0, 7.8, PAL["ink"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY)

    detail_map = QgsLayoutItemMap(layout)
    detail_map.attemptMove(QgsLayoutPoint(218, 20, QgsUnitTypes.LayoutMillimeters))
    detail_map.attemptResize(QgsLayoutSize(94, 140, QgsUnitTypes.LayoutMillimeters))
    detail_map.setBackgroundEnabled(True)
    detail_map.setBackgroundColor(QColor(PAL["paper"]))
    detail_map.setFrameEnabled(True)
    detail_map.setFrameStrokeColor(QColor(PAL["ink"]))
    detail_map.setFrameStrokeWidth(QgsLayoutMeasurement(0.55, QgsUnitTypes.LayoutMillimeters))
    detail_map.setExtent(detail_extent)
    detail_map.setLayers(detail_layers)
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

    ov = QgsLayoutItemMapOverview(overview_name, main_map)
    ov.setLinkedMap(detail_map)
    ov.setFrameSymbol(QgsFillSymbol.createSimple({"color": "22,125,141,28", "outline_color": PAL["teal"], "outline_width": "0.65"}))
    main_map.overviews().addOverview(ov)

    # 3. MIDDLE BOTTOM CARD: METADATA
    add_brutal_card(layout, 214, 176, 102, 113, fill=PAL["white"], border=PAL["ink"], bw=0.8, shadow_offset=1.6, radius=4.0)
    add_box(layout, 217.5, 179.5, 95, 7.5, fill=PAL["ice"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_label(layout, "IDENTITAS, REFERENSI & SUMBER DATA", 219, 179.5, 92, 7.5, 7.8, PAL["ink"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY)
    add_label(layout, meta_text, 217.5, 189, 95, 97, 6.1, PAL["ink"], bold=False, family=FONT_BODY)

    # 4. RIGHT SIDEBAR CARD
    add_brutal_card(layout, 320, 6, 94, 283, fill=PAL["white"], border=PAL["ink"], bw=0.8, shadow_offset=1.6, radius=4.0)
    add_box(layout, 323.5, 9.5, 87, 21, fill=PAL["ice"], border=PAL["ink"], bw=0.7, radius=3.5)
    add_label(layout, sidebar_title, 325, 10.5, 84, 19, 8.4, PAL["ink"], bold=True, align=Qt.AlignHCenter | Qt.AlignVCenter, family=FONT_DISPLAY)

    add_box(layout, 323.5, 33, 87, 128, fill=PAL["paper"], border=PAL["ink"], bw=0.5, radius=3.0)
    legend = QgsLayoutItemLegend(layout)
    legend.setTitle("LEGENDA PETA")
    legend.setLinkedMap(main_map)
    legend.setAutoUpdateModel(False)
    for lyr in legend_exclude_layers:
        legend.model().rootGroup().removeLayer(lyr)
    legend.setBackgroundEnabled(False)
    legend.setStyleFont(QgsLegendStyle.Title, make_font(FONT_DISPLAY, 7.8, bold=True))
    legend.setStyleFont(QgsLegendStyle.Subgroup, make_font(FONT_BODY, 6.2, bold=True))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, make_font(FONT_BODY, 5.7))
    legend.setFontColor(QColor(PAL["ink"]))
    legend.setSymbolWidth(4.5)
    legend.setSymbolHeight(2.5)
    legend.setBoxSpace(1.2)
    legend.setStyleMargin(QgsLegendStyle.Subgroup, 1.2)
    legend.setStyleMargin(QgsLegendStyle.Symbol, 0.7)
    legend.setResizeToContents(False)
    legend.setColumnCount(2)
    legend.setSplitLayer(True)
    legend.attemptMove(QgsLayoutPoint(324.5, 34, QgsUnitTypes.LayoutMillimeters))
    legend.attemptResize(QgsLayoutSize(85, 125, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(legend)

    add_box(layout, 323.5, 164, 87, 56, fill=PAL["white"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_box(layout, 323.5, 164, 87, 7.5, fill=PAL["ink"], border=PAL["ink"], bw=0.6, radius=2.0)
    add_label(layout, "ANALISIS MASALAH & LOKASI RAWAN", 325, 164.2, 84, 7, 7.2, PAL["white"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY)
    add_label(layout, masalah_txt, 325, 173, 84, 45, 5.9, PAL["ink"], family=FONT_BODY)

    add_box(layout, 323.5, 223, 87, 62, fill=PAL["ice"], border=PAL["ink"], bw=0.6, radius=3.0)
    add_box(layout, 323.5, 223, 87, 7.5, fill=PAL["teal"], border=PAL["ink"], bw=0.6, radius=2.0)
    add_label(layout, "UPAYA & SOLUSI AKAR MASALAH", 325, 223.2, 84, 7, 7.2, PAL["white"], bold=True, align=Qt.AlignLeft | Qt.AlignVCenter, family=FONT_DISPLAY)
    add_label(layout, solusi_txt, 325, 232, 84, 51, 5.9, PAL["ink"], family=FONT_BODY)

    project.layoutManager().addLayout(layout)
    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = 300
    res = exporter.exportToImage(out_png, settings)
    if res != QgsLayoutExporter.Success:
        raise RuntimeError(f"Export failed for {out_png}: {res}")
    project.write(out_qgz)
    log(f"Exported {os.path.basename(out_png)} & {os.path.basename(out_qgz)}")


def new_project(qgz_path: str) -> QgsProject:
    project = QgsProject.instance()
    project.clear()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    project.setBackgroundColor(QColor(PAL["paper"]))
    project.setFileName(qgz_path)
    project.writeEntryBool("Paths", "/Absolute", False)
    return project


def base_layers():
    kec = QgsVectorLayer("./web-peta-interaktif/data/batas_kecamatan_medan.geojson", "Batas 21 Kecamatan Kota Medan (BIG)", "ogr")
    water = QgsVectorLayer("./web-peta-interaktif/data/sungai_fokus_osm.geojson", "Sungai Kota Medan (OSM)", "ogr")
    roads = QgsVectorLayer("./data/jalan_fokus_osm.geojson", "Jaringan Jalan Fokus (OSM)", "ogr")
    buildings = QgsVectorLayer("./web-peta-interaktif/data/bangunan_fokus_3d.geojson", "Tapak Bangunan 81.584 Unit (OSM)", "ogr")
    style_kecamatan(kec)
    style_water(water)
    style_roads(roads)
    style_buildings_neutral(buildings)
    return kec, water, roads, buildings


def build_orang1_william():
    qgz = os.path.join(BASE_DIR, "Medan_UHI_Pohon_Orang1_William.qgz")
    png = os.path.join(BASE_DIR, "Layout_Peta_Orang1_William.png")
    project = new_project(qgz)
    kec, water, roads, buildings = base_layers()

    hex_uhi = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang1_masalah_uhi.geojson", "Grid Heksagon 500m - Suhu LST (°C)", "ogr")
    ranges = [
        ("Sangat Panas (> 34,5°C)", 34.5, 45.0, QColor(215, 25, 28, 190), QColor(7, 27, 43, 85)),
        ("Panas Tinggi (32,5 - 34,5°C)", 32.5, 34.5, QColor(253, 174, 97, 175), QColor(7, 27, 43, 85)),
        ("Hangat Sedang (30,5 - 32,5°C)", 30.5, 32.5, QColor(171, 221, 164, 155), QColor(7, 27, 43, 85)),
        ("Sejuk (< 30,5°C)", 20.0, 30.5, QColor(43, 131, 186, 145), QColor(7, 27, 43, 85)),
    ]
    rr = []
    for lbl, lo, hi, fc, oc in ranges:
        sym = QgsFillSymbol()
        sym.changeSymbolLayer(0, QgsSimpleFillSymbolLayer(fc, Qt.SolidPattern, oc, Qt.SolidLine, 0.14))
        rr.append(QgsRendererRange(lo, hi, sym, lbl))
    hex_uhi.setRenderer(QgsGraduatedSymbolRenderer("lst_mean", rr))

    jalur = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang1_solusi_peneduh.geojson|geometrytype=LineString", "Solusi: 10 Koridor Pohon Peneduh", "ogr")
    sym_j = QgsLineSymbol()
    c_j = QgsSimpleLineSymbolLayer(QColor(PAL["white"]), 1.7)
    core_j = QgsSimpleLineSymbolLayer(QColor(PAL["green"]), 0.95)
    sym_j.changeSymbolLayer(0, c_j)
    sym_j.appendSymbolLayer(core_j)
    jalur.setRenderer(QgsSingleSymbolRenderer(sym_j))

    halte = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang1_solusi_peneduh.geojson|geometrytype=Point", "Solusi: 14 Halte Sejuk & 150 Pohon", "ogr")
    cats = []
    sym_h = QgsMarkerSymbol()
    mh = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Square, 3.3)
    mh.setColor(QColor("#06B6D4"))
    mh.setStrokeColor(QColor(PAL["ink"]))
    mh.setStrokeWidth(0.35)
    sym_h.changeSymbolLayer(0, mh)
    cats.append(QgsRendererCategory("halte_teduh", sym_h, "14 Halte Bus Cool Roof"))

    sym_p = QgsMarkerSymbol()
    mp = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Circle, 2.0)
    mp.setColor(QColor("#22C55E"))
    mp.setStrokeColor(QColor(PAL["ink"]))
    mp.setStrokeWidth(0.25)
    sym_p.changeSymbolLayer(0, mp)
    cats.append(QgsRendererCategory("pohon_3d_koridor", sym_p, "150 Titik Pohon Peneduh"))
    halte.setRenderer(QgsCategorizedSymbolRenderer("sub_tipe", cats))

    for l in [halte, jalur, buildings, roads, water, hex_uhi, kec]:
        if not l.isValid():
            raise RuntimeError(f"Invalid Orang1 layer {l.name()}")
        project.addMapLayer(l)

    meta = (
        "PROGRAM STUDI: D-3 TEKNIK INFORMATIKA\n"
        "MATA KULIAH  : PRAKTIKUM SIG TA.2026/2027\n"
        "DOSEN        : Dr. Syahriol Sitorus, S.Si., M.IT.\n"
        "ASISTEN LAB  : Andri Wiguna\n"
        "PENYUSUN (ORANG 1): William Tanu Wijaya (241712036 / KOM A2'24)\n"
        "TOPIK        : Micro-UHI Suhu Permukaan & Koridor Pohon Peneduh\n\n"
        "SISTEM REFERENSI & KOORDINAT:\n"
        "• Proyeksi Peta: WGS 84 (EPSG:4326) & UTM 47N (EPSG:32647)\n"
        "• Resolusi Grid: Heksagon 500 Meter (1.470 Sel · 21 Kecamatan)\n\n"
        "SUMBER DATA RESMI:\n"
        "1. Suhu Permukaan (LST): Citra Landsat 8/9 OLI/TIRS 30m (USGS)\n"
        "2. Batas Wilayah: Peta RBI 1:50.000 BIG\n"
        "3. Jalan Arteri & Bangunan: OpenStreetMap API v0.6"
    )
    masalah = (
        "• Sebaran Kota (21 Kecamatan): Dari 1.470 petak heksagon, suhu permukaan awal "
        "berkisar 27,39°C hingga 38,28°C (rata-rata 32,32°C).\n"
        "• Zona Hotspot (>34,5°C): Terkonsentrasi pada koridor jalan arteri padat dan "
        "pusat kota (Medan Timur, Perjuangan, Petisah, Barat, dan Kota).\n"
        "• Akar Masalah: Permukaan aspal serta atap beton terbuka minim kanopi pohon peneduh."
    )
    solusi = (
        "1. Penanaman pohon Trembesi & Mahoni pada 10 koridor jalan arteri utama "
        "dengan 150 titik model pohon peneduh 3D.\n"
        "2. Pembangunan 14 Halte Bus Beratap Sejuk (Cool Roof) pada titik tunggu ramai.\n"
        "3. Dampak Simulasi Terukur: Rata-rata suhu permukaan kota turun menjadi 30,77°C "
        "(-1,55°C hingga -3,6°C di sepanjang koridor hijau)."
    )

    build_common_frame(
        project,
        "Layout Peta Micro-UHI & Pohon Peneduh (William)",
        "PETA UTAMA: SUHU PERMUKAAN LANDSAT (HEKSAGON 500M) & KORIDOR PENEDUH",
        "DETAIL FOKUS: KORIDOR ARTERI PANAS PUSAT KOTA MEDAN",
        "PETA TEMATIK SUHU PANAS (MICRO-UHI) & SOLUSI POHON PENEDUH KOTA MEDAN",
        [halte, jalur, water, hex_uhi, kec],
        [halte, jalur, buildings, roads, water, kec],
        QgsRectangle(98.645, 3.560, 98.700, 3.615),
        [],
        meta, masalah, solusi, png, qgz, "Fokus_UHI_William",
    )


def build_orang2_jordan():
    qgz = os.path.join(BASE_DIR, "Medan_RTH_NDVI_Orang2_Jordan.qgz")
    png = os.path.join(BASE_DIR, "Layout_Peta_Orang2_Jordan.png")
    project = new_project(qgz)
    kec, water, roads, buildings = base_layers()

    ndvi_tif = QgsRasterLayer("./data/ndvi_medan_sentinel2.tif", "Citra NDVI Sentinel-2 L2A (20m)")
    shader = QgsRasterShader()
    ramp = QgsColorRampShader()
    ramp.setColorRampType(QgsColorRampShader.Interpolated)
    ramp.setColorRampItemList([
        QgsColorRampShader.ColorRampItem(-0.15, QColor(215, 48, 39, 170), "-0,15 (Terbangun)"),
        QgsColorRampShader.ColorRampItem(0.111, QColor(252, 141, 89, 155), "0,11 (Defisit)"),
        QgsColorRampShader.ColorRampItem(0.236, QColor(254, 224, 139, 140), "0,24 (Sedang)"),
        QgsColorRampShader.ColorRampItem(0.65, QColor(26, 152, 80, 155), "0,65+ (Rimbun)"),
    ])
    shader.setRasterShaderFunction(ramp)
    ndvi_tif.setRenderer(QgsSingleBandPseudoColorRenderer(ndvi_tif.dataProvider(), 1, shader))
    ndvi_tif.setOpacity(0.42)

    hex_rth = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang2_masalah_rth.geojson", "Grid Heksagon 500m - Indeks NDVI", "ogr")
    ranges = [
        ("Sangat Gersang (NDVI <= 0,05)", -1.0, 0.05, QColor(215, 48, 39, 190), QColor(7, 27, 43, 85)),
        ("Defisit Kritis (0,05 - 0,111)", 0.05, 0.111, QColor(252, 141, 89, 175), QColor(7, 27, 43, 85)),
        ("Vegetasi Sedang (0,111 - 0,236)", 0.111, 0.236, QColor(254, 224, 139, 155), QColor(7, 27, 43, 85)),
        ("Rimbun / Hijau (> 0,236)", 0.236, 1.0, QColor(26, 152, 80, 145), QColor(7, 27, 43, 85)),
    ]
    rr = []
    for lbl, lo, hi, fc, oc in ranges:
        sym = QgsFillSymbol()
        sym.changeSymbolLayer(0, QgsSimpleFillSymbolLayer(fc, Qt.SolidPattern, oc, Qt.SolidLine, 0.14))
        rr.append(QgsRendererRange(lo, hi, sym, lbl))
    hex_rth.setRenderer(QgsGraduatedSymbolRenderer("ndvi_mean", rr))

    taman = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang2_solusi_taman.geojson", "Solusi: 52 Taman Saku Hijau RTH", "ogr")
    sym_t = QgsMarkerSymbol()
    halo = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Circle, 4.3)
    halo.setColor(QColor(34, 197, 94, 80))
    halo.setStrokeColor(QColor(PAL["ink"]))
    halo.setStrokeWidth(0.25)
    core = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Triangle, 2.8)
    core.setColor(QColor(PAL["green_bright"]))
    core.setStrokeColor(QColor(PAL["ink"]))
    core.setStrokeWidth(0.3)
    sym_t.changeSymbolLayer(0, halo)
    sym_t.appendSymbolLayer(core)
    taman.setRenderer(QgsSingleSymbolRenderer(sym_t))

    for l in [taman, buildings, roads, water, hex_rth, kec, ndvi_tif]:
        if not l.isValid():
            raise RuntimeError(f"Invalid Orang2 layer {l.name()}")
        project.addMapLayer(l)

    meta = (
        "PROGRAM STUDI: D-3 TEKNIK INFORMATIKA\n"
        "MATA KULIAH  : PRAKTIKUM SIG TA.2026/2027\n"
        "DOSEN        : Dr. Syahriol Sitorus, S.Si., M.IT.\n"
        "ASISTEN LAB  : Andri Wiguna\n"
        "PENYUSUN (ORANG 2): Jordan Immanuel Munthe (231712110 / KOM A2'24)\n"
        "TOPIK        : Defisit Ruang Terbuka Hijau (NDVI) & Taman Saku\n\n"
        "SISTEM REFERENSI & KOORDINAT:\n"
        "• Proyeksi Peta: WGS 84 (EPSG:4326) & UTM 47N (EPSG:32647)\n"
        "• Resolusi Grid: Heksagon 500 Meter (1.470 Sel · 21 Kecamatan)\n\n"
        "SUMBER DATA RESMI:\n"
        "1. Indeks Vegetasi: Citra Sentinel-2 L2A B04 & B08 20m (ESA)\n"
        "2. Batas Wilayah: Peta RBI 1:50.000 BIG & Standar RTH UU 26/2007\n"
        "3. Tapak Bangunan & Jalan: OpenStreetMap API v0.6"
    )
    masalah = (
        "• Sebaran Kota (21 Kecamatan): Nilai indeks kehijauan rata-rata awal kota "
        "adalah 0,302 (rentang citra -0,15 hingga 0,78).\n"
        "• Kelurahan Defisit RTH: Medan Area (0,242), Medan Petisah (0,250), Medan Perjuangan, "
        "Medan Kota, dan Medan Baru memiliki puluhan blok padat dengan NDVI <= 0,111.\n"
        "• Akar Masalah: Tingginya tutupan atap bangunan dan minimnya lahan taman lingkungan."
    )
    solusi = (
        "1. Injeksi 52 lokasi Taman Saku Hijau Kelurahan (Pocket Park) 3D secara merata "
        "pada sel heksagon gersang ber-NDVI kritis.\n"
        "2. Rumus Simulasi: NDVI_Sim = NDVI_Awal + 0,24 * exp(-Jarak_Taman / 550m).\n"
        "3. Dampak Terukur: Rata-rata indeks kehijauan meningkat dari 0,302 menjadi 0,382 "
        "dan menurunkan jumlah blok defisit kritis secara nyata."
    )

    build_common_frame(
        project,
        "Layout Peta Defisit RTH & Taman Saku (Jordan)",
        "PETA UTAMA: INDEKS VEGETASI NDVI SENTINEL-2 & 52 TAMAN SAKU",
        "DETAIL FOKUS: BLOK DEFISIT VEGETASI PUSAT KOTA MEDAN",
        "PETA TEMATIK DEFISIT RUANG TERBUKA HIJAU (NDVI) & SOLUSI TAMAN SAKU MEDAN",
        [taman, water, hex_rth, kec, ndvi_tif],
        [taman, buildings, roads, water, kec],
        QgsRectangle(98.650, 3.558, 98.708, 3.612),
        [ndvi_tif],
        meta, masalah, solusi, png, qgz, "Fokus_RTH_Jordan",
    )


def build_orang3_visel():
    qgz = os.path.join(BASE_DIR, "Medan_Banjir_RS_Orang3_Visel.qgz")
    png = os.path.join(BASE_DIR, "Layout_Peta_Orang3_Visel.png")
    project = new_project(qgz)
    kec, water, roads, buildings = base_layers()

    dem_tif = QgsRasterLayer("./data/dem_medan_srtm.tif", "Topografi DEM SRTM 30m (USGS)")
    shader = QgsRasterShader()
    ramp = QgsColorRampShader()
    ramp.setColorRampType(QgsColorRampShader.Interpolated)
    ramp.setColorRampItemList([
        QgsColorRampShader.ColorRampItem(0, QColor(3, 105, 161, 180), "0 mdpl (Pesisir)"),
        QgsColorRampShader.ColorRampItem(15, QColor(56, 189, 248, 130), "15 mdpl"),
        QgsColorRampShader.ColorRampItem(35, QColor(254, 240, 138, 110), "35 mdpl"),
        QgsColorRampShader.ColorRampItem(75, QColor(180, 83, 9, 130), "75+ mdpl"),
    ])
    shader.setRasterShaderFunction(ramp)
    dem_tif.setRenderer(QgsSingleBandPseudoColorRenderer(dem_tif.dataProvider(), 1, shader))
    dem_tif.setOpacity(0.45)

    kontur_banjir = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang3_kontur_banjir_dem.geojson", "Genangan Luapan Sungai (+2,5m HAND)", "ogr")
    kontur_banjir.setSubsetString("stage_m = 2.5")
    sym_kb = QgsFillSymbol.createSimple({"color": "2,132,199,130", "outline_color": "#0369A1", "outline_width": "0.35"})
    kontur_banjir.setRenderer(QgsSingleSymbolRenderer(sym_kb))

    kolam = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang3_solusi_evakuasi.geojson|geometrytype=Polygon", "Solusi: 12 Kolam Retensi & Pompa", "ogr")
    sym_kol = QgsFillSymbol.createSimple({"color": "14,165,233,210", "outline_color": PAL["ink"], "outline_width": "0.45"})
    kolam.setRenderer(QgsSingleSymbolRenderer(sym_kol))

    rute = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang3_solusi_evakuasi.geojson|geometrytype=LineString", "Solusi: 13 Rute Evakuasi Medis", "ogr")
    sym_r = QgsLineSymbol()
    c_r = QgsSimpleLineSymbolLayer(QColor(PAL["white"]), 1.4)
    d_r = QgsSimpleLineSymbolLayer(QColor("#F97316"), 0.75)
    d_r.setUseCustomDashPattern(True)
    d_r.setCustomDashVector([2.5, 1.5])
    sym_r.changeSymbolLayer(0, c_r)
    sym_r.appendSymbolLayer(d_r)
    rute.setRenderer(QgsSingleSymbolRenderer(sym_r))

    pts = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang3_solusi_evakuasi.geojson|geometrytype=Point", "Titik Banjir, 59 RS & 36 Posko", "ogr")
    cats = []
    for val, lbl, shp, sz, col in [
        ("titik_banjir_visel", "13 Titik Banjir Resmi", QgsSimpleMarkerSymbolLayer.Circle, 3.4, "#1D4ED8"),
        ("rs_rujukan_banjir", "59 RS Rujukan Banjir", QgsSimpleMarkerSymbolLayer.Cross2, 2.5, "#DC2626"),
        ("posko_evakuasi", "36 Posko Evakuasi Tinggi", QgsSimpleMarkerSymbolLayer.Triangle, 2.7, "#10B981"),
    ]:
        sym = QgsMarkerSymbol()
        m = QgsSimpleMarkerSymbolLayer(shp, sz)
        m.setColor(QColor(col))
        m.setStrokeColor(QColor(PAL["ink"]))
        m.setStrokeWidth(0.3)
        sym.changeSymbolLayer(0, m)
        cats.append(QgsRendererCategory(val, sym, lbl))
    pts.setRenderer(QgsCategorizedSymbolRenderer("sub_tipe", cats))

    for l in [pts, rute, kolam, buildings, roads, water, kontur_banjir, kec, dem_tif]:
        if not l.isValid():
            raise RuntimeError(f"Invalid Orang3 layer {l.name()}")
        project.addMapLayer(l)

    meta = (
        "PROGRAM STUDI: D-3 TEKNIK INFORMATIKA\n"
        "MATA KULIAH  : PRAKTIKUM SIG TA.2026/2027\n"
        "DOSEN        : Dr. Syahriol Sitorus, S.Si., M.IT.\n"
        "ASISTEN LAB  : Andri Wiguna\n"
        "PENYUSUN (ORANG 3): Visela Benedicta Simarmata (241712031 / KOM A2'24)\n"
        "TOPIK        : Luapan Banjir Sungai HAND, RS Rujukan & Evakuasi\n\n"
        "SISTEM REFERENSI & KOORDINAT:\n"
        "• Proyeksi Peta: WGS 84 (EPSG:4326) & UTM 47N (EPSG:32647)\n"
        "• Resolusi Topografi: DEM SRTM 30 Meter & Grid Heksagon 500m\n\n"
        "SUMBER DATA RESMI:\n"
        "1. Kejadian Banjir: forestearth.id (28-29 Okt 2026) & BPBD Medan\n"
        "2. Elevasi Lahan: DEM SRTM 30m (USGS / BIG) & 13 Sungai Utama OSM\n"
        "3. Rumah Sakit Rujukan: 59 Titik RS OpenStreetMap API"
    )
    masalah = (
        "• Sebaran Kota (21 Kecamatan): Luapan DAS Sungai Deli, Babura, Belawan, dan Badera "
        "pada skenario +2,5 m memicu genangan seluas 234,33 km² (model HAND).\n"
        "• Titik Kritis: 13 titik banjir resmi (Sei Mati 1,5 m, Aur 1,5 m, Kwala Bekala 1,0 m) "
        "berdampak pada ribuan gedung di Medan Petisah, Baru, Area, Polonia, dan Barat.\n"
        "• Akar Masalah: Cekungan lembah sungai padat dan minim tampungan retensi air."
    )
    solusi = (
        "1. Pembangunan 12 Kolam Retensi & Rumah Pompa yang menyurutkan tinggi muka air "
        "-1,5 m sehingga luas genangan turun dari 234,33 km² menjadi 122,19 km².\n"
        "2. Penetapan 36 Posko Evakuasi Tanah Tinggi & pemetaan 59 Rumah Sakit Rujukan.\n"
        "3. Pembuatan 13 Rute Evakuasi jalan raya tercepat dari titik banjir ke RS dan posko."
    )

    build_common_frame(
        project,
        "Layout Peta Luapan Banjir & Evakuasi (Visela)",
        "PETA UTAMA: GENANGAN LEMBAH SUNGAI (+2,5M), 59 RS & POSKO EVAKUASI",
        "DETAIL FOKUS: BANTARAN SUNGAI DELI, BABURA & RUTE EVAKUASI",
        "PETA TEMATIK KERENTANAN BANJIR SUNGAI, RS RUJUKAN & EVAKUASI MEDAN",
        [pts, rute, kolam, water, kontur_banjir, kec, dem_tif],
        [pts, rute, kolam, buildings, roads, water, kontur_banjir, kec],
        QgsRectangle(98.650, 3.550, 98.698, 3.612),
        [dem_tif],
        meta, masalah, solusi, png, qgz, "Fokus_Banjir_Visel",
    )


def build_orang4_peter():
    qgz = os.path.join(BASE_DIR, "Medan_Damkar_Isochrone_Orang4_Peter.qgz")
    png = os.path.join(BASE_DIR, "Layout_Peta_Orang4_Peter.png")
    project = new_project(qgz)
    kec, water, roads, buildings = base_layers()

    hex_damkar = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang4_masalah_damkar.geojson", "Grid Heksagon 500m - Kepadatan Blindspot", "ogr")
    ranges = [
        ("Sangat Padat (> 650 Gedung)", 650, 2000, QColor(103, 0, 13, 190), QColor(7, 27, 43, 85)),
        ("Padat Tinggi (350 - 650 Gedung)", 350, 650, QColor(211, 32, 32, 170), QColor(7, 27, 43, 85)),
        ("Sedang (100 - 350 Gedung)", 100, 350, QColor(251, 112, 80, 150), QColor(7, 27, 43, 85)),
        ("Rendah (< 100 Gedung)", 0, 100, QColor(254, 215, 170, 130), QColor(7, 27, 43, 85)),
    ]
    rr = []
    for lbl, lo, hi, fc, oc in ranges:
        sym = QgsFillSymbol()
        sym.changeSymbolLayer(0, QgsSimpleFillSymbolLayer(fc, Qt.SolidPattern, oc, Qt.SolidLine, 0.14))
        rr.append(QgsRendererRange(lo, hi, sym, lbl))
    hex_damkar.setRenderer(QgsGraduatedSymbolRenderer("jml_bangunan", rr))

    iso_eks = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang4_jangkauan_isochrone.geojson", "Isochrone <=10m Eksisting", "ogr")
    iso_eks.setSubsetString("mode_iso = 'eksisting'")
    sym_ie = QgsFillSymbol.createSimple({"color": "34,197,94,110", "outline_color": "#15803D", "outline_width": "0.55"})
    iso_eks.setRenderer(QgsSingleSymbolRenderer(sym_ie))

    iso_sim = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang4_jangkauan_isochrone.geojson", "Isochrone <=10m Simulasi", "ogr")
    iso_sim.setSubsetString("mode_iso = 'simulasi'")
    sym_is = QgsFillSymbol.createSimple({"color": "185,228,232,65", "outline_color": PAL["teal"], "outline_width": "0.5", "outline_style": "dash"})
    iso_sim.setRenderer(QgsSingleSymbolRenderer(sym_is))

    pts = QgsVectorLayer("./web-peta-interaktif/data/integrasi_tim/orang4_solusi_hidran.geojson", "Pos Damkar, 16 Hidran & 31 Pasar", "ogr")
    cats = []
    for val, lbl, shp, sz, col in [
        ("pos_damkar_eksisting", "2 Pos Damkar Eksisting", QgsSimpleMarkerSymbolLayer.Square, 3.8, "#991B1B"),
        ("pos_damkar_solusi", "20 Usulan Pos Damkar Baru", QgsSimpleMarkerSymbolLayer.Diamond, 3.3, "#DC2626"),
        ("hidran_darurat", "16 Hidran Air Darurat", QgsSimpleMarkerSymbolLayer.Circle, 2.8, "#3B82F6"),
        ("pasar_medan", "31 Pasar Tradisional", QgsSimpleMarkerSymbolLayer.Triangle, 2.4, "#EAB308"),
    ]:
        sym = QgsMarkerSymbol()
        m = QgsSimpleMarkerSymbolLayer(shp, sz)
        m.setColor(QColor(col))
        m.setStrokeColor(QColor(PAL["ink"]))
        m.setStrokeWidth(0.3)
        sym.changeSymbolLayer(0, m)
        cats.append(QgsRendererCategory(val, sym, lbl))
    pts.setRenderer(QgsCategorizedSymbolRenderer("sub_tipe", cats))

    for l in [pts, iso_eks, iso_sim, buildings, roads, water, hex_damkar, kec]:
        if not l.isValid():
            raise RuntimeError(f"Invalid Orang4 layer {l.name()}")
        project.addMapLayer(l)

    meta = (
        "PROGRAM STUDI: D-3 TEKNIK INFORMATIKA\n"
        "MATA KULIAH  : PRAKTIKUM SIG TA.2026/2027\n"
        "DOSEN        : Dr. Syahriol Sitorus, S.Si., M.IT.\n"
        "ASISTEN LAB  : Andri Wiguna\n"
        "PENYUSUN (ORANG 4): Peter Rangga Situmorang (241712039 / KOM A2'24)\n"
        "TOPIK        : Blindspot Pemadam Kebakaran >10 Menit & Hidran\n\n"
        "SISTEM REFERENSI & KOORDINAT:\n"
        "• Proyeksi Peta: WGS 84 (EPSG:4326) & UTM 47N (EPSG:32647)\n"
        "• Resolusi Grid: Heksagon 500 Meter (1.470 Sel · 21 Kecamatan)\n\n"
        "SUMBER DATA RESMI:\n"
        "1. Isochrone Jalan: OpenRouteService (ORS) Driving-Car 5 & 10 Menit\n"
        "2. Pos Damkar & Pasar: Dinas P2K Kota Medan & 31 Titik Pasar OSM\n"
        "3. Tapak Bangunan & Batas Wilayah: OpenStreetMap & RBI 50K BIG"
    )
    masalah = (
        "• Sebaran Kota (21 Kecamatan): Dengan hanya 2 pos pemadam eksisting, "
        "area layanan <= 10 menit baru menjangkau 87,21 km² di pusat kota.\n"
        "• Area Blindspot (>10 Menit): Sebanyak 383.754 unit bangunan pada agregat heksagon "
        "di kecamatan pinggiran dan pasar padat (Amplas, Marelan, Belawan) terlambat dijangkau.\n"
        "• Akar Masalah: Kurangnya pos pembantu dan hidran air di kawasan pasar padat."
    )
    solusi = (
        "1. Penambahan 20 usulan Pos Pemadam Baru secara merata di luar jangkauan "
        "isochrone eksisting 10 menit pada koridor strategis.\n"
        "2. Pemasangan 16 Hidran Air Darurat bertekanan tinggi di sekitar 31 Pasar Tradisional.\n"
        "3. Dampak Terukur: Bangunan di luar jangkauan >10 menit menyusut drastis dari "
        "383.754 menjadi tersisa 2.710 unit serta seluruh 31 pasar terlindungi."
    )

    build_common_frame(
        project,
        "Layout Peta Jangkauan Damkar & Hidran (Peter)",
        "PETA UTAMA: BLINDSPOT DAMKAR >10 MENIT & EXPANSI ISOCHRONE BARU",
        "DETAIL FOKUS: JANGKAUAN ISOCHRONE, PASAR TRADISIONAL & HIDRAN",
        "PETA TEMATIK JANGKAUAN PEMADAM KEBAKARAN & SOLUSI HIDRAN MEDAN",
        [pts, iso_eks, iso_sim, water, hex_damkar, kec],
        [pts, iso_eks, iso_sim, buildings, roads, water, kec],
        QgsRectangle(98.645, 3.550, 98.712, 3.618),
        [],
        meta, masalah, solusi, png, qgz, "Fokus_Damkar_Peter",
    )


def build_orang5_michael():
    qgz = os.path.join(BASE_DIR, "Medan_DarkZone_Crime_Orang5.qgz")
    png = os.path.join(BASE_DIR, "Layout_Peta_Orang5.png")
    project = new_project(qgz)
    kec, water, roads, buildings = base_layers()

    viirs = QgsRasterLayer("./data/viirs_medan_2024.tif", "Citra Cahaya Malam VIIRS 2024 (EOG/Zenodo)")
    shader = QgsRasterShader()
    ramp = QgsColorRampShader()
    ramp.setColorRampType(QgsColorRampShader.Interpolated)
    ramp.setColorRampItemList([
        QgsColorRampShader.ColorRampItem(0, QColor(7, 27, 43, 230), "0 (Gelap)"),
        QgsColorRampShader.ColorRampItem(15, QColor(15, 76, 92, 205), "15 (Redup)"),
        QgsColorRampShader.ColorRampItem(30, QColor(22, 125, 141, 185), "30 (Sedang)"),
        QgsColorRampShader.ColorRampItem(55, QColor(185, 228, 232, 140), "55 (Terang)"),
        QgsColorRampShader.ColorRampItem(95, QColor(255, 255, 255, 80), "95+ (Pusat)"),
    ])
    shader.setRasterShaderFunction(ramp)
    viirs.setRenderer(QgsSingleBandPseudoColorRenderer(viirs.dataProvider(), 1, shader))
    viirs.setOpacity(0.55)

    hex_l = QgsVectorLayer("./web-peta-interaktif/data/hex_viirs_medan_500m.geojson", "Grid Heksagon 500m - Risiko Zona Gelap", "ogr")
    ranges = [
        ("Kritis (68 - 100)", 68.0, 100.1, QColor(7, 27, 43, 190), QColor(7, 27, 43, 90)),
        ("Tinggi (50 - 68)", 50.0, 68.0, QColor(15, 76, 92, 150), QColor(7, 27, 43, 90)),
        ("Sedang (34 - 50)", 34.0, 50.0, QColor(22, 125, 141, 120), QColor(7, 27, 43, 90)),
        ("Rendah (0 - 34)", 0.0, 34.0, QColor(185, 228, 232, 110), QColor(7, 27, 43, 90)),
    ]
    rr = []
    for lbl, lo, hi, fc, oc in ranges:
        sym = QgsFillSymbol()
        sym.changeSymbolLayer(0, QgsSimpleFillSymbolLayer(fc, Qt.SolidPattern, oc, Qt.SolidLine, 0.15))
        rr.append(QgsRendererRange(lo, hi, sym, lbl))
    hex_l.setRenderer(QgsGraduatedSymbolRenderer("risk_score", rr))

    # Color buildings by status_rawan
    cats_b = []
    for val, lbl, rcol, wcol in [
        ("Tinggi", "Bangunan Gelap Rawan", QColor(PAL["ink"]), QColor(7, 27, 43, 235)),
        ("Sedang", "Bangunan Waspada", QColor(PAL["teal"]), QColor(7, 27, 43, 200)),
        ("Rendah", "Bangunan Terang", QColor(PAL["ice"]), QColor(22, 125, 141, 160)),
    ]:
        sym = QgsFillSymbol()
        sym.changeSymbolLayer(0, QgsSimpleFillSymbolLayer(wcol, Qt.SolidPattern, QColor(PAL["ink"]), Qt.SolidLine, 0.08))
        rsl = QgsSimpleFillSymbolLayer(rcol, Qt.SolidPattern, QColor(255, 255, 255, 90), Qt.SolidLine, 0.06)
        rsl.setDataDefinedProperty(QgsSymbolLayer.PropertyOffset, QgsProperty.fromExpression("array(-min(height_m, 35) * 0.035, -min(height_m, 35) * 0.05)"))
        sym.appendSymbolLayer(rsl)
        cats_b.append(QgsRendererCategory(val, sym, lbl))
    buildings.setRenderer(QgsCategorizedSymbolRenderer("status_rawan", cats_b))

    corridors = QgsVectorLayer("./web-peta-interaktif/data/koridor_rawan_begal.geojson", "24 Koridor Rawan Begal", "ogr")
    sym_c = QgsLineSymbol()
    c1 = QgsSimpleLineSymbolLayer(QColor(PAL["white"]), 1.6)
    c1.setPenCapStyle(Qt.RoundCap)
    c2 = QgsSimpleLineSymbolLayer(QColor(PAL["ink"]), 0.7)
    c2.setPenCapStyle(Qt.RoundCap)
    sym_c.changeSymbolLayer(0, c1)
    sym_c.appendSymbolLayer(c2)
    corridors.setRenderer(QgsSingleSymbolRenderer(sym_c))

    patrol = QgsVectorLayer("./web-peta-interaktif/data/solusi_rute_patroli.geojson", "7 Rute Patroli Malam KRYD", "ogr")
    sym_p = QgsLineSymbol()
    p1 = QgsSimpleLineSymbolLayer(QColor(PAL["white"]), 1.3)
    p2 = QgsSimpleLineSymbolLayer(QColor(PAL["teal"]), 0.6)
    p2.setUseCustomDashPattern(True)
    p2.setCustomDashVector([3.0, 1.8])
    sym_p.changeSymbolLayer(0, p1)
    sym_p.appendSymbolLayer(p2)
    patrol.setRenderer(QgsSingleSymbolRenderer(sym_p))

    police = QgsVectorLayer("./web-peta-interaktif/data/polisi_eksisting.geojson", "31 Kantor / Pos Polisi (OSM)", "ogr")
    sym_pol = QgsMarkerSymbol()
    halo = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Circle, 4.2)
    halo.setColor(QColor(PAL["ice"]))
    halo.setStrokeColor(QColor(PAL["ink"]))
    halo.setStrokeWidth(0.35)
    core = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Diamond, 2.8)
    core.setColor(QColor(PAL["teal"]))
    core.setStrokeColor(QColor(PAL["ink"]))
    core.setStrokeWidth(0.35)
    sym_pol.changeSymbolLayer(0, halo)
    sym_pol.appendSymbolLayer(core)
    police.setRenderer(QgsSingleSymbolRenderer(sym_pol))

    pju = QgsVectorLayer("./web-peta-interaktif/data/solusi_pju_cctv.geojson", "Solusi: 217 PJU Pintar & CCTV", "ogr")
    cats_p = []
    for val, lbl, sz, is_c in [
        ("Pos Pantau & Panic Button + CCTV", "Pos Pantau & Panic Button", 3.4, False),
        ("CCTV Analitik + PJU Pintar Terpadu", "CCTV Analitik + PJU Pintar", 2.8, True),
        ("PJU Pintar LED Solar + Sensor Gerak", "PJU Pintar LED Solar", 2.5, False),
    ]:
        sym = QgsMarkerSymbol()
        hl = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Circle, sz + 1.6)
        hl.setColor(QColor(255, 201, 77, 70))
        if is_c:
            hl.setStrokeColor(QColor(PAL["teal"]))
            hl.setStrokeWidth(0.35)
        else:
            hl.setStrokeStyle(Qt.NoPen)
        cr = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Star, sz)
        cr.setColor(QColor(PAL["lamp"]))
        cr.setStrokeColor(QColor(PAL["ink"]))
        cr.setStrokeWidth(0.25)
        sym.changeSymbolLayer(0, hl)
        sym.appendSymbolLayer(cr)
        cats_p.append(QgsRendererCategory(val, sym, lbl))
    pju.setRenderer(QgsCategorizedSymbolRenderer("jenis_solusi", cats_p))

    for l in [pju, police, patrol, corridors, buildings, roads, water, hex_l, kec, viirs]:
        if not l.isValid():
            raise RuntimeError(f"Invalid Orang5 layer {l.name()}")
        project.addMapLayer(l)

    meta = (
        "PROGRAM STUDI: D-3 TEKNIK INFORMATIKA\n"
        "MATA KULIAH  : PRAKTIKUM SIG TA.2026/2027\n"
        "DOSEN        : Dr. Syahriol Sitorus, S.Si., M.IT.\n"
        "ASISTEN LAB  : Andri Wiguna\n"
        "PENYUSUN (ORANG 5): Michael Deryl Aaron Matthew (241712042 / KOM A2'24)\n"
        "PERAN        : 3D Dark-Zone Crime & Integrator WebGIS 3D\n\n"
        "SISTEM REFERENSI & KOORDINAT:\n"
        "• Proyeksi Peta: WGS 84 (EPSG:4326) & UTM 47N (EPSG:32647)\n"
        "• Resolusi Grid: Heksagon 500 Meter (1.470 Sel · 21 Kecamatan)\n\n"
        "SUMBER DATA RESMI:\n"
        "1. Cahaya Malam: EOG / OpenGeoHub VIIRS V2.1 2024 (Zenodo)\n"
        "2. Batas Wilayah: Peta RBI 1:50.000 BIG\n"
        "3. 81.584 Gedung, Jalan, 31 Pos Polisi: OpenStreetMap API v0.6\n"
        "4. Koridor Rawan: Rilis Kriminalitas Polrestabes Medan & OSRM"
    )
    masalah = (
        "• Sebaran Kota (21 Kecamatan): Terpetakan 24 koridor rawan curas/begal serta "
        "14.229 dari 81.584 bangunan berada pada kelas zona gelap berisiko tinggi.\n"
        "• Ruas Kritis: Jl. Gatot Subroto, Jl. Sriwijaya, Jl. Jamin Ginting, Ring Road, "
        "Jl. K.L. Yos Sudarso (Belawan-Labuhan), Jl. Letda Sujono & Eks Polonia.\n"
        "• Akar Masalah: Defisit cahaya malam VIIRS (<25 DN) & jauh dari 31 pos polisi."
    )
    solusi = (
        "1. Penempatan 217 titik solusi merata di 21 Kecamatan: 35 PJU Pintar LED Solar, "
        "150 CCTV Analitik + PJU, dan 32 Pos Pantau Panic Button (radius 165-210 m).\n"
        "2. Optimalisasi 7 Rute Patroli Malam KRYD (196,92 km) pukul 21.30-05.00 WIB.\n"
        "3. Dampak Terukur: 5.767 gedung gelap terlindungi (sisa gelap turun ke 8.462)."
    )

    build_common_frame(
        project,
        "Layout Peta Dark-Zone Crime & Solusi PJU (Michael)",
        "PETA UTAMA: ZONA GELAP VIIRS 2024 (1.470 HEKSAGON) & RUTE PATROLI",
        "DETAIL FOKUS 2.5D: 81.584 BANGUNAN KOTA MEDAN",
        "PETA TEMATIK KERENTANAN ZONA GELAP RAWAN BEGAL & SOLUSI PJU MEDAN",
        [pju, police, patrol, corridors, water, hex_l, kec, viirs],
        [pju, police, patrol, corridors, buildings, roads, water, kec],
        QgsRectangle(98.643, 3.553, 98.678, 3.602),
        [viirs],
        meta, masalah, solusi, png, qgz, "Fokus_DarkZone_Michael",
    )


def main():
    os.chdir(BASE_DIR)
    QgsApplication.setPrefixPath(r"M:\QGIS\apps\qgis-ltr", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    load_project_fonts()
    try:
        build_orang1_william()
        build_orang2_jordan()
        build_orang3_visel()
        build_orang4_peter()
        build_orang5_michael()
    finally:
        qgs.exitQgis()


if __name__ == "__main__":
    main()
