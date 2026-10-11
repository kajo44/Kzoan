# -*- coding: utf-8 -*-
"""
Modul Database: Integrasi PostgreSQL untuk Penyimpanan Data Survei Jalan.
Menyediakan fitur tes koneksi dan sinkronisasi data JSONB ke server relasional.
"""

import json

class DatabaseManager:
    def __init__(self, host="localhost", port=5432, database="aprj_db", user="postgres", password=""):
        self.config = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }

    def test_connection(self):
        """Menguji koneksi ke server PostgreSQL."""
        try:
            import psycopg2
            conn = psycopg2.connect(**self.config)
            conn.close()
            return True, "Koneksi PostgreSQL Berhasil."
        except Exception as e:
            return False, str(e)

    def sync_to_postgres(self, survey_records):
        """Menyinkronkan rekaman survei jalan ke tabel PostgreSQL menggunakan JSONB."""
        try:
            import psycopg2
            conn = psycopg2.connect(**self.config)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS survey_results (
                    id SERIAL PRIMARY KEY,
                    photo_name TEXT,
                    folder_source TEXT,
                    survey_data JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            for filename, data in survey_records.items():
                cursor.execute("""
                    INSERT INTO survey_results (photo_name, folder_source, survey_data)
                    VALUES (%s, %s, %s);
                """, (filename, data.get("folder", ""), json.dumps(data)))
                
            conn.commit()
            cursor.close()
            conn.close()
            return True, "Sinkronisasi data survei ke PostgreSQL berhasil."
        except Exception as e:
            return False, str(e)