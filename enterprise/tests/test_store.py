# -*- coding: utf-8 -*-
"""Tes regresi penyimpanan survei SQLite."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aprj_store
from aprj_store import SQLiteSurveyStore


class TrackingConnection(sqlite3.Connection):
    opened = 0
    closed = 0

    def close(self):
        type(self).closed += 1
        super().close()


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "data" / "survey.sqlite3"

    def test_creates_parent_folder_and_roundtrips_unicode(self):
        store = SQLiteSurveyStore(self.path)
        store.save("jalan/ü.jpg", {"folder": "jalan", "kondisi": "baik"})
        store.save("jalan/ü.jpg", {"folder": "jalan", "kondisi": "rusak_ringan"})
        loaded = store.load_all()
        self.assertEqual(loaded, {"jalan/ü.jpg": {"folder": "jalan", "kondisi": "rusak_ringan"}})
        self.assertIsNone(store.recovery_notice)
        self.assertEqual(store.skipped_rows, 0)

    def test_every_connection_is_closed(self):
        TrackingConnection.opened = TrackingConnection.closed = 0
        real_connect = sqlite3.connect

        def tracking_connect(*args, **kwargs):
            TrackingConnection.opened += 1
            return real_connect(*args, factory=TrackingConnection, **kwargs)

        with mock.patch.object(aprj_store.sqlite3, "connect", tracking_connect):
            store = SQLiteSurveyStore(self.path)
            store.save("a.jpg", {"folder": "x"})
            store.load_all()
        self.assertGreaterEqual(TrackingConnection.opened, 3)
        self.assertEqual(TrackingConnection.opened, TrackingConnection.closed)

    def test_corrupt_database_is_quarantined_not_deleted(self):
        self.path.parent.mkdir(parents=True)
        original = b"ini bukan database sqlite" * 50
        self.path.write_bytes(original)
        store = SQLiteSurveyStore(self.path)
        self.assertIn("tidak dapat dibaca", store.recovery_notice)
        backups = list(self.path.parent.glob("survey.sqlite3.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        store.save("a.jpg", {"folder": "x"})
        self.assertEqual(list(store.load_all()), ["a.jpg"])

    def test_locked_database_is_not_treated_as_corrupt(self):
        store = SQLiteSurveyStore(self.path)
        store.save("a.jpg", {"folder": "x"})
        before = self.path.read_bytes()
        blocker = sqlite3.connect(str(self.path))
        self.addCleanup(blocker.close)
        blocker.execute("BEGIN IMMEDIATE")
        impatient = SQLiteSurveyStore.__new__(SQLiteSurveyStore)
        impatient.db_path, impatient.timeout = self.path, 0.1
        with self.assertRaises(sqlite3.OperationalError):
            impatient.save("b.jpg", {"folder": "y"})
        blocker.rollback()
        self.assertEqual(list(self.path.parent.glob("*.corrupt-*")), [])
        self.assertEqual(self.path.read_bytes(), before)

    def test_bad_json_rows_are_counted_and_kept(self):
        store = SQLiteSurveyStore(self.path)
        store.save("ok.jpg", {"folder": "x"})
        with sqlite3.connect(str(self.path)) as conn:
            conn.execute(
                "INSERT INTO survey_records(photo_key, folder_source, survey_data) VALUES (?, '', ?)",
                ("rusak.jpg", "{bukan json"),
            )
            conn.execute(
                "INSERT INTO survey_records(photo_key, folder_source, survey_data) VALUES (?, '', ?)",
                ("daftar.jpg", "[1, 2]"),
            )
        conn.close()
        loaded = store.load_all()
        self.assertEqual(list(loaded), ["ok.jpg"])
        self.assertEqual(store.skipped_rows, 2)
        with sqlite3.connect(str(self.path)) as check:
            count = check.execute("SELECT COUNT(*) FROM survey_records").fetchone()[0]
        check.close()
        self.assertEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
