@echo off
title Uninstall TeleKeyboard Auto-Start
echo ========================================================
echo   Mencopot Pemasangan Auto-Start TeleKeyboard
echo ========================================================
echo.

powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telekeyboard.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Menghentikan proses TeleKeyboard PID:' $_.ProcessId }"

powershell -Command "$startup = [Environment]::GetFolderPath('Startup') + '\TeleKeyboard.lnk'; if (Test-Path $startup) { Remove-Item $startup -Force; Write-Host 'Shortcut Startup berhasil dihapus.' }"

powershell -Command "$desktop = [Environment]::GetFolderPath('Desktop') + '\TeleKeyboard.lnk'; if (Test-Path $desktop) { Remove-Item $desktop -Force; Write-Host 'Shortcut Desktop berhasil dihapus.' }"

echo.
echo TeleKeyboard telah dihentikan dan dicopot dari Auto-Start Windows.
timeout /t 3 >nul
