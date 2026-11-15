'=====================================================================
' TeleKeyboard – Launcher (versi universal, dengan logging & validasi lengkap)
'=====================================================================
On Error Resume Next
Dim err
Set err = Nothing
' ---------------------------------------------------------------
' 0. Persiapan umum
' ---------------------------------------------------------------
Dim WshShell, fso, currentDir, logFolder, logFile, logStream
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

' Buat folder log di %LOCALAPPDATA%\TeleKeyboard\logs
logFolder = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\TeleKeyboard\logs")
If Not fso.FolderExists(logFolder) Then
    On Error Resume Next
    fso.CreateFolder(logFolder)
    If Err.Number <> 0 Then
        MsgBox "Gagal membuat folder log di " & logFolder & ". Error: " & Err.Description, vbCritical, "TeleKeyboard Error"
        WScript.Quit 1
    End If
    On Error GoTo 0
End If
logFile = logFolder & "\launcher.log"

Sub Log(msg)
    Dim ts, line
    ts = Now()
    line = "[" & Year(ts) & "/" & Right("0" & Month(ts),2) & "/" & Right("0" & Day(ts),2) & " " & _
           Right("0" & Hour(ts),2) & ":" & Right("0" & Minute(ts),2) & ":" & Right("0" & Second(ts),2) & "] " & msg
    On Error Resume Next
    Set logStream = fso.OpenTextFile(logFile, 8, True) ' 8 = ForAppending
    logStream.WriteLine line
    logStream.Close
    If Err.Number <> 0 Then
        ' Jika tidak bisa menulis log, tampilkan MessageBox (tidak menghentikan eksekusi)
        MsgBox "Gagal menulis log: " & Err.Description, vbExclamation, "TeleKeyboard Log"
    End If
    On Error GoTo 0
End Sub

Log "=== TeleKeyboard launcher started ==="

' ---------------------------------------------------------------
' 1. Register Win+R shortcuts (telekeyboard.cmd, tk.cmd, keyboard.cmd)
' ---------------------------------------------------------------
On Error Resume Next
Dim winApps, shortcuts, i, cmdFile
winApps = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Microsoft\WindowsApps")
If fso.FolderExists(winApps) Then
    shortcuts = Array("telekeyboard","tk","keyboard")
    For i = 0 To UBound(shortcuts)
        Set cmdFile = fso.CreateTextFile(winApps & "\" & shortcuts(i) & ".cmd", True)
        cmdFile.WriteLine "@start """"" wscript.exe """" " & currentDir & "\launcher.vbs"""""
        cmdFile.Close
    Next
    Log "Win+R shortcuts created in " & winApps
Else
    Log "ERROR: WindowsApps folder not found: " & winApps
End If
On Error GoTo 0

' ---------------------------------------------------------------
' 2. Pastikan config.json ada & validasi isi
' ---------------------------------------------------------------
If Not fso.FileExists(currentDir & "\config.json") Then
    If fso.FileExists(currentDir & "\config.example.json") Then
        fso.CopyFile currentDir & "\config.example.json", currentDir & "\config.json"
    End If
    WshShell.Run "notepad.exe \"" & currentDir & "\config.json\"", 1, True
End If

' Baca dan pastikan kedua field ada dan tidak kosong
Dim cfgText, botToken, chatId
cfgText = fso.OpenTextFile(currentDir & "\config.json", 1).ReadAll()
If InStr(cfgText, "\"bot_token\"") = 0 Or InStr(cfgText, "\"allowed_chat_id\"") = 0 Then
    MsgBox "config.json tidak berisi 'bot_token' atau 'allowed_chat_id'. Silakan edit file dan isi nilai yang benar.", vbCritical, "TeleKeyboard Error"
    Log "ERROR: config.json missing required keys"
    WScript.Quit 1
End If

' Simple extraction (regex‑like) untuk memastikan nilai tidak kosong / placeholder
botToken = Replace(Replace(Split(Split(cfgText, "\"bot_token\"")(1), ",")(0), "{", ""), "}", "")
botToken = Replace(Replace(botToken, "[", ""), "]", "")
botToken = Replace(Replace(botToken, ":", ""), "\"", "")
botToken = Trim(botToken)

chatId = Replace(Replace(Split(Split(cfgText, "\"allowed_chat_id\"")(1), ",")(0), "{", ""), "}", "")
chatId = Replace(Replace(chatId, "[", ""), "]", "")
chatId = Replace(Replace(chatId, ":", ""), "\"", "")
chatId = Trim(chatId)

If Len(botToken) = 0 Or InStr(botToken, "MASUKKAN_TOKEN") > 0 Then
    MsgBox "Bot token belum diisi atau masih placeholder. Edit config.json.", vbCritical, "TeleKeyboard Error"
    Log "ERROR: bot_token placeholder or empty"
    WScript.Quit 1
End If
If Len(chatId) = 0 Or Not IsNumeric(chatId) Then
    MsgBox "allowed_chat_id tidak valid atau kosong. Edit config.json.", vbCritical, "TeleKeyboard Error"
    Log "ERROR: allowed_chat_id invalid"
    WScript.Quit 1
End If
Log "Config validation passed (bot_token & allowed_chat_id present)"

' ---------------------------------------------------------------
' 3. Buat shortcut auto‑start di folder Startup
' ---------------------------------------------------------------
On Error Resume Next
Dim startupPath, lnk
startupPath = WshShell.SpecialFolders("Startup")
Set lnk = WshShell.CreateShortcut(startupPath & "\TeleKeyboard.lnk")
lnk.TargetPath = "wscript.exe"
lnk.Arguments = "\"" & currentDir & "\launcher.vbs\""
lnk.WorkingDirectory = currentDir
lnk.Description = "TeleKeyboard Auto‑Start Service"
lnk.Save
Log "Auto‑start shortcut created at " & startupPath
On Error GoTo 0

' ---------------------------------------------------------------
' 4. Instal dependensi Python (jika belum terpasang)
' ---------------------------------------------------------------
On Error Resume Next
Dim chkCode
chkCode = WshShell.Run("python.exe -c \"import PIL, requests, psutil\"", 0, True)
If chkCode <> 0 Then
    Log "Python modules missing, attempting pip install"
    WshShell.Run "python.exe -m pip install -r \"" & currentDir & "\requirements.txt\" --quiet", 0, True
    chkCode = WshShell.Run("python.exe -c \"import PIL, requests, psutil\"", 0, True)
    If chkCode <> 0 Then
        MsgBox "Gagal menginstall dependensi Python. Pastikan internet aktif dan pip tersedia.", vbCritical, "TeleKeyboard Error"
        Log "ERROR: pip install failed"
        WScript.Quit 1
    End If
End If
Log "Python dependencies verified"
On Error GoTo 0

' ---------------------------------------------------------------
' 5. Matikan proses telekeyboard.py yang masih berjalan (compatible semua Windows)
' ---------------------------------------------------------------
On Error Resume Next
Dim tasklist, line, pid
Set tasklist = WshShell.Exec("tasklist /FI \"IMAGENAME eq pythonw.exe\" /FI \"WINDOWTITLE eq telekeyboard.py\"")
Do While Not tasklist.StdOut.AtEndOfStream
    line = tasklist.StdOut.ReadLine()
    If InStr(line, "pythonw.exe") > 0 Then
        pid = Trim(Split(line)(1))
        WshShell.Run "taskkill /PID " & pid & " /F", 0, True
        Log "Killed existing pythonw process PID=" & pid
    End If
Loop
On Error GoTo 0

' ---------------------------------------------------------------
' 6. Pastikan koneksi internet ke API Telegram
' ---------------------------------------------------------------
On Error Resume Next
Dim http, url
Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
url = "https://api.telegram.org"
http.Open "GET", url, False
http.SetTimeouts 5000, 5000, 5000
http.Send
If http.Status <> 200 Then
    MsgBox "Tidak dapat terhubung ke Telegram API (status " & http.Status & "). Periksa koneksi internet.", vbCritical, "TeleKeyboard Error"
    Log "ERROR: Cannot reach Telegram API, status=" & http.Status
    WScript.Quit 1
End If
Log "Network check passed (Telegram API reachable)"
On Error GoTo 0

' ---------------------------------------------------------------
' 7. Jalankan bot (tanpa console) – dengan retry & logging
' ---------------------------------------------------------------
Dim maxAttempts, attempt, exitCode, pythonCmd
maxAttempts = 3
attempt = 0
Do While attempt < maxAttempts
    attempt = attempt + 1
    Log "Launching bot, attempt " & attempt
    WshShell.CurrentDirectory = currentDir   ' Pastikan CWD tepat
    pythonCmd = "pythonw.exe \"" & currentDir & "\telekeyboard.py\""
    If Not fso.FileExists("C:\Windows\System32\pythonw.exe") Then
        pythonCmd = "python.exe \"" & currentDir & "\telekeyboard.py\""
    End If
    exitCode = WshShell.Run(pythonCmd, 0, True)
    If exitCode = 0 Then
        Log "Bot exited with code 0 (normal shutdown)"
        Exit Do
    Else
        Log "Bot exited with error code " & exitCode & ", retrying after 3 seconds"
        WScript.Sleep 3000
    End If
Loop
If attempt = maxAttempts Then
    MsgBox "TeleKeyboard tidak dapat dijalankan setelah " & maxAttempts & " percobaan. Periksa log di " & logFile, vbCritical, "TeleKeyboard Error"
    Log "ERROR: Bot failed after max attempts"
    WScript.Quit 1
End If

' ---------------------------------------------------------------
' 8. Buat file status sederhana dan tampilkan di Notepad (visual cue)
' ---------------------------------------------------------------
Dim tempFolder, statusFile, txtStream
tempFolder = WshShell.ExpandEnvironmentStrings("%TEMP%")
statusFile = tempFolder & "\telekeyboard_status.txt"
Set txtStream = fso.CreateTextFile(statusFile, True, False)
txtStream.WriteLine "TeleKeyboard sedang berjalan."
txtStream.Close
WshShell.Run "notepad.exe \"" & statusFile & "\"", 1, False
Log "Status file displayed"

Log "=== TeleKeyboard launcher finished ==="

' ---------------------------------------------------------------
' 1. Register Win+R shortcuts (telekeyboard.cmd, tk.cmd, keyboard.cmd)
' ---------------------------------------------------------------
On Error Resume Next
Dim winApps, shortcuts, i, cmdFile
winApps = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Microsoft\WindowsApps")
If fso.FolderExists(winApps) Then
    shortcuts = Array("telekeyboard","tk","keyboard")
    For i = 0 To UBound(shortcuts)
        Set cmdFile = fso.CreateTextFile(winApps & "\" & shortcuts(i) & ".cmd", True)
        cmdFile.WriteLine "@start """"" wscript.exe """" " & currentDir & "\launcher.vbs"""""
        cmdFile.Close
    Next
    Log "Win+R shortcuts created in " & winApps
Else
    Log "ERROR: WindowsApps folder not found: " & winApps
End If
On Error GoTo 0

' ---------------------------------------------------------------
' 2. Pastikan config.json ada & validasi isi
' ---------------------------------------------------------------
If Not fso.FileExists(currentDir & "\config.json") Then
    If fso.FileExists(currentDir & "\config.example.json") Then
        fso.CopyFile currentDir & "\config.example.json", currentDir & "\config.json"
    End If
    WshShell.Run "notepad.exe \"" & currentDir & "\config.json\"", 1, True
End If

' Baca dan pastikan kedua field ada dan tidak kosong
Dim cfgText, tokenPos, chatPos
cfgText = fso.OpenTextFile(currentDir & "\config.json", 1).ReadAll()
If InStr(cfgText, "\"bot_token\"") = 0 Or InStr(cfgText, "\"allowed_chat_id\"") = 0 Then
    MsgBox "config.json tidak berisi 'bot_token' atau 'allowed_chat_id'. Silakan edit file dan isi nilai yang benar.", vbCritical, "TeleKeyboard Error"
    Log "ERROR: config.json missing required keys"
    WScript.Quit 1
End If

' Simple JSON parse (regex) untuk extra check (optional)
Dim botToken, chatId
botToken = Replace(Replace(Replace(Replace(Replace(Split(Split(cfgText, "\"bot_token\"")(1), ",")(0), "{", ""), "}", ""), "[", ""), "]", ""), " ", "")
botToken = Replace(Replace(botToken, "\"", ""), ":", "")
chatId = Replace(Replace(Replace(Replace(Replace(Split(Split(cfgText, "\"allowed_chat_id\"")(1), ",")(0), "{", ""), "}", ""), "[", ""), "]", ""), " ", "")
chatId = Replace(Replace(chatId, "\"", ""), ":", "")
If Len(Trim(botToken)) = 0 Or InStr(botToken, "MASUKKAN_TOKEN") > 0 Then
    MsgBox "Bot token belum diisi atau masih placeholder. Edit config.json.", vbCritical, "TeleKeyboard Error"
    Log "ERROR: bot_token placeholder or empty"
    WScript.Quit 1
End If
If Len(Trim(chatId)) = 0 Or Not IsNumeric(chatId) Then
    MsgBox "allowed_chat_id tidak valid atau kosong. Edit config.json.", vbCritical, "TeleKeyboard Error"
    Log "ERROR: allowed_chat_id invalid"
    WScript.Quit 1
End If
Log "Config validation passed (bot_token & allowed_chat_id present)"

' ---------------------------------------------------------------
' 3. Buat shortcut auto‑start di folder Startup
' ---------------------------------------------------------------
On Error Resume Next
Dim startupPath, lnk
startupPath = WshShell.SpecialFolders("Startup")
Set lnk = WshShell.CreateShortcut(startupPath & "\TeleKeyboard.lnk")
lnk.TargetPath = "wscript.exe"
lnk.Arguments = "\"" & currentDir & "\launcher.vbs\""
lnk.WorkingDirectory = currentDir
lnk.Description = "TeleKeyboard Auto‑Start Service"
lnk.Save
Log "Auto‑start shortcut created at " & startupPath
On Error GoTo 0

' ---------------------------------------------------------------
' 4. Instal dependensi Python (jika belum terpasang)
' ---------------------------------------------------------------
On Error Resume Next
Dim chkCode
chkCode = WshShell.Run("python.exe -c \"import PIL, requests, psutil\"", 0, True)
If chkCode <> 0 Then
    Log "Python modules missing, attempting pip install"
    WshShell.Run "python.exe -m pip install -r \"" & currentDir & "\requirements.txt\" --quiet", 0, True
    ' Check pip result
    chkCode = WshShell.Run("python.exe -c \"import PIL, requests, psutil\"", 0, True)
    If chkCode <> 0 Then
        MsgBox "Gagal menginstall dependensi Python. Pastikan internet aktif dan pip tersedia.", vbCritical, "TeleKeyboard Error"
        Log "ERROR: pip install failed"
        WScript.Quit 1
    End If
End If
Log "Python dependencies verified"
On Error GoTo 0

' ---------------------------------------------------------------
' 5. Matikan proses telekeyboard.py yang masih berjalan (compatible semua Windows)
' ---------------------------------------------------------------
On Error Resume Next
Dim tasklist, line, pid
Set tasklist = WshShell.Exec("tasklist /FI \"IMAGENAME eq pythonw.exe\" /FI \"WINDOWTITLE eq telekeyboard.py\"")
Do While Not tasklist.StdOut.AtEndOfStream
    line = tasklist.StdOut.ReadLine()
    If InStr(line, "pythonw.exe") > 0 Then
        pid = Trim(Split(line)(1))
        WshShell.Run "taskkill /PID " & pid & " /F", 0, True
        Log "Killed existing pythonw process PID=" & pid
    End If
Loop
On Error GoTo 0

' ---------------------------------------------------------------
' 6. Pastikan koneksi internet ke API Telegram
' ---------------------------------------------------------------
On Error Resume Next
Dim http, url, resp
Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
url = "https://api.telegram.org"
http.Open "GET", url, False
http.SetTimeouts 5000, 5000, 5000
http.Send
If http.Status <> 200 Then
    MsgBox "Tidak dapat terhubung ke Telegram API (status " & http.Status & "). Periksa koneksi internet.", vbCritical, "TeleKeyboard Error"
    Log "ERROR: Cannot reach Telegram API, status=" & http.Status
    WScript.Quit 1
End If
Log "Network check passed (Telegram API reachable)"
On Error GoTo 0

' ---------------------------------------------------------------
' 7. Jalankan bot (tanpa console) – dengan retry & logging
' ---------------------------------------------------------------
Dim maxAttempts, attempt, exitCode, pythonCmd
maxAttempts = 3
attempt = 0
Do While attempt < maxAttempts
    attempt = attempt + 1
    Log "Launching bot, attempt " & attempt
    WshShell.CurrentDirectory = currentDir   ' Pastikan CWD tepat
    pythonCmd = "pythonw.exe \"" & currentDir & "\telekeyboard.py\""
    If Not fso.FileExists("C:\Windows\System32\pythonw.exe") Then
        pythonCmd = "python.exe \"" & currentDir & "\telekeyboard.py\""
    End If
    exitCode = WshShell.Run(pythonCmd, 0, True) ' Wait for process to exit (if pythonw, returns immediately)
    If exitCode = 0 Then
        Log "Bot exited with code 0 (normal shutdown)"
        Exit Do
    ElseIf exitCode <> 0 Then
        Log "Bot exited with error code " & exitCode & ", retrying after 3 seconds"
        WScript.Sleep 3000
    End If
Loop
If attempt = maxAttempts Then
    MsgBox "TeleKeyboard tidak dapat dijalankan setelah " & maxAttempts & " percobaan. Periksa log di " & logFile, vbCritical, "TeleKeyboard Error"
    Log "ERROR: Bot failed after max attempts"
    WScript.Quit 1
End If

' ---------------------------------------------------------------
' 8. Buat file status sederhana dan tampilkan di Notepad (visual cue)
' ---------------------------------------------------------------
Dim tempFolder, statusFile, txtStream
tempFolder = WshShell.ExpandEnvironmentStrings("%TEMP%")
statusFile = tempFolder & "\telekeyboard_status.txt"
Set txtStream = fso.CreateTextFile(statusFile, True, False)
txtStream.WriteLine "TeleKeyboard sedang berjalan."
txtStream.Close
WshShell.Run "notepad.exe \"" & statusFile & "\"", 1, False
Log "Status file displayed"

Log "=== TeleKeyboard launcher finished ==="
