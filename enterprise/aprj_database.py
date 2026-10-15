# -*- coding: utf-8 -*-
"""Integrasi PostgreSQL untuk sinkronisasi catatan survei jalan.

SQLite tetap menjadi penyimpanan lokal utama; PostgreSQL adalah target sinkronisasi.
"""
import json
import os

UNIQUE_INDEX_NAME = "survey_results_photo_folder_uidx"
UPSERT_PAGE_SIZE = 500


class DatabaseManager:
    def __init__(self, host="localhost", port=5432, database="aprj_db", user="postgres", password=""):
        self.config = {
            "host": host,
            "port": int(port),
            "database": database,
            "user": user,
            "password": password,
            "connect_timeout": 8,
        }

    def _connect(self):
        import psycopg2
        return psycopg2.connect(**self.config)

    def test_connection(self):
        """Uji koneksi tanpa mengubah data."""
        conn = None
        try:
            conn = self._connect()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True, "Koneksi PostgreSQL berhasil."
        except Exception as error:
            return False, str(error)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def _prepare_rows(survey_records):
        """Ubah catatan menjadi baris unik per (photo_name, folder_source).

        Bila beberapa kunci menghasilkan pasangan yang sama, catatan terakhir dipakai;
        ON CONFLICT tidak boleh menerima pasangan yang sama dua kali dalam satu perintah.
        """
        rows = {}
        for record_key, raw_data in survey_records.items():
            data = raw_data if isinstance(raw_data, dict) else {}
            key_text = str(record_key)
            photo_name = str(data.get("filename") or os.path.basename(key_text) or key_text)
            folder_source = str(data.get("folder") or os.path.dirname(key_text) or "")
            payload = json.dumps(data, ensure_ascii=False, default=str)
            rows[(photo_name, folder_source)] = payload
        return [(photo, folder, payload) for (photo, folder), payload in rows.items()]

    @staticmethod
    def _ensure_unique_index(cursor):
        """Buat unique index; False bila data lama sudah mengandung duplikat.

        Data yang sudah ada tidak dihapus atau digabung otomatis. Kegagalan dibatasi
        dalam savepoint agar transaksi sinkronisasi tidak ikut gagal.
        """
        cursor.execute("SAVEPOINT aprj_unique_index")
        try:
            cursor.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {UNIQUE_INDEX_NAME} "
                "ON survey_results (photo_name, folder_source)"
            )
        except Exception:
            cursor.execute("ROLLBACK TO SAVEPOINT aprj_unique_index")
            return False
        cursor.execute("RELEASE SAVEPOINT aprj_unique_index")
        return True

    @staticmethod
    def _upsert_with_index(cursor, rows):
        from psycopg2.extras import execute_values

        if not rows:
            return 0, 0
        results = execute_values(
            cursor,
            """
            INSERT INTO survey_results (photo_name, folder_source, survey_data)
            VALUES %s
            ON CONFLICT (photo_name, folder_source) DO UPDATE
                SET survey_data = EXCLUDED.survey_data,
                    updated_at = CURRENT_TIMESTAMP
            RETURNING (xmax = 0)
            """,
            rows,
            template="(%s, %s, %s::jsonb)",
            page_size=UPSERT_PAGE_SIZE,
            fetch=True,
        )
        inserted = sum(1 for (is_insert,) in results if is_insert)
        return inserted, len(results) - inserted

    @staticmethod
    def _upsert_without_index(cursor, rows):
        """Jalur lama untuk tabel yang sudah punya duplikat; memperbarui baris pertama."""
        inserted = updated = 0
        for photo_name, folder_source, payload in rows:
            cursor.execute("""
                SELECT id FROM survey_results
                WHERE photo_name = %s AND folder_source = %s
                ORDER BY id LIMIT 1
            """, (photo_name, folder_source))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE survey_results
                    SET survey_data = %s::jsonb, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (payload, existing[0]))
                updated += 1
            else:
                cursor.execute("""
                    INSERT INTO survey_results (photo_name, folder_source, survey_data)
                    VALUES (%s, %s, %s::jsonb)
                """, (photo_name, folder_source, payload))
                inserted += 1
        return inserted, updated

    def sync_to_postgres(self, survey_records):
        """Sinkronkan catatan, memperbarui pasangan foto+folder bila sudah ada."""
        conn = None
        try:
            rows = self._prepare_rows(survey_records)
            conn = self._connect()
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
                    has_unique_index = self._ensure_unique_index(cursor)
                    if has_unique_index:
                        inserted, updated = self._upsert_with_index(cursor, rows)
                    else:
                        inserted, updated = self._upsert_without_index(cursor, rows)
            message = (
                f"Sinkronisasi selesai. Catatan baru: {inserted}; "
                f"catatan diperbarui: {updated}."
            )
            if not has_unique_index:
                message += (
                    " Peringatan: tabel survey_results sudah berisi pasangan foto+folder ganda, "
                    "sehingga indeks unik tidak dapat dibuat dan pengiriman ulang masih bisa "
                    "menimbulkan duplikat jika dua sinkronisasi berjalan bersamaan. "
                    "Bersihkan duplikat secara manual lalu sinkronkan lagi."
                )
            return True, message
        except Exception as error:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False, str(error)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
