"""
TeleKeyboard for Windows - Keyboard & Mouse Emulation Module
Menggunakan Windows SendInput API native & clipboard injection untuk simulasi tombol & ketik.
"""

import time
import ctypes
from ctypes import wintypes
import win32clipboard

user32 = ctypes.windll.user32

# Konstanta SendInput
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Virtual Key Codes Windows
VK = {
    # Modifiers
    'ctrl': 0x11, 'control': 0x11,
    'shift': 0x10,
    'alt': 0x12, 'menu': 0x12,
    'win': 0x5B, 'cmd': 0x5B, 'command': 0x5B, 'super': 0x5B,
    
    # Navigation & control
    'enter': 0x0D, 'return': 0x0D,
    'esc': 0x1B, 'escape': 0x1B,
    'tab': 0x09,
    'space': 0x20, 'spasi': 0x20,
    'backspace': 0x08, 'hapus': 0x08,
    'delete': 0x2E, 'del': 0x2E, 'forwarddelete': 0x2E,
    'insert': 0x2D,
    'home': 0x24,
    'end': 0x23,
    'pageup': 0x21, 'pgup': 0x21,
    'pagedown': 0x22, 'pgdn': 0x22,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    'capslock': 0x14,
    
    # Function keys
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74,
    'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79,
    'f11': 0x7A, 'f12': 0x7B,
    
    # Media
    'vol+': 0xAF, 'volup': 0xAF,
    'vol-': 0xAE, 'voldown': 0xAE,
    'mute': 0xAD,
    'media': 0xB3, 'playpause': 0xB3, 'play': 0xB3,
}

# Key codes untuk huruf & angka
for c in range(ord('a'), ord('z') + 1):
    VK[chr(c)] = ord(chr(c).upper())
for c in range(ord('0'), ord('9') + 1):
    VK[chr(c)] = c

# Extended keys yang memerlukan KEYEVENTF_EXTENDEDKEY
EXTENDED_KEYS = {
    0x25, 0x26, 0x27, 0x28, # Panah
    0x24, 0x23, 0x21, 0x22, # Home, End, PgUp, PgDn
    0x2D, 0x2E,             # Insert, Delete
    0x5B, 0x5C,             # Win keys
    0xAF, 0xAE, 0xAD, 0xB3  # Media keys
}

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_size_t),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', wintypes.DWORD), ('wParamL', wintypes.WORD), ('wParamH', wintypes.WORD)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [('mi', MOUSEINPUT), ('ki', KEYBDINPUT), ('hi', HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('union', _INPUT_UNION)]

def _send_key_event(vk_code, is_up=False):
    """Mengirim event key down atau key up via Windows SendInput."""
    flags = 0
    if is_up:
        flags |= KEYEVENTF_KEYUP
    if vk_code in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY

    inp = INPUT(type=INPUT_KEYBOARD, union=_INPUT_UNION(ki=KEYBDINPUT(vk_code, 0, flags, 0, 0)))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def press(combo_str):
    """
    Menekan kombinasi tombol.
    Contoh: 'ctrl+c', 'win+d', 'alt+tab', 'ctrl+shift+esc', 'enter', 'up'.
    """
    parts = [p.strip().lower() for p in combo_str.split('+') if p.strip()]
    if not parts:
        return

    # Map part ke VK code
    vk_list = []
    for p in parts:
        if p in VK:
            vk_list.append(VK[p])
        elif len(p) == 1 and ord(p.upper()) in range(0x30, 0x5B):
            vk_list.append(ord(p.upper()))
        else:
            raise ValueError(f"Tombol tidak dikenal: '{p}'")

    # Key down berurutan
    for vk in vk_list:
        _send_key_event(vk, is_up=False)
        time.sleep(0.01)

    time.sleep(0.03)

    # Key up urutan terbalik
    for vk in reversed(vk_list):
        _send_key_event(vk, is_up=True)
        time.sleep(0.01)

def type_text(text):
    """
    Mengetik teks di Windows.
    Jika teks pendek/alfanumerik biasa, diketik karakter demi karakter.
    Jika teks panjang, multiline, atau ada emoji/Unicode, menggunakan clipboard paste.
    """
    if not text:
        return

    # Cek apakah teks murni ASCII sederhana satu baris
    is_simple_ascii = all(32 <= ord(c) < 127 for c in text) and '\n' not in text

    if is_simple_ascii and len(text) < 40:
        # Kirim per karakter via KEYEVENTF_UNICODE
        inputs = []
        for char in text:
            code = ord(char)
            inp_down = INPUT(type=INPUT_KEYBOARD, union=_INPUT_UNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, 0)))
            inp_up = INPUT(type=INPUT_KEYBOARD, union=_INPUT_UNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)))
            inputs.extend([inp_down, inp_up])
            
        arr = (INPUT * len(inputs))(*inputs)
        user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    else:
        # Gunakan Windows Clipboard Paste (Ctrl+V)
        try:
            # Simpan isi clipboard lama jika memungkinkan
            old_clip = None
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    old_clip = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except Exception:
                pass

            # Masukkan teks baru ke clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            time.sleep(0.03)

            # Simulasikan Ctrl+V (Paste)
            press("ctrl+v")
            time.sleep(0.08)

            # Kembalikan clipboard lama setelah jeda singkat (opsional)
        except Exception as e:
            # Fallback Unicode sendinput jika clipboard gagal
            inputs = []
            for char in text:
                code = ord(char)
                inp_down = INPUT(type=INPUT_KEYBOARD, union=_INPUT_UNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, 0)))
                inp_up = INPUT(type=INPUT_KEYBOARD, union=_INPUT_UNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)))
                inputs.extend([inp_down, inp_up])
            arr = (INPUT * len(inputs))(*inputs)
            user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

def lock_workstation():
    """Mengunci layar Windows (Lock Screen)."""
    return user32.LockWorkStation() != 0

def wake_display():
    """Membangunkan layar Windows dari screensaver/display standby."""
    # Simulasikan gerakan mouse 1 piksel bolak-balik
    MOUSEEVENTF_MOVE = 0x0001
    inp1 = INPUT(type=0, union=_INPUT_UNION(mi=MOUSEINPUT(1, 0, 0, MOUSEEVENTF_MOVE, 0, 0)))
    inp2 = INPUT(type=0, union=_INPUT_UNION(mi=MOUSEINPUT(-1, 0, 0, MOUSEEVENTF_MOVE, 0, 0)))
    arr = (INPUT * 2)(inp1, inp2)
    user32.SendInput(2, arr, ctypes.sizeof(INPUT))
