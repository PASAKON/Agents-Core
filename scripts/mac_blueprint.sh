#!/usr/bin/env bash
# scripts/mac_blueprint.sh — read-only capture of the Mac (ADR 0031, IRON §58,
# docs/ops/briefs/machine-contract-phase1.md item 2). Written on Contabo,
# where there is no macOS to test against — run for real only on the Mac, by
# the Mac CTO (config/machine-contract.yaml machines.mac.run_by). Text only,
# secrets excluded by design: never reads .env*, .credentials.json,
# ~/.ssh/id_* (private keys), or any keychain item.
#
# Usage:
#   bash scripts/mac_blueprint.sh              # real capture — Mac only, Mac CTO only
#   bash scripts/mac_blueprint.sh --dry-run     # print the plan; touches nothing;
#                                                # safe on any box (this is what
#                                                # Contabo's own verification runs)
#
# Refuses a real (non---dry-run) run anywhere that is not Darwin, so a stray
# invocation on Contabo/winbox cannot half-execute Darwin-only commands
# (brew/launchctl/defaults) that do not exist there.

set -uo pipefail

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

if [ "$DRY_RUN" -eq 0 ] && [ "$(uname -s)" != "Darwin" ]; then
  echo "mac_blueprint.sh: refusing -- this is not macOS (uname -s = $(uname -s))." >&2
  echo "Run this only on the Mac (as the Mac CTO), or pass --dry-run to preview it anywhere." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE_TAG="$(date +%Y%m%d)"
B="$ROOT/state/mac-blueprint-$DATE_TAG"
CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

if [ "$DRY_RUN" -eq 1 ]; then
  cat <<PLAN
mac_blueprint.sh --dry-run -- nothing executed. On the Mac this would write
$B/ with:

 1. brew bundle dump --force --file="$B/Brewfile"
 2. launchctl list | grep -v com.apple > "$B/launchctl-list.txt"
 3. copy ~/Library/LaunchAgents/com.gob.*.plist + com.mooniex.*.plist into
    "$B/LaunchAgents/", redacting any secret-looking <string> value to <redacted>
 4. defaults read com.apple.dock autohide / autohide-delay;
    com.apple.finder AppleShowAllFiles;
    defaults -currentHost read com.apple.screensaver idleTime
    -> "$B/defaults.txt"
 5. walk "$CLAUDE_CONFIG_DIR" to depth 2 (type, size, path, link target) -> "$B/claude-tree.txt"
 5b. repos.tsv (every git repo under ~/MoonieXHQ + ~/Developer, with remotes), links.tsv
    (~/.claude/projects/*/memory + ~/Projects/* symlinks), claude-plugins/*.json, npm-globals.txt
 6. ~/.claude.json top-level keys + projects{} (allowedTools,
    hasTrustDialogAccepted only, same shape as contabo_blueprint.sh)
    -> "$B/claude-json-keys.txt"
 7. copy ~/.ssh/*.pub + ~/.ssh/config -> "$B/ssh-public-keys/"
 8. machine.json (hostname, OS via sw_vers, kernel, python/node versions,
    tailscale IP, disk free, users)
 9. final redaction pass over every file written above (same secret-shaped
    pattern as the verification grep), belt-and-braces

Output dir would be: $B
PLAN
  exit 0
fi

mkdir -p "$B/LaunchAgents" "$B/ssh-public-keys"

# 1. brew bundle (formulae + casks)
brew bundle dump --force --file="$B/Brewfile" > "$B/.brew-bundle.log" 2>&1 || true
rm -f "$B/.brew-bundle.log"

# 2. launchctl list, excluding Apple's own
launchctl list 2>/dev/null | grep -v com.apple > "$B/launchctl-list.txt" || true

# 3. org LaunchAgents (com.gob.* AND com.mooniex.* -- the org daemons are com.mooniex.*;
# the first real run on 2026-09-25 captured only the one com.gob plist and missed all 8),
# secret-looking <string> values redacted
cp -p "$HOME"/Library/LaunchAgents/com.gob.*.plist "$B/LaunchAgents/" 2>/dev/null || true
cp -p "$HOME"/Library/LaunchAgents/com.mooniex.*.plist "$B/LaunchAgents/" 2>/dev/null || true
python3 - "$B/LaunchAgents" <<'PYEOF'
import pathlib, re, sys

# A <key>NAME</key> whose name looks secret-ish, or a <string> value that
# itself looks like an opaque token, gets its <string> body replaced with
# <redacted>. Heuristic (no macOS box to validate against here) -- the Mac
# CTO should sanity-check this against the real plists on first use.
KEY_RE = re.compile(r"<key>([^<]*)</key>", re.IGNORECASE)
SECRET_KEY_RE = re.compile(r"token|secret|password|apikey|api_key|credential", re.IGNORECASE)
STRING_RE = re.compile(r"(<string>)([^<]*)(</string>)")
# No '/' or '.': with them, every absolute path and reverse-DNS Label looked "opaque" and the
# first real run redacted Label/WorkingDirectory/StandardOutPath in all 8 com.mooniex plists.
# Secrets under a secret-named <key> are still caught by SECRET_KEY_RE above.
OPAQUE_VALUE_RE = re.compile(r"^[A-Za-z0-9+_=\-]{24,}$")

root = pathlib.Path(sys.argv[1])
for path in sorted(root.glob("*.plist")):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    out = []
    pending_secret_key = False
    for line in lines:
        km = KEY_RE.search(line)
        if km:
            pending_secret_key = bool(SECRET_KEY_RE.search(km.group(1)))
            out.append(line)
            continue
        sm = STRING_RE.search(line)
        if sm and (pending_secret_key or OPAQUE_VALUE_RE.match(sm.group(2))):
            line = STRING_RE.sub(r"\1<redacted>\3", line)
            pending_secret_key = False
        out.append(line)
    path.write_text("".join(out), encoding="utf-8")
PYEOF

# 4. defaults read -- dock/finder autohide + screen (screensaver idle) settings only
{
  echo "com.apple.dock autohide: $(defaults read com.apple.dock autohide 2>&1)"
  echo "com.apple.dock autohide-delay: $(defaults read com.apple.dock autohide-delay 2>&1)"
  echo "com.apple.finder AppleShowAllFiles: $(defaults read com.apple.finder AppleShowAllFiles 2>&1)"
  echo "com.apple.screensaver idleTime: $(defaults -currentHost read com.apple.screensaver idleTime 2>&1)"
} > "$B/defaults.txt"

# 5. Claude Code tree (no file contents). BSD find has no -printf (the first real run wrote a
# one-line error here), so walk it in Python: "<type> <size> <path>[ -> <link target>]".
python3 - "$CLAUDE_CONFIG_DIR" > "$B/claude-tree.txt" <<'PYEOF'
import os, sys
root = sys.argv[1]
for dp, dn, fn in os.walk(root):
    depth = dp[len(root):].count(os.sep)
    if depth >= 2:
        dn[:] = []
    for name in sorted(dn) + sorted(fn):
        p = os.path.join(dp, name)
        if os.path.islink(p):
            print(f"l 0 {p} -> {os.readlink(p)}")
        elif os.path.isdir(p):
            print(f"d 0 {p}")
        else:
            try:
                print(f"f {os.path.getsize(p)} {p}")
            except OSError:
                print(f"f ? {p}")
PYEOF

# 5b. What a fresh Mac must re-clone and re-link (added 2026-09-25, first real wipe prep):
#   repos.tsv          every git repo under ~/MoonieXHQ and ~/Developer: path, branch, each remote + url
#   links.tsv          symlinks that tie the org together: ~/.claude/projects/*/memory, ~/Projects/*
#   claude-plugins/    installed_plugins.json + known_marketplaces.json (plugin names, no secrets)
#   npm-globals.txt    `npm ls -g --depth=0`
python3 - "$HOME" "$B" <<'PYEOF'
import os, subprocess, sys
home, out = sys.argv[1], sys.argv[2]
SKIP = {"node_modules", ".venv", "venv", "worktrees", ".next", "__pycache__", ".git"}
rows = []
for top in (os.path.join(home, "MoonieXHQ"), os.path.join(home, "Developer")):
    for dp, dn, fn in os.walk(top):
        if os.path.isdir(os.path.join(dp, ".git")):  # a real clone (worktrees have a .git FILE)
            rel = os.path.relpath(dp, home)
            git = lambda *a: subprocess.run(["git", "-C", dp, *a], capture_output=True, text=True).stdout.strip()
            branch = git("rev-parse", "--abbrev-ref", "HEAD")
            remotes = git("remote").split()
            # origin first: mac_restore.sh clones from the first row of a path, adds the rest as remotes
            for r in sorted(remotes, key=lambda x: (x != "origin", x)) or [""]:
                rows.append((rel, r != "origin", f"{rel}\t{branch}\t{r}\t{git('remote', 'get-url', r) if r else ''}"))
        dn[:] = [d for d in dn if d not in SKIP and not os.path.islink(os.path.join(dp, d))]
        if dp.count(os.sep) - top.count(os.sep) >= 4:
            dn[:] = []
rows.sort(key=lambda t: (t[0], t[1]))  # stable: origin row stays first within each path
open(os.path.join(out, "repos.tsv"), "w").write("path\tbranch\tremote\turl\n" + "\n".join(t[2] for t in rows) + "\n")
links = []
pj = os.path.join(home, ".claude", "projects")
for slug in sorted(os.listdir(pj)) if os.path.isdir(pj) else []:
    m = os.path.join(pj, slug, "memory")
    if os.path.islink(m):
        links.append(f"{os.path.relpath(m, home)}\t{os.readlink(m)}")
hub = os.path.join(home, "Projects")
for name in sorted(os.listdir(hub)) if os.path.isdir(hub) else []:
    p = os.path.join(hub, name)
    if os.path.islink(p):
        links.append(f"{os.path.relpath(p, home)}\t{os.readlink(p)}")
open(os.path.join(out, "links.tsv"), "w").write("link\ttarget\n" + "\n".join(links) + "\n")
PYEOF
mkdir -p "$B/claude-plugins"
cp -p "$CLAUDE_CONFIG_DIR/plugins/installed_plugins.json" "$CLAUDE_CONFIG_DIR/plugins/known_marketplaces.json" "$B/claude-plugins/" 2>/dev/null || true
npm ls -g --depth=0 > "$B/npm-globals.txt" 2>/dev/null || true

# 6. .claude.json top-level keys + projects{} map (allowedTools, hasTrustDialogAccepted only)
python3 - "$HOME/.claude.json" > "$B/claude-json-keys.txt" <<'PYEOF'
import json, sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, json.JSONDecodeError) as e:
    print(f"(unreadable: {e})")
    sys.exit(0)

print("top-level keys:")
for k in sorted(data.keys()):
    print(f"  {k}")
print()
print("projects{} (path, allowedTools, hasTrustDialogAccepted):")
for p, v in sorted((data.get("projects") or {}).items()):
    v = v or {}
    print(f"  {p}\tallowedTools={v.get('allowedTools')}\thasTrustDialogAccepted={v.get('hasTrustDialogAccepted')}")
PYEOF

# 7. SSH public keys + config only -- never id_* private keys
cp -p "$HOME"/.ssh/*.pub "$B/ssh-public-keys/" 2>/dev/null || true
cp -p "$HOME/.ssh/config" "$B/ssh-public-keys/config" 2>/dev/null || true

# 8. machine.json
python3 - > "$B/machine.json" <<'PYEOF'
import json, platform, shutil, subprocess


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (r.stdout or r.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return f"(error: {e})"


def disk_free_gb(path="/"):
    try:
        du = shutil.disk_usage(path)
        return round(du.free / (1024 ** 3), 1)
    except OSError:
        return None


users = []
try:
    with open("/etc/passwd", encoding="utf-8") as fh:
        for line in fh:
            parts = line.split(":")
            if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) >= 500:
                users.append(parts[0])
except OSError:
    pass

info = {
    "hostname": platform.node(),
    "os": run(["sw_vers", "-productVersion"]),
    "build": run(["sw_vers", "-buildVersion"]),
    "kernel": platform.release(),
    "python_version": platform.python_version(),
    "node_version": run(["node", "--version"]),
    "tailscale_ip": run(["tailscale", "ip", "-4"]),
    "disk_free_gb_root": disk_free_gb("/"),
    "users_uid_ge_500": users,
}
print(json.dumps(info, indent=2))
PYEOF

# 9. Final safety pass: redact any line anywhere in the capture that matches
# a secret-shaped pattern -- same pattern the verification grep uses, and the
# same belt-and-braces idiom as scripts/contabo_blueprint.sh step 10.
python3 - "$B" <<'PYEOF'
import pathlib, re, sys

root = pathlib.Path(sys.argv[1])
pattern = re.compile(r"token|secret|password|BEGIN .*PRIVATE", re.IGNORECASE)
redacted = []
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    changed = False
    out_lines = []
    for line in text.splitlines(keepends=True):
        if pattern.search(line):
            out_lines.append("[LINE REDACTED BY CAPTURE FILTER]\n")
            changed = True
        else:
            out_lines.append(line)
    if changed:
        path.write_text("".join(out_lines), encoding="utf-8")
        redacted.append(str(path.relative_to(root)))
if redacted:
    print("mac_blueprint.sh: redacted line(s) in: " + ", ".join(redacted), file=sys.stderr)
PYEOF

echo "$B"
exit 0
