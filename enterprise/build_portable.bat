@echo off
setlocal
cd /d "%~dp0"
title Build APRJ Portable ONEDIR

echo ============================================================
echo  APRJ - Build Windows ONEDIR Portable
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
echo [1/3] Memasang PyTorch CPU...
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto :fail

echo.
echo [2/3] Memasang dependensi...
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [3/3] Memeriksa sintaks aplikasi...
python -m py_compile main.py APRJ_v2.py core.py database.py ai_model.py pkrms_utils.py training_engine.py
if errorlevel 1 goto :fail

echo.
echo Mem-build aplikasi ONEDIR...
python -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --name APRJ ^
  --paths "." ^
  --collect-all PIL ^
  --collect-all openpyxl ^
  --collect-all torch ^
  --hidden-import ai_model ^
  --hidden-import training_engine ^
  --hidden-import database ^
  --hidden-import pkrms_utils ^
  --hidden-import psycopg2 ^
  --hidden-import psycopg2._psycopg ^
  main.py
if errorlevel 1 goto :fail

if exist "README_PORTABLE.txt" copy /Y "README_PORTABLE.txt" "dist\APRJ\README_PORTABLE.txt" >nul

echo.
echo ============================================================
echo BUILD BERHASIL
echo Folder aplikasi: %CD%\dist\APRJ
echo Jalankan: dist\APRJ\APRJ.exe
echo Salin SELURUH folder APRJ, jangan hanya file EXE.
echo ============================================================
pause
exit /b 0

:fail
echo.
echo BUILD GAGAL. Baca pesan error di atas sebelum mencoba ulang.
pause
exit /b 1
