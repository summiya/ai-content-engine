#!/bin/zsh
PLIST="$HOME/Library/LaunchAgents/com.contentengine.instagram.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo 'Local scheduler disabled. Existing images remain on your Mac.'
