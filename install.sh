#!/usr/bin/env bash
# rbgrab installer for macOS (Apple Silicon). Run in Terminal:
#   curl -fsSL https://raw.githubusercontent.com/neelb1/rbgrab/main/install.sh | bash
set -euo pipefail

REPO="neelb1/rbgrab"
SUPPORT="$HOME/Library/Application Support/rbgrab"
BIN="$SUPPORT/bin"
APPS="$HOME/Applications"
step() { printf '  \033[36m->\033[0m %s\n' "$1"; }

[ "$(uname)" = "Darwin" ] || { echo "This installer is for macOS. On Windows use install.ps1."; exit 1; }
if [ "$(uname -m)" != "arm64" ]; then
  echo "Prebuilt app is Apple Silicon only. On Intel Macs run from source:"
  echo "  pipx install git+https://github.com/$REPO && rbgrab"
  exit 1
fi

printf '\nInstalling rbgrab\n\n'
mkdir -p "$BIN" "$APPS"
pkill -f "rbgrab.app/Contents/MacOS/rbgrab" 2>/dev/null || true
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

step "Downloading rbgrab"
if [ -n "${RBGRAB_ZIP:-}" ]; then cp "$RBGRAB_ZIP" "$TMP/rbgrab.zip"
else curl -fsSL -o "$TMP/rbgrab.zip" "https://github.com/$REPO/releases/latest/download/rbgrab-macos-arm64.zip"; fi
rm -rf "$APPS/rbgrab.app"
ditto -x -k "$TMP/rbgrab.zip" "$APPS"
xattr -dr com.apple.quarantine "$APPS/rbgrab.app" 2>/dev/null || true

step "Downloading yt-dlp"
curl -fsSL -o "$BIN/yt-dlp" "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
chmod +x "$BIN/yt-dlp"

if [ -x "$BIN/ffmpeg" ] || command -v ffmpeg >/dev/null; then
  step "ffmpeg already installed"
elif command -v brew >/dev/null; then
  step "Installing ffmpeg with Homebrew"
  brew install ffmpeg
else
  step "Downloading ffmpeg"
  curl -fsSL -o "$TMP/ffmpeg.zip" "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffmpeg.zip" \
    && ditto -x -k "$TMP/ffmpeg.zip" "$BIN" && chmod +x "$BIN/ffmpeg" \
    || echo "Couldn't download ffmpeg. Install Homebrew (https://brew.sh) then run: brew install ffmpeg"
fi

open "$APPS/rbgrab.app"
printf '\n\033[32mDone.\033[0m rbgrab is in your menu bar. Allow it under\n'
printf 'System Settings -> Privacy & Security -> Input Monitoring, then press Control+Option+S.\n\n'
