"""
TeleKeyboard for Windows - Power Management Module
Mengelola Shutdown, Restart, Sleep, Lock, dan Pembatalan Daya Windows 10 & 11.
"""

import os
import subprocess
import ctypes

def shutdown_pc(seconds=15, force=False):
    """
    Mematikan komputer Windows.
    seconds: Jeda waktu sebelum shutdown (default 15 detik untuk memberi kesempatan cancel).
    Jika seconds == 0, langsung shutdown seketika.
    """
    if seconds == 0:
        cmd = ["shutdown.exe", "/s", "/f", "/t", "0"]
    else:
        msg = f"TeleKeyboard: Komputer akan dimatikan dalam {seconds} detik. Batalkan dengan /shutdown_cancel"
        cmd = ["shutdown.exe", "/s", "/t", str(seconds), "/c", msg]
        if force:
            cmd.append("/f")
            
    subprocess.run(cmd, check=False)
    return seconds

def restart_pc(seconds=15, force=False):
    """
    Me-restart komputer Windows (Reboot).
    seconds: Jeda waktu sebelum restart (default 15 detik).
    """
    if seconds == 0:
        cmd = ["shutdown.exe", "/r", "/f", "/t", "0"]
    else:
        msg = f"TeleKeyboard: Komputer akan di-restart dalam {seconds} detik. Batalkan dengan /shutdown_cancel"
        cmd = ["shutdown.exe", "/r", "/t", str(seconds), "/c", msg]
        if force:
            cmd.append("/f")
            
    subprocess.run(cmd, check=False)
    return seconds

def cancel_shutdown():
    """
    Membatalkan jadwal shutdown atau restart yang sedang berjalan (/a).
    """
    res = subprocess.run(["shutdown.exe", "/a"], capture_output=True, text=True)
    return res.returncode == 0

def sleep_pc():
    """
    Menidurkan komputer Windows (Sleep / Standby mode).
    Menggunakan API Powrprof SetSuspendState.
    """
    try:
        # Parameter: Hibernate (0=Sleep, 1=Hibernate), ForceCritical, DisableWakeEvent
        ret = ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
        if ret == 0:
            # Fallback ke rundll32
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    except Exception:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
