#!/bin/zsh
set -e
cd "$(dirname "$0")"
ROOT="$PWD"
PLIST="$HOME/Library/LaunchAgents/com.contentengine.instagram.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo 'First run: ./install_mac.sh'
  exit 1
fi
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.contentengine.instagram</string>
  <key>ProgramArguments</key><array>
    <string>$ROOT/.venv/bin/python</string>
    <string>$ROOT/content_engine.py</string>
    <string>run</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartInterval</key><integer>900</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$ROOT/logs/launchd-out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/launchd-error.log</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart "gui/$(id -u)/com.contentengine.instagram"
echo "Local scheduler enabled: every 15 min while Mac is awake/logged in."
echo "Nothing publishes unless AUTO_PUBLISH=true in .env."
