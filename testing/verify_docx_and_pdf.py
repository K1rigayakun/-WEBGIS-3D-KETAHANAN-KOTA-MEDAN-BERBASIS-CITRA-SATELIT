import os
import re
import fitz
import win32com.client
from docx import Document
from docx.oxml.ns import qn

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCX_PRIMARY = os.path.join(BASE_DIR, "Laporan_Kelompok.docx")
DOCX_ALT = os.path.join(BASE_DIR, "Laporan_Kelompok_Final.docx")
DOCX_PATH = DOCX_ALT if (os.path.exists(DOCX_ALT) and (not os.path.exists(DOCX_PRIMARY) or os.path.getmtime(DOCX_ALT) >= os.path.getmtime(DOCX_PRIMARY))) else DOCX_PRIMARY
RIS_PATH = os.path.join(BASE_DIR, "Referensi_Kelompok_Mendeley.ris")
PDF_PATH = os.path.join(BASE_DIR, "testing", "Laporan_Kelompok_Preview.pdf")
PREV_DIR = os.path.join(BASE_DIR, "testing", "pdf_preview")
os.makedirs(PREV_DIR, exist_ok=True)


def check_docx_xml():
    doc = Document(DOCX_PATH)
    print("=== DOCX XML CHECKS ===")
    print("Sections:", len(doc.sections))
    for i, s in enumerate(doc.sections, 1):
        w_cm = round(s.page_width.cm, 2)
        h_cm = round(s.page_height.cm, 2)
        tm, bm, lm, rm = round(s.top_margin.cm, 2), round(s.bottom_margin.cm, 2), round(s.left_margin.cm, 2), round(s.right_margin.cm, 2)
        if (w_cm, h_cm, tm, bm, lm, rm) != (21.0, 29.7, 3.0, 3.0, 4.0, 2.5):
            print(f"  SEC {i} MISMATCH:", (w_cm, h_cm, tm, bm, lm, rm))

    bad_fonts = []
    bad_colors = []
    underlines = []
    bad_spacing = []
    body_bolds = []
    body_text = []

    in_dp = False
    in_body = False
    for p in doc.paragraphs:
        st_name = p.style.name if p.style else ""
        if p.text.strip().startswith("BAB 1"):
            in_body = True
        if p.text.strip() == "DAFTAR PUSTAKA":
            in_body = False
            in_dp = True
        pf = p.paragraph_format
        sb = pf.space_before.pt if pf.space_before else 0
        sa = pf.space_after.pt if pf.space_after else 0
        if (sb != 0 or sa != 0) and st_name.lower() != "toc 1":
            bad_spacing.append((st_name, sb, sa, p.text[:40]))

        for r in p.runs:
            fn = r.font.name
            if fn and fn not in ("Times New Roman", "Courier New"):
                bad_fonts.append((fn, r.text[:30]))
            col = str(r.font.color.rgb) if (r.font.color and r.font.color.rgb) else None
            if col and col != "000000":
                bad_colors.append((col, r.text[:30]))
            if r.font.underline:
                underlines.append(r.text[:30])
            if in_body and st_name == "Normal" and r.font.bold and not p.text.startswith("Gambar") and not p.text.startswith("Tabel"):
                body_bolds.append(r.text[:40])
        if in_body:
            body_text.append(p.text)

    print("Bad fonts:", bad_fonts)
    print("Bad colors:", bad_colors)
    print("Underlines:", underlines)
    print("Bad spacing paras:", bad_spacing[:10])
    print("Body bold runs:", body_bolds[:10])

    # Check citations vs RIS
    full_body = "\n".join(body_text)
    cites = sorted(set(re.findall(r"\(([A-Z][A-Za-z0-9.&,\s-]+?,\s*\d{4})\)", full_body)))
    ris_txt = open(RIS_PATH, encoding="utf-8").read()
    ris_entries = [e.strip() for e in ris_txt.split("ER  -") if e.strip()]
    print(f"DOCX unique citations: {len(cites)}, RIS entries: {len(ris_entries)}")


def update_fields_and_export_pdf():
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(os.path.abspath(DOCX_PATH))
        # Configure TOC 1..4 and Table of Figures styles BEFORE updating (match C.15 & C.16 strictly)
        right_pos = 8221 / 20.0  # 411.05 pt
        toc_specs = [
            ("TOC 1", True, 12, 0, None),
            ("TOC 2", False, 0, 720 / 20.0, 1180 / 20.0),
            ("TOC 3", False, 0, 960 / 20.0, 1660 / 20.0),
            ("TOC 4", True, 0, 0, None),
            ("Table of Figures", False, 0, 0, None),
        ]
        for sname, is_bold, sb_pt, left_ind, left_tab in toc_specs:
            try:
                st = doc.Styles(sname)
                st.Font.Name = "Times New Roman"
                st.Font.Size = 12
                st.Font.Color = 0
                st.Font.Bold = is_bold
                st.ParagraphFormat.LineSpacingRule = 1 if sname == "Table of Figures" else 0  # 0=Single (1.0), 1=1.5
                st.ParagraphFormat.SpaceBefore = sb_pt
                st.ParagraphFormat.SpaceAfter = 0
                st.ParagraphFormat.LeftIndent = left_ind
                st.ParagraphFormat.FirstLineIndent = 0
                st.ParagraphFormat.TabStops.ClearAll()
                if left_tab:
                    st.ParagraphFormat.TabStops.Add(left_tab, 0, 0)
                st.ParagraphFormat.TabStops.Add(right_pos, 2, 0)
            except Exception:
                pass
        doc.Fields.Update()
        for toc in doc.TablesOfContents:
            toc.Update()
        for tof in doc.TablesOfFigures:
            tof.Update()
        doc.Fields.Update()
        # Re-enforce exact single line spacing, bold on TOC 1/4, zero spacing, and no dot leaders on TOC paragraphs
        for toc in doc.TablesOfContents:
            for p in toc.Range.Paragraphs:
                st_n = str(p.Style.NameLocal)
                p.Range.Font.Name = "Times New Roman"
                p.Range.Font.Size = 12
                p.Range.Font.Color = 0
                p.Range.Font.Underline = 0
                p.LineSpacingRule = 0  # wdLineSpaceSingle (1.0)
                p.SpaceAfter = 0
                p.FirstLineIndent = 0
                p.Format.TabStops.ClearAll()
                if "1" in st_n:
                    p.Range.Font.Bold = True
                    p.SpaceBefore = 12
                    p.LeftIndent = 0
                elif "4" in st_n:
                    p.Range.Font.Bold = True
                    p.SpaceBefore = 0
                    p.LeftIndent = 0
                elif "2" in st_n:
                    p.Range.Font.Bold = False
                    p.SpaceBefore = 0
                    p.LeftIndent = 720 / 20.0
                    p.Format.TabStops.Add(1180 / 20.0, 0, 0)
                elif "3" in st_n:
                    p.Range.Font.Bold = False
                    p.SpaceBefore = 0
                    p.LeftIndent = 960 / 20.0
                    p.Format.TabStops.Add(1660 / 20.0, 0, 0)
                p.Format.TabStops.Add(right_pos, 2, 0)
        for tof in doc.TablesOfFigures:
            for p in tof.Range.Paragraphs:
                p.Range.Font.Name = "Times New Roman"
                p.Range.Font.Size = 12
                p.Range.Font.Color = 0
                p.Range.Font.Underline = 0
                p.Range.Font.Bold = False
                p.LineSpacingRule = 1  # wdLineSpace1pt5
                p.SpaceBefore = 0
                p.SpaceAfter = 0
                p.LeftIndent = 0
                p.FirstLineIndent = 0
                p.Format.TabStops.ClearAll()
                p.Format.TabStops.Add(right_pos, 2, 0)
        # Re-run page numbers update ONLY after TOC shrank from 2 pages to 1 page!
        for toc in doc.TablesOfContents:
            toc.UpdatePageNumbers()
        for tof in doc.TablesOfFigures:
            tof.UpdatePageNumbers()
        doc.Save()
        doc.ExportAsFixedFormat(os.path.abspath(PDF_PATH), 17)  # 17 = wdExportFormatPDF
        doc.Close(False)
        print("PDF EXPORTED:", PDF_PATH)
    finally:
        word.Quit()


def inspect_pdf():
    pdf = fitz.open(PDF_PATH)
    print(f"TOTAL PDF PAGES: {len(pdf)}")
    y_top_limit = 85.04   # 3 cm
    y_bot_limit = 841.89 - 85.04  # 756.85
    usable_h = y_bot_limit - y_top_limit  # 671.81 pt

    bab_start_page = None
    dp_start_page = None

    for idx, page in enumerate(pdf, start=1):
        txt = page.get_text("text")
        first_line = next((x.strip() for x in txt.splitlines() if x.strip()), "")
        if "BAB 1" in txt[:120] and bab_start_page is None:
            bab_start_page = idx
        if "DAFTAR PUSTAKA" in txt[:120] and idx > 5:
            dp_start_page = idx

        # Find lowest y coordinate of content inside usable area (exclude header < 75 pt & footer > 770 pt)
        max_y = y_top_limit
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, btxt = b[:5]
            if y1 <= 78 or y0 >= 768:
                continue
            if not btxt.strip():
                continue
            if y1 > max_y:
                max_y = min(y1, y_bot_limit)
        for img in page.get_image_info():
            x0, y0, x1, y1 = img["bbox"]
            if y1 <= 78 or y0 >= 768:
                continue
            if y1 > max_y:
                max_y = min(y1, y_bot_limit)
        for drw in page.get_drawings():
            r = drw["rect"]
            if r.y1 <= 78 or r.y0 >= 768:
                continue
            if r.y1 > max_y:
                max_y = min(r.y1, y_bot_limit)

        fill_pct = round(max(0.0, (max_y - y_top_limit) / usable_h * 100.0), 1)
        print(f"  Page {idx:2d} | Fill={fill_pct:5.1f}% | Top: {first_line[:65]}")

        # Render all pages as PNGs so we can visually inspect key ones
        pix = page.get_pixmap(dpi=130)
        pix.save(os.path.join(PREV_DIR, f"page_{idx:02d}.png"))

    if bab_start_page and dp_start_page:
        print(f"ISI BAB 1..5 PAGES: {dp_start_page - bab_start_page} (pages {bab_start_page}..{dp_start_page - 1})")

    # Print TOC text from pages 3..5
    for pno in [3, 4, 5]:
        if pno <= len(pdf):
            print(f"\n--- PAGE {pno} TEXT ---")
            print(pdf[pno - 1].get_text("text")[:1500])


if __name__ == "__main__":
    check_docx_xml()
    update_fields_and_export_pdf()
    inspect_pdf()
