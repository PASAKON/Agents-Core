#!/usr/bin/env bash
# scripts/contabo_blueprint.sh — read-only capture of this Contabo VPS
# (ADR 0031, IRON §58, docs/ops/briefs/machine-contract-phase1.md item 1).
# Modeled 1:1 on windows/winbox-reinstall/rebuild/blueprint.ps1: numbered
# steps, text only, secrets excluded BY DESIGN — this script never reads
# .env*, .credentials.json, ~/.ssh/id_* (private keys), rclone.conf, or
# /home/secretary/.secretary.env. A final redaction pass (step 10) is a
# second, independent line of defense: it blanks any line anywhere in the
# capture that matches a secret-shaped pattern, even a name collision (the
# "secretary" systemd user/service literally contains the substring
# "secret") — belt-and-braces so `grep -riE 'token|secret|password|BEGIN
# .*PRIVATE'` over the output always returns nothing, matching the brief's
# own verification command exactly.
#
# Usage: bash scripts/contabo_blueprint.sh
# Writes state/contabo-blueprint-<YYYYMMDD>/ and prints its path. Idempotent
# (a same-day rerun overwrites the same dir); exits 0 even if an individual
# optional step's tool is missing (set -uo pipefail, NOT -e — every step is
# attempted and reported, matching blueprint.ps1's $ErrorActionPreference
# = 'Continue').

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE_TAG="$(date +%Y%m%d)"
B="$ROOT/state/contabo-blueprint-$DATE_TAG"
mkdir -p "$B/systemd-mooniex-units" "$B/ssh-public-keys"

# 1. apt packages explicitly installed (not pulled in as a dependency)
apt-mark showmanual > "$B/apt-packages.txt" 2>&1 || true
dpkg --print-foreign-architectures > "$B/foreign-archs.txt" 2>/dev/null || true   # e.g. i386 for wine32 — replayed before the BOM

# 2. pip freeze for the two known venvs (brief item 1: Agents/Core/.venv, /root/idm-venv)
if [ -x "$ROOT/.venv/bin/pip" ]; then
  "$ROOT/.venv/bin/pip" freeze > "$B/pip-freeze-agents-core-venv.txt" 2>&1 || true
fi
if [ -x /root/idm-venv/bin/pip ]; then
  /root/idm-venv/bin/pip freeze > "$B/pip-freeze-idm-venv.txt" 2>&1 || true
fi

# 3. npm global packages, node/npm version
npm ls -g --depth=0 > "$B/npm-global.txt" 2>&1 || true
{
  echo "node: $(node --version 2>&1)"
} > "$B/node-version.txt"

# 4. docker images, volumes (names + sizes only — never volume contents), compose files
docker images > "$B/docker-images.txt" 2>&1 || true
docker system df -v > "$B/.docker-df-v.tmp" 2>&1 || true
awk '/^Local Volumes/{f=1} /^Build cache usage/{f=0} f' "$B/.docker-df-v.tmp" > "$B/docker-volumes.txt" 2>/dev/null || true
rm -f "$B/.docker-df-v.tmp"
{
  find /opt /docker -maxdepth 6 \( \
    -iname 'docker-compose*.yml' -o -iname 'docker-compose*.yaml' \
    -o -iname 'compose.yml' -o -iname 'compose.yaml' \) 2>/dev/null
} | sort > "$B/docker-compose-files.txt"
# 4b. the compose files themselves — CONFIG that lives outside git (/docker/n8n, /opt/usage, ...):
# copied with the VALUE of any secret-looking key redacted, so the capture never carries a token.
# The .env beside each compose file is the secrets bundle's job and is never copied here.
mkdir -p "$B/compose-files"
while IFS= read -r f; do
  [ -f "$f" ] || continue
  sed -E 's/^([[:space:]]*-?[[:space:]]*[A-Za-z_]*(TOKEN|SECRET|PASSWORD|PASSWD|KEY|API|AUTH)[A-Za-z_]*[[:space:]]*[:=][[:space:]]*).+$/\1<redacted>/I' "$f" \
    > "$B/compose-files/$(printf '%s' "$f" | sed 's#^/##; s#/#__#g')"
done < "$B/docker-compose-files.txt"

# 5. systemd mooniex units — the unit files themselves (text; EnvironmentFile=
# lines point AT secret files, they never embed a secret value inline)
shopt -s nullglob
for f in /etc/systemd/system/mooniex-*.service /etc/systemd/system/mooniex-*.timer; do
  cp -p "$f" "$B/systemd-mooniex-units/" 2>/dev/null || true
done
shopt -u nullglob

# 6. root's crontab
crontab -l > "$B/crontab-root.txt" 2>&1 || echo "(no crontab)" > "$B/crontab-root.txt"

# 7. Claude Code tree (filenames/sizes only, never contents) + .claude.json
# top-level keys + projects{} map (allowedTools + hasTrustDialogAccepted only)
CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
find "$CLAUDE_CONFIG_DIR" -maxdepth 2 -printf '%y %s %p\n' > "$B/claude-tree.txt" 2>&1 || true
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

# 8. SSH: public keys + config only — never id_* private keys, never rclone.conf
cp -p "$HOME"/.ssh/*.pub "$B/ssh-public-keys/" 2>/dev/null || true
cp -p "$HOME/.ssh/config" "$B/ssh-public-keys/config" 2>/dev/null || true

# 9. machine.json — hostname, OS, kernel, python/node/docker versions, tailscale IP, disk free, users
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
            if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) >= 1000:
                users.append(parts[0])
except OSError:
    pass

info = {
    "hostname": platform.node(),
    "os": run(["bash", "-lc", '. /etc/os-release && echo "$PRETTY_NAME"']),
    "kernel": platform.release(),
    "python_version": platform.python_version(),
    "node_version": run(["node", "--version"]),
    "docker_version": run(["docker", "--version"]),
    "tailscale_ip": run(["tailscale", "ip", "-4"]),
    "disk_free_gb_root": disk_free_gb("/"),
    "users_uid_ge_1000": users,
}
print(json.dumps(info, indent=2))
PYEOF

# 10. Final safety pass — shape-aware (2026-09-24). The first version blanked any line containing
# "token|secret|password", which destroyed a package line in the pip freeze, a claude.json key line
# and the username "secretary" inside machine.json (invalid JSON, so the restore verb could not read
# the captured OS). Now: (a) a line that ASSIGNS a value to a secret-named key keeps the key and gets
# its value replaced by <redacted>; (b) a file holding private-key material is replaced whole;
# (c) list-style files whose words are NAMES, not values (package lists, machine.json, trees) are
# left alone — a name is not a secret. The brief's verification grep must be read with this in mind:
# `grep -riE 'token|secret|password'` now matches redacted KEY names, never live values.
python3 - "$B" <<'PYEOF'
import pathlib, re, sys

root = pathlib.Path(sys.argv[1])
SKIP = {"apt-packages.txt", "npm-global.txt", "node-version.txt", "docker-images.txt",
        "docker-volumes.txt", "docker-compose-files.txt", "claude-tree.txt", "machine.json",
        "foreign-archs.txt"}
assign = re.compile(
    r'^(?P<lead>\s*[-"\']?[A-Za-z0-9_.\-]*(?:token|secret|passw(?:or)?d|api[_-]?key|private[_-]?key|client[_-]?secret|access[_-]?key)[A-Za-z0-9_.\-]*["\']?\s*[:=]\s*)(?P<val>\S.*)$',
    re.IGNORECASE)
keymat = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")
redacted = []
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.name in SKIP or path.name.startswith("pip-freeze-"):
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    if keymat.search(text):
        path.write_text("[FILE REDACTED BY CAPTURE FILTER: private key material]\n", encoding="utf-8")
        redacted.append(str(path.relative_to(root)) + " (whole file)")
        continue
    changed = False
    out = []
    for line in text.splitlines(keepends=True):
        m = assign.match(line.rstrip("\n"))
        val = m.group("val").strip() if m else ""
        if m and val not in ("<redacted>", '"<redacted>"', "'<redacted>'", "''", '""'):
            quote = val[0] if val[:1] in ("'", '"') else ""
            out.append(m.group("lead") + quote + "<redacted>" + quote + ("," if val.endswith(",") else "") + "\n")
            changed = True
        else:
            out.append(line)
    if changed:
        path.write_text("".join(out), encoding="utf-8")
        redacted.append(str(path.relative_to(root)))
if redacted:
    print("contabo_blueprint.sh: redacted value(s) in: " + ", ".join(redacted), file=sys.stderr)
PYEOF

echo "$B"
exit 0
