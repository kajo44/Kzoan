APRJ - APLIKASI SURVEI JALAN PORTABLE
=====================================

BUILD
-----
1. Gunakan Windows 10/11 64-bit.
2. Instal Python 3.11 64-bit dari python.org dan pastikan Tcl/Tk ikut terpasang.
3. Buka folder enterprise, lalu jalankan build_portable.bat.
4. Hasil build berada di dist\APRJ\APRJ.exe.
5. Untuk memindahkan aplikasi, salin seluruh folder dist\APRJ, bukan hanya EXE.

ANTARMUKA TERPADU
-----------------
- Survei Jalan: pemuatan foto, penilaian manual, navigasi, preview, penyimpanan
  SQLite lokal, dan ekspor Excel.
- Rekayasa AI: pengelolaan dataset terkonfirmasi, impor hasil survei Excel,
  validasi dataset, kontrol training, dan pemeriksaan kesiapan inferensi.
- PKRMS: template Excel, ekspor catatan survei, audit foto, audit dataset
  klasifikasi lama, dan ekspor rekap dataset klasifikasi.
- Integrasi Online: ekspor skrip awal Google Colab, uji koneksi PostgreSQL,
  dan sinkronisasi catatan survei ke PostgreSQL.
- Entry point tunggal build adalah main.py yang memanggil APRJ_v2.py. Modul
  frontend.py lama dihapus setelah fitur UI-nya dipindahkan.

DATA PORTABLE
-------------
Aplikasi menyimpan database dan berkas AI di folder data/survey_ai di samping
executable. Letakkan folder aplikasi pada lokasi yang dapat ditulis, misalnya
C:\Tools\APRJ, bukan di lokasi yang membatasi hak tulis.

CATATAN PENTING
---------------
- Koneksi PostgreSQL memerlukan server yang dapat dijangkau, nama database,
  user, password, dan driver yang dipasang oleh build script.
- Skrip Colab yang diekspor saat ini adalah kerangka awal untuk menyiapkan
  Google Drive/PyTorch; skrip itu belum menjalankan training end-to-end.
- Kontrol training lokal masih berupa placeholder dan belum menjalankan loop
  training model penuh. Loader inferensi dan pemetaan output model juga belum
  selesai. Jangan menganggap prediksi AI tersedia hanya karena PyTorch/model
  file ada.
- Audit dataset menghitung berkas gambar dan tidak memvalidasi kebenaran label.
- Template PKRMS yang dibuat aplikasi adalah struktur kerja, bukan jaminan
  kesesuaian dengan semua skema resmi PKRMS. Validasi format tetap diperlukan.
- build_portable.bat menjalankan pemeriksaan sintaks; ini bukan pengganti uji
  GUI, uji koneksi PostgreSQL, pengujian alur data, atau pengujian hasil build.
- Build Windows belum dikonfirmasi berhasil di lingkungan pengembang. Jalankan
  build_portable.bat pada Windows untuk memverifikasi hasil aktual.
