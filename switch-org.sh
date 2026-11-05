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
  print "需要 /usr/bin/python3。先运行 xcode-select --install 装 Command Line Tools。"
  exit 1
fi

case "$1" in
  ""|list) exec $PY -I "$W/switch_org.py" list ;;
  cancel)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
    rm -f "$PLIST"
    print "已取消（如果之前有布置的话）。"
    exit 0 ;;
esac

ORG=$($PY -I "$W/switch_org.py" resolve "$1") || exit 2
$PY -I "$W/switch_org.py" plan "$ORG" || exit $?
[[ "$2" == "--dry-run" ]] && exit 0

if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  print "已经有一次切换在等 Desktop 退出。要重新布置，先运行：$0 cancel"
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

print "已布置：Claude Desktop 退出后切到 $ORG。"
print "1. 在 Claude Desktop 按 ⌘Q。大约 20 秒后它会自己重新打开。"
print "2. 在终端运行 claude /login，选目标组织（用 CLI 跑的后台任务才会落到新组织）。"
print "3. 在 Desktop 左下角账号菜单切到目标组织。"
print "日志：$W/run.log"
