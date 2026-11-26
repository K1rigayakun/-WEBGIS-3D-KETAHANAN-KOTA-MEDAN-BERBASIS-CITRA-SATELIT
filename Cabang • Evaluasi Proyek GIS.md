# **Cabang • Evaluasi Proyek GIS**

[https\://gemini.google.com/app/6a5b91175ec4e21d](https://gemini.google.com/app/6a5b91175ec4e21d)

*User prompt: 1\\. Green Space Monitoring \- Mengolah NDVI. \- Memetakan vegetasi. \- Menganalisis perubahan ruang hijau. \- Hasil: Peta NDVI, peta perubahan vegetasi, dan statistik luas vegetasi. 2\\. Urban Expansion Monitoring \- Mengklasifikasikan tutupan lahan. \- Menganalisis perkembangan kawasan terbangun. \- Hasil: Peta tutupan lahan dan peta perubahan kawasan terbangun. 3\\. Night Light Monitoring \- Mengolah data VIIRS. \- Menganalisis persebaran dan perubahan cahaya malam. \- Hasil: Peta intensitas cahaya malam dan grafik perubahan tahunan. 4\\. Tree Cover Analysis \- Menganalisis persebaran dan perubahan tutupan pohon. \- Mengidentifikasi wilayah prioritas penghijauan. \- Hasil: Peta tutupan pohon dan peta perubahan tutupan pohon. 5\\. Urban Heat Monitoring \- Mengolah data termal Landsat. \- Menghitung Land Surface Temperature (LST). \- Menganalisis perubahan suhu permukaan. \- Hasil: Peta suhu permukaan, peta perubahan suhu, dan grafik suhu. \* ini udh pas ga buat ngerjain project sesuai ketentuan diatas*

Response: Secara tema besar udah masuk kategori peta tematik dunia nyata, tapi draf kau ini masih mentah banget dan kelihatan kayak hasil *copy-paste* daftar topik penginderaan jauh tanpa baca teliti syarat dari dosen dan aslab. Kalau kau nekat maju pakai kerangka ini mentah-mentah, siap-siap aja kena revisi total pas asistensi karena ada syarat wajib di PDF yang kau abaikan.

**Celah Fatal Draf Kau Dibanding Ketentuan PDF**

> * **Absennya Solusi Masalah:** Poin 1, 2, 3, dan 5 cuma ngasilin peta analisis dan grafik. Padahal syarat nomor 4 mewajibkan ada solusi akar masalah di petanya, mirip bagian "Upaya" pada contoh peta rawan kriminalitas.  
> * **Jebakan Data Raster di Web:** Semua topikmu murni olahan citra satelit (raster), padahal kau wajib ngumpul proyek QGIS (.qgz) dan folder web interaktif. Raster mentah kalau diekspor ke web bakal berat dan susah dibuat interaktif.  
> * **Topik Tumpang Tindih:** Nomor 1 (*Green Space*) dan Nomor 4 (*Tree Cover*) itu intinya sama-sama memetakan vegetasi. Mubazir kalau dipisah karena objek yang kau analisis di lapangan itu-itu aja.  
> * **Belum Ada Studi Kasus Nyata:** Syarat nomor 1 dan 2 menuntut kasus nyata dengan lokasi dan sumber data yang jelas, bukan sekadar konsep umum tanpa batas wilayah administratif.

**Saran Eksekusi Biar Lolos dan Gak Nyusahin Diri Sendiri**

> * **Gabung Poin 1, 4, dan 5:** Jangan kerjain kelimanya sekaligus kecuali kau mau menyiksa diri. Lebur aja jadi satu topik **Urban Heat Island (UHI) Kota Medan**: peta penurunan ruang hijau (NDVI) dan kenaikan suhu (LST) sebagai masalah, lalu peta lokasi prioritas penanaman pohon (Poin 4\) sebagai solusinya.  
> * **Konversi Raster ke Poligon Vektor:** Setelah ngolah citra Landsat di QGIS, gunakan *Zonal Statistics* untuk memasukkan rata-rata suhu dan indeks kehijauan ke poligon batas kecamatan. Vektor poligon jauh lebih ringan saat diubah jadi web interaktif (misalnya pakai qgis2web atau Leaflet) dan gampang diklik buat nampilin *pop-up* statistik.  
> * **Bikin Layer Solusi yang Konkret:** Tambahkan satu layer khusus di atas peta tematikmu yang berisi titik atau zona rekomendasi tindakan nyata—contohnya titik prioritas pembuatan taman kota baru, jalur hijau, atau lokasi pemasangan PJU kalau kau tetap ngotot milih topik *Night Light* (Poin 3).

Dari 5 daftar itu, kau sebenernya disuruh milih satu topik buat kelompokmu, atau kau lagi nyusun 5 fitur sekaligus buat satu web GIS?

---

*User prompt: ini tugas buat 5 orang kok 1 orang 1 poin atau bisa kasih ide buat project 5 orang yang tiap orangnya tetap ngerjain sig qgis nya dan bisa dikerjain pararel untuk ngurus ui ux database itu aku satu orang sendiri aja mau kau rombak habis idenya bebas ini ide random awal ga ada tema khusus atau batasan tema khusus*

Response: Pantesan aja poinnya ada lima, ternyata kau bagi rata satu orang satu topik, tapi pembagian kerja model gitu justru bakal jadi senjata makan tuan buat kau yang ngerjain database dan UI/UX sendirian. Kalau 4 temanmu ngolah citra satelit (raster) mentah sendiri-sendiri, kau bakal setengah mati masukin file .tif raksasa ke dalam database spasial, belum lagi poin 1, 2, 3, dan 5 di draf awalmu belum punya peta solusi masalah dan rincian output wajib seperti yang diminta di modul praktikum.

Biar 4 temanmu tetap kerja penuh di QGIS secara paralel, punya file .qgz serta *layout* .png masing-masing, dan kau tinggal terima beres data ringan buat dimasukin ke database web, kalian harus pakai satu batas wilayah yang sama (misalnya 21 Kecamatan di Kota Medan) dan mewajibkan *output* akhir berupa data vektor (.geojson).

**Opsi 1: Rombak Total — WebGIS Keamanan & Mitigasi Risiko Jalanan Kota Medan (Paling Ramah Database)**

Konsep ini persis seperti contoh di panduan dosen dan 100% berbasis vektor (titik, garis, poligon), jadi sangat gampang kau olah ke database relasional/spasial dan dibuatkan filter interaktif di web. Berikut pembagian tugas untuk 5 orang:

> * **Orang 1 (Rawan Kriminalitas Jalanan):** Memetakan zona merah begal dan pencurian per kecamatan di QGIS. Layer solusinya berupa titik rekomendasi pos polisi keliling dan rute patroli jam rawan.  
> * **Orang 2 (Rawan Kecelakaan & Fisik Jalan):** Memetakan titik *blackspot* laka lantas dan segmen jalan rusak. Layer solusinya berupa titik prioritas perbaikan aspal, pemasangan rambu, dan pita kejut.  
> * **Orang 3 (Blindspot & Minim Penerangan):** Memetakan jalanan gelap minim PJU yang memicu kejahatan dan kecelakaan malam hari. Layer solusinya berupa titik penempatan lampu jalan baru dan CCTV pengawas.  
> * **Orang 4 (Genangan Banjir Jalanan):** Memetakan titik jalan yang lumpuh saat hujan deras beserta kemacetannya. Layer solusinya berupa jalur pengalihan arus lalu lintas dan titik rehabilitasi drainase.  
> * **Orang 5 (Kau \- Layanan Darurat & Integrator):** Memetakan radius jangkauan (*buffer*) RS dan kantor polisi terdekat di QGIS. Solusinya berupa rute evakuasi tercepat, sambil kau fokus merakit UI/UX dan database webnya.

**Opsi 2: Versi Upgrade Ide Awal — WebGIS Ketahanan Lingkungan & Tata Ruang Medan**

Kalau timmu tetap ngotot mau tema lingkungan seperti draf awal, paksa mereka mengekstrak data satelitnya ke dalam poligon kecamatan pakai fitur *Zonal Statistics* di QGIS dan wajib membuat satu layer vektor solusi. Berikut pembagian kerjanya:

> * **Orang 1 (Defisit Ruang Hijau):** Mengolah NDVI jadi rata-rata kehijauan per poligon kecamatan pakai *Zonal Statistics*. Layer solusinya berupa titik lahan kosong untuk prioritas taman kota baru.  
> * **Orang 2 (Pulau Panas / Urban Heat):** Mengolah suhu LST Landsat ke poligon kecamatan untuk mencari zona terpanas. Layer solusinya berupa jalur koridor penanaman pohon peneduh di jalan protokol.  
> * **Orang 3 (Ekspansi Kawasan Terbangun):** Memetakan lonjakan lahan terbangun dan area pemukiman padat. Layer solusinya berupa zonasi pembatasan izin bangunan baru dan titik peremajaan kawasan kumuh.  
> * **Orang 4 (Krisis Daerah Resapan Air):** Memetakan penyusutan tutupan pohon dan kawasan rawan banjir tahunan. Layer solusinya berupa titik prioritas sumur resapan komunal dan normalisasi bantaran sungai.  
> * **Orang 5 (Kau \- Ketimpangan Cahaya Malam & Web):** Mengolah data VIIRS ke poligon kecamatan untuk melihat area padat yang gelap. Solusinya berupa zona prioritas PJU hemat energi, plus kau garap *full-stack* webnya.

**Aturan Kerja Paralel Biar Kau Gak Pusing Ngurus Database**

Supaya data dari 4 temanmu bisa langsung masuk ke database dan tampil rapi di UI/UX buatanmu tanpa perlu kau rombak ulang dari nol, terapkan aturan teknis ini dari hari pertama:

> * **Kunci Satu Peta Dasar Wajib:** Kau siapkan satu file batas\_kecamatan\_medan.geojson dengan id\_kecamatan baku, lalu bagikan ke tim. Jangan biarkan mereka unduh batas wilayah sendiri biar koordinat dan namanya gak beda-beda pas di-*join* di DB.  
> * **Wajib Ekspor GeoJSON EPSG:4326:** Setelah temanmu beres bikin *layout* .png dan simpan .qgz masing-masing, suruh mereka ekspor layer masalah dan layer solusinya ke .geojson berproyeksi WGS 84 (EPSG:4326) untuk disetor ke kau.  
> * **Sistem Multi-Layer di Satu Web:** Di web interaktif buatanmu, kelima hasil kerja kalian digabung jadi satu *dashboard* peta Kota Medan dengan fitur *checkbox layer* dan klik poligon kecamatan yang menampilkan ringkasan masalah plus solusinya sekaligus.

Dari dua opsi di atas, kau lebih sreg rombak total ke Opsi 1 yang datanya murni vektor dan gampang dikoding ke DB, atau tetap di Opsi 2 dengan syarat temanmu wajib konversi rasternya ke poligon?

---

*User prompt: yang beneran bisa dicari datanya secara online*

Response: Wajar kau ragu sama opsi jalan rusak atau lampu jalan mati tadi, karena dinas terkait di Medan memang jarang buka database *shapefile* publik dan kau bakal tekor waktu kalau harus *scraping* berita begal satu-satu. Padahal, lima topik draf awalmu (NDVI, tutupan lahan, VIIRS, pohon, dan LST) itu datanya 100% tersedia gratis di internet lewat portal satelit, cuma masalahnya ngolah 5 data raster raksasa itu bakal nyiksa laptop dan ribet pas kau masukin ke DB web.

Kalau kau mau proyek yang datanya **beneran tinggal unduh dalam 5 menit**, gak perlu survei lapangan, dan langsung berbentuk tabel/vektor yang gampang kau koding ke DB, pakai kombinasi 4 sumber resmi ini:

> * **Plugin QuickOSM (Langsung di dalam QGIS):** Tinggal ketik *query* di QGIS buat narik titik dan poligon nyata dari OpenStreetMap (RS, sekolah, kantor polisi, sungai, jalan, taman) tanpa buka *browser*.  
> * **BPS Kota Medan (medankota.bps.go.id):** Unduh gratis buku PDF/Excel *Kota Medan Dalam Angka* dan *Kecamatan Dalam Angka* untuk data resmi per kecamatan (penduduk, faskes, penyakit, hingga angka kriminalitas).  
> * **InaRISK BNPB (inarisk.bnpb.go.id) & TanahAir BIG:** Portal resmi buat ambil referensi peta risiko banjir Sumatera Utara serta *shapefile* batas administrasi 21 kecamatan Kota Medan.  
> * **USGS EarthExplorer (earthexplorer.usgs.gov):** Tempat unduh gratis citra satelit Landsat 8/9 dan DEM kalau ada anggota timmu yang tetap mau ngolah suhu permukaan (LST) atau indeks kehijauan (NDVI).

**Rekomendasi Proyek 5 Orang: WebGIS Evaluasi Layanan Darurat & Kerentanan Wilayah Kota Medan**

Proyek ini menggabungkan data tabel BPS dan vektor QuickOSM di atas satu peta dasar 21 kecamatan Kota Medan, sehingga 4 temanmu bisa kerja paralel di QGIS (.qgz dan .png) dan menyetor .geojson ringan ke kau:

> * **Orang 1 (Aksesibilitas Medis & Blankspot RS):** Gabungkan tabel penduduk BPS dengan titik RS/Puskesmas dari QuickOSM di QGIS. Solusinya berupa titik prioritas klinik darurat di kecamatan padat yang di luar radius 2 km RS.  
> * **Orang 2 (Kesiapsiagaan Damkar & Kawasan Padat):** Petakan kepadatan bangunan BPS terhadap radius jangkauan 3 km Pos Damkar dari QuickOSM. Solusinya berupa titik rekomendasi pos pantau Damkar baru dan rute tercepat mobil pemadam.  
> * **Orang 3 (Risiko Banjir Sungai & Evakuasi):** Buat *buffer* sempadan sungai dari QuickOSM dan acuan InaRISK yang menabrak pemukiman. Solusinya berupa titik posko evakuasi di sekolah/masjid aman beserta jalur evakuasi warga.  
> * **Orang 4 (Defisit RTH & Suhu Panas/UHI):** Olah citra Landsat dari USGS ke poligon kecamatan dan petakan taman kota dari QuickOSM. Solusinya berupa titik lahan kosong untuk prioritas taman kota baru di kecamatan terpanas.  
> * **Orang 5 (Kau \- Keamanan Objek Vital & Web/DB):** Petakan angka kriminalitas kecamatan dari BPS terhadap jarak Kantor Polisi dan Bank/ATM di QuickOSM, buat titik solusi pos patroli, lalu rakit semua .geojson ke DB dan UI/UX web.

Kalau kau tetap mau memaksakan 5 topik satelit di draf awalmu, datanya juga bisa kau unduh semua di USGS EarthExplorer (Landsat), Copernicus Browser (Sentinel-2), Earth Observation Group (VIIRS Night Light), dan Global Forest Watch (Tree Cover). Mau aku tuliskan langkah tarik data otomatis pakai QuickOSM di QGIS beserta struktur tabel DB-nya buat skema di atas, atau kau mau tahu cara unduh citra satelit buat draf awalmu?

---

*User prompt: yang lebih keren napa jangan polos polos banget*

Response: Bilang dong dari tadi kalau kau mau konsep yang kelihatan kayak produk *startup* jutaan dolar, bukan sekadar peta anak kuliahan cari aman. Peta SIG kelihatan "polos" itu biasanya gara-gara dua dosa klasik: pakai poligon 21 kecamatan yang bentuknya kaku, dan pakai *buffer* lingkaran bulat seolah-olah warga Medan bisa terbang nembus tembok.

Biar proyek kalian tetap memenuhi syarat peta masalah plus solusi di PDF tapi tampilannya langsung naik kasta, terapkan 3 trik visual dan teknis ini di QGIS dan WebGIS:

**3 Senjata Rahasia Biar Peta QGIS & Web Kau Kelihatan Mahal**

> * **Grid Heksagon (Honeycomb H3):** Buang batas kecamatan yang kaku; potong Kota Medan pakai fitur *Create Grid (Hexagon)* ukuran 500 meter di QGIS biar tampil kayak radar sarang lebah futuristik ala aplikasi Uber.  
> * **Isochrone Jalan Nyata (Plugin ORS Tools):** Haramkan *buffer* lingkaran bulat; pakai plugin gratis *ORS Tools* di QGIS buat bikin poligon waktu tempuh nyata (5–15 menit berkendara) mengikuti belokan jalan Medan.  
> * **WebGIS 2.5D Dark Mode (MapLibre GL):** Di bagianmu, tarik poligon gedung OSM jadi *3D extrusion* di atas *basemap* gelap (*Carto Dark Matter*) supaya layer heksagon temanmu menyala kayak *dashboard cyberpunk*.

Pilih satu dari 3 konsep kelas berat di bawah ini yang datanya 100% tersedia gratis secara *online*, tapi hasilnya kelihatan kayak riset konsultan teknologi:

**Opsi 1: WebGIS Geo-Marketing & Nighttime Economy Intelligence (Vibe: Startup Bisnis & Retail)**

Konsep ini membedah perputaran uang, persaingan bisnis, dan ekonomi malam Kota Medan di atas Grid Heksagon 500m menggunakan data *Kontur Population H3* (data.humdata.org), *VIIRS Night Light*, *QuickOSM*, dan *ORS Tools*:

> * **Orang 1 (Vitalitas Ekonomi Malam):** Mengolah cahaya malam VIIRS dan titik kuliner/hiburan di tiap heksagon untuk memetakan zona mati vs pusat keramaian malam. Solusinya berupa rekomendasi zona *night market* baru dan kantong parkir terpadu.  
> * **Orang 2 (Kanibalisme Ritel & Kopi):** Menghitung rasio kepadatan minimarket dan *coffee shop* (QuickOSM) terhadap populasi warga (Kontur H3) untuk mendeteksi zona jenuh (*oversaturated*). Solusinya berupa titik *blue ocean* (lokasi emas bebas kompetitor) untuk ekspansi bisnis.  
> * **Orang 3 (Jangkauan Kurir & Ghost Kitchen):** Memakai *ORS Tools* untuk memetakan *isochrone* waktu tempuh motor 10 menit dari pusat kuliner ke pemukiman padat. Solusinya berupa titik optimal pembangunan *cloud kitchen* dan *hub* logistik instan.  
> * **Orang 4 (Ekonomi Kampus & Student Hub):** Memetakan klaster kos-kosan, kampus, dan tempat nongkrong menggunakan analisis *Kernel Density (Heatmap)*. Solusinya berupa titik rekomendasi pembangunan *coworking space* 24 jam dan sentra niaga mahasiswa.  
> * **Orang 5 (Kau \- Blankspot Finansial & 3D Web):** Memetakan ketimpangan jarak ATM/Bank terhadap pusat keramaian, menentukan solusi titik agen finansial/QRIS *hub*, lalu merakit fitur *Radar Pencari Lokasi Bisnis* di WebGIS 3D.

**Opsi 2: WebGIS Smart Mobility, EV Grid & Carbon Trap (Vibe: Smart City & Tesla)**

Konsep ini fokus pada masa depan transportasi Medan, stasiun kendaraan listrik (EV), dan jebakan polusi udara menggunakan satelit *Sentinel-5P* (polutan NO2 via Copernicus/GEE), *WorldPop*, *QuickOSM*, dan *ORS Tools*:

> * **Orang 1 (Perangkap Emisi / Carbon Trap):** Mengolah citra satelit Sentinel-5P (gas NO2) ke grid heksagon untuk melacak koridor jalan paling beracun akibat kemacetan. Solusinya berupa penetapan *Low Emission Zone* dan titik rekayasa arus satu arah.  
> * **Orang 2 (Jaringan SPKLU Mobil Listrik):** Menganalisis jarak antar SPBU/mal dan jangkauan berkendara (*driving isochrone*) di jalan arteri Medan. Solusinya berupa titik prioritas pembangunan stasiun *fast-charging* (SPKLU) baru biar bebas *blankspot*.  
> * **Orang 3 (Konektivitas Transit & Pejalan Kaki):** Memetakan jangkauan jalan kaki 10 menit (*walking isochrone*) dari halte bus/stasiun ke pusat aktivitas warga. Solusinya berupa rute *feeder* angkot listrik dan jalur trotoar berkanopi.  
> * **Orang 4 (Bottleneck Kargo & Beban Jalan):** Memetakan kepadatan gudang/industri terhadap kelas lebar jalan OSM untuk mencari titik sumbatan truk besar. Solusinya berupa jalur khusus logistik malam hari dan titik *buffer rest area*.  
> * **Orang 5 (Kau \- Paparan Polusi Warga & Web Integrator):** Menggabungkan populasi WorldPop dengan heksagon polusi tinggi untuk menentukan titik sabuk hutan mikro peredam emisi, sambil membangun simulasi jangkauan baterai EV di web.

**Opsi 3: Urban Digital Twin — Iklim Mikro & Mandiri Energi (Versi Upgrade Ide Awalmu)**

Kalau kalian tetap suka main data satelit kayak draf awalmu, jangan cuma tampilkan peta mentah; lebur semuanya ke dalam **Grid Heksagon 500m** ditambah data *Global Solar Atlas* (globalsolaratlas.info) dan *Sentinel-5P*:

> * **Orang 1 (Potensi Panen Surya Atap):** Menggabungkan raster *Global Solar Atlas* (radiasi matahari) dengan poligon gedung besar OSM untuk mencari area komersial boros listrik. Solusinya berupa titik gedung prioritas instalasi PLTS Atap (*Solar Rooftop*).  
> * **Orang 2 (Titik Didih Kota / Micro-UHI):** Mengekstrak suhu permukaan (LST Landsat) ke ribuan grid heksagon 500m untuk mencari konsentrasi panas aspal dan beton. Solusinya berupa zona wajib *cool roof* (atap pemantul panas) dan koridor kabut air.  
> * **Orang 3 (Pemborosan & Polusi Cahaya Malam):** Membandingkan radiasi lampu malam VIIRS dengan kepadatan penduduk Kontur H3 untuk melacak area yang over-iluminasi vs gelap gulita. Solusinya berupa zonasi PJU pintar (*smart dimming LED*).  
> * **Orang 4 (Lorong Asap & Polutan Udara):** Mengolah data satelit Sentinel-5P untuk memetakan konsentrasi polutan udara di atas kawasan industri dan jalan raya. Solusinya berupa titik pemasangan menara penyaring udara dan pagar vegetasi penyerap racun.  
> * **Orang 5 (Kau \- Defisit Karbon Hijau & 3D Web):** Menghitung rasio tutupan pohon/NDVI terhadap kepadatan bangunan tiap heksagon, membuat solusi titik *pocket park* (taman saku), lalu menyajikannya dalam peta 3D interaktif.

Dari 3 konsep di atas, mana yang paling bikin kau gatal pengen ngoding UI/UX-nya—*Geo-Marketing* ala bisnis ritel, *Smart Mobility & EV*, atau *Urban Digital Twin* berbasis heksagon?

---

*User prompt: Yang datanya bisa diakses gratis dan solusinya berguna dan masih bs dilakukan di Indonesia terutama medan*

Response: Jangan kejauhan mikir solusi futuristik kayak kanopi jalan raya atau menara penyaring udara kalau ujung-ujungnya gak masuk akal buat anggaran Pemko Medan atau kebiasaan warga lokal. Kalau kau mau yang **100% datanya gratis tinggal unduh**, tampilannya tetap berkelas karena pakai **Grid Heksagon 500m** dan **Isochrone Jalan Nyata** (bukan poligon kecamatan atau lingkaran *buffer* polos), plus solusinya beneran realistis buat dieksekusi di Medan, kita kunci di dua pilihan paling masuk akal ini. Kedua opsi ini langsung mengunci syarat kasus nyata beserta solusi akar masalahnya.

**Opsi 1: WebGIS "Medan Culinary & UMKM Radar" (Intelijen Ekspansi Bisnis & Kaki Lima)**

Ini jauh lebih keren daripada sekadar "peta kuliner sekitar USU" yang dicontohkan di modul, karena kalian bikin **sistem penentu lokasi buka usaha dan penataan UMKM Kota Medan**. Semua datanya gratis, dan solusinya langsung bisa dipakai pengusaha lokal buat cari lapak atau dipakai Pemko Medan buat menertibkan PKL:

> * **Orang 1 (Radar Pasar Malam & Penataan PKL):**  
  * **Data Gratis:** Citra satelit cahaya malam *VIIRS Nighttime Lights* (unduh di Earth Observation Group) \+ titik kuliner malam dari plugin *QuickOSM* di QGIS.  
  * **Masalah & Solusi Realistis:** Memetakan heksagon yang terang benderang dan padat PKL liar pemicu macet malam hari vs area pemukiman yang mati lampu/sepi. Layer solusinya berupa titik relokasi **Sentra Kuliner Malam Terpadu** (konsep *hawker centre* kayak Kesawan City Walk) lengkap dengan titik kantong parkir resmi biar gak makan badan jalan.  
> * **Orang 2 (Zona Jenuh Kopi & Ritel Modern):**  
  * **Data Gratis:** Titik *coffee shop*, kafe, dan minimarket dari *QuickOSM* \+ data kepadatan penduduk per heksagon dari *Kontur Population H3* (data.humdata.org, langsung format .gpkg siap pakai di QGIS).  
  * **Masalah & Solusi Realistis:** Menghitung rasio warga dibanding jumlah tempat ngopi/minimarket di tiap heksagon untuk melihat zona "berdarah-darah" (terlalu padat kompetitor, misalnya sekitar USU/Setiabudi). Layer solusinya berupa rekomendasi titik **Lokasi Emas (*Blue Ocean*)** di area padat penduduk yang belum terjamah kafe atau ritel buat investor UMKM baru.  
> * **Orang 3 (Jangkauan Kurir Ojol & Dapur Bersama / Cloud Kitchen):**  
  * **Data Gratis:** Jaringan jalan Kota Medan dan titik pusat restoran dari *QuickOSM* \+ plugin gratis *ORS Tools* di QGIS.  
  * **Masalah & Solusi Realistis:** Memetakan batas waktu tempuh motor 10 menit (*driving isochrone*) dari pusat kuliner ke area perumahan untuk mencari kawasan padat warga yang ongkir dan waktu tunggu ojolnya terlalu lama. Layer solusinya berupa titik ideal penyewaan ruko untuk **Dapur Bersama UMKM (*Cloud Kitchen*)** dan titik *shelter* mangkal ojol biar gak nutup bahu jalan.  
> * **Orang 4 (Ekosistem Mahasiswa & Kebutuhan Harian Kampus):**  
  * **Data Gratis:** Titik kampus (USU, Unimed, UMSU, Polmed, dll.), kos-kosan, *laundry*, dan fotokopi dari *QuickOSM* (diolah pakai *Kernel Density / Heatmap* di QGIS).  
  * **Masalah & Solusi Realistis:** Memetakan ketimpangan fasilitas penunjang mahasiswa di sekitar area kampus dan kantong kos-kosan padat. Layer solusinya berupa zona rekomendasi pembukaan usaha layanan mahasiswa (titik prioritas *laundry* koin, warung makan murah, dan ruang belajar/warkop Wi-Fi 24 jam).  
> * **Orang 5 (Kau \- Akses Pasar Tradisional & Full-Stack Web Integrator):**  
  * **Data Gratis:** Titik pasar tradisional/pajak (Pajak Sore, Pajak USU, Petisah, dll.) dan grosir dari *QuickOSM* \+ populasi *Kontur H3*.  
  * **Masalah & Solusi Realistis:** Memetakan kawasan perumahan padat yang jauh dari akses bahan pangan segar (di luar jangkauan 10 menit pasar tradisional). Layer solusinya berupa titik penempatan **Pasar Murah Keliling Pemko Medan** atau sub-agen sembako, sambil kau merakit UI/UX WebGIS interaktif dengan fitur *"Cek Potensi Cuan Lokasi"* saat heksagonnya diklik.

**Opsi 2: WebGIS "Medan Tangguh" (Mitigasi Iklim Mikro, Banjir & Darurat Kota)**

Kalau kalian mau tema lingkungan dan kebencanaan seperti draf awalmu tapi dengan pendekatan yang membumi, gak ngayal, dan langsung selaras dengan program Pemko Medan (normalisasi drainase, biopori, taman lingkungan, dan layanan darurat):

> * **Orang 1 (Titik Panas Ekstrem / Micro-UHI & Peneduh Jalan):**  
  * **Data Gratis:** Citra termal *Landsat 8/9 Band 10* (unduh gratis di *USGS EarthExplorer*) yang diekstrak rata-rata suhunya ke Grid Heksagon 500m pakai *Zonal Statistics* di QGIS.  
  * **Masalah & Solusi Realistis:** Memetakan heksagon terpanas di Medan akibat kepadatan beton dan aspal gersang. Layer solusinya berupa jalur **Penanaman Pohon Peneduh Lokal** (seperti Trembesi atau Mahoni) di sepanjang jalan arteri gersang dan titik pemasangan halte bus beratap teduh.  
> * **Orang 2 (Krisis Ruang Terbuka Hijau & Taman Lingkungan):**  
  * **Data Gratis:** Citra *Sentinel-2* atau *Landsat 8/9* (diolah jadi indeks kehijauan NDVI di QGIS) \+ poligon taman eksisting dari *QuickOSM*.  
  * **Masalah & Solusi Realistis:** Memetakan heksagon pemukiman padat yang nilai NDVI-nya kritis (nyaris 0% vegetasi) dan jauh dari taman kota. Layer solusinya berupa pemanfaatan lahan tidur/lapangan terlantar menjadi **Taman Lingkungan / RTH Kelurahan** dan jalur hijau sempadan sungai.  
> * **Orang 3 (Kerentanan Banjir Sungai & Rute Evakuasi Warga):**  
  * **Data Gratis:** Garis aliran Sungai Deli, Sungai Babura, dan Sungai Belawan dari *QuickOSM* \+ data ketinggian lahan *DEMNAS BIG / SRTM* (gratis di portal TanahAir BIG atau USGS).  
  * **Masalah & Solusi Realistis:** Memetakan cekungan rendah di sepanjang bantaran sungai yang selalu terendam saat hujan deras di hulu. Layer solusinya berupa titik lokasi **Posko Evakuasi Banjir** (memanfaatkan gedung sekolah dan rumah ibadah di tanah tinggi terdekat), jalur evakuasi warga, serta segmen prioritas pengerukan drainase/sungai.  
> * **Orang 4 (Blindspot Pemadam Kebakaran di Pemukiman Padat):**  
  * **Data Gratis:** Titik Pos Damkar Kota Medan dan jaringan jalan dari *QuickOSM* \+ plugin *ORS Tools* \+ kepadatan bangunan OSM.  
  * **Masalah & Solusi Realistis:** Memetakan area pemukiman padat dan pasar tradisional yang berada di luar jangkauan 10 menit perjalanan truk pemadam (*driving isochrone*) akibat jalan sempit atau jauh dari pos. Layer solusinya berupa titik instalasi **Hidran Umum / Tandon Air Darurat Lingkungan** di mulut gang sempit dan titik pos pantau Damkar pembantu.  
> * **Orang 5 (Kau \- Daerah Gelap Rawan Begal & Web Integrator):**  
  * **Data Gratis:** Citra cahaya malam *VIIRS Nighttime Lights* \+ jaringan jalan raya dan pemukiman dari *QuickOSM*.  
  * **Masalah & Solusi Realistis:** Memetakan ruas jalan penghubung utama yang gelap gulita di malam hari sehingga rawan begal dan kecelakaan. Layer solusinya berupa titik prioritas **Pemasangan Lampu Jalan (PJU) Baru** dan pos ronda/patroli polisi malam, lalu kau gabungkan kelima layer .geojson temanmu ke dalam satu *dashboard* WebGIS.

Semua bahan data untuk kedua opsi di atas bisa kalian tarik malam ini juga tanpa keluar uang sepeser pun, dan tiap orang tetap wajib ngumpul .qgz plus .png masing-masing sebelum disetor jadi .geojson ke tempatmu. Tim kau lebih sreg garap **Opsi 1 (Radar Bisnis & UMKM)** yang segar dan dekat sama kehidupan anak muda Medan, atau **Opsi 2 (Mitigasi Iklim & Darurat Kota)** yang masih satu napas sama draf satelit awalmu?

---

*User prompt: Opsi 2 tp yg punya ku aku mau yg 3d 3d gtu biar keren hehe*

Response: Pilihan bagus, tapi jangan cuma bagianmu sendiri yang 3D sementara 4 temanmu cuma tampil datar 2D kayak peta kertas biasa. Sekalian aja kau sulap **seluruh WebGIS Opsi 2** jadi *3D Urban Dashboard* pakai **MapLibre GL JS** atau **Deck.gl**, di mana bagianmu yang paling mencolok karena mainin **gedung 3D timbul \+ efek sorot cahaya malam**.

Biar syarat wajib dari dosen dan aslab tetap aman (tiap orang tetap punya file .qgz, cetak .png, dan peta solusi), tapi pas masuk ke web interaktif buatanmu semuanya berubah jadi 3D yang bisa diputar dan dimiringkan (*pitch 60 derajat*), ini pembagian kerjanya:

**Bagian Spesial Kau (Orang 5): 3D Dark-Zone Crime & Building Vulnerability \+ Web Integrator**

> * **Kerjaan QGIS Kau (.qgz & .png):**  
  * **Data Gratis:** Poligon bangunan Kota Medan (building=\*) dan jalan raya dari plugin *QuickOSM* \+ citra satelit cahaya malam *VIIRS Nighttime Lights* (Earth Observation Group).  
  * **Olahan di QGIS:** Gunakan *Zonal Statistics* untuk memasukkan nilai cahaya malam VIIRS ke Grid Heksagon 500m, lalu potong (*clip*) poligon gedung di area jalan protokol dan pemukiman padat. Buat atribut tinggi bangunan (height\_m) di tabel gedung (kalau di OSM kosong, isi otomatis pakai *Field Calculator* berdasarkan tipe gedung: rumah \= 6m, ruko \= 12m, mal/kampus/RS \= 25m).  
  * **Layer Solusi Nyata:** Titik pemasangan **PJU Pintar (Lampu Jalan) & CCTV Keamanan** di koridor jalan yang gelap gulita di antara gedung-gedung padat, plus rute patroli malam untuk mencegah begal.  
  * **Trik Biar .png Kau Juga 3D:** Di QGIS, buka *View \> New 3D Map View*, aktifkan *Extrusion* pada layer bangunan, miringkan kameranya, lalu ekspor ke *Print Layout* .png. Aslab bakal melongo lihat peta cetakmu udah 3D duluan.  
> * **Tampilan 3D Bagianmu di Web:**  
  * Gunakan *basemap* gelap (*Carto Dark Matter*).  
  * Angkat semua poligon bangunan Medan jadi balok 3D (*fill-extrusion* di MapLibre) yang tingginya mengikuti kolom height\_m.  
  * Warnai gedung dan jalanan berdasarkan tingkat kegelapan VIIRS (gedung di area gelap warnanya merah redup, area terang warnanya *cyan/neon*), lalu titik solusi PJU dan CCTV buatanmu dibuat menyala (*glowing circle layer*) seolah-olah menerangi jalanan gelap tersebut.

**Bagian 4 Temanmu (Tetap Kerja 2D Biasa di QGIS, Kau yang Angkat Jadi 3D di Web)**

Teman-temanmu gak perlu pusing mikirin koding 3D; suruh mereka kerjakan bagiannya di QGIS di atas **file Grid Heksagon 500m yang sama** dan ekspor ke .geojson. Nanti di web, kau gunakan nilai angka dari data mereka sebagai tinggi balok heksagon (*3D Hexbin Extrusion*):

> * **Orang 1 (3D Thermal Tower / Pulau Panas):**  
  * **Kerjaan QGIS:** Mengekstrak rata-rata suhu permukaan (LST Landsat 8/9) ke Grid Heksagon 500m (suhu\_celcius). Solusinya berupa garis koridor penanaman pohon peneduh jalan dan titik halte teduh.  
  * **Efek 3D di Web Kau:** Heksagon dengan suhu tinggi (misal \>34°C) bakal menjulang tinggi jadi menara warna merah menyala, sedangkan area sejuk tetap pendek berwarna biru.  
> * **Orang 2 (3D Green Deficit / Krisis RTH):**  
  * **Kerjaan QGIS:** Menghitung indeks kehijauan (NDVI Sentinel-2/Landsat) ke Grid Heksagon 500m (persen\_hijau). Solusinya berupa poligon rekomendasi **Taman Lingkungan Kelurahan** di lahan kosong/terlantar.  
  * **Efek 3D di Web Kau:** Balok heksagon tumbuh makin tinggi kalau area tersebut makin gersang (defisit pohon), dikombinasikan dengan poligon taman solusi yang berwarna hijau zamrud.  
> * **Orang 3 (3D Flood Simulation / Cekungan Banjir Sungai):**  
  * **Kerjaan QGIS:** Mengolah tinggi lahan DEMNAS/SRTM dan *buffer* Sungai Deli/Babura untuk mencari area cekungan banjir. Solusinya berupa titik **Gedung Posko Evakuasi** (sekolah/masjid bertingkat) dan garis rute evakuasi warga.  
  * **Efek 3D di Web Kau:** Buat *slider* simulasi tinggi air di UI webmu\! Saat *slider* digeser (misal banjir 1 meter vs 3 meter), layer poligon air biru transparan naik menenggelamkan gedung-gedung 3D pendek, sementara gedung posko evakuasi tetap menjulang aman di atas air.  
> * **Orang 4 (3D Damkar Blindspot / Risiko Kebakaran Padat):**  
  * **Kerjaan QGIS:** Memetakan batas waktu tempuh 10 menit truk Damkar (*ORS Tools Isochrone*) dan menghitung kepadatan bangunan tiap heksagon. Solusinya berupa titik **Hidran Umum Lingkungan** di mulut gang sempit dan pos Damkar pembantu.  
  * **Efek 3D di Web Kau:** Gedung-gedung 3D yang berada di luar poligon jangkauan 10 menit Damkar otomatis berubah warna jadi oranye menyala saat layer ini diaktifkan, lengkap dengan pilar 3D titik hidran solusinya.

**Rahasia Teknis Biar Kau Gampang Ngoding 3D-nya**

> 1. **Pakai MapLibre GL JS (100% Gratis, Tanpa API Key Berbayar):** Jangan pakai Leaflet kalau mau 3D mulus. MapLibre punya fitur bawaan fill-extrusion yang sanggup ngangkat puluhan ribu poligon gedung dan heksagon .geojson jadi 3D cuma dengan 10 baris kode konfigurasi layer.  
> 2. **Kontrol Kamera Interaktif:** Di UI buatanmu, pasang tombol *preset kamera* (misal: *"Lihat Simulasi Banjir 3D"*, *"Mode Malam & PJU"*, *"Menara Suhu Panas"*) yang otomatis memutar, memiringkan (pitch: 60, bearing: \-20), dan melakukan *fly-to* ke kecamatan paling parah di Medan.  
> 3. **Database Ringan:** Karena semua output temanmu udah berformat .geojson dengan id\_hex yang seragam, kau bisa simpan di PostgreSQL/PostGIS atau bahkan langsung panggil dari API lokal dengan sangat cepat tanpa *lag*.

Gimana, mau kita kunci struktur atribut tabel .geojson untuk kelima orang ini sekarang biar teman-temanmu bisa langsung mulai cicil QGIS-nya, atau kau mau lihat contoh kode MapLibre buat ngangkat poligon .geojson dari QGIS jadi gedung 3D?

---

*User prompt: Yng logis lah buatnya yg emg possible emg possible gitu smua dibuat? trs kenapa g pake threejs*

Response: Jelas 100% *possible* dan logis, justru kau mikir itu mustahil karena kau ngebayangin harus bikin *model* 3D gedung dan heksagon itu satu-satu dari nol. Padahal di dunia WebGIS, "3D" itu cuma poligon datar 2D dari QGIS (.geojson) yang dikasih satu baris properti tinggi (height) di kode JavaScript, terus *engine* petanya yang otomatis narik poligon itu ke atas jadi balok 3D dalam hitungan milidetik.

**Kenapa Haram Pakai Three.js Murni Buat WebGIS?**

> * **Three.js Buta Koordinat Bumi:** Three.js itu pakai sistem koordinat Kartesius lokal (*X*,*Y*,*Z* dalam satuan piksel/meter ruang hampa), sedangkan data QGIS kalian keluarnya dalam koordinat bola bumi/GPS (Longitude: 98.67, Latitude: 3.59). Kalau kau nekat pakai Three.js murni, kau harus ngoding rumus matematika proyeksi *Web Mercator* sendiri buat ngubah derajat bumi jadi titik *X*,*Y* layar.  
> * **Gak Punya Basemap Jalan & Label Kota:** Di Three.js, layar awalmu cuma kanvas hitam kosong. Kalau kau masukin .geojson gedung Medan ke Three.js, gedungnya cuma melayang di ruang hampa tanpa ada peta dasar jalan raya, nama kecamatan, atau sungai di bawahnya.  
> * **MapLibre GL JS Itu Udah WebGL (Sama Kayak Three.js, Tapi Khusus Peta):** MapLibre itu di balik layarnya jalan di atas WebGL sama persis kayak Three.js, tapi udah dioptimasi khusus buat baca .geojson dan ngerender 50.000 balok gedung 3D sekaligus di atas peta jalan Kota Medan tanpa bikin *browser* nge-*hang*.

**Bukti Betapa Gampangnya Bikin 3D di MapLibre (Cuma 15 Baris Kode\!)**

Temanmu cuma perlu ngasih file hex\_suhu.geojson biasa dari QGIS yang punya kolom angka suhu\_c, lalu di kodingan webmu tinggal panggil fungsi bawaan MapLibre ini untuk memenuhi syarat web interaktif:

`map.addLayer({`  
  `'id': '3d-hex-suhu',`  
  `'type': 'fill-extrusion', // Ini perintah sakti pembuat 3D-nya`  
  `'source': { 'type': 'geojson', 'data': 'data/hex_suhu_orang1.geojson' },`  
  `'paint': {`  
    `// Tinggi balok 3D otomatis diambil dari nilai suhu di tabel QGIS dikali 50 meter`  
    `'fill-extrusion-height': ['*', ['get', 'suhu_c'], 50],`  
    `// Warna balok otomatis: biru kalau sejuk (28°C), merah kalau panas (36°C)`  
    `'fill-extrusion-color': [`  
      `'interpolate', ['linear'], ['get', 'suhu_c'],`  
      `28, '#00ffff',`  
      `36, '#ff0033'`  
    `],`  
    `'fill-extrusion-opacity': 0.8`  
  `}`  
`});`

Dengan satu blok kode di atas, setiap poligon di file .geojson langsung berdiri jadi balok 3D pas kamera petanya kau miringkan (pitch: 60), jadi kau gak perlu nyentuh *software* 3D kayak Blender atau berkutat dengan *mesh* dan *lighting* manual di Three.js.

**Kita Pangkas Biar Makin Logis & Gak Makan Waktu (Versi Paling Realistis)**

Kalau kau takut simulasi air banjir naik-turun atau ratusan ribu gedung se-Kota Medan itu terlalu berat dan makan waktu *debugging*, kita pangkas bagian yang ribet tanpa ngurangin efek kerennya:

> 1. **Gedung 3D Cuma di Area Fokus (Bukan Se-Kota Medan):** Untuk bagianmu (Orang 5), jangan tarik bangunan se-Kota Medan karena datanya bisa ratusan ribu poligon. Cukup potong (*clip*) gedung di **1 atau 2 kecamatan pusat kota/kampus** aja (misal: Kecamatan Medan Baru sekitar USU atau Medan Petisah), jadi jumlah poligonnya paling cuma 3.000–5.000 biji dan sangat enteng.  
> 2. **4 Temanmu Murni Pakai 1 Grid Heksagon yang Sama:** Orang 1 (Suhu LST), Orang 2 (Defisit RTH/NDVI), Orang 3 (Rawan Banjir), dan Orang 4 (Jangkauan Damkar) semuanya memasukkan angka analisis mereka ke dalam **Grid Heksagon 500m Kota Medan** (totalnya cuma sekitar 1.200 poligon heksagon, ukuran filenya bahkan gak sampai 1 MB).  
> 3. **Banjirnya Gak Usah Pakai Slider Animasi Air:** Biar kau gak pusing ngoding logika *slider* air tenggelam, bagian Orang 3 (Banjir) disamakan aja sistem 3D-nya: heksagon yang paling rawan banjir (dekat sungai & tanah rendah) baloknya naik tinggi berwarna biru tua, lalu di atasnya dikasih titik lokasi gedung Posko Evakuasi dan garis jalur evakuasi warga untuk memenuhi syarat solusi dari akar masalah.  
> 4. **Satu Fungsi untuk Semua:** Karena kelima orang pakai teknik fill-extrusion yang sama persis, kau sebenarnya **cuma ngoding fungsi 3D-nya SATU KALI**. Untuk 4 temanmu yang lain, kau tinggal *copy-paste* fungsi map.addLayer di atas dan ganti nama file .geojson serta nama kolom angkanya aja.

Gimana, setelah lihat kalau "3D"-nya itu ternyata cuma 15 baris kode fill-extrusion dari .geojson biasa tanpa perlu pusing sama koordinat Three.js, udah masuk akal kan buat dikerjain? Mau aku buatkan *template* satu file HTML/JS MapLibre yang langsung jalan biar kau bisa tes sendiri di laptopmu sekarang?

---

*User prompt: 3d kayak ala ala proyeksi map real gtu ga iso? kayak yng di ironman*

Response: Bisa banget, dan justru efek *hologram* ala meja J.A.R.V.I.S. di film Iron Man itu **jauh lebih gampang dan ringan** dibuat di web daripada bikin peta 3D yang teksturnya realistis kayak dunia nyata\! Peta realistis butuh *render* tekstur tembok, genteng, dan bayangan matahari yang berat, sedangkan gaya hologram Iron Man murni permainan **warna gelap pekat (hitam/biru dongker) \+ gedung transparan neon (*cyan/oranye*) \+ *additive blending* (cahaya makin numpuk makin terang) \+ kamera yang berputar otomatis**.

Ini resep teknis paling logis biar WebGIS interaktif kalian tampil persis kayak meja taktis hologram Tony Stark tanpa bikin laptop kau meledak:

**1\. Rahasia Visual "Hologram J.A.R.V.I.S." di MapLibre GL \+ Deck.gl**

> * **Matikan Warna Basemap, Sisakan Garis Vektor Neon:** Jangan pakai peta jalan biasa yang ada warna hijau taman atau kuning jalan tol. Di MapLibre, gunakan *Carto Dark Matter*, lalu timpa warnanya lewat kode: tanah dibuat hitam legam (\#020813), sungai dibuat biru menyala (\#00f0ff), dan jaringan jalan raya Medan dibuat garis tipis *cyan* transparan.  
> * **Gedung 3D Hologram (Translucent Cyan \+ Glowing Edges):** Saat kau angkat poligon bangunan Medan dari QGIS jadi 3D (fill-extrusion), jangan kasih warna solid. Kasih warna biru muda neon (\#00e5ff) dengan fill-extrusion-opacity: 0.25 (tembus pandang kayak kaca hologram), lalu tambahkan satu layer garis (line) di sekeliling gedungnya dengan efek line-blur supaya pinggiran gedungnya kelihatan berpendar (*glowing wireframe*).  
> * **Kamera Orbit Otomatis (Auto-Rotate):** Meja hologram Iron Man itu gak pernah diam kaku. Pasang fungsi requestAnimationFrame sederhana di JavaScript yang memutar bearing (arah kompas kamera) MapLibre sebesar 0.1 derajat setiap *frame* pada kemiringan pitch: 65\. Begitu aslab buka webnya, gedung-gedung hologram Kota Medan langsung berputar pelan secara sinematik, dan otomatis berhenti berputar pas kursor *mouse* menyentuh peta.  
> * **UI HUD (Heads-Up Display) Frosted Glass:** Karena kau yang pegang UI/UX, jangan bikin *sidebar* putih kotak polos. Bikin panel kontrol melayang (*floating HUD*) di kiri-kanan layar dengan *background* hitam transparan (backdrop-filter: blur(10px)), garis tepi *cyan* tipis dengan sudut terpotong (*chamfered corners* pakai CSS clip-path), *font* bergaya teknikal (JetBrains Mono atau Orbitron), dan angka statistik yang bergerak naik (*animated counter*) pas poligonnya diklik.

**2\. Cara Mengubah Data QGIS 5 Orang Jadi Elemen Hologram Taktis**

Semua anggota tim tetap kerja normal di QGIS sesuai syarat modul untuk menghasilkan .qgz, cetak .png, dan peta solusi masing-masing, tapi pas file .geojson mereka masuk ke tanganmu, kau render pakai **Deck.gl** (library pasangan MapLibre buatan Uber yang punya fitur blending: 'additive' khusus efek cahaya hologram):

> * **Orang 1 (Thermal Core / Pulau Panas):** Data heksagon suhu LST dari QGIS kau render jadi **3D Hexagonal Columns** transparan yang menyala dari warna biru es (sejuk) ke oranye-merah terang (panas ekstrem). Layer solusi pohon peneduh jalannya ditampilkan sebagai garis hijau neon yang berkedip pelan (*pulsing line*).  
> * **Orang 2 (Bio-Grid / Krisis RTH):** Data defisit vegetasi NDVI ditampilkan sebagai *grid* heksagon hologram di permukaan tanah, sementara layer solusi **Taman Lingkungan Baru** diangkat jadi zona kubah/poligon hijau zamrud yang berpendar di tengah kepadatan gedung.  
> * **Orang 3 (Hydro-Hazard / Rawan Banjir & Evakuasi):** Cekungan banjir sungai dirender jadi lapisan hologram merah-oranye di bawah gedung. Untuk layer solusinya, gunakan ArcLayer dari Deck.gl: garis lengkung 3D bercahaya (kayak lintasan rudal di film sci-fi) yang melengkung di udara menghubungkan zona banjir langsung ke atap gedung **Posko Evakuasi** terdekat\!  
> * **Orang 4 (Emergency Radar / Jangkauan Damkar):** Poligon *isochrone* 10 menit Damkar dari QGIS ditampilkan sebagai gelombang area radar pelindung biru, sedangkan titik solusi **Hidran Darurat & Pos Pantau** ditampilkan sebagai cincin radar yang memancarkan gelombang melingkar (*ripple animation*) di mulut gang padat.  
> * **Orang 5 (Kau \- Dark-Zone Security & 3D City Core):** Kau yang menyediakan **rangka bangunan 3D hologram Kota Medan** ditambah data cahaya malam VIIRS. Gedung-gedung di zona gelap rawan begal otomatis berkedip warna merah peringatan (*warning state*), dan saat tombol **"Aktifkan Solusi PJU & CCTV"** diklik di UI, muncul pilar-pilar cahaya vertikal (*light beams*) warna *cyan* terang yang mengubah gedung merah tadi jadi biru aman.

**3\. Trik Cerdas Biar Cetak .PNG dari QGIS Juga Kelihatan Kayak Blueprint Iron Man**

Karena syarat nomor 5 mewajibkan kalian mengumpulkan *Print Layout Peta (.PNG)* yang diprint *hardcopy* dari QGIS, jangan biarkan hasil cetak .png kalian kelihatan cupu dibanding webnya:

> * Di QGIS, suruh teman-temanmu ganti warna *Background* kanvas dan *Print Layout* jadi biru gelap/hitam (\#050b14).  
> * Di pengaturan *Layer Styling* QGIS, ubah *Blending Mode* layer poligon dan garis solusi dari Normal menjadi **Screen atau Addition**\! Fitur bawaan QGIS ini otomatis bikin garis jalan, heksagon, dan titik solusi saling bertumpuk cahayanya persis efek hologram tanpa perlu aplikasi desain tambahan.

Gimana, konsep **Hologram Taktis J.A.R.V.I.S.** pakai kombinasi *MapLibre \+ Deck.gl \+ CSS HUD* ini jauh lebih masuk akal untuk dikoding sendiri tapi efek visualnya persis yang kau bayangkan, kan? Mau aku tuliskan *starter code* HTML satu file yang langsung nampilin gedung 3D hologram biru transparan yang muter otomatis di atas peta hitam Kota Medan biar kau bisa langsung jajal sekarang?

---

*User prompt: Aku ga mau nyuruh mereka buat hal yang rumit aku cmn suruh mrk yg diawal sblm kubilang minta 3d aku sendiri yg mau buat soalnya wkwkk trs emg 3d nya ketinggian bangunannya sesuai? kayak ketinggian jalan dll?*

Response: Masuk akal dan itu langkah paling pinter. Kalau kau nyuruh 4 temanmu yang belum tentu paham data 3D buat ngatur tinggi bangunan atau bikin *grid* rumit, ujung-ujungnya kau juga yang bakal begadang benerin file .geojson mereka satu-satu.

Biarkan mereka berempat kerja 2D standar di QGIS sesuai skema awal (bikin peta masalah \+ layer solusi masing-masing, simpan .qgz, cetak .png, lalu setor .geojson datar ke kau). Urusan "menyulap" peta itu jadi hologram 3D ala J.A.R.V.I.S., murni kau yang pegang di kodingan web dan di data bagianmu sendiri.

Menjawab pertanyaanmu soal **apakah tinggi bangunan dan jalannya bakal sesuai aslinya**: **Tidak 100% otomatis akurat kalau di Medan, tapi ada triknya biar kelihatan sangat realistis.** Ini fakta teknisnya biar kau gak ketipu ekspektasi:

**1\. Fakta Data Tinggi Bangunan di Medan (OpenStreetMap)**

> * **Kondisi Asli Data OSM Medan:** Gedung-gedung besar (kayak Podomoro, Sun Plaza, Cambridge, RS Adam Malik, atau gedung rektorat USU) biasanya udah punya atribut building:levels (jumlah lantai) atau height (tinggi meter) di database OSM. Tapi untuk rumah warga, kos-kosan, atau ruko biasa di Medan, 80% datanya di OSM itu **cuma poligon datar tanpa angka tinggi** (null).  
> * **Trik Akalin di Kode Web / QGIS Kau (Smart Fallback):** Biar gedung yang datanya kosong gak rata sama tanah pas diangkat jadi 3D, kau pasang rumus *fallback* otomatis di kode MapLibre-mu (atau di *Field Calculator* QGIS):  
  * Kalau ada data height asli → pakai angka aslinya.  
  * Kalau cuma ada building:levels (jumlah lantai) → kalikan 4 meter per lantai.  
  * Kalau kosong melompong (null), baca tipe bangunannya (building tag): kalau apartments / commercial / hotel kasih tinggi 25–40 meter, kalau retail / shophouse (ruko) kasih 12 meter, kalau yes / house (rumah biasa) kasih tinggi acak antara 5 sampai 8 meter.  
> * Hasilnya? Begitu dirender jadi hologram *cyan* transparan, siluet kota Medan tetap kelihatan hidup banget—gedung mal dan hotel menjulang tinggi, ruko sedang, dan perumahan warga pendek-pendek di bawahnya.

**2\. Gimana dengan Ketinggian Jalan, Flyover, dan Kontur Tanah?**

> * **Ketinggian Jalan & Flyover (Jembatan Layang):** Secara *default*, jalan raya dari OSM itu dirender menempel mengikuti permukaan tanah (2D). Kalau di OSM jalan itu punya tag bridge=yes dan layer=1 (kayak Flyover Jamin Ginting atau Flyover Amplas), di MapLibre jalan itu sebenarnya tetap digambar menempel di kanvas dasar, bukan melayang punya tiang beton 3D. Tapi karena kita pakai gaya **Hologram Iron Man**, jalan raya itu kita render sebagai **garis laser neon bercahaya** yang menembus di sela-sela balok gedung, jadi secara visual udah kelihatan keren banget tanpa perlu bikin struktur beton *flyover*.  
> * **Kontur Permukaan Tanah (DEM Terrain 3D):** Kalau kau tanya apakah tanah Kota Medan bisa dibuat naik-turun mengikuti bukit/lembah asli (misal dari daerah bawah Medan Kota naik ke arah Padang Bulan/Pancur Batu)? **Bisa banget\!** MapLibre punya fitur map.setTerrain() yang mengambil data satelit ketinggian tanah global (AWS Terrain Tiles / MapTiler Terrain) secara gratis. Jadi permukaan tanah petamu beneran bergelombang 3D, sungai berada di cekungan rendah, dan gedung-gedung 3D berdiri mengikuti kemiringan tanah tersebut.

**Alur Kerja Paling Santai Buat Tim (Temanmu Gampang, Web Kau Tetap Mewah)**

> 1. **4 Temanmu (Kerja 2D Biasa di QGIS):** Suruh mereka kerjakan Opsi 2 versi awal yang datar-datar aja (Orang 1: Suhu Panas LST, Orang 2: Krisis RTH/NDVI, Orang 3: Banjir Sungai & Posko Evakuasi, Orang 4: Jangkauan Damkar & Hidran). Mereka gak perlu tahu-menahu soal 3D, cukup kumpul .qgz, .png, dan kasih file .geojson 2D mereka ke kau.  
> 2. **Kau di WebGIS (Sang Pesulap 3D):**  
   * Kau masukkan 1 layer bangunan Kota Medan (.geojson atau Vector Tiles bawaan MapLibre) yang langsung kau angkat jadi **rangka gedung 3D hologram biru transparan** di seluruh peta.  
   * Saat aslab menyalakan *checkbox* punya temanmu (misal layer Rawan Banjir atau Suhu Panas), poligon 2D buatan temanmu bakal menyala kayak karpet neon hologram di bawah kaki gedung-gedung 3D buatanmu, sementara titik solusi mereka (Posko Evakuasi, Hidran, PJU) kau beri efek ikon/pilar bercahaya di antara gedung-gedung itu.

Dengan cara ini, temanmu gak bakal ngeluh tugasnya kerumitan, semua syarat dokumen fisik/digital dari dosen terpenuhi, dan kau bisa bebas pamer *skill* UI/UX 3D hologram tanpa diganggu kerjaan mereka. Mau aku kasih lihat kode HTML+JS MapLibre (cuma sekitar 60 baris) yang langsung narik gedung 3D otomatis di koordinat Kota Medan tanpa kau perlu unduh data gedung manual di QGIS?

---

