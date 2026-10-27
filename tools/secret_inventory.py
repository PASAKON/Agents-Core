#!/usr/bin/env python3
"""Names-only inventory of every credential the org holds (HQSecurity M0, task-0a7c9dcc).

Read-only on every host and provider. It never prints, logs or writes a secret VALUE, not even a
prefix: a row carries the variable NAME, where it sits (host:path:line, Infisical project/env, or
a GitHub repo secret / deploy key) and `sha256(value)[:12]`, the way PLAN.md §1 measured Contabo
(docs/design/secrets-infisical/PLAN.md). The hash exists only for "same value in two places" and
"dead copy" detection; the report withholds it for low-entropy values (see WEAK_*).

    scan-local [--root DIR ..] [--host NAME]   Walk this machine's credential files; print JSON
                                               rows on stdout. Stdlib only, so the same file runs
                                               on Contabo, winbox (piped over ssh) and the Mac.
    scan-winbox                                Pipe this file to `ssh winbox python -` and run
                                               scan-local there; the hashing happens on winbox.
    github [--owner PASAKON]                   Actions secret names, deploy keys and the secret
                                               scanning / push protection state per repo (gh).
    infisical [--as contabo]                   Secret names + metadata per project/env, read with
                                               this machine's existing identity
                                               (tools/infisical_setup.py, no new identity).
    report --in A.json [--in B.json ..] --out PATH.md
                                               Merge the JSON from the steps above into one
                                               table (+ PATH.json). Names, places and hashes only.

Never opened, on any host: /etc/infisical, /proc, /run/sompong-coo, the Windows Infisical
credential folders (DENY_*). A value is hashed the moment it is parsed and then dropped.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

# --- what counts as a credential ------------------------------------------------------------

DENY_POSIX = ("/etc/infisical", "/proc", "/sys", "/run/sompong-coo", "/dev")
DENY_NT_SUFFIXES = (r"\programdata\infisical", r"\appdata\local\mooniex\infisical")
SKIP_DIRS = {"node_modules", ".venv", "venv", ".git", "__pycache__", "site-packages", ".cache",
             ".npm", ".pnpm-store", ".next", ".tox", ".mypy_cache", ".pytest_cache", "dist-packages"}
NT_SKIP_DIRS = {"AppData", "Application Data", "Local Settings", "Cookies", "NetHood", "PrintHood",
                "Recent", "SendTo", "Start Menu", "Templates", "My Documents", "Saved Games"}
MAX_BYTES = 2 * 1024 * 1024

FILE_GLOBS = (".env", ".env.*", "*.env", "*.env.*", "settings*.json", "config*.json", "config*.yaml",
              "config*.yml", "config*.toml", "credentials*", ".credentials*", "*.pem", "*.key",
              "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa")
EXTRA_NAMES = {".git-credentials", ".netrc", "_netrc", ".pgpass", ".npmrc", ".pypirc", "rclone.conf",
               "hosts.yml", "token.json"}
KEY_FILE_GLOBS = ("*.pem", "*.key", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa")

SECRET_NAME_RE = re.compile(
    r"(api[_-]?key|apikey|token|secret(?!ary)|passw|pwd|credential|private[_-]?key|privatekey|dsn|cookie|"
    r"webhook|signing|client[_-]?secret|access[_-]?key|auth[_-]?key|_pat$|^pat$|_key$|^key$)", re.I)
NOT_SECRET_NAME_RE = re.compile(
    r"(_path|_file|_dir|_ttl|_enabled|_uri|_url|_host|_bin|_workdir|_config|_mode|_expires(_at)?|_expiry|_id_?$|_header|_name|_type|_url_env|"
    r"_length|_len|_count|_max|_min|_timeout|_seconds|_version|_prefix|_suffix|_field|_env)$|"
    r"^(token_?type|key_?id|max_?tokens?|tokens?|num_?tokens?|tokenizer.*|.*_tokens)$", re.I)
URL_WITH_PASSWORD_RE = re.compile(r"^[a-z][a-z0-9+.-]*://[^:/@\s]+:[^@\s]+@", re.I)
PLACEHOLDER_RE = re.compile(
    r"^(|x+|\*+|\.+|-+|<.*>|\$\{.*\}|\$[A-Z_][A-Z0-9_]*|%[A-Z_]+%|true|false|yes|no|none|null|nil|"
    r"todo|tbd|changeme|change[_-]?me|secret|password|token|your[_-].*|.*(fake|dummy|example|placeholder|"
    r"redacted|replace[_-]?me|xxxx).*)$", re.I)
MIN_VALUE_LEN = 6
# A value an attacker could guess from a word list: its hash12 in a PUBLIC report would confirm the
# guess. The report shows a same-value group label instead (w1, w2 ...) — the dedup stays visible.
WEAK_NAME_RE = re.compile(r"(passw|pwd|pin$|passphrase)", re.I)
WEAK_MAX_LEN = 19

ENV_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*(.*?)\s*$")
JSON_PAIR_RE = re.compile(r'"([A-Za-z_][A-Za-z0-9_.-]*)"\s*:\s*"((?:[^"\\]|\\.)*)"')
YAML_LINE_RE = re.compile(r"""^\s*-?\s*["']?([A-Za-z_][A-Za-z0-9_.-]*)["']?\s*:\s+(.+?)\s*$""")
TOML_LINE_RE = re.compile(r"""^\s*["']?([A-Za-z_][A-Za-z0-9_.-]*)["']?\s*=\s*(.+?)\s*$""")
INI_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*[=:]\s*(.+?)\s*$")
INLINE_ASSIGN_RE = re.compile(r"\b([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PAT))=([^\s\"'\\),;]+)")
# Token shapes worth a row even without a name (a permission rule in settings.local.json held two
# Supabase PATs on 2026-10-02). The row names the provider, never the literal prefix.
TOKEN_SHAPES = (
    ("SUPABASE_PAT(inline)", re.compile(r"\bsbp_[A-Za-z0-9]{20,}")),
    ("GITHUB_TOKEN(inline)", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("ANTHROPIC_KEY(inline)", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OPENAI_STYLE_KEY(inline)", re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{20,}")),
    ("AWS_ACCESS_KEY(inline)", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GOOGLE_API_KEY(inline)", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}")),
    ("SLACK_TOKEN(inline)", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
)


def hash12(value: str | bytes) -> str:
    data = value.encode("utf-8", "surrogateescape") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()[:12]


def is_secret_name(name: str) -> bool:
    leaf = name.rsplit(".", 1)[-1]
    return bool(SECRET_NAME_RE.search(leaf)) and not NOT_SECRET_NAME_RE.search(leaf)


def clean_value(raw: str) -> str:
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if " #" in v:   # an unquoted inline comment
        v = v.split(" #", 1)[0].rstrip()
    return v.rstrip(",")


def is_placeholder(value: str) -> bool:
    return len(value) < MIN_VALUE_LEN or bool(PLACEHOLDER_RE.match(value))


def is_weak(name: str, value: str) -> bool:
    return len(value) <= WEAK_MAX_LEN or bool(WEAK_NAME_RE.search(name))


def _row(name: str, value: str, line: int, kind: str) -> dict:
    return {"name": name, "line": line, "kind": kind, "hash12": hash12(value),
            "weak": is_weak(name, value)}


def file_kind(basename: str) -> str | None:
    low = basename.lower()
    if low in EXTRA_NAMES:
        return "extra"
    for g in FILE_GLOBS:
        if fnmatch.fnmatch(low, g):
            return "keyfile" if any(fnmatch.fnmatch(low, k) for k in KEY_FILE_GLOBS) else "text"
    return None


def parse_text(text: str, basename: str) -> list[dict]:
    """Rows for every credential-looking assignment in a config/env file. Values are hashed here
    and never leave this function."""
    low = basename.lower()
    if low.endswith(".json") or low in {"token.json"}:
        style = "json"
    elif low.endswith((".yaml", ".yml")):
        style = "yaml"
    elif low.endswith(".toml"):
        style = "toml"
    elif low.startswith(".env") or low.endswith(".env") or ".env." in low:
        style = "env"
    else:
        style = "ini"
    rows: list[dict] = []
    seen: set[tuple] = set()

    def add(name, value, ln, kind):
        key = (name, ln, kind)
        h = (ln, hash12(value))
        if key in seen or is_placeholder(value) or (kind in ("inline", "shape") and h in seen):
            return
        seen.update((key, h))
        rows.append(_row(name, value, ln, kind))

    for ln, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", ";")):
            continue
        if style == "json":
            for m in JSON_PAIR_RE.finditer(line):
                name, value = m.group(1), m.group(2)
                if is_secret_name(name) or URL_WITH_PASSWORD_RE.match(value):
                    add(name, value, ln, "json")
        else:
            m = {"env": ENV_LINE_RE, "yaml": YAML_LINE_RE, "toml": TOML_LINE_RE,
                 "ini": INI_LINE_RE}[style].match(line)
            if m:
                name, value = m.group(1), clean_value(m.group(2))
                if is_secret_name(name) or URL_WITH_PASSWORD_RE.match(value):
                    add(name, value, ln, style)
                    continue
        for m in INLINE_ASSIGN_RE.finditer(line):
            add(m.group(1) + "(inline)", m.group(2), ln, "inline")
        for label, rx in TOKEN_SHAPES:
            for m in rx.finditer(line):
                add(label, m.group(0), ln, "shape")
    return rows


def keyfile_row(data: bytes, basename: str) -> dict | None:
    """One row per private key file (public certificates are not credentials)."""
    if b"PRIVATE KEY" not in data and not basename.lower().startswith("id_"):
        return None
    if basename.lower().endswith(".pub"):
        return None
    return {"name": basename, "line": 0, "kind": "keyfile", "hash12": hash12(data), "weak": False}


def denied(path: str) -> bool:
    if os.name == "nt":
        low = os.path.normcase(os.path.abspath(path)).rstrip("\\")
        return any((s + "\\") in (low + "\\") for s in DENY_NT_SUFFIXES)
    real = os.path.realpath(path)
    return any(real == d or real.startswith(d + "/") for d in DENY_POSIX)


def default_roots() -> list[str]:
    if os.name == "nt":
        home = os.path.expanduser("~")
        # the whole profile (project folders sit straight under it: cookierun-bot, ph-*, MoonieXHQ),
        # with AppData and the legacy junctions skipped (NT_SKIP_DIRS) except the dirs named below
        roots = [r"C:\Users\UsEr\Projects", home]
        appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        roots += [os.path.join(appdata, d) for d in ("gh", "rclone", "Code\\User")]
        roots += [os.path.join(home, f) for f in (".git-credentials", ".netrc", "_netrc", ".npmrc", ".pypirc")]
        return roots
    if sys.platform == "darwin":
        home = os.path.expanduser("~")
        roots = [os.path.join(home, d) for d in ("MoonieXHQ", "Projects", "LungNote Projects", ".claude",
                                                 ".config", ".ssh", ".docker", ".aws", ".codex", ".gemini")]
        roots += [os.path.join(home, f) for f in (".git-credentials", ".netrc", ".npmrc", ".pypirc",
                                                  ".pgpass", ".claude.json")]
        return roots
    roots = ["/opt/MoonieXHQ", "/root/projects", "/etc/mooniex", "/docker"]
    roots += sorted(os.path.join("/home", u) for u in _listdir("/home"))
    roots += [os.path.join("/root", d) for d in (".claude", ".config", ".ssh", ".docker", ".aws",
                                                 ".codex", ".gemini")]
    roots += [os.path.join("/root", f) for f in (".git-credentials", ".netrc", ".npmrc", ".pypirc",
                                                 ".pgpass", ".claude.json")]
    return roots


def _listdir(path: str) -> list[str]:
    try:
        return os.listdir(path)
    except OSError:
        return []


def scan_file(path: str, basename: str, kind: str) -> list[dict]:
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return []
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return []
    if kind == "keyfile":
        row = keyfile_row(data, basename)
        return [row] if row else []
    if b"\x00" in data[:4096]:
        return []
    return parse_text(data.decode("utf-8", "replace"), basename)


def scan(roots: list[str], host: str, skip_dirs: set[str] | None = None) -> dict:
    """Walk the roots; one entry per file that holds at least one credential row. Symlinked
    directories are not followed and a file reached twice (a compat link) is counted once."""
    skip = (SKIP_DIRS | (NT_SKIP_DIRS if os.name == "nt" else set())) if skip_dirs is None else skip_dirs
    files, unreadable, seen_real = [], [], set()
    walked: list[str] = []

    def visit(path: str, basename: str) -> None:
        if denied(path):
            return
        kind = file_kind(basename)
        if not kind:
            return
        real = os.path.realpath(path)
        if real in seen_real or denied(real):
            return
        seen_real.add(real)
        if not os.access(path, os.R_OK):
            unreadable.append(path)
            return
        rows = scan_file(path, basename, kind)
        if rows:
            files.append({"path": path, "rows": rows})

    for root in roots:
        if not os.path.lexists(root) or denied(root):
            continue
        walked.append(root)
        if os.path.isfile(root):
            visit(root, os.path.basename(root))
            continue
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: unreadable.append(e.filename)):
            dirnames[:] = [d for d in dirnames if d not in skip and not denied(os.path.join(dirpath, d))]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                if fn == "settings.local.json" or file_kind(fn):
                    visit(full, fn)
    return {"source": "disk", "host": host, "scanned_at": _now(), "roots": walked,
            "files": files, "unreadable": sorted(set(p for p in unreadable if p))}


def _hostname() -> str:
    if os.name == "nt":
        return os.environ.get("COMPUTERNAME", "windows").lower()
    return os.uname().nodename


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- winbox -----------------------------------------------------------------------------------

def scan_winbox(ssh_host: str = "winbox", timeout: int = 900) -> dict:
    """Run scan-local on winbox by piping this very file to its python over ssh. Values are hashed
    on winbox; only names, paths and hashes cross the wire."""
    with open(os.path.abspath(__file__), "rb") as fh:
        source = fh.read()
    proc = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", ssh_host,
                           "python", "-", "scan-local", "--host", ssh_host],
                          input=source, capture_output=True, timeout=timeout, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ssh {ssh_host} scan exited {proc.returncode}")
    return json.loads(proc.stdout.decode("utf-8", "replace"))


# --- GitHub -----------------------------------------------------------------------------------

def _gh_json(args: list[str], run=None):
    run = run or (lambda a: subprocess.run(a, capture_output=True, text=True, timeout=120, check=False))
    proc = run(["gh", *args])
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return json.loads(out) if out else None


def github(owner: str = "PASAKON", run=None, workers: int = 8) -> dict:
    """Names only: the API never returns an Actions secret's value."""
    repos = _gh_json(["repo", "list", owner, "--limit", "1000", "--json",
                      "name,visibility,isArchived,isFork"], run) or []

    def one(repo: dict) -> dict:
        full = f"{owner}/{repo['name']}"
        secrets = _gh_lines(["api", f"repos/{full}/actions/secrets", "--paginate",
                             "--jq", ".secrets[] | {name, created_at, updated_at}"], run)
        keys = _gh_lines(["api", f"repos/{full}/keys", "--paginate", "--jq",
                          ".[] | {id, title, read_only, created_at, last_used}"], run)
        meta = _gh_json(["api", f"repos/{full}", "--jq", ".security_and_analysis"], run)
        return {"repo": repo["name"], "visibility": repo.get("visibility"),
                "archived": repo.get("isArchived"), "fork": repo.get("isFork"),
                "secrets": secrets or [], "secrets_ok": secrets is not None,
                "deploy_keys": keys or [], "deploy_keys_ok": keys is not None,
                "security_and_analysis": meta}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        out = list(pool.map(one, repos))
    return {"source": "github", "owner": owner, "scanned_at": _now(), "repos": out}


def _parse_jsonl_objects(text: str) -> list[dict]:
    """`gh api --jq '.x[] | {...}'` prints one JSON object per line."""
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _gh_lines(args: list[str], run=None) -> list[dict] | None:
    run = run or (lambda a: subprocess.run(a, capture_output=True, text=True, timeout=120, check=False))
    proc = run(["gh", *args])
    if proc.returncode != 0:
        return None
    return _parse_jsonl_objects(proc.stdout)


# --- Infisical --------------------------------------------------------------------------------

def infisical(identity: str = "contabo", org=None) -> dict:
    """Names + metadata per project/env through the machine's existing identity. A value is
    hashed in memory and dropped; it is never printed or stored."""
    if org is None:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from tools import infisical_setup   # the identity flow it already has (PLAN §5)
        org = infisical_setup.Org(identity)
    projects_out, errors = [], []
    for slug, p in sorted(org.projects().items()):
        try:
            envs = org.environments(p["id"])
        except Exception as exc:  # noqa: BLE001 — one unreadable project must not stop the rest
            errors.append({"project": p.get("name") or slug, "error": _err(exc)})
            continue
        for env in sorted(envs):
            try:
                out = org.get("/api/v3/secrets/raw", workspaceId=p["id"], environment=env,
                              secretPath="/", recursive="true", include_imports="false")
            except Exception as exc:  # noqa: BLE001
                errors.append({"project": p.get("name") or slug, "env": env, "error": _err(exc)})
                continue
            rows = []
            for s in out.get("secrets", []):
                value = s.get("secretValue")
                meta = {m.get("key"): m.get("value") for m in (s.get("secretMetadata") or [])
                        if isinstance(m, dict) and m.get("key")}
                rows.append({
                    "name": s.get("secretKey"), "path": s.get("secretPath") or "/",
                    "hash12": hash12(value) if value else None,
                    "weak": is_weak(s.get("secretKey") or "", value or ""),
                    "comment": bool(s.get("secretComment")),
                    "tags": sorted(t.get("slug") or t.get("name") for t in (s.get("tags") or [])
                                   if isinstance(t, dict)),
                    "scope": meta.get("scope"), "expires": meta.get("expires"),
                    "owner": meta.get("owner"), "meta_keys": sorted(meta),
                    "created_at": s.get("createdAt"), "updated_at": s.get("updatedAt"),
                    "version": s.get("version"),
                })
                value = None
            projects_out.append({"project": p.get("name") or slug, "env": env, "secrets": rows})
    return {"source": "infisical", "identity": identity, "scanned_at": _now(),
            "projects": projects_out, "errors": errors}


def _err(exc: Exception) -> str:
    """An API error message, cut short. Infisical error bodies carry no secret value."""
    return f"{type(exc).__name__}: {str(exc)[:200]}"


# --- report -----------------------------------------------------------------------------------

PROVIDERS = (
    ("OPENROUTER", "openrouter"), ("ANTHROPIC", "anthropic"), ("CLAUDE", "anthropic"),
    ("OPENAI", "openai"), ("SUPABASE", "supabase"), ("TELEGRAM", "telegram"), ("LINE_", "line"),
    ("FAL", "fal"), ("GEMINI", "google"), ("GOOGLE", "google"), ("GCP", "google"), ("YOUTUBE", "google"),
    ("DRIVE", "google"), ("GITHUB", "github"), ("GH_", "github"), ("CLOUDFLARE", "cloudflare"),
    ("CF_", "cloudflare"), ("R2_", "cloudflare-r2"), ("NOTION", "notion"), ("ZAI", "z.ai"),
    ("GLM", "z.ai"), ("DEEPGRAM", "deepgram"), ("ELEVENLABS", "elevenlabs"), ("META", "meta"),
    ("FB_", "meta"), ("FACEBOOK", "meta"), ("INSTAGRAM", "meta"), ("STRIPE", "stripe"),
    ("AWS", "aws"), ("VERCEL", "vercel"), ("TAILSCALE", "tailscale"), ("TS_", "tailscale"),
    ("INFISICAL", "infisical"), ("POSTGRES", "postgres"), ("PG", "postgres"), ("DATABASE", "postgres"),
    ("ORG_DB", "postgres"), ("DB_", "postgres"), ("REDIS", "redis"), ("JULES", "google-jules"),
    ("NINEROUTER", "9router"), ("RUNPOD", "runpod"), ("HIGGSFIELD", "higgsfield"),
    ("DISCORD", "discord"), ("SLACK", "slack"), ("RESEND", "resend"), ("SENDGRID", "sendgrid"),
    ("MINIMAX", "minimax"), ("KLING", "kling"), ("REPLICATE", "replicate"), ("HF_", "huggingface"),
    ("HUGGINGFACE", "huggingface"), ("TIKTOK", "tiktok"), ("JEV", "jev"), ("TYPESAFE", "jev"),
    ("TOPVIEW", "topview"), ("SEEDANCE", "seedance"), ("XAI", "xai"), ("GROQ", "groq"),
    ("MISTRAL", "mistral"), ("DEEPSEEK", "deepseek"), ("TWILIO", "twilio"), ("SENTRY", "sentry"),
    ("RUN_INBOX", "mooniex-run-inbox"), ("RELAY", "mooniex-relay"), ("LUNGNOTE", "lungnote"),
    ("CODEX", "openai"), ("GMAIL", "google"), ("OUTLOOK", "microsoft"), ("PEXELS", "pexels"),
    ("SERPAPI", "serpapi"), ("SENDPULSE", "sendpulse"), ("XM_", "xm-broker"), ("EXNESS", "exness"),
    ("POSTFORME", "postforme"), ("HERMES", "hermes"), ("SECRETARY", "mooniex-secretary"), ("JWT", "self"), ("SESSION", "self"),
    ("ADMIN", "self"), ("WEBHOOK", "self"),
)


# a credential file in a tool's profile dir says whose it is when the variable name does not
PROFILE_PROVIDERS = {"profile:.claude": "anthropic (claude oauth)", "profile:.config/gh": "github",
                     "profile:.config/colab-cli": "google", "profile:.codex": "openai",
                     "profile:.gemini": "google", "profile:AppData/Roaming/rclone": "google (drive sync)"}


def provider_of(name: str) -> str:
    up = name.upper().lstrip("_")
    for prefix, prov in PROVIDERS:
        if up.startswith(prefix):
            return prov
    for prefix, prov in PROVIDERS:
        if len(prefix) > 3 and prefix.strip("_") in up:
            return prov
    if up.startswith(("ID_", "ID_RSA", "ID_ED25519")) or up.endswith((".PEM", ".KEY")):
        return "ssh/tls key"
    return "?"


def consumer_of(host: str, path: str) -> str:
    p = path.replace("\\", "/")
    m = re.search(r"/MoonieXHQ/Projects/([^/]+)/([^/]+)", p)
    if m and "/Archive/" not in p:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"/MoonieXHQ/Agents/([^/]+)", p)
    if m:
        return f"Agents-{m.group(1)}"
    m = re.search(r"/MoonieXHQ/Archive/(.+)$", p)
    if m:
        parts = m.group(1).split("/")
        return "Archive/" + "/".join(parts[:2] if len(parts) > 2 else parts[:1])
    m = re.search(r"/MoonieXHQ/([^/]+)/([^/]+)", p)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    m = re.search(r"/etc/mooniex/([^/]+)$", p)
    if m:
        return "etc-mooniex:" + re.sub(r"[-.](secrets?|env)$|\.env$", "", m.group(1).rsplit(".", 1)[0])
    m = re.search(r"^/root/projects/([^/]+)", p)
    if m:
        return m.group(1)
    m = re.search(r"/(?:Users/[^/]+/|home/[^/]+/|root/)(\.claude|\.config/gh|\.config/[^/]+|\.ssh|\.docker|"
                  r"\.codex|\.gemini|\.aws|AppData/Roaming/[^/]+)", p)
    if m:
        user = re.search(r"/(?:Users|home)/([^/]+)/", p)
        return f"profile:{m.group(1)}({user.group(1) if user else 'root'})"
    m = re.search(r"/mooniex/repo/([^/]+)/", p)
    if m:
        return m.group(1)
    m = re.search(r"/Users/[^/]+/Projects/([^/]+)", p)
    if m:
        return m.group(1)
    m = re.search(r"^[A-Za-z]:/Users/[^/]+/([^/.][^/]*)/", p)   # a project folder straight under the profile
    if m:
        return m.group(1)
    m = re.search(r"^/home/([^/]+)/", p)
    if m:
        return f"home:{m.group(1)}"
    m = re.search(r"^/docker/([^/]+)", p)
    if m:
        return f"docker:{m.group(1)}"
    return "?"


TEMPLATE_RE = re.compile(r"\.(example|sample|template|dist)$", re.I)


def _disk_rows(scan_out: dict) -> list[dict]:
    rows = []
    host = scan_out["host"]
    for f in scan_out["files"]:
        archive = bool(re.search(r"[/\\]Archive[/\\]", f["path"]))
        template = bool(TEMPLATE_RE.search(f["path"]))
        for r in f["rows"]:
            rows.append({"name": r["name"], "where": f"{host}:{f['path']}" + (f":{r['line']}" if r["line"] else ""),
                         "host": host, "kind": r["kind"], "hash12": r["hash12"], "weak": r["weak"],
                         "consumer": consumer_of(host, f["path"]), "archive": archive,
                         "template": template, "scope": "?", "expiry": "", "rotated": ""})
    return rows


def _inf_rows(inf: dict) -> list[dict]:
    rows = []
    for pe in inf["projects"]:
        for s in pe["secrets"]:
            folder = "" if s["path"] in ("/", "") else s["path"].rstrip("/")
            rows.append({"name": s["name"], "where": f"infisical:{pe['project']}/{pe['env']}{folder}",
                         "host": "infisical", "kind": "infisical", "hash12": s["hash12"], "weak": s["weak"],
                         "consumer": pe["project"], "archive": False, "scope": s.get("scope") or "?",
                         "expiry": s.get("expires") or "", "rotated": (s.get("updated_at") or "")[:10],
                         "tags": s.get("tags") or []})
    return rows


def _gh_rows(gh: dict) -> list[dict]:
    rows = []
    for r in gh["repos"]:
        for s in r["secrets"]:
            rows.append({"name": s.get("name"), "where": f"github:{gh['owner']}/{r['repo']} (actions secret)",
                         "host": "github", "kind": "gh-secret", "hash12": None, "weak": False,
                         "consumer": r["repo"], "archive": bool(r.get("archived")), "scope": "repo",
                         "expiry": "", "rotated": (s.get("updated_at") or "")[:10]})
        for k in r["deploy_keys"]:
            rows.append({"name": f"deploy key: {k.get('title')}",
                         "where": f"github:{gh['owner']}/{r['repo']} (deploy key)", "host": "github",
                         "kind": "deploy-key", "hash12": None, "weak": False, "consumer": r["repo"],
                         "archive": bool(r.get("archived")),
                         "scope": "read-only" if k.get("read_only") else "read-write", "expiry": "none",
                         "rotated": (k.get("created_at") or "")[:10]})
    return rows


def classify(rows: list[dict]) -> None:
    """status per row (task-0a7c9dcc): infisical-only / disk-only / both / dead.
    dead = an Archive copy, or a live disk copy whose name is in Infisical under another value.
    GitHub rows carry no value, so their status is `github`."""
    inf_hashes = {r["hash12"] for r in rows if r["host"] == "infisical" and r["hash12"]}
    inf_names = {r["name"] for r in rows if r["host"] == "infisical"}
    live_disk_hashes = {r["hash12"] for r in rows
                        if r["host"] not in ("infisical", "github") and not r["archive"]}
    for r in rows:
        if r["host"] == "github":
            r["status"] = "github"
        elif r["host"] == "infisical":
            r["status"] = "both" if r["hash12"] in live_disk_hashes else "infisical-only"
        elif r["archive"]:
            r["status"] = "dead"
        elif r["hash12"] in inf_hashes:
            r["status"] = "both"
        elif r["name"] in inf_names:
            r["status"] = "dead"
        else:
            r["status"] = "disk-only"


def display_hashes(rows: list[dict]) -> None:
    """hash12 for strong values; a same-value group label (w1, w2 ..) for weak ones, so a public
    report never offers a word-list attacker a hash to test guesses against."""
    groups: dict[str, str] = {}
    for r in sorted(rows, key=lambda x: (x["name"], x["where"])):
        h = r.get("hash12")
        if not h:
            r["hash"] = "—"
        elif r.get("weak"):
            groups.setdefault(h, f"w{len(groups) + 1}")
            r["hash"] = f"withheld={groups[h]}"
        else:
            r["hash"] = h


def hq_status(hq_path: str = "/opt/MoonieXHQ/hq.yaml") -> dict[str, str]:
    """repo name -> hq.yaml status (active / parked / retired) for the 'still used' mark."""
    try:
        import yaml  # noqa: PLC0415 — Contabo venv has it; the scanner itself stays stdlib
        with open(hq_path) as fh:
            doc = yaml.safe_load(fh)
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for row in doc.get("folders", []) or []:
        repo = (row.get("repo") or "").split("/")[-1]
        if repo:
            out[repo] = row.get("status") or "active"
    return out


def build_report(inputs: list[dict], hq: dict[str, str] | None = None) -> tuple[str, dict]:
    rows: list[dict] = []
    meta = {"hosts": [], "unreadable": {}, "infisical_errors": [], "gh_security": []}
    for doc in inputs:
        if doc["source"] == "disk":
            rows += _disk_rows(doc)
            meta["hosts"].append({"host": doc["host"], "roots": doc["roots"], "scanned_at": doc["scanned_at"],
                                  "files": len(doc["files"])})
            meta["unreadable"][doc["host"]] = doc.get("unreadable", [])
        elif doc["source"] == "infisical":
            rows += _inf_rows(doc)
            meta["infisical_errors"] = doc.get("errors", [])
            meta["hosts"].append({"host": "infisical", "identity": doc["identity"],
                                  "scanned_at": doc["scanned_at"],
                                  "projects": sorted({p["project"] for p in doc["projects"]})})
        elif doc["source"] == "github":
            rows += _gh_rows(doc)
            meta["hosts"].append({"host": "github", "owner": doc["owner"], "scanned_at": doc["scanned_at"],
                                  "repos": len(doc["repos"])})
            for r in doc["repos"]:
                if r.get("visibility", "").upper() == "PUBLIC":
                    sa = r.get("security_and_analysis") or {}
                    meta["gh_security"].append({
                        "repo": r["repo"], "archived": bool(r.get("archived")),
                        "secret_scanning": (sa.get("secret_scanning") or {}).get("status", "?"),
                        "push_protection": (sa.get("secret_scanning_push_protection") or {}).get("status", "?")})
    # a .env.example is a template: its rows stay only when a value equals a real value somewhere
    real = {r["hash12"] for r in rows if r.get("hash12") and not r.get("template")}
    meta["templates_dropped"] = sum(1 for r in rows if r.get("template") and r["hash12"] not in real)
    meta["templates_real"] = sorted({r["where"] for r in rows if r.get("template") and r["hash12"] in real})
    rows = [r for r in rows if not r.get("template") or r["hash12"] in real]
    classify(rows)
    display_hashes(rows)
    for r in rows:
        r["provider"] = provider_of(r["name"])
        if r["provider"] == "?":
            r["provider"] = PROFILE_PROVIDERS.get(r["consumer"].split("(")[0], "?")
    hq = hq if hq is not None else {}
    md = render_md(rows, meta, hq)
    public_rows = [{k: r[k] for k in ("name", "where", "provider", "consumer", "scope", "expiry", "rotated",
                                      "hash", "status")} for r in rows]
    return md, {"generated_at": _now(), "meta": meta, "summary": summary(rows), "rows": public_rows}


def summary(rows: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        host = r["host"] + (" (Archive)" if r["archive"] and r["host"] not in ("github",) else "")
        out.setdefault(host, {})
        out[host][r["status"]] = out[host].get(r["status"], 0) + 1
    return out


STATUSES = ("disk-only", "both", "dead", "infisical-only", "github")
# names whose last-rotated date the brief asks about (ORG_DB_URL: the 26 Oct leak, rotation due 27 Oct)
WATCH_NAMES = ("ORG_DB_URL",)


def _cell(v) -> str:
    return str(v if v not in (None, "") else "").replace("|", "\\|")


def render_md(rows: list[dict], meta: dict, hq: dict[str, str]) -> str:
    L: list[str] = []
    L.append("# Credential inventory — names only (HQSecurity M0)\n")
    L.append(f"Generated {_now()} by `tools/secret_inventory.py` (task-0a7c9dcc). No value appears in this "
             "file. `hash` = `sha256(value)[:12]`, only for spotting one value in two places; for a "
             "low-entropy value (a password, or 19 characters or fewer) the hash is withheld and a "
             "same-value group label (`withheld=wN`) is shown instead.\n")
    L.append("## Summary (rows by host × status)\n")
    s = summary(rows)
    L.append("| host | " + " | ".join(STATUSES) + " | total |")
    L.append("|---|" + "---|" * (len(STATUSES) + 1))
    tot = {k: 0 for k in STATUSES}
    for host in sorted(s):
        c = s[host]
        for k in STATUSES:
            tot[k] += c.get(k, 0)
        L.append(f"| {host} | " + " | ".join(str(c.get(k, 0)) for k in STATUSES) + f" | {sum(c.values())} |")
    L.append("| **total** | " + " | ".join(str(tot[k]) for k in STATUSES) + f" | {sum(tot.values())} |\n")
    L.append("Status: `disk-only` = on disk, value not in Infisical · `both` = the same value is on disk and in "
             "Infisical · `dead` = an Archive copy, or a disk copy whose name is in Infisical under a different "
             "value · `infisical-only` = in Infisical, no live disk copy found on the scanned hosts · `github` = "
             "a GitHub Actions secret or deploy key (GitHub never returns a value, so it cannot be compared).\n")
    distinct = len({r["hash12"] for r in rows if r.get("hash12")})
    shared = _shared_values(rows)
    L.append(f"Distinct values seen: {distinct}. Values found under more than one live place: {len(shared)}.\n")
    L.append("## Sources\n")
    for h in meta["hosts"]:
        L.append("- " + ", ".join(f"{k}: {_fmt(v)}" for k, v in h.items()))
    for host, bad in meta["unreadable"].items():
        if bad:
            L.append(f"- {host}: {len(bad)} path(s) unreadable (permission): " + ", ".join(f"`{b}`" for b in bad[:10])
                     + (" …" if len(bad) > 10 else ""))
    if meta.get("templates_dropped"):
        L.append(f"- {meta['templates_dropped']} row(s) from template files (.env.example …) dropped: no value equals a "
                 "real one. Template rows kept because a value equals a real value: "
                 + (", ".join(f"`{w}`" for w in meta["templates_real"]) or "none"))
    for e in meta["infisical_errors"]:
        L.append(f"- infisical: could not read {e.get('project')}/{e.get('env', '*')}: {e.get('error')}")
    L.append("")
    watch = [r for r in rows if r["name"] in WATCH_NAMES]
    if watch:
        L.append("## Watch list\n")
        L.append("| variable | where | last rotated | tags | status |")
        L.append("|---|---|---|---|---|")
        for r in sorted(watch, key=lambda r: r["where"]):
            L.append(f"| {r['name']} | {_cell(r['where'])} | {r['rotated'] or '?'} | "
                     f"{', '.join(r.get('tags') or []) or '—'} | {r['status']} |")
        L.append("")
    if shared:
        L.append("## One value, several places (live copies only)\n")
        L.append("| hash | names | places |")
        L.append("|---|---|---|")
        for h, rs in shared:
            L.append(f"| {rs[0]['hash']} | {', '.join(sorted({r['name'] for r in rs}))} | "
                     + "<br>".join(_cell(r["where"]) for r in rs) + " |")
        L.append("")
    L.extend(_by_provider(rows))
    if meta["gh_security"]:
        L.append("## GitHub public repos: secret scanning and push protection\n")
        L.append("| repo | archived | secret scanning | push protection |")
        L.append("|---|---|---|---|")
        for g in sorted(meta["gh_security"], key=lambda g: g["repo"].lower()):
            L.append(f"| {g['repo']} | {'yes' if g['archived'] else ''} | {g['secret_scanning']} | {g['push_protection']} |")
        L.append("")
    live = [r for r in rows if not (r["archive"] and r["host"] != "github")]
    archive = [r for r in rows if r["archive"] and r["host"] != "github"]
    groups: dict[str, list[dict]] = {}
    canon: dict[str, str] = {}   # LungNote-Mcp (disk) and LungNote-MCP (Infisical) are one project
    for r in sorted(live, key=lambda r: r["host"] != "infisical"):
        canon.setdefault(r["consumer"].lower(), r["consumer"])
    for r in live:
        groups.setdefault(canon[r["consumer"].lower()], []).append(r)
    hq = {k.lower(): v for k, v in hq.items()}

    def order(item):
        name, rs = item
        on_disk = sum(1 for r in rs if r["status"] in ("disk-only", "dead"))
        return (0 if on_disk else 1, -on_disk, name.lower())

    L.append("## By project\n")
    L.append("Projects whose keys still sit on a machine (`disk-only` / `dead`) come first. `hq.yaml` = the row's "
             "status in the HQ map (active / parked / retired); whether the CEO still uses a project is his call "
             "and is not marked here.\n")
    for name, rs in sorted(groups.items(), key=order):
        on_disk = sum(1 for r in rs if r["status"] in ("disk-only", "dead"))
        L.append(f"### {name}  ·  hq.yaml: {hq.get(name.lower(), '—')}  ·  on disk: {on_disk} / {len(rs)}\n")
        L.extend(_table(rs))
    if archive:
        L.append("## Archive copies (dead by definition)\n")
        L.extend(_table(archive))
    return "\n".join(L) + "\n"


def _by_provider(rows: list[dict]) -> list[str]:
    """Keys that still sit on a machine (live copies, not Archive), per provider: what a relay login
    per provider has to cover."""
    by: dict[str, dict[str, set]] = {}
    for r in rows:
        if r["host"] in ("infisical", "github") or r["archive"]:
            continue
        cell = by.setdefault(r["provider"], {})
        cell.setdefault(r["name"], set()).add(f"{r['host']}:{r['consumer']}" + ("" if r["status"] == "disk-only"
                                                                                else f" ({r['status']})"))
    if not by:
        return []
    out = ["## Keys on disk by provider (live copies)\n",
           "| provider | variable | host:consumer (status when not disk-only) |", "|---|---|---|"]
    for prov in sorted(by, key=lambda p: (p == "?", p)):
        for name in sorted(by[prov]):
            out.append(f"| {prov} | {_cell(name)} | {_cell(', '.join(sorted(by[prov][name])))} |")
    out.append("")
    return out


def _shared_values(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    by: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("hash12") and not r["archive"] and r["host"] not in ("github", "infisical"):
            by.setdefault(r["hash12"], []).append(r)
    out = [(h, rs) for h, rs in by.items() if len({_file_of(r["where"]) for r in rs}) > 1]
    return sorted(out, key=lambda x: (-len(x[1]), x[1][0]["name"]))


def _file_of(where: str) -> str:
    return re.sub(r":\d+$", "", where)


def _table(rs: list[dict]) -> list[str]:
    out = ["| variable | where | provider | consumer | scope | expiry | last rotated | hash | status |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rs, key=lambda r: (STATUSES.index(r["status"]), r["name"], r["where"])):
        out.append("| " + " | ".join(_cell(r[k]) for k in ("name", "where", "provider", "consumer", "scope",
                                                            "expiry", "rotated", "hash", "status")) + " |")
    out.append("")
    return out


def _fmt(v) -> str:
    if isinstance(v, list):
        return f"{len(v)} ({', '.join(map(str, v[:12]))}{' …' if len(v) > 12 else ''})"
    return str(v)


# --- CLI --------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan-local")
    s.add_argument("--root", action="append", default=[])
    s.add_argument("--host", "--host-label", dest="host", default=_hostname(),
                   help="label written into every row (contabo / winbox / mac)")
    w = sub.add_parser("scan-winbox")
    w.add_argument("--ssh-host", default="winbox")
    g = sub.add_parser("github")
    g.add_argument("--owner", default="PASAKON")
    i = sub.add_parser("infisical")
    i.add_argument("--as", dest="identity", default="contabo")
    r = sub.add_parser("report")
    r.add_argument("--in", dest="inputs", action="append", required=True)
    r.add_argument("--out", required=True, help="path of the .md; the .json goes beside it")
    r.add_argument("--hq", default="/opt/MoonieXHQ/hq.yaml")
    a = ap.parse_args(argv)
    if a.cmd == "scan-local":
        out = scan(a.root or default_roots(), a.host)
    elif a.cmd == "scan-winbox":
        out = scan_winbox(a.ssh_host)
    elif a.cmd == "github":
        out = github(a.owner)
    elif a.cmd == "infisical":
        out = infisical(a.identity)
    else:
        docs = []
        for p in a.inputs:
            with open(p) as fh:
                docs.append(json.load(fh))
        md, js = build_report(docs, hq_status(a.hq))
        base = a.out[:-3] if a.out.endswith(".md") else a.out
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(base + ".md", "w") as fh:
            fh.write(md)
        with open(base + ".json", "w") as fh:
            json.dump(js, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print(f"wrote {base}.md and {base}.json: {len(js['rows'])} rows", file=sys.stderr)
        return 0
    json.dump(out, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
