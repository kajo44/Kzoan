# -*- coding: utf-8 -*-
"""Tes regresi pembacaan/penyimpanan manifest dataset AI."""
import json
import tempfile
import unittest
from pathlib import Path

from aprj_core import load_record_manifest, save_record_manifest


class RecordManifestTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "dataset" / "labels.json"

    def test_missing_file_returns_empty_without_warning(self):
        self.assertEqual(load_record_manifest(self.path), ([], None))

    def test_roundtrip_keeps_unicode(self):
        records = [{"photo": "jalan_ü.jpg", "labels": {"kondisi": "baik"}}]
        save_record_manifest(self.path, records)
        loaded, warning = load_record_manifest(self.path)
        self.assertEqual(loaded, records)
        self.assertIsNone(warning)

    def test_corrupt_json_is_backed_up_and_reported(self):
        self.path.parent.mkdir(parents=True)
        original = '[{"photo": "a.jpg"'  # JSON terpotong
        self.path.write_text(original, encoding="utf-8")
        records, warning = load_record_manifest(self.path)
        self.assertEqual(records, [])
        self.assertIn("tidak dapat dibaca", warning)
        backups = list(self.path.parent.glob("labels.json.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), original)

    def test_saving_after_corrupt_load_keeps_original_copy(self):
        self.path.parent.mkdir(parents=True)
        original = "bukan json"
        self.path.write_text(original, encoding="utf-8")
        records, _ = load_record_manifest(self.path)
        save_record_manifest(self.path, records)
        backups = list(self.path.parent.glob("labels.json.corrupt-*"))
        self.assertEqual([b.read_text(encoding="utf-8") for b in backups], [original])

    def test_non_list_json_is_treated_as_corrupt(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"a": 1}), encoding="utf-8")
        records, warning = load_record_manifest(self.path)
        self.assertEqual(records, [])
        self.assertIn("bukan daftar record", warning)

    def test_non_dict_entries_are_counted_in_warning(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps([{"photo": "a.jpg"}, 5, "x"]), encoding="utf-8")
        records, warning = load_record_manifest(self.path)
        self.assertEqual(records, [{"photo": "a.jpg"}])
        self.assertIn("2 entri", warning)

    def test_save_keeps_previous_version_as_bak(self):
        save_record_manifest(self.path, [{"photo": "lama.jpg"}])
        save_record_manifest(self.path, [{"photo": "baru.jpg"}])
        bak = self.path.with_name("labels.json.bak")
        self.assertEqual(json.loads(bak.read_text(encoding="utf-8")), [{"photo": "lama.jpg"}])
        self.assertEqual(load_record_manifest(self.path)[0], [{"photo": "baru.jpg"}])
        self.assertFalse(self.path.with_name("labels.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
