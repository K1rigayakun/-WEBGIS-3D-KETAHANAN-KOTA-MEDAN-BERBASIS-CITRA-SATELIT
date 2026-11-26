import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Polygon

OUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "flowchart_alur_proyek.png"))


def draw_terminator(ax, cx, cy, w, h, text):
    box = FancyBboxPatch(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle=f"round,pad=0,rounding_size={h / 2}",
        facecolor="#FFFFFF",
        edgecolor="#000000",
        linewidth=1.5,
    )
    ax.add_patch(box)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#000000", family="DejaVu Sans")


def draw_process(ax, cx, cy, w, h, text):
    box = patches.Rectangle(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        facecolor="#FFFFFF",
        edgecolor="#000000",
        linewidth=1.5,
    )
    ax.add_patch(box)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=8.0, color="#000000", family="DejaVu Sans")


def draw_io(ax, cx, cy, w, h, text):
    dx = 0.25
    pts = [
        (cx - w / 2 + dx, cy + h / 2),
        (cx + w / 2 + dx, cy + h / 2),
        (cx + w / 2 - dx, cy - h / 2),
        (cx - w / 2 - dx, cy - h / 2),
    ]
    poly = Polygon(pts, closed=True, facecolor="#FFFFFF", edgecolor="#000000", linewidth=1.5)
    ax.add_patch(poly)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=8.0, color="#000000", family="DejaVu Sans")


def draw_decision(ax, cx, cy, w, h, text):
    pts = [
        (cx, cy + h / 2),
        (cx + w / 2, cy),
        (cx, cy - h / 2),
        (cx - w / 2, cy),
    ]
    poly = Polygon(pts, closed=True, facecolor="#FFFFFF", edgecolor="#000000", linewidth=1.5)
    ax.add_patch(poly)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=7.8, color="#000000", family="DejaVu Sans")


def arrow(ax, x1, y1, x2, y2, label=None, lx=None, ly=None):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color="#000000", lw=1.4, shrinkA=0, shrinkB=0),
    )
    if label:
        ax.text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2, label, fontsize=7.5, fontweight="bold", color="#000000", ha="center", va="center")


def main():
    # Wide 3-row zig-zag layout (~14.5 cm x 8.0 cm aspect ratio)
    fig, ax = plt.subplots(figsize=(11.4, 6.2), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9.2)
    ax.axis("off")

    y1, y2, y3 = 7.7, 4.7, 1.7
    xs = [1.8, 5.9, 10.1, 14.2]

    # Row 1: Left -> Right
    draw_terminator(ax, xs[0], y1, 2.2, 0.95, "Mulai")
    draw_io(ax, xs[1], y1, 2.8, 1.15, "Akuisisi Data\nSatelit & Spasial\n(21 Kecamatan)")
    draw_process(ax, xs[2], y1, 2.9, 1.15, "Pembuatan Grid\nHeksagon 500m &\nZonal Statistics")
    draw_process(ax, xs[3], y1, 2.8, 1.15, "Analisis 5 Topik\n& Skoring Risiko\ndi QGIS")

    arrow(ax, xs[0] + 1.1, y1, xs[1] - 1.4 + 0.12, y1)
    arrow(ax, xs[1] + 1.4 - 0.12, y1, xs[2] - 1.45, y1)
    arrow(ax, xs[2] + 1.45, y1, xs[3] - 1.4, y1)

    # Connector Row 1 -> Row 2 (right side down)
    arrow(ax, xs[3], y1 - 0.575, xs[3], y2 + 0.575)

    # Row 2: Right -> Left (Zig-Zag)
    draw_process(ax, xs[3], y2, 2.8, 1.15, "Rancang Layer Solusi\n& Ekspor GeoJSON\nEPSG:4326")
    draw_process(ax, xs[2], y2, 2.9, 1.15, "Buat 10 Aset 3D GLB\n& Integrasi Kontrak\n5 Anggota Tim")
    draw_process(ax, xs[1], y2, 2.9, 1.15, "Bangun WebGIS 3D\n(MapLibre GL JS +\nThree.js r169)")
    draw_decision(ax, xs[0], y2, 2.6, 1.45, "Validasi Peta\n& Uji WebGL\nLolos?")

    arrow(ax, xs[3] - 1.4, y2, xs[2] + 1.45, y2)
    arrow(ax, xs[2] - 1.45, y2, xs[1] + 1.45, y2)
    arrow(ax, xs[1] - 1.45, y2, xs[0] + 1.3, y2)

    # Decision "Tidak" loop back to Row 2 Build WebGIS or Row 1? Loop up to Row 1 or right back:
    # Draw "Tidak" branch going up to y1+0.85? Let's route cleanly: top of diamond -> up to y1-1.35 -> right to xs[1] -> down to process!
    ax.plot([xs[0], xs[0], xs[1], xs[1]], [y2 + 0.725, 6.25, 6.25, y2 + 0.575], color="#000000", lw=1.4)
    ax.annotate("", xy=(xs[1], y2 + 0.575), xytext=(xs[1], y2 + 0.65), arrowprops=dict(arrowstyle="-|>", color="#000000", lw=1.4))
    ax.text((xs[0] + xs[1]) / 2, 6.45, "Tidak (Perbaiki)", fontsize=7.5, fontweight="bold", ha="center", va="center", color="#000000")

    # Connector Row 2 -> Row 3 (left side down, "Ya")
    arrow(ax, xs[0], y2 - 0.725, xs[0], y3 + 0.575, label="Ya", lx=xs[0] + 0.35, ly=(y2 - 0.725 + y3 + 0.575) / 2)

    # Row 3: Left -> Right
    draw_process(ax, xs[0], y3, 2.6, 1.15, "Pengujian Fungsional\n& Simulasi 3 Tahap\n(10 Skenario)")
    draw_io(ax, xs[1], y3, 2.8, 1.15, "Output: .qgz, .png,\nWebGIS 3D & Laporan\nDokumentasi")
    draw_terminator(ax, xs[2], y3, 2.2, 0.95, "Selesai")

    arrow(ax, xs[0] + 1.3, y3, xs[1] - 1.4 + 0.12, y3)
    arrow(ax, xs[1] + 1.4 - 0.12, y3, xs[2] - 1.1, y3)

    plt.tight_layout(pad=0.2)
    plt.savefig(OUT_PATH, dpi=300, facecolor="#FFFFFF", bbox_inches="tight")
    print("SAVED:", OUT_PATH)


if __name__ == "__main__":
    main()
