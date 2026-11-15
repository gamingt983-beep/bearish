<#====================================================================
 TeleKeyboard – PowerShell installer (universal for Windows 7/8/10/11)
====================================================================#>

# 1. Tentukan folder instalasi (AppData\Local\TeleKeyboard)
$target = Join-Path $env:LOCALAPPDATA 'TeleKeyboard'
Write-Host "🚀 Menginstal TeleKeyboard ke $target" -ForegroundColor Cyan

# 2. Buat atau bersihkan folder tujuan
if (Test-Path $target) {
    Write-Host "🗑️ Menghapus instalasi lama…" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $target
}
New-Item -ItemType Directory -Path $target | Out-Null

# 3. Salin semua file dari folder ini ke $target
$src = Split-Path -Parent $MyInvocation.MyCommand.Path   # folder installer ini
Copy-Item -Path (Join-Path $src '*') -Destination $target -Recurse -Force

# 4. Pastikan Python ada di PATH
function Get-PythonPath {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($py) { return $py }
    Write-Warning "⚠️ Python tidak ditemukan di PATH. Unduh dulu dari https://www.python.org/downloads/ dan pastikan ‘Add Python to PATH’ dicentang."
    return $null
}
$pythonExe = Get-PythonPath
if (-not $pythonExe) { exit 1 }

# 5. Instal dependensi Python (pip)
Write-Host "🔧 Memasang dependensi Python…" -ForegroundColor Green
& $pythonExe -m pip install -r (Join-Path $target 'requirements.txt') --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Gagal memasang paket pip. Periksa koneksi internet atau hak admin."
    exit 1
}

# 6. Buat config.json bila belum ada
$config = Join-Path $target 'config.json'
if (-not (Test-Path $config)) {
    Copy-Item -Path (Join-Path $target 'config.example.json') -Destination $config
    Write-Host "📝 Membuka Notepad untuk mengisi token Bot Telegram…" -ForegroundColor Magenta
    notepad $config
    Read-Host "Tekan ENTER setelah selesai mengedit config.json"
}

# 7. Registrasi shortcut Win+R (telekeyboard.cmd, tk.cmd, keyboard.cmd)
$winApps = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
if (-not (Test-Path $winApps)) { New-Item -ItemType Directory -Path $winApps | Out-Null }
$shortcuts = 'telekeyboard','tk','keyboard'
foreach ($s in $shortcuts) {
    $cmdPath = Join-Path $winApps ("$s.cmd")
    "@start `"`" wscript.exe `"$target\launcher.vbs`"" | Set-Content -Path $cmdPath -Encoding ASCII
}
Write-Host "🔗 Shortcut Win+R terdaftar." -ForegroundColor Cyan

# 8. Registrasi auto‑start di folder Startup
$startup = [Environment]::GetFolderPath('Startup')
$lnkPath = Join-Path $startup 'TeleKeyboard.lnk'
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath = 'wscript.exe'
$lnk.Arguments = "`"$target\launcher.vbs`""
$lnk.WorkingDirectory = $target
$lnk.Description = 'TeleKeyboard Auto‑Start Service'
$lnk.Save()
Write-Host "✅ Auto‑start di Startup selesai." -ForegroundColor Green

# 9. Jalankan launcher untuk pertama kali
Write-Host "🚦 Menjalankan TeleKeyboard…" -ForegroundColor Green
wscript "${target}\launcher.vbs"
Write-Host "✅ Instalasi selesai! Tekan Win+R → ketik 'telekeyboard' atau 'tk' untuk memulai." -ForegroundColor Cyan