APRJ - APLIKASI SURVEI JALAN PORTABLE
=====================================

BUILD
-----
1. Gunakan Windows 10/11 64-bit.
2. Instal Python 3.11 64-bit dari python.org dan pastikan Tcl/Tk ikut terpasang.
3. Buka folder enterprise, lalu jalankan build_portable.bat.
4. Hasil build berada di dist\APRJ\APRJ.exe.
5. Untuk memindahkan aplikasi, salin seluruh folder dist\APRJ, bukan hanya EXE.

ANTARMUKA
---------
- Survei Jalan: pemuatan foto, penilaian manual, navigasi foto, penyimpanan lokal,
  preview, dan ekspor Excel.
- Rekayasa AI: pengelolaan dataset terkonfirmasi dan kontrol pelatihan model.
- PKRMS: pembuatan template Excel, ekspor catatan survei, dan audit jumlah dataset.

DATA PORTABLE
-------------
Aplikasi menyimpan database dan berkas AI di folder data/survey_ai di samping
executable. Letakkan folder aplikasi pada lokasi yang dapat ditulis, misalnya
C:\Tools\APRJ, bukan di lokasi yang membatasi hak tulis.

BATASAN DAN VERIFIKASI
----------------------
- Template ekspor yang dibuat aplikasi adalah struktur kerja; validasi terhadap
  skema resmi PKRMS tetap perlu dilakukan.
- PyTorch CPU disertakan, tetapi tidak berarti model terlatih sudah tersedia.
  Hasil AI hanya dapat dianggap nyata setelah model dilatih/dimuat dan diuji.
- build_portable.bat menjalankan pemeriksaan sintaks. Pemeriksaan ini bukan
  pengganti uji GUI, uji alur data, atau pengujian hasil build di Windows.
- Build Windows belum dikonfirmasi berhasil di lingkungan pengembang; jalankan
  build_portable.bat pada Windows untuk memverifikasi hasil aktual.
