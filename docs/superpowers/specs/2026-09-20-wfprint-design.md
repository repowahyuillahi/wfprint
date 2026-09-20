# wfprint — Design Spec (2026-09-20)

## 1. Tujuan
- Ganti SMB printer sharing rapuh kena update Windows 10/11 (error 0x0000011b, 0x00000709).
- Printer USB colok 1 PC Windows kantor. Client LAN tetap File > Print dari Word/Excel normal.
- Cakupan: LAN saja. Tanpa cloud/relay internet, tanpa mobile. Inspirasi PrinterShare: **satu exe dual-mode** (server/client), kemudahan setup lokal.

## 2. Batasan
- Server & client pakai **satu exe** `wfprint.exe`. Mode dipilih via argumen: `--server` atau `--client`.
- Repo `print-server/` kosong. Proyek baru, tanpa flow lama.
- Stdlib/BCL dulu. Tanpa driver virtual, tanpa installer driver signed, tanpa dependensi baru.
- Satu printer = satu port TCP. Printer pertama 9100, berikutnya 9101, dst.

## 3. Kriteria sukses
- Client tambah printer via Standard TCP/IP Port ke IP server:9100, driver sama dengan server, test page keluar.
- File > Print Word/Excel jalan normal dari tiap client.
- Update Windows tidak putuskan cetak (tanpa SMB/RPC).
- 2 client cetak bareng: hasil benar berurutan (FIFO), tanpa halaman tercampur.
- Cabut USB saat cetak: job gagal jelas di log, koneksi ditutup, server tetap jalan.
- Restart server saat antre: client dapat error konek jelas, bukan hang.

## 4. Arsitektur (diperbarui: single-exe dual-mode)
- `wfprint.exe --server` di PC USB: `TcpListener` 9100/printer → teruskan byte mentah ke USB via `OpenPrinter/StartDocPrinter/WritePrinter/EndDocPrinter` (`winspool.drv`). Antre 1 job aktif per printer (FIFO). Tray icon, autostart registry, log file.
- `wfprint.exe --client` di tiap client: bukan driver virtual. Helper setup: cek TCP, buat Standard TCP/IP Port + printer via PowerShell (`Add-PrinterPort`, `Add-Printer`), cetak test page, pesan error jelas.
- Tanpa SMB. Client anggap server sebagai printer IP (`192.168.1.10:9100`), bukan share `\\PC\Nama`.
- Konfigurasi server disimpan di `%APPDATA%\wfprint\config.json` (port→printer mapping). Client menyimpan last-used server IP di registry.

## 5. Data flow (disetujui)
1. Client File > Print → driver lokal render PCL/PS.
2. Spooler client kirim byte mentah via TCP ke server:9100.
3. Server terima utuh sampai FIN (timeout terima 30 dtk).
4. Server `OpenPrinter` → `StartDocPrinter` → `WritePrinter` (chunk) → `EndDocPrinter` ke printer USB.
5. Tutup koneksi. Job berikutnya diproses FIFO.
6. Timeout fase cetak ikut timeout spooler Windows (tanpa timeout custom).

## 6. Konfigurasi
- Server: daftar mapping `port → nama printer Windows lokal` (contoh `9100 → "HP LaserJet Pro M12w"`). UI tray minimal: daftar printer, port, status, tombol start/stop, lihat log.
- Autostart: registry `HKCU\...\Run` (tanpa service dulu; `ponytail:` naik ke Windows Service bila butuh jalan tanpa login).
- Firewall: installer buka inbound TCP 9100+ hanya untuk subnet LAN (bukan publik).
- Client: input IP server + port + nama printer + pilihan driver. Default port 9100.

## 7. Error handling (disetujui)
- Bind gagal (port dipakai): log jelas + exit, tanpa crash diam.
- Printer offline/USB dicabut: tolak job baru, kirim RST, tulis log `printer offline: <nama>`.
- `WritePrinter` gagal tengah job: `EndDocPrinter`/`Abort`, tutup koneksi, log job-id + byte terkirim.
- Client gagal konek: pesan `cek IP/port, firewall server, wfprint-server jalan`.
- Semua error tulis log dengan timestamp, printer, port, client IP.

## 8. Keamanan
- Dengarkan hanya di interface LAN. Tanpa binding `0.0.0.0` publik bila ada NIC ganda — pilih IP LAN eksplisit.
- Firewall rule cakup subnet LAN saja.
- Tanpa auth dulu (LAN kantor dipercaya). `ponytail:` tambah token pre-shared per port bila segmen LAN tidak dipercaya.

## 9. Testing
- Test page bawaan dari `wfprint.exe --client`.
- Print Word 1 halaman + Excel 3 halaman dari 2 client beda.
- Uji bareng: 2 client kirim bersamaan → cek urutan utuh.
- Uji cabut USB saat cetak → log jelas, server hidup.
- Uji restart server saat antre → client error jelas, cetak ulang sukses setelah server naik.
- Self-check: assert satu arah — byte diterima == byte ditulis ke spooler (satu test kecil, tanpa framework).

## 10. Non-goals
- Tanpa relay/cloud, tanpa akun, tanpa mobile Android/iOS.
- Tanpa IPP dulu (tambah bila butuh nama multi-printer/status HTTP).
- Tanpa driver virtual signed.
- Tanpa upload-via-browser sebagai jalur utama.

## 11. Keputusan terbuka
- Tidak ada. Arsitektur, flow, error handling sudah disetujui user 2026-09-20.