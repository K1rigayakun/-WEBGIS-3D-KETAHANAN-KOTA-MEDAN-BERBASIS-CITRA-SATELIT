import os
import re
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DRAFT_PATH = os.path.join(BASE_DIR, "Draft_Isi_Kelompok.md")
OUT_DOCX = os.path.join(BASE_DIR, "Laporan_Kelompok.docx")
LOGO_PATH = os.path.join(BASE_DIR, "Logo USU-01.png")

BLACK = RGBColor(0x00, 0x00, 0x00)


def set_run_font(run, font_name="Times New Roman", size_pt=12, bold=False, italic=False, highlight_yellow=False):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    run.font.underline = False
    run.font.color.rgb = BLACK
    if highlight_yellow:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), font_name)
    rFonts.set(qn("w:eastAsia"), font_name)
    lang = rPr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rPr.append(lang)
    lang.set(qn("w:val"), "id-ID")


def set_para_zero_spacing(p, line_spacing=1.5, align=None, left_indent_dxa=None, first_line_dxa=None, hanging_dxa=None, keep_with_next=False, widow_control=True):
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = line_spacing
    if align is not None:
        p.alignment = align
    if left_indent_dxa is not None:
        pf.left_indent = Pt(left_indent_dxa / 20.0)
    if first_line_dxa is not None:
        pf.first_line_indent = Pt(first_line_dxa / 20.0)
    if hanging_dxa is not None:
        pf.first_line_indent = Pt(-hanging_dxa / 20.0)
    pf.keep_with_next = keep_with_next
    pf.widow_control = widow_control


def add_blank(doc, count=1, size_pt=12, line_spacing=1.0):
    for _ in range(count):
        p = doc.add_paragraph()
        set_para_zero_spacing(p, line_spacing=line_spacing, align=WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run("")
        set_run_font(r, size_pt=size_pt)


def add_rich_runs(p, text, size_pt=12, base_bold=False, base_italic=False):
    # Parse [ISI: ...] placeholders and *italic* segments
    # Split first by [ISI: ...]
    parts = re.split(r"(\[ISI:[^\]]+\])", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("[ISI:") and part.endswith("]"):
            r = p.add_run(part)
            set_run_font(r, size_pt=size_pt, bold=base_bold, italic=base_italic, highlight_yellow=True)
            continue
        # Parse *italic* and `code` inside non-placeholder part
        tokens = re.split(r"(\*[^*]+\*|`[^`]+`)", part)
        for tok in tokens:
            if not tok:
                continue
            if tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                r = p.add_run(tok[1:-1])
                set_run_font(r, size_pt=size_pt, bold=base_bold, italic=True)
            elif tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
                r = p.add_run(tok[1:-1])
                set_run_font(r, size_pt=size_pt, bold=base_bold, italic=base_italic)
            else:
                r = p.add_run(tok)
                set_run_font(r, size_pt=size_pt, bold=base_bold, italic=base_italic)


def add_field_to_paragraph(p, instr_text, cached_text="", size_pt=12, bold=False):
    r_begin = p.add_run()
    set_run_font(r_begin, size_pt=size_pt, bold=bold)
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    r_begin._r.append(fld1)

    r_instr = p.add_run()
    set_run_font(r_instr, size_pt=size_pt, bold=bold)
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr_text} "
    r_instr._r.append(it)

    r_sep = p.add_run()
    set_run_font(r_sep, size_pt=size_pt, bold=bold)
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "separate")
    r_sep._r.append(fld2)

    r_val = p.add_run(cached_text)
    set_run_font(r_val, size_pt=size_pt, bold=bold)

    r_end = p.add_run()
    set_run_font(r_end, size_pt=size_pt, bold=bold)
    fld3 = OxmlElement("w:fldChar")
    fld3.set(qn("w:fldCharType"), "end")
    r_end._r.append(fld3)


def configure_section_a4(sec, pg_fmt=None, pg_start=None, title_page=False, header_page_num=False, footer_page_num=False):
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(3.0)
    sec.bottom_margin = Cm(3.0)
    sec.left_margin = Cm(4.0)
    sec.right_margin = Cm(2.5)
    sec.header_distance = Cm(1.5)
    sec.footer_distance = Cm(1.5)
    sec.different_first_page_header_footer = title_page

    # Unlink all headers & footers
    for hf in [sec.header, sec.footer, sec.first_page_header, sec.first_page_footer]:
        hf.is_linked_to_previous = False
        for p in list(hf.paragraphs):
            p._element.getparent().remove(p._element)

    if header_page_num:
        p = sec.header.add_paragraph()
        set_para_zero_spacing(p, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_field_to_paragraph(p, "PAGE", "", size_pt=12)
    else:
        p = sec.header.add_paragraph()
        set_para_zero_spacing(p, line_spacing=1.0)

    if title_page:
        p_fp = sec.first_page_header.add_paragraph()
        set_para_zero_spacing(p_fp, line_spacing=1.0)
        pf_fp = sec.first_page_footer.add_paragraph()
        set_para_zero_spacing(pf_fp, line_spacing=1.0)

    if footer_page_num:
        p = sec.footer.add_paragraph()
        set_para_zero_spacing(p, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_field_to_paragraph(p, "PAGE", "", size_pt=12)
    else:
        p = sec.footer.add_paragraph()
        set_para_zero_spacing(p, line_spacing=1.0)

    sectPr = sec._sectPr
    for old in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(old)
    if pg_fmt:
        pg = OxmlElement("w:pgNumType")
        pg.set(qn("w:fmt"), pg_fmt)
        if pg_start is not None:
            pg.set(qn("w:start"), str(pg_start))
        sectPr.append(pg)


def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for k, v in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{k}")
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_shading(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_table_borders(tbl, sz="4", color="000000", none=False):
    tblPr = tbl._tbl.tblPr
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    val = "none" if none else "single"
    b_attrs = f'w:val="{val}"' if none else f'w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"'
    xml = f"""
    <w:tblBorders {nsdecls("w")}>
      <w:top {b_attrs}/>
      <w:left {b_attrs}/>
      <w:bottom {b_attrs}/>
      <w:right {b_attrs}/>
      <w:insideH {b_attrs}/>
      <w:insideV {b_attrs}/>
    </w:tblBorders>
    """
    tblPr.append(parse_xml(xml))


def set_row_cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    if trPr.find(qn("w:cantSplit")) is None:
        trPr.append(OxmlElement("w:cantSplit"))


def set_row_header(row):
    trPr = row._tr.get_or_add_trPr()
    if trPr.find(qn("w:tblHeader")) is None:
        trPr.append(OxmlElement("w:tblHeader"))


def set_table_col_widths(tbl, col_widths_dxa):
    tblPr = tbl._tbl.tblPr
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), str(sum(col_widths_dxa)))
    tblW.set(qn("w:type"), "dxa")
    tblPr.append(tblW)

    for old in tblPr.findall(qn("w:tblLayout")):
        tblPr.remove(old)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblPr.append(lay)

    tblGrid = tbl._tbl.tblGrid
    for old in list(tblGrid):
        tblGrid.remove(old)
    for w in col_widths_dxa:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(w))
        tblGrid.append(gc)

    for row in tbl.rows:
        for idx, cell in enumerate(row.cells):
            if idx < len(col_widths_dxa):
                tcPr = cell._tc.get_or_add_tcPr()
                for old in tcPr.findall(qn("w:tcW")):
                    tcPr.remove(old)
                tcW = OxmlElement("w:tcW")
                tcW.set(qn("w:w"), str(col_widths_dxa[idx]))
                tcW.set(qn("w:type"), "dxa")
                tcPr.append(tcW)


def setup_styles_and_numbering(doc):
    # Enable updateFields in settings.xml
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        uf = OxmlElement("w:updateFields")
        uf.set(qn("w:val"), "true")
        settings.append(uf)

    # Style helper
    def style_font(st, size_pt, bold=False, italic=False):
        st.font.name = "Times New Roman"
        st.font.size = Pt(size_pt)
        st.font.bold = bold
        st.font.italic = italic
        st.font.color.rgb = BLACK
        rPr = st._element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.insert(0, rFonts)
        rFonts.set(qn("w:ascii"), "Times New Roman")
        rFonts.set(qn("w:hAnsi"), "Times New Roman")
        rFonts.set(qn("w:cs"), "Times New Roman")
        rFonts.set(qn("w:eastAsia"), "Times New Roman")
        lang = rPr.find(qn("w:lang"))
        if lang is None:
            lang = OxmlElement("w:lang")
            rPr.append(lang)
        lang.set(qn("w:val"), "id-ID")

    def clear_style_spacing(st, line_spacing=1.5, align=None, space_before_pt=0):
        pf = st.paragraph_format
        pf.space_before = Pt(space_before_pt)
        pf.space_after = Pt(0)
        pf.line_spacing = line_spacing
        if align is not None:
            pf.alignment = align

    # Normal
    normal = doc.styles["Normal"]
    style_font(normal, 12, bold=False, italic=False)
    clear_style_spacing(normal, line_spacing=1.5)

    # JudulFrontMatter
    if "JudulFrontMatter" not in [s.name for s in doc.styles]:
        jfm = doc.styles.add_style("JudulFrontMatter", WD_STYLE_TYPE.PARAGRAPH)
    else:
        jfm = doc.styles["JudulFrontMatter"]
    jfm.base_style = normal
    style_font(jfm, 13, bold=True, italic=False)
    clear_style_spacing(jfm, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)

    # Heading 1..3
    h1 = doc.styles["Heading 1"]
    style_font(h1, 13, bold=True, italic=False)
    clear_style_spacing(h1, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    pPr1 = h1._element.get_or_add_pPr()
    for old in pPr1.findall(qn("w:outlineLvl")):
        pPr1.remove(old)
    ol1 = OxmlElement("w:outlineLvl")
    ol1.set(qn("w:val"), "0")
    pPr1.append(ol1)

    h2 = doc.styles["Heading 2"]
    style_font(h2, 12, bold=True, italic=False)
    clear_style_spacing(h2, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT)
    h2.paragraph_format.left_indent = Pt(0)
    h2.paragraph_format.first_line_indent = Pt(0)
    h2.paragraph_format.keep_with_next = True
    h2.paragraph_format.tab_stops.clear_all()
    h2.paragraph_format.tab_stops.add_tab_stop(Pt(709 / 20.0), WD_TAB_ALIGNMENT.LEFT)
    pPr2 = h2._element.get_or_add_pPr()
    for old in pPr2.findall(qn("w:outlineLvl")):
        pPr2.remove(old)
    ol2 = OxmlElement("w:outlineLvl")
    ol2.set(qn("w:val"), "1")
    pPr2.append(ol2)

    h3 = doc.styles["Heading 3"]
    style_font(h3, 12, bold=True, italic=False)
    clear_style_spacing(h3, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT)
    h3.paragraph_format.left_indent = Pt(0)
    h3.paragraph_format.first_line_indent = Pt(0)
    h3.paragraph_format.keep_with_next = True
    h3.paragraph_format.tab_stops.clear_all()
    h3.paragraph_format.tab_stops.add_tab_stop(Pt(709 / 20.0), WD_TAB_ALIGNMENT.LEFT)
    pPr3 = h3._element.get_or_add_pPr()
    for old in pPr3.findall(qn("w:outlineLvl")):
        pPr3.remove(old)
    ol3 = OxmlElement("w:outlineLvl")
    ol3.set(qn("w:val"), "2")
    pPr3.append(ol3)

    # TOC 1..4 and table of figures
    def get_or_add_style(name, sid):
        existing = {s.name.lower(): s for s in doc.styles}
        if name.lower() in existing:
            return existing[name.lower()]
        st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        st._element.set(qn("w:styleId"), sid)
        st.base_style = normal
        return st

    toc1 = get_or_add_style("toc 1", "TOC1")
    style_font(toc1, 12, bold=True, italic=False)
    clear_style_spacing(toc1, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT, space_before_pt=12)
    toc1.paragraph_format.left_indent = Pt(0)
    toc1.paragraph_format.first_line_indent = Pt(0)
    toc1.paragraph_format.tab_stops.clear_all()
    toc1.paragraph_format.tab_stops.add_tab_stop(Pt(8221 / 20.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)

    toc2 = get_or_add_style("toc 2", "TOC2")
    style_font(toc2, 12, bold=False, italic=False)
    clear_style_spacing(toc2, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT, space_before_pt=0)
    toc2.paragraph_format.left_indent = Pt(709 / 20.0)
    toc2.paragraph_format.first_line_indent = Pt(0)
    toc2.paragraph_format.tab_stops.clear_all()
    toc2.paragraph_format.tab_stops.add_tab_stop(Pt(1150 / 20.0), WD_TAB_ALIGNMENT.LEFT)
    toc2.paragraph_format.tab_stops.add_tab_stop(Pt(8221 / 20.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)

    toc3 = get_or_add_style("toc 3", "TOC3")
    style_font(toc3, 12, bold=False, italic=False)
    clear_style_spacing(toc3, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT, space_before_pt=0)
    toc3.paragraph_format.left_indent = Pt(960 / 20.0)
    toc3.paragraph_format.first_line_indent = Pt(0)
    toc3.paragraph_format.tab_stops.clear_all()
    toc3.paragraph_format.tab_stops.add_tab_stop(Pt(1580 / 20.0), WD_TAB_ALIGNMENT.LEFT)
    toc3.paragraph_format.tab_stops.add_tab_stop(Pt(8221 / 20.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)

    toc4 = get_or_add_style("toc 4", "TOC4")
    style_font(toc4, 12, bold=True, italic=False)
    clear_style_spacing(toc4, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT, space_before_pt=0)
    toc4.paragraph_format.left_indent = Pt(0)
    toc4.paragraph_format.first_line_indent = Pt(0)
    toc4.paragraph_format.tab_stops.clear_all()
    toc4.paragraph_format.tab_stops.add_tab_stop(Pt(8221 / 20.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)

    tof = get_or_add_style("table of figures", "TableofFigures")
    style_font(tof, 12, bold=False, italic=False)
    clear_style_spacing(tof, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT, space_before_pt=0)
    tof.paragraph_format.left_indent = Pt(0)
    tof.paragraph_format.tab_stops.clear_all()
    tof.paragraph_format.tab_stops.add_tab_stop(Pt(8221 / 20.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)

    # Numbering abstractNum
    numbering_part = doc.part.numbering_part
    numbering_elm = numbering_part.numbering_definitions._numbering
    abstract_id = 99
    abs_xml = f"""
    <w:abstractNum {nsdecls("w")} w:abstractNumId="{abstract_id}">
      <w:multiLevelType w:val="multilevel"/>
      <w:lvl w:ilvl="0">
        <w:start w:val="1"/>
        <w:numFmt w:val="decimal"/>
        <w:lvlText w:val="%1."/>
        <w:lvlJc w:val="left"/>
        <w:pPr><w:ind w:left="357" w:hanging="357"/></w:pPr>
        <w:rPr>
          <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
          <w:color w:val="000000"/>
          <w:sz w:val="24"/><w:szCs w:val="24"/>
        </w:rPr>
      </w:lvl>
      <w:lvl w:ilvl="1">
        <w:start w:val="1"/>
        <w:numFmt w:val="lowerLetter"/>
        <w:lvlText w:val="%2."/>
        <w:lvlJc w:val="left"/>
        <w:pPr><w:ind w:left="714" w:hanging="357"/></w:pPr>
        <w:rPr>
          <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
          <w:color w:val="000000"/>
          <w:sz w:val="24"/><w:szCs w:val="24"/>
        </w:rPr>
      </w:lvl>
    </w:abstractNum>
    """
    numbering_elm.insert(0, parse_xml(abs_xml))

    num_counter = [100]

    def new_num_id():
        num_counter[0] += 1
        nid = num_counter[0]
        num_xml = f"""
        <w:num {nsdecls("w")} w:numId="{nid}">
          <w:abstractNumId w:val="{abstract_id}"/>
          <w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride>
          <w:lvlOverride w:ilvl="1"><w:startOverride w:val="1"/></w:lvlOverride>
        </w:num>
        """
        numbering_elm.append(parse_xml(num_xml))
        return nid

    return new_num_id


def apply_num_to_paragraph(p, num_id, ilvl=0):
    pPr = p._p.get_or_add_pPr()
    numPr = OxmlElement("w:numPr")
    il = OxmlElement("w:ilvl")
    il.set(qn("w:val"), str(ilvl))
    ni = OxmlElement("w:numId")
    ni.set(qn("w:val"), str(num_id))
    numPr.append(il)
    numPr.append(ni)
    pPr.append(numPr)


def build_cover(doc):
    configure_section_a4(doc.sections[0], pg_fmt=None, title_page=False, header_page_num=False, footer_page_num=False)

    # Title: inverted triangle, 14pt bold, ALL CAPS, centered, 1.15
    p_title = doc.add_paragraph()
    set_para_zero_spacing(p_title, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r1 = p_title.add_run("WEBGIS 3D KETAHANAN KOTA MEDAN")
    set_run_font(r1, size_pt=14, bold=True)
    r1.add_break()
    r2 = p_title.add_run("BERBASIS CITRA SATELIT")
    set_run_font(r2, size_pt=14, bold=True)

    add_blank(doc, 3, size_pt=14, line_spacing=1.15)

    # Borderless centered 2-col table for 5 members
    members = [
        ("NAMA", "NIM"),
        ("WILLIAM TANU WIJAYA", "241712036"),
        ("JORDAN IMMANUEL MUNTHE", "231712110"),
        ("VISELA BENEDICTA SIMARMATA", "241712031"),
        ("PETER RANGGA SITUMORANG", "241712039"),
        ("MICHAEL DERYL AARON MATTHEW", "241712042"),
    ]
    tbl = doc.add_table(rows=len(members), cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl, none=True)
    col_w = [5800, 2400]  # total 8200 <= 8221, fits single line cleanly
    set_table_col_widths(tbl, col_w)
    for idx, (nama, nim) in enumerate(members):
        row = tbl.rows[idx]
        set_row_cant_split(row)
        for c_i, val in enumerate([nama, nim]):
            cell = row.cells[c_i]
            set_cell_margins(cell, top=24, bottom=24, left=60, right=60)
            p = cell.paragraphs[0]
            set_para_zero_spacing(p, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
            r = p.add_run(val)
            set_run_font(r, size_pt=14, bold=True)

    # Directly under table: KOM A2’24
    p_kom = doc.add_paragraph()
    set_para_zero_spacing(p_kom, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_k = p_kom.add_run("KOM A2\u201924")
    set_run_font(r_k, size_pt=14, bold=True)

    add_blank(doc, 4, size_pt=12, line_spacing=1.0)

    # Logo USU 5 x 5 cm
    p_logo = doc.add_paragraph()
    set_para_zero_spacing(p_logo, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_logo = p_logo.add_run()
    r_logo.add_picture(LOGO_PATH, width=Cm(5.0), height=Cm(5.0))

    add_blank(doc, 9, size_pt=12, line_spacing=1.0)

    inst_lines = [
        "PROGRAM STUDI D-3 TEKNIK INFORMATIKA",
        "FAKULTAS VOKASI",
        "UNIVERSITAS SUMATERA UTARA",
        "MEDAN",
        "2026",
    ]
    for line in inst_lines:
        p = doc.add_paragraph()
        set_para_zero_spacing(p, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
        r = p.add_run(line)
        set_run_font(r, size_pt=13, bold=True)


def build_front_matter(doc, kp_lines):
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    configure_section_a4(sec, pg_fmt="lowerRoman", pg_start=1, title_page=False, header_page_num=False, footer_page_num=True)

    # 1. KATA PENGANTAR
    p_kp = doc.add_paragraph(style="JudulFrontMatter")
    set_para_zero_spacing(p_kp, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r = p_kp.add_run("KATA PENGANTAR")
    set_run_font(r, size_pt=13, bold=True)
    add_blank(doc, 3, size_pt=12, line_spacing=1.0)

    for ln in kp_lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("Medan,"):
            add_blank(doc, 3, size_pt=12, line_spacing=1.0)
            p = doc.add_paragraph()
            set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.CENTER, left_indent_dxa=5103)
            add_rich_runs(p, s, size_pt=12)
            add_blank(doc, 3, size_pt=12, line_spacing=1.0)
        elif s in ("Penulis", "Michael Deryl Aaron Matthew"):
            p = doc.add_paragraph()
            set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.CENTER, left_indent_dxa=5103)
            add_rich_runs(p, s, size_pt=12)
        else:
            p = doc.add_paragraph()
            set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_dxa=709)
            add_rich_runs(p, s, size_pt=12)

    doc.add_page_break()

    # 2. DAFTAR ISI
    p_di = doc.add_paragraph(style="JudulFrontMatter")
    set_para_zero_spacing(p_di, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_run_font(p_di.add_run("DAFTAR ISI"), size_pt=13, bold=True)
    add_blank(doc, 3, size_pt=12, line_spacing=1.0)

    p_hal = doc.add_paragraph()
    set_para_zero_spacing(p_hal, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.RIGHT)
    set_run_font(p_hal.add_run("Halaman"), size_pt=12, bold=False)

    p_toc = doc.add_paragraph()
    set_para_zero_spacing(p_toc, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT)
    add_field_to_paragraph(p_toc, 'TOC \\o "1-3" \\h \\z \\t "JudulFrontMatter,4" \\n "1-1"', "", size_pt=12)

    doc.add_page_break()

    # 3. DAFTAR GAMBAR
    p_dg = doc.add_paragraph(style="JudulFrontMatter")
    set_para_zero_spacing(p_dg, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_run_font(p_dg.add_run("DAFTAR GAMBAR"), size_pt=13, bold=True)
    add_blank(doc, 3, size_pt=12, line_spacing=1.0)

    p_tof = doc.add_paragraph()
    set_para_zero_spacing(p_tof, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT)
    add_field_to_paragraph(p_tof, 'TOC \\h \\z \\c "Gambar"', "", size_pt=12)

    doc.add_page_break()

    # 4. DAFTAR TABEL
    p_dt = doc.add_paragraph(style="JudulFrontMatter")
    set_para_zero_spacing(p_dt, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_run_font(p_dt.add_run("DAFTAR TABEL"), size_pt=13, bold=True)
    add_blank(doc, 3, size_pt=12, line_spacing=1.0)

    p_tot = doc.add_paragraph()
    set_para_zero_spacing(p_tot, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT)
    add_field_to_paragraph(p_tot, 'TOC \\h \\z \\c "Tabel"', "", size_pt=12)


def build_gantt_table(doc):
    # Tabel 3.1: 3 weeks (16 Nov - 6 Des 2026) -> 23 cols total
    # Col widths: No (480) + Judul Kegiatan (2911) + 21 * 230 = 8221 DXA
    activities = [
        ("1", "Identifikasi Masalah", [1, 2, 3, 4]),
        ("2", "Analisis Kebutuhan", [4, 5, 6]),
        ("3", "Studi Literatur", [5, 6, 7, 8, 9]),
        ("4", "Perancangan Konsep Proyek", [9, 10, 11, 12]),
        ("5", "Implementasi Proyek (*Coding*)", [11, 12, 13, 14, 15, 16, 17]),
        ("6", "Pengujian Proyek", [17, 18, 19]),
        ("7", "Pengembangan Fitur Proyek", [18, 19, 20]),
        ("8", "Penyusunan Laporan Akhir", [19, 20, 21]),
    ]
    days = ["S", "S", "R", "K", "J", "S", "M"]
    tbl = doc.add_table(rows=3 + len(activities), cols=23)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl, sz="4", color="000000")
    col_w = [480, 2911] + [230] * 21
    set_table_col_widths(tbl, col_w)

    # Header merges
    tbl.cell(0, 0).merge(tbl.cell(2, 0))
    tbl.cell(0, 1).merge(tbl.cell(2, 1))
    tbl.cell(0, 2).merge(tbl.cell(0, 22))
    tbl.cell(1, 2).merge(tbl.cell(1, 8))
    tbl.cell(1, 9).merge(tbl.cell(1, 15))
    tbl.cell(1, 16).merge(tbl.cell(1, 22))

    def fill_cell(r, c, txt, align=WD_ALIGN_PARAGRAPH.CENTER, shade=None):
        cell = tbl.cell(r, c)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(cell, top=35, bottom=35, left=30, right=30)
        if shade:
            set_cell_shading(cell, shade)
        p = cell.paragraphs[0]
        set_para_zero_spacing(p, line_spacing=1.0, align=align, keep_with_next=True)
        add_rich_runs(p, txt, size_pt=10, base_bold=False)

    fill_cell(0, 0, "No")
    fill_cell(0, 1, "Judul Kegiatan")
    fill_cell(0, 2, "Minggu / Hari (16 Nov \u2013 6 Des 2026)")
    fill_cell(1, 2, "Minggu 1")
    fill_cell(1, 9, "Minggu 2")
    fill_cell(1, 16, "Minggu 3")
    for w_i in range(3):
        for d_i, d_ch in enumerate(days):
            fill_cell(2, 2 + w_i * 7 + d_i, d_ch)

    for hr in range(3):
        set_row_cant_split(tbl.rows[hr])
        set_row_header(tbl.rows[hr])

    for r_idx, (no_str, title_str, active_days) in enumerate(activities):
        rr = 3 + r_idx
        row = tbl.rows[rr]
        set_row_cant_split(row)
        keep_n = (r_idx < len(activities) - 1)
        for c_i, val, al in [(0, no_str, WD_ALIGN_PARAGRAPH.CENTER), (1, title_str, WD_ALIGN_PARAGRAPH.LEFT)]:
            cell = tbl.cell(rr, c_i)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=35, bottom=35, left=45, right=45)
            p = cell.paragraphs[0]
            set_para_zero_spacing(p, line_spacing=1.0, align=al, keep_with_next=keep_n)
            add_rich_runs(p, val, size_pt=10, base_bold=False)
        for d_num in range(1, 22):
            cell = tbl.cell(rr, 1 + d_num)
            set_cell_margins(cell, top=35, bottom=35, left=10, right=10)
            if d_num in active_days:
                set_cell_shading(cell, "8EAADB")
            p = cell.paragraphs[0]
            set_para_zero_spacing(p, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.CENTER, keep_with_next=keep_n)
            set_run_font(p.add_run(""), size_pt=10)


def build_normal_table(doc, header_row, data_rows, col_widths_dxa, keep_together=False):
    tbl = doc.add_table(rows=1 + len(data_rows), cols=len(header_row))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl, sz="4", color="000000")
    set_table_col_widths(tbl, col_widths_dxa)

    # Header row: centered, NOT bold, NO shading (C.13.5)
    hdr = tbl.rows[0]
    set_row_cant_split(hdr)
    set_row_header(hdr)
    for c_i, htxt in enumerate(header_row):
        cell = hdr.cells[c_i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(cell, top=50, bottom=50, left=70, right=70)
        p = cell.paragraphs[0]
        set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.CENTER, keep_with_next=True)
        add_rich_runs(p, htxt, size_pt=12, base_bold=False)

    for r_i, rdata in enumerate(data_rows):
        row = tbl.rows[1 + r_i]
        set_row_cant_split(row)
        keep_n = keep_together and (r_i < len(data_rows) - 1)
        for c_i, val in enumerate(rdata):
            cell = row.cells[c_i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=50, bottom=50, left=70, right=70)
            al = WD_ALIGN_PARAGRAPH.CENTER if (c_i == 0 or (len(rdata) == 4 and c_i == 3)) else WD_ALIGN_PARAGRAPH.LEFT
            p = cell.paragraphs[0]
            set_para_zero_spacing(p, line_spacing=1.5, align=al, keep_with_next=keep_n)
            add_rich_runs(p, val, size_pt=12, base_bold=False)


def build_code_block(doc, code_lines):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_table_borders(tbl, none=True)
    set_table_col_widths(tbl, [8221])
    cell = tbl.rows[0].cells[0]
    set_cell_shading(cell, "D9D9D9")
    set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
    # Remove default empty paragraph
    p0 = cell.paragraphs[0]
    for idx, line in enumerate(code_lines):
        p = p0 if idx == 0 else cell.add_paragraph()
        set_para_zero_spacing(p, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(line)
        set_run_font(r, font_name="Courier New", size_pt=10, bold=False, italic=False)
        # Preserve spaces
        for t_elm in r._r.findall(qn("w:t")):
            t_elm.set(qn("xml:space"), "preserve")


def main():
    raw = open(DRAFT_PATH, encoding="utf-8").read()
    kp_block = raw.split("## KATA PENGANTAR")[1].split("---")[0].strip().splitlines()
    dp_block = raw.split("## DAFTAR PUSTAKA")[1].strip().splitlines()

    # Extract BAB 1..5 blocks
    bab_matches = list(re.finditer(r"^## (BAB \d+)\s+(.+)$", raw, re.M))
    dp_start = raw.find("## DAFTAR PUSTAKA")
    bab_sections = []
    for i, m in enumerate(bab_matches):
        start = m.end()
        end = bab_matches[i + 1].start() if i + 1 < len(bab_matches) else dp_start
        bab_sections.append((m.group(1), m.group(2).strip(), raw[start:end].strip()))

    doc = Document()
    new_num_id = setup_styles_and_numbering(doc)

    # Section 1: Cover
    build_cover(doc)
    # Section 2: Front Matter
    build_front_matter(doc, kp_block)

    # Sections 3..7: BAB 1..5
    fig_seq_bab = {}
    tbl_seq_bab = {}

    for bab_idx, (bab_label, bab_title, content) in enumerate(bab_sections, start=1):
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
        configure_section_a4(
            sec,
            pg_fmt="decimal",
            pg_start=(1 if bab_idx == 1 else None),
            title_page=True,
            header_page_num=True,
            footer_page_num=False,
        )

        # BAB Heading 1
        p_bab = doc.add_paragraph(style="Heading 1")
        set_para_zero_spacing(p_bab, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
        r_b1 = p_bab.add_run(bab_label)
        set_run_font(r_b1, size_pt=13, bold=True)
        r_b1.add_break()
        r_b2 = p_bab.add_run(bab_title)
        set_run_font(r_b2, size_pt=13, bold=True)

        add_blank(doc, 3, size_pt=12, line_spacing=1.0)

        lines = content.splitlines()
        i = 0
        first_heading_seen = False
        prev_kind = "heading"  # heading | body | list | image | table | code
        active_list_nid = None

        while i < len(lines):
            s = lines[i].strip()
            if not s or s == "---":
                i += 1
                continue

            # Heading 2 (### X.X\tTitle)
            if s.startswith("### "):
                if first_heading_seen:
                    add_blank(doc, 2, size_pt=12, line_spacing=1.0)
                first_heading_seen = True
                htxt = s[4:].strip()
                p = doc.add_paragraph(style="Heading 2")
                set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT, keep_with_next=True)
                p.paragraph_format.left_indent = Pt(0)
                p.paragraph_format.first_line_indent = Pt(0)
                p.paragraph_format.tab_stops.clear_all()
                p.paragraph_format.tab_stops.add_tab_stop(Pt(709 / 20.0), WD_TAB_ALIGNMENT.LEFT)
                add_rich_runs(p, htxt, size_pt=12, base_bold=True)
                prev_kind = "heading"
                i += 1
                continue

            # Heading 3 (#### X.X.X\tTitle)
            if s.startswith("#### "):
                if first_heading_seen:
                    add_blank(doc, 2, size_pt=12, line_spacing=1.0)
                first_heading_seen = True
                htxt = s[5:].strip()
                p = doc.add_paragraph(style="Heading 3")
                set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT, keep_with_next=True)
                p.paragraph_format.left_indent = Pt(0)
                p.paragraph_format.first_line_indent = Pt(0)
                p.paragraph_format.tab_stops.clear_all()
                p.paragraph_format.tab_stops.add_tab_stop(Pt(709 / 20.0), WD_TAB_ALIGNMENT.LEFT)
                add_rich_runs(p, htxt, size_pt=12, base_bold=True)
                prev_kind = "heading"
                i += 1
                continue

            # Code block
            if s.startswith("```"):
                if prev_kind in ("body", "list", "image", "table"):
                    add_blank(doc, 1, size_pt=12, line_spacing=1.5)
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i].rstrip("\r\n"))
                    i += 1
                i += 1  # skip closing ```
                build_code_block(doc, code_lines)
                prev_kind = "code"
                continue

            # Image + Caption
            if s.startswith("!["):
                m_img = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", s)
                img_rel = m_img.group(2)
                img_abs = os.path.join(BASE_DIR, img_rel.replace("/", os.sep))
                if prev_kind in ("body", "list", "code", "table", "image"):
                    add_blank(doc, 1, size_pt=12, line_spacing=1.5)

                p_im = doc.add_paragraph()
                set_para_zero_spacing(p_im, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.CENTER, keep_with_next=True)
                r_im = p_im.add_run()
                # Width tuning: flowchart = 14.5 cm, Layout_Peta = 13.5 cm, screenshots = 12.2 cm
                if "flowchart" in img_rel:
                    w_cm = 13.0
                elif "Layout_Peta" in img_rel:
                    w_cm = 8.6
                else:
                    w_cm = 10.6
                r_im.add_picture(img_abs, width=Cm(w_cm))

                # Look ahead for "Gambar ..."
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                cap_line = lines[i].strip() if i < len(lines) else ""
                m_cap = re.match(r"Gambar\s+\d+\.\d+\s+(.+)$", cap_line)
                cap_title = m_cap.group(1) if m_cap else cap_line
                fig_seq_bab[bab_idx] = fig_seq_bab.get(bab_idx, 0) + 1
                seq_num = fig_seq_bab[bab_idx]

                p_cap = doc.add_paragraph()
                set_para_zero_spacing(p_cap, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.CENTER)
                set_run_font(p_cap.add_run(f"Gambar {bab_idx}."), size_pt=12)
                add_field_to_paragraph(p_cap, r"SEQ Gambar \* ARABIC \s 1", str(seq_num), size_pt=12)
                set_run_font(p_cap.add_run(" "), size_pt=12)
                add_rich_runs(p_cap, cap_title, size_pt=12)
                prev_kind = "image"
                i += 1
                continue

            # Table Caption ("Tabel X.Y ...") + Markdown Table
            if re.match(r"^Tabel\s+\d+\.\d+\s+", s):
                m_tcap = re.match(r"^Tabel\s+\d+\.\d+\s+(.+)$", s)
                t_title = m_tcap.group(1)
                if prev_kind in ("body", "list", "code", "image", "table"):
                    add_blank(doc, 1, size_pt=12, line_spacing=1.5)
                tbl_seq_bab[bab_idx] = tbl_seq_bab.get(bab_idx, 0) + 1
                seq_num = tbl_seq_bab[bab_idx]

                p_tcap = doc.add_paragraph()
                set_para_zero_spacing(p_tcap, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT, keep_with_next=True)
                set_run_font(p_tcap.add_run(f"Tabel {bab_idx}."), size_pt=12)
                add_field_to_paragraph(p_tcap, r"SEQ Tabel \* ARABIC \s 1", str(seq_num), size_pt=12)
                set_run_font(p_tcap.add_run(" "), size_pt=12)
                add_rich_runs(p_tcap, t_title, size_pt=12)

                # Advance to markdown table
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                tbl_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    tbl_lines.append(lines[i].strip())
                    i += 1

                if "Jadwal Penelitian" in t_title:
                    build_gantt_table(doc)
                else:
                    # Parse markdown table
                    hdr_cells = [c.strip() for c in tbl_lines[0].strip("|").split("|")]
                    rows_data = []
                    for tl in tbl_lines[2:]:
                        rows_data.append([c.strip() for c in tl.strip("|").split("|")])
                    if len(hdr_cells) == 5:
                        col_w = [480, 1750, 1850, 2000, 2141]  # sum 8221
                        build_normal_table(doc, hdr_cells, rows_data, col_w, keep_together=False)
                    elif len(hdr_cells) == 4:
                        col_w = [480, 2700, 3841, 1200]  # sum 8221
                        build_normal_table(doc, hdr_cells, rows_data, col_w, keep_together=False)
                prev_kind = "table"
                continue

            # Numbered list block (keep same numId if continuing 2., 3., ... after an image!)
            m_num = re.match(r"^(\d+)\.\s+", s)
            if m_num:
                if prev_kind in ("code", "image", "table"):
                    add_blank(doc, 1, size_pt=12, line_spacing=1.5)
                start_num = int(m_num.group(1))
                if start_num == 1 or active_list_nid is None:
                    active_list_nid = new_num_id()
                nid = active_list_nid
                while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                    item_txt = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                    p = doc.add_paragraph()
                    set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
                    apply_num_to_paragraph(p, nid, ilvl=0)
                    add_rich_runs(p, item_txt, size_pt=12)
                    i += 1
                prev_kind = "list"
                continue

            # Regular body paragraph
            if prev_kind in ("code", "image", "table"):
                add_blank(doc, 1, size_pt=12, line_spacing=1.5)
            p = doc.add_paragraph()
            set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_dxa=709)
            add_rich_runs(p, s, size_pt=12)
            prev_kind = "body"
            i += 1

    # Section 8: DAFTAR PUSTAKA
    sec_dp = doc.add_section(WD_SECTION.NEW_PAGE)
    configure_section_a4(sec_dp, pg_fmt="decimal", pg_start=None, title_page=True, header_page_num=True, footer_page_num=False)

    p_dp = doc.add_paragraph(style="Heading 1")
    set_para_zero_spacing(p_dp, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_run_font(p_dp.add_run("DAFTAR PUSTAKA"), size_pt=13, bold=True)
    add_blank(doc, 3, size_pt=12, line_spacing=1.0)

    for ln in dp_block:
        s = ln.strip()
        if not s:
            continue
        # Insert zero-width break after '://', '/', and '.' inside URLs so Word justify never stretches prior line
        def _wrap_url(m):
            u = m.group(0)
            prefix, rest = u.split("://", 1)
            return prefix + "://\u200b" + rest.replace("/", "/\u200b").replace(".", ".\u200b")
        s_fmt = re.sub(r"https?://\S+", _wrap_url, s)
        p = doc.add_paragraph()
        set_para_zero_spacing(p, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, left_indent_dxa=709, hanging_dxa=709)
        add_rich_runs(p, s_fmt, size_pt=12)

    try:
        doc.save(OUT_DOCX)
        print("GENERATED:", OUT_DOCX)
    except PermissionError:
        alt_docx = os.path.join(BASE_DIR, "Laporan_Kelompok_Final.docx")
        doc.save(alt_docx)
        print("LOCKED_FALLBACK_GENERATED:", alt_docx)


if __name__ == "__main__":
    main()
