# -*- coding: utf-8 -*-
"""Tes sinkronisasi PostgreSQL memakai psycopg2 palsu (tanpa server nyata).

Tes ini memeriksa logika pemilihan jalur, penghitungan, rollback, dan penutupan
koneksi. Perilaku terhadap server PostgreSQL sungguhan belum tercakup.
"""
import sys
import types
import unittest

import aprj_database
from aprj_database import DatabaseManager


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.last = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(str(sql).split())
        self.connection.statements.append((normalized, params))
        self.last = normalized
        if "CREATE UNIQUE INDEX" in normalized and self.connection.index_fails:
            raise RuntimeError("could not create unique index: duplicate key")
        if normalized.startswith("SELECT id FROM survey_results"):
            self.connection.select_calls += 1

    def fetchone(self):
        if self.last and self.last.startswith("SELECT id FROM survey_results"):
            return (1,) if self.connection.existing else None
        return (1,)


class FakeConnection:
    def __init__(self, index_fails=False, existing=False):
        self.statements = []
        self.index_fails = index_fails
        self.existing = existing
        self.select_calls = 0
        self.closed = False
        self.rolled_back = False
        self.committed = False

    def cursor(self):
        return FakeCursor(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.committed = True
        else:
            self.rolled_back = True
        return False

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def install_fake_execute_values(returned_flags):
    """Pasang psycopg2.extras.execute_values palsu; kembalikan daftar panggilannya."""
    calls = []

    def execute_values(cursor, sql, argslist, template=None, page_size=100, fetch=False):
        calls.append({"sql": " ".join(sql.split()), "rows": list(argslist), "fetch": fetch})
        return [(flag,) for flag in returned_flags]

    package = types.ModuleType("psycopg2")
    extras = types.ModuleType("psycopg2.extras")
    extras.execute_values = execute_values
    package.extras = extras
    previous = {name: sys.modules.get(name) for name in ("psycopg2", "psycopg2.extras")}
    sys.modules["psycopg2"] = package
    sys.modules["psycopg2.extras"] = extras

    def restore():
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    return calls, restore


class ManagerUnderTest(DatabaseManager):
    def __init__(self, connection):
        super().__init__()
        self._fake = connection

    def _connect(self):
        return self._fake


class PrepareRowsTests(unittest.TestCase):
    def test_duplicate_pairs_collapse_to_last_record(self):
        records = {
            "C:/a/foto1.jpg": {"filename": "foto1.jpg", "folder": "C:/a", "nilai": 1},
            "D:/b/foto1.jpg": {"filename": "foto1.jpg", "folder": "C:/a", "nilai": 2},
            "C:/a/foto2.jpg": {"nilai": 3},
        }
        rows = DatabaseManager._prepare_rows(records)
        self.assertEqual(len(rows), 2)
        by_key = {(photo, folder): payload for photo, folder, payload in rows}
        self.assertIn('"nilai": 2', by_key[("foto1.jpg", "C:/a")])
        self.assertIn(("foto2.jpg", "C:/a"), by_key)

    def test_non_dict_record_becomes_empty_object(self):
        rows = DatabaseManager._prepare_rows({"x/y.jpg": "bukan dict"})
        self.assertEqual(rows, [("y.jpg", "x", "{}")])


class SyncTests(unittest.TestCase):
    def test_upsert_path_counts_inserted_and_updated(self):
        calls, restore = install_fake_execute_values([True, True, False])
        self.addCleanup(restore)
        connection = FakeConnection()
        manager = ManagerUnderTest(connection)
        ok, message = manager.sync_to_postgres({
            "a/1.jpg": {}, "a/2.jpg": {}, "a/3.jpg": {},
        })
        self.assertTrue(ok, message)
        self.assertIn("Catatan baru: 2", message)
        self.assertIn("diperbarui: 1", message)
        self.assertNotIn("Peringatan", message)
        self.assertEqual(len(calls), 1)
        self.assertIn("ON CONFLICT (photo_name, folder_source) DO UPDATE", calls[0]["sql"])
        self.assertTrue(calls[0]["fetch"])
        self.assertEqual(connection.select_calls, 0)
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)

    def test_existing_duplicates_fall_back_with_warning_and_keep_transaction(self):
        calls, restore = install_fake_execute_values([])
        self.addCleanup(restore)
        connection = FakeConnection(index_fails=True, existing=True)
        manager = ManagerUnderTest(connection)
        ok, message = manager.sync_to_postgres({"a/1.jpg": {}})
        self.assertTrue(ok, message)
        self.assertIn("Peringatan", message)
        self.assertIn("diperbarui: 1", message)
        self.assertEqual(calls, [])
        sql = [statement for statement, _ in connection.statements]
        self.assertIn("ROLLBACK TO SAVEPOINT aprj_unique_index", sql)
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)

    def test_fallback_inserts_new_rows(self):
        _, restore = install_fake_execute_values([])
        self.addCleanup(restore)
        connection = FakeConnection(index_fails=True, existing=False)
        ok, message = ManagerUnderTest(connection).sync_to_postgres({"a/1.jpg": {}})
        self.assertTrue(ok, message)
        self.assertIn("Catatan baru: 1", message)

    def test_empty_records_do_nothing_but_succeed(self):
        calls, restore = install_fake_execute_values([])
        self.addCleanup(restore)
        connection = FakeConnection()
        ok, message = ManagerUnderTest(connection).sync_to_postgres({})
        self.assertTrue(ok, message)
        self.assertIn("Catatan baru: 0", message)
        self.assertEqual(calls, [])

    def test_failure_rolls_back_closes_and_reports(self):
        def failing_execute_values(*args, **kwargs):
            raise RuntimeError("server hilang")

        package = types.ModuleType("psycopg2")
        extras = types.ModuleType("psycopg2.extras")
        extras.execute_values = failing_execute_values
        package.extras = extras
        previous = {n: sys.modules.get(n) for n in ("psycopg2", "psycopg2.extras")}
        sys.modules["psycopg2"], sys.modules["psycopg2.extras"] = package, extras

        def restore():
            for name, module in previous.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

        self.addCleanup(restore)
        connection = FakeConnection()
        ok, message = ManagerUnderTest(connection).sync_to_postgres({"a/1.jpg": {}})
        self.assertFalse(ok)
        self.assertIn("server hilang", message)
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.closed)

    def test_connection_failure_is_reported_without_crash(self):
        class Unreachable(DatabaseManager):
            def _connect(self):
                raise OSError("tidak dapat terhubung")

        ok, message = Unreachable().sync_to_postgres({"a/1.jpg": {}})
        self.assertFalse(ok)
        self.assertIn("tidak dapat terhubung", message)
        ok, message = Unreachable().test_connection()
        self.assertFalse(ok)
        self.assertIn("tidak dapat terhubung", message)

    def test_test_connection_closes_connection(self):
        connection = FakeConnection()
        ok, _ = ManagerUnderTest(connection).test_connection()
        self.assertTrue(ok)
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
