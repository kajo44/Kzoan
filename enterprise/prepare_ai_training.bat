@echo off
setlocal
cd /d "%~dp0"
title APRJ Next - Persiapan AI Survei

echo ============================================================
echo APRJ NEXT - PERSIAPAN LINGKUNGAN AI
echo ============================================================
echo Folder kerja: %CD%
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python Launcher ^(py^) tidak ditemukan.
  echo Instal Python 3.11 64-bit dan aktifkan Python Launcher serta Tcl/Tk.
  pause
  exit /b 1
)

py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 tidak ditemukan.
  echo Instal Python 3.11 64-bit sebelum melanjutkan.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Membuat virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :failed
) else (
  echo [1/5] Menggunakan virtual environment .venv yang sudah ada.
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :failed

echo.
echo [2/5] Memperbarui pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo.
echo [3/5] Memasang dependensi runtime, termasuk PyTorch CPU...
python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo [4/5] Mengunduh dan memvalidasi bobot dasar ResNet-18 ImageNet...
python prepare_pretrained_model.py
if errorlevel 1 goto :failed

echo.
echo [5/5] Menyiapkan folder data model APRJ...
if not exist "survey_ai\models" mkdir "survey_ai\models"
if not exist "survey_ai\dataset" mkdir "survey_ai\dataset"
if not exist "survey_ai\training_runs" mkdir "survey_ai\training_runs"
if not exist "survey_ai\cache" mkdir "survey_ai\cache"

echo.
echo PERSIAPAN DASAR SELESAI.
echo Bobot pretrained tersedia di folder pretrained.
echo PENTING: model ini belum dilatih untuk kondisi jalan APRJ.
echo Checkpoint survey_multi_task_model.pth baru akan dibuat setelah
echo training berhasil memakai dataset foto dan label survei yang valid.
echo.
choice /C YN /M "Buka APRJ Next sekarang"
if errorlevel 2 goto :done
python aprj_main.py
if errorlevel 1 (
  echo.
  echo Aplikasi berhenti dengan kode error. Periksa pesan di atas dan logs.
  pause
)
goto :done

:failed
echo.
echo PERSIAPAN GAGAL. Jangan lanjutkan training sebelum error di atas diperbaiki.
echo Periksa koneksi internet, ruang disk, Python 3.11 64-bit, dan pesan pip.
pause
exit /b 1

:done
endlocal
