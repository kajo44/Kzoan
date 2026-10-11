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
echo.

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
echo [1/2] Memasang seluruh dependensi dari requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [2/2] Memeriksa sintaks aplikasi...
python -m py_compile aprj_main.py aprj_ui.py aprj_core.py aprj_database.py aprj_ai_model.py aprj_pkrms.py aprj_training_engine.py main.py APRJ_v2.py core.py database.py ai_model.py pkrms_utils.py training_engine.py
if errorlevel 1 goto :fail

echo.
echo Mem-build aplikasi ONEDIR...
python -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --name APRJ_Next ^
  --paths "." ^
  --collect-all PIL ^
  --collect-all openpyxl ^
  --collect-all torch ^
  --hidden-import aprj_core ^
  --hidden-import aprj_ai_model ^
  --hidden-import aprj_training_engine ^
  --hidden-import aprj_database ^
  --hidden-import aprj_pkrms ^
  --hidden-import psycopg2 ^
  --hidden-import psycopg2._psycopg ^
  aprj_main.py
if errorlevel 1 goto :fail

if exist "..\APRJ_PORTABLE_GUIDE.txt" copy /Y "..\APRJ_PORTABLE_GUIDE.txt" "dist\APRJ_Next\APRJ_PORTABLE_GUIDE.txt" >nul

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
