# -*- coding: utf-8 -*-
"""Model multi-task untuk klasifikasi kondisi dan tipe perkerasan jalan."""
from pathlib import Path
import random

from core import CLASSES, SURFACE_CLASSES, IMAGE_SIZE, SURVEY_AI_MODELS

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False

SURVEY_WIDTH_FIELDS = ("lebar_bahu_kiri", "lebar_drainase_kiri", "lebar_perkerasan", "lebar_bahu_kanan", "lebar_drainase_kanan")
TASK_CLASSES = {"condition": CLASSES, "surface_type": SURFACE_CLASSES}
DEFAULT_CHECKPOINT = SURVEY_AI_MODELS / "aprj_multitask.pt"


if TORCH_AVAILABLE:
    class SurveyMultiTaskNet(nn.Module):
        def __init__(self, task_classes=None):
            super().__init__()
            task_classes = task_classes or TASK_CLASSES
            self.features = nn.Sequential(
                nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
                nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
                nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool2d(1),
            )
            self.heads = nn.ModuleDict({
                key: nn.Linear(128, len(values)) for key, values in task_classes.items()
            })
            self.width_head = nn.Linear(128, len(SURVEY_WIDTH_FIELDS))

        def forward(self, images):
            features = self.features(images).flatten(1)
            return {
                "classes": {key: head(features) for key, head in self.heads.items()},
                "widths": self.width_head(features),
            }


def image_to_tensor(image, augment=False):
    """Normalisasi gambar ke RGB dan tensor ImageNet; aman untuk grayscale/RGBA."""
    if not TORCH_AVAILABLE:
        return None
    from PIL import Image, ImageOps
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = image.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
    if augment and random.random() < 0.5:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    values = torch.frombuffer(bytearray(image.tobytes()), dtype=torch.uint8)
    values = values.reshape(IMAGE_SIZE, IMAGE_SIZE, 3).permute(2, 0, 1).float() / 255.0
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    return (values - mean) / std


class ModelInference:
    """Memuat checkpoint lokal; tidak pernah mengarang prediksi jika model tidak tersedia."""

    def __init__(self, checkpoint=DEFAULT_CHECKPOINT, device=None):
        self.checkpoint = Path(checkpoint)
        self.device = device or ("cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu")
        self.model = None
        self.error = None
        self._load()

    @property
    def available(self):
        return self.model is not None

    def _load(self):
        if not TORCH_AVAILABLE:
            self.error = "PyTorch belum terpasang."
            return
        if not self.checkpoint.is_file():
            self.error = f"Checkpoint model belum tersedia: {self.checkpoint}"
            return
        try:
            payload = torch.load(str(self.checkpoint), map_location=self.device, weights_only=False)
            if isinstance(payload, dict) and "model_state_dict" in payload:
                state = payload["model_state_dict"]
            elif isinstance(payload, dict) and "state_dict" in payload:
                state = payload["state_dict"]
            elif isinstance(payload, dict):
                state = payload
            else:
                raise ValueError("Format checkpoint tidak dikenal.")
            self.model = SurveyMultiTaskNet(TASK_CLASSES).to(self.device)
            self.model.load_state_dict(state, strict=True)
            self.model.eval()
            self.error = None
        except Exception as exc:
            self.model = None
            self.error = f"Checkpoint tidak cocok atau gagal dimuat: {exc}"

    def predict(self, image):
        if not self.available:
            raise RuntimeError(self.error or "Model tidak tersedia.")
        tensor = image_to_tensor(image)
        if tensor is None:
            raise RuntimeError("PyTorch tidak tersedia.")
        with torch.inference_mode():
            output = self.model(tensor.unsqueeze(0).to(self.device))
            result = {}
            for task, labels in TASK_CLASSES.items():
                logits = output["classes"][task][0]
                probabilities = torch.softmax(logits, dim=0)
                index = int(torch.argmax(probabilities).item())
                result[task] = {
                    "label": labels[index],
                    "confidence": float(probabilities[index].item()),
                }
            return result


class GoogleDriveColabManager:
    @staticmethod
    def generate_colab_training_notebook(destination_path):
        """Buat template pelatihan yang secara eksplisit menandai kebutuhan dataset dan kode training."""
        script = '''# Template pelatihan APRJ - Google Colab
# Ini bukan model terlatih. Siapkan dataset berlabel, lalu implementasikan training/validasi
# sesuai arsitektur SurveyMultiTaskNet sebelum menyimpan checkpoint.
from google.colab import drive
drive.mount("/content/drive")
import torch
print("PyTorch:", torch.__version__)
print("GPU tersedia:", torch.cuda.is_available())
print("Siapkan dataset train/validation dan evaluasi metrik sebelum deployment.")
'''
        Path(destination_path).write_text(script, encoding="utf-8")
        return True, "Template Colab disimpan. Template ini belum melatih model."
