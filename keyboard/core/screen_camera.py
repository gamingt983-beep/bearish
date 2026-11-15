"""
TeleKeyboard for Windows - Screen & Camera Capture Module
Screenshot beresolusi penuh / cepat dan akses Webcam native Windows via DirectShow / OpenCV.
"""

import os
import time
import datetime
import ctypes
from PIL import Image, ImageGrab
import cv2

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Mengaktifkan Per-Monitor DPI Awareness agar hasil screenshot tidak terpotong / blur
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

def _attach_interactive_desktop():
    """Menghubungkan thread saat ini ke Input Desktop aktif Windows (WinSta0)."""
    try:
        hDesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hDesk:
            user32.SetThreadDesktop(hDesk)
            user32.CloseDesktop(hDesk)
    except Exception:
        pass

def capture_screen(save_to_downloads=True, full=False):
    """
    Mengambil screenshot layar Windows.
    save_to_downloads: Jika True, menyimpan salinan berkas ke folder Downloads.
    full: Jika True, resolusi asli 100%. Jika False, dioptimalkan (max 1920) untuk pratinjau cepat Telegram.
    Mengembalikan path file gambar hasil tangkapan layar.
    """
    _attach_interactive_desktop()
    time.sleep(0.05)
    
    # 1. Coba ImageGrab terlebih dahulu
    img = None
    try:
        img = ImageGrab.grab()
    except Exception:
        pass

    # 2. Fallback jika ImageGrab gagal: gunakan GDI BitBlt langsung
    if img is None:
        try:
            w = user32.GetSystemMetrics(0) # SM_CXSCREEN
            h = user32.GetSystemMetrics(1) # SM_CYSCREEN
            hDesktopDC = user32.GetDC(0)
            hCaptureDC = gdi32.CreateCompatibleDC(hDesktopDC)
            hCaptureBitmap = gdi32.CreateCompatibleBitmap(hDesktopDC, w, h)
            gdi32.SelectObject(hCaptureDC, hCaptureBitmap)

            SRCCOPY = 0x00CC0020
            CAPTURBLT = 0x40000000
            gdi32.BitBlt(hCaptureDC, 0, 0, w, h, hDesktopDC, 0, 0, SRCCOPY | CAPTURBLT)

            # Buat DIB Header
            from ctypes import wintypes
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG),
                    ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD)
                ]
            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = w
            bmi.biHeight = -h # top-down
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            buf = ctypes.create_string_buffer(w * h * 4)
            gdi32.GetDIBits(hCaptureDC, hCaptureBitmap, 0, h, buf, ctypes.byref(bmi), 0)
            img = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')

            # Cleanup GDI
            gdi32.DeleteObject(hCaptureBitmap)
            gdi32.DeleteDC(hCaptureDC)
            user32.ReleaseDC(0, hDesktopDC)
        except Exception as e:
            raise RuntimeError(f"Gagal mengambil screenshot: {e}")

    if img is None:
        raise RuntimeError("Gagal menghasilkan gambar layar.")

    # Tentukan folder output
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"Screenshot_{stamp}.jpg"
    
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.exists(downloads_path):
        downloads_path = os.environ.get("TEMP", ".")
    
    dest_path = os.path.join(downloads_path, filename) if save_to_downloads else os.path.join(os.environ.get("TEMP", "."), filename)

    if not full:
        # Resize ke maksimal lebar 1920 agar kirim foto ke Telegram super cepat
        max_dim = 1920
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        img.save(dest_path, "JPEG", quality=85)
    else:
        # Kualitas penuh tanpa penurunan resolusi
        img.save(dest_path, "JPEG", quality=95)

    return dest_path

def capture_camera(save_to_downloads=True):
    """
    Mengambil foto dari kamera webcam Windows.
    Mencoba deteksi kamera dari index 0 hingga 3 dengan DirectShow dan MSMF.
    Mengembalikan path file foto atau None jika kamera gagal.
    """
    cap = None
    selected_idx = None
    
    # Cari kamera yang dapat dibuka
    for idx in range(4):
        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
            try:
                c = cv2.VideoCapture(idx, backend)
                if c.isOpened():
                    cap = c
                    selected_idx = idx
                    break
            except Exception:
                continue
        if cap is not None:
            break

    if cap is None:
        raise RuntimeError("Tidak ditemukan kamera aktif yang terhubung pada Windows.")

    try:
        # Warm-up beberapa frame agar auto-exposure dan fokus menyesuaikan cahaya ruangan
        for _ in range(8):
            cap.read()
            time.sleep(0.04)

        ret, frame = cap.read()
        if not ret or frame is None or frame.size == 0:
            raise RuntimeError("Kamera tidak menghasilkan frame gambar.")

        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Foto_Kamera_{stamp}.jpg"
        
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads_path):
            downloads_path = os.environ.get("TEMP", ".")

        dest_path = os.path.join(downloads_path, filename) if save_to_downloads else os.path.join(os.environ.get("TEMP", "."), filename)
        
        # Simpan dengan kualitas JPEG tinggi (90%)
        cv2.imwrite(dest_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        return dest_path
    finally:
        cap.release()
