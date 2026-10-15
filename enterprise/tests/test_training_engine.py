# -*- coding: utf-8 -*-
"""Tes bagian training engine yang tidak membutuhkan PyTorch.

Training, inferensi, dan penyimpanan checkpoint sesungguhnya TIDAK tercakup di sini
(PyTorch tidak dipasang pada lingkungan tes otomatis).
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aprj_training_engine as engine


class CollectBatchTests(unittest.TestCase):
    def test_unreadable_photos_are_reported_not_dropped_silently(self):
        def fake_tensor(path, size):
            if "rusak" in path:
                raise OSError("file korup")
            return f"tensor:{path}:{size}"

        batch = [
            {"path": "a.jpg", "labels": {"kondisi": "baik"}},
            {"path": "rusak.jpg", "labels": {"kondisi": "rusak_berat"}},
            {"path": "b.jpg", "labels": {"kondisi": "baik"}},
        ]
        skipped = {}
        with mock.patch.object(engine, "_image_tensor", fake_tensor):
            images, labels = engine._collect_batch(batch, 224, skipped)
        self.assertEqual(images, ["tensor:a.jpg:224", "tensor:b.jpg:224"])
        self.assertEqual(labels, [{"kondisi": "baik"}, {"kondisi": "baik"}])
        self.assertEqual(list(skipped), ["rusak.jpg"])
        self.assertIn("OSError", skipped["rusak.jpg"])
        self.assertIn("file korup", skipped["rusak.jpg"])

    def test_same_photo_is_recorded_once_across_epochs(self):
        skipped = {}
        with mock.patch.object(engine, "_image_tensor", side_effect=ValueError("x")):
            engine._collect_batch([{"path": "p.jpg", "labels": {}}], 224, skipped)
            engine._collect_batch([{"path": "p.jpg", "labels": {}}], 224, skipped)
        self.assertEqual(len(skipped), 1)


class ModelCacheTests(unittest.TestCase):
    def setUp(self):
        engine.clear_model_cache()
        self.addCleanup(engine.clear_model_cache)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.checkpoint = Path(self._tmp.name) / "model.pth"
        self.checkpoint.write_bytes(b"v1")

    def test_checkpoint_is_loaded_once_for_repeated_predictions(self):
        with mock.patch.object(engine, "load_model", return_value=("m", {"k": 1}, "cpu")) as loader:
            first = engine.get_cached_model(self.checkpoint, "CPU")
            second = engine.get_cached_model(self.checkpoint, "CPU")
        self.assertIs(first, second)
        self.assertEqual(loader.call_count, 1)

    def test_cache_is_invalidated_when_checkpoint_changes(self):
        with mock.patch.object(engine, "load_model", side_effect=lambda *a: (object(), {}, "cpu")) as loader:
            first = engine.get_cached_model(self.checkpoint, "CPU")
            self.checkpoint.write_bytes(b"versi-baru-lebih-panjang")
            stat = self.checkpoint.stat()
            os.utime(self.checkpoint, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
            second = engine.get_cached_model(self.checkpoint, "CPU")
        self.assertIsNot(first, second)
        self.assertEqual(loader.call_count, 2)

    def test_different_device_is_a_different_cache_entry(self):
        with mock.patch.object(engine, "load_model", side_effect=lambda *a: (object(), {}, "x")) as loader:
            engine.get_cached_model(self.checkpoint, "CPU")
            engine.get_cached_model(self.checkpoint, "GPU (CUDA)")
        self.assertEqual(loader.call_count, 2)

    def test_missing_checkpoint_reports_the_original_error(self):
        # Tanpa PyTorch -> RuntimeError; dengan PyTorch -> FileNotFoundError. Keduanya
        # berasal dari load_model, bukan KeyError/None dari cache.
        with self.assertRaises((RuntimeError, FileNotFoundError)):
            engine.get_cached_model(Path(self._tmp.name) / "tidak_ada.pth", "CPU")


if __name__ == "__main__":
    unittest.main()
