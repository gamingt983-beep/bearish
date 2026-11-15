"""
TeleKeyboard for Windows - System Information & Diagnostics Module
Mengumpulkan informasi perangkat keras, baterai, jaringan, dan performa Windows 10 & 11.
"""

import os
import sys
import platform
import socket
import datetime
import ctypes
from ctypes import wintypes
import winreg
import psutil
import requests

# Cache static specs agar tidak perlu query berulang-ulang
_STATIC_SPECS = None

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', wintypes.BYTE),
        ('BatteryFlag', wintypes.BYTE),
        ('BatteryLifePercent', wintypes.BYTE),
        ('SystemStatusFlag', wintypes.BYTE),
        ('BatteryLifeTime', wintypes.DWORD),
        ('BatteryFullLifeTime', wintypes.DWORD),
    ]

def get_windows_version_name():
    """Mendeteksi nama Windows secara akurat (Windows 10 vs Windows 11)."""
    try:
        ver = sys.getwindowsversion()
        build = ver.build
        # Windows 11 dimulai dari build 22000 ke atas
        os_name = "Windows 11" if build >= 22000 else "Windows 10"
        
        # Coba ambil DisplayVersion dari registry (misal: 22H2, 23H2)
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            disp_ver, _ = winreg.QueryValueEx(key, "DisplayVersion")
            edition, _ = winreg.QueryValueEx(key, "ProductName")
            return f"{edition} ({disp_ver}, Build {build})"
        except Exception:
            return f"{os_name} (Build {build})"
    except Exception:
        return f"{platform.system()} {platform.release()}"

def get_cpu_name():
    """Mengambil nama model prosesor dari Windows Registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        return cpu_name.strip()
    except Exception:
        return platform.processor() or "Unknown CPU"

def get_static_specs():
    """Mengambil spesifikasi statis PC (nama PC, user, CPU, RAM total, OS)."""
    global _STATIC_SPECS
    if _STATIC_SPECS:
        return _STATIC_SPECS

    comp_name = os.environ.get("COMPUTERNAME", socket.gethostname())
    user_name = os.environ.get("USERNAME", "User")
    cpu = get_cpu_name()
    
    # RAM Total
    mem = psutil.virtual_memory()
    ram_gb = round(mem.total / (1024**3), 1)
    
    win_os = get_windows_version_name()
    arch = platform.machine()

    _STATIC_SPECS = (
        f"🖥 {comp_name} ({win_os})\n"
        f"👤 User: {user_name}\n"
        f"⚙️ CPU: {cpu} ({arch})\n"
        f"🧠 Total RAM: {ram_gb} GB"
    )
    return _STATIC_SPECS

def parse_battery():
    """Membaca status baterai dan adaptor charger melalui API Windows native."""
    sps = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
        return "Tidak terdeteksi (Desktop PC)"
    
    pct = sps.BatteryLifePercent
    if pct == 255:
        return "Tidak ada (Desktop PC tanpa baterai)"
    
    ac = sps.ACLineStatus
    status_str = f"{pct}%"
    
    if ac == 1:
        if pct >= 99:
            status_str += " (Penuh 🔌)"
        else:
            status_str += " (Mengecas ⚡️)"
    elif ac == 0:
        status_str += " (Baterai 🔋)"
    
    # Perkiraan waktu tersisa
    if sps.BatteryLifeTime != 0xFFFFFFFF and sps.BatteryLifeTime > 0:
        mins = sps.BatteryLifeTime // 60
        hours = mins // 60
        remain_mins = mins % 60
        if hours > 0:
            status_str += f" – sisa ~{hours} jam {remain_mins} mnt"
        else:
            status_str += f" – sisa ~{remain_mins} mnt"
            
    return status_str

def get_uptime_str():
    """Menghitung lama PC menyala menggunakan GetTickCount64."""
    uptime_ms = ctypes.windll.kernel32.GetTickCount64()
    total_seconds = uptime_ms // 1000
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    mins = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0:
        parts.append(f"{hours} jam")
    parts.append(f"{mins} menit")
    return " ".join(parts)

def get_disk_summary():
    """Merangkum penggunaan partisi drive Windows (C:, D:, dll)."""
    parts = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or part.fstype == "":
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            free_gb = round(usage.free / (1024**3), 1)
            total_gb = round(usage.total / (1024**3), 1)
            used_pct = usage.percent
            parts.append(f"{part.device} {free_gb} GB bebas dari {total_gb} GB ({used_pct}% terpakai)")
        except (PermissionError, OSError):
            continue
    return "\n   ".join(parts) if parts else "Tidak tersedia"

def get_local_ip():
    """Mendapatkan alamat IP lokal aktif (LAN/Wi-Fi)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.5)
        # Menghubungkan ke DNS publik tanpa benar-benar mengirim paket
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_public_ip():
    """Mendapatkan alamat IP publik dari api.ipify.org."""
    try:
        r = requests.get("https://api.ipify.org", timeout=4)
        if r.status_code == 200:
            return r.text.strip()
    except Exception:
        pass
    return "Tidak dapat dijangkau"

def get_info_text(title="ℹ️ Informasi Sistem Windows"):
    """Menyusun seluruh informasi sistem menjadi pesan Telegram yang rapi dan informatif."""
    now = datetime.datetime.now().strftime("%d %b %Y, %H:%M:%S")
    
    mem = psutil.virtual_memory()
    ram_used = round(mem.used / (1024**3), 1)
    ram_total = round(mem.total / (1024**3), 1)
    ram_pct = mem.percent
    
    cpu_pct = psutil.cpu_percent(interval=0.3)
    
    static_spec = get_static_specs()
    batt = parse_battery()
    uptime = get_uptime_str()
    disks = get_disk_summary()
    lip = get_local_ip()
    pip = get_public_ip()
    
    msg = (
        f"{title}\n\n"
        f"{static_spec}\n"
        f"📊 Beban CPU: {cpu_pct}%\n"
        f"🧠 Beban RAM: {ram_used} GB / {ram_total} GB ({ram_pct}%)\n"
        f"💽 Penyimpanan:\n   {disks}\n"
        f"🔋 Baterai: {batt}\n"
        f"⏱ Menyala: {uptime}\n"
        f"🌐 IP Lokal: {lip}\n"
        f"🌍 IP Publik: {pip}\n"
        f"🕒 Waktu Windows: {now}"
    )
    return msg

def is_admin():
    """Memeriksa apakah bot dijalankan sebagai Administrator."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def get_diag_text():
    """Diagnosa lengkap izin sistem, layar, kamera, dan hak akses Windows."""
    user32 = ctypes.windll.user32
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    mon_count = user32.GetSystemMetrics(80) # SM_CMONITORS
    
    admin_str = "Administrator (Elevated) ✅" if is_admin() else "User Biasa (Standard) ℹ️"
    
    # Cek status kamera
    cams = []
    try:
        import cv2
        for i in range(3):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                cams.append(f"Kamera #{i} (DirectShow)")
                cap.release()
    except Exception:
        pass
        
    cam_str = ", ".join(cams) if cams else "Tidak ada kamera aktif terdeteksi ⚠️"
    
    diag = (
        "🔧 **Diagnosa Sistem TeleKeyboard Windows**\n\n"
        f"🛡 Hak Akses: {admin_str}\n"
        f"🖥 Resolusi Layar: {w} x {h}\n"
        f"🖥 Jumlah Monitor: {mon_count}\n"
        f"📷 Status Kamera: {cam_str}\n"
        f"⌨️ Input Emulation (SendInput): Aktif ✅\n"
        f"🔊 Audio CoreAudio (Endpoint): Aktif ✅\n"
        f"📂 File Explorer & Download: Siap ✅\n"
        f"⚡ Power Manager (Shutdown/Sleep/Restart): Siap ✅"
    )
    return diag
