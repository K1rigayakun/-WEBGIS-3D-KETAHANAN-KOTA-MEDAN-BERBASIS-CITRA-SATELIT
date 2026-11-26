# Panduan Pemakaian Mendeley Cite untuk `Laporan_Kelompok.docx`

Dokumen `Laporan_Kelompok.docx` memakai sitasi teks biasa dengan format APA 7th Edition agar langsung rapi saat dibuka. Untuk menghubungkannya ke Mendeley Cite yang terikat dengan akun Mendeley Anda, ikuti langkah berikut ini.

---

## 1. Langkah Import ke Mendeley Reference Manager

1. Buka aplikasi **Mendeley Reference Manager**.
2. Klik **File** → **Import Library** → **RIS (.ris)**, lalu pilih berkas `Referensi_Kelompok_Mendeley.ris`.
3. Periksa kembali apakah seluruh **13 referensi** sudah masuk ke pustaka Mendeley Anda.

### Catatan Entri Manual Referensi Web/RFC (`ELEC` & `RPRT`)
Beberapa versi Mendeley Reference Manager kadang melewatkan rincian situs pada entri `ELEC` atau `RPRT` saat import RIS. Jika ada di antara empat entri di bawah ini yang tidak tampil lengkap, tambahkan secara manual melalui **+ Add New** → **Add Entry Manually** (pilih tipe **Web Page** atau **Report**):

| No | Tipe | Judul (`Title`) | Penulis (`Authors`) | Tahun | Situs / Penerbit | URL |
|---|---|---|---|---|---|---|
| 1 | Report | `The GeoJSON Format (RFC 7946)` | Butler, Howard; Daly, Martin; Doyle, Allan; Gillies, Sean; Hagen, Stefan; Schaub, Tim | 2016 | Internet Engineering Task Force | `https://www.rfc-editor.org/info/rfc7946` |
| 2 | Web Page | `MapLibre GL JS Documentation` | MapLibre Organization | 2025 | MapLibre | `https://maplibre.org/maplibre-gl-js/docs/` |
| 3 | Web Page | `QGIS User Guide (3.40): Laying Out the Maps and Raster Analysis` | QGIS Development Team | 2025 | QGIS Project | `https://docs.qgis.org/3.40/en/docs/user_manual/print_composer/index.html` |
| 4 | Web Page | `Three.js Documentation: WebGLRenderer and GLTFLoader` | Three.js Authors | 2025 | Three.js | `https://threejs.org/docs/` |

---

## 2. Mengaktifkan Mendeley Cite di Microsoft Word

1. Buka `Laporan_Kelompok.docx` di Microsoft Word.
2. Masuk ke tab **Sisipkan** (*Insert*) → **Dapatkan Add-in** (*Get Add-ins*) → cari **"Mendeley Cite"**, lalu pasang dan masuk (*login*) ke akun Mendeley Anda.
3. Buka panel **Mendeley Cite** di tab **Referensi** (*References*), masuk ke bagian **Pengaturan Sitasi** (*Citation Settings*) → **Ubah Gaya Sitasi** (*Change Citation Style*) → pilih **American Psychological Association 7th edition**.

---

## 3. Tabel Peta Sitasi (Ganti Satu per Satu)

Ganti seluruh **18 sitasi** di dalam isi laporan mengikuti urutan tabel berikut. Caranya: blok teks `(Nama, Tahun)` → hapus → di panel Mendeley Cite cari judul pada kolom paling kanan → klik **Sisipkan Sitasi** (*Insert Citation*).

| No | Lokasi (BAB / Subbab) | Potongan Kalimat (5–8 Kata Sebelum Sitasi) | Sitasi Teks | Referensi yang Dipilih di Mendeley (`TI`) |
|---|---|---|---|---|
| 1 | BAB 1 / 1.1 | `...surface temperature (LST) sejalan dengan berkurangnya vegetasi` | `(Pohan & Sulistiyono, 2023)` | `Analysis of the Relationship Between Urban Heat Island (UHI) Phenomenon and Land Cover Change in Medan City Using Landsat Satellite Imagery` |
| 2 | BAB 1 / 1.1 | `...koridor komersial dan permukiman padat di pusat kota` | `(Putri et al., 2025)` | `Pemanfaatan Google Earth Engine untuk Menganalisis Pola Urban Heat Island di Kota Medan` |
| 3 | BAB 1 / 1.1 | `...pinggiran berada di luar jangkauan layanan cepat pemadam` | `(Evalianto et al., 2024)` | `Analisis Lokasi Pos Damkar Berdasarkan Peta Kerawanan Kebakaran Menggunakan SIG Di Jakarta Timur` |
| 4 | BAB 1 / 1.1 | `...membedakan kawasan terang dan kantong gelap secara terukur` | `(Elvidge et al., 2021)` | `Annual Time Series of Global VIIRS Nighttime Lights Derived from Monthly Averages: 2012 to 2019` |
| 5 | BAB 2 / 2.1 | `...jaringan jalan guna mendukung keputusan tata ruang kota` | `(Evalianto et al., 2024)` | `Analisis Lokasi Pos Damkar Berdasarkan Peta Kerawanan Kebakaran Menggunakan SIG Di Jakarta Timur` |
| 6 | BAB 2 / 2.1 | `...minimum, dan maksimum piksel raster pada tiap poligon wilayah` | `(QGIS Development Team, 2025)` | `QGIS User Guide (3.40): Laying Out the Maps and Raster Analysis` |
| 7 | BAB 2 / 2.2.1 | `...supaya nilai radiansi malam antarwilayah bisa dibandingkan konsisten` | `(Elvidge et al., 2021)` | `Annual Time Series of Global VIIRS Nighttime Lights Derived from Monthly Averages: 2012 to 2019` |
| 8 | BAB 2 / 2.2.1 | `...pergeseran kawasan sejuk menjadi zona urban heat island akibat penambahan bangunan` | `(Pohan & Sulistiyono, 2023)` | `Analysis of the Relationship Between Urban Heat Island (UHI) Phenomenon and Land Cover Change in Medan City Using Landsat Satellite Imagery` |
| 9 | BAB 2 / 2.2.1 | `...suhu permukaan tertinggi selalu terkumpul pada kawasan pusat kota yang padat` | `(Putri et al., 2025)` | `Pemanfaatan Google Earth Engine untuk Menganalisis Pola Urban Heat Island di Kota Medan` |
| 10 | BAB 2 / 2.2.2 | `...air, sedangkan nilai tinggi menandakan kanopi pohon rimbun` | `(Sufrianto et al., 2025)` | `Sentinel-2 NDVI Analysis Using GEE and QGIS for Green Open Space Sustainability Assessment in Kendari City` |
| 11 | BAB 2 / 2.2.2 | `...menghitung selisih tinggi lahan terhadap dasar alur sungai pengalirnya` | `(Hu & Demir, 2021)` | `Real-Time Flood Mapping on Client-Side Web Systems Using HAND Model` |
| 12 | BAB 2 / 2.3 | `...memengaruhi ketajaman pola keruangan yang terbaca dari data perkotaan` | `(Luo et al., 2021)` | `The Influence of Spatial Grid Division on the Layout Analysis of Urban Functional Areas` |
| 13 | BAB 2 / 2.3 | `...menjaga keseimbangan antara detail lokal dan kestabilan statistik wilayah` | `(Kang et al., 2021)` | `Improvements in Evaluating Grids for Basic Living Infrastructure: The Case of Gwangjin District in Seoul, South Korea` |
| 14 | BAB 2 / 2.3 | `...mampu mengungkap kantong blindspot yang luput oleh jarak garis lurus` | `(Evalianto et al., 2024)` | `Analisis Lokasi Pos Damkar Berdasarkan Peta Kerawanan Kebakaran Menggunakan SIG Di Jakarta Timur` |
| 15 | BAB 2 / 2.4.1 | `...(EPSG:4326) dalam format titik, garis, dan poligon` | `(Butler et al., 2016)` | `The GeoJSON Format (RFC 7946)` |
| 16 | BAB 2 / 2.4.1 | `...peralihan mulus antara proyeksi datar Mercator dan bola bumi 3D` | `(MapLibre Organization, 2025)` | `MapLibre GL JS Documentation` |
| 17 | BAB 2 / 2.4.1 | `...kecepatan bingkai gambar tinggi pada aplikasi peta web maupun seluler` | `(Ammann et al., 2022)` | `MapLibre-RS: Toward Portable Map Renderers` |
| 18 | BAB 2 / 2.4.2 | `...mekanisme custom layer yang berbagi konteks WebGL bersama kanvas MapLibre` | `(Three.js Authors, 2025)` | `Three.js Documentation: WebGLRenderer and GLTFLoader` |

---

## 4. Menyisipkan Daftar Pustaka dari Mendeley Cite

1. Gulir ke halaman **DAFTAR PUSTAKA** di bagian akhir dokumen.
2. **Jangan menghapus baris pertama** yang berisi tautan GitHub proyek (`https://github.com/K1rigayakun/-WEBGIS-3D-KETAHANAN-KOTA-MEDAN-BERBASIS-CITRA-SATELIT.git`).
3. Hapus ke-13 entri referensi teks biasa di bawah baris tautan GitHub tersebut.
4. Letakkan kursor di baris kosong tepat di bawah tautan GitHub.
5. Di panel Mendeley Cite, klik **Lainnya** (*More*) → **Sisipkan Bibliografi** (*Insert Bibliography*).
6. Rapikan hasil bibliografi agar sesuai aturan format: font **Times New Roman 12pt**, **rata kiri-kanan** (*justify*), spasi baris **1,5**, *hanging indent* **1,25 cm**, *spacing before/after* **0**, warna teks **hitam**, serta hapus garis bawah (*underline*) pada URL/DOI.

## 5. Pengecekan Akhir

1. Pastikan jumlah sitasi Mendeley di dokumen tepat **18 buah** (sesuai jumlah baris pada Tabel Peta Sitasi di atas).
2. Pastikan jumlah entri bibliografi yang muncul dari Mendeley tepat **13 referensi** (ditambah 1 tautan GitHub di baris paling atas).
