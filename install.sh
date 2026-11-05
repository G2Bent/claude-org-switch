#!/bin/zsh
# Install claude-org-switch: scripts to ~/Library/Application Support/claude-org-switch,
# the /switch skill to ~/.claude/skills/switch.
#   ./install.sh           install or update
#   ./install.sh --force   replace an existing /switch skill that is not this one
set -e
SRC="${0:A:h}"
DEST="$HOME/Library/Application Support/claude-org-switch"
SKILL_DIR="$HOME/.claude/skills/switch"

[[ "$(uname)" == "Darwin" ]] || { print "Only Claude Desktop on macOS is supported."; exit 1; }
if ! /usr/bin/python3 -c 'import sys' >/dev/null 2>&1; then
  print "/usr/bin/python3 is required. Run xcode-select --install, then run this script again."
  exit 1
fi
if [[ -f "$SKILL_DIR/SKILL.md" && "$1" != "--force" ]] && ! grep -q 'claude-org-switch' "$SKILL_DIR/SKILL.md"; then
  print "$SKILL_DIR already holds a different /switch skill. To replace it, run: $0 --force"
  exit 1
fi

mkdir -p "$DEST" "$SKILL_DIR"
cp "$SRC/switch_org.py" "$SRC/switch-org.sh" "$SRC/run_after_quit.sh" "$DEST/"
chmod +x "$DEST/switch-org.sh" "$DEST/run_after_quit.sh"
[[ -f "$DEST/aliases.json" ]] || cp "$SRC/aliases.example.json" "$DEST/aliases.json"
cp "$SRC/skill/SKILL.md" "$SKILL_DIR/SKILL.md"

print "Installed to $DEST"
print "Type /switch in Claude Code to use it. Your organizations:"
"$DEST/switch-org.sh" list
