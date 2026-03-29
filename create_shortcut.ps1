$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop", "Video Auto-Poster.lnk")
$Shortcut = $WshShell.CreateShortcut($DesktopPath)
$Shortcut.TargetPath = "c:\Users\Admin\Desktop\PROJECTS\video-auto-poster\launch.bat"
$Shortcut.WorkingDirectory = "c:\Users\Admin\Desktop\PROJECTS\video-auto-poster"
$Shortcut.IconLocation = "shell32.dll,176"
$Shortcut.Description = "Launch Video Auto-Poster"
$Shortcut.Save()
Write-Host "Desktop shortcut created: $DesktopPath"
