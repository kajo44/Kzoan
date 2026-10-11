# -*- coding: utf-8 -*-
"""
Modul PKRMS Utils: Excel Reporting, Template PKRMS, & Dataset Auditing.
Menyediakan fungsi untuk validasi dataset dan ekspor rekapitulasi penilaian jalan.
"""

from datetime import datetime
import re
import openpyxl
from aprj_core import DATASET_ROOT, CLASSES, SURFACE_CLASSES, IMAGE_EXTENSIONS

PKRMS_TEMPLATE_COLUMNS = [
    "province", "regency", "district", "road_code", "road_name",
    "segment_id", "start_km", "end_km", "length_km", "survey_date",
    "photo_name", "surface_type", "condition", "ai_condition",
    "corrected_condition", "final_condition", "review_status",
    "road_width_m", "width_measurement_status", "remarks"
]


def audit_dataset():
    """Hitung sampel gambar per kelas, tanpa menghitung folder sebagai sampel."""
    def count_images(directory):
        if not directory.is_dir():
            return 0
        return sum(
            1 for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )

    return {
        "condition_counts": {label: count_images(DATASET_ROOT / label) for label in CLASSES},
        "surface_counts": {
            label: count_images(DATASET_ROOT / "surface_type" / label)
            for label in SURFACE_CLASSES
        },
        "invalid": [],
        "duplicate_groups": 0,
    }


def normalize_condition(value):
    """Normalisasi label kondisi tanpa mengubah frasa negatif menjadi label positif."""
    text = re.sub(r"\\s+", " ", str(value or "").strip().lower())
    text = text.replace("_", " ").replace("-", " ")
    if not text:
        return None

    # Jangan menafsirkan "tidak baik" atau "kurang baik" sebagai "baik".
    # Frasa ambigu dibiarkan untuk pemeriksaan manusia, bukan ditebak.
    negative_or_ambiguous = (
        "tidak baik", "kurang baik", "belum baik", "tidak layak",
        "belum layak", "tidak aman", "belum aman",
    )
    if any(term in text for term in negative_or_ambiguous):
        return None

    # Urutkan kondisi dari paling berat agar kata "rusak" umum tidak menimpa kelas spesifik.
    if any(term in text for term in (
        "rusak berat", "rusak parah", "sangat rusak", "heavy damage",
        "heavily damaged", "buruk",
    )):
        return "rusak_berat"
    if any(term in text for term in ("rusak sedang", "moderate damage", "moderately damaged")):
        return "rusak_sedang"
    if any(term in text for term in ("rusak ringan", "minor damage", "slightly damaged")):
        return "rusak_ringan"

    # Label positif hanya dikenali sebagai nilai/frasanya sendiri, bukan substring
    # dari kalimat yang mungkin mengandung penyangkalan.
    if text in {"baik", "bagus", "normal", "layak", "good", "aman", "kondisi baik"}:
        return "baik"
    if text in {"sedang", "moderate"}:
        return "rusak_sedang"
    if text in {"ringan", "minor"}:
        return "rusak_ringan"
    if text in {"berat", "parah", "heavy"}:
        return "rusak_berat"
    return None
s