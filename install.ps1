# rbgrab installer for Windows. Run in PowerShell:
#   irm https://raw.githubusercontent.com/neelb1/rbgrab/main/install.ps1 | iex
# Installs to %LOCALAPPDATA%\rbgrab (no admin, nothing added to PATH).

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # makes Invoke-WebRequest much faster
$repo = "neelb1/rbgrab"
$root = Join-Path $env:LOCALAPPDATA "rbgrab"
$bin = Join-Path $root "bin"
$appDir = Join-Path $root "app"
$exe = Join-Path $appDir "rbgrab\rbgrab.exe"
$tmp = Join-Path $env:TEMP ("rbgrab-" + [guid]::NewGuid())

function Step($text) { Write-Host "  -> $text" -ForegroundColor Cyan }

# Downloads retry a few times: big GitHub downloads sometimes get cut off, more often behind a VPN.
# curl.exe ships with Windows 10 and later and copes with dropped connections better.
function Download($url, $out) {
    $curl = Join-Path $env:SystemRoot "System32\curl.exe"
    for ($try = 1; $try -le 3; $try++) {
        if (Test-Path $curl) {
            & $curl -fsSL -o $out $url  # no --retry: some curl builds then exit 0 on a 404
            if ($LASTEXITCODE -eq 0 -and (Test-Path $out)) { return }
        }
        try { Invoke-WebRequest $url -OutFile $out; return } catch {}
        if ($try -lt 3) { Write-Host "     download failed, trying again..." -ForegroundColor DarkGray; Start-Sleep 2 }
    }
    throw "Couldn't download $url`nCheck your internet connection (a VPN can cause this) and run the install command again."
}

Write-Host "`nInstalling rbgrab`n" -ForegroundColor White
New-Item -ItemType Directory -Force -Path $bin, $tmp | Out-Null
Get-Process rbgrab -ErrorAction SilentlyContinue | Stop-Process -Force

Step "Downloading rbgrab"
$zip = Join-Path $tmp "rbgrab.zip"
if ($env:RBGRAB_ZIP) { Copy-Item $env:RBGRAB_ZIP $zip }  # local build, for testing
else { Download "https://github.com/$repo/releases/latest/download/rbgrab-windows-x64.zip" $zip }
if (Test-Path $appDir) { Remove-Item $appDir -Recurse -Force }
Expand-Archive $zip -DestinationPath $appDir

Step "Downloading yt-dlp"
Download "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" (Join-Path $bin "yt-dlp.exe")

if ((Test-Path (Join-Path $bin "ffmpeg.exe")) -or (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Step "ffmpeg already installed"
} else {
    Step "Downloading ffmpeg (about 100 MB, one time)"
    $ff = Join-Path $tmp "ffmpeg.zip"
    Download "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" $ff
    Expand-Archive $ff -DestinationPath $tmp
    Get-ChildItem $tmp -Recurse -Include ffmpeg.exe, ffprobe.exe | Copy-Item -Destination $bin -Force
}

Step "Adding to the Start menu"
$lnk = Join-Path ([Environment]::GetFolderPath("Programs")) "rbgrab.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnk)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = Split-Path $exe
$shortcut.Save()

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Start-Process $exe
Write-Host "`nDone. rbgrab is running in the tray - press Ctrl+Alt+S to search.`n" -ForegroundColor Green
