# -*- coding: utf-8 -*-
"""Pemeriksa dependensi APRJ/PKRMS; tidak menimpa file aplikasi."""
import importlib.util
import sys
from pathlib import Path

REQUIRED = {"Pillow": "PIL", "openpyxl": "openpyxl"}
OPTIONAL = {"PyTorch untuk inferensi AI": "torch", "psycopg2-binary untuk PostgreSQL": "psycopg2"}

def main():
    print("APRJ/PKRMS - pemeriksaan instalasi")
    print("Folder:", Path(__file__).resolve().parent)
    print("Python:", sys.version.split()[0])
    missing = []
    for package, module in REQUIRED.items():
        if importlib.util.find_spec(module) is None:
            missing.append(package)
            print("[KURANG]", package)
        else:
            print("[OK]", package)
    for package, module in OPTIONAL.items():
        print("[OK]" if importlib.util.find_spec(module) else "[OPSIONAL BELUM TERPASANG]", package)
    if missing:
        print("Pasang dependensi wajib:", sys.executable, "-m pip install", *missing)
        return 1
    print("Pemeriksaan selesai. Tidak ada file aplikasi yang ditimpa.")
    print("Jalankan aplikasi dengan: python main.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
