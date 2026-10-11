# -*- coding: utf-8 -*-
"""Pemeriksa instalasi APRJ/PKRMS yang aman.

Skrip ini tidak membuat ulang atau menimpa file aplikasi. Jalankan dari folder enterprise:
    python setup_project.py
"""
import importlib.util
import sys
from pathlib import Path

REQUIRED = {
    "Pillow": "PIL",
    "openpyxl": "openpyxl",
}
OPTIONAL = {
    "PyTorch (fitur inferensi AI)": "torch",
    "psycopg2-binary (sinkronisasi PostgreSQL)": "psycopg2",
}


def main():
    root = Path(__file__).resolve().parent
    print(f"APRJ/PKRMS - pemeriksaan instalasi\nFolder aplikasi: {root}")
    print(f"Python: {sys.version.split()[0]}")
    missing = []
    for package, module in REQUIRED.items():
        if importlib.util.find_spec(module) is None:
            missing.append(package)
            print(f"[KURANG] {package}")
        else:
            print(f"[OK] {package}")
    for package, module in OPTIONAL.items():
        print(f"[OK] {package}" if importlib.util.find_spec(module) else f"[OPSIONAL] {package} belum terpasang")
    if missing:
        print("\nPasang dependensi wajib dengan:")
        print(f'"{sys.executable}" -m pip install ' + " ".join(missing))
        return 1
    print("\nPemeriksaan dependensi wajib selesai. Tidak ada file aplikasi yang ditimpa.")
    print("Jalankan aplikasi dengan: python main.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
