"""
TeleKeyboard for Windows - Audio & Media Control Module
Menggunakan Windows CoreAudio API via pycaw dengan fallback ke virtual key events.
"""

import ctypes
import time

try:
    from pycaw.pycaw import AudioUtilities
    _PYCAW_AVAILABLE = True
except Exception:
    _PYCAW_AVAILABLE = False

user32 = ctypes.windll.user32
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

def _get_endpoint_volume():
    """Mengambil interface EndpointVolume dari speaker default Windows."""
    if not _PYCAW_AVAILABLE:
        return None
    try:
        device = AudioUtilities.GetSpeakers()
        if device:
            return device.EndpointVolume
    except Exception:
        pass
    return None

def get_volume():
    """Mendapatkan volume master saat ini (0 - 100)."""
    ep = _get_endpoint_volume()
    if ep:
        try:
            val = ep.GetMasterVolumeLevelScalar()
            return round(val * 100)
        except Exception:
            pass
    return 50

def set_volume(level):
    """Mengatur volume master ke angka pasti (0 - 100)."""
    level = max(0, min(100, int(level)))
    ep = _get_endpoint_volume()
    if ep:
        try:
            ep.SetMasterVolumeLevelScalar(level / 100.0, None)
            return level
        except Exception:
            pass
            
    # Fallback jika endpoint volume gagal
    return level

def change_volume(delta):
    """Menambah atau mengurangi volume (+6 / -6)."""
    ep = _get_endpoint_volume()
    if ep:
        try:
            cur = round(ep.GetMasterVolumeLevelScalar() * 100)
            target = max(0, min(100, cur + delta))
            ep.SetMasterVolumeLevelScalar(target / 100.0, None)
            return target
        except Exception:
            pass

    # Fallback ke virtual key
    vk = VK_VOLUME_UP if delta > 0 else VK_VOLUME_DOWN
    steps = abs(delta) // 2 or 1
    for _ in range(steps):
        user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)
    return get_volume()

def toggle_mute():
    """Mengaktifkan/mematikan mute volume."""
    ep = _get_endpoint_volume()
    if ep:
        try:
            cur = ep.GetMute()
            new_state = not cur
            ep.SetMute(new_state, None)
            return bool(new_state)
        except Exception:
            pass

    # Fallback keybd_event
    user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
    user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    return is_muted()

def is_muted():
    """Memeriksa apakah audio sedang dimute."""
    ep = _get_endpoint_volume()
    if ep:
        try:
            return bool(ep.GetMute())
        except Exception:
            pass
    return False

def toggle_media():
    """Menjalankan Play / Pause pada pemutar media Windows (Spotify, YouTube, Media Player, dll)."""
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY, 0)
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
