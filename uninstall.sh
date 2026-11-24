#!/usr/bin/env bash
# Removes rbgrab. Your downloaded songs and rekordbox.xml are kept.
#   curl -fsSL https://raw.githubusercontent.com/neelb1/rbgrab/main/uninstall.sh | bash
pkill -f "rbgrab.app/Contents/MacOS/rbgrab" 2>/dev/null || true
rm -rf "$HOME/Applications/rbgrab.app" "$HOME/Library/Application Support/rbgrab"
rm -f "$HOME/Library/LaunchAgents/com.rbgrab.app.plist"
echo "rbgrab removed. Your music folder was left alone."
