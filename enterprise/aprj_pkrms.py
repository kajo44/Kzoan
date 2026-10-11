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
    """Menormalkan teks kondisi kerusakan jalan dari berbagai variasi input."""
    text = re.sub(r"\s+", " ", str(value or "").strip().lower())
    text = text.replace("_", " ").replace("-", " ")
    if any(term in text for term in ("rusak berat", "rusak parah", "sangat rusak", "buruk", "heavy")):
        return "rusak_berat"
    if any(term in text for term in ("rusak sedang", "sedang", "moderate")):
        return "rusak_sedang"
    if any(term in text for term in ("rusak ringan", "ringan", "minor")):
        return "rusak_ringan"
    if any(term in text for term in ("baik", "bagus", "normal", "layak", "good", "aman")):
        return "baik"
    return None


def create_pkrms_template(destination):
    """Membuat file template Excel standar PKRMS."""
    output = openpyxl.Workbook()
    sheet = output.active
    sheet.title = "PKRMS_Survey"
    sheet.append(PKRMS_TEMPLATE_COLUMNS)
    sheet.append([
        "Sumatera Barat", "Padang", "", "", "", "SEG-001", 0, 1, 1,
        datetime.now().date().isoformat(), "contoh.jpg", "aspal",
        "baik", "baik", "", "baik", "Belum diverifikasi", "",
        "belum_diukur", "",
    ])
    for cell in sheet[1]:
        cell.font = cell.font.copy(bold=True)
    output.save(destination)


def export_pkrms_report(destination):
    """Mengekspor rekapitulasi audit dataset ke format laporan PKRMS Excel."""
    workbook = openpyxl.Workbook()
    survey = workbook.active
    survey.title = "PKRMS_Survey"
    survey.append(PKRMS_TEMPLATE_COLUMNS)
    counts = {label: 0 for label in CLASSES}
    for label in CLASSES:
        target_dir = DATASET_ROOT / label
        if target_dir.is_dir():
            for photo in target_dir.rglob("*"):
                if photo.is_file() and photo.suffix.lower() in IMAGE_EXTENSIONS:
                    counts[label] += 1
                    survey.append([
                        "", "", "", "", "", "",
                        "", "", "", datetime.now().date().isoformat(),
                        photo.name, "", label, label, "", label, "Belum diverifikasi",
                        "", "belum_diukur", "Berkas ditemukan pada folder dataset; label perlu diverifikasi"
                    ])
    workbook.save(destination)
    return counts