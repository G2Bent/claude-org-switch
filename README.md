# claude-org-switch

[简体中文](README.zh-CN.md)

If your Claude account belongs to more than one organization, this moves your Claude Desktop **Code sessions** and **Code scheduled tasks** from one organization to another with a single command. A typical reason is that one organization has run out of usage and you want to keep working in another without losing your sidebar history or your scheduled tasks.

## Who it is for

- Your Claude account belongs to **two or more organizations**, and you switch between them.
- You have built up sessions in the Claude Desktop Code tab, or created Code scheduled tasks.

If you only have one organization, you do not need this.

## Why it is needed

Claude Desktop stores the Code sidebar and scheduled tasks separately for each organization:

```
~/Library/Application Support/Claude/claude-code-sessions/<account>/<org>/
  local_*.json              sidebar record for each session
  archived-sessions.idx     archived sessions
  scheduled-tasks.json      Code scheduled tasks
```

After you switch organizations, the sidebar is empty and the scheduled tasks are gone. The session transcripts (`~/.claude/projects/`) and the scheduled task prompts (`~/.claude/scheduled-tasks/`) are shared by all organizations. So once these few files are moved over, the sessions and scheduled tasks come back.

## What moves and what does not

| Item | Moves? |
|---|---|
| Code tab sidebar sessions, including archived ones | Yes |
| Code scheduled tasks | Yes. They are removed from the source organization, so they do not run twice |
| Chat conversations | No. Chat lives on claude.ai servers, separately for each organization |
| Cowork (local agent mode) sessions | Not handled |
| The organization the CLI is logged into | No. Run `claude /login` yourself |

## Install

You need macOS and `/usr/bin/python3`. If you do not have it, run `xcode-select --install` first.

```bash
git clone https://github.com/G2Bent/claude-org-switch.git
```

```bash
cd claude-org-switch && ./install.sh
```

The installer:

- puts the scripts in `~/Library/Application Support/claude-org-switch/`
- puts the `/switch` skill in `~/.claude/skills/switch/`
- lists your organizations

If you already have a different `/switch` skill, the installer stops and tells you. To replace it, run `./install.sh --force`.

## Usage

In Claude Code, type:

```
/switch
```

Or name the target organization: `/switch My Team Org` (name) or `/switch 1a2b` (uuid prefix). Claude first shows how many sessions and which scheduled tasks will move, then arms the switch.

Then **three steps are yours**:

1. Press **⌘Q** to quit Claude Desktop. The script waits until Desktop has quit before it touches any file, because a running Desktop overwrites the files from its in-memory state. About 20 seconds after the move, Desktop reopens by itself.
2. Run `claude /login` in a terminal and pick the target organization. Background sessions started from the CLI (`claude --bg`, or claude run from cron or a LaunchAgent) land in the organization the CLI is logged into, so without this they keep going to the old one.
3. Switch to the target organization in Desktop's account menu (bottom left).

You can also use it from a terminal without Claude:

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh list
```

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh <target> --dry-run
```

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh <target>
```

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh cancel
```

### Naming the organization

`list` shows each organization's uuid, session count and scheduled task count. The target can be:

- the full uuid, or a uuid prefix of at least 4 characters
- the organization name. The script learns the name of any organization the CLI has logged into.
- an alias from `aliases.json` in the script folder, written as `{"work": "<uuid>", "backup": "<uuid>"}`

In `list`, `*` marks the organization the CLI is logged into. With exactly two organizations, a bare `/switch` goes to the other one.

## Safety

- **Format check first.** Before touching anything, the script checks every session record, the archive index and the scheduled tasks. If they do not look like what it knows (for example after a Desktop update changed the format), it exits with code 3 and changes nothing.
- **Never while Desktop runs.** If Desktop is running, or the script cannot tell, it does not run.
- **Backup first.** Each switch first packs the whole `claude-code-sessions` folder into `backup-<time>.tgz`, keeping the 5 newest.
- **Records.** Each switch writes `manifest-<time>.json` listing the files it moved. The log is `run.log`.
- **Local files only.** No network access and no credentials. From `~/.claude.json` it reads only `oauthAccount.organizationUuid` and `organizationName`.
- **Gives up on timeout.** If Desktop is not quit within 2 hours of arming, the switch is dropped.

## Undo

Quit Desktop, then run the command below. It renames the current folder to keep it, then unpacks the latest backup:

```bash
cd ~/Library/Application\ Support/Claude && mv claude-code-sessions "claude-code-sessions.undo-$(date +%Y%m%d-%H%M%S)" && tar -xzf "$(ls -t ~/Library/Application\ Support/claude-org-switch/backup-*.tgz | head -1)"
```

Once your sessions are back, you can delete `claude-code-sessions.undo-*`.

## Uninstall

```bash
~/Library/Application\ Support/claude-org-switch/switch-org.sh cancel; rm -rf ~/Library/Application\ Support/claude-org-switch ~/.claude/skills/switch
```

## Limits

- It relies on Claude Desktop's internal storage layout, which is not documented. An app update may change it. The script then refuses to run instead of writing bad data, and needs an update.
- It moves only between organizations of the same Claude account, not between accounts.
- Do not use unvetted third-party packages such as `npx claude-transplant` for this.
