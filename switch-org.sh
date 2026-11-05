#!/bin/zsh
# Switch Claude Desktop Code sessions and scheduled tasks to another organization.
#   switch-org.sh                     list organizations
#   switch-org.sh <target> --dry-run  show what would move
#   switch-org.sh <target>            arm the switch, then press ⌘Q in Claude Desktop
#   switch-org.sh cancel              cancel an armed switch
# <target>: organization uuid / uuid prefix / alias / name (see list).
W="${0:A:h}"
LABEL=com.claude-org-switch.mover
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY=/usr/bin/python3

if ! $PY -c 'import sys' >/dev/null 2>&1; then
  print "/usr/bin/python3 is required. Run xcode-select --install to get the Command Line Tools."
  exit 1
fi

case "$1" in
  ""|list) exec $PY -I "$W/switch_org.py" list ;;
  cancel)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
    rm -f "$PLIST"
    print "Cancelled (if a switch was armed)."
    exit 0 ;;
esac

ORG=$($PY -I "$W/switch_org.py" resolve "$1") || exit 2
$PY -I "$W/switch_org.py" plan "$ORG" || exit $?
[[ "$2" == "--dry-run" ]] && exit 0

if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  print "A switch is already waiting for Desktop to quit. To re-arm, first run: $0 cancel"
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$LABEL</string>
<key>ProgramArguments</key><array><string>/bin/zsh</string><string>$W/run_after_quit.sh</string><string>$ORG</string></array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><false/>
</dict></plist>
EOF
launchctl bootstrap "gui/$(id -u)" "$PLIST" || { rm -f "$PLIST"; exit 1; }

print "Armed: switching to $ORG once Claude Desktop quits."
print "1. Press ⌘Q in Claude Desktop. It reopens by itself in about 20 seconds."
print "2. Run claude /login in a terminal and pick the target org, so CLI-started background sessions land there too."
print "3. Switch to the target org in Desktop's account menu (bottom left)."
print "Log: $W/run.log"
