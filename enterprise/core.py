# -*- coding: utf-8 -*-
"""Konfigurasi, path portabel, dan logging APRJ/PKRMS."""
import logging
import sys
from pathlib import Path

APP_NAME = "APRJ"
APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
APP_LOGS = APP_ROOT / "logs"
APP_ERROR_LOG = APP_LOGS / "application_errors.log"
DATA_ROOT = APP_ROOT / "data"
SURVEY_DB_PATH = DATA_ROOT / "survey.sqlite3"
DATASET_ROOT = APP_ROOT / "dataset"
FEEDBACK_ROOT = DATASET_ROOT / "feedback"
DOWNLOAD_ROOT = APP_ROOT / "downloads"
CONFIG_ROOT = APP_ROOT / "config"
SURVEY_AI_ROOT = APP_ROOT / "survey_ai"
SURVEY_AI_DATASET = SURVEY_AI_ROOT / "dataset"
SURVEY_AI_IMAGES = SURVEY_AI_DATASET / "images"
SURVEY_AI_MODELS = SURVEY_AI_ROOT / "models"

CLASSES = ("baik", "rusak_ringan", "rusak_sedang", "rusak_berat")
SURFACE_CLASSES = ("aspal", "beton", "tanah", "kerikil")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
IMAGE_SIZE = 224


def log_application_error(context, error_type, error, error_traceback):
    """Catat error tanpa membuat kegagalan logging menghentikan aplikasi."""
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


def initialize_portable_dirs():
    """Buat direktori yang diperlukan tanpa menghapus data yang sudah ada."""
    for directory in (
        APP_LOGS, DATA_ROOT, DATASET_ROOT, FEEDBACK_ROOT, DOWNLOAD_ROOT,
        CONFIG_ROOT, SURVEY_AI_IMAGES, SURVEY_AI_MODELS,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for label in CLASSES:
        (DATASET_ROOT / label).mkdir(parents=True, exist_ok=True)
    for label in SURFACE_CLASSES:
        (DATASET_ROOT / "surface_type" / label).mkdir(parents=True, exist_ok=True)
