# -*- coding: utf-8 -*-
"""Siapkan bobot resmi ResNet-18 untuk dimasukkan ke build portable APRJ."""
from pathlib import Path
import sys

OUTPUT = Path(__file__).resolve().parent / "pretrained" / "resnet18-f37072fd.pth"


def main():
    try:
        import torch
        from torchvision.models import ResNet18_Weights
    except Exception as exc:
        print(f"ERROR: torch/torchvision tidak dapat diimpor: {exc}", file=sys.stderr)
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.is_file() and OUTPUT.stat().st_size > 1_000_000:
        try:
            try:
                existing = torch.load(OUTPUT, map_location="cpu", weights_only=True)
            except TypeError:
                existing = torch.load(OUTPUT, map_location="cpu")
            if isinstance(existing, dict) and "conv1.weight" in existing and "layer4.0.conv1.weight" in existing:
                print(f"Bobot pretrained tervalidasi dan sudah tersedia: {OUTPUT}")
                return 0
            print("Bobot yang ada tidak valid; akan diunduh ulang.")
        except Exception as exc:
            print(f"Bobot yang ada tidak dapat dibaca; akan diunduh ulang: {exc}")
        OUTPUT.unlink(missing_ok=True)
    try:
        weights = ResNet18_Weights.IMAGENET1K_V1
        state_dict = weights.get_state_dict(progress=True, check_hash=True)
        temp = OUTPUT.with_suffix(".pth.tmp")
        torch.save(state_dict, temp)
        temp.replace(OUTPUT)
        print(f"Bobot ResNet-18 ImageNet disiapkan: {OUTPUT}")
        print(f"Ukuran: {OUTPUT.stat().st_size:,} byte")
        print("Catatan: bobot ImageNet bukan model kondisi jalan yang sudah terlatih.")
        return 0
    except Exception as exc:
        print("ERROR: gagal mengambil/menyiapkan bobot pretrained.", file=sys.stderr)
        print("Periksa koneksi internet, proxy, ruang disk, serta versi torchvision.", file=sys.stderr)
        print(f"Detail: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
