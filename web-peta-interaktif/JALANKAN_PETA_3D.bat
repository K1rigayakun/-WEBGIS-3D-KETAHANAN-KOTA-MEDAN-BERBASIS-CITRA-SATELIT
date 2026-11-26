@echo off
title Server WebGIS 3D Kota Medan (5 Fitur - 21 Kecamatan)
cd /d "%~dp0"
if exist "web-peta-interaktif\index.html" (
    cd /d "%~dp0web-peta-interaktif"
)
echo ======================================================================
echo   WEBGIS 3D KOTA MEDAN - 5 FITUR ANGGOTA TIM (21 KECAMATAN PENUH)
echo   William (Suhu) ^| Jordan (RTH) ^| Visel (Banjir ^& RS) ^| Peter (Damkar) ^| Michael (PJU)
echo ======================================================================
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    echo Menjalankan server lokal di http://localhost:8080 ...
    start "" "http://localhost:8080"
    python -m http.server 8080
    goto :eof
)
where py >nul 2>nul
if %errorlevel%==0 (
    echo Menjalankan server lokal di http://localhost:8080 ...
    start "" "http://localhost:8080"
    py -m http.server 8080
    goto :eof
)
echo Python tidak ditemukan di PATH, membuka index.html langsung di browser...
start "" "index.html"
