# -*- coding: utf-8 -*-
"""Penyimpanan survei SQLite lokal dan sinkronisasi opsional ke PostgreSQL."""
import json
import sqlite3
from pathlib import Path


class SQLiteSurveyStore:
    """Penyimpanan lokal persisten; kunci rekaman adalah path foto relatif."""

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self):
        connection = sqlite3.connect(str(self.db_path), timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS survey_records (
                    photo_key TEXT PRIMARY KEY,
                    folder_source TEXT NOT NULL DEFAULT '',
                    survey_data TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_survey_updated_at ON survey_records(updated_at)")

    def load_all(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT photo_key, survey_data FROM survey_records").fetchall()
        records = {}
        for row in rows:
            try:
                value = json.loads(row["survey_data"])
                if isinstance(value, dict):
                    records[row["photo_key"]] = value
            except (TypeError, json.JSONDecodeError):
                # Abaikan rekaman korup tanpa menghentikan pemuatan rekaman lain.
                continue
        return records

    def save(self, photo_key, data):
        if not photo_key:
            raise ValueError("Kunci foto tidak boleh kosong.")
        payload = json.dumps(data, ensure_ascii=False)
        folder = str(data.get("folder", ""))
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO survey_records(photo_key, folder_source, survey_data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(photo_key) DO UPDATE SET
                    folder_source=excluded.folder_source,
                    survey_data=excluded.survey_data,
                    updated_at=CURRENT_TIMESTAMP
            """, (str(photo_key), folder, payload))

    def save_many(self, records):
        with self._connect() as conn:
            conn.executemany("""
                INSERT INTO survey_records(photo_key, folder_source, survey_data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(photo_key) DO UPDATE SET
                    folder_source=excluded.folder_source,
                    survey_data=excluded.survey_data,
                    updated_at=CURRENT_TIMESTAMP
            """, [
                (str(key), str(data.get("folder", "")), json.dumps(data, ensure_ascii=False))
                for key, data in records.items()
            ])


class DatabaseManager:
    def __init__(self, host="localhost", port=5432, database="aprj_db", user="postgres", password=""):
        self.config = {
            "host": host, "port": port, "database": database,
            "user": user, "password": password,
        }

    def test_connection(self):
        conn = None
        try:
            import psycopg2
            conn = psycopg2.connect(**self.config)
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True, "Koneksi PostgreSQL berhasil."
        except Exception as exc:
            return False, str(exc)
        finally:
            if conn is not None:
                conn.close()

    def sync_to_postgres(self, survey_records):
        """Sinkronisasi idempoten: rekaman foto yang sama diperbarui, bukan ditambah terus."""
        conn = None
        try:
            import psycopg2
            conn = psycopg2.connect(**self.config)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS survey_results (
                            id BIGSERIAL PRIMARY KEY,
                            photo_name TEXT NOT NULL,
                            folder_source TEXT NOT NULL DEFAULT '',
                            survey_data JSONB NOT NULL,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    for photo_key, data in survey_records.items():
                        folder = str(data.get("folder", ""))
                        # DELETE+INSERT avoids duplicates even for older tables without a unique index.
                        cursor.execute(
                            "DELETE FROM survey_results WHERE photo_name = %s AND folder_source = %s",
                            (str(photo_key), folder),
                        )
                        cursor.execute("""
                            INSERT INTO survey_results(photo_name, folder_source, survey_data, updated_at)
                            VALUES (%s, %s, %s::jsonb, CURRENT_TIMESTAMP)
                        """, (str(photo_key), folder, json.dumps(data, ensure_ascii=False)))
            return True, f"Sinkronisasi PostgreSQL berhasil: {len(survey_records)} rekaman diproses."
        except Exception as exc:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False, str(exc)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
