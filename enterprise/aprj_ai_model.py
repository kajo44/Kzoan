# -*- coding: utf-8 -*-
"""Arsitektur AI APRJ Next: ResNet-18 pretrained lokal dan kepala multi-task survei."""
from __future__ import annotations

import random
import sys
from pathlib import Path

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False

from aprj_core import IMAGE_SIZE

SURVEY_WIDTH_FIELDS = (
    "lebar_bahu_kiri",
    "lebar_drainase_kiri",
    "lebar_perkerasan",
    "lebar_bahu_kanan",
    "lebar_drainase_kanan",
)
PRETRAINED_RELATIVE_PATH = Path("pretrained") / "resnet18-f37072fd.pth"


def pretrained_weights_path() -> Path:
    """Cari bobot yang dibundel pada source atau folder ONEDIR."""
    candidates = []
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        candidates.append(Path(frozen_root) / PRETRAINED_RELATIVE_PATH)
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / PRETRAINED_RELATIVE_PATH)
    candidates.append(Path(__file__).resolve().parent / PRETRAINED_RELATIVE_PATH)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    checked = "\n".join(str(p) for p in candidates)
    raise FileNotFoundError(
        "Bobot pretrained ResNet-18 tidak ditemukan. Jalankan "
        "prepare_pretrained_model.py sebelum build dan sertakan folder pretrained. "
        "Lokasi yang diperiksa:\n" + checked
    )


def load_pretrained_state_dict():
    """Muat bobot ImageNet lokal; fungsi ini tidak mengunduh data saat runtime."""
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch belum terpasang.")
    path = pretrained_weights_path()
    try:
        state = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        state = torch.load(path, map_location="cpu")
    if not isinstance(state, dict) or not state:
        raise ValueError(f"File bobot pretrained tidak valid: {path}")
    return state


if TORCH_AVAILABLE:
    class LegacySurveyMultiTaskNet(nn.Module):
        """Arsitektur CNN APRJ lama, untuk membaca checkpoint format terdahulu."""
        def __init__(self, task_classes):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1),
            )
            self.heads = nn.ModuleDict(
                {key: nn.Linear(128, len(values)) for key, values in task_classes.items()}
            )
            self.width_head = nn.Linear(128, len(SURVEY_WIDTH_FIELDS))

        def forward(self, images):
            features = self.features(images).flatten(1)
            return {
                "classes": {key: head(features) for key, head in self.heads.items()},
                "widths": self.width_head(features),
            }


    class SurveyMultiTaskNet(nn.Module):
        """ResNet-18 backbone dengan kepala klasifikasi dan regresi khusus survei."""
        def __init__(self, task_classes, pretrained_state_dict=None):
            super().__init__()
            try:
                from torchvision.models import resnet18
            except ImportError as error:
                raise RuntimeError(
                    "torchvision belum tersedia. Instal dependensi dari requirements.txt."
                ) from error
            self.backbone = resnet18(weights=None)
            self.backbone.fc = nn.Identity()
            if pretrained_state_dict is not None:
                incompatible = self.backbone.load_state_dict(pretrained_state_dict, strict=False)
                # ResNet ImageNet memiliki fc.* yang sengaja dibuang saat fc diganti Identity.
                unexpected = [key for key in incompatible.unexpected_keys if not key.startswith("fc.")]
                if incompatible.missing_keys or unexpected:
                    raise ValueError(
                        "Bobot ResNet-18 tidak cocok dengan arsitektur yang diharapkan. "
                        f"Missing={incompatible.missing_keys}; unexpected={unexpected}"
                    )
            self.heads = nn.ModuleDict(
                {key: nn.Linear(512, len(values)) for key, values in task_classes.items()}
            )
            self.width_head = nn.Linear(512, len(SURVEY_WIDTH_FIELDS))

        def forward(self, images):
            features = self.backbone(images)
            return {
                "classes": {key: head(features) for key, head in self.heads.items()},
                "widths": self.width_head(features),
            }


def image_to_tensor(image, augment=False):
    """Ubah PIL Image menjadi tensor RGB dengan normalisasi ImageNet."""
    if not TORCH_AVAILABLE:
        return None
    image = image.resize((IMAGE_SIZE, IMAGE_SIZE), image.Resampling.BILINEAR)
    if augment and random.random() < 0.5:
        image = image.transpose(image.Transpose.FLIP_LEFT_RIGHT)
    values = torch.frombuffer(bytearray(image.tobytes()), dtype=torch.uint8)
    values = values.reshape(IMAGE_SIZE, IMAGE_SIZE, 3).permute(2, 0, 1).float() / 255.0
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    return (values - mean) / std


class GoogleDriveColabManager:
    @staticmethod
    def generate_colab_training_notebook(destination_path):
        """Buat skrip awal untuk menyiapkan sesi training di Google Colab."""
        colab_script = '''# -*- coding: utf-8 -*-
"""Template awal training APRJ di Google Colab."""
from google.colab import drive
drive.mount('/content/drive')

import torch
print("PyTorch Version:", torch.__version__)
print("GPU Tersedia:", torch.cuda.is_available())
DATA_DIR = '/content/drive/MyDrive/APRJ_Dataset'
print("Direktori Dataset:", DATA_DIR)
print("Template siap. Hubungkan dataset berlabel dan kode training APRJ yang sesuai.")
'''
        Path(destination_path).write_text(colab_script, encoding="utf-8")
        return True, "Skrip Google Colab berhasil dibuat."
