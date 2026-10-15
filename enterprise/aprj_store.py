# -*- coding: utf-8 -*-
"""Penyimpanan survei lokal persisten berbasis SQLite (tanpa dependensi GUI)."""
import json
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


class SQLiteSurveyStore:
    """Simpan catatan survei per foto di SQLite.

    - Setiap operasi membuka lalu MENUTUP koneksinya (``with sqlite3.connect`` saja
      hanya commit/rollback dan membiarkan file terkunci pada Windows).
    - Database yang rusak (bukan sekadar terkunci) tidak dihapus: file dipindahkan ke
      ``<nama>.corrupt-<waktu>`` dan database baru dibuat. Penjelasannya ada di
      ``recovery_notice`` agar antarmuka dapat memberi tahu pengguna.
    - Baris dengan JSON rusak dilewati saat membaca, tetapi jumlahnya dicatat di
      ``skipped_rows`` dan tidak dihapus dari database.
    """

    def __init__(self, db_path, timeout=30):
        self.db_path = Path(db_path)
        self.timeout = timeout
        self.recovery_notice = None
        self.skipped_rows = 0
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._initialize()
        except sqlite3.OperationalError:
            # Terkunci, tidak bisa dibuka, dsb.: bukan bukti file rusak. Jangan diubah.
            raise
        except sqlite3.DatabaseError as error:
            self._quarantine_corrupt_database(error)
            self._initialize()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=self.timeout)
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    def _initialize(self):
        with closing(self._connect()) as conn:
            with conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS survey_records (
                        photo_key TEXT PRIMARY KEY,
                        folder_source TEXT NOT NULL DEFAULT '',
                        survey_data TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("SELECT COUNT(*) FROM survey_records").fetchone()

    def _quarantine_corrupt_database(self, error):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.db_path.with_name(f"{self.db_path.name}.corrupt-{stamp}")
        try:
            shutil.move(str(self.db_path), str(backup))
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(self.db_path) + suffix)
                if sidecar.exists():
                    shutil.move(str(sidecar), str(backup) + suffix)
        except OSError as move_error:
            raise sqlite3.DatabaseError(
                f"Database survei rusak ({error}) dan tidak dapat dipindahkan "
                f"ke cadangan: {move_error}"
            ) from error
        self.recovery_notice = (
            f"Database survei tidak dapat dibaca ({error}). "
            f"File asli disimpan di: {backup}. Database baru yang kosong dibuat; "
            "data lama dapat dipulihkan dari file tersebut."
        )

    def load_all(self):
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT photo_key, survey_data FROM survey_records").fetchall()
        result = {}
        skipped = 0
        for key, payload in rows:
            try:
                data = json.loads(payload)
            except (TypeError, ValueError):
                skipped += 1
                continue
            if isinstance(data, dict):
                result[key] = data
            else:
                skipped += 1
        self.skipped_rows = skipped
        return result

    def save(self, photo_key, data):
        payload = json.dumps(data, ensure_ascii=False)
        with closing(self._connect()) as conn:
            with conn:
                conn.execute("""
                    INSERT INTO survey_records(photo_key, folder_source, survey_data, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(photo_key) DO UPDATE SET
                        folder_source=excluded.folder_source,
                        survey_data=excluded.survey_data,
                        updated_at=CURRENT_TIMESTAMP
                """, (str(photo_key), str(data.get("folder", "")), payload))
