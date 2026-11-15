"""
TeleKeyboard for Windows - File Manager & Download Module (Enhanced & High Speed)
Navigasi berkas cepat dengan cache memori, download file tunggal tanpa batasan ekstensi,
dan fitur download semua file dalam satu folder (.ZIP) langsung ke Telegram.
"""

import os
import sys
import datetime
import string
import ctypes
import zipfile
import tempfile
import requests

# Cache in-memory untuk navigasi cepat
_DIR_CACHE = {}

def get_shortcut_folders():
    """Mengembalikan daftar jalan pintas (shortcut) folder utama Windows."""
    user_home = os.path.expanduser("~")
    shortcuts = [
        ("🖥 Desktop", os.path.join(user_home, "Desktop")),
        ("📥 Downloads", os.path.join(user_home, "Downloads")),
        ("📁 Documents", os.path.join(user_home, "Documents")),
        ("🖼 Pictures", os.path.join(user_home, "Pictures")),
        ("🎵 Music", os.path.join(user_home, "Music")),
        ("🎬 Videos", os.path.join(user_home, "Videos")),
    ]
    
    # Deteksi semua drive Windows (C:\, D:\, dll)
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                drives.append((f"💾 Drive {letter}:", drive_path))
        bitmask >>= 1

    return [s for s in shortcuts if os.path.exists(s[1])] + drives

def format_file_size(bytes_size):
    """Memformat ukuran byte ke KB, MB, atau GB yang mudah dibaca."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024**2:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024**3:
        return f"{bytes_size / (1024**2):.1f} MB"
    else:
        return f"{bytes_size / (1024**3):.2f} GB"

def get_file_icon(filename, is_dir=False):
    """Memberikan emoji representatif berdasarkan ekstensi berkas."""
    if is_dir:
        return "📁"
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".ico"]:
        return "🖼"
    elif ext in [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"]:
        return "🎬"
    elif ext in [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"]:
        return "🎵"
    elif ext in [".zip", ".rar", ".7z", ".tar", ".gz", ".iso"]:
        return "📦"
    elif ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]:
        return "📑"
    elif ext in [".txt", ".log", ".py", ".js", ".json", ".md", ".csv", ".xml", ".html", ".css", ".bat", ".ps1"]:
        return "📄"
    elif ext in [".exe", ".msi", ".dll"]:
        return "⚙️"
    return "📄"

def list_directory(target_path, page=0, page_size=6, force_refresh=False):
    """
    Mendaftar folder dan file dalam suatu direktori dengan paginasi dan cache cepat.
    Mengembalikan metadata direktori dan daftar item untuk halaman yang diminta.
    """
    target_path = os.path.abspath(target_path)
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Folder tidak ditemukan: {target_path}")
    if not os.path.isdir(target_path):
        raise NotADirectoryError(f"Bukan folder: {target_path}")

    parent_path = os.path.dirname(target_path)
    is_root = (parent_path == target_path)

    # Gunakan cache jika tersedia dan tidak dipaksa refresh
    if not force_refresh and target_path in _DIR_CACHE:
        entries = _DIR_CACHE[target_path]
    else:
        entries = []
        try:
            with os.scandir(target_path) as it:
                for entry in it:
                    try:
                        is_d = entry.is_dir(follow_symlinks=False)
                        size = 0 if is_d else entry.stat().st_size
                        entries.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": is_d,
                            "size": size,
                            "size_str": format_file_size(size) if not is_d else "Folder"
                        })
                    except (PermissionError, OSError):
                        continue
        except PermissionError:
            raise PermissionError(f"Akses ditolak pada folder: {target_path}")

        # Urutkan: folder terlebih dahulu, kemudian file abjad
        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        _DIR_CACHE[target_path] = entries

    total_items = len(entries)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * page_size
    items_slice = entries[start_idx : start_idx + page_size]

    return {
        "current_path": target_path,
        "parent_path": parent_path if not is_root else None,
        "is_root": is_root,
        "items": items_slice,
        "all_entries": entries,
        "start_idx": start_idx,
        "total_items": total_items,
        "current_page": page,
        "total_pages": total_pages
    }

def get_file_info(file_path):
    """Mengambil rincian detail sebuah berkas."""
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Berkas tidak ditemukan: {file_path}")
    
    stat = os.stat(file_path)
    size_str = format_file_size(stat.st_size)
    mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y, %H:%M:%S")
    name = os.path.basename(file_path)
    is_dir = os.path.isdir(file_path)
    
    return {
        "name": name,
        "path": file_path,
        "is_dir": is_dir,
        "size_bytes": stat.st_size,
        "size_str": size_str,
        "mod_time": mod_time,
        "icon": get_file_icon(name, is_dir)
    }

def read_text_preview(file_path, max_chars=3500):
    """Membaca isi berkas teks untuk pratinjau langsung di Telegram."""
    if not os.path.exists(file_path):
        return "❌ Berkas tidak ditemukan."
    
    size = os.path.getsize(file_path)
    if size > 200 * 1024:
        return f"⚠️ Berkas terlalu besar ({format_file_size(size)}) untuk pratinjau teks. Gunakan tombol Download."

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars + 100)
            if len(content) > max_chars:
                return content[:max_chars] + f"\n\n... (Dipotong, total {format_file_size(size)})"
            return content
    except Exception as e:
        return f"❌ Gagal membaca berkas: {e}"

def open_in_windows(path):
    """Membuka berkas atau folder langsung di Windows menggunakan program default."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Tidak ditemukan: {path}")
    os.startfile(path)

def download_file_to_telegram(token, chat_id, file_path, caption=""):
    """
    Mengirimkan berkas dari PC Windows ke chat Telegram.
    Batas upload bot Telegram adalah 50 MB.
    """
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Berkas tidak ditemukan di path: {file_path}")
    
    size = os.path.getsize(file_path)
    if size > 50 * 1024 * 1024:
        raise ValueError(
            f"Ukuran berkas ({format_file_size(size)}) melebihi batas upload Telegram Bot (50 MB).\n"
            f"Lokasi lokal di Windows: {file_path}"
        )

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    name = os.path.basename(file_path)
    if not caption:
        caption = f"📥 Berkas dari Windows:\n📄 `{name}` ({format_file_size(size)})"

    with open(file_path, "rb") as f:
        files = {"document": (name, f)}
        data = {"chat_id": chat_id, "caption": caption}
        r = requests.post(url, data=data, files=files, timeout=180)
        res = r.json()
        if not res.get("ok"):
            raise RuntimeError(res.get("description", str(res)))
        return res

def zip_and_download_folder(token, chat_id, folder_path):
    """
    Mengompresi semua file dalam suatu folder menjadi file .ZIP
    lalu mengirimkannya ke Telegram.
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Bukan folder: {folder_path}")

    folder_name = os.path.basename(folder_path.rstrip("\\/")) or "Files"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{folder_name}_{stamp}.zip"
    temp_zip = os.path.join(tempfile.gettempdir(), zip_filename)

    # Buat arsip zip
    total_files = 0
    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, folder_path)
                try:
                    zf.write(full_p, rel_p)
                    total_files += 1
                except Exception:
                    continue

    if total_files == 0:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        raise ValueError("Folder ini kosong (tidak ada file untuk dikompresi).")

    zip_size = os.path.getsize(temp_zip)
    if zip_size > 50 * 1024 * 1024:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        raise ValueError(
            f"Ukuran total arsip ZIP ({format_file_size(zip_size)}) melebihi batas upload Telegram Bot (50 MB).\n"
            f"Silakan unduh file secara individual."
        )

    caption = f"📦 **Paket Berkas ZIP Folder:** `{folder_name}`\n📊 Total Berkas: {total_files}\n📏 Ukuran: {format_file_size(zip_size)}"
    try:
        return download_file_to_telegram(token, chat_id, temp_zip, caption)
    finally:
        try:
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
        except Exception:
            pass

def save_uploaded_telegram_file(token, file_id, original_name, dest_dir=None):
    """
    Mengunduh berkas yang dikirimkan user di chat Telegram dan menyimpannya ke PC Windows.
    Default disimpan ke folder Downloads pengguna.
    """
    if not dest_dir:
        dest_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(dest_dir, exist_ok=True)

    info_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
    r = requests.get(info_url, timeout=15).json()
    if not r.get("ok"):
        raise RuntimeError(f"Gagal mengambil metadata file dari Telegram: {r}")

    remote_path = r["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{token}/{remote_path}"

    if not original_name:
        original_name = os.path.basename(remote_path)

    base, ext = os.path.splitext(original_name)
    save_path = os.path.join(dest_dir, original_name)
    counter = 1
    while os.path.exists(save_path):
        save_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
        counter += 1

    with requests.get(download_url, stream=True, timeout=120) as stream:
        stream.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in stream.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)

    return save_path
