' ==============================================================================
' TeleKeyboard - Silent Auto-Setup & Launcher (GitHub Ready)
' 1. Tidak pernah memunculkan jendela CMD / konsol hitam (Zero CMD).
' 2. Mendaftarkan perintah Win + R (telekeyboard & tk).
' 3. Jika config.json belum ada, otomatis dibuatkan template.
' 4. Mendukung laptop baru secara otomatis (cek dependensi di latar belakang).
' 5. Mendaftarkan auto-start di Startup Windows.
' 6. Menampilkan Notepad berisi tulisan 'terhubung ke keyboard'.
' ==============================================================================

Option Explicit
Dim WshShell, fso, currentDir, tempFolder, statusFile, txtStream
Dim desktopPath, startupPath, lnk, chkCode, winApps, cmdFile

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Dapatkan path folder saat ini secara dinamis
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

' 0. Daftarkan perintah Win + R via WindowsApps
winApps = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Microsoft\WindowsApps")
If fso.FolderExists(winApps) Then
    Set cmdFile = fso.CreateTextFile(winApps & "\telekeyboard.cmd", True)
    cmdFile.WriteLine "@start """" wscript.exe """ & currentDir & "\launcher.vbs"""
    cmdFile.Close
    
    Set cmdFile = fso.CreateTextFile(winApps & "\tk.cmd", True)
    cmdFile.WriteLine "@start """" wscript.exe """ & currentDir & "\launcher.vbs"""
    cmdFile.Close
    
    Set cmdFile = fso.CreateTextFile(winApps & "\keyboard.cmd", True)
    cmdFile.WriteLine "@start """" wscript.exe """ & currentDir & "\launcher.vbs"""
    cmdFile.Close
End If

' 1. Jika config.json belum ada (misal baru clone dari GitHub), siapkan dari config.example.json
If Not fso.FileExists(currentDir & "\config.json") Then
    If fso.FileExists(currentDir & "\config.example.json") Then
        fso.CopyFile currentDir & "\config.example.json", currentDir & "\config.json"
    End If
    WshShell.Run "notepad.exe """ & currentDir & "\config.json""", 1, True
End If

' 2. Perbarui / Daftarkan auto-start di Startup Windows (otomatis aktif saat laptop nyala)
startupPath = WshShell.SpecialFolders("Startup")
Set lnk = WshShell.CreateShortcut(startupPath & "\TeleKeyboard.lnk")
lnk.TargetPath = "wscript.exe"
lnk.Arguments = """" & currentDir & "\launcher.vbs"""
lnk.WorkingDirectory = currentDir
lnk.Description = "TeleKeyboard Auto-Start Service"
lnk.Save

' 3. Cek dependensi jika dijalankan di laptop baru (semua dilakukan hening / hidden Style 0)
chkCode = WshShell.Run("python.exe -c ""import PIL, requests, psutil""", 0, True)
If chkCode <> 0 Then
    WshShell.Run "python.exe -m pip install -r """ & currentDir & "\requirements.txt"" --quiet", 0, True
End If

' 4. Hentikan instance lama jika ada, lalu jalankan bot dengan pythonw.exe (Hidden Style 0)
WshShell.Run "powershell.exe -NoProfile -WindowStyle Hidden -Command ""Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telekeyboard.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }""", 0, True

WshShell.Run "pythonw.exe """ & currentDir & "\telekeyboard.py""", 0, False

' 5. Buat file status dan buka Notepad bertuliskan 'terhubung ke keyboard'
tempFolder = WshShell.ExpandEnvironmentStrings("%TEMP%")
statusFile = tempFolder & "\password.txt"

Set txtStream = fso.CreateTextFile(statusFile, True, False)
txtStream.WriteLine "password:990"
txtStream.Close

' Buka Notepad (Style 1 = Tampil normal di layar)
WshShell.Run "notepad.exe """ & statusFile & """", 1, False
