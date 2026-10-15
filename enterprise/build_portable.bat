@echo off
setlocal
cd /d "%~dp0"
title Build APRJ Next Portable ONEDIR

echo ============================================================
echo  APRJ Next - Build Windows ONEDIR Portable
echo ============================================================
echo.
echo Prasyarat: Windows 10/11 64-bit, Python 3.11 64-bit dan Tcl/Tk.
echo PyTorch CPU akan dipasang; ukuran output dapat besar.
echo Modul Geospasial Jalan membutuhkan bin\exiftool.exe.
echo Jika bin belum tersedia, script akan mencoba menyalin dari C:\Tools\ExifTool.
echo.

if not exist "bin\exiftool.exe" (
  if exist "C:\Tools\ExifTool\exiftool.exe" (
    if not exist "bin" mkdir "bin"
    copy /Y "C:\Tools\ExifTool\exiftool.exe" "bin\exiftool.exe" >nul
    if exist "C:\Tools\ExifTool\exiftool_files" (
      xcopy "C:\Tools\ExifTool\exiftool_files" "bin\exiftool_files\" /E /I /Y >nul
    )
  )
)
if not exist "bin\exiftool.exe" (
  echo ERROR: ExifTool tidak ditemukan.
  echo Salin exiftool.exe ke enterprise\bin\exiftool.exe.
  echo Sertakan folder exiftool_files jika distribusi ExifTool Anda membutuhkannya.
  pause
  exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python Launcher "py" tidak ditemukan.
  echo Instal Python 3.11 64-bit dan aktifkan opsi Python Launcher.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

python -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo.
echo [1/5] Memasang dependency build dari requirements-build.txt...
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail

echo.
echo [2/5] Menyiapkan bobot pretrained ResNet-18 (perlu internet saat build pertama)...
python prepare_pretrained_model.py
if errorlevel 1 goto :fail

echo.
echo [3/5] Memeriksa sintaks seluruh modul dan tes...
python -m compileall -q prepare_pretrained_model.py aprj_main.py aprj_ui.py aprj_core.py aprj_database.py aprj_ai_model.py aprj_pkrms.py aprj_training_engine.py aprj_geospasial.py aprj_metadata.py aprj_map_matching.py aprj_exif_fallback.py tests
if errorlevel 1 goto :fail

echo.
echo [4/5] Menjalankan tes regresi...
python -m unittest discover -s tests -v
if errorlevel 1 goto :fail

echo.
echo [5/5] Mem-build aplikasi ONEDIR...
python -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --contents-directory "." ^
  --name APRJ_Next ^
  --paths "." ^
  --collect-all PIL ^
  --collect-all piexif ^
  --collect-all openpyxl ^
  --collect-all torch ^
  --collect-all torchvision ^
  --add-data "pretrained;pretrained" ^
  --add-data "bin;bin" ^
  --hidden-import aprj_core ^
  --hidden-import aprj_ai_model ^
  --hidden-import aprj_training_engine ^
  --hidden-import aprj_database ^
  --hidden-import aprj_pkrms ^
  --hidden-import aprj_geospasial ^
  --hidden-import aprj_metadata ^
  --hidden-import aprj_map_matching ^
  --hidden-import aprj_exif_fallback ^
  --hidden-import psycopg2 ^
  --hidden-import psycopg2._psycopg ^
  aprj_main.py
if errorlevel 1 goto :fail

if exist "..\APRJ_PORTABLE_GUIDE.txt" copy /Y "..\APRJ_PORTABLE_GUIDE.txt" "dist\APRJ_Next\APRJ_PORTABLE_GUIDE.txt" >nul
if exist "README.md" copy /Y "README.md" "dist\APRJ_Next\PANDUAN_PENGGUNAAN.md" >nul
if exist "PENGEMBANGAN_APRJ.txt" copy /Y "PENGEMBANGAN_APRJ.txt" "dist\APRJ_Next\PENGEMBANGAN_APRJ.txt" >nul
if exist "MODEL_PRETRAINED.txt" copy /Y "MODEL_PRETRAINED.txt" "dist\APRJ_Next\MODEL_PRETRAINED.txt" >nul
if exist "RIWAYAT_PERUBAHAN.txt" copy /Y "RIWAYAT_PERUBAHAN.txt" "dist\APRJ_Next\RIWAYAT_PERUBAHAN.txt" >nul

echo.
echo ============================================================
echo BUILD BERHASIL
echo Folder aplikasi: %CD%\dist\APRJ_Next
echo Jalankan: dist\APRJ_Next\APRJ_Next.exe
echo Salin SELURUH folder APRJ_Next, jangan hanya file EXE.
echo ============================================================
pause
exit /b 0

:fail
echo.
echo BUILD GAGAL. Baca pesan error di atas sebelum mencoba ulang.
pause
exit /b 1
