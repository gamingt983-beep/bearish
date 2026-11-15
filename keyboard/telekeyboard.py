"""
================================================================================
  TeleKeyboard untuk Windows 10 & 11
  Remote Control & Keyboard Nirkabel PC lewat Telegram Bot.
  Dikembangkan dengan Antigravity AI Engine.
================================================================================
"""

import os
import sys
import time
import json
import threading
import concurrent.futures
import subprocess
import requests

# Pastikan folder project ada di sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.system_info import get_info_text, get_diag_text, get_uptime_str
from core.keyboard_mouse import press, type_text, lock_workstation, wake_display
from core.audio_media import get_volume, set_volume, change_volume, toggle_mute, toggle_media, is_muted
from core.screen_camera import capture_screen, capture_camera
from core.power_manager import shutdown_pc, restart_pc, cancel_shutdown, sleep_pc
from core.location_manager import get_location_text, set_gps, is_gps_enabled, get_location_data
from core.file_manager import (
    get_shortcut_folders, list_directory, get_file_info,
    read_text_preview, open_in_windows, download_file_to_telegram,
    zip_and_download_folder, save_uploaded_telegram_file, format_file_size
)

# ----------------- KONFIGURASI -----------------
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config():
    defaults = {
        "bot_token": "8646536009:AAEog1hB6C5HAVBdLYel0XO0flZSWWZdIbo",
        "allowed_chat_id": 5373838573,
        "download_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
        "save_screenshots_to_disk": True,
        "auto_start": True,
        "healthcheck_url": ""
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
        except Exception as e:
            print(f"[Warning] Gagal membaca config.json: {e}")
    return defaults

CONFIG = load_config()
TOKEN = CONFIG["bot_token"]
ALLOWED = int(CONFIG["allowed_chat_id"])
HEALTHCHECK_URL = CONFIG.get("healthcheck_url", "")

# Thread pool untuk tugas-tugas I/O berat (screenshot, kamera, transfer file)
EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=5)

# State bot & cache sesi file browser
DIRECT_MODE = False
CURRENT_BROWSE_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
CURRENT_BROWSE_PAGE = 0
CURRENT_PAGE_ITEMS = [] # Menyimpan item pada halaman saat ini untuk akses indeks cepat

# ----------------- TELEGRAM API HELPER -----------------
def api(method, params=None, timeout=25):
    """Panggilan HTTP sinkron ke Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    try:
        r = requests.post(url, data=params, timeout=timeout)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def api_bg(method, params=None):
    """Panggilan asinkron ke Telegram Bot API di background."""
    EXECUTOR.submit(api, method, params)

def send_chat_action(action="typing"):
    """Mengirim indikator sedang mengetik/mengunggah."""
    api_bg("sendChatAction", {"chat_id": ALLOWED, "action": action})

def say(text, markup=None):
    """Mengirim pesan teks baru ke chat."""
    params = {"chat_id": ALLOWED, "text": text}
    if markup:
        params["reply_markup"] = json.dumps(markup)
    return api("sendMessage", params)

def say_bg(text, markup=None):
    """Mengirim pesan teks di background thread."""
    EXECUTOR.submit(say, text, markup)

def edit_or_say(chat_id, message_id, text, markup=None):
    """Mengedit pesan secara in-place agar navigasi super cepat tanpa lag."""
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if markup:
        params["reply_markup"] = json.dumps(markup)
    res = api("editMessageText", params, timeout=10)
    if not res.get("ok"):
        # Jika gagal edit (misal pesan lama/identik), fallback kirim pesan baru
        say(text, markup)

def answer_callback(query_id, text=None):
    """Merespons callback query inline button agar tombol tidak loading terus."""
    params = {"callback_query_id": query_id}
    if text:
        params["text"] = text
    api_bg("answerCallbackQuery", params)

def send_location(lat, lon):
    """Mengirimkan pin lokasi peta interaktif ke Telegram."""
    api("sendLocation", {"chat_id": ALLOWED, "latitude": lat, "longitude": lon})

# ----------------- PANEL KEYBOARD & MENU -----------------
PANEL_ROWS = [
    [("⬆️", "key:up")],
    [("⬅️", "key:left"), ("⬇️", "key:down"), ("➡️", "key:right")],
    [("⏎ Enter", "key:enter"), ("␣ Spasi", "key:space"), ("⌫ Hapus", "key:backspace")],
    [("⎋ Esc", "key:esc"), ("⇥ Tab", "key:tab"), ("⌦ Del", "key:delete")],
    [("Ctrl+C", "key:ctrl+c"), ("Ctrl+V", "key:ctrl+v"), ("Ctrl+Z", "key:ctrl+z")],
    [("Alt+Tab", "key:alt+tab"), ("🔍 Start", "key:win"), ("Alt+F4", "key:alt+f4")],
    [("🔉 Vol -", "act:vol-"), ("🔇 Mute", "act:mute"), ("🔊 Vol +", "act:vol+")],
    [("⏯ Play/Pause", "act:media"), ("🔒 Kunci", "act:lock"), ("ℹ️ Info", "act:info")],
    [("📸 Screenshot", "act:screenshot"), ("📷 Kamera", "act:camera"), ("🔄 Refresh", "act:refresh")],
    [("📁 File & Folder", "menu:files"), ("📍 Lokasi & GPS", "menu:loc")],
    [("⚡ Daya & Power", "menu:power")]
]

MAIN_MARKUP = {
    "inline_keyboard": [
        [{"text": btn[0], "callback_data": btn[1]} for btn in row]
        for row in PANEL_ROWS
    ]
}

def get_power_menu_markup():
    return {
        "inline_keyboard": [
            [{"text": "🔴 Matikan PC (Shutdown)", "callback_data": "pwr:confirm_shutdown"}],
            [{"text": "🔄 Restart PC", "callback_data": "pwr:confirm_restart"}],
            [{"text": "💤 Tidurkan PC (Sleep)", "callback_data": "pwr:sleep"}],
            [{"text": "🔒 Kunci Layar (Lock)", "callback_data": "pwr:lock"}],
            [{"text": "🔙 Kembali ke Remote Keyboard", "callback_data": "menu:main"}]
        ]
    }

def get_confirm_shutdown_markup():
    return {
        "inline_keyboard": [
            [{"text": "⚠️ YA, MATIKAN PC SEKARANG", "callback_data": "pwr:do_shutdown"}],
            [{"text": "❌ Batalkan", "callback_data": "menu:power"}]
        ]
    }

def get_confirm_restart_markup():
    return {
        "inline_keyboard": [
            [{"text": "⚠️ YA, RESTART PC SEKARANG", "callback_data": "pwr:do_restart"}],
            [{"text": "❌ Batalkan", "callback_data": "menu:power"}]
        ]
    }

def get_location_menu_markup():
    gps_on = is_gps_enabled()
    return {
        "inline_keyboard": [
            [{"text": "📍 Kirim Pin Peta (Live Map)", "callback_data": "loc:send_pin"}],
            [
                {"text": "🟢 Hidupkan GPS", "callback_data": "loc:gps_on"},
                {"text": "🔴 Matikan GPS", "callback_data": "loc:gps_off"}
            ],
            [{"text": "🔄 Refresh Status Lokasi", "callback_data": "loc:refresh"}],
            [{"text": "🔙 Kembali ke Remote Keyboard", "callback_data": "menu:main"}]
        ]
    }

def build_file_browser_markup(browse_info):
    """Menyusun inline keyboard untuk navigasi folder & berkas berbasis indeks cepat."""
    global CURRENT_PAGE_ITEMS
    CURRENT_PAGE_ITEMS = browse_info["items"]
    buttons = []
    
    # 1. Baris item file & folder (Gunakan indeks pendek fitem:0 agar tidak ada limit 64 byte)
    for idx, item in enumerate(browse_info["items"]):
        icon = "📁 " if item["is_dir"] else f"{item['size_str']} | "
        display_name = (item["name"][:20] + "...") if len(item["name"]) > 22 else item["name"]
        btn_text = f"{icon}{display_name}"
        buttons.append([{"text": btn_text, "callback_data": f"fitem:{idx}"}])

    # 2. Paginasi jika lebih dari 1 halaman
    nav_row = []
    cur_p = browse_info["current_page"]
    tot_p = browse_info["total_pages"]
    if tot_p > 1:
        if cur_p > 0:
            nav_row.append({"text": "⬅️ Prev", "callback_data": f"fpage:{cur_p - 1}"})
        nav_row.append({"text": f"📄 {cur_p + 1}/{tot_p}", "callback_data": "fpage:noop"})
        if cur_p < tot_p - 1:
            nav_row.append({"text": "Next ➡️", "callback_data": f"fpage:{cur_p + 1}"})
    if nav_row:
        buttons.append(nav_row)

    # 3. Baris Aksi Folder: Download Semua File (.ZIP)
    buttons.append([{"text": "📦 Download Semua File (ZIP)", "callback_data": "fzip:curr"}])

    # 4. Baris Navigasi Atas & Home Shortcuts
    action_row = []
    if browse_info["parent_path"]:
        action_row.append({"text": "⬆️ Ke Atas", "callback_data": "fnav:up"})
    action_row.append({"text": "🏠 Shortcuts", "callback_data": "fnav:shortcuts"})
    action_row.append({"text": "🔄 Refresh", "callback_data": "fnav:refresh"})
    buttons.append(action_row)

    # 5. Tombol Kembali ke remote utama
    buttons.append([{"text": "🔙 Kembali ke Remote Keyboard", "callback_data": "menu:main"}])

    return {"inline_keyboard": buttons}

def build_shortcuts_markup():
    shortcuts = get_shortcut_folders()
    buttons = []
    row = []
    for i, (name, path) in enumerate(shortcuts):
        row.append({"text": name, "callback_data": f"fsc:{i}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([{"text": "🔙 Kembali ke Remote Keyboard", "callback_data": "menu:main"}])
    return {"inline_keyboard": buttons}

def build_file_action_markup(idx):
    """Menu aksi untuk sebuah berkas berbasis indeks (pasti akurat tanpa truncate)."""
    return {
        "inline_keyboard": [
            [{"text": "📥 Download File Ini ke Telegram", "callback_data": f"fdown:{idx}"}],
            [{"text": "🚀 Buka di Windows (/open)", "callback_data": f"fopen:{idx}"}],
            [{"text": "📋 Baca Konten Teks", "callback_data": f"fview:{idx}"}],
            [{"text": "🔙 Kembali ke Daftar File", "callback_data": "fnav:refresh"}]
        ]
    }

# ----------------- AKSI-AKSI UTAMA -----------------
def do_screenshot(full=False):
    try:
        send_chat_action("upload_document" if full else "upload_photo")
        wake_display()
        path = capture_screen(save_to_downloads=True, full=full)
        sz_str = format_file_size(os.path.getsize(path))
        caption = f"📸 Tangkapan Layar Windows ({sz_str})\n💾 Tersimpan di: `{path}`"
        if full:
            download_file_to_telegram(TOKEN, ALLOWED, path, caption)
        else:
            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            with open(path, "rb") as f:
                requests.post(url, data={"chat_id": ALLOWED, "caption": caption}, files={"photo": f}, timeout=60)
    except Exception as e:
        say(f"❌ Screenshot gagal: {e}")

def do_camera():
    try:
        send_chat_action("upload_photo")
        say("📷 Mengambil foto dari webcam Windows...", None)
        path = capture_camera(save_to_downloads=True)
        sz_str = format_file_size(os.path.getsize(path))
        caption = f"📷 Foto Webcam Windows ({sz_str})\n💾 Tersimpan di: `{path}`"
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        with open(path, "rb") as f:
            requests.post(url, data={"chat_id": ALLOWED, "caption": caption}, files={"photo": f}, timeout=60)
    except Exception as e:
        say(f"❌ Kamera gagal: {e}\n(Pastikan webcam terpasang dan tidak dipakai aplikasi lain)")

def do_send_location(chat_id=ALLOWED):
    """Mengirim informasi lokasi dan pin peta Telegram."""
    send_chat_action("find_location")
    text, lat, lon = get_location_text()
    say(text, get_location_menu_markup())
    if lat is not None and lon is not None:
        send_location(lat, lon)

def show_file_browser(target_dir, page=0, force_refresh=False, message_id=None):
    """Menampilkan penjelajah berkas di chat Telegram dengan performa tinggi."""
    global CURRENT_BROWSE_DIR, CURRENT_BROWSE_PAGE
    CURRENT_BROWSE_DIR = target_dir
    CURRENT_BROWSE_PAGE = page
    try:
        info = list_directory(target_dir, page=page, page_size=6, force_refresh=force_refresh)
        text = (
            f"📂 **Penjelajah Berkas Windows**\n"
            f"📍 Path: `{info['current_path']}`\n"
            f"📊 Total: {info['total_items']} item (Hal {info['current_page']+1}/{info['total_pages']})\n\n"
            f"Klik folder untuk masuk, atau klik berkas untuk mengunduh:"
        )
        markup = build_file_browser_markup(info)
        if message_id:
            edit_or_say(ALLOWED, message_id, text, markup)
        else:
            say(text, markup)
    except Exception as e:
        say(f"❌ Gagal membuka folder: {e}")

def show_shortcuts_menu(message_id=None):
    text = "📁 **Pilih Folder Pintas (Shortcuts):**\nPilih salah satu folder atau drive di bawah:"
    markup = build_shortcuts_markup()
    if message_id:
        edit_or_say(ALLOWED, message_id, text, markup)
    else:
        say(text, markup)

def do_download_file(file_path):
    """Mengunduh berkas tunggal dan mengirimkannya ke Telegram."""
    if not os.path.exists(file_path):
        say(f"❌ Berkas tidak ditemukan: `{file_path}`")
        return
    send_chat_action("upload_document")
    say_bg(f"⏳ Sedang mengirim `{os.path.basename(file_path)}` ({format_file_size(os.path.getsize(file_path))}) ke Telegram...")
    try:
        download_file_to_telegram(TOKEN, ALLOWED, file_path)
    except Exception as e:
        say(f"❌ Gagal mengunduh berkas: {e}")

def do_download_all_zip(folder_path):
    """Mengompresi seluruh file dalam folder dan mengirimkannya sebagai arsip ZIP."""
    send_chat_action("upload_document")
    say_bg(f"⏳ Sedang mengompresi semua file di `{os.path.basename(folder_path)}` menjadi ZIP...")
    try:
        zip_and_download_folder(TOKEN, ALLOWED, folder_path)
    except Exception as e:
        say(f"❌ Gagal membuat paket ZIP: {e}")

def help_text():
    return (
        "📖 **Panduan Lengkap TeleKeyboard Windows**\n\n"
        "🎮 **Kontrol Keyboard & Media:**\n"
        "• `/start` atau `/panel` : Munculkan panel tombol remote\n"
        "• `/type <teks>` : Ketik teks langsung di Windows (support emoji)\n"
        "• `/key <shortcut>` : Tekan tombol (ctrl+c, win+d, alt+tab, win+r, enter, dll)\n"
        "• `/mode` : Mode ketik langsung (on/off: setiap pesan otomatis diketik)\n"
        "• `/vol <0-100|+|-` : Atur volume master Windows\n"
        "• `/mute` : Mute / unmute audio Windows\n"
        "• `/media` : Play / Pause lagu atau video\n\n"
        "📍 **Lokasi & GPS Laptop:**\n"
        "• `/lokasi` atau `/gps` : Cek lokasi laptop & kirim pin Google Maps\n"
        "• `/gps on` : Hidupkan Layanan Lokasi (GPS) Windows\n"
        "• `/gps off` : Matikan Layanan Lokasi (GPS) Windows\n\n"
        "📂 **File Manager & Download:**\n"
        "• `/folder` atau `/files` : Buka penjelajah file & jalan pintas folder\n"
        "• `/ls <path>` : Buka folder tertentu di Windows\n"
        "• `/download <path>` : Download berkas apa saja dari Windows ke Telegram\n"
        "• `/zip [path]` : Download seluruh isi folder sebagai berkas .ZIP\n"
        "• `/open <app|path|url>` : Buka file, aplikasi, atau URL di Windows\n"
        "• `/cat <path>` : Pratinjau isi file teks di Telegram\n"
        "• *Kirim File apa saja ke bot* : Otomatis disimpan ke folder Downloads PC! 📥\n\n"
        "⚡ **Daya & Power (Windows):**\n"
        "• `/shutdown` : Matikan PC (jeda 15s dengan tombol batal)\n"
        "• `/shutdown now` : Langsung matikan PC seketika\n"
        "• `/shutdown_cancel` : Batalkan jadwal shutdown/restart\n"
        "• `/restart` : Re-start komputer Windows (Reboot)\n"
        "• `/sleep` : Tidurkan PC (Sleep mode)\n"
        "• `/lock` : Kunci layar Windows\n"
        "• `/wake` : Bangunkan layar monitor\n\n"
        "📸 **Layar & Kamera:**\n"
        "• `/ss` atau `/screenshot` : Screenshot layar (format foto)\n"
        "• `/ssfull` : Screenshot resolusi asli (format dokumen)\n"
        "• `/cam` atau `/foto` : Ambil foto lewat webcam Windows\n\n"
        "⚙️ **Sistem:**\n"
        "• `/info` : Spek, CPU, RAM, disk, baterai, & IP\n"
        "• `/diag` : Diagnosa hak akses, resolusi, kamera, & keyboard"
    )

# ----------------- MESSAGE ROUTER -----------------
def on_message(msg):
    global DIRECT_MODE
    text = msg.get("text", "")
    
    # 1. Simpan berkas yang dikirim user dari Telegram ke PC
    if "document" in msg:
        doc = msg["document"]
        file_id = doc["file_id"]
        file_name = doc.get("file_name", "telegram_file.bin")
        say_bg(f"⏳ Sedang menerima berkas `{file_name}`...")
        try:
            save_path = save_uploaded_telegram_file(TOKEN, file_id, file_name, CONFIG["download_dir"])
            say(f"✅ Berkas berhasil disimpan di Windows!\n💾 Lokasi: `{save_path}`\nUkuran: {format_file_size(doc.get('file_size', 0))}")
        except Exception as e:
            say(f"❌ Gagal menyimpan berkas: {e}")
        return

    if "photo" in msg:
        photo = msg["photo"][-1]
        file_id = photo["file_id"]
        file_name = f"Telegram_Photo_{int(time.time())}.jpg"
        say_bg(f"⏳ Sedang menerima foto dari Telegram...")
        try:
            save_path = save_uploaded_telegram_file(TOKEN, file_id, file_name, CONFIG["download_dir"])
            say(f"✅ Foto berhasil disimpan di Windows!\n💾 Lokasi: `{save_path}`")
        except Exception as e:
            say(f"❌ Gagal menyimpan foto: {e}")
        return

    if not text:
        return

    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0]
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ["/start", "/panel"]:
        say("🎮 **Remote Keyboard Windows Aktif**\nGunakan tombol panel di bawah atau ketik perintah:", MAIN_MARKUP)
    elif cmd in ["/help", "/bantuan"]:
        say(help_text())
    elif cmd in ["/info", "/status"]:
        say_bg(get_info_text())
    elif cmd == "/diag":
        say_bg(get_diag_text())
    elif cmd in ["/lokasi", "/location", "/gps"]:
        if arg.lower() in ["on", "hidup", "aktif"]:
            set_gps(True)
            say("🟢 Layanan Lokasi (GPS) Windows berhasil diaktifkan!")
        elif arg.lower() in ["off", "mati", "nonaktif"]:
            set_gps(False)
            say("🔴 Layanan Lokasi (GPS) Windows berhasil dimatikan!")
        else:
            EXECUTOR.submit(do_send_location)
    elif cmd in ["/gps_on", "/hidupkan_gps"]:
        set_gps(True)
        say("🟢 Layanan Lokasi (GPS) Windows berhasil diaktifkan!")
    elif cmd in ["/gps_off", "/matikan_gps"]:
        set_gps(False)
        say("🔴 Layanan Lokasi (GPS) Windows berhasil dimatikan!")
    elif cmd in ["/ss", "/screenshot"]:
        EXECUTOR.submit(do_screenshot, False)
    elif cmd == "/ssfull":
        EXECUTOR.submit(do_screenshot, True)
    elif cmd in ["/cam", "/foto"]:
        EXECUTOR.submit(do_camera)
    elif cmd == "/lock":
        lock_workstation()
        say("🔒 Layar Windows dikunci.")
    elif cmd == "/sleep":
        say("💤 Menidurkan komputer Windows (Sleep mode)...")
        time.sleep(1)
        sleep_pc()
    elif cmd == "/wake":
        wake_display()
        say("☀️ Layar Windows dibangunkan.")
    elif cmd == "/shutdown":
        if arg.lower() in ["now", "sekarang", "0"]:
            say("⚠️ Mematikan komputer Windows seketika (Shutdown)...")
            shutdown_pc(0)
        else:
            shutdown_pc(15)
            say("🔴 Komputer akan dimatikan dalam 15 detik!\nKetik `/shutdown_cancel` jika ingin membatalkan.")
    elif cmd in ["/restart", "/reboot"]:
        restart_pc(15)
        say("🔄 Komputer Windows akan di-restart dalam 15 detik!\nKetik `/shutdown_cancel` jika ingin membatalkan.")
    elif cmd == "/shutdown_cancel":
        if cancel_shutdown():
            say("✅ Jadwal shutdown/restart Windows berhasil dibatalkan!")
        else:
            say("ℹ️ Tidak ada jadwal shutdown aktif yang perlu dibatalkan.")
    elif cmd == "/vol":
        if arg in ["+", "up"]:
            v = change_volume(6)
            say(f"🔊 Volume: {v}%")
        elif arg in ["-", "down"]:
            v = change_volume(-6)
            say(f"🔉 Volume: {v}%")
        elif arg.isdigit():
            v = set_volume(int(arg))
            say(f"🔊 Volume diatur ke: {v}%")
        else:
            say(f"🔊 Volume saat ini: {get_volume()}% (Mute: {'Ya 🔇' if is_muted() else 'Tidak 🔊'})")
    elif cmd == "/mute":
        muted = toggle_mute()
        say("🔇 Volume: MUTE" if muted else "🔊 Volume: UNMUTE")
    elif cmd in ["/media", "/play", "/pause"]:
        toggle_media()
        say("⏯ Play / Pause media dikirim.")
    elif cmd == "/type":
        if arg:
            type_text(arg)
            say(f"✅ Diketik di Windows: {arg}")
        else:
            say("Contoh: `/type halo dunia`")
    elif cmd == "/key":
        if arg:
            try:
                press(arg)
                say(f"✅ Ditekan: `{arg}`")
            except Exception as e:
                say(f"❌ {e}")
        else:
            say("Contoh: `/key ctrl+c`, `/key win+d`, `/key alt+tab`, `/key enter`")
    elif cmd == "/mode":
        DIRECT_MODE = not DIRECT_MODE
        status_txt = "AKTIF ✅ (Pesan biasa otomatis diketik di Windows)" if DIRECT_MODE else "MATI ❌"
        say(f"Mode ketik langsung: {status_txt}")
    elif cmd in ["/files", "/folder"]:
        if arg and os.path.exists(arg):
            show_file_browser(arg, force_refresh=True)
        else:
            show_shortcuts_menu()
    elif cmd == "/ls":
        target = arg if arg else CURRENT_BROWSE_DIR
        show_file_browser(target, force_refresh=True)
    elif cmd in ["/download", "/dl"]:
        if arg and os.path.exists(arg):
            EXECUTOR.submit(do_download_file, arg)
        else:
            say("Format: `/download <path_file>`\nContoh: `/download C:\\Users\\gamin\\Downloads\\dokumen.pdf`")
    elif cmd == "/zip":
        target = arg if (arg and os.path.isdir(arg)) else CURRENT_BROWSE_DIR
        EXECUTOR.submit(do_download_all_zip, target)
    elif cmd in ["/cat", "/view"]:
        if arg and os.path.exists(arg):
            preview = read_text_preview(arg)
            say(f"📄 **Isi Berkas:** `{os.path.basename(arg)}`\n```\n{preview}\n```")
        else:
            say("Format: `/cat <path_file>`")
    elif cmd == "/open":
        if arg:
            try:
                open_in_windows(arg)
                say(f"🚀 Membuka di Windows: `{arg}`")
            except Exception as e:
                say(f"❌ Gagal membuka: {e}")
        else:
            say("Contoh: `/open C:\\Users\\gamin\\Downloads`")
    elif cmd == "/restart_bot":
        say("🔄 Memuat ulang bot TeleKeyboard Windows...")
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)
    elif cmd == "/exit":
        say("🔴 Bot TeleKeyboard dihentikan.")
        sys.exit(0)
    elif DIRECT_MODE and not text.startswith("/"):
        type_text(text)

# ----------------- CALLBACK QUERY ROUTER -----------------
def on_callback_query(cq):
    global CURRENT_BROWSE_DIR, CURRENT_BROWSE_PAGE, CURRENT_PAGE_ITEMS
    cq_id = cq["id"]
    data = cq.get("data", "")
    msg = cq.get("message", {})
    msg_id = msg.get("message_id")

    answer_callback(cq_id)

    # 1. Navigasi Menu Utama & Submenu
    if data == "menu:main":
        edit_or_say(ALLOWED, msg_id, "🎮 **Remote Keyboard Windows**", MAIN_MARKUP)
    elif data == "menu:power":
        edit_or_say(ALLOWED, msg_id, "⚡ **Menu Daya & Power Windows:**", get_power_menu_markup())
    elif data == "menu:files":
        show_shortcuts_menu(msg_id)
    elif data == "menu:loc":
        text, _, _ = get_location_text()
        edit_or_say(ALLOWED, msg_id, text, get_location_menu_markup())

    # 2. Lokasi & GPS
    elif data == "loc:send_pin":
        EXECUTOR.submit(do_send_location)
    elif data == "loc:gps_on":
        set_gps(True)
        text, _, _ = get_location_text()
        edit_or_say(ALLOWED, msg_id, f"🟢 **GPS Windows Dihidupkan**\n\n{text}", get_location_menu_markup())
    elif data == "loc:gps_off":
        set_gps(False)
        text, _, _ = get_location_text()
        edit_or_say(ALLOWED, msg_id, f"🔴 **GPS Windows Dimatikan**\n\n{text}", get_location_menu_markup())
    elif data == "loc:refresh":
        text, _, _ = get_location_text()
        edit_or_say(ALLOWED, msg_id, text, get_location_menu_markup())

    # 3. Tombol Aksi Langsung
    elif data.startswith("act:"):
        act = data.split(":", 1)[1]
        if act == "screenshot":
            EXECUTOR.submit(do_screenshot, False)
        elif act == "camera":
            EXECUTOR.submit(do_camera)
        elif act == "info":
            say_bg(get_info_text())
        elif act == "vol+":
            v = change_volume(6)
            say(f"🔊 Volume: {v}%")
        elif act == "vol-":
            v = change_volume(-6)
            say(f"🔉 Volume: {v}%")
        elif act == "mute":
            m = toggle_mute()
            say("🔇 Volume: MUTE" if m else "🔊 Volume: UNMUTE")
        elif act == "media":
            toggle_media()
        elif act == "lock":
            lock_workstation()
            say("🔒 Layar Windows dikunci.")
        elif act == "refresh":
            edit_or_say(ALLOWED, msg_id, "🔄 Panel remote keyboard diperbarui.", MAIN_MARKUP)

    # 4. Tombol Keyboard
    elif data.startswith("key:"):
        k = data.split(":", 1)[1]
        try:
            press(k)
        except Exception as e:
            say(f"❌ Gagal: {e}")

    # 5. Daya & Power
    elif data == "pwr:confirm_shutdown":
        edit_or_say(ALLOWED, msg_id, "⚠️ **Konfirmasi Shutdown:**\nApakah Anda yakin ingin mematikan PC Windows?", get_confirm_shutdown_markup())
    elif data == "pwr:do_shutdown":
        shutdown_pc(15)
        say("🔴 Komputer Windows akan dimatikan dalam 15 detik!\nKetik `/shutdown_cancel` jika ingin membatalkan.")
    elif data == "pwr:confirm_restart":
        edit_or_say(ALLOWED, msg_id, "⚠️ **Konfirmasi Restart:**\nApakah Anda yakin ingin me-restart PC Windows?", get_confirm_restart_markup())
    elif data == "pwr:do_restart":
        restart_pc(15)
        say("🔄 Komputer Windows akan di-restart dalam 15 detik!\nKetik `/shutdown_cancel` jika ingin membatalkan.")
    elif data == "pwr:sleep":
        say("💤 Menidurkan komputer Windows (Sleep mode)...")
        time.sleep(1)
        sleep_pc()
    elif data == "pwr:lock":
        lock_workstation()
        say("🔒 Layar Windows dikunci.")

    # 6. File Manager Cepat (Indeks Aman & Edit In-place)
    elif data.startswith("fsc:"):
        sc_idx = int(data.split(":", 1)[1])
        shortcuts = get_shortcut_folders()
        if 0 <= sc_idx < len(shortcuts):
            show_file_browser(shortcuts[sc_idx][1], page=0, force_refresh=True, message_id=msg_id)
    elif data.startswith("fitem:"):
        idx = int(data.split(":", 1)[1])
        if 0 <= idx < len(CURRENT_PAGE_ITEMS):
            item = CURRENT_PAGE_ITEMS[idx]
            if item["is_dir"]:
                # Masuk ke folder
                show_file_browser(item["path"], page=0, force_refresh=True, message_id=msg_id)
            else:
                # Tampilkan rincian berkas & tombol aksi
                info = get_file_info(item["path"])
                caption = (
                    f"{info['icon']} **Berkas:** `{info['name']}`\n"
                    f"📏 Ukuran: {info['size_str']}\n"
                    f"🕒 Modifikasi: {info['mod_time']}\n"
                    f"📍 Path: `{info['path']}`\n\n"
                    f"Pilih tindakan di bawah:"
                )
                edit_or_say(ALLOWED, msg_id, caption, build_file_action_markup(idx))
    elif data.startswith("fdown:"):
        idx = int(data.split(":", 1)[1])
        if 0 <= idx < len(CURRENT_PAGE_ITEMS):
            item = CURRENT_PAGE_ITEMS[idx]
            EXECUTOR.submit(do_download_file, item["path"])
    elif data.startswith("fopen:"):
        idx = int(data.split(":", 1)[1])
        if 0 <= idx < len(CURRENT_PAGE_ITEMS):
            item = CURRENT_PAGE_ITEMS[idx]
            try:
                open_in_windows(item["path"])
                say(f"🚀 Membuka di Windows: `{item['name']}`")
            except Exception as e:
                say(f"❌ {e}")
    elif data.startswith("fview:"):
        idx = int(data.split(":", 1)[1])
        if 0 <= idx < len(CURRENT_PAGE_ITEMS):
            item = CURRENT_PAGE_ITEMS[idx]
            preview = read_text_preview(item["path"])
            say(f"📄 **Isi Berkas:** `{item['name']}`\n```\n{preview}\n```")
    elif data == "fzip:curr":
        EXECUTOR.submit(do_download_all_zip, CURRENT_BROWSE_DIR)
    elif data.startswith("fpage:"):
        page_arg = data.split(":", 1)[1]
        if page_arg.isdigit():
            show_file_browser(CURRENT_BROWSE_DIR, page=int(page_arg), force_refresh=False, message_id=msg_id)
    elif data == "fnav:up":
        parent = os.path.dirname(CURRENT_BROWSE_DIR)
        if parent and parent != CURRENT_BROWSE_DIR:
            show_file_browser(parent, page=0, force_refresh=True, message_id=msg_id)
    elif data == "fnav:shortcuts":
        show_shortcuts_menu(msg_id)
    elif data == "fnav:refresh":
        show_file_browser(CURRENT_BROWSE_DIR, page=CURRENT_BROWSE_PAGE, force_refresh=True, message_id=msg_id)

# ----------------- MAIN LOOP (LONG POLLING) -----------------
def main():
    print("=" * 60)
    print("  TeleKeyboard untuk Windows 10 & 11 - Aktif!")
    print(f"  Target Telegram Chat ID: {ALLOWED}")
    print("=" * 60)

    try:
        api("deleteWebhook", {"drop_pending_updates": False}, timeout=10)
    except Exception:
        pass

    announced = False
    offset = 0
    last_ok_time = time.time()
    last_ping_time = 0

    while True:
        try:
            if not announced:
                startup_msg = get_info_text("🟢 Windows 10/11 Terhubung")
                r = say(startup_msg, MAIN_MARKUP)
                if r.get("ok"):
                    print("[TeleKeyboard] Pengumuman koneksi berhasil dikirim ke Telegram!")
                    d = api("getUpdates", {"offset": -1, "timeout": 0}, timeout=10)
                    if d.get("ok") and d.get("result"):
                        offset = d["result"][-1]["update_id"] + 1

                    announced = True
                    last_ok_time = time.time()
                else:
                    print(f"[TeleKeyboard] Menunggu koneksi internet... (Error: {r.get('error', r)})")
                    time.sleep(3)
                    continue

            res = api("getUpdates", {"offset": offset, "timeout": 25}, timeout=35)
            if not res.get("ok"):
                time.sleep(3)
                continue

            now = time.time()
            if now - last_ok_time > 90:
                try:
                    say(f"🟢 **Windows terhubung kembali**\n⚠️ Sempat terputus sejak {time.strftime('%H:%M:%S', time.localtime(last_ok_time))}")
                except Exception:
                    pass
            last_ok_time = now

            if HEALTHCHECK_URL and now - last_ping_time > 60:
                try:
                    requests.get(HEALTHCHECK_URL, timeout=5)
                    last_ping_time = now
                except Exception:
                    pass

            for u in res.get("result", []):
                offset = u["update_id"] + 1
                
                if "message" in u:
                    m = u["message"]
                    sender_id = m.get("from", {}).get("id")
                    if sender_id == ALLOWED:
                        on_message(m)
                    else:
                        print(f"[Security] Pesan ditolak dari ID tak dikenal: {sender_id}")

                elif "callback_query" in u:
                    cq = u["callback_query"]
                    sender_id = cq.get("from", {}).get("id")
                    if sender_id == ALLOWED:
                        on_callback_query(cq)
                    else:
                        answer_callback(cq["id"], "Akses Ditolak!")

        except KeyboardInterrupt:
            print("\n[TeleKeyboard] Dihentikan oleh pengguna.")
            break
        except Exception as e:
            print(f"[Error Polling] {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
