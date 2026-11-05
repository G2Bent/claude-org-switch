#!/usr/bin/env python3
"""Move Claude Desktop Code sessions and scheduled tasks between organizations
of one Claude account.

Claude Desktop keeps the Code tab sidebar and Code scheduled tasks per
organization, under
  ~/Library/Application Support/Claude/claude-code-sessions/<account>/<org>/
This script moves every session record, archived-index entry and scheduled
task from the other organization folders of the same account into the target
organization folder. When a record exists in both, the copy with the newer
lastActivityAt ends up in the target.

Commands:
  switch_org.py list                 show organizations and which one the CLI is on
  switch_org.py resolve <target>     print the organization uuid for <target>
  switch_org.py plan <target>        show what would move (changes nothing)
  switch_org.py apply <target>       move it (Claude Desktop must be closed)

<target> is a full organization uuid, a unique uuid prefix (4+ characters),
an alias from aliases.json next to this script, or an organization name the
CLI has been logged into before (learned automatically).

Exit codes: 0 ok, 2 usage / unknown target, 3 storage format not recognized
(nothing changed), 4 Claude Desktop is running (nothing changed).
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

BASE = os.path.expanduser("~/Library/Application Support/Claude/claude-code-sessions")
WORK = os.path.dirname(os.path.abspath(__file__))
ALIASES = os.path.join(WORK, "aliases.json")
KNOWN = os.path.join(WORK, "known-orgs.json")
CLI_CONFIG = os.path.expanduser("~/.claude.json")
IDX = "archived-sessions.idx"
TASKS = "scheduled-tasks.json"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class FormatError(Exception):
    pass


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(path, data):
    tmp = path + ".tmp-switch"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


# ---------- discovery ----------

def accounts():
    if not os.path.isdir(BASE):
        return []
    return sorted(a for a in os.listdir(BASE)
                  if UUID_RE.match(a) and os.path.isdir(os.path.join(BASE, a)))


def orgs_of(account):
    path = os.path.join(BASE, account)
    return sorted(o for o in os.listdir(path)
                  if UUID_RE.match(o) and os.path.isdir(os.path.join(path, o)))


def cli_org():
    """Return (uuid, name) of the organization the CLI is logged into.

    Reads only oauthAccount.organizationUuid / organizationName.
    """
    acct = load(CLI_CONFIG, {}).get("oauthAccount") or {}
    return acct.get("organizationUuid"), acct.get("organizationName")


def known_names():
    names = load(KNOWN, {})
    uuid, name = cli_org()
    if uuid and name and names.get(uuid) != name:
        names[uuid] = name
        save(KNOWN, names)
    return names


def resolve(target):
    """Return (account, org_uuid) for a target string, or exit 2."""
    target = target.strip()
    names = known_names()
    aliases = load(ALIASES, {})
    pairs = [(a, o) for a in accounts() for o in orgs_of(a)]

    if target in aliases:
        target = aliases[target]
    lowered = target.lower()
    by_name = [u for u, n in names.items() if n.lower() == lowered]
    if len(by_name) == 1:
        target = by_name[0]
        lowered = target.lower()

    if UUID_RE.match(lowered):
        hits = [(a, o) for a, o in pairs if o == lowered]
        if not hits and len(accounts()) == 1:
            # The org folder does not exist yet (Desktop never opened it).
            return accounts()[0], lowered
    elif len(lowered) >= 4 and re.match(r"^[0-9a-f-]+$", lowered):
        hits = [(a, o) for a, o in pairs if o.startswith(lowered)]
    else:
        hits = []

    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        print(f"'{target}' matches several organizations; use the full uuid. Run list to see them.", file=sys.stderr)
        sys.exit(2)
    print(f"No organization '{target}'. Run list to see the available ones.", file=sys.stderr)
    sys.exit(2)


# ---------- validation ----------

def validate(org_dir):
    """Raise FormatError when the folder does not look like what this script knows."""
    problems = []
    for path in glob.glob(os.path.join(org_dir, "local_*.json")):
        name = os.path.basename(path)
        try:
            rec = load(path, None)
        except ValueError:
            problems.append(f"{name}: not valid JSON")
            continue
        if not isinstance(rec, dict):
            problems.append(f"{name}: not a JSON object")
        elif rec.get("sessionId") != name[:-5]:
            problems.append(f"{name}: sessionId does not match the file name")
        elif not isinstance(rec.get("lastActivityAt"), int):
            problems.append(f"{name}: lastActivityAt is not an integer")
        if len(problems) >= 5:
            break

    idx = load(os.path.join(org_dir, IDX), {"v": 1, "archived": []})
    if not (isinstance(idx, dict) and idx.get("v") == 1 and isinstance(idx.get("archived"), list)):
        problems.append(f"{IDX}: not shaped like {{v: 1, archived: [...]}}")

    tasks = load(os.path.join(org_dir, TASKS), {"scheduledTasks": []})
    if not (isinstance(tasks, dict) and isinstance(tasks.get("scheduledTasks"), list)
            and all(isinstance(t, dict) and isinstance(t.get("id"), str)
                    for t in tasks["scheduledTasks"])):
        problems.append(f"{TASKS}: not shaped like {{scheduledTasks: [{{id, ...}}]}}")

    if problems:
        raise FormatError(org_dir + "\n  " + "\n  ".join(problems))


def desktop_running():
    try:
        out = subprocess.run(["osascript", "-e", 'application "Claude" is running'],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return True  # cannot tell: treat as running
    return out != "false"


# ---------- plan / apply ----------

def activity(path):
    return load(path, {}).get("lastActivityAt") or 0


def plan_one(src, dst):
    dst_names = set(os.listdir(dst)) if os.path.isdir(dst) else set()
    move, overwrite = [], []
    for path in sorted(glob.glob(os.path.join(src, "local_*.json"))):
        name = os.path.basename(path)
        if name not in dst_names:
            move.append(name)
        elif activity(path) > activity(os.path.join(dst, name)):
            overwrite.append(name)
    src_tasks = load(os.path.join(src, TASKS), {}).get("scheduledTasks", [])
    return move, overwrite, src_tasks


def apply_one(src, dst, move, overwrite, src_tasks):
    for name in overwrite:
        os.replace(os.path.join(src, name), os.path.join(dst, name))
    for name in move:
        os.rename(os.path.join(src, name), os.path.join(dst, name))

    carried = {n[:-5] for n in move + overwrite}
    src_idx = load(os.path.join(src, IDX), {"v": 1, "archived": []})
    dst_idx = load(os.path.join(dst, IDX), {"v": 1, "archived": []})
    have = set(dst_idx["archived"])
    dst_idx["archived"] += [a for a in src_idx["archived"] if a in carried and a not in have]
    src_idx["archived"] = [a for a in src_idx["archived"] if a not in carried]
    save(os.path.join(dst, IDX), dst_idx)
    save(os.path.join(src, IDX), src_idx)

    if src_tasks:
        dst_doc = load(os.path.join(dst, TASKS), {"scheduledTasks": []})
        incoming = {t["id"] for t in src_tasks}
        dst_doc["scheduledTasks"] = [t for t in dst_doc["scheduledTasks"]
                                     if t["id"] not in incoming] + src_tasks
        save(os.path.join(dst, TASKS), dst_doc)
        src_doc = load(os.path.join(src, TASKS), {})
        src_doc["scheduledTasks"] = []
        save(os.path.join(src, TASKS), src_doc)


def label(uuid, names):
    return f"{names[uuid]} ({uuid[:8]})" if uuid in names else uuid


def run(target, do_apply):
    account, dst_uuid = resolve(target)
    names = known_names()
    acct_dir = os.path.join(BASE, account)
    dst = os.path.join(acct_dir, dst_uuid)
    sources = [o for o in orgs_of(account) if o != dst_uuid]

    try:
        for o in sources + ([dst_uuid] if os.path.isdir(dst) else []):
            validate(os.path.join(acct_dir, o))
    except FormatError as e:
        print("Claude Desktop storage does not look like what this script knows; "
              "an app update may have changed it. Nothing was changed.\n" + str(e), file=sys.stderr)
        sys.exit(3)

    if do_apply and desktop_running():
        print("Claude Desktop is running (or its state is unknown). Nothing was changed. Quit it with ⌘Q first.", file=sys.stderr)
        sys.exit(4)

    manifest = {"account": account, "dst": dst_uuid, "sources": {}}
    total = 0
    for src_uuid in sources:
        src = os.path.join(acct_dir, src_uuid)
        move, overwrite, src_tasks = plan_one(src, dst)
        total += len(move) + len(overwrite) + len(src_tasks)
        print(f"{label(src_uuid, names)} -> {label(dst_uuid, names)}: "
              f"move={len(move)} overwrite={len(overwrite)} "
              f"tasks={[t['id'] for t in src_tasks]}")
        if do_apply:
            os.makedirs(dst, exist_ok=True)
            apply_one(src, dst, move, overwrite, src_tasks)
            manifest["sources"][src_uuid] = {"moved": move, "overwritten": overwrite,
                                             "tasks": [t["id"] for t in src_tasks]}
    if not sources:
        print("This account has only one organization folder; nothing to move.")
    elif total == 0:
        print("Nothing to move: sessions and scheduled tasks are already in the target organization.")
    if do_apply:
        path = os.path.join(WORK, f"manifest-{time.strftime('%Y%m%d-%H%M%S')}.json")
        with open(path, "w") as f:
            json.dump(manifest, f, indent=1)
        print("manifest=" + path)


def cmd_list():
    names = known_names()
    current, _ = cli_org()
    accts = accounts()
    if not accts:
        print("Claude Desktop Code session folder not found: " + BASE)
        return
    aliases = load(ALIASES, {})
    rev = {v: k for k, v in aliases.items()}
    for a in accts:
        print(f"account {a}")
        for o in orgs_of(a):
            d = os.path.join(BASE, a, o)
            n = len(glob.glob(os.path.join(d, "local_*.json")))
            t = len(load(os.path.join(d, TASKS), {}).get("scheduledTasks", []))
            mark = "*" if o == current else " "
            extra = "  ".join(x for x in [names.get(o, ""), f"alias={rev[o]}" if o in rev else ""] if x)
            print(f" {mark} {o}  sessions={n} tasks={t}  {extra}".rstrip())
    print("* = organization the CLI is logged into. Names appear once the CLI has logged into that organization.")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 2)
    cmd = args[0]
    if cmd == "list":
        cmd_list()
    elif cmd in ("resolve", "plan", "apply") and len(args) == 2:
        if cmd == "resolve":
            print(resolve(args[1])[1])
        else:
            run(args[1], do_apply=(cmd == "apply"))
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
