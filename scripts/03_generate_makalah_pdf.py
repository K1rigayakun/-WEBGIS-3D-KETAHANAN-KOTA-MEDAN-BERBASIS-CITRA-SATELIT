import json
import subprocess
from pathlib import Path

BASE_DIR = Path(r"M:\Kuliah\Semester 5\SIG\Project Akhir")
DATA_DIR = BASE_DIR / "data"
SCREEN_DIR = BASE_DIR / "testing" / "screenshoot"
HTML_OUT = BASE_DIR / "scripts" / "makalah_source.html"
PDF_OUT = BASE_DIR / "Makalah_Tugas_Akhir_SIG_Orang5.pdf"
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def main() -> None:
    kec = json.loads((DATA_DIR / "batas_kecamatan_medan.geojson").read_text(encoding="utf-8"))["features"]
    kor = json.loads((DATA_DIR / "koridor_rawan_begal.geojson").read_text(encoding="utf-8"))["features"]
    pat = json.loads((DATA_DIR / "solusi_rute_patroli.geojson").read_text(encoding="utf-8"))["features"]

    kec_sorted = sorted(kec, key=lambda x: x["properties"]["avg_risk_score"], reverse=True)
    kec_rows = "\n".join(
        f"<tr><td>{i+1}</td><td>{f['properties']['nama_kec']}</td>"
        f"<td class='num'>{f['properties']['luas_km2']:.2f}</td>"
        f"<td class='num'>{f['properties']['penduduk_2025']:,}</td>"
        f"<td class='num'>{f['properties']['viirs_mean']:.2f}</td>"
        f"<td class='num'>{f['properties']['hex_total']}</td>"
        f"<td class='num'>{f['properties']['hex_kritis']}</td>"
        f"<td class='num'><strong>{f['properties']['avg_risk_score']:.1f}</strong></td>"
        f"<td class='num'>{f['properties']['jumlah_pju_solusi']}</td></tr>"
        for i, f in enumerate(kec_sorted)
    )

    kor_rows = "\n".join(
        f"<tr><td>{i+1}</td><td>{f['properties']['nama_jalan']}</td>"
        f"<td>{f['properties']['kecamatan']}</td>"
        f"<td class='num'>{f['properties']['panjang_km']:.2f}</td>"
        f"<td class='num'>{f['properties']['viirs_min']}</td>"
        f"<td class='num'>{f['properties']['viirs_mean']}</td>"
        f"<td>{f['properties']['tingkat_bahaya']}</td></tr>"
        for i, f in enumerate(kor)
    )

    pat_rows = "\n".join(
        f"<tr><td>{f['properties']['nama_rute']}</td>"
        f"<td>{f['properties']['unit_pelaksana']}</td>"
        f"<td>{f['properties']['jam_patroli']}</td>"
        f"<td class='num'>{f['properties']['panjang_km']:.2f} km</td></tr>"
        for f in pat
    )

    layout_uri = (BASE_DIR / "Layout_Peta_Orang5.png").as_uri()
    shot_prob = (SCREEN_DIR / "webgis_3d_problem_mode.png").as_uri()
    shot_sol = (SCREEN_DIR / "webgis_3d_solution_active.png").as_uri()
    shot_sat = (SCREEN_DIR / "webgis_satellite_proof.png").as_uri()
    shot_terrain = (SCREEN_DIR / "webgis_terrain_3d.png").as_uri()
    shot_globe = (SCREEN_DIR / "webgis_globe_3d.png").as_uri()
    shot_hex = (SCREEN_DIR / "webgis_hex_overview.png").as_uri()
    shot_blender = (SCREEN_DIR / "blender_models_preview.png").as_uri()
    shot_closeup = (SCREEN_DIR / "webgis_models_closeup.png").as_uri()

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <title>Makalah Tugas Akhir Praktikum SIG - Orang 5</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@600;700&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet" />
  <style>
    @page {{
      size: A4 portrait;
      margin: 18mm 18mm 18mm 20mm;
    }}
    body {{
      font-family: "Nunito", "Segoe UI", Arial, sans-serif;
      font-size: 10.5pt;
      line-height: 1.5;
      color: #071B2B;
      background: #FFFFFF;
      margin: 0;
    }}
    .cover {{
      page-break-after: always;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 248mm;
      text-align: center;
      background: #FFFFFF;
      border: 3px solid #071B2B;
      border-radius: 24px;
      box-shadow: 6px 6px 0 #071B2B;
      padding: 20mm 14mm;
      box-sizing: border-box;
    }}
    .cover-kicker {{
      display: inline-block;
      font-family: "Fredoka", "Segoe UI", Arial, sans-serif;
      font-size: 10.5pt;
      font-weight: 700;
      letter-spacing: 0.8px;
      color: #071B2B;
      background: #B9E4E8;
      border: 2.5px solid #071B2B;
      border-radius: 9999px;
      padding: 6px 16px;
      margin-bottom: 14px;
    }}
    .cover-title {{
      font-family: "Fredoka", "Segoe UI", Arial, sans-serif;
      font-size: 18.5pt;
      font-weight: 700;
      line-height: 1.3;
      color: #071B2B;
      margin: 12px 0;
    }}
    .cover-sub {{
      font-size: 11pt;
      color: #167D8D;
      font-weight: 700;
      max-width: 145mm;
      margin: 0 auto;
    }}
    .cover-box {{
      margin: 18px auto;
      width: 145mm;
      text-align: left;
      border: 3px solid #071B2B;
      border-radius: 18px;
      box-shadow: 4px 4px 0 #071B2B;
      background: #EEEEEE;
      padding: 14px 16px;
      font-size: 10.2pt;
    }}
    .cover-box table {{ width: 100%; border-collapse: collapse; }}
    .cover-box td {{ padding: 4px 4px; vertical-align: top; border: none; color: #071B2B; }}
    .cover-footer {{
      font-family: "Fredoka", "Segoe UI", Arial, sans-serif;
      font-weight: 700;
      font-size: 11pt;
      color: #071B2B;
      line-height: 1.6;
    }}
    h1 {{
      font-family: "Fredoka", "Segoe UI", Arial, sans-serif;
      font-size: 14pt;
      color: #071B2B;
      border-bottom: 3px solid #167D8D;
      padding-bottom: 4px;
      margin-top: 16px;
      page-break-after: avoid;
    }}
    h2 {{
      font-family: "Fredoka", "Segoe UI", Arial, sans-serif;
      font-size: 11.5pt;
      color: #167D8D;
      margin-top: 12px;
      margin-bottom: 5px;
      page-break-after: avoid;
    }}
    p {{ text-align: justify; margin: 6px 0 9px 0; }}
    ul, ol {{ margin: 5px 0 10px 0; padding-left: 20px; }}
    li {{ margin-bottom: 4px; text-align: justify; }}
    code {{
      background: #EEEEEE;
      padding: 1px 4px;
      border-radius: 4px;
      font-size: 9.2pt;
    }}
    table.data {{
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0 14px 0;
      font-size: 8.5pt;
      page-break-inside: avoid;
    }}
    table.data th {{
      background: #071B2B;
      color: #FFFFFF;
      padding: 5px 6px;
      text-align: left;
      border: 1px solid #071B2B;
      font-family: "Fredoka", "Segoe UI", Arial, sans-serif;
    }}
    table.data td {{
      padding: 4px 6px;
      border: 1px solid #071B2B;
    }}
    table.data tr:nth-child(even) {{ background: #EEEEEE; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .callout {{
      background: #B9E4E8;
      border: 2px solid #071B2B;
      border-left: 6px solid #167D8D;
      border-radius: 12px;
      padding: 9px 12px;
      margin: 10px 0;
      font-size: 9.8pt;
      font-weight: 600;
    }}
    .figure {{
      text-align: center;
      margin: 9px 0;
      page-break-inside: avoid;
    }}
    .figure img {{
      width: 96%;
      border: 2.5px solid #071B2B;
      border-radius: 12px;
    }}
    .caption {{
      font-size: 8.8pt;
      color: #071B2B;
      margin-top: 5px;
      font-style: italic;
    }}
    .page-break {{ page-break-before: always; }}
  </style>
</head>
<body>

  <!-- COVER PAGE -->
  <section class="cover">
    <div>
      <div class="cover-kicker">LAPORAN TUGAS AKHIR PRAKTIKUM SISTEM INFORMASI GEOGRAFIS</div>
      <div class="cover-title">
        PEMETAAN KERENTANAN ZONA GELAP RAWAN KEJAHATAN JALANAN (BEGAL) BERBASIS CITRA VIIRS 2024 DAN MODEL 3D BLENDER SERTA WEBGIS INTERAKTIF KOTA MEDAN
      </div>
      <p class="cover-sub">
        Implementasi Bagian Orang 5: 3D Dark-Zone Crime &amp; Building Vulnerability + Web Integrator dalam Proyek WebGIS Ketahanan Kota Medan
      </p>
    </div>

    <div class="cover-box">
      <table>
        <tr><td width="34%"><strong>Program Studi</strong></td><td>: DIII - Teknik Informatika</td></tr>
        <tr><td><strong>Mata Kuliah</strong></td><td>: Praktikum Sistem Informasi Geografis (TA. 2026/2027)</td></tr>
        <tr><td><strong>Dosen Pengampu</strong></td><td>: Dr. Syahriol Sitorus, S.Si., M.Si.</td></tr>
        <tr><td><strong>Asisten Laboratorium</strong></td><td>: Bernita Agustien P Habeahan<br>&nbsp;&nbsp;Andri Wiguna</td></tr>
        <tr><td><strong>Penyusun (Orang 5)</strong></td><td>: Michael Deryl Aaron Matthew (NIM. 241712042 / KOM A2)</td></tr>
        <tr><td><strong>Fokus Wilayah Studi</strong></td><td>: Kota Medan (21 Kecamatan, 73.021 Bangunan 3D di 12 Kec.)</td></tr>
      </table>
    </div>

    <div class="cover-footer">
      PROGRAM STUDI DIII TEKNIK INFORMATIKA<br>
      TAHUN AKADEMIK 2026/2027
    </div>
  </section>

  <!-- BAB 1 -->
  <h1>BAB I. PENDAHULUAN</h1>
  <h2>1.1 Latar Belakang Masalah Dunia Nyata</h2>
  <p>
    Kejahatan jalanan pada malam hingga dini hari, khususnya pencurian dengan kekerasan (curas atau begal) dan pencurian kendaraan bermotor (curanmor), merupakan permasalahan keamanan perkotaan yang nyata di Kota Medan. Berdasarkan rilis pemetaan kerawanan kriminalitas Polrestabes Medan dan pemberitaan resmi pengawasan Kegiatan Rutin Yang Ditingkatkan (KRYD), sejumlah koridor protokol maupun jalan penghubung seperti Jalan Gatot Subroto, Jalan Sriwijaya, Jalan Sei Serayu, Jalan Gajah Mada, Jalan S. Parman, Jalan Jamin Ginting, Jalan Gagak Hitam (Ring Road), dan Jalan Yos Sudarso tercatat sebagai ruas berisiko tinggi akibat kombinasi aktivitas malam, keterbatasan pengawasan, dan titik gelap atau minimnya Penerangan Jalan Umum (PJU).
  </p>
  <p>
    Pendekatan pemetaan tradisional yang hanya menampilkan poligon kecamatan datar tanpa mengintegrasikan intensitas cahaya malam satelit, bentuk fisik bangunan di koridor padat, serta keterjangkauan jarak dari pos polisi aktif sering kali belum mampu memberikan rekomendasi penanggulangan akar masalah yang tepat sasaran. Oleh karena itu, proyek ini mengimplementasikan sistem pemetaan tematik terpadu berbasis Quantum GIS (QGIS) dan WebGIS 3D interaktif bergaya neubrutalism kontras tinggi yang memetakan zona gelap rawan kejahatan jalanan di seluruh 21 kecamatan Kota Medan sekaligus merumuskan solusi mitigasi fisik dan operasional.
  </p>

  <h2>1.2 Rumusan Masalah &amp; Tujuan</h2>
  <ol>
    <li>Bagaimana mengintegrasikan citra satelit cahaya malam VIIRS tahun 2024 ke dalam grid heksagon 500 meter di seluruh 21 kecamatan Kota Medan untuk mengidentifikasi zona gelap yang beririsan dengan koridor rawan kejahatan Polrestabes Medan?</li>
    <li>Bagaimana memetakan kerentanan bangunan 3D secara detail di 12 kecamatan wilayah fokus utama (73.021 tapak bangunan nyata OpenStreetMap API v0.6) serta seluruh 21 kecamatan menggunakan layer bangunan vektor 3D, citra satelit asli, dan elevasi Terrain 3D SRTM?</li>
    <li>Bagaimana merancang solusi akar masalah berupa penempatan titik PJU Pintar, CCTV Analitik, Pos Pantau Panic Button, dan rute patroli malam KRYD serta memvisualisasikannya dalam proyek QGIS (<code>.qgz</code>), cetak peta (<code>.png</code>), dan WebGIS 3D dengan model aset Blender?</li>
  </ol>

  <!-- BAB 2 -->
  <h1>BAB II. SUMBER DATA RESMI &amp; METODOLOGI SPASIAL</h1>
  <h2>2.1 Inventarisasi Sumber Data Nyata</h2>
  <p>
    Seluruh lapisan data pada proyek ini bersumber dari repositori geospasial publik resmi dan rilis pemetaan kepolisian tanpa menggunakan data koordinat fiktif:
  </p>
  <table class="data">
    <thead>
      <tr>
        <th>No</th>
        <th>Lapisan Data</th>
        <th>Sumber Resmi &amp; Keterangan</th>
        <th>Format / Resolusi</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td>Citra Cahaya Malam 2024</td>
        <td>EOG / OpenGeoHub Annual VIIRS V2.1 (Zenodo DOI: 10.5281/zenodo.17294744)</td>
        <td>GeoTIFF 500 m (<code>EPSG:4326</code>)</td>
      </tr>
      <tr>
        <td>2</td>
        <td>Batas Administrasi 21 Kecamatan</td>
        <td>Peta Rupa Bumi Indonesia (RBI) 1:50.000 Badan Informasi Geospasial (BIG) &amp; Data Kependudukan BPS 2024/2025</td>
        <td>GeoJSON (21 Poligon)</td>
      </tr>
      <tr>
        <td>3</td>
        <td>Tapak Bangunan, Jalan &amp; Sungai</td>
        <td>OpenStreetMap API v0.6 (44 tile melintasi 12 kecamatan inti Kota Medan) &amp; OpenFreeMap Vector Tiles (21 kecamatan)</td>
        <td>GeoJSON (73.021 Bangunan 3D)</td>
      </tr>
      <tr>
        <td>4</td>
        <td>Elevasi Topografi</td>
        <td>DEM SRTM 30 Meter Sumatera Utara (USGS / BIG) dipotong ke wilayah Kota Medan</td>
        <td>GeoTIFF 30 m</td>
      </tr>
      <tr>
        <td>5</td>
        <td>Kantor Polisi &amp; Koridor Rawan</td>
        <td>Nominatim OpenStreetMap, OSRM Driving API, serta Rilis Pemetaan Rawan Kejahatan Polrestabes Medan &amp; Polres Pelabuhan Belawan</td>
        <td>GeoJSON (23 Pos Polisi, 24 Koridor)</td>
      </tr>
    </tbody>
  </table>

  <h2>2.2 Tahapan Pengolahan Spasial &amp; Skema Warna Tematik</h2>
  <ol>
    <li><strong>Pembentukan Grid Heksagon 500 Meter (UTM 47N / EPSG:32647)</strong>: Membagi seluruh luasan 21 kecamatan Kota Medan menjadi 1.470 sel heksagon berukuran 500 meter untuk menghindari bias bentuk batas administratif yang kaku.</li>
    <li><strong>Zonal Statistics VIIRS &amp; DEM SRTM</strong>: Mengekstrak nilai rata-rata, minimum, dan maksimum intensitas cahaya malam VIIRS 2024 (rentang 0,0 hingga 105,0 DN di Kota Medan; rata-rata kota 26,13 DN) serta elevasi rata-rata pada setiap sel heksagon.</li>
    <li><strong>Perhitungan Skor Risiko Zona Gelap (0-100)</strong>: Menggabungkan defisit cahaya malam VIIRS (42%), jarak metrik sel terhadap pos polisi eksisting (33%), dan kedekatan terhadap koridor jalan rawan Polrestabes Medan (25%).</li>
    <li><strong>Ekstrusi Tinggi Bangunan 3D &amp; Skema Palet</strong>: Sebanyak 73.021 poligon bangunan nyata di 12 kecamatan inti Kota Medan (Medan Petisah 13.993, Medan Baru 8.481, Medan Area 8.121, Medan Polonia 7.544, Medan Barat 6.073, Medan Selayang 5.814, Medan Kota 4.728, Medan Timur 4.397, Medan Helvetia 3.950, Medan Maimun 3.599, Medan Sunggal 3.272, dan Medan Perjuangan 3.049) diberi tinggi <code>height_m</code> (dari tag <code>height</code>, <code>building:levels * 4 m</code>, serta fallback tipe/luas tapak). Seluruh visualisasi mengikuti palet Color Hunt: navy gelap <code>#071B2B</code> untuk zona gelap/kritis, teal <code>#167D8D</code> untuk tingkat sedang/rute patroli, biru es <code>#B9E4E8</code> untuk zona aman atau terlindungi PJU, abu terang <code>#EEEEEE</code> untuk dasar kanvas, serta aksen lampu hangat <code>#FFC94D</code> khusus untuk cahaya dan radius PJU 3D.</li>
  </ol>

  <!-- BAB 3 -->
  <h1 class="page-break">BAB III. HASIL ANALISIS ZONA GELAP &amp; PETA TEMATIK</h1>
  <h2>3.1 Distribusi Kerentanan Zona Gelap per Kecamatan</h2>
  <p>
    Hasil agregasi 1.470 sel heksagon 500 meter menunjukkan bahwa 106 sel (7,2%) berada pada kelas <em>Kritis (Dark-Zone)</em> dan 598 sel (40,7%) berada pada kelas <em>Tinggi</em>. Kecamatan pinggiran seperti Medan Tuntungan (skor risiko 60,2; rata-rata VIIRS 14,81 DN) dan Medan Selayang (60,0) maupun kawasan utara Medan Belawan (53,6) memiliki defisit penerangan terluas, sedangkan Medan Baru (47,4; 13 sel kritis) di pusat kota memiliki koridor gelap yang beririsan langsung dengan titik rawan kejahatan jalanan.
  </p>

  <table class="data">
    <thead>
      <tr>
        <th>No</th>
        <th>Kecamatan</th>
        <th>Luas (km2)</th>
        <th>Penduduk 2025</th>
        <th>VIIRS Mean</th>
        <th>Total Hex</th>
        <th>Hex Kritis/Tinggi</th>
        <th>Skor Risiko</th>
        <th>Solusi PJU</th>
      </tr>
    </thead>
    <tbody>
      {kec_rows}
    </tbody>
  </table>

  <h2>3.2 Visualisasi Layout Peta Tematik QGIS (300 DPI)</h2>
  <div class="figure">
    <img src="{layout_uri}" alt="Layout Peta QGIS Orang 5" />
    <div class="caption">
      Gambar 1. Hasil Cetak Layout Peta Tematik QGIS (<code>Layout_Peta_Orang5.png</code>, A3 300 DPI) bergaya kartu neubrutalism dengan palet #071B2B, #167D8D, #B9E4E8, #EEEEEE, serta aksen titik solusi #FFC94D.
    </div>
  </div>

  <h2>3.3 Koridor Rawan Kejahatan Jalanan (Rilis Polrestabes Medan)</h2>
  <p>
    Dari ekstraksi geometri jalan nyata di OpenStreetMap dan Nominatim serta perluasan ruas pengawasan tingkat kota, terpetakan 24 koridor jalan utama rawan kejahatan jalanan di seluruh 21 kecamatan yang dianalisis terhadap nilai radiansi VIIRS 2024:
  </p>
  <table class="data">
    <thead>
      <tr>
        <th>No</th>
        <th>Nama Koridor Jalan</th>
        <th>Wilayah Kecamatan</th>
        <th>Panjang (km)</th>
        <th>VIIRS Min</th>
        <th>VIIRS Mean</th>
        <th>Tingkat Bahaya</th>
      </tr>
    </thead>
    <tbody>
      {kor_rows}
    </tbody>
  </table>

  <!-- BAB 4 -->
  <h1 class="page-break">BAB IV. SOLUSI AKAR MASALAH &amp; IMPLEMENTASI WEBGIS 3D</h1>
  <h2>4.1 Rekomendasi Solusi Akar Masalah Berbasis Spasial</h2>
  <ul>
    <li><strong>Penempatan Merata 217 Titik PJU Pintar, CCTV Analitik &amp; Pos Pantau (Seluruh 21 Kecamatan)</strong>: Terdiri atas <strong>35 unit PJU Pintar LED Solar + Sensor Gerak</strong> (radius terang 165 m), <strong>150 unit CCTV Analitik + PJU Pintar Terpadu</strong> (radius 185 m), serta <strong>32 unit Pos Pantau &amp; Panic Button + CCTV</strong> (radius 210 m) dengan 182 titik berstatus <em>Prioritas 1 - Kritis</em> dan 35 titik berstatus <em>Prioritas 2 - Tinggi</em> (minimal 9 unit pada setiap kecamatan Kota Medan).</li>
    <li><strong>Dampak Terukur Terhadap Bangunan Zona Gelap</strong>: Dari 73.021 bangunan 3D pada 12 kecamatan fokus, tercatat 10.905 bangunan berstatus kerentanan zona gelap <em>Tinggi</em> (17.568 Sedang dan 44.548 Rendah). Saat radius terang 217 titik solusi diaktifkan, sebanyak <strong>3.149 bangunan berisiko tinggi (28,9%)</strong> dan total <strong>17.357 bangunan</strong> masuk dalam cakupan proteksi penerangan, sehingga menyisakan 7.756 bangunan berisiko tinggi di zona gelap.</li>
    <li><strong>Optimalisasi 7 Rute Patroli Malam Satgas Anti-Begal (KRYD)</strong>: Dirancang melalui jaringan jalan nyata OSRM pukul 21.30-05.00 WIB sepanjang total <strong>196,92 km</strong> menjangkau seluruh sektor Utara (Belawan-Labuhan-Marelan-Deli), Selatan (Tuntungan-Johor-Amplas), Tenggara (Denai-Tembung), Barat-Ring Road, hingga Pusat Kota:</li>
  </ul>
  <table class="data">
    <thead>
      <tr>
        <th>Nama Rute Patroli</th>
        <th>Unit Pelaksana</th>
        <th>Jam Operasi</th>
        <th>Panjang Rute</th>
      </tr>
    </thead>
    <tbody>
      {pat_rows}
    </tbody>
  </table>

  <h2>4.2 Implementasi WebGIS 3D Interaktif, Bumi Malam NASA &amp; Terrain 3D Satelit</h2>
  <p>
    Antarmuka WebGIS dibangun dengan gaya kartu neubrutalism (border tegas 3px <code>#071B2B</code>, bayangan keras 6px, tipografi Fredoka dan Nunito, serta ikon vektor Lucide SVG) di atas MapLibre GL JS v5.24.1 dengan opsi peta dasar otentik: <em>Tematik</em> (Esri World Light Gray), <em>Bumi Malam NASA</em> (tile satelit global resmi <strong>NASA EOSDIS GIBS Suomi-NPP VIIRS Earth at Night / VIIRS_CityLights_2012</strong> yang dikombinasikan dengan masker kegelapan sensor VIIRS 2024 tanpa pewarnaan artifisial serta kontur zona gelap <code>viirs_kontur_gelap.geojson</code>), <em>Satelit Siang 3D</em> (citra satelit Esri World Imagery dibentangkan di atas elevasi <strong>Terrain 3D Terrarium DEM</strong>), dan <em>Jalan OSM</em>. Proyeksi peta berpindah otomatis menjadi <strong>Globe 3D terpusat</strong> (maksimal zoom-out terkunci pada <code>Z 2,0</code>) saat zoom-out global (<code>Z &lt; 7,5</code>) dan kembali ke <strong>Mercator 3D</strong> saat zoom-in perkotaan. Legenda terperinci dapat dilipat, sedangkan klik fitur menampilkan perbandingan <strong>matriks piksel satelit 9x9 VIIRS</strong> terhadap pusat terang Kota Medan serta dialog <em>Bukti &amp; Rumus</em>.
  </p>

  <div class="figure">
    <img src="{shot_prob}" alt="WebGIS 3D Mode Masalah" />
    <div class="caption">
      Gambar 2. Tampilan WebGIS 3D pada Mode Masalah (default): 73.021 gedung 3D pada 12 kecamatan (plus vektor 21 kecamatan OpenFreeMap) dengan 10.905 gedung zona gelap berisiko tinggi berwarna navy gelap (#071B2B) di sepanjang koridor rawan Polrestabes Medan.
    </div>
  </div>

  <div class="figure">
    <img src="{shot_sol}" alt="WebGIS 3D Simulasi Solusi Aktif" />
    <div class="caption">
      Gambar 3. Tampilan WebGIS 3D saat Simulasi Solusi 217 Titik PJU Pintar &amp; CCTV diaktifkan: 3.149 gedung berisiko tinggi (total 17.357 gedung) terlindungi biru es (#B9E4E8) di dalam radius terang hangat (#FFC94D), menyisakan 7.756 gedung berisiko tinggi.
    </div>
  </div>

  <div class="figure">
    <img src="{shot_sat}" alt="Verifikasi Bumi Malam NASA VIIRS" />
    <div class="caption">
      Gambar 4. Verifikasi citra Bumi Malam asli dari <em>NASA EOSDIS GIBS Suomi-NPP VIIRS Earth at Night</em> memperlihatkan kontras pendar cahaya Kota Medan dibanding hamparan gelap Sumatera Utara lengkap dengan kontur zona gelap dan matriks 9x9 piksel VIIRS 2024.
    </div>
  </div>

  <div class="figure">
    <img src="{shot_terrain}" alt="Terrain 3D Satelit Bukit Barisan" />
    <div class="caption">
      Gambar 5. Tampilan <em>Terrain 3D Satelit Siang</em> menggunakan citra Esri World Imagery di atas kontur elevasi nyata Terrarium DEM kawasan selatan Kota Medan dan perbukitan Bukit Barisan tanpa masker warna buatan.
    </div>
  </div>

  <div class="figure">
    <img src="{shot_globe}" alt="Proyeksi Otomatis Globe 3D Bumi Malam NASA" />
    <div class="caption">
      Gambar 6. Mode proyeksi otomatis Globe 3D terpusat pada batas zoom-out maksimal (<code>Z 2,0</code>) menampilkan citra asli Bumi Malam NASA VIIRS Earth at Night beserta legenda yang dapat dilipat.
    </div>
  </div>

  <h2 class="page-break">4.3 Model 3D Blender &amp; Rendering three.js</h2>
  <div class="callout">
    Model infrastruktur solusi dan fasilitas keamanan dibuat secara terprogram (<em>headless</em>) di <strong>Blender 4.4.3</strong>, diekspor sebagai berkas <strong>GLB (glTF 2.0)</strong>, lalu dirender langsung di atas kanvas peta MapLibre GL JS v5.24.1 menggunakan <strong>custom layer three.js r169 (<code>GLTFLoader</code>)</strong>.
  </div>
  <p>
    Empat aset 3D bergaya <em>clay/beveled low-poly</em>—yakni <code>pju_smart.glb</code> (576 vertex), <code>cctv_pole.glb</code> (588 vertex), <code>pos_pantau.glb</code> (676 vertex), dan <code>police_post.glb</code> (840 vertex)—menggunakan palet terstandarisasi (<code>#071B2B</code>, <code>#167D8D</code>, <code>#B9E4E8</code>, <code>#EEEEEE</code>, <code>#FFFFFF</code>) dan material emisi khusus <code>LampGlow</code> berwarna <code>#FFC94D</code>. Pada WebGIS, 217 instansi model solusi ditempatkan pada skala <code>2,5x</code> di seluruh 21 kecamatan dan 23 instansi kantor polisi pada skala <code>1,6x</code> (total 240 instansi 3D); dalam mode masalah model PJU tampil semi-transparan (<em>rencana</em>), lalu berubah solid dengan lampu berdenyut saat simulasi diaktifkan.
  </p>

  <div class="figure">
    <img src="{shot_blender}" alt="Preview 4 Model 3D Blender" />
    <div class="caption">
      Gambar 7. Render pratinjau Blender EEVEE Next untuk keempat model 3D GLB (kiri ke kanan: PJU Pintar Solar, Tiang CCTV Analitik, Pos Pantau Panic Button, dan Bangunan Kantor Polisi).
    </div>
  </div>

  <div class="figure">
    <img src="{shot_closeup}" alt="Close-up Model 3D Blender di WebGIS" />
    <div class="caption">
      Gambar 8. Tampilan dekat (zoom 17.2) model 3D Blender yang dirender via custom layer three.js r169 tepat di atas titik koordinat koridor pada MapLibre GL JS v5.24.1 saat simulasi lampu aktif.
    </div>
  </div>

  <div class="figure">
    <img src="{shot_hex}" alt="WebGIS 3D Menara Heksagon 21 Kecamatan" />
    <div class="caption">
      Gambar 9. Visualisasi Menara Heksagon 3D (1.470 sel 500m) di seluruh 21 Kecamatan Kota Medan menggunakan gradasi palet #B9E4E8 hingga #071B2B beserta sebaran merata 217 solusi PJU, 24 koridor, 7 rute patroli, dan 23 pos polisi.
    </div>
  </div>

  <h2>4.4 Kesiapan Integrasi 5 Anggota Tim (WebGIS Medan Tangguh)</h2>
  <p>
    Sebagai Web Integrator (Orang 5), sistem menyediakan kontrak penyatuan data terstandarisasi pada direktori <code>data/integrasi_tim/</code> berbasis kunci gabungan bersama (<code>hex_id</code> <code>HEX-0001..HEX-1470</code> dan <code>id_kec</code> 21 kecamatan, proyeksi <code>EPSG:4326</code>) yang terdokumentasi di <code>KONTRAK_INTEGRASI_5_ORANG.md</code>. Berkas <code>team_layers_bundle.js</code> dan pengimpor <code>.geojson</code> langsung di antarmuka memungkinkan penggabungan layer masalah maupun solusi dari <strong>Orang 1</strong> (Micro-UHI &amp; peneduh), <strong>Orang 2</strong> (Defisit RTH &amp; taman), <strong>Orang 3</strong> (Cekungan banjir &amp; posko evakuasi), serta <strong>Orang 4</strong> (Blindspot Damkar &amp; hidran) ke dalam satu aplikasi terpadu.
  </p>

  <!-- BAB 5 -->
  <h1>BAB V. KESIMPULAN &amp; DAFTAR REFERENSI</h1>
  <h2>5.1 Kesimpulan</h2>
  <ol>
    <li>Integrasi citra cahaya malam VIIRS V2.1 2024, DEM SRTM 30m, data bangunan dan jalan OpenStreetMap, serta rilis Polrestabes Medan dan Polres Pelabuhan Belawan memetakan kerentanan zona gelap pada 1.470 sel heksagon 500m serta sebaran koridor dan solusi di seluruh 21 kecamatan bersama 73.021 gedung 3D detail (didukung vektor 3D 21 kecamatan OpenFreeMap).</li>
    <li>Rekomendasi merata 217 titik PJU Pintar, CCTV Analitik, dan Pos Pantau Panic Button (minimal 9 unit per kecamatan) bersama 7 rute patroli KRYD (196,92 km) secara spasial melindungi 3.149 dari 10.905 gedung berisiko tinggi (total 17.357 bangunan terlindungi).</li>
    <li>Penyatuan sistem desain neubrutalism, palet warna Color Hunt (<code>#071B2B</code>, <code>#167D8D</code>, <code>#B9E4E8</code>, <code>#EEEEEE</code> + aksen lampu <code>#FFC94D</code>), Bumi Malam NASA VIIRS, Terrain 3D satelit nyata, proyeksi adaptif Globe 3D (maks zoom-out Z 2,0)/Mercator 3D, serta 240 instansi aset GLB Blender di MapLibre GL JS v5.24.1 + three.js r169 menghasilkan seluruh keluaran wajib praktikum (<code>.qgz</code>, <code>.png</code>, WebGIS interaktif, dan makalah <code>.pdf</code>) secara utuh dan terverifikasi.</li>
  </ol>

  <h2>5.2 Referensi Data &amp; Pustaka</h2>
  <ul>
    <li>Elvidge, C. D., Zhizhin, M., Ghosh, T., Hsu, F. C., &amp; Taneja, J. (2021). <em>Annual time series of global VIIRS nighttime lights derived from monthly averages</em>. Remote Sensing, 13(5), 922 (Dataset 2024 OpenGeoHub / Zenodo DOI: 10.5281/zenodo.17294744).</li>
    <li>Badan Informasi Geospasial (BIG). <em>Peta Rupabumi Indonesia (RBI) Skala 1:50.000 Batas Administrasi Kecamatan Kota Medan</em>.</li>
    <li>OpenStreetMap Contributors &amp; Nominatim / OSRM Project (2026). <em>Data Bangunan, Jalan, Sungai, dan Fasilitas Keamanan Kota Medan melalui OSM API v0.6</em>.</li>
    <li>Polrestabes Medan &amp; Polda Sumatera Utara. <em>Rilis Pemetaan Titik Rawan Kejahatan Jalanan (Curas/Begal) dan Layanan Call Center Satgas Anti-Begal Kota Medan (110 / 0812-6262-0110)</em>.</li>
  </ul>
</body>
</html>
"""

    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"[03_PDF] Wrote Makalah HTML -> {HTML_OUT}")

    cmd = [
        CHROME_EXE,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_OUT}",
        HTML_OUT.as_uri(),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    print(f"[03_PDF] Generated PDF -> {PDF_OUT} ({PDF_OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
