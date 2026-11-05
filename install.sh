#!/bin/zsh
# Install claude-org-switch: scripts to ~/Library/Application Support/claude-org-switch,
# the /switch skill to ~/.claude/skills/switch.
#   ./install.sh           install or update
#   ./install.sh --force   replace an existing /switch skill that is not this one
set -e
SRC="${0:A:h}"
DEST="$HOME/Library/Application Support/claude-org-switch"
SKILL_DIR="$HOME/.claude/skills/switch"

[[ "$(uname)" == "Darwin" ]] || { print "只支持 macOS 上的 Claude Desktop。"; exit 1; }
if ! /usr/bin/python3 -c 'import sys' >/dev/null 2>&1; then
  print "需要 /usr/bin/python3。先运行 xcode-select --install，装完再运行本脚本。"
  exit 1
fi
if [[ -f "$SKILL_DIR/SKILL.md" && "$1" != "--force" ]] && ! grep -q 'claude-org-switch' "$SKILL_DIR/SKILL.md"; then
  print "$SKILL_DIR 已经有一个别的 /switch skill。确认要替换的话运行：$0 --force"
  exit 1
fi

mkdir -p "$DEST" "$SKILL_DIR"
cp "$SRC/switch_org.py" "$SRC/switch-org.sh" "$SRC/run_after_quit.sh" "$DEST/"
chmod +x "$DEST/switch-org.sh" "$DEST/run_after_quit.sh"
[[ -f "$DEST/aliases.json" ]] || cp "$SRC/aliases.example.json" "$DEST/aliases.json"
cp "$SRC/skill/SKILL.md" "$SKILL_DIR/SKILL.md"

print "已安装到 $DEST"
print "在 Claude Code 里输入 /switch 即可。先看看你的组织："
"$DEST/switch-org.sh" list
