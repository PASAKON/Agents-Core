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
 3. copy ~/Library/LaunchAgents/com.gob.*.plist into "$B/LaunchAgents/",
    redacting any secret-looking <string> value to <redacted>
 4. defaults read com.apple.dock autohide / autohide-delay;
    com.apple.finder AppleShowAllFiles;
    defaults -currentHost read com.apple.screensaver idleTime
    -> "$B/defaults.txt"
 5. find "$CLAUDE_CONFIG_DIR" -maxdepth 2 -printf '%y %s %p\n' -> "$B/claude-tree.txt"
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

# 3. com.gob.*.plist LaunchAgents, secret-looking <string> values redacted
cp -p "$HOME"/Library/LaunchAgents/com.gob.*.plist "$B/LaunchAgents/" 2>/dev/null || true
python3 - "$B/LaunchAgents" <<'PYEOF'
import pathlib, re, sys

# A <key>NAME</key> whose name looks secret-ish, or a <string> value that
# itself looks like an opaque token, gets its <string> body replaced with
# <redacted>. Heuristic (no macOS box to validate against here) -- the Mac
# CTO should sanity-check this against the real plists on first use.
KEY_RE = re.compile(r"<key>([^<]*)</key>", re.IGNORECASE)
SECRET_KEY_RE = re.compile(r"token|secret|password|apikey|api_key|credential", re.IGNORECASE)
STRING_RE = re.compile(r"(<string>)([^<]*)(</string>)")
OPAQUE_VALUE_RE = re.compile(r"^[A-Za-z0-9+/_=\-.]{20,}$")

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

# 5. Claude Code tree (no file contents)
find "$CLAUDE_CONFIG_DIR" -maxdepth 2 -printf '%y %s %p\n' > "$B/claude-tree.txt" 2>&1 || true

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
