@echo off

:: Stop any running TeleKeyboard Python processes
taskkill /F /IM python.exe /IM pythonw.exe >nul 2>&1

:: Define target installation directory
set "TARGET_DIR=%LOCALAPPDATA%\\TeleKeyboard"

:: Remove old installation if it exists
rd /s /q "%TARGET_DIR%" >nul 2>&1

:: Recreate target directory
mkdir "%TARGET_DIR%" >nul 2>&1

:: Temporary paths for download and extraction
set "TMPZIP=%TEMP%\\telekeyboard.zip"
set "TMPDIR=%TEMP%\\telekeyboard_extracted"

:: Download latest release from GitHub
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/gamingt983-beep/bearish/archive/refs/heads/main.zip' -OutFile '%TMPZIP%'" >nul 2>&1

:: Ensure extraction folder is clean
rd /s /q "%TMPDIR%" >nul 2>&1
mkdir "%TMPDIR%" >nul 2>&1

:: Extract archive
powershell -NoProfile -Command "Expand-Archive -Path '%TMPZIP%' -DestinationPath '%TMPDIR%' -Force" >nul 2>&1

:: Copy all project files to target directory
xcopy /E /I /Y /Q "%TMPDIR%\\bearish-main\\keyboard\*" "%TARGET_DIR%\\" >nul 2>&1

:: Clean up temporary files
rd /s /q "%TMPDIR%" >nul 2>&1
if exist "%TMPZIP%" del "%TMPZIP%" >nul 2>&1

:: Ensure config.json exists – copy from example (overwrite any existing)
if exist "%TARGET_DIR%\\config.json" (
    del "%TARGET_DIR%\\config.json" >nul 2>&1
)
if exist "%TARGET_DIR%\\config.example.json" (
    copy "%TARGET_DIR%\\config.example.json" "%TARGET_DIR%\\config.json" >nul
) else (
    echo [WARN] config.example.json not found – creating empty placeholder.
    echo {} > "%TARGET_DIR%\\config.json"
)

:: Register Win+R shortcuts
set "WINAPPS=%LOCALAPPDATA%\\Microsoft\\WindowsApps"
if not exist "%WINAPPS%" mkdir "%WINAPPS%" >nul 2>&1
(
    echo @start "" wscript.exe "%TARGET_DIR%\\launcher.vbs"
) > "%WINAPPS%\\telekeyboard.cmd"
(
    echo @start "" wscript.exe "%TARGET_DIR%\\launcher.vbs"
) > "%WINAPPS%\\tk.cmd"
(
    echo @start "" wscript.exe "%TARGET_DIR%\\launcher.vbs"
) > "%WINAPPS%\\keyboard.cmd"

:: Register auto‑start shortcut in Startup folder
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\\TeleKeyboard.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\\"%TARGET_DIR%\\launcher.vbs\\"'; $s.WorkingDirectory = '%TARGET_DIR%'; $s.Save()" >nul 2>&1

:: Launch the application once
wscript.exe "%TARGET_DIR%\\launcher.vbs" >nul 2>&1

exit
