"""
TeleKeyboard for Windows - Location & GPS Manager
Mendapatkan lokasi laptop (koordinat, kota, ISP, Google Maps) dan kontrol GPS / Layanan Lokasi Windows 10 & 11.
"""

import os
import sys
import subprocess
import winreg
import requests

def is_gps_enabled():
    """Memeriksa apakah Layanan Lokasi (GPS) aktif di Windows."""
    for hkey, subkey in [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location")
    ]:
        try:
            k = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(k, "Value")
            winreg.CloseKey(k)
            return val == "Allow"
        except Exception:
            continue
    return False

def set_gps(enable=True):
    """
    Mengaktifkan atau mematikan Layanan Lokasi (GPS) Windows.
    Mengubah izin di HKCU & HKLM dan mengontrol service lfsvc (Geolocation Service).
    """
    val = "Allow" if enable else "Deny"
    success = False

    # 1. Ubah registry HKCU & HKLM
    for hkey, subkey in [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location")
    ]:
        try:
            k = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "Value", 0, winreg.REG_SZ, val)
            winreg.CloseKey(k)
            success = True
        except Exception:
            pass

    # 2. Kontrol service Geolocation (lfsvc)
    svc_action = "start" if enable else "stop"
    try:
        subprocess.run(
            ["sc.exe", svc_action, "lfsvc"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except Exception:
        pass

    return success

def get_location_data():
    """
    Mengambil data koordinat dan informasi geolokasi laptop.
    Menggunakan API IP Geolocation dengan fallback multi-provider.
    """
    providers = [
        "http://ip-api.com/json/?fields=status,country,regionName,city,zip,lat,lon,timezone,isp,query",
        "https://ipapi.co/json/",
        "https://freeipapi.com/api/json"
    ]

    for url in providers:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                lat = data.get("lat") or data.get("latitude")
                lon = data.get("lon") or data.get("longitude")
                if lat is not None and lon is not None:
                    city = data.get("city") or "Tidak diketahui"
                    region = data.get("regionName") or data.get("region") or ""
                    country = data.get("country") or data.get("country_name") or ""
                    isp = data.get("isp") or data.get("org") or "Internet Provider"
                    ip = data.get("query") or data.get("ip") or ""
                    
                    return {
                        "lat": float(lat),
                        "lon": float(lon),
                        "city": city,
                        "region": region,
                        "country": country,
                        "isp": isp,
                        "ip": ip,
                        "maps_url": f"https://www.google.com/maps?q={lat},{lon}"
                    }
        except Exception:
            continue

    return None

def get_location_text():
    """Menyusun teks informasi lokasi lengkap untuk chat Telegram."""
    gps_status = "Aktif (ON) 🟢" if is_gps_enabled() else "Mati (OFF) 🔴"
    loc = get_location_data()

    if not loc:
        return (
            "📍 **Informasi Lokasi Laptop**\n\n"
            f"📡 Status GPS Windows: {gps_status}\n"
            "⚠️ Gagal mendapatkan koordinat lokasi saat ini (Periksa koneksi internet)."
        )

    text = (
        "📍 **Informasi Lokasi Laptop**\n\n"
        f"📡 Status GPS Windows: {gps_status}\n"
        f"🏙 Kota: {loc['city']}, {loc['region']}\n"
        f"🇮🇩 Negara: {loc['country']}\n"
        f"🌐 IP Publik: `{loc['ip']}`\n"
        f"🏢 ISP / Jaringan: {loc['isp']}\n"
        f"🗺 Koordinat: `{loc['lat']}, {loc['lon']}`\n\n"
        f"🔗 [Buka di Google Maps]({loc['maps_url']})"
    )
    return text, loc['lat'], loc['lon']
