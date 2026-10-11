# -*- coding: utf-8 -*-
"""
Modul PKRMS Utils: Excel Reporting, Template PKRMS, & Dataset Auditing.
Menyediakan fungsi untuk validasi dataset dan ekspor rekapitulasi penilaian jalan.
"""

from datetime import datetime
from collections import defaultdict
import hashlib
import re
import openpyxl
from core import DATASET_ROOT, CLASSES, SURFACE_CLASSES, IMAGE_EXTENSIONS

PKRMS_TEMPLATE_COLUMNS = [
    "province", "regency", "district", "road_code", "road_name",
    "segment_id", "start_km", "end_km", "length_km", "survey_date",
    "photo_name", "surface_type", "condition", "ai_condition",
    "corrected_condition", "final_condition", "review_status",
    "road_width_m", "width_measurement_status", "remarks"
]


def audit_dataset():
    """Hitung gambar saja dan laporkan file rusak serta duplikasi SHA-256."""
    report = {"condition_counts": {}, "surface_counts": {}, "invalid": [],
              "duplicate_groups": 0, "duplicate_files": [], "scanned_files": 0}
    candidates = []
    for label in CLASSES:
        folder = DATASET_ROOT / label
        images = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS) if folder.is_dir() else []
        report["condition_counts"][label] = len(images)
        candidates.extend(images)
    for label in SURFACE_CLASSES:
        folder = DATASET_ROOT / "surface_type" / label
        images = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS) if folder.is_dir() else []
        report["surface_counts"][label] = len(images)
        candidates.extend(images)
    hashes = defaultdict(list)
    for path in candidates:
        report["scanned_files"] += 1
        try:
            with path.open("rb") as stream:
                hashes[hashlib.sha256(stream.read()).hexdigest()].append(str(path))
            try:
                from PIL import Image
                with Image.open(path) as image:
                    image.verify()
            except ImportError:
                pass
            except Exception as exc:
                report["invalid"].append({"path": str(path), "reason": str(exc)})
        except OSError as exc:
            report["invalid"].append({"path": str(path), "reason": str(exc)})
    groups = [paths for paths in hashes.values() if len(paths) > 1]
    report["duplicate_groups"] = len(groups)
    report["duplicate_files"] = groups
    return report

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
    sheet.append([""] * len(PKRMS_TEMPLATE_COLUMNS))
    sheet["J2"] = datetime.now().date().isoformat()
    sheet["Q2"] = "Belum diverifikasi"
    sheet["T2"] = "Isi berdasarkan hasil survei lapangan"
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        from copy import copy
        cell.font = copy(cell.font)
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
                        "Sumatera Barat", "", "", "", "", "",
                        "", "", "", datetime.now().date().isoformat(),
                        photo.name, "", label, label, "", label, "Belum diverifikasi",
                        "", "belum_diukur", "Hasil audit sistem"
                    ])
    workbook.save(destination)
    return counts