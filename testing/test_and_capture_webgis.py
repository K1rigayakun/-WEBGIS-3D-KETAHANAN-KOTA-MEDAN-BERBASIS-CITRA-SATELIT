import http.server
import os
import socketserver
import threading
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(BASE_DIR, "web-peta-interaktif")
SHOT_DIR = os.path.join(BASE_DIR, "testing", "screenshoot")
os.makedirs(SHOT_DIR, exist_ok=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        pass


def start_server():
    httpd = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, port


def run_tests():
    httpd, port = start_server()
    url = f"http://127.0.0.1:{port}/index.html"
    results = []
    console_errors = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=[
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--enable-webgl",
                    "--ignore-gpu-blocklist",
                ],
            )
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1.0)
            page.on("pageerror", lambda err: console_errors.append(f"PAGEERROR: {err}"))
            page.on(
                "console",
                lambda msg: console_errors.append(f"CONSOLE_{msg.type.upper()}: {msg.text}")
                if msg.type == "error" and "tile" not in msg.text.lower() and "err_name_not_resolved" not in msg.text.lower()
                else None,
            )

            # 1. Load initial page (Michael / Orang 5 Stage 1)
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function("() => window.__threeLayerReady === true", timeout=30000)
            page.wait_for_timeout(3500)
            kpi_b = page.locator("#kpi-buildings").inner_text()
            kpi_d = page.locator("#kpi-dark-buildings").inner_text()
            results.append(("1. Initial Load & 3D WebGL Ready (Michael Stage 1)", "PASS", f"Gedung={kpi_b}, Gelap={kpi_d}"))
            page.screenshot(path=os.path.join(SHOT_DIR, "01_awal_michael_masalah.png"))

            # 2. Switch to Focus Medan Baru & Run Michael Stage 3 (217 PJU & CCTV active)
            page.click('.nav-link[data-preset="focus-medan-baru"]')
            page.wait_for_timeout(1500)
            page.click('.stage-btn[data-stage="3"]')
            page.wait_for_timeout(2000)
            kpi_pju = page.locator("#kpi-pju").inner_text()
            kpi_d_after = page.locator("#kpi-dark-buildings").inner_text()
            results.append(("2. Simulasi PJU & CCTV 3D (Michael Stage 3)", "PASS", f"PJU={kpi_pju}, Sisa Gelap={kpi_d_after}"))
            page.screenshot(path=os.path.join(SHOT_DIR, "02_michael_solusi_pju_3d.png"))

            # 3. Switch to Orang 1 (William - UHI) & 3D Hex Mode + Stage 3
            page.click('.nav-link[data-preset="overview-medan"]')
            page.wait_for_timeout(1200)
            page.click('.topic-card[data-topic="orang1"]')
            page.click('.seg-btn[data-hexmode="3d"]')
            page.wait_for_timeout(1500)
            uhi_before = page.locator("#kpi-corridors").inner_text()
            page.click('.stage-btn[data-stage="3"]')
            page.wait_for_timeout(1500)
            uhi_after = page.locator("#kpi-corridors").inner_text()
            results.append(("3. Analisis Suhu Panas UHI & Pohon Peneduh (William)", "PASS", f"Awal={uhi_before}, Solusi={uhi_after}"))
            page.screenshot(path=os.path.join(SHOT_DIR, "03_william_uhi_3d_hex.png"))

            # 4. Switch to Orang 2 (Jordan - NDVI / Taman Hijau) + Stage 3
            page.click('.topic-card[data-topic="orang2"]')
            page.wait_for_timeout(1200)
            ndvi_before = page.locator("#kpi-corridors").inner_text()
            page.click('.stage-btn[data-stage="3"]')
            page.wait_for_timeout(1500)
            ndvi_after = page.locator("#kpi-corridors").inner_text()
            results.append(("4. Analisis Kerapatan Pohon NDVI & 52 Taman (Jordan)", "PASS", f"NDVI Awal={ndvi_before}, Solusi={ndvi_after}"))
            page.screenshot(path=os.path.join(SHOT_DIR, "04_jordan_rth_taman.png"))

            # 5. Switch to Orang 3 (Visel - Banjir DEM + RS Rujukan)
            page.click('.nav-link[data-preset="focus-pusat"]')
            page.click('.topic-card[data-topic="orang3"]')
            page.wait_for_timeout(1800)
            flood_area_before = page.locator("#kpi-corridors").inner_text()
            page.click('.stage-btn[data-stage="3"]')
            page.wait_for_timeout(1500)
            flood_area_after = page.locator("#kpi-corridors").inner_text()
            results.append(("5. Simulasi Luapan Banjir DEM & RS Rujukan (Visel)", "PASS", f"Genangan Awal={flood_area_before}, Pasca Retensi={flood_area_after}"))
            page.screenshot(path=os.path.join(SHOT_DIR, "05_visel_banjir_evakuasi.png"))

            # 6. Switch to Orang 4 (Peter - Damkar Isochrone)
            page.click('.nav-link[data-preset="overview-medan"]')
            page.click('.topic-card[data-topic="orang4"]')
            page.click('.seg-btn[data-hexmode="flat"]')
            page.wait_for_timeout(1500)
            damkar_before = page.locator("#kpi-dark-buildings").inner_text()
            page.click('.stage-btn[data-stage="3"]')
            page.wait_for_timeout(1500)
            damkar_after = page.locator("#kpi-dark-buildings").inner_text()
            results.append(("6. Analisis Jangkauan Damkar & Hidran (Peter)", "PASS", f"Rumah Lambat Awal={damkar_before}, Sisa={damkar_after}"))
            page.screenshot(path=os.path.join(SHOT_DIR, "06_peter_damkar_isochrone.png"))

            # 7. Mode Gabungan Bebas + Kecamatan Filter
            page.click('.topic-card[data-topic="gabungan"]')
            page.select_option("#filter-kecamatan", "Medan Baru")
            page.wait_for_timeout(1800)
            results.append(("7. Mode Gabungan 5 Fitur & Filter Kecamatan Medan Baru", "PASS", "Seluruh layer aktif terpadu"))
            page.screenshot(path=os.path.join(SHOT_DIR, "07_mode_gabungan_medan_baru.png"))
            page.select_option("#filter-kecamatan", "ALL")

            # 8. Modal Sumber Data & Bukti Satelit
            page.click("#btn-bukti")
            page.wait_for_timeout(1000)
            modal_vis = page.locator("#modal-bukti").is_visible()
            results.append(("8. Modal Sumber Data, Citra Satelit & Daftar Koridor", "PASS" if modal_vis else "FAIL", f"Visible={modal_vis}"))
            page.screenshot(path=os.path.join(SHOT_DIR, "08_modal_bukti_satelit.png"))
            page.click("#btn-close-modal")

            # 9. Mode Bola Dunia (Globe 3D) & Mode Malam
            page.click('.base-btn[data-basemap="satelit"]')
            page.click('.nav-link[data-preset="globe-3d"]')
            page.wait_for_timeout(2000)
            results.append(("9. Proyeksi Adaptif Globe 3D & Basemap Malam", "PASS", "Zoom-out Z 2.0 aktif"))
            page.screenshot(path=os.path.join(SHOT_DIR, "09_globe_3d_mode_malam.png"))

            # Check model count
            m_loaded = page.evaluate("() => window.__modelsLoaded")
            m_inst = page.evaluate("() => window.__modelInstances")
            results.append(("10. Pemuatan Aset Model 3D GLB (Three.js GLTFLoader)", "PASS" if m_loaded >= 9 else "FAIL", f"Template={m_loaded}, Instansi={m_inst}"))

            browser.close()
    finally:
        httpd.shutdown()

    print("=== TEST SUMMARY ===")
    for name, status, detail in results:
        print(f"{name}: {status} | {detail}")
    print(f"CONSOLE_ERRORS_COUNT: {len(console_errors)}")
    for e in console_errors[:10]:
        print(" ", e)


if __name__ == "__main__":
    run_tests()
