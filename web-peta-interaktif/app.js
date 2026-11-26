/* ==========================================================================
   Peta 3D Ketahanan Kota Medan — Integrasi 5 Fitur Analisis & Simulasi Bertahap
   Stack: MapLibre GL JS v5 + Three.js r169 (10 Model GLB 3D) + Anime.js v4
   Fitur Baru:
   - Basemap Google Maps / Hybrid / Terrain (Bebas API Key Required & Bebas Map Data Not Available)
   - 3 Tahapan Simulasi Solusi: (1) Kondisi Sekarang -> (2) Munculkan Titik Solusi Satu-Satu -> (3) Hasil & Rumus
   - Sub-Layer Terpisah per Fitur + Raster Citra Satelit Asli (VIIRS 2024, Sentinel-2 20m, DEM SRTM 30m)
   ========================================================================== */

(function () {
  "use strict";

  const PAL = {
    ink: "#071B2B",
    teal: "#167D8D",
    ice: "#B9E4E8",
    paper: "#EEEEEE",
    white: "#FFFFFF",
    lamp: "#FFC94D",
    waterDeep: "#0369A1",
    waterMid: "#0284C7",
    waterFoam: "#38BDF8",
    fireRed: "#DC2626",
    greenBright: "#22C55E",
    greenDark: "#15803D",
  };

  const DATA_SOURCES = {
    orang1: "Citra Satelit Termal Landsat 8/9 OLI/TIRS (USGS EarthExplorer) & Jaringan Jalan Arteri OpenStreetMap",
    orang2: "Citra Satelit Copernicus Sentinel-2 L2A Band 4 (Red) & Band 8 (NIR) Resolusi 20m (ESA) & Peta RTH Kota Medan",
    orang3: "Data Banjir Visel (forestearth.id 28-29 Okt 2026), 59 Rumah Sakit OpenStreetMap, Topografi DEM SRTM 30m USGS/BIG & BPBD Medan",
    orang4: "OpenRouteService (ORS) Isochrone Driving-Car API, Data Pos Dinas P2K (Damkar) Kota Medan, 31 Pasar & Gedung OpenStreetMap",
    orang5: "Citra Satelit Malam Suomi-NPP VIIRS V2.1 Tahun 2024 (EOG / OpenGeoHub), Rilis Jalan Rawan KRYD Polrestabes Medan & OpenStreetMap",
    gabungan: "Integrasi Multi-Satelit (Landsat 8/9, Sentinel-2, DEM SRTM 30m, Suomi-NPP VIIRS 2024), ORS Isochrone, OpenStreetMap & Batas RBI 50K BIG",
  };

  const TOPIC_NAMES = {
    orang1: "Suhu Panas & Pohon Peneduh (William)",
    orang2: "Kerapatan Pohon & Taman Hijau (Jordan)",
    orang3: "Luapan Banjir Sungai, RS Rujukan & Evakuasi (Visel)",
    orang4: "Jangkauan Pemadam Kebakaran & Hidran (Peter)",
    orang5: "Jalan Gelap Rawan Begal & Lampu PJU (Michael)",
    gabungan: "Mode Gabungan Bebas (Semua Fitur)",
  };

  const PRESETS = {
    "overview-medan": { center: [98.672, 3.605], zoom: 11.4, pitch: 48, bearing: -8 },
    "focus-pusat": { center: [98.6745, 3.5915], zoom: 14.3, pitch: 62, bearing: -16 },
    "focus-medan-baru": { center: [98.6598, 3.5715], zoom: 14.8, pitch: 62, bearing: -24 },
    "focus-utara": { center: [98.683, 3.745], zoom: 13.0, pitch: 56, bearing: 12 },
    "focus-selatan": { center: [98.632, 3.518], zoom: 13.4, pitch: 58, bearing: -14 },
    "globe-3d": { center: [98.668, 3.615], zoom: 2.0, pitch: 0, bearing: 0 },
  };

  const state = {
    activeSimTab: "orang5", // orang1 | orang2 | orang3 | orang4 | orang5 | gabungan
    simStage: 1,            // 1 = Kondisi Sekarang, 2 = Titik Solusi Satu per Satu, 3 = Hasil & Rumus Solusi
    solutionStepLimit: 99999,
    solutionTotalCount: 217,

    simulationActive: false,       // Michael Stage 3 outcome
    simUhiActive: false,           // William Stage 3 outcome
    simRthActive: false,           // Jordan Stage 3 outcome
    simFloodSolutionActive: false, // Visel Stage 3 outcome (-1.5m water reduction)
    simDamkarActive: false,        // Peter Stage 3 outcome

    uhiMinTemp: 28.0,
    jordanColorMode: "ndvi", // ndvi | uhi
    ndviMinFilter: -0.20,
    floodStageM: 0.0,        // 0.0 .. 5.0 meters
    damkarMinBld: 0,

    hexMode: "flat",
    basemap: "tematik",
    satSubmode: "night",
    dataOpacity: 0.90,
    autoOrbit: false,
    terrain3D: false,
    currentProj: "mercator",
    filterKec: "ALL",
    filterRisk: "ALL",
    layers: {
      buildings: true,
      hex: true,
      models3d: true,
      nightMask: false,
      rawViirs: false,
      rawNdvi: false,
      rawDem: false,
      water: false,
      kec: true,
    },
    teamLayers: {
      orang1: false,
      orang2: false,
      orang3: false,
      orang4: false,
      orang5: true,
    },
    // Separable sub-layers per feature
    subLayers: {
      o1_hex: true,
      o1_jalur: true,
      o1_halte: true,
      o1_sat: false,

      o2_hex: true,
      o2_taman: true,
      o2_sat: false,

      o3_titik: true,
      o3_rs: true,
      o3_air: true,
      o3_solusi: true,
      o3_rute: true,
      o3_hex: false,
      o3_sat: false,

      o4_hex: true,
      o4_iso: true,
      o4_eks: true,
      o4_sol: true,

      o5_hex: true,
      o5_koridor: true,
      o5_polisi: true,
      o5_pju: true,
      o5_patroli: true,
      o5_sat: false,
    },
  };

  let rawData = null;
  let teamData = null;
  let map = null;
  let orbitFrameId = null;
  let threeLayerApi = null;
  let hexViirsP90 = 52.0;
  let floodTween = null;
  let stepAnimTimer = null;
  const kpiPrevVals = { k1: 0, k2: 0, k3: 0, k4: 0 };

  window.__threeLayerReady = false;
  window.__modelsLoaded = 0;
  window.__modelInstances = 0;

  function initIcons() {
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  function getEffectiveFloodStage() {
    if (state.floodStageM <= 0.05) return 0.0;
    if (state.simFloodSolutionActive) {
      return Math.max(0.3, state.floodStageM - 1.5);
    }
    return state.floodStageM;
  }

  function animateKpiText(elId, targetNum, suffix = "", decimals = 0) {
    const el = document.getElementById(elId);
    if (!el) return;
    const key = elId;
    const startVal = Number.isFinite(kpiPrevVals[key]) ? kpiPrevVals[key] : 0;
    kpiPrevVals[key] = targetNum;

    const formatVal = (v) => {
      if (decimals > 0) return v.toFixed(decimals) + suffix;
      return Math.round(v).toLocaleString("id-ID") + suffix;
    };

    if (window.anime && typeof window.anime.animate === "function") {
      const obj = { val: startVal };
      window.anime.animate(obj, {
        val: targetNum,
        duration: 550,
        ease: "outExpo",
        onUpdate: () => {
          el.textContent = formatVal(obj.val);
        },
      });
    } else {
      el.textContent = formatVal(targetNum);
    }
  }

  function pulseElement(selector) {
    if (window.anime && typeof window.anime.animate === "function") {
      const el = typeof selector === "string" ? document.querySelector(selector) : selector;
      if (!el) return;
      window.anime.animate(el, {
        scale: [0.98, 1.0],
        opacity: [0.85, 1.0],
        duration: 320,
        ease: "outQuad",
      });
    }
  }

  async function loadAllGeoJSON() {
    if (window.MEDAN_SPATIAL_DATA) {
      rawData = window.MEDAN_SPATIAL_DATA;
    } else {
      const keys = [
        "batas_kecamatan_medan",
        "hex_viirs_medan_500m",
        "bangunan_fokus_3d",
        "koridor_rawan_begal",
        "solusi_pju_cctv",
        "solusi_rute_patroli",
        "polisi_eksisting",
        "sungai_fokus_osm",
      ];
      const entries = await Promise.all(
        keys.map(async (k) => {
          const res = await fetch(`./data/${k}.geojson`);
          return [k, await res.json()];
        })
      );
      rawData = Object.fromEntries(entries);
    }

    if (window.MEDAN_TEAM_LAYERS) {
      teamData = window.MEDAN_TEAM_LAYERS;
    } else {
      teamData = {
        orang1_masalah: { type: "FeatureCollection", features: [] },
        orang1_solusi: { type: "FeatureCollection", features: [] },
        orang2_masalah: { type: "FeatureCollection", features: [] },
        orang2_solusi: { type: "FeatureCollection", features: [] },
        orang3_masalah: { type: "FeatureCollection", features: [] },
        orang3_solusi: { type: "FeatureCollection", features: [] },
        orang3_kontur_banjir: { type: "FeatureCollection", features: [] },
        orang4_masalah: { type: "FeatureCollection", features: [] },
        orang4_solusi: { type: "FeatureCollection", features: [] },
        orang4_isochrone: { type: "FeatureCollection", features: [] },
      };
    }

    const viirsArr = rawData.hex_viirs_medan_500m.features
      .map((f) => Number(f.properties.viirs_mean || 0))
      .sort((a, b) => a - b);
    if (viirsArr.length > 0) {
      hexViirsP90 = viirsArr[Math.floor(viirsArr.length * 0.9)] || 52.0;
    }
  }

  function buildCirclePolygon(lon, lat, radiusM, steps = 28) {
    const coords = [];
    const latRad = (lat * Math.PI) / 180;
    const dLat = radiusM / 110540;
    const dLon = radiusM / (111320 * Math.cos(latRad));
    for (let i = 0; i <= steps; i++) {
      const a = (i / steps) * 2 * Math.PI;
      coords.push([lon + dLon * Math.cos(a), lat + dLat * Math.sin(a)]);
    }
    return [coords];
  }

  function getFilteredPjuFC() {
    if (!rawData || !rawData.solusi_pju_cctv) return { type: "FeatureCollection", features: [] };
    if (state.activeSimTab === "orang5" && state.simStage === 1) {
      return { type: "FeatureCollection", features: [] };
    }
    const maxStep = state.activeSimTab === "orang5" ? state.solutionStepLimit : 99999;
    const feats = rawData.solusi_pju_cctv.features.filter((f, idx) => {
      const p = f.properties || {};
      if (state.filterKec !== "ALL" && p.kecamatan && p.kecamatan !== state.filterKec) return false;
      const ord = Number(p.step_order || idx + 1);
      return ord <= maxStep;
    });
    return { type: "FeatureCollection", features: feats };
  }

  function buildPjuDiscsSource() {
    const pjuFc = getFilteredPjuFC();
    return {
      type: "FeatureCollection",
      features: pjuFc.features.map((f) => {
        const [lon, lat] = f.geometry.coordinates;
        const rad = Number(f.properties.radius_terang_m || 180);
        return {
          type: "Feature",
          properties: { ...f.properties },
          geometry: { type: "Polygon", coordinates: buildCirclePolygon(lon, lat, rad, 24) },
        };
      }),
    };
  }

  function populateFilters() {
    const kecSelect = document.getElementById("filter-kecamatan");
    if (!kecSelect) return;
    const kecList = rawData.batas_kecamatan_medan.features
      .map((f) => f.properties.nama_kec)
      .sort((a, b) => a.localeCompare(b));
    kecList.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      kecSelect.appendChild(opt);
    });
  }

  function renderKecamatanChart() {
    const container = document.getElementById("kec-chart");
    const titleEl = document.getElementById("chart-sec-title");
    if (!container || !titleEl) return;
    let rowsData = [];

    if (state.activeSimTab === "orang1" && teamData.orang1_masalah) {
      titleEl.textContent = "6 Kecamatan Suhu Terpanas (William)";
      const byKec = {};
      teamData.orang1_masalah.features.forEach((f) => {
        const k = f.properties.kecamatan || "Kota Medan";
        const val = state.simUhiActive ? Number(f.properties.lst_sim) : Number(f.properties.lst_mean);
        if (!byKec[k]) byKec[k] = [];
        byKec[k].push(val);
      });
      rowsData = Object.entries(byKec)
        .map(([k, arr]) => ({ name: k, val: arr.reduce((a, b) => a + b, 0) / arr.length, suffix: "°C", max: 39.0 }))
        .sort((a, b) => b.val - a.val)
        .slice(0, 6);
    } else if (state.activeSimTab === "orang2" && teamData.orang2_masalah) {
      titleEl.textContent = "6 Kecamatan Paling Minim Pohon (Jordan)";
      const byKec = {};
      teamData.orang2_masalah.features.forEach((f) => {
        const v = state.simRthActive ? f.properties.ndvi_sim : f.properties.ndvi_mean;
        if (v === null || v === undefined) return;
        const k = f.properties.kecamatan || "Kota Medan";
        if (!byKec[k]) byKec[k] = [];
        byKec[k].push(Number(v));
      });
      rowsData = Object.entries(byKec)
        .map(([k, arr]) => ({ name: k, val: arr.reduce((a, b) => a + b, 0) / arr.length, suffix: "", max: 0.5, decimals: 3 }))
        .sort((a, b) => a.val - b.val)
        .slice(0, 6);
    } else if (state.activeSimTab === "orang3") {
      titleEl.textContent = "6 Kecamatan Rawan Banjir & Evakuasi (Visel)";
      const byKec = {};
      const st = Math.max(1.5, getEffectiveFloodStage() || 2.5);
      rawData.bangunan_fokus_3d.features.forEach((f) => {
        if (Number(f.properties.flood_crit_m || 99) <= st) {
          const k = f.properties.kecamatan || "Kota Medan";
          byKec[k] = (byKec[k] || 0) + 1;
        }
      });
      rowsData = Object.entries(byKec)
        .map(([k, cnt]) => ({ name: k, val: cnt, suffix: " gedung", max: 3500, decimals: 0 }))
        .sort((a, b) => b.val - a.val)
        .slice(0, 6);
    } else if (state.activeSimTab === "orang4" && teamData.orang4_masalah) {
      titleEl.textContent = "6 Kecamatan Terlambat Dijangkau Damkar (Peter)";
      const byKec = {};
      teamData.orang4_masalah.features.forEach((f) => {
        if (state.simDamkarActive && f.properties.tercakup_simulasi === 1) return;
        const k = f.properties.kecamatan || "Kota Medan";
        byKec[k] = (byKec[k] || 0) + Number(f.properties.jml_bangunan || 0);
      });
      rowsData = Object.entries(byKec)
        .map(([k, cnt]) => ({ name: k, val: cnt, suffix: "", max: 35000, decimals: 0 }))
        .sort((a, b) => b.val - a.val)
        .slice(0, 6);
    } else {
      titleEl.textContent = "6 Kecamatan Jalan Gelap Tertinggi (Michael)";
      rowsData = [...rawData.batas_kecamatan_medan.features]
        .sort((a, b) => (b.properties.avg_risk_score || 0) - (a.properties.avg_risk_score || 0))
        .slice(0, 6)
        .map((f) => ({
          name: f.properties.nama_kec,
          val: Number(f.properties.avg_risk_score || 0),
          suffix: "",
          max: 100,
          decimals: 1,
        }));
    }

    container.innerHTML = rowsData
      .map((r) => {
        const dec = r.decimals !== undefined ? r.decimals : 1;
        const txt = dec === 0 ? Math.round(r.val).toLocaleString("id-ID") : r.val.toFixed(dec);
        const pct = Math.max(8, Math.min(100, (r.val / Math.max(r.max, 0.01)) * 100));
        return `
          <div class="bar-row" data-kec="${r.name.split(" / ")[0]}" style="cursor:pointer" title="Klik untuk fokus ke ${r.name}">
            <div class="bar-name">${r.name}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
            <div class="bar-val">${txt}${r.suffix}</div>
          </div>
        `;
      })
      .join("");

    container.querySelectorAll(".bar-row").forEach((row) => {
      row.addEventListener("click", () => {
        const kname = row.getAttribute("data-kec");
        const sel = document.getElementById("filter-kecamatan");
        if (sel && [...sel.options].some((o) => o.value === kname)) {
          sel.value = kname;
          state.filterKec = kname;
          flyToKecamatan(kname);
          applyFiltersAndRedraw();
        }
      });
    });
  }

  function updateDynamicLegend() {
    const dyn = document.getElementById("legend-dynamic-content");
    if (!dyn) return;

    if (state.activeSimTab === "orang1") {
      dyn.innerHTML = `
        <div class="legend-sec-title">Suhu Panas &amp; Pohon Peneduh (William)</div>
        <div class="viirs-scale-bar" style="background:linear-gradient(90deg, #2b83ba 0%, #abdda4 35%, #fdae61 68%, #d7191c 100%)"></div>
        <div class="viirs-scale-ticks">
          <span>Biru: &lt;30,5&deg;C Sejuk</span>
          <span>Hijau/Oranye: 30,5–34,5&deg;C</span>
          <span>Merah: &gt;34,5&deg;C Panas</span>
        </div>
        <div class="legend-easy-list">
          <div class="legend-item-row"><span class="legend-swatch" style="background:#d7191c"></span><span>Petak Merah (&gt;34,5&deg;C): Kawasan Sangat Panas (Hotspot Aspal/Atap)</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#fdae61"></span><span>Petak Oranye (32,5–34,5&deg;C): Kawasan Panas Sedang–Tinggi</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#abdda4"></span><span>Petak Hijau Muda (30,5–32,5&deg;C): Kawasan Hangat Normal</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#2b83ba"></span><span>Petak Biru (&lt;30,5&deg;C): Kawasan Sejuk / Dekat Pepohonan</span></div>
          <div class="legend-item-row"><span class="legend-swatch-line" style="background:#10b981"></span><span>Garis Hijau Putus-Putus: 6 Koridor Jalan Raya Pohon Peneduh (2.988 Pohon)</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#06b6d4"></span><span>Titik Biru Muda &amp; Halte 3D: 10 Halte Bus Beratap Sejuk (Cool Roof)</span></div>
          <div class="legend-item-row"><span class="legend-swatch-line" style="background:#071B2B"></span><span>Garis Putus-Putus Hitam Tipis: Batas 21 Kecamatan Kota Medan</span></div>
        </div>
        <div class="legend-source-note"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang1}</div>`;
    } else if (state.activeSimTab === "orang2") {
      dyn.innerHTML = `
        <div class="legend-sec-title">Kerapatan Pohon &amp; Taman Hijau (Jordan)</div>
        <div class="viirs-scale-bar" style="background:linear-gradient(90deg, #d73027 0%, #fc8d59 32%, #fee08b 62%, #1a9850 100%)"></div>
        <div class="viirs-scale-ticks">
          <span>Merah: Sangat Gersang</span>
          <span>Kuning: Sedang</span>
          <span>Hijau: Rimbun / Banyak Pohon</span>
        </div>
        <div class="legend-easy-list">
          <div class="legend-item-row"><span class="legend-swatch" style="background:#d73027"></span><span>Petak Merah / Oranye (NDVI &le; 0,111): Kawasan Sangat Gersang Minim Pohon</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#fee08b"></span><span>Petak Kuning (0,111–0,236): Kawasan Tutupan Pohon Sedang</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#1a9850"></span><span>Petak Hijau Tua (&gt; 0,236): Kawasan Pepohonan Rimbun / Rapat</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#22c55e"></span><span>Titik Bulat Hijau Terang &amp; Pohon 3D: 52 Lokasi Taman Saku Hijau Baru</span></div>
          <div class="legend-item-row"><span class="legend-swatch-line" style="background:#071B2B"></span><span>Garis Putus-Putus Hitam Tipis: Batas 21 Kecamatan Kota Medan</span></div>
        </div>
        <div class="legend-source-note"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang2}</div>`;
    } else if (state.activeSimTab === "orang3") {
      dyn.innerHTML = `
        <div class="legend-sec-title">Luapan Banjir Sungai, RS Rujukan &amp; Evakuasi (Visel)</div>
        <div class="viirs-scale-bar" style="background:linear-gradient(90deg, #bae6fd 0%, #38bdf8 35%, #0284c7 70%, #0369a1 100%)"></div>
        <div class="viirs-scale-ticks">
          <span>Biru Muda: Genangan Tepian</span>
          <span>Biru Sedang: Lembah Sungai</span>
          <span>Biru Tua: Banjir Dalam</span>
        </div>
        <div class="legend-easy-list">
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#3182bd"></span><span>Lingkaran Biru Tua (Ukuran = Kedalaman): 13 Titik Banjir Resmi (Visel &amp; BPBD)</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#ff7f00"></span><span>Titik Bulat Oranye &amp; RS 3D: Rumah Sakit di Kecamatan Terdampak Banjir (Visel)</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#e31a1c"></span><span>Titik Bulat Merah &amp; RS 3D: Rumah Sakit Rujukan di Zona Aman Banjir (Visel)</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#10b981"></span><span>Titik Bulat Hijau Toska &amp; Tenda 3D: 25 Posko Evakuasi Tanah Tinggi</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#0ea5e9"></span><span>Kotak Biru Muda: 14 Kolam Retensi &amp; Rumah Pompa Pengendali Banjir (-1,5m)</span></div>
          <div class="legend-item-row"><span class="legend-swatch-line" style="background:#f97316;border:1.5px dashed #071B2B"></span><span>Garis Putus-Putus Oranye: 13 Rute Jalan Raya Evakuasi dari Titik Banjir ke RS &amp; Posko</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#0284c7"></span><span>Air Biru 3D &amp; Gedung Biru: Luapan Air Sungai DEM SRTM &amp; Gedung Terendam</span></div>
          <div class="legend-item-row"><span class="legend-swatch-line" style="background:#0284c7"></span><span>Garis Biru Berkelok: Alur Sungai Deli, Babura, Sikambing &amp; Sei Putih</span></div>
        </div>
        <div class="legend-source-note"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang3}</div>`;
    } else if (state.activeSimTab === "orang4") {
      dyn.innerHTML = `
        <div class="legend-sec-title">Jangkauan Pemadam Kebakaran &amp; Hidran (Peter)</div>
        <div class="viirs-scale-bar" style="background:linear-gradient(90deg, #fed7aa 0%, #fb7050 45%, #d32020 75%, #67000d 100%)"></div>
        <div class="viirs-scale-ticks">
          <span>Oranye Muda: Sedikit Rumah</span>
          <span>Merah Tua: Padat &amp; Terlambat &gt;10 Menit</span>
        </div>
        <div class="legend-easy-list">
          <div class="legend-item-row"><span class="legend-swatch" style="background:#22c55e"></span><span>Area Hijau Muda &amp; Tua: Wilayah Terjangkau Mobil Pemadam &le;5 &amp; &le;10 Menit</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#d32020"></span><span>Petak Oranye / Merah: Wilayah Terlambat &gt;10 Menit (Blindspot Damkar)</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#991b1b"></span><span>Titik Bulat Merah Tua &amp; Pos 3D: 2 Pos Pemadam Kebakaran Eksisting</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#dc2626"></span><span>Titik Bulat Merah Terang &amp; Pos 3D: 16 Usulan Pos Pemadam Baru</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#3b82f6"></span><span>Titik Bulat Biru &amp; Hidran 3D: 11 Hidran Air Darurat</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#eab308"></span><span>Titik Bulat Kuning: 31 Lokasi Pasar Tradisional Rawan Kebakaran</span></div>
          <div class="legend-item-row"><span class="legend-swatch-line" style="background:#071B2B"></span><span>Garis Putus-Putus Hitam Tipis: Batas 21 Kecamatan Kota Medan</span></div>
        </div>
        <div class="legend-source-note"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang4}</div>`;
    } else if (state.activeSimTab === "gabungan") {
      dyn.innerHTML = `
        <div class="legend-sec-title">Mode Gabungan Bebas (Semua Fitur 21 Kecamatan)</div>
        <div class="legend-easy-list">
          <div class="legend-item-row"><span class="legend-swatch" style="background:#d7191c"></span><span>Suhu Panas &amp; Pohon Peneduh (William) — Landsat 8/9 TIRS</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#1a9850"></span><span>Kerapatan Pohon &amp; Taman Hijau (Jordan) — Sentinel-2 L2A</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#0284c7"></span><span>Luapan Banjir Sungai &amp; RS Rujukan (Visel) — forestearth.id &amp; DEM</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#dc2626"></span><span>Jangkauan Pemadam &amp; Hidran (Peter) — ORS Isochrone</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#FFC94D"></span><span>Jalan Gelap &amp; Lampu PJU Pintar (Michael) — VIIRS 2024</span></div>
        </div>
        <div class="legend-source-note"><strong>Sumber Data:</strong> ${DATA_SOURCES.gabungan}</div>`;
    } else {
      dyn.innerHTML = `
        <div class="legend-sec-title">Jalan Gelap Rawan Begal &amp; Lampu PJU (Michael)</div>
        <div class="viirs-scale-bar"></div>
        <div class="viirs-scale-ticks">
          <span>Biru Gelap: Gelap Gulita (Rawan)</span>
          <span>Toska: Redup</span>
          <span>Kuning: Terang Benderang</span>
        </div>
        <div class="legend-easy-list">
          <div class="legend-item-row"><span class="legend-swatch" style="background:#071B2B"></span><span>Petak &amp; Gedung Biru Gelap: Area Gelap Rawan Kejahatan Malam (VIIRS &lt;25 DN)</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#167D8D"></span><span>Petak &amp; Gedung Biru Toska: Area Cahaya Redup / Sedang (25–50 DN)</span></div>
          <div class="legend-item-row"><span class="legend-swatch" style="background:#B9E4E8"></span><span>Petak &amp; Gedung Biru Muda: Area Terang / Sudah Diterangi Lampu PJU</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#FFC94D"></span><span>Titik Bulat Kuning &amp; Tiang 3D: 217 Lampu PJU Pintar, CCTV &amp; Pos Pantau</span></div>
          <div class="legend-item-row"><span class="legend-swatch legend-swatch-circle" style="background:#167D8D"></span><span>Titik Bulat Toska Besar &amp; Pos 3D: 31 Kantor Polsek &amp; Pos Polisi Eksisting</span></div>
          <div class="legend-item-row"><span class="legend-swatch-line" style="background:#071B2B"></span><span>Garis Tebal Hitam-Putih: 24 Ruas Jalan Raya Rawan Begal Malam Hari</span></div>
          <div class="legend-item-row"><span class="legend-swatch-line" style="background:#167D8D"></span><span>Garis Putus-Putus Toska: 7 Rute Patroli Polisi Malam (196,9 km)</span></div>
        </div>
        <div class="legend-source-note"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang5}</div>`;
    }
  }

  function updateKPIs() {
    const buildings = rawData.bangunan_fokus_3d.features;
    const totalB = buildings.length;
    const darkCard = document.getElementById("kpi-dark-card");
    const l1 = document.getElementById("kpi-1-label");
    const s1 = document.getElementById("kpi-1-sub");
    const l2 = document.getElementById("kpi-dark-label");
    const s2 = document.getElementById("kpi-dark-sub");
    const l3 = document.getElementById("kpi-3-label");
    const s3 = document.getElementById("kpi-3-sub");
    const l4 = document.getElementById("kpi-4-label");
    const s4 = document.getElementById("kpi-4-sub");

    const simPjuCountEl = document.getElementById("sim-pju-count");
    if (simPjuCountEl) {
      simPjuCountEl.textContent = rawData.solusi_pju_cctv.features.length.toString();
    }

    if (state.activeSimTab === "orang1" && teamData.orang1_masalah) {
      const feats = teamData.orang1_masalah.features.filter(
        (f) => state.uhiMinTemp <= 28.05 || (state.simUhiActive ? f.properties.lst_sim : f.properties.lst_mean) >= state.uhiMinTemp
      );
      const hotspots = feats.filter(
        (f) => (state.simUhiActive ? f.properties.lst_sim : f.properties.lst_mean) >= 34.5
      );
      const avgLst =
        feats.reduce((acc, f) => acc + Number(state.simUhiActive ? f.properties.lst_sim : f.properties.lst_mean), 0) /
        Math.max(1, feats.length);

      l1.textContent = "CAKUPAN PETAK SUHU";
      animateKpiText("kpi-buildings", feats.length, " Petak", 0);
      s1.textContent = "21 Kecamatan (Landsat 8/9)";

      l2.textContent = state.simUhiActive ? "AREA PANAS TERSISA" : "AREA SANGAT PANAS";
      animateKpiText("kpi-dark-buildings", hotspots.length, " Petak", 0);
      s2.textContent = state.simUhiActive ? "Turun drastis berkat pohon" : "Suhu siang > 34,5 °C";
      darkCard.classList.toggle("kpi-ice", state.simUhiActive);
      darkCard.classList.toggle("kpi-dark-mode", !state.simUhiActive);

      l3.textContent = "SOLUSI PENEDUH 3D";
      const visSol = state.simStage === 1 ? 0 : Math.min(16, state.solutionStepLimit);
      animateKpiText("kpi-pju", visSol, " Titik/Jalur", 0);
      s3.textContent = "6 Jalur Pohon + 10 Halte 3D";

      l4.textContent = "SUHU RATA-RATA KOTA";
      animateKpiText("kpi-corridors", avgLst, " °C", 2);
      s4.textContent = state.simUhiActive ? "Lebih sejuk -3,1 °C" : "Suhu siang sebelum solusi";
    } else if (state.activeSimTab === "orang2" && teamData.orang2_masalah) {
      const feats = teamData.orang2_masalah.features;
      const deficit = feats.filter(
        (f) => Number(state.simRthActive ? f.properties.ndvi_sim : f.properties.ndvi_mean) <= 0.111
      );
      const avgNdvi =
        feats.reduce((acc, f) => acc + Number(state.simRthActive ? f.properties.ndvi_sim : f.properties.ndvi_mean), 0) /
        Math.max(1, feats.length);

      l1.textContent = "CAKUPAN PETAK POHON";
      animateKpiText("kpi-buildings", feats.length, " Petak", 0);
      s1.textContent = "21 Kecamatan (Sentinel-2)";

      l2.textContent = state.simRthActive ? "AREA GERSANG SISA" : "AREA SANGAT GERSANG";
      animateKpiText("kpi-dark-buildings", deficit.length, " Petak", 0);
      s2.textContent = "Tutupan pohon sangat rendah";
      darkCard.classList.toggle("kpi-ice", state.simRthActive);
      darkCard.classList.toggle("kpi-dark-mode", !state.simRthActive);

      l3.textContent = "TAMAN HIJAU BARU 3D";
      const visSol = state.simStage === 1 ? 0 : Math.min(teamData.orang2_solusi.features.length, state.solutionStepLimit);
      animateKpiText("kpi-pju", visSol, " Taman", 0);
      s3.textContent = "Tersebar di 21 Kecamatan";

      l4.textContent = "SKOR KEHIJAUAN KOTA";
      animateKpiText("kpi-corridors", avgNdvi, "", 3);
      s4.textContent = state.simRthActive ? "Meningkat pasca taman baru" : "Data Sentinel-2 (Jordan)";
    } else if (state.activeSimTab === "orang3") {
      const effSt = getEffectiveFloodStage();
      const floodedBlds = effSt <= 0.05 ? 0 : buildings.filter((f) => Number(f.properties.flood_crit_m || 99) <= effSt).length;
      let areaKm2 = 0.0;
      if (effSt > 0.05 && teamData.orang3_kontur_banjir) {
        const nearestStage = Math.max(0.5, Math.min(5.0, Math.round(effSt * 2) / 2));
        const cf = teamData.orang3_kontur_banjir.features.find((f) => Number(f.properties.stage_m) === nearestStage);
        if (cf) areaKm2 = Number(cf.properties.luas_genangan_km2 || 0);
      }

      l1.textContent = "TINGGI AIR SUNGAI";
      animateKpiText("kpi-buildings", effSt, " m", 1);
      s1.textContent = state.simFloodSolutionActive ? `Turun -1,5m dari +${state.floodStageM.toFixed(1)}m` : "Topografi DEM SRTM 30m";

      l2.textContent = "GEDUNG & TITIK BANJIR";
      animateKpiText("kpi-dark-buildings", floodedBlds, "", 0);
      s2.textContent = "13 Titik Banjir Resmi (Visel & BPBD)";
      darkCard.classList.toggle("kpi-ice", effSt <= 0.05 || state.simFloodSolutionActive);
      darkCard.classList.toggle("kpi-dark-mode", effSt > 0.05 && !state.simFloodSolutionActive);

      l3.textContent = "RS RUJUKAN & POSKO 3D";
      animateKpiText("kpi-pju", 84, " Unit", 0);
      s3.textContent = "59 RS Rujukan + 25 Posko + 14 Kolam";

      l4.textContent = "LUAS GENANGAN BANJIR";
      animateKpiText("kpi-corridors", areaKm2, " km²", 2);
      s4.textContent = state.simFloodSolutionActive ? "Surut berkat kolam retensi" : "88 Ruas Sungai (21 Kec.)";
    } else if (state.activeSimTab === "orang4" && teamData.orang4_masalah) {
      const allBs = teamData.orang4_masalah.features.filter((f) => Number(f.properties.jml_bangunan || 0) >= state.damkarMinBld);
      const activeBs = state.simDamkarActive ? allBs.filter((f) => f.properties.tercakup_simulasi !== 1) : allBs;
      const totalBldBlindspot = activeBs.reduce((acc, f) => acc + Number(f.properties.jml_bangunan || 0), 0);

      l1.textContent = "PETAK LAMBAT (>10 MNT)";
      animateKpiText("kpi-buildings", activeBs.length, " Petak", 0);
      s1.textContent = "21 Kecamatan (ORS Isochrone)";

      l2.textContent = state.simDamkarActive ? "RUMAH BELUM TERCAKUP" : "RUMAH RAWAN TERLAMBAT";
      animateKpiText("kpi-dark-buildings", totalBldBlindspot, "", 0);
      s2.textContent = state.simDamkarActive ? "96% Medan terjangkau <=10m" : "Waktu tempuh Damkar >10 mnt";
      darkCard.classList.toggle("kpi-ice", state.simDamkarActive);
      darkCard.classList.toggle("kpi-dark-mode", !state.simDamkarActive);

      l3.textContent = "POS DAMKAR & HIDRAN";
      const visSol = state.simStage === 1 ? 2 : Math.min(29, 2 + state.solutionStepLimit);
      animateKpiText("kpi-pju", visSol, " Unit", 0);
      s3.textContent = "2 Pos Lama + 16 Pos Baru + 11 Hidran";

      l4.textContent = "PASAR TRADISIONAL";
      animateKpiText("kpi-corridors", 31, " Pasar", 0);
      s4.textContent = state.simDamkarActive ? "31/31 Pasar Terlindungi" : "Titik Pasar Rawan Kebakaran";
    } else {
      const highDark = buildings.filter((f) => f.properties.status_rawan === "Tinggi");
      const stillDark = state.simulationActive
        ? highDark.filter((f) => f.properties.terlindungi_solusi !== 1)
        : highDark;
      const protectedCount = highDark.length - stillDark.length;

      l1.textContent = "GEDUNG 3D KOTA MEDAN";
      animateKpiText("kpi-buildings", totalB, "", 0);
      s1.textContent = "Cakupan Penuh 21 Kecamatan";

      l2.textContent = state.simulationActive ? "GEDUNG MASIH GELAP" : "GEDUNG AREA GELAP";
      animateKpiText("kpi-dark-buildings", stillDark.length, "", 0);
      s2.textContent = state.simulationActive
        ? `-${protectedCount.toLocaleString("id-ID")} gedung diterangi PJU`
        : `${highDark.length.toLocaleString("id-ID")} gedung rawan malam`;
      darkCard.classList.toggle("kpi-ice", state.simulationActive);
      darkCard.classList.toggle("kpi-dark-mode", !state.simulationActive);

      l3.textContent = "LAMPU PJU & CCTV 3D";
      const visPju = state.simStage === 1 ? 0 : Math.min(rawData.solusi_pju_cctv.features.length, state.solutionStepLimit);
      animateKpiText("kpi-pju", visPju, " Unit", 0);
      s3.textContent = "Radius cahaya 165–210m (21 Kec.)";

      l4.textContent = "JALAN RAWAN & PATROLI";
      animateKpiText("kpi-corridors", rawData.koridor_rawan_begal.features.length, " Ruas", 0);
      s4.textContent = "Data Polrestabes Medan & VIIRS";
    }

    renderKecamatanChart();
    updateDynamicLegend();
  }

  function lookupViirsAt(lon, lat) {
    const ov = window.MEDAN_RASTER_OVERLAYS && window.MEDAN_RASTER_OVERLAYS.viirs;
    if (!ov || !ov.matrix || !ov.gt) return null;
    const mat = ov.matrix;
    const h = mat.length;
    const w = mat[0].length;
    const gt = ov.gt;
    const col = Math.max(0, Math.min(w - 1, Math.floor((lon - gt[0]) / gt[1])));
    const row = Math.max(0, Math.min(h - 1, Math.floor((lat - gt[3]) / gt[5])));
    const extractPatch = (cr, cc) => {
      const out = [];
      for (let dr = -4; dr <= 4; dr++) {
        const line = [];
        for (let dc = -4; dc <= 4; dc++) {
          const rr = Math.max(0, Math.min(h - 1, cr + dr));
          const cc2 = Math.max(0, Math.min(w - 1, cc + dc));
          line.push(Number(mat[rr][cc2] || 0));
        }
        out.push(line);
      }
      return out;
    };
    const bCol = Math.max(0, Math.min(w - 1, Math.floor((98.678 - gt[0]) / gt[1])));
    const bRow = Math.max(0, Math.min(h - 1, Math.floor((3.591 - gt[3]) / gt[5])));
    return {
      centerVal: Number(mat[row][col] || 0),
      medanMax: Number(ov.medanMax || 105),
      localPatch: extractPatch(row, col),
      brightPatch: extractPatch(bRow, bCol),
      brightVal: Number(mat[bRow][bCol] || 95),
    };
  }

  function viirsToColorStr(dn) {
    if (dn >= 75) return PAL.lamp;
    if (dn >= 45) return PAL.ice;
    if (dn >= 24) return PAL.teal;
    return PAL.ink;
  }

  function drawInspectorSatProof(canvasEl, patch) {
    if (!canvasEl || !patch) return;
    const ctx = canvasEl.getContext("2d");
    const cw = canvasEl.width;
    const ch = canvasEl.height;
    ctx.fillStyle = PAL.ink;
    ctx.fillRect(0, 0, cw, ch);

    const drawGrid = (grid, ox, oy, size, titleText) => {
      const cell = size / 9;
      for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
          ctx.fillStyle = viirsToColorStr(grid[r][c]);
          ctx.fillRect(ox + c * cell, oy + r * cell, Math.ceil(cell), Math.ceil(cell));
        }
      }
      ctx.strokeStyle = PAL.lamp;
      ctx.lineWidth = 2;
      ctx.strokeRect(ox + 4 * cell, oy + 4 * cell, cell, cell);
      ctx.strokeStyle = PAL.white;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(ox, oy, size, size);

      ctx.fillStyle = PAL.white;
      ctx.font = "bold 9px Nunito, sans-serif";
      ctx.fillText(titleText, ox, oy - 3);
    };

    const gSize = 62;
    drawGrid(patch.localPatch, 10, 16, gSize, `LOKASI: ${patch.centerVal.toFixed(0)}`);
    drawGrid(patch.brightPatch, cw - gSize - 14, 16, gSize, `PUSAT: ${patch.brightVal.toFixed(0)}`);

    ctx.fillStyle = PAL.ice;
    ctx.font = "bold 9px Nunito, sans-serif";
    ctx.textAlign = "center";
    const pct = Math.max(0, Math.round((patch.centerVal / Math.max(patch.medanMax, 1)) * 100));
    ctx.fillText("VS", cw / 2, 36);
    ctx.fillStyle = PAL.lamp;
    ctx.font = "bold 11px Fredoka, sans-serif";
    ctx.fillText(`${pct}%`, cw / 2, 52);
    ctx.fillStyle = PAL.white;
    ctx.font = "700 8px Nunito, sans-serif";
    ctx.fillText("CAHAYA", cw / 2, 63);
    ctx.textAlign = "left";
  }

  function showInspector(typeLabel, badgeText, badgeClass, title, rows, formulaHtml = "", coords = null) {
    const box = document.getElementById("inspector-box");
    if (!box) return;
    const tableRows = rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");
    const formulaBlock = formulaHtml
      ? `<div class="insp-formula"><div class="insp-formula-title">Perhitungan Rumus &amp; Sumber Data</div>${formulaHtml}</div>`
      : "";

    let satPatch = null;
    let satProofBlock = "";
    if (state.activeSimTab === "orang5" && coords && Number.isFinite(coords[0]) && Number.isFinite(coords[1])) {
      satPatch = lookupViirsAt(coords[0], coords[1]);
      if (satPatch) {
        const deficit = Math.max(0, Math.round(100 - (satPatch.centerVal / Math.max(satPatch.medanMax, 1)) * 100));
        const verdict =
          satPatch.centerVal < 25
            ? `AREA GELAP SATELIT MALAM (${deficit}% lebih gelap dibanding pusat Kota Medan)`
            : satPatch.centerVal < 50
            ? `AREA REDUP SATELIT MALAM (cahaya ${100 - deficit}% dari pusat kota)`
            : `AREA TERANG SATELIT MALAM`;
        satProofBlock = `
          <div class="insp-sat-proof">
            <div class="insp-formula-title">Perbandingan Cahaya Satelit Malam (VIIRS 2024)</div>
            <canvas id="insp-sat-canvas" width="266" height="84"></canvas>
            <div class="insp-sat-caption">${verdict}</div>
          </div>`;
      }
    }

    const actionBlock =
      coords && Number.isFinite(coords[0]) && Number.isFinite(coords[1])
        ? `<div class="insp-actions">
            <button type="button" class="btn btn-xs btn-secondary" id="btn-insp-sat">Lihat Mode Malam</button>
            <button type="button" class="btn btn-xs btn-ghost" id="btn-insp-sat-day">Foto Satelit Siang</button>
            <a class="btn btn-xs btn-ghost insp-act-wide" target="_blank" rel="noopener noreferrer" href="https://www.google.com/maps/@?api=1&amp;map_action=pano&amp;viewpoint=${coords[1]},${coords[0]}">Buka Kondisi Asli di Google Street View</a>
          </div>`
        : "";

    box.innerHTML = `
      <div class="insp-head">
        <span class="insp-type">${typeLabel}</span>
        <span class="insp-badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="insp-title">${title}</div>
      <table class="insp-table">${tableRows}</table>
      ${satProofBlock}
      ${formulaBlock}
      ${actionBlock}
    `;

    pulseElement("#inspector-box");

    if (satPatch) {
      drawInspectorSatProof(document.getElementById("insp-sat-canvas"), satPatch);
    }

    const satBtn = document.getElementById("btn-insp-sat");
    if (satBtn && coords) {
      satBtn.addEventListener("click", () => {
        inspectOnRealSatellite(coords[0], coords[1], "night");
      });
    }
    const satDayBtn = document.getElementById("btn-insp-sat-day");
    if (satDayBtn && coords) {
      satDayBtn.addEventListener("click", () => {
        inspectOnRealSatellite(coords[0], coords[1], "day");
      });
    }
  }

  function inspectOnRealSatellite(lon, lat, submode = "night") {
    state.satSubmode = submode;
    if (map && map.getSource("src-sat-spotlight")) {
      map.getSource("src-sat-spotlight").setData({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            properties: { kind: "ring" },
            geometry: { type: "Polygon", coordinates: buildCirclePolygon(lon, lat, 130, 32) },
          },
          {
            type: "Feature",
            properties: { kind: "dot" },
            geometry: { type: "Point", coordinates: [lon, lat] },
          },
        ],
      });
    }
    setBasemap(submode === "day" ? "satelit-terang" : "satelit");
    setDataOpacity(0.45);
    if (map) {
      map.flyTo({ center: [lon, lat], zoom: 16.2, pitch: 52, bearing: -15, duration: 1000 });
    }
  }

  function getFilteredHexFC() {
    return {
      type: "FeatureCollection",
      features: rawData.hex_viirs_medan_500m.features.filter((f) => {
        const p = f.properties;
        const okKec = state.filterKec === "ALL" || p.kecamatan === state.filterKec;
        const okRisk = state.filterRisk === "ALL" || p.kelas_risiko === state.filterRisk;
        return okKec && okRisk;
      }),
    };
  }

  // Basemap style using Google Maps tiles (mt1.google.com) -> ZERO "API KEY REQUIRED", ZERO 403, ZERO "Map data not yet available" up to zoom 20!
  function buildLightBrutalStyle() {
    return {
      version: 8,
      name: "MedanTangguh Multi-Basemap 3D Anti-Error",
      sources: {
        "google-clean": {
          type: "raster",
          tiles: ["https://mt1.google.com/vt/lyrs=m&hl=id&x={x}&y={y}&z={z}"],
          tileSize: 256,
          maxzoom: 20,
          attribution: "&copy; Google Maps &amp; OpenStreetMap",
        },
        "google-streets": {
          type: "raster",
          tiles: ["https://mt1.google.com/vt/lyrs=m&hl=id&x={x}&y={y}&z={z}"],
          tileSize: 256,
          maxzoom: 20,
          attribution: "&copy; Google Maps",
        },
        "google-hybrid": {
          type: "raster",
          tiles: ["https://mt1.google.com/vt/lyrs=y&hl=id&x={x}&y={y}&z={z}"],
          tileSize: 256,
          maxzoom: 20,
          attribution: "&copy; Google Satellite &amp; Maxar",
        },
        "google-night": {
          type: "raster",
          tiles: ["https://mt1.google.com/vt/lyrs=s&hl=id&x={x}&y={y}&z={z}"],
          tileSize: 256,
          maxzoom: 20,
          attribution: "&copy; NASA Suomi-NPP VIIRS Night Satellite",
        },
        "nasa-gibs-night": {
          type: "raster",
          tiles: [
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_CityLights_2012/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg",
          ],
          tileSize: 256,
          maxzoom: 8,
          attribution: "NASA Earth Observatory Suomi-NPP VIIRS",
        },
        "google-terrain": {
          type: "raster",
          tiles: ["https://mt1.google.com/vt/lyrs=p&hl=id&x={x}&y={y}&z={z}"],
          tileSize: 256,
          maxzoom: 20,
          attribution: "&copy; Google Terrain &amp; Topografi",
        },
        "openfreemap-planet": {
          type: "vector",
          url: "https://tiles.openfreemap.org/planet",
        },
        "terrarium-dem": {
          type: "raster-dem",
          tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
          encoding: "terrarium",
          tileSize: 256,
          maxzoom: 12,
        },
        "terrarium-hillshade": {
          type: "raster-dem",
          tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
          encoding: "terrarium",
          tileSize: 256,
          maxzoom: 12,
        },
      },
      layers: [
        {
          id: "paper-background",
          type: "background",
          paint: { "background-color": PAL.paper },
        },
        {
          id: "basemap-light",
          type: "raster",
          source: "google-clean",
          paint: {
            "raster-saturation": -0.88,
            "raster-contrast": -0.06,
            "raster-brightness-min": 0.16,
          },
        },
        {
          id: "basemap-satelit",
          type: "raster",
          source: "google-hybrid",
          layout: { visibility: "none" },
        },
        {
          id: "basemap-nasa-night",
          type: "raster",
          source: "google-night",
          layout: { visibility: "none" },
          paint: {
            "raster-brightness-max": 0.14,
            "raster-saturation": -1.0,
            "raster-contrast": 0.45,
          },
        },
        {
          id: "basemap-gibs-night",
          type: "raster",
          source: "nasa-gibs-night",
          layout: { visibility: "none" },
          paint: {
            "raster-opacity": 0.72,
          },
        },
        {
          id: "basemap-topo",
          type: "raster",
          source: "google-terrain",
          layout: { visibility: "none" },
        },
        {
          id: "basemap-osm",
          type: "raster",
          source: "google-streets",
          layout: { visibility: "none" },
        },
        {
          id: "dem-hillshade",
          type: "hillshade",
          source: "terrarium-hillshade",
          layout: { visibility: "none" },
          paint: {
            "hillshade-shadow-color": PAL.ink,
            "hillshade-highlight-color": PAL.white,
            "hillshade-accent-color": PAL.ink,
            "hillshade-exaggeration": 0.45,
          },
        },
      ],
    };
  }

  function inspectBuilding(p, clickLngLat) {
    const effFlood = getEffectiveFloodStage();
    const isFlooded = effFlood > 0.05 && Number(p.flood_crit_m || 99) <= effFlood;
    const isRescuedFlood =
      state.simFloodSolutionActive &&
      state.floodStageM > 0.05 &&
      Number(p.flood_crit_m || 99) <= state.floodStageM &&
      Number(p.flood_crit_m || 99) > effFlood;
    const isProtectedPju = state.simulationActive && p.terlindungi_solusi === 1;
    const isProtectedDamkar = state.simDamkarActive && Number(p.damkar_sim_10m) === 1;

    let statusText = `Risiko Malam: ${p.status_rawan}`;
    let badgeCls = p.status_rawan === "Tinggi" ? "insp-badge-ink" : p.status_rawan === "Sedang" ? "insp-badge-teal" : "insp-badge-ice";
    if (isFlooded) {
      statusText = `TERENDAM BANJIR (+${effFlood.toFixed(1)}m)`;
      badgeCls = "insp-badge-ink";
    } else if (isRescuedFlood) {
      statusText = "BEBAS BANJIR (KOLAM RETENSI)";
      badgeCls = "insp-badge-ice";
    } else if (state.activeSimTab === "orang4") {
      statusText = isProtectedDamkar || Number(p.damkar_eks_10m) === 1 ? "TERJANGKAU DAMKAR <=10M" : "TERLAMBAT >10 MENIT";
      badgeCls = statusText.includes("TERLAMBAT") ? "insp-badge-ink" : "insp-badge-ice";
    } else if (isProtectedPju) {
      statusText = "DITERANGI LAMPU PJU 3D";
      badgeCls = "insp-badge-ice";
    }

    const fHtml =
      `<div><strong>1. Rumus Kerawanan Malam (Michael):</strong> Cahaya malam ${p.viirs_rad} DN · Lampu terdekat ${p.nearest_pju_id} (jarak ${p.dist_pju_m} m).</div>` +
      `<div><strong>2. Rumus Luapan Banjir (Visel):</strong> Elevasi tanah ${p.elev_m} mdpl (+${p.hand_m ?? "-"} m di atas sungai). Terendam jika air sungai naik <strong>+${p.flood_crit_m ?? "-"} m</strong>.</div>` +
      `<div><strong>3. Jangkauan Pemadam (Peter):</strong> Awal: ${Number(p.damkar_eks_10m) === 1 ? "Cepat (<=10 menit)" : "Terlambat (>10 menit)"} &rarr; Solusi: ${Number(p.damkar_sim_10m) === 1 ? "Terjangkau <=10 menit" : "Dilindungi Hidran Lokal"}.</div>` +
      `<div style="margin-top:4px;color:#167D8D"><strong>Sumber Data:</strong> ${p.sumber_data || DATA_SOURCES.gabungan}</div>`;

    const coords = [Number(p.lon || (clickLngLat && clickLngLat.lng)), Number(p.lat || (clickLngLat && clickLngLat.lat))];
    showInspector(
      "Gedung & Bangunan 3D (21 Kecamatan)",
      statusText,
      badgeCls,
      p.nama || `Bangunan #${p.osm_id}`,
      [
        ["Kecamatan", p.kecamatan],
        ["Jenis & Tinggi Gedung", `${p.building} · Tinggi ${p.height_m} meter`],
        ["Ketinggian Tanah", `${p.elev_m} mdpl (+${p.hand_m ?? "-"} m dari sungai)`],
        ["Mulai Terendam Banjir", `Jika air sungai naik +${p.flood_crit_m ?? "-"} meter`],
        ["Jangkauan Pemadam", `${Number(p.damkar_eks_10m) === 1 ? "Awal: <=10 Menit" : "Awal: >10 Menit"} -> Solusi: <=10 Menit`],
        ["Lampu PJU Terdekat", `${p.nearest_pju_id} (Jarak ${p.dist_pju_m} m)`],
      ],
      fHtml,
      coords
    );
  }

  function inspectCitywideBuilding(props, lngLat) {
    let hexProps = null;
    if (map) {
      const pt = map.project(lngLat);
      const hexHits = map.queryRenderedFeatures(pt, { layers: ["hex-flat-fill", "hex-3d-extrusion"] });
      if (hexHits.length > 0) hexProps = hexHits[0].properties;
    }
    const h = Number(props.render_height || props.height || 8);
    const kec = hexProps ? hexProps.kecamatan : "Kota Medan";
    const elev = hexProps ? hexProps.elev_mean : "-";
    const fHtml =
      `<div>Bangunan 3D dari peta vektor OpenStreetMap Kota Medan (${kec}).</div>` +
      `<div style="margin-top:4px;color:#167D8D"><strong>Sumber Data:</strong> OpenFreeMap / OpenStreetMap Building Footprints &amp; DEM SRTM 30m</div>`;

    showInspector(
      "Bangunan 3D Kota Medan",
      hexProps ? hexProps.kelas_risiko : "Kota Medan",
      "insp-badge-teal",
      `Bangunan #${props.id || "OSM"} (${kec})`,
      [
        ["Kecamatan", kec],
        ["Koordinat GPS", `${lngLat.lat.toFixed(5)}, ${lngLat.lng.toFixed(5)}`],
        ["Tinggi Bangunan", `${h} meter`],
        ["Ketinggian Tanah", `${elev} mdpl`],
      ],
      fHtml,
      [lngLat.lng, lngLat.lat]
    );
  }

  function inspectHex(p, clickLngLat) {
    const effFlood = getEffectiveFloodStage();
    const isFlooded = effFlood > 0.05 && Number(p.flood_crit_stage_m || 99) <= effFlood;
    const badgeCls = isFlooded
      ? "insp-badge-ink"
      : p.kelas_risiko.includes("Kritis") || p.kelas_risiko === "Tinggi"
      ? "insp-badge-ink"
      : p.kelas_risiko === "Sedang"
      ? "insp-badge-teal"
      : "insp-badge-ice";

    const darkN = Math.max(0, Math.min(1, (hexViirsP90 - Number(p.viirs_mean)) / Math.max(hexViirsP90, 1)));
    const polG = Math.max(0, Math.min(1, Number(p.dist_polisi_m) / 4500));
    const korP = Math.max(0, Math.min(1, 1 - Number(p.dist_koridor_m) / 1500));

    const fHtml =
      `<div><strong>Rumus Perhitungan Skor Gelap (Michael):</strong><br/>42% Gelap VIIRS (+${(42 * darkN).toFixed(1)}) + 33% Jarak Polisi (+${(33 * polG).toFixed(1)}) + 25% Dekat Koridor Begal (+${(25 * korP).toFixed(1)}) = <strong>${p.risk_score}/100</strong>.</div>` +
      `<div><strong>Rumus Banjir Lembah Sungai (Visel):</strong> Ketinggian tanah ${p.elev_mean} mdpl (+${p.hand_m ?? "-"} m di atas sungai). Terendam jika air sungai naik <strong>+${p.flood_crit_stage_m ?? "-"} m</strong>.</div>` +
      `<div style="margin-top:4px;color:#167D8D"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang5} &amp; DEM SRTM 30m USGS</div>`;

    const coords = clickLngLat ? [clickLngLat.lng, clickLngLat.lat] : null;
    showInspector(
      "Petak Wilayah Heksagon 500m",
      isFlooded ? `TERENDAM (+${effFlood.toFixed(1)}m)` : p.kelas_risiko,
      badgeCls,
      `${p.hex_id} — ${p.kecamatan}`,
      [
        ["Fitur & Pembuat", "Jalan Gelap Rawan Begal & Lampu PJU (Michael)"],
        ["Tingkat Risiko Malam", `${p.risk_score} / 100 (${p.kelas_risiko})`],
        ["Cahaya Malam Satelit", `${p.viirs_mean} DN (Rentang ${p.viirs_min}–${p.viirs_max})`],
        ["Ketinggian Tanah", `${p.elev_mean} mdpl (+${p.hand_m ?? "-"} m dari sungai)`],
        ["Batas Aman Banjir", `Tergenang jika sungai naik +${p.flood_crit_stage_m ?? "-"} m`],
        ["Jarak Kantor Polisi", `${p.dist_polisi_m} meter`],
      ],
      fHtml,
      coords
    );
  }

  function inspectCorridor(p, clickLngLat) {
    const fHtml =
      `<div><strong>Catatan Kepolisian:</strong> ${p.bukti_rilis || p.sumber_data} (Jam rawan: ${p.jam_rawan || "22:00-05:00 WIB"}).</div>` +
      `<div style="margin-top:4px;color:#167D8D"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang5}</div>`;
    const coords = [Number(p.lon || (clickLngLat && clickLngLat.lng)), Number(p.lat || (clickLngLat && clickLngLat.lat))];
    showInspector(
      "Jalan Gelap Rawan Begal (Michael)",
      p.tingkat_bahaya,
      "insp-badge-ink",
      p.nama_jalan,
      [
        ["Fitur & Pembuat", "Jalan Gelap Rawan Begal & Lampu PJU (Michael)"],
        ["Kecamatan", p.kecamatan],
        ["Masalah Utama", p.jenis_kerawanan],
        ["Panjang Jalan", `${p.panjang_km} km`],
        ["Jam Rawan Kejahatan", p.jam_rawan || "22:00 - 05:00 WIB"],
        ["Sumber Data", "Rilis Polrestabes Medan & Satelit VIIRS 2024"],
      ],
      fHtml,
      coords
    );
  }

  function inspectPJU(p, geomCoords) {
    const fHtml =
      `<div><strong>Perhitungan Solusi (Michael):</strong> Dipasang pada titik jalan gelap (<code>VIIRS = ${p.viirs_awal} DN</code>) untuk menerangi <strong>${p.gedung_terlindungi} bangunan</strong> dalam radius ${p.radius_terang_m} meter.</div>` +
      `<div style="margin-top:4px;color:#167D8D"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang5}</div>`;
    showInspector(
      "Solusi Lampu PJU & CCTV 3D (Michael)",
      p.prioritas,
      "insp-badge-teal",
      `${p.id_unit} — ${p.nama_lokasi}`,
      [
        ["Fitur & Pembuat", "Jalan Gelap Rawan Begal & Lampu PJU (Michael)"],
        ["Jenis Alat 3D", p.jenis_solusi],
        ["Kecamatan", p.kecamatan],
        ["Jangkauan Cahaya", `Radius ${p.radius_terang_m} meter`],
        ["Rumah Terlindungi", `${p.gedung_terlindungi} bangunan sekitar`],
        ["Sumber Data", "Analisis Satelit VIIRS 2024 & Jaringan Jalan OSM"],
      ],
      fHtml,
      geomCoords
    );
  }

  function inspectPatrol(p, clickLngLat) {
    const fHtml =
      `<div>Rute patroli malam kepolisian yang menghubungkan polsek melewati jalan-jalan gelap rawan kejahatan.</div>` +
      `<div style="margin-top:4px;color:#167D8D"><strong>Sumber Data:</strong> ${DATA_SOURCES.orang5}</div>`;
    const coords = clickLngLat ? [clickLngLat.lng, clickLngLat.lat] : null;
    showInspector(
      "Rute Patroli Malam (Michael)",
      `${p.panjang_km} km`,
      "insp-badge-teal",
      p.nama_rute,
      [
        ["Fitur & Pembuat", "Jalan Gelap Rawan Begal & Lampu PJU (Michael)"],
        ["Tim Patroli", p.unit_pelaksana],
        ["Jam Patroli", p.jam_patroli],
        ["Jalan yang Dilalui", p.koridor_dilalui],
        ["Sumber Data", "Rute OSRM OpenStreetMap & Polrestabes Medan"],
      ],
      fHtml,
      coords
    );
  }

  function inspectPolice(p, geomCoords) {
    const fHtml =
      `<div>Lokasi kantor polisi resmi untuk menghitung jarak pengamanan ke permukiman warga di 21 kecamatan.</div>` +
      `<div style="margin-top:4px;color:#167D8D"><strong>Sumber Data:</strong> ${p.sumber_data || DATA_SOURCES.orang5}</div>`;
    showInspector(
      "Kantor & Pos Polisi (Michael)",
      p.jenis,
      "insp-badge-ice",
      p.nama,
      [
        ["Fitur & Pembuat", "Jalan Gelap Rawan Begal & Lampu PJU (Michael)"],
        ["Kecamatan", p.kecamatan],
        ["Alamat", p.alamat || "Kota Medan"],
        ["Sumber Data", p.sumber || "OpenStreetMap & Polrestabes Medan"],
      ],
      fHtml,
      geomCoords
    );
  }

  function inspectRiver(p, clickLngLat) {
    const coords = clickLngLat ? [clickLngLat.lng, clickLngLat.lat] : null;
    showInspector(
      "Jaringan Sungai & Kanal Kota Medan",
      p.waterway === "canal" ? "Kanal / Drainase" : "Sungai Utama",
      "insp-badge-teal",
      p.nama || "Aliran Sungai Kota Medan",
      [
        ["Fitur Terkait", "Luapan Banjir Sungai, RS Rujukan & Evakuasi (Visel)"],
        ["Kecamatan", p.kecamatan || "Kota Medan"],
        ["Jenis Aliran", p.waterway === "canal" ? "Kanal / Saluran Drainase Primer" : "Aliran Sungai DAS Medan"],
        ["Sumber Data", p.sumber_data || DATA_SOURCES.orang3],
      ],
      `<div>Aliran sungai menjadi pusat perhitungan ketinggian luapan air banjir pada peta topografi DEM SRTM 30m.</div>`,
      coords
    );
  }

  function inspectTeamFeature(p, clickLngLat) {
    const coords = clickLngLat ? [clickLngLat.lng, clickLngLat.lat] : null;
    const tim = p.tim || "Tim";

    if (tim === "Orang 1") {
      if (p.sub_tipe === "jalur_peneduh") {
        showInspector(
          "Suhu Panas & Pohon Peneduh (William)",
          p.prioritas || "Jalur Pohon",
          "insp-badge-teal",
          p.nama_jalan || p.nama_solusi,
          [
            ["Fitur & Pembuat", "Suhu Panas & Pohon Peneduh (William)"],
            ["Kecamatan / Segmen", `${p.kecamatan || "Kota Medan"} · ${p.segmen || "-"}`],
            ["Panjang Koridor", `${p.panjang_km} km (${p.tipe_jalan})`],
            ["Perhitungan Penurunan Suhu", `Awal ${p.suhu_rata_c} °C -> Setelah Solusi ${p.suhu_sim_c} °C`],
            ["Jenis & Jumlah Pohon", `${p.jenis_pohon} (${p.est_pohon} Pohon)`],
            ["Sumber Data", p.sumber_data || DATA_SOURCES.orang1],
          ],
          `<div><strong>Rumus &amp; Alasan Solusi (William):</strong> ${p.alasan_solusi}</div>`,
          coords
        );
        return;
      }
      if (p.sub_tipe === "halte_teduh" || p.sub_tipe === "pohon_3d_koridor") {
        showInspector(
          "Suhu Panas & Pohon Peneduh (William)",
          p.sub_tipe === "halte_teduh" ? "Halte Sejuk 3D" : "Pohon Peneduh 3D",
          "insp-badge-ice",
          p.nama_halte || p.nama_solusi,
          [
            ["Fitur & Pembuat", "Suhu Panas & Pohon Peneduh (William)"],
            ["Kecamatan", p.kecamatan],
            ["Lokasi", p.lokasi_patokan || p.jenis_pohon || "-"],
            ["Perhitungan Penurunan Suhu", p.suhu_lokasi_c ? `${p.suhu_lokasi_c} °C -> ${p.suhu_sim_c} °C` : "Menurunkan suhu sekitar -2,8 s/d -3,6 °C"],
            ["Sumber Data", p.sumber_data || DATA_SOURCES.orang1],
          ],
          `<div><strong>Spesifikasi Solusi (William):</strong> ${p.fasilitas_desain || p.indikator_utama}</div>`,
          coords
        );
        return;
      }
      showInspector(
        "Suhu Panas & Pohon Peneduh (William)",
        state.simUhiActive ? `SETELAH SOLUSI: ${p.lst_sim} °C` : `${p.lst_mean} °C`,
        state.simUhiActive ? "insp-badge-ice" : "insp-badge-ink",
        `${p.hex_id} — ${p.kecamatan}`,
        [
          ["Fitur & Pembuat", "Suhu Panas & Pohon Peneduh (William)"],
          ["Suhu Siang Hari (Awal)", `${p.lst_mean} °C (Rentang ${p.lst_min}–${p.lst_max} °C)`],
          ["Suhu Setelah Pohon Ditanam", `${p.lst_sim} °C (Turun -${p.cooling_delta_c} °C)`],
          ["Kondisi Lingkungan", p.karakter_tapak],
          ["Jarak ke Jalur Pohon / Halte", `${p.dist_jalur_peneduh_m} m / ${p.dist_halte_teduh_m} m`],
          ["Sumber Data", p.sumber_data || DATA_SOURCES.orang1],
        ],
        `<div><strong>Rumus Perhitungan Pendinginan (William):</strong> <code>LST_Sim = ${p.lst_mean}°C - ${p.cooling_delta_c}°C = ${p.lst_sim}°C</code> berdasarkan jarak ke jalur pohon (${p.dist_jalur_peneduh_m}m) &amp; halte sejuk (${p.dist_halte_teduh_m}m).<br/><strong>Rekomendasi:</strong> ${p.rekomendasi_solusi}</div>`,
        coords
      );
      return;
    }

    if (tim === "Orang 2") {
      if (p.sub_tipe === "taman_rth") {
        showInspector(
          "Kerapatan Pohon & Taman Hijau (Jordan)",
          "Taman Hijau 3D",
          "insp-badge-teal",
          p.nama_solusi,
          [
            ["Fitur & Pembuat", "Kerapatan Pohon & Taman Hijau (Jordan)"],
            ["Petak & Kecamatan", `${p.hex_id || "-"} · ${p.kecamatan}`],
            ["Kerapatan Pohon Awal", `${Number(p.ndvi_awal).toFixed(3)} (Gersang / Kurang Pohon)`],
            ["Kerapatan Setelah Taman Baru", `${Number(p.ndvi_target).toFixed(3)} (Hijau Rimbun)`],
            ["Sumber Data", p.sumber_data || DATA_SOURCES.orang2],
          ],
          `<div><strong>Rumus Perhitungan Solusi (Jordan):</strong> ${p.indikator_utama}</div>`,
          coords
        );
        return;
      }
      const ndviStr = p.ndvi_mean !== null && p.ndvi_mean !== undefined ? Number(p.ndvi_mean).toFixed(3) : "-";
      const ndviSimStr = p.ndvi_sim !== null && p.ndvi_sim !== undefined ? Number(p.ndvi_sim).toFixed(3) : "-";
      showInspector(
        "Kerapatan Pohon & Taman Hijau (Jordan)",
        state.simRthActive ? "HIJAU (SETELAH TAMAN)" : p.ndvi_class,
        state.simRthActive ? "insp-badge-ice" : "insp-badge-teal",
        `${p.hex_id} — ${p.kecamatan}`,
        [
          ["Fitur & Pembuat", "Kerapatan Pohon & Taman Hijau (Jordan)"],
          ["Skor Kerapatan Pohon (Awal)", `${ndviStr} (${p.ndvi_class})`],
          ["Skor Setelah Taman Dibangun", `${ndviSimStr} (Bertambah Rimbun)`],
          ["Suhu Siang Hari di Area Ini", `${p.lst_mean} °C`],
          ["Sumber Data", p.sumber_data || DATA_SOURCES.orang2],
        ],
        `<div><strong>Rumus NDVI Sentinel-2 (Jordan):</strong> <code>NDVI = (NIR_B08 - Red_B04)/(NIR_B08 + Red_B04) = ${ndviStr}</code> &rarr; Pasca Injeksi Taman Saku: <code>${ndviSimStr}</code>.<br/><strong>Rekomendasi:</strong> ${p.rekomendasi_solusi || p.status_tim}</div>`,
        coords
      );
      return;
    }

    if (tim === "Orang 3") {
      if (p.sub_tipe === "titik_banjir_visel") {
        showInspector(
          "Titik Kejadian Banjir & Evakuasi (Visel)",
          state.simFloodSolutionActive ? `Surut: ${p.kedalaman_setelah_solusi_m} m` : `Kedalaman: ${p.kedalaman_air_m} m`,
          state.simFloodSolutionActive ? "insp-badge-ice" : "insp-badge-ink",
          `Kelurahan ${p.kelurahan} — ${p.kecamatan}`,
          [
            ["Fitur & Pembuat", "Luapan Banjir Sungai, RS Rujukan & Evakuasi (Visel)"],
            ["Kelurahan / Kecamatan", `Kel. ${p.kelurahan} · ${p.kecamatan}`],
            ["Kedalaman Air Banjir", state.simFloodSolutionActive ? `Awal ${p.kedalaman_air_m} m -> Surut Jadi ${p.kedalaman_setelah_solusi_m} m` : `${p.kedalaman_air_m} meter`],
            ["Warga Dievakuasi", `${p.warga_dievakuasi} warga`],
            ["Sungai Meluap & Tanggal", `${p.sungai} (${p.tanggal})`],
            ["RS Rujukan Terdekat", `${p.rs_rujukan_terdekat} (Jarak ${p.jarak_rs_m} m)`],
            ["Asal Data Resmi", p.asal_titik || `${p.sumber} (Banjir Medan 28-29 Okt 2026)`],
          ],
          `<div><strong>Perhitungan Solusi (Visel):</strong> ${p.indikator_utama}</div>`,
          coords
        );
        return;
      }
      if (p.sub_tipe === "rs_rujukan_banjir") {
        const isTerdampak = String(p.status_banjir || "").toLowerCase().includes("terdampak");
        showInspector(
          "Rumah Sakit Rujukan Banjir 3D (Visel)",
          isTerdampak ? "RS di Kec. Terdampak Banjir" : "RS Rujukan Aman Banjir",
          isTerdampak ? "insp-badge-ink" : "insp-badge-ice",
          p.nama_solusi || p.name,
          [
            ["Fitur & Pembuat", "Luapan Banjir Sungai, RS Rujukan & Evakuasi (Visel)"],
            ["Kecamatan & Alamat", `${p.kecamatan} · ${p.alamat || "-"}`],
            ["Status Banjir (Visel)", p.status_banjir],
            ["Ketinggian Tanah (DEM)", `${p.elev_mdpl} mdpl (+${p.hand_m} m di atas sungai)`],
            ["Kontak Darurat Medis", p.telepon || "112 / 119"],
            ["Sumber Data", p.sumber_banjir || DATA_SOURCES.orang3],
          ],
          `<div><strong>Peran Evakuasi Medis (Visel):</strong> ${p.indikator_utama}</div>`,
          coords
        );
        return;
      }
      if (p.stage_m !== undefined) {
        const effSt = getEffectiveFloodStage();
        showInspector(
          "Luapan Banjir Sungai, RS Rujukan & Evakuasi (Visel)",
          `Air Sungai +${ effSt.toFixed(1) } m`,
          state.simFloodSolutionActive ? "insp-badge-ice" : "insp-badge-ink",
          `Genangan Air Banjir Lembah Sungai (+${p.stage_m} m)`,
          [
            ["Fitur & Pembuat", "Luapan Banjir Sungai, RS Rujukan & Evakuasi (Visel)"],
            ["Kenaikan Air Sungai", `+${p.stage_m} meter di atas permukaan sungai normal`],
            ["Luas Area Terendam", state.simFloodSolutionActive ? `${p.luas_setelah_solusi_km2 || (p.luas_genangan_km2 * 0.42).toFixed(2)} km² (Surut berkat Kolam Retensi)` : `${p.luas_genangan_km2} km²`],
            ["Cara Perhitungan", "Ketinggian Tanah DEM SRTM 30m + Cekungan Lembah Sungai (HAND)"],
            ["Sumber Data", p.sumber_data || DATA_SOURCES.orang3],
          ],
          `<div><strong>Rumus Perhitungan Genangan (Visel):</strong> Area dengan ketinggian di atas sungai terdekat (<code>HAND &le; +${p.stage_m}m</code>) terendam luapan DAS. Saat solusi 14 Kolam Retensi &amp; Pompa diaktifkan, tinggi air turun <strong>-1,5 meter</strong>.</div>`,
          coords
        );
        return;
      }
      showInspector(
        "Luapan Banjir Sungai, RS Rujukan & Evakuasi (Visel)",
        p.sub_tipe === "kolam_retensi" ? "Kolam Retensi & Pompa" : p.sub_tipe === "posko_evakuasi" ? "Posko Evakuasi 3D" : p.sub_tipe === "jalur_evakuasi_rs" ? "Rute Evakuasi ke RS" : p.kelas_masalah || "Area Banjir",
        "insp-badge-teal",
        p.nama_solusi || `${p.hex_id} — ${p.kecamatan}`,
        [
          ["Fitur & Pembuat", "Luapan Banjir Sungai, RS Rujukan & Evakuasi (Visel)"],
          ["Kecamatan", p.kecamatan || "-"],
          ["Ketinggian Tanah (DEM SRTM)", `${p.elev_mean ?? p.elev_mdpl ?? "-"} meter di atas laut (mdpl)`],
          ["Tinggi dari Permukaan Sungai", `+${p.hand_m ?? "-"} meter`],
          ["RS Rujukan Terdekat", p.rs_rujukan_terdekat ? `${p.rs_rujukan_terdekat} (${p.jarak_rs_m} m)` : "Tersedia di Kecamatan Ini"],
          ["Sumber Data", p.sumber_data || DATA_SOURCES.orang3],
        ],
        `<div><strong>Penjelasan &amp; Perhitungan (Visel):</strong> ${p.indikator_utama || p.status_tim}</div>`,
        coords
      );
      return;
    }

    if (tim === "Orang 4") {
      if (p.mode_iso) {
        showInspector(
          "Jangkauan Pemadam Kebakaran & Hidran (Peter)",
          `Terjangkau <= ${p.aa_mins} Menit`,
          p.mode_iso === "simulasi" ? "insp-badge-ice" : "insp-badge-teal",
          p.nama_solusi,
          [
            ["Fitur & Pembuat", "Jangkauan Pemadam Kebakaran & Hidran (Peter)"],
            ["Waktu Tempuh Mobil Damkar", `Maksimal ${p.aa_mins} Menit lewat jalan raya`],
            ["Kondisi Pos Pemadam", p.mode_iso === "simulasi" ? "Setelah Ditambah Pos Pemadam Baru di 21 Kecamatan" : "Kondisi Awal (Hanya 2 Pos Pemadam Eksisting)"],
            ["Jumlah Warga Terlindungi", `${Number(p.total_pop || 0).toLocaleString("id-ID")} jiwa`],
            ["Sumber Data", p.sumber_data || DATA_SOURCES.orang4],
          ],
          `<div><strong>Rumus Isochrone (Peter):</strong> ${p.indikator_utama}</div>`,
          coords
        );
        return;
      }
      if (p.sub_tipe) {
        showInspector(
          "Jangkauan Pemadam Kebakaran & Hidran (Peter)",
          p.sub_tipe.replace(/_/g, " ").toUpperCase(),
          "insp-badge-teal",
          p.nama_solusi,
          [
            ["Fitur & Pembuat", "Jangkauan Pemadam Kebakaran & Hidran (Peter)"],
            ["Kecamatan", `${p.kecamatan} (${p.wilayah_cakupan || p.keterangan || "Kota Medan"})`],
            ["Fungsi Utama", p.kategori_solusi],
            ["Status Perlindungan", p.indikator_utama],
            ["Sumber Data", p.sumber_data || DATA_SOURCES.orang4],
          ],
          `<div>Titik infrastruktur pemadam kebakaran &amp; pasar tradisional dari analisis Peter (mencakup seluruh 21 kecamatan).</div>`,
          coords
        );
        return;
      }
      showInspector(
        "Jangkauan Pemadam Kebakaran & Hidran (Peter)",
        state.simDamkarActive && p.tercakup_simulasi === 1 ? "TERJANGKAU <=10 MENIT" : "TERLAMBAT >10 MENIT",
        state.simDamkarActive && p.tercakup_simulasi === 1 ? "insp-badge-ice" : "insp-badge-ink",
        `Wilayah #${p.fid} — ${p.kecamatan} (${p.hex_id})`,
        [
          ["Fitur & Pembuat", "Jangkauan Pemadam Kebakaran & Hidran (Peter)"],
          ["Jumlah Rumah/Bangunan", `${Number(p.jml_bangunan).toLocaleString("id-ID")} bangunan`],
          ["Waktu Tempuh Awal", `${p.eta_awal_menit} menit (Jarak pos lama: ${p.dist_pos_eksisting_m} m)`],
          ["Waktu Tempuh Setelah Solusi", `${p.eta_sim_menit} menit (Jarak pos baru: ${p.dist_pos_solusi_m} m)`],
          ["Jarak Hidran Air Terdekat", `${p.dist_hidran_m} meter`],
          ["Sumber Data", p.sumber_data || DATA_SOURCES.orang4],
        ],
        `<div><strong>Rumus Perhitungan Waktu Tempuh (Peter):</strong> <code>ETA_Awal = ${p.eta_awal_menit} menit</code> (di luar jangkauan 10 menit ORS) &rarr; Setelah Pos Damkar Baru: <code>ETA_Solusi = ${p.eta_sim_menit} menit</code>.</div>`,
        coords
      );
      return;
    }
  }

  function syncBasemapLayers() {
    if (!map) return;
    const vis = (flag) => (flag ? "visible" : "none");
    const isGlobe = state.currentProj === "globe";
    const mode = state.basemap;
    const isNightSat = mode === "satelit";
    const isDaySat = mode === "satelit-terang" || mode === "3d";
    const isTopo = mode === "topo";
    const isOsm = mode === "osm";
    const isTematik = mode === "tematik" || mode === "viirs";

    if (map.getLayer("paper-background")) {
      map.setPaintProperty("paper-background", "background-color", isNightSat ? PAL.ink : PAL.paper);
    }
    if (map.getLayer("basemap-light")) {
      map.setLayoutProperty("basemap-light", "visibility", vis(isTematik && !isGlobe));
    }
    if (map.getLayer("basemap-osm")) {
      map.setLayoutProperty("basemap-osm", "visibility", vis(isOsm));
    }
    if (map.getLayer("basemap-topo")) {
      map.setLayoutProperty("basemap-topo", "visibility", vis(isTopo));
    }
    if (map.getLayer("basemap-nasa-night")) {
      map.setLayoutProperty("basemap-nasa-night", "visibility", vis(isNightSat || (isGlobe && isTematik)));
    }
    if (map.getLayer("basemap-gibs-night")) {
      map.setLayoutProperty("basemap-gibs-night", "visibility", vis(isNightSat || (isGlobe && isTematik)));
    }
    if (map.getLayer("basemap-satelit")) {
      map.setLayoutProperty("basemap-satelit", "visibility", vis(isDaySat));
    }
  }

  function setBasemap(mode) {
    state.basemap = mode;
    state.satSubmode = mode === "satelit" ? "night" : "day";
    document.querySelectorAll(".base-btn").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-basemap") === mode);
    });
    if (!map) return;

    if (mode === "3d") {
      state.terrain3D = true;
      const btnT = document.getElementById("btn-terrain");
      if (btnT) btnT.classList.add("is-active");
      map.setTerrain({ source: "terrarium-dem", exaggeration: 3.2 });
      if (state.currentProj !== "globe" && map.getPitch() < 55) {
        map.easeTo({ pitch: 65, duration: 700 });
      }
      if (threeLayerApi) threeLayerApi.updateElevations();
      state.layers.nightMask = false;
      if (state.dataOpacity > 0.75) setDataOpacity(0.65);
    } else if (mode === "topo" || mode === "osm" || mode === "satelit-terang") {
      state.layers.nightMask = false;
      if (state.dataOpacity > 0.8) setDataOpacity(0.70);
    } else if (mode === "satelit") {
      state.layers.nightMask = true;
      if (state.dataOpacity > 0.75) setDataOpacity(0.65);
    } else {
      state.layers.nightMask = false;
      if (state.dataOpacity < 0.8) setDataOpacity(0.90);
    }
    applyFiltersAndRedraw();
  }

  function setProjectionMode(targetProj) {
    if (!map) return;
    document.querySelectorAll('.seg-btn[data-projmode]').forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-projmode") === targetProj);
    });
    if (targetProj === "globe") {
      map.setPadding({ top: 16, bottom: 120, left: 0, right: 0 });
      map.jumpTo({ ...PRESETS["globe-3d"] });
    } else {
      map.setPadding({ top: 0, bottom: 0, left: 0, right: 0 });
      if (map.getZoom() < 7.5) {
        map.jumpTo(PRESETS["overview-medan"]);
      }
    }
    syncProjectionByZoom();
    applyFiltersAndRedraw();
  }

  function setDataOpacity(valFloat) {
    state.dataOpacity = valFloat;
    const pct = Math.round(valFloat * 100);
    const sEl = document.getElementById("slider-opacity");
    const vEl = document.getElementById("opacity-val");
    if (sEl) sEl.value = String(pct);
    if (vEl) vEl.textContent = `${pct}%`;
    if (!map) return;
    if (map.getLayer("buildings-3d")) map.setPaintProperty("buildings-3d", "fill-extrusion-opacity", valFloat);
    if (map.getLayer("buildings-citywide-3d")) map.setPaintProperty("buildings-citywide-3d", "fill-extrusion-opacity", Math.max(0.2, valFloat - 0.2));
    if (map.getLayer("hex-flat-fill")) map.setPaintProperty("hex-flat-fill", "fill-opacity", Math.min(0.45, valFloat * 0.42));
    if (map.getLayer("hex-3d-extrusion")) map.setPaintProperty("hex-3d-extrusion", "fill-extrusion-opacity", Math.max(0.3, valFloat * 0.88));
  }

  function syncProjectionByZoom() {
    if (!map) return;
    const z = map.getZoom();
    const target = z < 7.5 ? "globe" : "mercator";
    if (state.currentProj !== target) {
      state.currentProj = target;
      if (target === "globe") {
        map.setPadding({ top: 16, bottom: 120, left: 0, right: 0 });
      } else {
        map.setPadding({ top: 0, bottom: 0, left: 0, right: 0 });
      }
      try {
        map.setProjection({ type: target });
      } catch (e) {
        console.warn("setProjection fallback:", e);
      }
      map.setTerrain(state.terrain3D ? { source: "terrarium-dem", exaggeration: 3.2 } : null);
      const pBadge = document.getElementById("proj-badge");
      if (pBadge) {
        pBadge.textContent = target === "globe" ? "BOLA DUNIA 3D" : "PETA KOTA 3D";
      }
      document.querySelectorAll('.seg-btn[data-projmode]').forEach((b) => {
        b.classList.toggle("active", b.getAttribute("data-projmode") === target);
      });
      requestAnimationFrame(() => {
        if (!map) return;
        if (state.currentProj === "globe" && (map.getPitch() > 2 || Math.abs(map.getBearing()) > 2 || map.getZoom() <= 2.4)) {
          map.jumpTo({ center: [98.668, 3.615], zoom: Math.max(2.0, Math.min(map.getZoom(), 3.2)), pitch: 0, bearing: 0 });
        }
        applyFiltersAndRedraw();
      });
    }
  }

  function refreshBuildingPaint() {
    if (!map || !map.getLayer("buildings-3d")) return;

    const effFlood = getEffectiveFloodStage();
    const floodThresh = effFlood > 0.05 && state.subLayers.o3_air ? effFlood : -1.0;
    const rawFloodThresh = state.simFloodSolutionActive && state.floodStageM > 0.05 && state.subLayers.o3_air ? state.floodStageM : -1.0;

    if ((state.activeSimTab === "orang3" || effFlood > 0.05) && state.subLayers.o3_air) {
      map.setPaintProperty("buildings-3d", "fill-extrusion-color", [
        "case",
        ["<=", ["coalesce", ["get", "flood_crit_m"], 99], floodThresh],
        PAL.waterMid,
        ["<=", ["coalesce", ["get", "flood_crit_m"], 99], rawFloodThresh],
        PAL.greenBright,
        "#e2e8f0",
      ]);
    } else if (state.activeSimTab === "orang4" && state.teamLayers.orang4) {
      const colExpr = state.simDamkarActive
        ? [
            "case",
            ["==", ["get", "damkar_sim_10m"], 1],
            "#86efac",
            PAL.fireRed,
          ]
        : [
            "case",
            ["==", ["get", "damkar_eks_10m"], 1],
            PAL.ice,
            "#991b1b",
          ];
      map.setPaintProperty("buildings-3d", "fill-extrusion-color", colExpr);
    } else if (state.activeSimTab === "orang1" && state.teamLayers.orang1) {
      map.setPaintProperty("buildings-3d", "fill-extrusion-color",
        state.simUhiActive
          ? ["match", ["get", "status_rawan"], "Tinggi", "#86efac", "Sedang", "#bae6fd", "#e0f2fe"]
          : ["match", ["get", "status_rawan"], "Tinggi", "#d7191c", "Sedang", "#fdae61", "#abdda4"]
      );
    } else if (state.activeSimTab === "orang2" && state.teamLayers.orang2) {
      map.setPaintProperty("buildings-3d", "fill-extrusion-color",
        state.simRthActive
          ? ["match", ["get", "status_rawan"], "Tinggi", "#22c55e", "Sedang", "#86efac", "#bbf7d0"]
          : ["match", ["get", "status_rawan"], "Tinggi", "#d73027", "Sedang", "#fc8d59", "#fee08b"]
      );
    } else if (state.simulationActive) {
      map.setPaintProperty("buildings-3d", "fill-extrusion-color", [
        "case",
        ["==", ["get", "terlindungi_solusi"], 1],
        PAL.ice,
        ["==", ["get", "status_rawan"], "Tinggi"],
        PAL.ink,
        ["==", ["get", "status_rawan"], "Sedang"],
        PAL.teal,
        PAL.ice,
      ]);
    } else {
      map.setPaintProperty("buildings-3d", "fill-extrusion-color", [
        "case",
        ["==", ["get", "status_rawan"], "Tinggi"],
        PAL.ink,
        ["==", ["get", "status_rawan"], "Sedang"],
        PAL.teal,
        PAL.ice,
      ]);
    }
    map.setPaintProperty("buildings-3d", "fill-extrusion-opacity", state.dataOpacity);
  }

  function refreshHexPaint() {
    if (!map) return;
    const isMercator = state.currentProj !== "globe";
    const is3d = (state.hexMode === "3d" || state.basemap === "3d") && isMercator;
    const effFlood = getEffectiveFloodStage();
    const hideMasterForTeamHex =
      (state.teamLayers.orang1 && (state.subLayers.o1_hex || state.subLayers.o1_sat)) ||
      (state.teamLayers.orang2 && (state.subLayers.o2_hex || state.subLayers.o2_sat)) ||
      (state.teamLayers.orang3 && (state.subLayers.o3_hex || state.subLayers.o3_sat)) ||
      (state.teamLayers.orang4 && state.subLayers.o4_hex) ||
      (state.teamLayers.orang3 && effFlood > 0.05 && state.subLayers.o3_air) ||
      state.subLayers.o5_sat ||
      state.basemap === "satelit" ||
      !state.teamLayers.orang5 ||
      !state.subLayers.o5_hex;
    const showHex = state.layers.hex && !hideMasterForTeamHex;

    if (map.getLayer("hex-3d-extrusion")) {
      map.setLayoutProperty("hex-3d-extrusion", "visibility", showHex && is3d ? "visible" : "none");
    }
    if (map.getLayer("hex-flat-fill")) {
      map.setLayoutProperty("hex-flat-fill", "visibility", showHex && !is3d ? "visible" : "none");
      map.setLayoutProperty("hex-flat-line", "visibility", showHex ? "visible" : "none");
    }
  }

  function buildCombinedTeamFC(kind) {
    if (!teamData) return { type: "FeatureCollection", features: [] };
    const feats = [];

    ["orang1", "orang2", "orang3", "orang4"].forEach((memberKey) => {
      if (!state.teamLayers[memberKey]) return;

      if (kind === "masalah") {
        if (memberKey === "orang1" && (!state.subLayers.o1_hex || state.subLayers.o1_sat)) return;
        if (memberKey === "orang2" && (!state.subLayers.o2_hex || state.subLayers.o2_sat)) return;
        if (memberKey === "orang3" && (!state.subLayers.o3_hex || state.subLayers.o3_sat)) return;
        if (memberKey === "orang4" && !state.subLayers.o4_hex) return;
      }

      const fc = teamData[`${memberKey}_${kind}`];
      if (!fc || !Array.isArray(fc.features)) return;

      const isCurrentTab = state.activeSimTab === memberKey;
      const stage1HideSol = isCurrentTab && state.simStage === 1;
      const maxStep = isCurrentTab ? state.solutionStepLimit : 99999;

      fc.features.forEach((f, idx) => {
        const p = f.properties || {};
        if (state.filterKec !== "ALL" && p.kecamatan && !String(p.kecamatan).includes(state.filterKec)) {
          return;
        }
        if (kind === "masalah") {
          if (memberKey === "orang1") {
            const curLst = state.simUhiActive ? Number(p.lst_sim) : Number(p.lst_mean);
            if (state.uhiMinTemp > 28.05 && curLst < state.uhiMinTemp) return;
          } else if (memberKey === "orang2") {
            const curNdvi = state.simRthActive ? p.ndvi_sim : p.ndvi_mean;
            if (curNdvi !== null && curNdvi !== undefined && Number(curNdvi) < state.ndviMinFilter) {
              return;
            }
          } else if (memberKey === "orang4") {
            if (Number(p.jml_bangunan || 0) < state.damkarMinBld) return;
          }
          feats.push(f);
        } else {
          // Sub-layer & 3-stage filtering for solution/reference features
          const st = p.sub_tipe || "";
          const ord = Number(p.step_order || idx + 1);

          if (memberKey === "orang1") {
            if (stage1HideSol || ord > maxStep) return;
            if (st === "jalur_peneduh" && !state.subLayers.o1_jalur) return;
            if ((st === "halte_teduh" || st === "pohon_3d_koridor") && !state.subLayers.o1_halte) return;
          } else if (memberKey === "orang2") {
            if (stage1HideSol || ord > maxStep) return;
            if (!state.subLayers.o2_taman) return;
          } else if (memberKey === "orang3") {
            if (st === "titik_banjir_visel") {
              if (!state.subLayers.o3_titik) return;
              // Flood incident points are existing problem/reference points (always visible in Stage 1..3)
            } else if (st === "rs_rujukan_banjir") {
              if (!state.subLayers.o3_rs) return;
              // Visel's 59 Hospitals are existing reference points (always visible in Stage 1..3)
            } else if (st === "jalur_evakuasi" || st === "jalur_evakuasi_rs") {
              if (!state.subLayers.o3_rute || stage1HideSol || ord > maxStep) return;
            } else {
              if (!state.subLayers.o3_solusi || stage1HideSol || ord > maxStep) return;
            }
          } else if (memberKey === "orang4") {
            if (st === "pos_damkar_eksisting" || st === "pasar_medan") {
              if (!state.subLayers.o4_eks) return;
              // Existing fire stations & 31 markets are Stage 1..3 reference points
            } else {
              // Proposed new fire stations & emergency hydrants are Stage 2..3 solutions
              if (!state.subLayers.o4_sol || stage1HideSol || ord > maxStep) return;
            }
          }
          feats.push(f);
        }
      });
    });
    return { type: "FeatureCollection", features: feats };
  }

  function buildActiveFloodContourFC() {
    const effFlood = getEffectiveFloodStage();
    if (!teamData || !teamData.orang3_kontur_banjir || effFlood <= 0.05 || !state.subLayers.o3_air) {
      return { type: "FeatureCollection", features: [] };
    }
    const nearestStage = Math.max(0.5, Math.min(5.0, Math.round(effFlood * 2) / 2));
    const feats = teamData.orang3_kontur_banjir.features.filter(
      (f) => Number(f.properties.stage_m) <= nearestStage
    );
    return { type: "FeatureCollection", features: feats };
  }

  function buildActiveIsochroneFC() {
    if (!teamData || !teamData.orang4_isochrone || !state.teamLayers.orang4 || !state.subLayers.o4_iso) {
      return { type: "FeatureCollection", features: [] };
    }
    const targetMode = state.simDamkarActive ? "simulasi" : "eksisting";
    const feats = teamData.orang4_isochrone.features.filter((f) => f.properties.mode_iso === targetMode);
    return { type: "FeatureCollection", features: feats };
  }

  function refreshTeamMasalahPaint() {
    if (!map || !map.getLayer("team-masalah-fill")) return;

    const uhiProp = state.simUhiActive ? "lst_sim" : "lst_mean";
    const ndviProp = state.simRthActive ? "ndvi_sim" : "ndvi_mean";

    const williamColorExpr = [
      "step",
      ["coalesce", ["get", uhiProp], 30.0],
      "#2b83ba",
      30.5,
      "#abdda4",
      32.5,
      "#fdae61",
      34.5,
      "#d7191c",
    ];

    const jordanColorExpr =
      state.jordanColorMode === "uhi"
        ? williamColorExpr
        : [
            "step",
            ["coalesce", ["get", ndviProp], 0.15],
            "#d73027",
            0.0001,
            "#fc8d59",
            0.111,
            "#fee08b",
            0.236,
            "#1a9850",
          ];

    const orang3ColorExpr = [
      "step",
      ["coalesce", ["get", "flood_crit_stage_m"], 3.0],
      "#0369a1",
      1.5,
      "#0284c7",
      2.5,
      "#38bdf8",
    ];

    const peterColorExpr = state.simDamkarActive
      ? [
          "case",
          ["==", ["get", "tercakup_simulasi"], 1],
          "#86efac",
          [
            "step",
            ["coalesce", ["get", "jml_bangunan"], 0],
            "#fed7aa",
            102,
            "#fcbea5",
            273,
            "#fb7050",
            448,
            "#d32020",
            654,
            "#67000d",
          ],
        ]
      : [
          "step",
          ["coalesce", ["get", "jml_bangunan"], 0],
          "#fed7aa",
          102,
          "#fcbea5",
          273,
          "#fb7050",
          448,
          "#d32020",
          654,
          "#67000d",
        ];

    const combinedColorExpr = [
      "match",
      ["get", "tim"],
      "Orang 1",
      williamColorExpr,
      "Orang 2",
      jordanColorExpr,
      "Orang 3",
      orang3ColorExpr,
      "Orang 4",
      peterColorExpr,
      PAL.teal,
    ];

    map.setPaintProperty("team-masalah-fill", "fill-color", combinedColorExpr);
    if (map.getLayer("team-masalah-3d")) {
      const scoreProp =
        (state.activeSimTab === "orang1" && state.simUhiActive) ||
        (state.activeSimTab === "orang2" && state.simRthActive) ||
        (state.activeSimTab === "orang4" && state.simDamkarActive)
          ? "skor_simulasi"
          : "skor_masalah";
      map.setPaintProperty("team-masalah-3d", "fill-extrusion-color", combinedColorExpr);
      map.setPaintProperty("team-masalah-3d", "fill-extrusion-height", ["*", ["coalesce", ["get", scoreProp], 30], 4.8]);
    }
  }

  function updateTeamBadge() {
    const badge = document.getElementById("team-active-badge");
    if (badge) {
      badge.textContent = `FITUR AKTIF: ${(TOPIC_NAMES[state.activeSimTab] || TOPIC_NAMES.orang5).toUpperCase()}`;
    }
    const simBadge = document.getElementById("sim-topic-badge");
    if (simBadge) {
      simBadge.innerHTML = `<span class="badge-dot"></span>${TOPIC_NAMES[state.activeSimTab] || TOPIC_NAMES.orang5}`;
    }
    const btnAll = document.getElementById("btn-toggle-all-team");
    if (btnAll) {
      const allOn = ["orang1", "orang2", "orang3", "orang4", "orang5"].every((k) => state.teamLayers[k]);
      btnAll.textContent = allOn ? "Matikan Semua" : "Nyalakan Semua";
    }
  }

  function updateSimStateChip() {
    const card = document.getElementById("sim-card");
    const tag = document.getElementById("sim-state-tag");
    if (!card || !tag) return;

    document.querySelectorAll(".stage-btn").forEach((b) => {
      b.classList.toggle("active", Number(b.getAttribute("data-stage")) === state.simStage);
    });

    if (state.simStage === 1) {
      card.classList.remove("sim-active");
      tag.textContent = "TAHAP 1: MASALAH";
    } else if (state.simStage === 2) {
      card.classList.remove("sim-active");
      tag.textContent = "TAHAP 2: TITIK SOLUSI";
    } else {
      card.classList.add("sim-active");
      tag.textContent = "TAHAP 3: HASIL SOLUSI";
    }
  }

  function applyFiltersAndRedraw() {
    if (!map) return;
    if (map.getSource("src-hex")) {
      map.getSource("src-hex").setData(getFilteredHexFC());
    }
    if (map.getSource("src-pju")) {
      map.getSource("src-pju").setData(getFilteredPjuFC());
    }
    if (map.getSource("src-pju-discs")) {
      map.getSource("src-pju-discs").setData(buildPjuDiscsSource());
    }
    if (map.getSource("src-team-masalah")) {
      map.getSource("src-team-masalah").setData(buildCombinedTeamFC("masalah"));
    }
    if (map.getSource("src-team-solusi")) {
      map.getSource("src-team-solusi").setData(buildCombinedTeamFC("solusi"));
    }
    if (map.getSource("src-flood-contour")) {
      map.getSource("src-flood-contour").setData(buildActiveFloodContourFC());
    }
    if (map.getSource("src-damkar-isochrone")) {
      map.getSource("src-damkar-isochrone").setData(buildActiveIsochroneFC());
    }

    const vis = (flag) => (flag ? "visible" : "none");
    const isMercator = state.currentProj !== "globe";
    const is3dHex = (state.hexMode === "3d" || state.basemap === "3d") && isMercator;
    const anyTeam14 = ["orang1", "orang2", "orang3", "orang4"].some((k) => state.teamLayers[k]);
    const effFlood = getEffectiveFloodStage();
    const showFloodWater = state.teamLayers.orang3 && state.subLayers.o3_air && effFlood > 0.05 && isMercator;
    const showMichael = state.teamLayers.orang5;
    const showMichaelSol = showMichael && !(state.activeSimTab === "orang5" && state.simStage === 1);

    const showTeamHex =
      state.layers.hex &&
      isMercator &&
      ((state.teamLayers.orang1 && state.subLayers.o1_hex && !state.subLayers.o1_sat) ||
        (state.teamLayers.orang2 && state.subLayers.o2_hex && !state.subLayers.o2_sat) ||
        (state.teamLayers.orang4 && state.subLayers.o4_hex) ||
        (state.teamLayers.orang3 && state.subLayers.o3_hex && !state.subLayers.o3_sat));

    const pairs = [
      ["buildings-citywide-3d", state.layers.buildings && isMercator],
      ["buildings-shadow", state.layers.buildings && isMercator],
      ["buildings-3d", state.layers.buildings && isMercator],
      ["raw-night-mask-layer", (state.layers.nightMask || state.basemap === "satelit") && isMercator],
      ["viirs-zone-outline", false],
      ["raw-lst-layer", (state.teamLayers.orang1 && state.subLayers.o1_sat) && isMercator],
      ["raw-viirs-layer", (state.layers.rawViirs || (showMichael && state.subLayers.o5_sat)) && isMercator],
      ["raw-ndvi-layer", (state.layers.rawNdvi || (state.teamLayers.orang2 && state.subLayers.o2_sat)) && isMercator],
      ["raw-dem-layer", (state.layers.rawDem || (state.teamLayers.orang3 && state.subLayers.o3_sat)) && isMercator],
      ["dem-hillshade", state.layers.rawDem || state.subLayers.o3_sat || state.terrain3D || state.basemap === "topo" || state.basemap === "3d"],
      ["team-masalah-fill", showTeamHex && !is3dHex],
      ["team-masalah-line", showTeamHex],
      ["team-masalah-3d", showTeamHex && is3dHex],
      ["damkar-isochrone-fill", state.teamLayers.orang4 && state.subLayers.o4_iso && isMercator],
      ["damkar-isochrone-line", state.teamLayers.orang4 && state.subLayers.o4_iso && isMercator],
      ["flood-contour-3d", showFloodWater],
      ["flood-contour-outline", showFloodWater],
      ["team-solusi-polygons-fill", anyTeam14],
      ["team-solusi-polygons-line", anyTeam14],
      ["team-solusi-lines-casing", anyTeam14],
      ["team-solusi-lines", anyTeam14],
      ["team-solusi-points", anyTeam14],
      ["corridors-casing", showMichael && state.subLayers.o5_koridor],
      ["corridors-core", showMichael && state.subLayers.o5_koridor],
      ["corridors-dash", showMichael && state.subLayers.o5_koridor],
      ["patrol-casing", showMichaelSol && state.subLayers.o5_patroli],
      ["patrol-core", showMichaelSol && state.subLayers.o5_patroli],
      ["pju-points", showMichaelSol && state.subLayers.o5_pju],
      ["pju-illumination-fill", showMichaelSol && state.subLayers.o5_pju && state.simulationActive && isMercator],
      ["pju-illumination-ring", showMichaelSol && state.subLayers.o5_pju && state.simulationActive && isMercator],
      ["pju-illumination-outline", showMichaelSol && state.subLayers.o5_pju && state.simulationActive && isMercator],
      ["police-points", showMichael && state.subLayers.o5_polisi],
      ["water-glow", state.layers.water || state.teamLayers.orang3],
      ["water-core", state.layers.water || state.teamLayers.orang3],
      ["kec-outline", state.layers.kec],
    ];
    pairs.forEach(([id, flag]) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", vis(flag));
      }
    });

    if (showFloodWater && map.getLayer("flood-contour-3d")) {
      map.setPaintProperty("flood-contour-3d", "fill-extrusion-height", Math.max(1.0, effFlood * 2.8));
    }

    updateTeamBadge();
    updateSimStateChip();
    syncBasemapLayers();
    refreshHexPaint();
    refreshTeamMasalahPaint();
    refreshBuildingPaint();
    if (threeLayerApi) {
      threeLayerApi.syncState();
    }
    map.triggerRepaint();
    updateKPIs();
  }

  function b64ToArrayBuffer(b64) {
    const bin = atob(b64);
    const len = bin.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = bin.charCodeAt(i);
    }
    return bytes.buffer;
  }

  function createThreeCustomLayer(mapInstance) {
    if (!window.THREE || !window.GLTFLoader || !window.MEDAN_MODELS) {
      console.warn("three.js atau MEDAN_MODELS tidak tersedia; fallback ke marker 2D.");
      return null;
    }

    const THREE = window.THREE;
    const GLTFLoader = window.GLTFLoader;
    const ORIGIN_LNG_LAT = [98.662, 3.585];
    const originMc = maplibregl.MercatorCoordinate.fromLngLat(ORIGIN_LNG_LAT, 0);
    const scaleUnit = originMc.meterInMercatorCoordinateUnits();

    const pjuGroup = new THREE.Group();
    const policeGroup = new THREE.Group();
    const teamGroups = {
      orang1: new THREE.Group(),
      orang2: new THREE.Group(),
      orang3: new THREE.Group(),
      orang4: new THREE.Group(),
    };
    const lampMats = [];
    const solutionBodyMats = [];
    const placedItems = [];
    const loadedTemplates = {};

    let camera = null;
    let scene = null;
    let renderer = null;
    let animStart = performance.now();

    const modelMatrix = new THREE.Matrix4()
      .makeTranslation(originMc.x, originMc.y, originMc.z)
      .scale(new THREE.Vector3(scaleUnit, -scaleUnit, scaleUnit))
      .multiply(new THREE.Matrix4().makeRotationAxis(new THREE.Vector3(1, 0, 0), Math.PI / 2));

    function updateElevations() {
      for (const item of placedItems) {
        let elev = 0;
        if (state.terrain3D && typeof mapInstance.queryTerrainElevation === "function") {
          const q = mapInstance.queryTerrainElevation(item.lngLat);
          if (typeof q === "number" && Number.isFinite(q)) elev = q;
        }
        item.obj.position.y = elev;
      }
    }

    function rebuildTeam3DInstances() {
      ["orang1", "orang2", "orang3", "orang4"].forEach((mk) => {
        const grp = teamGroups[mk];
        while (grp.children.length > 0) {
          grp.remove(grp.children[0]);
        }
        const fc = teamData && teamData[`${mk}_solusi`];
        if (!fc || !Array.isArray(fc.features)) return;

        fc.features.forEach((feat, idx) => {
          if (!feat.geometry || feat.geometry.type !== "Point") return;
          const p = feat.properties || {};
          const modelKey = p.model_3d;
          if (!modelKey || !loadedTemplates[modelKey]) return;

          const tpl = loadedTemplates[modelKey];
          const clone = tpl.clone(true);
          const [lon, lat] = feat.geometry.coordinates;
          const mc = maplibregl.MercatorCoordinate.fromLngLat([lon, lat], 0);
          const x = (mc.x - originMc.x) / scaleUnit;
          const z = (mc.y - originMc.y) / scaleUnit;
          clone.position.set(x, 0, z);

          let sc = 2.6;
          if (modelKey === "pohon_peneduh") sc = 3.2;
          else if (modelKey === "halte_teduh") sc = 3.0;
          else if (modelKey === "posko_evakuasi") sc = 2.8;
          else if (modelKey === "hidran_darurat") sc = 3.8;
          else if (modelKey === "pos_damkar") sc = 2.2;
          else if (modelKey === "rs_rujukan") sc = 2.4;

          clone.scale.setScalar(sc);
          clone.rotation.y = ((idx * 83.0) % 360) * (Math.PI / 180);
          clone.userData = {
            stepOrder: Number(p.step_order || idx + 1),
            subTipe: p.sub_tipe || "",
            kecamatan: p.kecamatan || "",
          };
          grp.add(clone);
          placedItems.push({ obj: clone, lngLat: [lon, lat] });
        });
      });
    }

    function syncState() {
      const notGlobe = state.currentProj !== "globe";
      const show3d = state.layers.models3d && notGlobe;

      // Michael 3D models (PJU & Police)
      const hideMichaelSol = state.activeSimTab === "orang5" && state.simStage === 1;
      const maxPjuStep = state.activeSimTab === "orang5" ? state.solutionStepLimit : 99999;
      pjuGroup.visible = show3d && state.teamLayers.orang5 && state.subLayers.o5_pju && !hideMichaelSol;
      pjuGroup.children.forEach((ch, idx) => {
        const ord = ch.userData && ch.userData.stepOrder ? ch.userData.stepOrder : idx + 1;
        ch.visible = ord <= maxPjuStep;
      });
      policeGroup.visible = show3d && state.teamLayers.orang5 && state.subLayers.o5_polisi;

      // Team 1..4 3D models with Stage 1..3 and Sub-Layer visibility
      ["orang1", "orang2", "orang3", "orang4"].forEach((mk) => {
        const grp = teamGroups[mk];
        grp.visible = show3d && state.teamLayers[mk];
        if (!grp.visible) return;
        const isCur = state.activeSimTab === mk;
        const hideSol = isCur && state.simStage === 1;
        const maxStep = isCur ? state.solutionStepLimit : 99999;

        grp.children.forEach((ch) => {
          const st = (ch.userData && ch.userData.subTipe) || "";
          const ord = (ch.userData && ch.userData.stepOrder) || 1;
          if (mk === "orang1") {
            ch.visible = !hideSol && ord <= maxStep && state.subLayers.o1_halte;
          } else if (mk === "orang2") {
            ch.visible = !hideSol && ord <= maxStep && state.subLayers.o2_taman;
          } else if (mk === "orang3") {
            if (st === "rs_rujukan_banjir") {
              ch.visible = state.subLayers.o3_rs;
            } else {
              ch.visible = !hideSol && ord <= maxStep && state.subLayers.o3_solusi;
            }
          } else if (mk === "orang4") {
            if (st === "pos_damkar_eksisting") {
              ch.visible = state.subLayers.o4_eks;
            } else {
              ch.visible = !hideSol && ord <= maxStep && state.subLayers.o4_sol;
            }
          }
        });
      });

      const anySim =
        state.simulationActive ||
        state.simUhiActive ||
        state.simRthActive ||
        state.simFloodSolutionActive ||
        state.floodStageM > 0.05 ||
        state.simDamkarActive;

      for (const m of solutionBodyMats) {
        m.transparent = !anySim;
        m.opacity = anySim ? 1.0 : 0.85;
        m.needsUpdate = true;
      }
      for (const lm of lampMats) {
        if (anySim) {
          lm.color.set(PAL.lamp);
          lm.emissive.set(PAL.lamp);
          lm.emissiveIntensity = 1.45;
          lm.transparent = false;
          lm.opacity = 1.0;
        } else {
          lm.color.set(PAL.paper);
          lm.emissive.set(PAL.paper);
          lm.emissiveIntensity = 0.35;
          lm.transparent = true;
          lm.opacity = 0.78;
        }
        lm.needsUpdate = true;
      }
      updateElevations();
    }

    function prepareTemplateMaterials(templateScene, isSolution) {
      const seen = new Set();
      templateScene.traverse((child) => {
        if (!child.isMesh || !child.material) return;
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        mats.forEach((mat) => {
          if (seen.has(mat)) return;
          seen.add(mat);
          if (mat.name === "LampGlow") {
            lampMats.push(mat);
          } else if (isSolution) {
            solutionBodyMats.push(mat);
          }
        });
      });
    }

    const customLayer = {
      id: "models-3d",
      type: "custom",
      renderingMode: "3d",

      onAdd(m, gl) {
        camera = new THREE.Camera();
        scene = new THREE.Scene();

        const hemi = new THREE.HemisphereLight(0xffffff, 0xb9e4e8, 1.7);
        scene.add(hemi);

        const dirLight = new THREE.DirectionalLight(0xffffff, 2.25);
        dirLight.position.set(0.5, 1.4, -1.0).normalize();
        scene.add(dirLight);

        scene.add(pjuGroup);
        scene.add(policeGroup);
        Object.values(teamGroups).forEach((g) => scene.add(g));

        renderer = new THREE.WebGLRenderer({
          canvas: m.getCanvas(),
          context: gl,
          antialias: true,
        });
        renderer.autoClear = false;
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        window.__threeLayerReady = true;

        const loader = new GLTFLoader();
        const names = [
          "pju_smart",
          "cctv_pole",
          "pos_pantau",
          "police_post",
          "halte_teduh",
          "pohon_peneduh",
          "posko_evakuasi",
          "hidran_darurat",
          "pos_damkar",
          "rs_rujukan",
        ].filter((n) => Boolean(window.MEDAN_MODELS[n]));

        names.forEach((name) => {
          const b64 = window.MEDAN_MODELS[name];
          const buf = b64ToArrayBuffer(b64);
          loader.parse(
            buf,
            "",
            (gltf) => {
              prepareTemplateMaterials(gltf.scene, name !== "police_post");
              loadedTemplates[name] = gltf.scene;
              window.__modelsLoaded += 1;

              if (window.__modelsLoaded === names.length) {
                rawData.solusi_pju_cctv.features.forEach((feat, idx) => {
                  const jenis = String(feat.properties.jenis_solusi || "");
                  const key = jenis.includes("Pos Pantau")
                    ? "pos_pantau"
                    : jenis.includes("CCTV")
                    ? "cctv_pole"
                    : "pju_smart";
                  const tpl = loadedTemplates[key];
                  if (!tpl) return;
                  const clone = tpl.clone(true);
                  const [lon, lat] = feat.geometry.coordinates;
                  const mc = maplibregl.MercatorCoordinate.fromLngLat([lon, lat], 0);
                  const x = (mc.x - originMc.x) / scaleUnit;
                  const z = (mc.y - originMc.y) / scaleUnit;
                  clone.position.set(x, 0, z);
                  clone.scale.setScalar(2.5);
                  clone.rotation.y = ((idx * 137.5) % 360) * (Math.PI / 180);
                  clone.userData = { stepOrder: Number(feat.properties.step_order || idx + 1) };
                  pjuGroup.add(clone);
                  placedItems.push({ obj: clone, lngLat: [lon, lat] });
                });

                rawData.polisi_eksisting.features.forEach((feat, idx) => {
                  const tpl = loadedTemplates.police_post;
                  if (!tpl) return;
                  const clone = tpl.clone(true);
                  const [lon, lat] = feat.geometry.coordinates;
                  const mc = maplibregl.MercatorCoordinate.fromLngLat([lon, lat], 0);
                  const x = (mc.x - originMc.x) / scaleUnit;
                  const z = (mc.y - originMc.y) / scaleUnit;
                  clone.position.set(x, 0, z);
                  clone.scale.setScalar(1.6);
                  clone.rotation.y = ((idx * 45) % 360) * (Math.PI / 180);
                  policeGroup.add(clone);
                  placedItems.push({ obj: clone, lngLat: [lon, lat] });
                });

                rebuildTeam3DInstances();
                window.__modelInstances = placedItems.length;
                syncState();
                m.triggerRepaint();
              }
            },
            (err) => {
              console.warn(`Gagal parse model ${name}:`, err);
            }
          );
        });
      },

      render(gl, args) {
        if (!renderer || !scene || !camera || state.currentProj === "globe") return;

        const anySim =
          state.simulationActive ||
          state.simUhiActive ||
          state.simRthActive ||
          state.simFloodSolutionActive ||
          state.floodStageM > 0.05 ||
          state.simDamkarActive;

        if (anySim && lampMats.length > 0) {
          const t = (performance.now() - animStart) * 0.001;
          const pulse = 1.2 + 0.65 * Math.sin(t * 2.8);
          for (const lm of lampMats) {
            lm.emissiveIntensity = pulse;
          }
          mapInstance.triggerRepaint();
        }

        const projArr =
          args && args.defaultProjectionData && args.defaultProjectionData.mainMatrix
            ? args.defaultProjectionData.mainMatrix
            : args;
        const m = new THREE.Matrix4().fromArray(projArr);
        camera.projectionMatrix = m.multiply(modelMatrix);

        renderer.resetState();
        renderer.render(scene, camera);
      },
    };

    mapInstance.addLayer(customLayer);
    return { syncState, updateElevations, rebuildTeam3DInstances };
  }

  function flyToKecamatan(kname) {
    if (!map) return;
    if (kname === "ALL") {
      map.flyTo({ ...PRESETS["overview-medan"], duration: 1100 });
      return;
    }
    const feat = rawData.batas_kecamatan_medan.features.find((f) => f.properties.nama_kec === kname);
    if (!feat) return;
    const coords = [];
    const extract = (c) => {
      if (typeof c[0] === "number") coords.push(c);
      else c.forEach(extract);
    };
    extract(feat.geometry.coordinates);
    const lons = coords.map((c) => c[0]);
    const lats = coords.map((c) => c[1]);
    const cx = (Math.min(...lons) + Math.max(...lons)) / 2;
    const cy = (Math.min(...lats) + Math.max(...lats)) / 2;
    map.flyTo({ center: [cx, cy], zoom: 13.8, pitch: 58, bearing: -18, duration: 1100 });
  }

  function toggleOrbit(enable) {
    state.autoOrbit = enable;
    const btnO = document.getElementById("btn-orbit");
    if (btnO) btnO.classList.toggle("is-active", enable);
    if (orbitFrameId) {
      cancelAnimationFrame(orbitFrameId);
      orbitFrameId = null;
    }
    if (enable) {
      const step = () => {
        if (!state.autoOrbit || !map) return;
        map.rotateTo(map.getBearing() + 0.14, { duration: 0 });
        orbitFrameId = requestAnimationFrame(step);
      };
      orbitFrameId = requestAnimationFrame(step);
    }
  }

  function toggleTerrain3D(forceOn = null) {
    state.terrain3D = forceOn !== null ? forceOn : !state.terrain3D;
    const btnT = document.getElementById("btn-terrain");
    if (btnT) btnT.classList.toggle("is-active", state.terrain3D);
    if (map) {
      map.setTerrain(state.terrain3D ? { source: "terrarium-dem", exaggeration: 3.2 } : null);
      if (state.terrain3D && state.basemap === "tematik") {
        setBasemap("3d");
        return;
      }
      if (state.terrain3D && state.currentProj !== "globe" && map.getPitch() < 55) {
        map.easeTo({ pitch: 65, duration: 700 });
      }
      if (threeLayerApi) threeLayerApi.updateElevations();
    }
    applyFiltersAndRedraw();
  }

  function getTotalSolutionCountForTab(tabKey) {
    if (tabKey === "orang5") return rawData.solusi_pju_cctv.features.length;
    if (tabKey === "orang1") return teamData.orang1_solusi.features.length;
    if (tabKey === "orang2") return teamData.orang2_solusi.features.length;
    if (tabKey === "orang3") return teamData.orang3_solusi.features.length;
    if (tabKey === "orang4") return teamData.orang4_solusi.features.length;
    return 100;
  }

  function setOutcomeForTab(tabKey, activeFlag) {
    if (tabKey === "orang5") state.simulationActive = activeFlag;
    else if (tabKey === "orang1") state.simUhiActive = activeFlag;
    else if (tabKey === "orang2") state.simRthActive = activeFlag;
    else if (tabKey === "orang3") state.simFloodSolutionActive = activeFlag;
    else if (tabKey === "orang4") state.simDamkarActive = activeFlag;
    else if (tabKey === "gabungan") {
      state.simulationActive = activeFlag;
      state.simUhiActive = activeFlag;
      state.simRthActive = activeFlag;
      state.simFloodSolutionActive = activeFlag;
      state.simDamkarActive = activeFlag;
    }
    syncSimButtonLabels();
  }

  function syncSimButtonLabels() {
    const upd = (btnId, lblId, flag, onTxt, offTxt) => {
      const b = document.getElementById(btnId);
      const l = document.getElementById(lblId);
      if (b) b.classList.toggle("is-active", flag);
      if (l) l.textContent = flag ? onTxt : offTxt;
    };
    upd("btn-simulasi-pju", "btn-sim-label", state.simulationActive, "Kembali ke Tahap 1 (Kondisi Sekarang)", "Jalankan Tahap 2 -> 3: Munculkan PJU Satu-Satu & Nyalakan");
    upd("btn-simulasi-uhi", "btn-sim-uhi-label", state.simUhiActive, "Kembali ke Tahap 1 (Kondisi Sekarang)", "Jalankan Tahap 2 -> 3: Munculkan Solusi & Hasil");
    upd("btn-simulasi-rth", "btn-sim-rth-label", state.simRthActive, "Kembali ke Tahap 1 (Kondisi Sekarang)", "Jalankan Tahap 2 -> 3: Munculkan 52 Taman & Hasil");
    upd("btn-simulasi-banjir-solusi", "btn-sim-banjir-solusi-label", state.simFloodSolutionActive, "Kembali ke Tahap 1 (Banjir Sebelum Solusi)", "Jalankan Tahap 2 -> 3: Kolam Retensi & Surutkan Banjir");
    upd("btn-simulasi-damkar", "btn-sim-damkar-label", state.simDamkarActive, "Kembali ke Tahap 1 (Kondisi Sekarang)", "Jalankan Tahap 2 -> 3: Pos Pemadam Baru & Hasil");
  }

  // 3-Stage Progressive Solution Engine:
  // Stage 1: Kondisi Sekarang (Only problem layers, 0 solutions, outcome off)
  // Stage 2: Titik Solusi Satu per Satu (Animate solution points appearing one by one on the map, outcome off)
  // Stage 3: Hasil & Rumus Solusi (All solutions visible + physical outcome active + formula highlighted)
  function setSimStage(stageNum, autoAdvanceToStage3 = false) {
    if (stepAnimTimer) {
      clearInterval(stepAnimTimer);
      stepAnimTimer = null;
    }
    const tabKey = state.activeSimTab;
    const totalSol = getTotalSolutionCountForTab(tabKey);
    state.solutionTotalCount = totalSol;
    const progBox = document.getElementById("stage-progress-box");
    const progTxt = document.getElementById("stage-progress-text");

    if (stageNum === 1) {
      state.simStage = 1;
      state.solutionStepLimit = 0;
      if (progBox) progBox.classList.add("hidden");
      setOutcomeForTab(tabKey, false);
      if (tabKey === "orang3") setFloodStage(state.floodStageM || 2.5, false);
      applyFiltersAndRedraw();
      return;
    }

    if (stageNum === 2) {
      state.simStage = 2;
      setOutcomeForTab(tabKey, false);
      state.solutionStepLimit = 1;
      if (progBox) progBox.classList.remove("hidden");
      if (progTxt) progTxt.textContent = `1 / ${totalSol}`;
      applyFiltersAndRedraw();

      const stepInc = Math.max(1, Math.ceil(totalSol / 28));
      stepAnimTimer = setInterval(() => {
        state.solutionStepLimit = Math.min(totalSol, state.solutionStepLimit + stepInc);
        if (progTxt) progTxt.textContent = `${state.solutionStepLimit} / ${totalSol}`;
        applyFiltersAndRedraw();

        if (state.solutionStepLimit >= totalSol) {
          clearInterval(stepAnimTimer);
          stepAnimTimer = null;
          if (autoAdvanceToStage3) {
            setTimeout(() => setSimStage(3, false), 450);
          }
        }
      }, 75);
      return;
    }

    // Stage 3: Hasil & Perhitungan Solusi
    state.simStage = 3;
    state.solutionStepLimit = 99999;
    if (progBox) {
      progBox.classList.remove("hidden");
      if (progTxt) progTxt.textContent = `${totalSol} / ${totalSol} Titik Solusi Terpasang (Hasil Aktif)`;
    }
    setOutcomeForTab(tabKey, true);
    if (tabKey === "orang3") {
      if (state.floodStageM <= 0.05) state.floodStageM = 2.5;
      setFloodStage(state.floodStageM, false);
    }
    pulseElement(`#calc-box-${tabKey}`);
    applyFiltersAndRedraw();
  }

  function runProgressiveSimulationForActiveTab() {
    if (state.simStage === 3) {
      setSimStage(1, false);
    } else {
      setSimStage(2, true);
    }
  }

  function switchSimTab(tabKey, exclusive = true) {
    if (stepAnimTimer) {
      clearInterval(stepAnimTimer);
      stepAnimTimer = null;
    }
    state.activeSimTab = tabKey;
    document.querySelectorAll(".topic-card").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-topic") === tabKey);
    });
    ["orang1", "orang2", "orang3", "orang4", "orang5", "gabungan"].forEach((k) => {
      const pane = document.getElementById(`sim-pane-${k}`);
      if (pane) pane.classList.toggle("hidden", k !== tabKey);
    });

    if (tabKey === "gabungan") {
      ["orang1", "orang2", "orang3", "orang4", "orang5"].forEach((k, idx) => {
        state.teamLayers[k] = true;
        const chk = document.getElementById(`lyr-team-${idx + 1}`);
        if (chk) chk.checked = true;
      });
    } else if (exclusive) {
      ["orang1", "orang2", "orang3", "orang4", "orang5"].forEach((k, idx) => {
        const isTarget = k === tabKey;
        state.teamLayers[k] = isTarget;
        const chk = document.getElementById(`lyr-team-${idx + 1}`);
        if (chk) chk.checked = isTarget;
      });
    }

    state.layers.water = (tabKey === "orang3");
    const chkWater = document.getElementById("lyr-water");
    if (chkWater) chkWater.checked = state.layers.water;

    if (tabKey === "orang3") {
      if (state.floodStageM <= 0.05) {
        setFloodStage(2.5, false);
      }
    } else if (tabKey !== "gabungan") {
      if (state.floodStageM > 0.05) {
        setFloodStage(0.0, false);
      }
    }

    // Check current tab's stage state
    const isTabSimActive =
      (tabKey === "orang1" && state.simUhiActive) ||
      (tabKey === "orang2" && state.simRthActive) ||
      (tabKey === "orang3" && state.simFloodSolutionActive) ||
      (tabKey === "orang4" && state.simDamkarActive) ||
      (tabKey === "orang5" && state.simulationActive);

    state.simStage = isTabSimActive ? 3 : 2;
    state.solutionStepLimit = 99999;
    const progBox = document.getElementById("stage-progress-box");
    if (progBox) progBox.classList.add("hidden");

    pulseElement(`#sim-pane-${tabKey}`);
    applyFiltersAndRedraw();
  }

  function setFloodStage(stageVal, redraw = true) {
    state.floodStageM = Math.max(0.0, Math.min(5.0, Number(stageVal)));
    const slider = document.getElementById("slider-flood-stage");
    const lbl = document.getElementById("val-flood-stage");
    if (slider) slider.value = String(state.floodStageM);
    if (lbl) {
      if (state.floodStageM <= 0.05) {
        lbl.textContent = "0,0 Meter (Air Normal)";
      } else if (state.simFloodSolutionActive) {
        const eff = getEffectiveFloodStage();
        lbl.textContent = `+${state.floodStageM.toFixed(1)}m -> Surut +${eff.toFixed(1)}m`;
      } else {
        lbl.textContent = `+${state.floodStageM.toFixed(1)} Meter (${state.floodStageM >= 3.0 ? "Banjir Besar" : "Luapan Sungai"})`;
      }
    }
    if (state.floodStageM > 0.05 && !state.teamLayers.orang3) {
      state.teamLayers.orang3 = true;
      const chk3 = document.getElementById("lyr-team-3");
      if (chk3) chk3.checked = true;
    }
    if (redraw) applyFiltersAndRedraw();
  }

  function animateFloodWave() {
    state.teamLayers.orang3 = true;
    state.subLayers.o3_air = true;
    const chkAir = document.getElementById("sub-o3-air");
    if (chkAir) chkAir.checked = true;
    const chk3 = document.getElementById("lyr-team-3");
    if (chk3) chk3.checked = true;
    if (floodTween && typeof floodTween.pause === "function") {
      floodTween.pause();
      floodTween = null;
    }
    const startSt = state.floodStageM >= 4.0 ? 0.5 : state.floodStageM;
    const targetStage = state.floodStageM >= 4.0 ? 2.5 : 4.5;
    const btnLbl = document.getElementById("btn-anim-banjir-label");
    if (btnLbl) btnLbl.textContent = "Air Naik...";

    if (window.anime && typeof window.anime.animate === "function") {
      const proxy = { st: startSt };
      floodTween = window.anime.animate(proxy, {
        st: targetStage,
        duration: 3200,
        ease: "inOutQuad",
        onUpdate: () => {
          const snapped = Math.round(proxy.st * 2) / 2;
          if (Math.abs(snapped - state.floodStageM) >= 0.45 || snapped === targetStage) {
            setFloodStage(snapped);
          }
        },
        onComplete: () => {
          setFloodStage(targetStage);
          if (btnLbl) btnLbl.textContent = "Animasi Air Naik";
        },
      });
    } else {
      setFloodStage(targetStage);
      if (btnLbl) btnLbl.textContent = "Animasi Air Naik";
    }
  }

  function toggleAllSimulations() {
    const allActive =
      state.simulationActive &&
      state.simUhiActive &&
      state.simRthActive &&
      state.simFloodSolutionActive &&
      state.simDamkarActive;
    const target = !allActive;
    state.simStage = target ? 3 : 1;
    state.solutionStepLimit = target ? 99999 : 0;
    setOutcomeForTab("gabungan", target);
    if (target && state.floodStageM <= 0.05) {
      state.floodStageM = 2.5;
    }
    const btn = document.getElementById("btn-simulasi-semua");
    const lbl = document.getElementById("btn-sim-semua-label");
    if (btn) btn.classList.toggle("is-active", target);
    if (lbl) {
      lbl.textContent = target
        ? "Matikan Seluruh Solusi 5 Fitur"
        : "Aktifkan Seluruh Solusi Sekaligus";
    }
    setFloodStage(state.floodStageM, true);
  }

  function populateEvidenceModal() {
    if (window.MEDAN_RASTER_OVERLAYS) {
      const v = window.MEDAN_RASTER_OVERLAYS.viirs;
      const d = window.MEDAN_RASTER_OVERLAYS.dem;
      const n = window.MEDAN_RASTER_OVERLAYS.ndvi;
      const l = window.MEDAN_RASTER_OVERLAYS.lst;
      const imgL = document.getElementById("proof-img-lst");
      const stL = document.getElementById("proof-stats-lst");
      if (imgL && stL && l) {
        imgL.src = l.dataUri;
        stL.innerHTML =
          `<div><strong>Ukuran Citra:</strong> ${l.stats.width} x ${l.stats.height} piksel (${l.stats.pixel_res_m})</div>` +
          `<div><strong>Suhu Permukaan:</strong> ${l.stats.min}°C s/d ${l.stats.max}°C (Rata-rata ${l.stats.mean}°C)</div>` +
          `<div><strong>Sumber Resmi:</strong> ${l.stats.source}</div>`;
      }
      const imgV = document.getElementById("proof-img-viirs");
      const stV = document.getElementById("proof-stats-viirs");
      if (imgV && stV && v) {
        imgV.src = v.dataUri;
        stV.innerHTML =
          `<div><strong>Ukuran Citra:</strong> ${v.stats.width} x ${v.stats.height} piksel (${v.stats.pixel_res_m})</div>` +
          `<div><strong>Rentang Cahaya:</strong> ${v.stats.min} s/d ${v.stats.max} (Rata-rata ${v.stats.mean})</div>` +
          `<div><strong>Sumber Resmi:</strong> ${v.stats.source}</div>`;
      }

      const imgN = document.getElementById("proof-img-ndvi");
      const stN = document.getElementById("proof-stats-ndvi");
      if (imgN && stN && n) {
        imgN.src = n.dataUri;
        stN.innerHTML =
          `<div><strong>Ukuran Citra:</strong> ${n.stats.width} x ${n.stats.height} piksel (${n.stats.pixel_res_m})</div>` +
          `<div><strong>Indeks Pohon:</strong> ${n.stats.min} s/d ${n.stats.max} (Rata-rata ${n.stats.mean})</div>` +
          `<div><strong>Sumber Resmi:</strong> ${n.stats.source}</div>`;
      }

      const imgD = document.getElementById("proof-img-dem");
      const stD = document.getElementById("proof-stats-dem");
      if (imgD && stD && d) {
        imgD.src = d.dataUri;
        stD.innerHTML =
          `<div><strong>Ukuran Peta:</strong> ${d.stats.width} x ${d.stats.height} piksel (${d.stats.pixel_res_m})</div>` +
          `<div><strong>Ketinggian Tanah:</strong> ${d.stats.min_m} mdpl s/d ${d.stats.max_m} mdpl (Rata-rata ${d.stats.mean_m} m)</div>` +
          `<div><strong>Sumber Resmi:</strong> ${d.stats.source}</div>`;
      }
    }

    const tbody = document.querySelector("#modal-corridors-table tbody");
    if (!tbody) return;
    tbody.innerHTML = rawData.koridor_rawan_begal.features
      .map((f, i) => {
        const p = f.properties;
        return `
          <tr>
            <td><strong>${p.nama_jalan}</strong></td>
            <td>${p.kecamatan}</td>
            <td>${p.panjang_km} km</td>
            <td>${p.viirs_min} / ${p.viirs_mean}</td>
            <td>${p.bukti_rilis || p.jenis_kerawanan}</td>
            <td><button type="button" class="btn btn-xs btn-secondary modal-fly-btn" data-idx="${i}">Lihat di Peta</button></td>
          </tr>
        `;
      })
      .join("");

    tbody.querySelectorAll(".modal-fly-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const feat = rawData.koridor_rawan_begal.features[Number(btn.getAttribute("data-idx"))];
        if (!feat) return;
        document.getElementById("modal-bukti").classList.add("hidden");
        switchSimTab("orang5", true);
        inspectCorridor(feat.properties);
        inspectOnRealSatellite(feat.properties.lon, feat.properties.lat, "night");
      });
    });
  }

  function initMap() {
    map = new maplibregl.Map({
      container: "map",
      style: buildLightBrutalStyle(),
      ...PRESETS["overview-medan"],
      minZoom: 2.0,
      maxZoom: 19,
      maxPitch: 75,
      antialias: true,
      attributionControl: false,
      preserveDrawingBuffer: true,
      canvasContextAttributes: { preserveDrawingBuffer: true },
    });
    window.__medanMap = map;

    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");

    map.on("load", () => {
      try {
        map.setLight({ anchor: "viewport", color: PAL.white, intensity: 0.42, position: [1.25, 210, 35] });
      } catch (err) {
        console.warn("setLight skipped:", err);
      }

      map.addSource("src-kec", { type: "geojson", data: rawData.batas_kecamatan_medan });
      map.addSource("src-hex", { type: "geojson", data: getFilteredHexFC() });
      map.addSource("src-water", { type: "geojson", data: rawData.sungai_fokus_osm });
      map.addSource("src-buildings", { type: "geojson", data: rawData.bangunan_fokus_3d });
      map.addSource("src-corridors", { type: "geojson", data: rawData.koridor_rawan_begal });
      map.addSource("src-patrol", { type: "geojson", data: rawData.solusi_rute_patroli });
      map.addSource("src-pju", { type: "geojson", data: getFilteredPjuFC() });
      map.addSource("src-pju-discs", { type: "geojson", data: buildPjuDiscsSource() });
      map.addSource("src-police", { type: "geojson", data: rawData.polisi_eksisting });

      if (window.MEDAN_RASTER_OVERLAYS) {
        const ov = window.MEDAN_RASTER_OVERLAYS;
        map.addSource("src-raw-viirs", { type: "image", url: ov.viirs.dataUri, coordinates: ov.viirs.bounds });
        if (ov.viirs.nightDataUri) {
          map.addSource("src-raw-night-mask", { type: "image", url: ov.viirs.nightDataUri, coordinates: ov.viirs.bounds });
          map.addLayer({
            id: "raw-night-mask-layer",
            type: "raster",
            source: "src-raw-night-mask",
            minzoom: 9.5,
            layout: { visibility: "none" },
            paint: { "raster-opacity": 0.92 },
          });
        }
        if (ov.viirsZones) {
          map.addSource("src-viirs-zones", { type: "geojson", data: ov.viirsZones });
          map.addLayer({
            id: "viirs-zone-outline",
            type: "line",
            source: "src-viirs-zones",
            filter: ["==", ["get", "feature_type"], "zone_poly"],
            layout: { visibility: "none" },
            paint: {
              "line-color": [
                "match",
                ["get", "zona_jenis"],
                "TERANG_KOTA",
                PAL.lamp,
                "GELAP_KRITIS",
                PAL.ice,
                PAL.teal,
              ],
              "line-width": 1.8,
              "line-dasharray": [3, 2],
              "line-opacity": 0.85,
            },
          });
        }
        if (ov.lst) {
          map.addSource("src-raw-lst", { type: "image", url: ov.lst.dataUri, coordinates: ov.lst.bounds });
          map.addLayer({
            id: "raw-lst-layer",
            type: "raster",
            source: "src-raw-lst",
            layout: { visibility: "none" },
            paint: { "raster-opacity": 0.88 },
          });
        }
        if (ov.ndvi) {
          map.addSource("src-raw-ndvi", { type: "image", url: ov.ndvi.dataUri, coordinates: ov.ndvi.bounds });
          map.addLayer({
            id: "raw-ndvi-layer",
            type: "raster",
            source: "src-raw-ndvi",
            layout: { visibility: "none" },
            paint: { "raster-opacity": 0.88 },
          });
        }
        map.addSource("src-raw-dem", { type: "image", url: ov.dem.dataUri, coordinates: ov.dem.bounds });
        map.addLayer({
          id: "raw-viirs-layer",
          type: "raster",
          source: "src-raw-viirs",
          layout: { visibility: "none" },
          paint: { "raster-opacity": 0.82 },
        });
        map.addLayer({
          id: "raw-dem-layer",
          type: "raster",
          source: "src-raw-dem",
          layout: { visibility: "none" },
          paint: { "raster-opacity": 0.82 },
        });
      }

      map.addSource("src-sat-spotlight", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("src-team-masalah", { type: "geojson", data: buildCombinedTeamFC("masalah") });
      map.addSource("src-team-solusi", { type: "geojson", data: buildCombinedTeamFC("solusi") });
      map.addSource("src-flood-contour", { type: "geojson", data: buildActiveFloodContourFC() });
      map.addSource("src-damkar-isochrone", { type: "geojson", data: buildActiveIsochroneFC() });

      // 1. Kecamatan borders (all 21 Kecamatan)
      map.addLayer({
        id: "kec-outline",
        type: "line",
        source: "src-kec",
        paint: {
          "line-color": PAL.ink,
          "line-width": 1.6,
          "line-dasharray": [3, 2],
          "line-opacity": 0.65,
        },
      });

      // 2. Hexagon VIIRS (Flat & 3D Towers)
      map.addLayer({
        id: "hex-flat-fill",
        type: "fill",
        source: "src-hex",
        paint: {
          "fill-color": ["interpolate", ["linear"], ["get", "risk_score"], 20, PAL.ice, 45, PAL.teal, 70, PAL.ink],
          "fill-opacity": 0.36,
        },
      });

      map.addLayer({
        id: "hex-flat-line",
        type: "line",
        source: "src-hex",
        paint: { "line-color": PAL.ink, "line-width": 0.6, "line-opacity": 0.25 },
      });

      map.addLayer({
        id: "hex-3d-extrusion",
        type: "fill-extrusion",
        source: "src-hex",
        layout: { visibility: "none" },
        paint: {
          "fill-extrusion-color": ["interpolate", ["linear"], ["get", "risk_score"], 20, PAL.ice, 45, PAL.teal, 70, PAL.ink],
          "fill-extrusion-height": ["*", ["get", "risk_score"], 5.5],
          "fill-extrusion-opacity": 0.84,
          "fill-extrusion-vertical-gradient": true,
        },
      });

      // 2.5 Integrated Team Problem Grids
      map.addLayer({
        id: "team-masalah-fill",
        type: "fill",
        source: "src-team-masalah",
        layout: { visibility: "none" },
        paint: {
          "fill-color": PAL.teal,
          "fill-opacity": 0.66,
        },
      });
      map.addLayer({
        id: "team-masalah-line",
        type: "line",
        source: "src-team-masalah",
        layout: { visibility: "none" },
        paint: { "line-color": PAL.ink, "line-width": 0.8, "line-opacity": 0.50 },
      });
      map.addLayer({
        id: "team-masalah-3d",
        type: "fill-extrusion",
        source: "src-team-masalah",
        layout: { visibility: "none" },
        paint: {
          "fill-extrusion-color": PAL.teal,
          "fill-extrusion-height": ["*", ["coalesce", ["get", "skor_masalah"], 40], 4.8],
          "fill-extrusion-opacity": 0.82,
          "fill-extrusion-vertical-gradient": true,
        },
      });

      // 2.6 Peter's ORS Damkar Isochrones
      map.addLayer({
        id: "damkar-isochrone-fill",
        type: "fill",
        source: "src-damkar-isochrone",
        layout: { visibility: "none" },
        paint: {
          "fill-color": ["match", ["get", "aa_mins"], 5, "#22c55e", "#15803d"],
          "fill-opacity": 0.34,
        },
      });
      map.addLayer({
        id: "damkar-isochrone-line",
        type: "line",
        source: "src-damkar-isochrone",
        layout: { visibility: "none" },
        paint: {
          "line-color": ["match", ["get", "aa_mins"], 5, "#16a34a", "#14532d"],
          "line-width": 2.4,
          "line-dasharray": [3, 1.5],
        },
      });

      // 2.7 Real Topographic DEM SRTM Flood Water Surface
      map.addLayer({
        id: "flood-contour-3d",
        type: "fill-extrusion",
        source: "src-flood-contour",
        layout: { visibility: "none" },
        paint: {
          "fill-extrusion-color": [
            "interpolate",
            ["linear"],
            ["get", "stage_m"],
            0.5,
            "#38bdf8",
            2.0,
            "#0284c7",
            4.0,
            "#0369a1",
          ],
          "fill-extrusion-height": 4.0,
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.82,
          "fill-extrusion-vertical-gradient": true,
        },
      });
      map.addLayer({
        id: "flood-contour-outline",
        type: "line",
        source: "src-flood-contour",
        layout: { visibility: "none" },
        paint: {
          "line-color": "#e0f2fe",
          "line-width": 2.2,
          "line-opacity": 0.95,
        },
      });

      // 2.8 Team Solution Polygons (Kolam Retensi Banjir & Taman RTH Polygons)
      map.addLayer({
        id: "team-solusi-polygons-fill",
        type: "fill",
        source: "src-team-solusi",
        filter: ["==", ["geometry-type"], "Polygon"],
        layout: { visibility: "none" },
        paint: {
          "fill-color": [
            "match",
            ["get", "sub_tipe"],
            "kolam_retensi",
            "#0ea5e9",
            "#22c55e",
          ],
          "fill-opacity": 0.72,
        },
      });
      map.addLayer({
        id: "team-solusi-polygons-line",
        type: "line",
        source: "src-team-solusi",
        filter: ["==", ["geometry-type"], "Polygon"],
        layout: { visibility: "none" },
        paint: {
          "line-color": PAL.ink,
          "line-width": 2.2,
        },
      });

      // 3. PJU Illumination Discs
      map.addLayer({
        id: "pju-illumination-fill",
        type: "fill",
        source: "src-pju-discs",
        layout: { visibility: "none" },
        paint: { "fill-color": PAL.lamp, "fill-opacity": 0.22 },
      });
      map.addLayer({
        id: "pju-illumination-ring",
        type: "line",
        source: "src-pju-discs",
        layout: { visibility: "none" },
        paint: { "line-color": PAL.lamp, "line-width": 2.2 },
      });
      map.addLayer({
        id: "pju-illumination-outline",
        type: "line",
        source: "src-pju-discs",
        layout: { visibility: "none" },
        paint: { "line-color": PAL.ink, "line-width": 1.0, "line-opacity": 0.4 },
      });

      // 4. Rivers (All 21 Kecamatan)
      map.addLayer({ id: "water-glow", type: "line", source: "src-water", paint: { "line-color": "#7dd3fc", "line-width": 6.5, "line-opacity": 0.75 } });
      map.addLayer({ id: "water-core", type: "line", source: "src-water", paint: { "line-color": "#0284c7", "line-width": 2.4, "line-opacity": 0.95 } });

      // 5. Crime Corridors
      map.addLayer({ id: "corridors-casing", type: "line", source: "src-corridors", paint: { "line-color": PAL.white, "line-width": 8 } });
      map.addLayer({ id: "corridors-core", type: "line", source: "src-corridors", paint: { "line-color": PAL.ink, "line-width": 3.5 } });
      map.addLayer({ id: "corridors-dash", type: "line", source: "src-corridors", paint: { "line-color": PAL.ice, "line-width": 1.0, "line-dasharray": [1, 3] } });

      // 6. Patrol Routes
      map.addLayer({ id: "patrol-casing", type: "line", source: "src-patrol", paint: { "line-color": PAL.white, "line-width": 7 } });
      map.addLayer({ id: "patrol-core", type: "line", source: "src-patrol", paint: { "line-color": PAL.teal, "line-width": 3.0, "line-dasharray": [2, 1.5] } });

      // 6.5 Team Solution Lines
      map.addLayer({
        id: "team-solusi-lines-casing",
        type: "line",
        source: "src-team-solusi",
        filter: ["==", ["geometry-type"], "LineString"],
        layout: { visibility: "none" },
        paint: { "line-color": PAL.ink, "line-width": 8.0 },
      });
      map.addLayer({
        id: "team-solusi-lines",
        type: "line",
        source: "src-team-solusi",
        filter: ["==", ["geometry-type"], "LineString"],
        layout: { visibility: "none" },
        paint: {
          "line-color": [
            "match",
            ["get", "sub_tipe"],
            "jalur_evakuasi",
            "#f97316",
            "jalur_evakuasi_rs",
            "#ef4444",
            "#10b981",
          ],
          "line-width": 4.8,
          "line-dasharray": [2, 1],
        },
      });

      // 7. City-wide 3D Buildings
      map.addLayer({
        id: "buildings-citywide-3d",
        type: "fill-extrusion",
        source: "openfreemap-planet",
        "source-layer": "building",
        minzoom: 13,
        paint: {
          "fill-extrusion-color": [
            "step",
            ["coalesce", ["get", "render_height"], ["get", "height"], 8],
            PAL.teal,
            14,
            PAL.ink,
          ],
          "fill-extrusion-height": ["coalesce", ["get", "render_height"], 8],
          "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
          "fill-extrusion-opacity": 0.65,
          "fill-extrusion-vertical-gradient": true,
        },
      });

      // 8. Scored 81,584 3D Buildings across all 21 Kecamatan
      map.addLayer({
        id: "buildings-shadow",
        type: "fill",
        source: "src-buildings",
        paint: {
          "fill-color": PAL.ink,
          "fill-opacity": 0.22,
          "fill-translate": [4, 4],
          "fill-translate-anchor": "viewport",
        },
      });

      map.addLayer({
        id: "buildings-3d",
        type: "fill-extrusion",
        source: "src-buildings",
        paint: {
          "fill-extrusion-color": ["match", ["get", "status_rawan"], "Tinggi", PAL.ink, "Sedang", PAL.teal, PAL.ice],
          "fill-extrusion-height": ["get", "height_m"],
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.90,
          "fill-extrusion-vertical-gradient": true,
        },
      });

      // 9. Point Click Targets
      map.addLayer({
        id: "pju-points",
        type: "circle",
        source: "src-pju",
        paint: {
          "circle-radius": 5.5,
          "circle-color": PAL.lamp,
          "circle-stroke-width": 2.5,
          "circle-stroke-color": PAL.ink,
          "circle-pitch-alignment": "map",
        },
      });

      map.addLayer({
        id: "police-points",
        type: "circle",
        source: "src-police",
        paint: {
          "circle-radius": 7.5,
          "circle-color": PAL.teal,
          "circle-stroke-width": 3,
          "circle-stroke-color": PAL.ink,
          "circle-pitch-alignment": "map",
        },
      });

      map.addLayer({
        id: "team-solusi-points",
        type: "circle",
        source: "src-team-solusi",
        filter: ["all", ["==", ["geometry-type"], "Point"], ["!=", ["get", "sub_tipe"], "pohon_3d_koridor"]],
        layout: { visibility: "none" },
        paint: {
          "circle-radius": [
            "case",
            ["==", ["get", "sub_tipe"], "titik_banjir_visel"],
            ["+", 9, ["*", ["coalesce", ["get", "kedalaman_air_m"], 1.2], 4.2]],
            ["==", ["get", "sub_tipe"], "rs_rujukan_banjir"],
            8.5,
            ["==", ["get", "sub_tipe"], "pohon_3d_koridor"],
            4.8,
            ["==", ["get", "sub_tipe"], "pasar_medan"],
            6.5,
            7.8,
          ],
          "circle-color": [
            "match",
            ["get", "sub_tipe"],
            "titik_banjir_visel",
            "#3182bd",
            "rs_rujukan_banjir",
            ["case", ["in", "terdampak", ["downcase", ["coalesce", ["get", "status_banjir"], ""]]], "#ff7f00", "#e31a1c"],
            "halte_teduh",
            "#06b6d4",
            "taman_rth",
            "#22c55e",
            "posko_evakuasi",
            "#10b981",
            "pos_damkar_solusi",
            "#dc2626",
            "pos_damkar_eksisting",
            "#991b1b",
            "hidran_darurat",
            "#3b82f6",
            "pasar_medan",
            "#eab308",
            PAL.ice,
          ],
          "circle-stroke-width": 2.5,
          "circle-stroke-color": PAL.ink,
          "circle-pitch-alignment": "map",
        },
      });

      map.addLayer({
        id: "sat-spotlight-ring",
        type: "line",
        source: "src-sat-spotlight",
        filter: ["==", ["get", "kind"], "ring"],
        paint: { "line-color": PAL.lamp, "line-width": 3.0 },
      });
      map.addLayer({
        id: "sat-spotlight-dot",
        type: "circle",
        source: "src-sat-spotlight",
        filter: ["==", ["get", "kind"], "dot"],
        paint: { "circle-radius": 6, "circle-color": PAL.lamp, "circle-stroke-width": 2.5, "circle-stroke-color": PAL.ink },
      });

      // 10. Mount three.js GLB Custom Layer (all 10 3D GLB types)
      const mountThree = () => {
        if (!threeLayerApi && window.THREE && window.GLTFLoader) {
          threeLayerApi = createThreeCustomLayer(map);
          applyFiltersAndRedraw();
        }
      };
      if (window.THREE && window.GLTFLoader) {
        mountThree();
      } else {
        window.addEventListener("three-ready", mountThree, { once: true });
      }

      // Click handlers
      map.on("click", "team-solusi-points", (e) => {
        if (e.features && e.features[0]) inspectTeamFeature(e.features[0].properties, e.lngLat);
      });
      map.on("click", "team-solusi-lines", (e) => {
        if (e.features && e.features[0]) inspectTeamFeature(e.features[0].properties, e.lngLat);
      });
      map.on("click", "team-solusi-polygons-fill", (e) => {
        if (e.features && e.features[0]) inspectTeamFeature(e.features[0].properties, e.lngLat);
      });
      map.on("click", "flood-contour-3d", (e) => {
        if (e.features && e.features[0]) inspectTeamFeature(e.features[0].properties, e.lngLat);
      });
      map.on("click", "damkar-isochrone-fill", (e) => {
        if (e.features && e.features[0]) inspectTeamFeature(e.features[0].properties, e.lngLat);
      });
      map.on("click", "water-core", (e) => {
        if (e.features && e.features[0]) inspectRiver(e.features[0].properties, e.lngLat);
      });
      map.on("click", "buildings-3d", (e) => {
        if (e.features && e.features[0]) inspectBuilding(e.features[0].properties, e.lngLat);
      });
      map.on("click", "buildings-citywide-3d", (e) => {
        const hits = map.queryRenderedFeatures(e.point, { layers: ["buildings-3d"] });
        if (hits.length > 0) return;
        if (e.features && e.features[0]) inspectCitywideBuilding(e.features[0].properties, e.lngLat);
      });
      map.on("click", "pju-points", (e) => {
        if (e.features && e.features[0]) inspectPJU(e.features[0].properties, e.features[0].geometry.coordinates);
      });
      map.on("click", "police-points", (e) => {
        if (e.features && e.features[0]) inspectPolice(e.features[0].properties, e.features[0].geometry.coordinates);
      });
      map.on("click", "corridors-core", (e) => {
        if (e.features && e.features[0]) inspectCorridor(e.features[0].properties, e.lngLat);
      });
      map.on("click", "patrol-core", (e) => {
        if (e.features && e.features[0]) inspectPatrol(e.features[0].properties, e.lngLat);
      });
      map.on("click", "team-masalah-fill", (e) => {
        const bldHits = map.queryRenderedFeatures(e.point, {
          layers: ["buildings-3d", "team-solusi-points", "team-solusi-lines", "team-solusi-polygons-fill"],
        });
        if (bldHits.length > 0) return;
        if (e.features && e.features[0]) inspectTeamFeature(e.features[0].properties, e.lngLat);
      });
      map.on("click", "team-masalah-3d", (e) => {
        if (e.features && e.features[0]) inspectTeamFeature(e.features[0].properties, e.lngLat);
      });
      map.on("click", "hex-flat-fill", (e) => {
        if (e.features && e.features[0]) inspectHex(e.features[0].properties, e.lngLat);
      });
      map.on("click", "hex-3d-extrusion", (e) => {
        if (e.features && e.features[0]) inspectHex(e.features[0].properties, e.lngLat);
      });

      [
        "buildings-3d",
        "buildings-citywide-3d",
        "pju-points",
        "police-points",
        "corridors-core",
        "patrol-core",
        "water-core",
        "hex-flat-fill",
        "hex-3d-extrusion",
        "team-masalah-fill",
        "team-masalah-3d",
        "team-solusi-lines",
        "team-solusi-points",
        "team-solusi-polygons-fill",
        "flood-contour-3d",
        "damkar-isochrone-fill",
      ].forEach((lid) => {
        map.on("mouseenter", lid, () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", lid, () => (map.getCanvas().style.cursor = ""));
      });

      syncProjectionByZoom();
      applyFiltersAndRedraw();
    });

    map.on("zoom", syncProjectionByZoom);

    map.on("idle", () => {
      if (threeLayerApi && state.terrain3D) {
        threeLayerApi.updateElevations();
      }
    });

    map.on("move", () => {
      const p = map.getPitch().toFixed(0);
      const z = map.getZoom().toFixed(1);
      const tEl = document.getElementById("telemetry-text");
      if (tEl) tEl.textContent = `${p}° | Z ${z}`;
    });

    map.on("mousemove", (e) => {
      const cEl = document.getElementById("cursor-coords");
      if (cEl) {
        cEl.textContent = `KOORDINAT: ${e.lngLat.lng.toFixed(4)} BT, ${e.lngLat.lat.toFixed(4)} LU · KOTA MEDAN (21 KECAMATAN)`;
      }
    });

    map.on("mousedown", () => {
      if (state.autoOrbit) toggleOrbit(false);
    });
  }

  function bindUIEvents() {
    // Navbar camera presets
    document.querySelectorAll(".nav-link").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-link").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const key = btn.getAttribute("data-preset");
        const p = PRESETS[key];
        if (p && map) {
          const willBeGlobe = p.zoom < 7.5;
          const crossingProj =
            (willBeGlobe && state.currentProj !== "globe") ||
            (!willBeGlobe && state.currentProj === "globe");
          if (crossingProj || willBeGlobe) {
            map.setPadding(willBeGlobe ? { top: 16, bottom: 120, left: 0, right: 0 } : { top: 0, bottom: 0, left: 0, right: 0 });
            map.jumpTo(p);
            syncProjectionByZoom();
            applyFiltersAndRedraw();
          } else {
            map.flyTo({ ...p, duration: 1100 });
          }
        }
      });
    });

    // Feature Topic Cards (.topic-card[data-topic])
    document.querySelectorAll(".topic-card").forEach((btn) => {
      btn.addEventListener("click", () => {
        switchSimTab(btn.getAttribute("data-topic"), true);
      });
    });

    // 3-Stage Progressive Solution Stepper Buttons (Tahap 1, Tahap 2, Tahap 3)
    document.querySelectorAll(".stage-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const stNum = Number(btn.getAttribute("data-stage"));
        setSimStage(stNum, false);
      });
    });

    const btnOrbit = document.getElementById("btn-orbit");
    if (btnOrbit) btnOrbit.addEventListener("click", () => toggleOrbit(!state.autoOrbit));
    const btnTerrain = document.getElementById("btn-terrain");
    if (btnTerrain) btnTerrain.addEventListener("click", () => toggleTerrain3D());

    // Progressive Stage 2 -> 3 triggers for each feature's main simulation button
    ["btn-simulasi-pju", "btn-simulasi-uhi", "btn-simulasi-rth", "btn-simulasi-banjir-solusi", "btn-simulasi-damkar"].forEach((id) => {
      const b = document.getElementById(id);
      if (b) b.addEventListener("click", runProgressiveSimulationForActiveTab);
    });

    const btnSimAll = document.getElementById("btn-simulasi-semua");
    if (btnSimAll) btnSimAll.addEventListener("click", toggleAllSimulations);

    // Separable Sub-Layer Checkboxes per Feature
    const subLayerBindings = {
      "sub-o1-hex": "o1_hex",
      "sub-o1-jalur": "o1_jalur",
      "sub-o1-halte": "o1_halte",
      "sub-o1-sat": "o1_sat",
      "sub-o2-hex": "o2_hex",
      "sub-o2-taman": "o2_taman",
      "sub-o2-sat": "o2_sat",
      "sub-o3-titik": "o3_titik",
      "sub-o3-rs": "o3_rs",
      "sub-o3-air": "o3_air",
      "sub-o3-solusi": "o3_solusi",
      "sub-o3-rute": "o3_rute",
      "sub-o3-hex": "o3_hex",
      "sub-o3-sat": "o3_sat",
      "sub-o4-hex": "o4_hex",
      "sub-o4-iso": "o4_iso",
      "sub-o4-eks": "o4_eks",
      "sub-o4-sol": "o4_sol",
      "sub-o5-hex": "o5_hex",
      "sub-o5-koridor": "o5_koridor",
      "sub-o5-polisi": "o5_polisi",
      "sub-o5-pju": "o5_pju",
      "sub-o5-patroli": "o5_patroli",
      "sub-o5-sat": "o5_sat",
    };
    Object.entries(subLayerBindings).forEach(([elId, key]) => {
      const el = document.getElementById(elId);
      if (el) {
        el.addEventListener("change", (e) => {
          state.subLayers[key] = e.target.checked;
          // If checking a solution sub-layer while in Stage 1, bump to Stage 2 so it is visible
          if (e.target.checked && state.simStage === 1 && ["o1_jalur", "o1_halte", "o2_taman", "o3_solusi", "o4_sol", "o5_pju", "o5_patroli"].includes(key)) {
            state.simStage = 2;
            state.solutionStepLimit = 99999;
          }
          applyFiltersAndRedraw();
        });
      }
    });

    // William (Suhu Panas & Pohon Peneduh) slider
    const sldUhi = document.getElementById("slider-uhi-filter");
    if (sldUhi) {
      sldUhi.addEventListener("input", (e) => {
        state.uhiMinTemp = Number(e.target.value);
        const vEl = document.getElementById("val-uhi-filter");
        if (vEl) {
          vEl.textContent =
            state.uhiMinTemp <= 28.0 ? "Semua Suhu (>= 28°C)" : `Suhu >= ${state.uhiMinTemp.toFixed(1)} °C`;
        }
        state.teamLayers.orang1 = true;
        const chk1 = document.getElementById("lyr-team-1");
        if (chk1) chk1.checked = true;
        applyFiltersAndRedraw();
      });
    }

    // Jordan (Kerapatan Pohon & Taman Hijau) controls
    document.querySelectorAll('.seg-btn[data-jmode]').forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll('.seg-btn[data-jmode]').forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.jordanColorMode = btn.getAttribute("data-jmode");
        state.teamLayers.orang2 = true;
        const chk2 = document.getElementById("lyr-team-2");
        if (chk2) chk2.checked = true;
        applyFiltersAndRedraw();
      });
    });
    const sldNdvi = document.getElementById("slider-ndvi-filter");
    if (sldNdvi) {
      sldNdvi.addEventListener("input", (e) => {
        state.ndviMinFilter = Number(e.target.value);
        const vEl = document.getElementById("val-ndvi-filter");
        if (vEl) {
          vEl.textContent = state.ndviMinFilter <= -0.19 ? "Tampilkan Semua" : `Indeks >= ${state.ndviMinFilter.toFixed(2)}`;
        }
        state.teamLayers.orang2 = true;
        const chk2 = document.getElementById("lyr-team-2");
        if (chk2) chk2.checked = true;
        applyFiltersAndRedraw();
      });
    }

    // Visel (Luapan Banjir Sungai, RS Rujukan & Evakuasi) controls
    const sldFlood = document.getElementById("slider-flood-stage");
    if (sldFlood) {
      sldFlood.addEventListener("input", (e) => {
        setFloodStage(Number(e.target.value));
      });
    }
    const btnAnimBanjir = document.getElementById("btn-anim-banjir");
    if (btnAnimBanjir) btnAnimBanjir.addEventListener("click", animateFloodWave);
    const btnResetBanjir = document.getElementById("btn-reset-banjir");
    if (btnResetBanjir) {
      btnResetBanjir.addEventListener("click", () => {
        if (floodTween && typeof floodTween.pause === "function") floodTween.pause();
        setFloodStage(0.0);
      });
    }

    // Peter (Jangkauan Pemadam Kebakaran & Hidran) slider
    const sldDamkar = document.getElementById("slider-damkar-filter");
    if (sldDamkar) {
      sldDamkar.addEventListener("input", (e) => {
        state.damkarMinBld = Number(e.target.value);
        const vEl = document.getElementById("val-damkar-filter");
        if (vEl) {
          vEl.textContent = state.damkarMinBld <= 0 ? "Semua Area" : `>= ${state.damkarMinBld} Rumah/Petak`;
        }
        state.teamLayers.orang4 = true;
        const chk4 = document.getElementById("lyr-team-4");
        if (chk4) chk4.checked = true;
        applyFiltersAndRedraw();
      });
    }

    // Toggle all 5 features button
    const btnToggleAllTeam = document.getElementById("btn-toggle-all-team");
    if (btnToggleAllTeam) {
      btnToggleAllTeam.addEventListener("click", () => {
        const allOn = ["orang1", "orang2", "orang3", "orang4", "orang5"].every((k) => state.teamLayers[k]);
        const target = !allOn;
        ["orang1", "orang2", "orang3", "orang4", "orang5"].forEach((k, idx) => {
          state.teamLayers[k] = target;
          const chk = document.getElementById(`lyr-team-${idx + 1}`);
          if (chk) chk.checked = target;
        });
        if (target) {
          state.activeSimTab = "gabungan";
          document.querySelectorAll(".topic-card").forEach((b) => {
            b.classList.toggle("active", b.getAttribute("data-topic") === "gabungan");
          });
          ["orang1", "orang2", "orang3", "orang4", "orang5", "gabungan"].forEach((k) => {
            const pane = document.getElementById(`sim-pane-${k}`);
            if (pane) pane.classList.toggle("hidden", k !== "gabungan");
          });
        }
        applyFiltersAndRedraw();
      });
    }

    // Basemap switcher & opacity
    document.querySelectorAll(".base-btn").forEach((btn) => {
      btn.addEventListener("click", () => setBasemap(btn.getAttribute("data-basemap")));
    });
    const sldOp = document.getElementById("slider-opacity");
    if (sldOp) {
      sldOp.addEventListener("input", (e) => {
        setDataOpacity(Number(e.target.value) / 100);
      });
    }

    const lyrMap = {
      "lyr-buildings": "buildings",
      "lyr-hex": "hex",
      "lyr-models-3d": "models3d",
      "lyr-water": "water",
      "lyr-kec": "kec",
    };
    Object.entries(lyrMap).forEach(([elId, key]) => {
      const el = document.getElementById(elId);
      if (el) {
        el.addEventListener("change", (e) => {
          state.layers[key] = e.target.checked;
          applyFiltersAndRedraw();
        });
      }
    });

    // Equal ON/OFF switches for all 5 features (lyr-team-1 .. lyr-team-5)
    ["orang1", "orang2", "orang3", "orang4", "orang5"].forEach((memberKey, idx) => {
      const el = document.getElementById(`lyr-team-${idx + 1}`);
      if (el) {
        el.addEventListener("change", (e) => {
          state.teamLayers[memberKey] = e.target.checked;
          if (e.target.checked) {
            state.activeSimTab = memberKey;
            document.querySelectorAll(".topic-card").forEach((b) => {
              b.classList.toggle("active", b.getAttribute("data-topic") === memberKey);
            });
            ["orang1", "orang2", "orang3", "orang4", "orang5", "gabungan"].forEach((k) => {
              const pane = document.getElementById(`sim-pane-${k}`);
              if (pane) pane.classList.toggle("hidden", k !== memberKey);
            });
            if (memberKey === "orang3" && state.floodStageM <= 0.05) {
              setFloodStage(2.5, false);
            }
          } else if (memberKey === "orang3") {
            setFloodStage(0.0, false);
          }
          applyFiltersAndRedraw();
        });
      }
    });

    document.querySelectorAll('.seg-btn[data-hexmode]').forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll('.seg-btn[data-hexmode]').forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.hexMode = btn.getAttribute("data-hexmode");
        if (state.hexMode === "3d" && map && map.getPitch() < 45) {
          map.easeTo({ pitch: 60, duration: 600 });
        }
        applyFiltersAndRedraw();
      });
    });

    document.querySelectorAll('.seg-btn[data-projmode]').forEach((btn) => {
      btn.addEventListener("click", () => {
        setProjectionMode(btn.getAttribute("data-projmode"));
      });
    });

    const selKec = document.getElementById("filter-kecamatan");
    if (selKec) {
      selKec.addEventListener("change", (e) => {
        state.filterKec = e.target.value;
        flyToKecamatan(state.filterKec);
        applyFiltersAndRedraw();
      });
    }

    document.querySelectorAll(".collapse-btn[data-target]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-target");
        const body = document.getElementById(targetId);
        if (body) body.classList.toggle("collapsed");
      });
    });

    const modal = document.getElementById("modal-bukti");
    const btnBukti = document.getElementById("btn-bukti");
    if (btnBukti && modal) {
      btnBukti.addEventListener("click", () => modal.classList.remove("hidden"));
    }
    const btnCloseModal = document.getElementById("btn-close-modal");
    if (btnCloseModal && modal) {
      btnCloseModal.addEventListener("click", () => modal.classList.add("hidden"));
    }
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
      });
    }

    const btnModalLst = document.getElementById("btn-modal-show-lst");
    if (btnModalLst) {
      btnModalLst.addEventListener("click", () => {
        if (modal) modal.classList.add("hidden");
        switchSimTab("orang1", true);
        state.subLayers.o1_sat = true;
        const chk = document.getElementById("sub-o1-sat");
        if (chk) chk.checked = true;
        applyFiltersAndRedraw();
      });
    }
    const btnModalViirs = document.getElementById("btn-modal-show-viirs");
    if (btnModalViirs) {
      btnModalViirs.addEventListener("click", () => {
        if (modal) modal.classList.add("hidden");
        switchSimTab("orang5", true);
        state.subLayers.o5_sat = true;
        const chk = document.getElementById("sub-o5-sat");
        if (chk) chk.checked = true;
        applyFiltersAndRedraw();
      });
    }
    const btnModalNdvi = document.getElementById("btn-modal-show-ndvi");
    if (btnModalNdvi) {
      btnModalNdvi.addEventListener("click", () => {
        if (modal) modal.classList.add("hidden");
        switchSimTab("orang2", true);
        state.subLayers.o2_sat = true;
        const chk = document.getElementById("sub-o2-sat");
        if (chk) chk.checked = true;
        applyFiltersAndRedraw();
      });
    }
    const btnModalDem = document.getElementById("btn-modal-show-dem");
    if (btnModalDem) {
      btnModalDem.addEventListener("click", () => {
        if (modal) modal.classList.add("hidden");
        switchSimTab("orang3", true);
        state.subLayers.o3_sat = true;
        const chk = document.getElementById("sub-o3-sat");
        if (chk) chk.checked = true;
        applyFiltersAndRedraw();
      });
    }
  }

  async function boot() {
    initIcons();
    try {
      await loadAllGeoJSON();
      populateFilters();
      populateEvidenceModal();
      bindUIEvents();
      updateKPIs();
      initMap();
    } catch (err) {
      console.error("Gagal memuat aplikasi WebGIS:", err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
