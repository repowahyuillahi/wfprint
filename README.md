# wfprint

Satu aplikasi kecil (`wfprint.exe`) pengganti **printer sharing SMB Windows** yang sering rusak setiap update Windows 10/11 (error `0x0000011b`, `0x00000709`).

Printer USB tetap colok di satu PC kantor. PC itu menjalankan `wfprint.exe --server`, yang mendengarkan port TCP **9100** dan meneruskan data cetak mentah ke printer USB via Windows Spooler. PC lain di LAN menambah printer ini sebagai **Standard TCP/IP Port** — tanpa SMB, tanpa share `\\PC\Nama` — lalu File > Print dari Word/Excel jalan normal seperti biasa.

Terinspirasi kemudahan setup [PrinterShare](https://printershare.net/index.php), tapi murni **LAN lokal**: tanpa cloud, tanpa akun, tanpa relay internet, tanpa aplikasi HP.

## Cara pakai

Download `dist/wfprint.exe`, atau jalankan dari source (Python 3.12, stdlib saja):

**1. Di PC yang colok printer USB (server):**

```powershell
wfprint.exe --server --bind 192.168.1.10 --port 9100 --printer "HP LaserJet Pro M12w"
```

Mapping port→printer tersimpan otomatis di `%APPDATA%\wfprint\config.json`, jadi restart cukup `--server --bind ...` saja. Log: `%APPDATA%\wfprint\wfprint.log`.

**2. Di tiap PC client — cek koneksi dulu:**

```powershell
wfprint.exe --client --host 192.168.1.10 --port 9100
```

**3. Pasang printer otomatis (PowerShell admin):**

```powershell
wfprint.exe --setup --host 192.168.1.10 --port 9100 --printer "Kantor-HP" --driver "HP LaserJet Pro M12w"
```

Ini membuat Standard TCP/IP Port + printer + siap dipakai. Lalu cetak test page:

```powershell
wfprint.exe --test-page --printer "Kantor-HP"
```

**4. Instalasi server sekali jalan (PowerShell admin):**

```powershell
scripts/install_server.ps1 -Port 9100 -Subnet "192.168.1.0/24"
```

Membuka firewall inbound khusus subnet LAN + autostart saat login.

## Cara kerja

1. Client File > Print → driver lokal me-render PCL/PS → spooler client kirim byte mentah via TCP ke server:9100.
2. Server menerima sampai FIN (timeout 30 dtk), lalu `OpenPrinter → StartDocPrinter → WritePrinter` per chunk 64KB → `EndDocPrinter` ke printer USB. Streaming, tanpa menampung satu job utuh di RAM.
3. Satu job aktif per printer (FIFO, antre ketat). Job kosong ditolak tanpa menyentuh spooler; printer offline/USB dicabut → job ditolak, koneksi ditutup, server tetap jalan.
4. Satu printer = satu port (9100, 9101, ...).

## Batasan

- Windows 10/11, LAN tepercaya (tanpa auth). Bind ke IP LAN eksplisit; firewall hanya subnet LAN.
- Driver di client harus sama dengan di server (Windows yang me-render, bukan wfprint).
- Tanpa IPP/status HTTP, tanpa service Windows (autostart registry, jalan saat user login), tanpa mobile.

## Pengembangan

```powershell
python -m unittest discover -s tests -v   # 15 test, stdlib unittest
python -m PyInstaller --onefile --console --name wfprint wfprint.py  # build exe
```

Struktur: `wfprint.py` (CLI dual-mode) · `wfprint/server.py` (TCP→spooler) · `wfprint/spool.py` (ctypes `winspool.drv`) · `wfprint/client.py` (probe + setup PowerShell) · `wfprint/config.py` · `tests/` · `docs/superpowers/` (spec + plan).

## Status

Fungsi inti + test lolos. Belum diuji di printer fisik — uji Word/Excel, 2 client bareng, dan cabut-USB diperlukan sebelum pemakaian produksi.
