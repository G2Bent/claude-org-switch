---
name: switch
description: Move Claude Desktop Code sessions and Code scheduled tasks to another organization of the same Claude account (claude-org-switch), typically when one organization has run out of usage. Triggers - /switch, /switch <org>, switch org, move to my other organization, this org is out of tokens. Does not handle Chat conversations (they live on claude.ai servers and cannot be moved).
argument-hint: "[org name | alias | uuid prefix]"
---

# Switch Claude organization

Script: `~/Library/Application Support/claude-org-switch/switch-org.sh` (logic in `switch_org.py` in the same folder).

## Steps

1. **List organizations.** Run `switch-org.sh list`. `*` marks the organization the CLI is logged into. Each line shows the session count, the scheduled task count, and a known name or alias.
2. **Pick the target.**
   - If there is an argument, use it. It can be an organization name, an alias from `aliases.json`, a uuid, or a uuid prefix.
   - With no argument and exactly two organizations, the target is the one without `*`.
   - With more than two organizations, show the list and ask the user to pick one.
3. **Show the plan.** Run `switch-org.sh <target> --dry-run` and tell the user in a sentence or two how many sessions and which scheduled tasks will move.
   - If it says there is nothing to move, the user is already in the target organization. Tell them only the login and Desktop steps in step 5 are needed, and stop.
   - If it exits with code 3, Desktop's storage format has changed. Show the user the output and stop. Do not edit the files yourself.
4. **Arm the switch.** The user typing `/switch` is the go-ahead, so run `switch-org.sh <target>` directly. launchctl does not work inside the Claude Code sandbox, so run it with the sandbox disabled. If it says a switch is already waiting, tell the user `switch-org.sh cancel` clears it, and ask whether to cancel and re-arm.
5. **Tell the user the three steps only they can do:**
   - Press ⌘Q in Claude Desktop. This conversation disconnects; Desktop reopens by itself in about 20 seconds with a notification.
   - Run `claude /login` in a terminal and pick the target organization. Background sessions started from the CLI (`claude --bg`, claude run from cron) land in the organization the CLI is logged into.
   - Switch to the target organization in Desktop's account menu (bottom left).

## When something goes wrong

- The log is `run.log` in the script folder. If Desktop is not quit within 2 hours, the script gives up and changes nothing.
- To undo, have the user quit Desktop and follow the "Undo" section of the README. It renames `claude-code-sessions` aside first, then unpacks the latest `backup-*.tgz`. Never unpack over the existing folder: files already moved into the target organization would stay there and exist on both sides.
- Do not use unvetted third-party packages such as `npx claude-transplant`.
