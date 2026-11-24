# Removes rbgrab. Your downloaded songs and rekordbox.xml are kept.
#   irm https://raw.githubusercontent.com/neelb1/rbgrab/main/uninstall.ps1 | iex

$ErrorActionPreference = "SilentlyContinue"
Get-Process rbgrab | Stop-Process -Force
Start-Sleep -Milliseconds 500
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name rbgrab
Remove-Item (Join-Path ([Environment]::GetFolderPath("Programs")) "rbgrab.lnk")
Remove-Item (Join-Path $env:LOCALAPPDATA "rbgrab") -Recurse -Force
Remove-Item (Join-Path $env:APPDATA "rbgrab") -Recurse -Force
Write-Host "rbgrab removed. Your music folder was left alone." -ForegroundColor Green
