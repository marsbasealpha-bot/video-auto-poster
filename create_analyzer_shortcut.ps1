# Find pythonw.exe from the project venv
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonW = Join-Path $ProjectDir "venv\Scripts\pythonw.exe"
if (-not (Test-Path $PythonW)) {
    Write-Host "ERROR: pythonw.exe not found at $PythonW" -ForegroundColor Red
    exit 1
}

$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop", "Video Analyzer.lnk")
$Shortcut = $WshShell.CreateShortcut($DesktopPath)
$Shortcut.TargetPath = $PythonW
$Shortcut.Arguments = "`"$ProjectDir\analyzer_gui.pyw`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.IconLocation = "shell32.dll,14"
$Shortcut.Description = "Launch Video Analyzer"
$Shortcut.Save()
Write-Host "Desktop shortcut created: $DesktopPath" -ForegroundColor Green
