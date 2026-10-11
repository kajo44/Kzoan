# -*- coding: utf-8 -*-
"""Fallback pembacaan metadata EXIF menggunakan Pillow saat ExifTool tidak tersedia.

Fallback ini mendukung metadata dasar GPS/waktu/arah yang tersimpan pada EXIF.
Untuk format/metadata khusus, ExifTool tetap direkomendasikan.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ExifTags

_TAGS = ExifTags.TAGS
_GPS_TAGS = ExifTags.GPSTAGS


def _as_float(value):
    """Konversi nilai EXIF rasional/angka ke float secara defensif."""
    try:
        if isinstance(value, (tuple, list)) and len(value) == 2:
            denominator = float(value[1])
            return float(value[0]) / denominator if denominator else None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None


def _as_text(value):
    if isinstance(value, bytes):
        return value.decode("ascii", errors="replace").strip("\x00 ")
    return str(value or "").strip()


def _dms_to_decimal(value, reference=""):
    """Konversi derajat-menit-detik EXIF ke derajat desimal."""
    if not isinstance(value, (tuple, list)) or len(value) < 3:
        direct = _as_float(value)
        if direct is None:
            return None
        decimal = direct
    else:
        parts = [_as_float(part) for part in value[:3]]
        if any(part is None for part in parts):
            return None
        decimal = parts[0] + parts[1] / 60.0 + parts[2] / 3600.0
    if _as_text(reference).upper() in {"S", "W"}:
        decimal = -abs(decimal)
    return decimal if math.isfinite(decimal) else None


def _read_one(path):
    path = Path(path)
    try:
        source_path = str(path.resolve())
    except OSError:
        source_path = str(path.absolute())
    item = {
        "SourceFile": source_path,
        "FileName": path.name,
        "Directory": str(path.parent),
    }
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            if not exif:
                return item
            exif_named = {_TAGS.get(key, key): value for key, value in exif.items()}
            exif_ifd = {}
            try:
                exif_ifd = {
                    _TAGS.get(key, key): value
                    for key, value in exif.get_ifd(0x8769).items()
                }
            except (AttributeError, KeyError, TypeError, ValueError):
                pass
            item["DateTimeOriginal"] = exif_ifd.get("DateTimeOriginal")
            item["CreateDate"] = exif_ifd.get("DateTimeDigitized") or exif_ifd.get("DateTime")
            item["CreateDate"] = item["CreateDate"] or exif_named.get("DateTime")

            gps = {}
            try:
                raw_gps = exif.get_ifd(0x8825)
                gps = {_GPS_TAGS.get(key, key): value for key, value in raw_gps.items()}
            except (AttributeError, KeyError, TypeError, ValueError):
                gps = {}

            lat = _dms_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
            lon = _dms_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
            if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
                item["GPSLatitude"] = lat
                item["GPSLongitude"] = lon

            direction = _as_float(gps.get("GPSImgDirection"))
            if direction is not None:
                item["GPSImgDirection"] = direction % 360.0
                item["GPSImgDirectionRef"] = _as_text(gps.get("GPSImgDirectionRef") or "T").upper()
    except Exception:
        # File rusak/tidak didukung: tetap kembalikan SourceFile agar proses batch lanjut.
        # Exception sengaja dibatasi per-file, bukan membatalkan seluruh batch.
    return item


def read_metadata_batch(paths):
    """Baca metadata satu batch; file gagal dibaca tidak menggagalkan batch lain."""
    results = {}
    for path in paths:
        item = _read_one(path)
        source = item.get("SourceFile")
        if source:
            results[source] = item
    return results
