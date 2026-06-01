"""Category definitions + state I/O for the GateGuard category-bypass wrapper.

Each category is a (name, path-regex) pair. A file_path matches the FIRST
category whose regex matches; the rest are ignored. Order matters — keep
narrow patterns first.

State lives at $HOME/.claude/state/mooniex-gateguard-<session>.json.
session id derivation MUST match what ECC GateGuard uses (so cache
boundaries align):
  1. env CLAUDE_SESSION_ID    (canonical, when present)
  2. env ECC_SESSION_ID       (fallback)
  3. SHA256 prefix of CLAUDE_PROJECT_DIR or cwd  (matches ECC's
     resolveSessionKey() final fallback)

Schema:
  { "categories": ["wiki_edit", "agents_config"],
    "last_active": <unix-ms> }

last_active expires the cache after 30 minutes of idle, matching ECC's
SESSION_TIMEOUT_MS. After expiry, categories start empty again.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path

CATEGORIES = [
    ("wiki_edit",     re.compile(r"^/Users/gob/Projects/LLMs/")),
    ("agents_config", re.compile(r"^/Users/gob/Projects/Agents/config/")),
    ("agents_roles",  re.compile(r"^/Users/gob/Projects/Agents/roles/")),
    ("memory",        re.compile(r"/\.claude/projects/.*/memory/")),
    ("claudemd",      re.compile(r"^/Users/gob/(Projects/)?CLAUDE\.md$|^/Users/gob/\.claude/CLAUDE\.md$")),
]

SESSION_TIMEOUT_MS = 30 * 60 * 1000
STATE_DIR = Path(os.environ.get("HOME", "/tmp")) / ".claude" / "state"


def category_for(file_path: str) -> str | None:
    for name, pattern in CATEGORIES:
        if pattern.search(file_path):
            return name
    return None


def session_key() -> str:
    for env_key in ("CLAUDE_SESSION_ID", "ECC_SESSION_ID"):
        v = os.environ.get(env_key, "").strip()
        if v:
            # Sanitize same way ECC does — alphanum/dash/underscore only
            safe = re.sub(r"[^a-zA-Z0-9_-]", "_", v)[:64]
            if safe:
                return safe
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return "proj-" + hashlib.sha256(cwd.encode()).hexdigest()[:24]


def state_file() -> Path:
    return STATE_DIR / f"mooniex-gateguard-{session_key()}.json"


def load_state() -> dict:
    sf = state_file()
    if not sf.exists():
        return {"categories": [], "last_active": 0}
    try:
        s = json.loads(sf.read_text())
        if (time.time() * 1000) - s.get("last_active", 0) > SESSION_TIMEOUT_MS:
            return {"categories": [], "last_active": 0}
        return s
    except Exception:
        return {"categories": [], "last_active": 0}


def save_state(s: dict) -> bool:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        s["last_active"] = int(time.time() * 1000)
        sf = state_file()
        tmp = sf.with_suffix(f".tmp.{os.getpid()}")
        tmp.write_text(json.dumps(s))
        tmp.replace(sf)
        return True
    except Exception:
        return False


def is_category_presented(category: str) -> bool:
    return category in load_state().get("categories", [])


def mark_category_presented(category: str) -> None:
    s = load_state()
    cats = s.get("categories", [])
    if category not in cats:
        cats.append(category)
        s["categories"] = cats
        save_state(s)
