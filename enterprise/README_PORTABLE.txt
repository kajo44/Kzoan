APRJ - APLIKASI SURVEI JALAN PORTABLE
=====================================

BUILD
-----
1. Gunakan Windows 10/11 64-bit.
2. Instal Python 3.11 64-bit dari python.org. Pastikan Tcl/Tk ikut terpasang.
3. Buka folder enterprise di terminal, lalu jalankan build_portable.bat.
4. Hasil build berada di dist\APRJ\APRJ.exe.
5. Untuk memindahkan aplikasi ke komputer lain, salin seluruh folder dist\APRJ,
   bukan hanya APRJ.exe.

STRUKTUR PORTABLE
-----------------
Aplikasi membuat folder data lokal di samping executable, misalnya:
- data / survey_ai
- dataset
- downloads
- config
- logs

Letakkan folder aplikasi di lokasi yang dapat ditulis oleh pengguna, misalnya
C:\Tools\APRJ atau folder lain di luar Program Files.

CATATAN FITUR
-------------
- Entry point build adalah main.py, yang menggunakan frontend.py, core.py,
  database.py, ai_model.py, dan pkrms_utils.py.
- APRJ_v2.py adalah implementasi GUI terpisah/alternatif dan bukan entry point
  build default. File itu ikut diperiksa sintaksnya, tetapi tidak dijalankan
  sebagai GUI kedua.
- Fitur koneksi PostgreSQL memerlukan server PostgreSQL yang dapat dijangkau
  dan kredensial yang sesuai.
- Kode AI memiliki arsitektur model, tetapi loader inferensi dan pipeline
  training end-to-end belum selesai. Aplikasi tidak boleh dianggap menghasilkan
  prediksi AI nyata sampai bagian tersebut diimplementasikan dan diuji.
- PyTorch CPU disertakan dalam build ini; ini tidak berarti model AI terlatih
  ikut disertakan.
- Build harus dilakukan pada Windows untuk menghasilkan aplikasi Windows.
- Build script menjalankan py_compile sebagai pemeriksaan sintaks, tetapi
  pemeriksaan sintaks bukan pengganti pengujian GUI dan pengujian alur kerja.
