# ⌨️ TeleKeyboard untuk Windows 10 & 11

**TeleKeyboard Windows** adalah remote control dan keyboard nirkabel untuk PC/Laptop Windows Anda yang dioperasikan sepenuhnya melalui Bot Telegram. Dikembangkan dan disempurnakan dari hasil *reverse engineering* versi macOS, kini sepenuhnya dioptimalkan secara native untuk **Windows 10 dan Windows 11**.

---

## 🚀 Fitur Unggulan

- 🎮 **Remote Keyboard & Emulasi Tombol**: Navigasi panah, Enter, Spasi, Backspace, Esc, Tab, Delete, shortcut Windows (`Ctrl+C`, `Ctrl+V`, `Ctrl+Z`, `Alt+Tab`, `Alt+F4`, `Win+D`, dll).
- ⌨️ **Ketik Teks & Mode Langsung**: `/type <teks>` untuk mengetik langsung (support emoji Unicode via clipboard injection) atau `/mode` untuk mode ketik interaktif.
- ⚡ **Power Management**: `/shutdown` (jeda 15 detik), `/shutdown now` (seketika), `/shutdown_cancel`, `/restart`, `/sleep`, `/lock`, dan `/wake`. Dilengkapi tombol konfirmasi aman agar tidak terpencet.
- 📂 **File Explorer & Shortcuts**: Jelajahi folder Windows langsung dari Telegram (Desktop, Downloads, Documents, Pictures, Drive C:\, D:\) dengan tombol interaktif dan paginasi.
- 📥 **Download Dua Arah (PC ↔ Telegram)**:
  - Download file dari Windows ke Telegram: `/download <path_file>` atau klik tombol di file browser.
  - Upload file dari Telegram ke Windows: Kirim file/foto apa saja ke bot, otomatis tersimpan ke folder `Downloads` PC.
- 🔊 **Audio & Media Control**: Atur volume master 0–100% via CoreAudio (`/vol 50`), mute/unmute (`/mute`), dan play/pause (`/media`).
- 📸 **Screenshot & Webcam**: Tangkapan layar DPI-aware tanpa blur (`/ss` atau `/ssfull`) dan foto webcam laptop via DirectShow (`/cam`).
- ℹ️ **Status Sistem Real-time**: Cek CPU, beban RAM, hard disk, baterai & charger, uptime, IP lokal, dan IP publik (`/info` atau `/diag`).
- 🤫 **Zero CMD & Notepad Status**: Berjalan 100% hening di background tanpa jendela hitam CMD, dan memunculkan konfirmasi Notepad bertuliskan `terhubung ke keyboard`.
- ⚡ **Jalankan via Win + R**: Bisa dijalankan kapan saja dengan menekan tombol **Win + R** lalu ketik **`telekeyboard`** atau **`tk`**.

---

## 🛠 Panduan Instalasi & Penggunaan

### 1. Konfigurasi Bot Telegram
Salin atau ganti nama file `config.example.json` menjadi `config.json`, lalu isi Token dan Chat ID Telegram Anda:
```json
{
  "bot_token": "MASUKKAN_TOKEN_DARI_BOTFATHER",
  "allowed_chat_id": 123456789,
  "download_dir": "",
  "save_screenshots_to_disk": true,
  "auto_start": true
}
```

### 2. Pemasangan Otomatis (1-Klik)
Cukup klik dua kali file:
👉 **`setup.bat`**

Skrip akan secara otomatis:
1. Memindahkan file ke folder tersembunyi `%LOCALAPPDATA%\TeleKeyboard` (Desktop tetap bersih tanpa folder yang menuh-menuhin layar).
2. Memasang dependensi Python di latar belakang secara hening.
3. Mendaftarkan perintah **Win + R** (`telekeyboard` dan `tk`).
4. Mendaftarkan auto-start di **Startup Windows** (otomatis tersambung setiap laptop dinyalakan).
5. Memunculkan Notepad bertuliskan:
   ```text
   terhubung ke keyboard
   ```

---

## ⌨️ Cara Menjalankan via `Win + R`

Kapan saja Anda ingin memastikan bot menyala atau menghubungkan ulang:
1. Tekan tombol **Win + R** di keyboard.
2. Ketik `telekeyboard` (atau `tk`).
3. Tekan **Enter**.

---

## 📋 Daftar Perintah Telegram

| Perintah | Fungsi |
| :--- | :--- |
| `/start` atau `/panel` | Memunculkan panel tombol keyboard remote |
| `/help` atau `/bantuan` | Menampilkan panduan lengkap semua perintah |
| `/info` atau `/status` | Info spek, CPU, RAM, disk, baterai, uptime, & IP |
| `/diag` | Diagnosa hak akses, resolusi, kamera, & keyboard |
| `/ss` atau `/screenshot` | Tangkap screenshot layar (format foto cepat) |
| `/ssfull` | Tangkap screenshot layar resolusi asli (format file) |
| `/cam` atau `/foto` | Mengambil foto dari webcam Windows |
| `/folder` atau `/files` | Membuka penjelajah file & jalan pintas folder |
| `/ls <path>` | Menampilkan isi folder tertentu di Windows |
| `/download <path>` | Mengunduh file dari Windows ke Telegram |
| `/cat <path>` | Membaca isi file teks langsung di Telegram |
| `/open <app\|path\|url>` | Membuka file, aplikasi, atau URL website di Windows |
| `/shutdown` | Mematikan PC (jeda 15 detik dengan tombol pembatalan) |
| `/shutdown now` | Mematikan PC seketika tanpa jeda |
| `/shutdown_cancel` | Membatalkan jadwal shutdown atau restart |
| `/restart` | Me-restart komputer Windows (Reboot) |
| `/sleep` | Menidurkan PC ke mode Sleep / Standby |
| `/lock` | Mengunci layar Windows (Lock Screen) |
| `/wake` | Membangunkan layar monitor dari standby |
| `/vol <0-100\|+\|->` | Mengatur volume suara (contoh: `/vol 40`, `/vol +`) |
| `/mute` | Mute / unmute volume audio Windows |
| `/media` atau `/play` | Play / Pause media player atau YouTube |
| `/type <teks>` | Mengetik teks di Windows (contoh: `/type halo dunia`) |
| `/key <kombinasi>` | Tekan shortcut (contoh: `/key win+d`, `/key ctrl+c`) |
| `/mode` | Aktifkan/matikan mode ketik langsung |
| `/restart_bot` | Memuat ulang program TeleKeyboard |
| `/exit` | Menghentikan bot sementara |
