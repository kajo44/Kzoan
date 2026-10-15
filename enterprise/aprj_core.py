# -*- coding: utf-8 -*-
"""
Modul Core: Konfigurasi Global, Konstanta, Path Portabel, dan Sistem Logging.
Bertanggung jawab atas struktur direktori dan konfigurasi dasar aplikasi APRJ & PKRMS.
"""

import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

APP_NAME = "APRJ_Next"
APP_ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

# Struktur Direktori Portabel
APP_LOGS = APP_ROOT / "logs"
APP_ERROR_LOG = APP_LOGS / "application_errors.log"
DATASET_ROOT = APP_ROOT / "dataset"
FEEDBACK_ROOT = DATASET_ROOT / "feedback"
DOWNLOAD_ROOT = APP_ROOT / "downloads"
CONFIG_ROOT = APP_ROOT / "config"

SURVEY_AI_ROOT = APP_ROOT / "survey_ai"
SURVEY_AI_DATASET = SURVEY_AI_ROOT / "dataset"
SURVEY_AI_IMAGES = SURVEY_AI_DATASET / "images"
SURVEY_AI_MODELS = SURVEY_AI_ROOT / "models"
SURVEY_AI_MANIFEST = SURVEY_AI_DATASET / "labels.json"
SURVEY_AI_RUNS = SURVEY_AI_ROOT / "training_runs"
SURVEY_AI_CACHE = SURVEY_AI_ROOT / "cache"
SURVEY_DB_PATH = APP_ROOT / "data" / "survey.sqlite3"

# Klasifikasi AI Multi-Task & Perkerasan
CLASSES = ("baik", "rusak_ringan", "rusak_sedang", "rusak_berat")
SURFACE_CLASSES = ("aspal", "beton", "tanah", "kerikil")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
IMAGE_SIZE = 224


def log_application_error(context, error_type, error, error_traceback):
    """Mencatat error aplikasi secara terpusat ke dalam file log lokal."""
    try:
        APP_LOGS.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(APP_NAME)
        if not logger.handlers:
            handler = logging.FileHandler(APP_ERROR_LOG, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.ERROR)
        logger.error("%s: %s", context, error, exc_info=(error_type, error, error_traceback))
    except OSError as log_error:
        sys.stderr.write(f"{context}: {error}\nGagal menulis log: {log_error}\n")


def load_record_manifest(path):
    """Baca manifest JSON berisi daftar record dan kembalikan (records, peringatan).

    File yang tidak terbaca tidak dibuang diam-diam: salinannya disimpan sebagai
    ``<nama>.corrupt-<waktu>`` sebelum daftar kosong dikembalikan, sehingga simpan
    berikutnya tidak menghapus satu-satunya salinan data asli.
    """
    path = Path(path)
    if not path.exists():
        return [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("isi manifest bukan daftar record")
    except (OSError, ValueError) as error:
        backup = path.with_name(f"{path.name}.corrupt-{datetime.now():%Y%m%d-%H%M%S}")
        try:
            shutil.copy2(path, backup)
            saved = f"Salinan file asli disimpan di: {backup}"
        except OSError:
            saved = "Salinan file asli GAGAL dibuat; jangan simpan dataset sebelum file diperiksa."
        return [], f"Manifest dataset tidak dapat dibaca ({error}). {saved}"
    records = [record for record in data if isinstance(record, dict)]
    skipped = len(data) - len(records)
    warning = f"{skipped} entri manifest bukan record dan dilewati." if skipped else None
    return records, warning


def save_record_manifest(path, records):
    """Simpan manifest secara atomik; versi sebelumnya disimpan sebagai ``<nama>.bak``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    if path.is_file():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    temporary.replace(path)


def initialize_portable_dirs():
    """Membuat seluruh direktori pendukung secara otomatis jika belum ada."""
    for directory in (
        APP_LOGS, DATASET_ROOT, FEEDBACK_ROOT, DOWNLOAD_ROOT, CONFIG_ROOT,
        SURVEY_AI_IMAGES, SURVEY_AI_MODELS
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for surface_class in SURFACE_CLASSES:
        (DATASET_ROOT / "surface_type" / surface_class).mkdir(parents=True, exist_ok=True)