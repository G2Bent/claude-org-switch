#!/bin/zsh
# Started by switch-org.sh through a one-shot LaunchAgent. Waits for Claude
# Desktop to quit, backs up, moves Code sessions and scheduled tasks to the
# target organization, then reopens Desktop.
W="${0:A:h}"
LABEL=com.claude-org-switch.mover
ORG="$1"
LOG="$W/run.log"
exec >>"$LOG" 2>&1
cleanup() {
  rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
}
trap cleanup EXIT
echo "[$(date)] switch to $ORG: waiting for Claude Desktop to quit"

for i in {1..1440}; do  # up to 2 hours, 5s interval
  [[ "$(osascript -e 'application "Claude" is running' 2>/dev/null)" == "false" ]] && break
  sleep 5
done
if [[ "$(osascript -e 'application "Claude" is running' 2>/dev/null)" != "false" ]]; then
  echo "[$(date)] Desktop still running after 2h, giving up without changes"
  exit 1
fi

sleep 5
echo "[$(date)] Desktop quit, backing up"
cd "$HOME/Library/Application Support/Claude" || exit 1
tar -czf "$W/backup-$(date +%Y%m%d-%H%M%S).tgz" claude-code-sessions \
  || { echo "backup failed, abort"; open -a Claude; exit 1; }
ls -t "$W"/backup-*.tgz | tail -n +6 | while read -r old; do rm -f "$old"; done  # keep 5 newest

/usr/bin/python3 -I "$W/switch_org.py" apply "$ORG"
rc=$?
echo "[$(date)] switch finished (exit $rc), reopening Desktop"
open -a Claude
if [[ $rc -eq 0 ]]; then
  osascript -e 'display notification "运行 claude /login 选目标组织，再在 Desktop 切换组织" with title "Code 会话已移到目标组织"' 2>/dev/null
elif [[ $rc -eq 3 || $rc -eq 4 ]]; then
  osascript -e 'display notification "什么都没改，详情看 run.log" with title "切换组织没有执行"' 2>/dev/null
else
  osascript -e 'display notification "可能只搬了一部分，按 README 用最新备份回滚，详情看 run.log" with title "切换组织出错"' 2>/dev/null
fi
echo "[$(date)] done"
