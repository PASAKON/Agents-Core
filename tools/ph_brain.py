"""Persistent Project Head planning brains with AGY-to-Codex quota fallback.

Runs Project Head (PH) reasoning, planning, long-script context (e.g. 95-shot
video pipelines), and worker delegation on Antigravity CLI (`agy`) or Codex,
consuming 0% Claude Code ($20 Pro) usage.

Architecture:
- Primary Brain: `claude-opus-5-5-medium` (bucket `agy-claude`)
- Auto-Fallback 1: `gemini-4-argon-high` (bucket `agy-gemini`)
- Auto-Fallback 2: `claude-sonnet-5-5-high` (bucket `agy-claude`)
- Auto-Fallback 3: `gemini-3.8-flash-high` (bucket `agy-gemini`)

Key property verified on `agy` CLI:
Passing `--conversation <uuid> --model <new_model>` resumes the exact same
multi-turn conversation thread across model families (Claude Opus 5.5 <->
Gemini 4 Argon High) without losing any prior turns or shot continuity.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from contextvars import ContextVar
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BRAINS_DIR = ROOT / "state" / "ph-brains"
from lib import ph_state

_IN_TURN = ContextVar('ph_brain_turn', default=False)
QUOTA_SNAPSHOT = ROOT / "state" / "quota-snapshot.json"

PRIMARY_MODEL = "claude-opus-5-5-medium"
FALLBACK_MODEL = "gemini-4-argon-high"

MODEL_CHAIN: tuple[tuple[str, str], ...] = (
    ("claude-opus-5-5-medium", "agy-claude"),
    ("gemini-4-argon-high", "agy-gemini"),
    ("claude-sonnet-5-5-high", "agy-claude"),
    ("gemini-3.8-flash-high", "agy-gemini"),
)

MODEL_TO_BUCKET: dict[str, str] = {
    **dict(MODEL_CHAIN),
    "claude-opus-5-5-high": "agy-claude",
    "claude-opus-5-5-low": "agy-claude",
    "claude-sonnet-5-5-medium": "agy-claude",
    "claude-sonnet-5-5-low": "agy-claude",
    "gemini-4-argon-medium": "agy-gemini",
    "gemini-4-argon-low": "agy-gemini",
    "gemini-3.8-flash-medium": "agy-gemini",
    "gemini-3.8-flash-low": "agy-gemini",
}

LIMIT_PATTERNS: tuple[str, ...] = (
    "you have exhausted your quota on this model",
    "ai: out of credits",
    "resource_exhausted",
    "quota exceeded",
    "rate_limit_exceeded",
    "model capacity exhausted",
    "individual quota reached",
)

# 3 Nov 2026: a brain run with edit rights tried edit_file itself, was refused and sat
# for the full 600 s. The brain plans; workers edit.
TURN_TIMEOUT_S = 240
PLANNER_RULE = ("You are a planner. Never edit or create files yourself; "
                "put every change in a delegate brief for a worker.")

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_agy_bin() -> str:
    """Find the `agy` binary across Contabo (/root/.local/bin/agy), Mac (~/.local/bin/agy), and Winbox."""
    env_bin = os.environ.get("AGY_BIN", "").strip()
    if env_bin and Path(env_bin).is_file():
        return env_bin
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    candidates = [
        Path.home() / ".local" / "bin" / "agy",
        Path("/root/.local/bin/agy"),
        Path("/Users/gob/.local/bin/agy"),
    ]
    if local_app_data:
        candidates.append(Path(local_app_data) / "agy" / "bin" / "agy.exe")
    candidates.append(Path("C:/Users/passg/AppData/Local/agy/bin/agy.exe"))
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)
    which = shutil.which("agy") or shutil.which("agy.exe")
    if which:
        return which
    return str(Path.home() / ".local" / "bin" / "agy")


def load_quota_buckets(snapshot_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Read bucket remaining fractions from state/quota-snapshot.json."""
    path = Path(snapshot_path or QUOTA_SNAPSHOT)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        buckets = data.get("buckets")
        if isinstance(buckets, dict):
            return buckets
    except (OSError, ValueError):
        pass
    return {}


def bucket_is_usable(
    bucket_name: str,
    buckets: dict[str, dict[str, Any]],
    *,
    min_remaining: float = 0.02,
) -> bool:
    """Return True unless the snapshot explicitly shows the bucket is exhausted or below reserve."""
    info = buckets.get(bucket_name)
    if not isinstance(info, dict):
        return True
    weekly = info.get("weekly_remaining")
    daily = info.get("daily_remaining")
    if isinstance(weekly, (int, float)) and weekly <= min_remaining:
        return False
    if isinstance(daily, (int, float)) and daily <= min_remaining:
        return False
    return True


_QUOTA_COOLDOWN_PREFIX = "quota_cooldown:"


def record_shared_model_cooldown(model: str, *, ttl_s: int = 1800) -> bool:
    """Record a cross-host quota cooldown in the Hub DB `locks` table so all
    machines (`contabo`, `mac`, `winbox`) immediately skip `model` while it is
    rate-limited."""
    if not model:
        return False
    try:
        from datetime import timedelta
        from lib import config, db
        exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl_s)).isoformat(timespec="seconds")
        key = f"{_QUOTA_COOLDOWN_PREFIX}{model}"
        owner = config.self_host()
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO locks (key, owner, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET owner=excluded.owner, expires_at=excluded.expires_at",
                (key, owner, exp),
            )
        return True
    except Exception:
        return False


def get_shared_cooldown_models() -> set[str]:
    """Return set of model names currently in cross-host quota cooldown on the Hub DB."""
    out: set[str] = set()
    try:
        from lib import db
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with db.get_conn() as conn:
            rows = conn.execute(
                "SELECT key FROM locks WHERE key LIKE ? AND expires_at > ?",
                (f"{_QUOTA_COOLDOWN_PREFIX}%", now),
            ).fetchall()
        for r in rows:
            k = str(r["key"] or "")
            if k.startswith(_QUOTA_COOLDOWN_PREFIX):
                out.add(k[len(_QUOTA_COOLDOWN_PREFIX):])
    except Exception:
        pass
    return out


def select_model_chain(
    preferred_model: str | None = None,
    *,
    snapshot_path: Path | None = None,
    min_remaining: float = 0.02,
    force_fallback: bool = False,
    check_shared_cooldown: bool | None = None,
) -> list[str]:
    """Return ordered list of AGY models to try for this turn."""
    buckets = load_quota_buckets(snapshot_path)
    use_shared = (
        check_shared_cooldown
        if check_shared_cooldown is not None
        else (snapshot_path is None and os.environ.get("ORG_SHARED_QUOTA_SYNC") == "1")
    )
    cooled_down = get_shared_cooldown_models() if use_shared else set()
    chain: list[str] = []

    if force_fallback:
        ordered = [
            ("gemini-4-argon-high", "agy-gemini"),
            ("gemini-3.8-flash-high", "agy-gemini"),
            ("claude-opus-5-5-medium", "agy-claude"),
            ("claude-sonnet-5-5-high", "agy-claude"),
        ]
    else:
        ordered = list(MODEL_CHAIN)

    if preferred_model and not force_fallback and preferred_model not in cooled_down:
        bucket = MODEL_TO_BUCKET.get(preferred_model, "agy-claude")
        if bucket_is_usable(bucket, buckets, min_remaining=min_remaining):
            chain.append(preferred_model)

    for model, bucket in ordered:
        if (
            model not in chain
            and model not in cooled_down
            and bucket_is_usable(bucket, buckets, min_remaining=min_remaining)
        ):
            chain.append(model)

    # Always keep fallback / cooled-down models at the tail so the chain is never empty
    for model, _ in ordered:
        if model not in chain:
            chain.append(model)

    return chain


def is_quota_limit_text(text: str) -> str | None:
    """Return the matched limit pattern if `text` indicates an AGY model quota/capacity stop."""
    low = (text or "").lower()
    if re.search(r"\b429\b", low):
        return "429"
    for pat in LIMIT_PATTERNS:
        if pat in low:
            return pat
    return None


def _validate_ph_id(ph_id: str) -> str:
    clean = (ph_id or "").strip()
    if not _SAFE_ID_RE.fullmatch(clean):
        raise ValueError(f"invalid ph_id {ph_id!r}; expected [A-Za-z0-9_-]{{1,64}}")
    return clean


def state_path(ph_id: str, brains_dir: Path | None = None) -> Path:
    clean = _validate_ph_id(ph_id)
    base = Path(brains_dir or BRAINS_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{clean}.json"


def _fetch_hub_ph_state(ph_id: str) -> dict[str, Any] | None:
    """Query the Hub `ph_state` table for the latest state of `ph-<ph_id>` / `<ph_id>`
    so a PH brain relocated to another host inherits its context seamlessly."""
    try:
        from lib import db
        candidates = (f"ph-{ph_id}", ph_id)
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT session_id, project, lane, owner, host, model, doing "
                "FROM ph_state WHERE session_id IN (?, ?) ORDER BY updated DESC LIMIT 1",
                candidates,
            ).fetchone()
            if row:
                return dict(row)
    except Exception:
        pass
    return None


def load_brain_state(
    ph_id: str,
    brains_dir: Path | None = None,
    *,
    fetch_hub: bool | None = None,
) -> dict[str, Any]:
    path = state_path(ph_id, brains_dir)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
    clean_id = _validate_ph_id(ph_id)
    base = {
        "ph_id": clean_id,
        "project": None,
        "lane": "cto",
        "owner": None,
        "conversation_id": None,
        "active_model": PRIMARY_MODEL,
        "turn_count": 0,
        "fallback_events": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "last_summary": "",
    }
    should_fetch = fetch_hub if fetch_hub is not None else (brains_dir is None)
    if should_fetch:
        hub_row = _fetch_hub_ph_state(clean_id)
        if isinstance(hub_row, dict):
            if hub_row.get("project"):
                base["project"] = hub_row["project"]
            if hub_row.get("lane"):
                base["lane"] = str(hub_row["lane"]).lower()
            if hub_row.get("owner"):
                base["owner"] = hub_row["owner"]
            if hub_row.get("doing"):
                base["last_summary"] = str(hub_row["doing"])
            if hub_row.get("host"):
                base["relocated_from_host"] = str(hub_row["host"])
    return base


def save_brain_state(state: dict[str, Any], brains_dir: Path | None = None) -> Path:
    path = state_path(state["ph_id"], brains_dir)
    state["updated_at"] = _now_iso()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def build_initial_prompt(
    *,
    ph_id: str,
    project: str,
    lane: str,
    owner: str | None,
    message: str,
    previous_summary: str | None = None,
    relocated_from_host: str | None = None,
) -> str:
    """Wrap the first turn of a Project Head with its identity and core rules."""
    owner_str = owner or f"{lane}-main"
    continuity_block = ""
    if (previous_summary or "").strip():
        from_note = f" on '{relocated_from_host}'" if relocated_from_host else ""
        continuity_block = (
            f"\n[Cross-Host Continuity Summary from previous PH turn{from_note}]\n"
            f"{previous_summary.strip()}\n"
        )
    return (
        f"[Project Head Identity: PH#{ph_id} ({lane.upper()}) - Project: {project} | Reports to: {owner_str}]\n"
        f"You are the Project Head (PH) for project '{project}' in the '{lane}' lane.\n"
        f"Core rules:\n"
        f"1. Plan milestones, keep full continuity across all turns/shots, and delegate hands-on execution to workers.\n"
        f"2. Never use Claude Code worker quota when Claude is exhausted; leave a worker's runner empty so the router picks it: it skips an exhausted AGY bucket and falls to Codex. Pin AGY only when its quota is not at 0%.\n"
        f"3. Browser & Computer Use 80/20 rule: for routine browser jobs (Champa port 9280, Higgsfield port 9281, XM port 9224), always include `tools/agy_browse.py` and `http://127.0.0.1:<port>` in the brief so the router sends `browser_operator` to `agy:gemini-3.8-flash-high`; use `gemini-4-argon-high` to inspect screenshots (`shot` + `read_file`).\n"
        f"4. Keep responses concise, structured, and actionable.\n"
        f"5. {PLANNER_RULE}\n"
        f"{continuity_block}\n"
        f"--- Task / Message ---\n{message}"
    )


def ensure_browser_agy_brief(brief: str, *, port: int = 9280) -> str:
    """Ensure a browser_operator brief targeting AGY carries the exact tokens tools/route.py requires."""
    text = (brief or "").strip()
    has_tool = bool(re.search(r"(?<![\w/])tools/agy_browse\.py\b", text))
    has_cdp = bool(re.search(r"\bhttp://127\.0\.0\.1:\d{4,5}\b", text))
    if has_tool and has_cdp:
        return text
    inferred_port = port
    low = text.lower()
    if "higgsfield" in low or "9281" in low:
        inferred_port = 9281
    elif "xm" in low or "mypartners" in low or "9224" in low:
        inferred_port = 9224
    suffix = (
        f"\n\nBrowser Home: http://127.0.0.1:{inferred_port}. "
        f"Use only `tools/agy_browse.py --port {inferred_port} <verb>`."
    )
    return text + suffix


def _parse_agy_json(stdout: str) -> dict[str, Any] | None:
    """Parse the JSON object emitted by `agy --output-format json`."""
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except ValueError:
        pass
    # Fallback: find the last JSON object in stdout if prefix logs exist
    start = text.rfind("\n{")
    if start != -1:
        try:
            obj = json.loads(text[start + 1 :])
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
    return None


def invoke_agy(
    prompt: str,
    *,
    model: str,
    conversation_id: str | None = None,
    add_dirs: list[Path] | None = None,
    mode: str = "plan",
    timeout_s: int = TURN_TIMEOUT_S,
    agy_bin: str | None = None,
) -> dict[str, Any]:
    """Execute one `agy` CLI call and return structured result."""
    if not _IN_TURN.get():
        raise RuntimeError('PH brains must enter through run_turn')
    binary = agy_bin or resolve_agy_bin()
    cmd = [
        binary,
        "-p",
        prompt,
        "--model",
        model,
        "--mode",
        mode,
        "--output-format",
        "json",
    ]
    if conversation_id:
        cmd.extend(["--conversation", conversation_id])
    dirs = add_dirs if add_dirs is not None else [ROOT]
    for d in dirs:
        if d and Path(d).exists():
            cmd.extend(["--add-dir", str(d)])

    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        # A hung brain must not hang the PH shell's turn: give it a reply to show.
        return {
            "ok": False,
            "returncode": None,
            "model": model,
            "conversation_id": conversation_id,
            "response": f"brain timed out after {timeout_s}s; retry once with a shorter message",
            "limit_hit": None,
            "timed_out": True,
            "raw_stdout": "",
            "raw_stderr": "",
        }
    parsed = _parse_agy_json(proc.stdout)
    conv_id = (parsed or {}).get("conversation_id") or conversation_id
    response_text = (parsed or {}).get("response")
    if response_text is None:
        response_text = (proc.stdout or proc.stderr or "").strip()

    combined_text = "\n".join(
        part for part in (
            proc.stdout,
            proc.stderr,
            response_text or "",
        ) if part
    )
    # When a resumed conversation_id had an earlier turn hit 429, agy --output-format json
    # keeps that earlier turn's `"error"` field inside proc.stdout even when the fallback
    # model (e.g. gemini-4-argon-high) succeeds with returncode == 0 and a non-empty response.
    # Only treat this turn as limit_hit when it actually failed or emitted AGY_ERROR / limit text in response.
    has_agy_error_banner = "AGY_ERROR:" in (proc.stdout or "") or "AGY_ERROR:" in (proc.stderr or "")
    if (
        isinstance(parsed, dict)
        and proc.returncode == 0
        and bool((response_text or "").strip())
        and not has_agy_error_banner
    ):
        limit_hit = is_quota_limit_text("\n".join(part for part in (proc.stderr, response_text) if part))
    else:
        limit_hit = is_quota_limit_text(combined_text)

    ok = (
        proc.returncode == 0
        and limit_hit is None
        and bool((response_text or "").strip())
        and "jetski: no output produced" not in combined_text
    )
    return {
        "ok": ok,
        "returncode": proc.returncode,
        "model": model,
        "conversation_id": conv_id,
        "response": response_text,
        "limit_hit": limit_hit,
        "raw_stdout": proc.stdout,
        "raw_stderr": proc.stderr,
    }


# New brain adapters belong here, never in a second turn/launch branch. The
# common loop below records every adapter before it receives a prompt.
def codex_config() -> tuple[str, str]:
    from tools.quota import load_plans
    # The cheaper planning entry (Sol), rather than the complex-work Astra entry.
    entries = load_plans()['roles']['c_level_openai']
    entry = next(e for e in entries if e.startswith('codex:'))
    _, model, *effort = entry.split(':')
    # plans.yaml carries the short label; the Codex CLI only knows the full id
    # (same map as scripts/spawn-worker-remote.sh). "sol" alone fails with
    # "Model metadata for sol not found".
    if model in ('sol', 'astra', 'luna'):
        model = f'gpt-6-{model}'
    return model, effort[0] if effort else 'high'


def check_codex_budget(snapshot_path: Path | None) -> None:
    from tools import forecast, limits, quota
    info = load_quota_buckets(snapshot_path).get('codex', {})
    q = quota.Quota(provider='openai', weekly_remaining=info.get('weekly_remaining'),
                    daily_remaining=info.get('daily_remaining'))
    rows = limits.load_limits()
    cost, _ = forecast.cost_for('codex', 'S', limits=rows)
    verdict, _, why = forecast.verdict(q, cost, rows.get('codex'))
    if verdict == 'will_hit' or info.get('limit_hit'):
        raise RuntimeError(f'codex brain blocked by router budget reserve: {why}')


def invoke_codex(prompt: str, *, model: str, conversation_id=None,
                 timeout_s=TURN_TIMEOUT_S, **kwargs) -> dict[str, Any]:
    if not _IN_TURN.get():
        raise RuntimeError('PH brains must enter through run_turn')
    _, effort = codex_config()
    cmd = [os.environ.get('CODEX_BIN') or shutil.which('codex') or 'codex',
           '-c', 'sandbox_mode="read-only"', '-c', 'approval_policy="never"', 'exec']
    if conversation_id:
        cmd += ['resume', conversation_id]
    cmd += ['--json', '-m', model, '-c', f'model_reasoning_effort="{effort}"', '-']
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=timeout_s, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return dict(ok=False, returncode=None, conversation_id=conversation_id,
                    response=f'brain timed out after {timeout_s}s', limit_hit=None, timed_out=True)
    replies = []
    failed = False
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'thread.started':
            conversation_id = event.get('thread_id') or conversation_id
        if event.get('type') in ('error', 'turn.failed'):
            failed = True
        item = event.get('item', {})
        if event.get('type') == 'item.completed' and item.get('type') == 'agent_message':
            replies.append(item.get('text', ''))
    response = '\n'.join(replies)
    limit = is_quota_limit_text(proc.stderr + proc.stdout)
    return dict(ok=proc.returncode == 0 and not failed and not limit and bool(response) and bool(conversation_id),
                returncode=proc.returncode, conversation_id=conversation_id,
                response=response, limit_hit=limit, raw_stderr=proc.stderr,
                raw_stdout=proc.stdout)


BRAIN_RUNNERS = {'agy': lambda *args, **kwargs: invoke_agy(*args, **kwargs),
                 'codex': invoke_codex}

_PROJECT_ALIASES: dict[str, str] = {
    "cookie-run": "cookierun-bot",
    "cookierun": "cookierun-bot",
    "expert-advisor": "mooniex-expertadvisor",
    "expertadvisor": "mooniex-expertadvisor",
    "ea": "mooniex-expertadvisor",
    "lumina-skies": "mooniex-bedrock",
    "luminaskies": "mooniex-bedrock",
    "bedrock": "mooniex-bedrock",
    "comfy-runpod": "comfy-runpod-worker",
    "comfyrunpod": "comfy-runpod-worker",
}


def resolve_project_repo_dir(project: str | None) -> Path | None:
    """Resolve the local checkout directory for `project` on this host if it exists."""
    if not project:
        return None
    clean = (project or "").strip()
    resolved_key = _PROJECT_ALIASES.get(clean.lower(), clean)
    try:
        from lib import config
        host = ph_state.host_name()
        for entry in config.projects():
            key = (entry.get("key") or "").strip()
            name = (entry.get("name") or "").strip()
            if key.lower() == resolved_key.lower() or name.lower() == clean.lower():
                paths = entry.get("paths") or {}
                candidate = paths.get(host) or entry.get("path")
                if candidate and Path(candidate).is_dir():
                    return Path(candidate)
    except Exception:
        pass
    return None


def run_turn(
    *,
    ph_id: str,
    message: str,
    project: str | None = None,
    lane: str | None = None,
    owner: str | None = None,
    preferred_model: str | None = None,
    force_fallback: bool = False,
    add_dirs: list[Path] | None = None,
    brains_dir: Path | None = None,
    snapshot_path: Path | None = None,
    timeout_s: int = TURN_TIMEOUT_S,
    agy_bin: str | None = None,
    brain: str = 'agy',
) -> dict[str, Any]:
    """Run a persistent planning turn, falling back to Codex on AGY quota exhaustion."""
    if brain not in BRAIN_RUNNERS:
        raise ValueError(f'unknown PH brain: {brain}')
    state = load_brain_state(ph_id, brains_dir=brains_dir)
    if project:
        state["project"] = project
    elif not state.get("project"):
        state["project"] = ph_id
    if lane:
        state["lane"] = lane.lower()
    if owner:
        state["owner"] = owner

    effective_dirs = list(add_dirs) if add_dirs is not None else [ROOT]
    if add_dirs is None or (len(effective_dirs) == 1 and effective_dirs[0] == ROOT):
        proj_dir = resolve_project_repo_dir(state.get("project"))
        if proj_dir and proj_dir not in effective_dirs:
            effective_dirs.append(proj_dir)

    conv_id = state.get("conversation_id")
    is_first_turn = not bool(conv_id)
    prompt = (
        build_initial_prompt(
            ph_id=state["ph_id"],
            project=state["project"],
            lane=state.get("lane") or "cto",
            owner=state.get("owner"),
            message=message,
            previous_summary=state.get("last_summary"),
            relocated_from_host=state.get("relocated_from_host"),
        )
        if is_first_turn
        else message
    )

    effective_preferred = preferred_model
    if not effective_preferred and state.get("fallback_events") and state.get("active_model") in MODEL_TO_BUCKET:
        effective_preferred = state["active_model"]
    models_to_try = select_model_chain(
        effective_preferred,
        snapshot_path=snapshot_path,
        force_fallback=force_fallback,
    ) + ['codex'] if brain == 'agy' else ['codex']
    attempted: list[dict[str, Any]] = []
    last_res: dict[str, Any] = {}
    telemetry_warning = {}

    for idx, model in enumerate(models_to_try):
        runner = brain
        if model == 'codex':
            if brain == 'agy' and not all(a['limit_hit'] for a in attempted):
                break
            check_codex_budget(snapshot_path)
            runner = 'codex'
            model = (preferred_model if brain == 'codex' else None) or codex_config()[0]
            conv_id = state.get('codex_session_id')
            prompt = build_initial_prompt(ph_id=ph_id, project=state['project'],
                lane=state.get('lane') or 'cto', owner=state.get('owner'),
                message=f"Previous brain summary: {state.get('last_summary', '')}\n{message}")
        fallback_triggered = idx > 0 or (force_fallback and model != PRIMARY_MODEL)
        with ph_state.turn(session_id=ph_id, project=state['project'],
                           warning_state=telemetry_warning,
                           brain=runner, model=model, doing=message,
                           owner=state.get('owner'), lane=state.get('lane') or 'cto') as outcome:
            guard = _IN_TURN.set(True)
            try:
                res = BRAIN_RUNNERS[runner](
                    prompt, model=model, conversation_id=conv_id,
                    add_dirs=effective_dirs, timeout_s=timeout_s, agy_bin=agy_bin,
                )
                code = res.get('returncode')
                outcome.update(returncode=code if code is not None else
                               (124 if res.get('timed_out') else 1))
            finally:
                _IN_TURN.reset(guard)
        # Preserve conversation_id when the turn succeeded or when continuing an established thread.
        # On turn 1 (turn_count == 0), if the first model failed before producing any output, keep
        # conv_id only if the next model needs it or let it mint/resume cleanly.
        if res.get("conversation_id") and (res.get("ok") or state.get("turn_count", 0) > 0 or conv_id):
            conv_id = res["conversation_id"]
            state['codex_session_id' if runner == 'codex' else 'conversation_id'] = conv_id
            save_brain_state(state, brains_dir=brains_dir)
        elif res.get("conversation_id") and runner == 'agy':
            # Still pass the minted conversation_id within this turn if needed, and save on success
            conv_id = res["conversation_id"]
            state['conversation_id'] = conv_id
            save_brain_state(state, brains_dir=brains_dir)
        attempted.append({
            "model": model,
            "ok": res["ok"],
            "limit_hit": res["limit_hit"],
            "returncode": res["returncode"],
            "error": ' '.join((res.get('raw_stderr') or res.get('raw_stdout') or res.get('response') or '').split())[:120],
        })
        if res.get("limit_hit") and (brains_dir is None or os.environ.get("ORG_SHARED_QUOTA_SYNC") == "1"):
            record_shared_model_cooldown(model)
        last_res = res
        if res.get("timed_out"):
            # A timeout is not a quota limit: the next model would hang as long again.
            save_brain_state(state, brains_dir=brains_dir)
            return {
                "ok": False,
                "ph_id": state["ph_id"],
                "project": state["project"],
                "lane": state.get("lane"),
                "conversation_id": conv_id,
                "model_used": model,
                "fallback_triggered": fallback_triggered,
                "attempts": attempted,
                "response": res["response"],
                "claude_code_tokens_used": 0,
            }
        if res["ok"]:
            previous_model = state.get("active_model")
            if fallback_triggered or (previous_model and previous_model != model):
                from_model = attempted[0]["model"] if idx > 0 else (previous_model or models_to_try[0])
                state.setdefault("fallback_events", []).append({
                    "ts": _now_iso(),
                    "from_model": from_model,
                    "to_model": 'codex' if runner == 'codex' else model,
                    "reason": attempted[0].get("limit_hit") or ("forced_fallback" if force_fallback else "quota_gate_or_error"),
                })
            state["active_model"] = model
            state["turn_count"] = int(state.get("turn_count") or 0) + 1
            summary_line = (res["response"] or "").strip().splitlines()[0][:200] if res.get("response") else ""
            state["last_summary"] = summary_line
            save_brain_state(state, brains_dir=brains_dir)
            return {
                "ok": True,
                "ph_id": state["ph_id"],
                "project": state["project"],
                "lane": state["lane"],
                "conversation_id": conv_id,
                "model_used": model,
                "bucket_used": 'codex' if runner == 'codex' else MODEL_TO_BUCKET.get(model, "agy"),
                "turn_count": state["turn_count"],
                "fallback_triggered": fallback_triggered,
                "attempts": attempted,
                "response": res["response"],
                "claude_code_tokens_used": 0,
            }

    summary = '; '.join(f"{a['model']} rc={a['returncode']} limit={a['limit_hit']} err={a['error'][:80]}"
                        for a in attempted)
    raise RuntimeError(
        f"brain chain {models_to_try} failed for PH {ph_id}; "
        # Every model's own result: the last model's 429 once hid an earlier non-quota failure.
        f"attempts: {summary}; "
        f"last error: rc={last_res.get('returncode')} limit={last_res.get('limit_hit')} "
        f"error={' '.join((last_res.get('raw_stderr') or last_res.get('raw_stdout') or last_res.get('response') or '').split())[:200]}"
    )


def delegate_from_ph(
    *,
    ph_id: str,
    project: str,
    role: str,
    title: str,
    brief: str,
    touches: list[str] | None = None,
    host: str | None = None,
    runner: str = "agy",
    runner_model: str = FALLBACK_MODEL,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create and dispatch a worker task from an AGY PH without using Claude Code."""
    state = load_brain_state(ph_id)
    resolved_project = _PROJECT_ALIASES.get((project or "").strip().lower(), project)
    resolved_host = (host or "").strip() or ("winbox" if resolved_project == "cookierun-bot" else None)
    if role == "browser_operator" and runner == "agy":
        brief = ensure_browser_agy_brief(brief)
        if runner_model == FALLBACK_MODEL:
            runner_model = "gemini-3.8-flash-high"
    touches_json = json.dumps(touches or [])
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "ph_id": ph_id,
            "project": resolved_project,
            "host": resolved_host,
            "role": role,
            "title": title,
            "runner": runner,
            "runner_model": runner_model,
            "touches": touches or [],
            "ph_conversation_id": state.get("conversation_id"),
            "claude_code_tokens_used": 0,
        }
    from lib import db, org_tools_registry
    from tools import delegate as delegate_module

    # A PH owns its tasks as project_head-<id> (its launcher unsets CTO_SESSION_ID too).
    os.environ.pop("CTO_SESSION_ID", None)
    os.environ["CXO_ROLE"] = "project_head"
    os.environ["CXO_SESSION_ID"] = ph_id
    os.environ["ORG_PH_PROJECT"] = resolved_project
    os.environ["ORG_PH_LANE"] = state.get("lane") or "cto"

    task_id = org_tools_registry.dispatch_sync(
        "create_task",
        project=resolved_project,
        role=role,
        title=title,
        description=brief,
        depends_on="",
        touches=touches_json,
        host=resolved_host or "",
    ).strip()
    if not re.fullmatch(r"task-[0-9a-f]{8}", task_id):
        raise ValueError(f"create_task refused: {task_id}")
    db.set_fields(task_id, runner=runner, runner_model=runner_model, host=resolved_host)
    row = asyncio.run(delegate_module.delegate_task(task_id, host=resolved_host))
    return {
        "ok": True,
        "task_id": task_id,
        "ph_id": ph_id,
        "project": resolved_project,
        "host": (row or {}).get("host") or resolved_host,
        "status": (row or {}).get("status"),
        "pid": (row or {}).get("pid"),
        "branch": (row or {}).get("branch"),
        "delegate_log": (row or {}).get("delegate_log"),
        "role": role,
        "runner": (row or {}).get("runner") or runner,
        "runner_model": (row or {}).get("runner_model") or runner_model,
        "claude_code_tokens_used": 0,
    }


def list_brains(brains_dir: Path | None = None, snapshot_path: Path | None = None) -> dict[str, Any]:
    base = Path(brains_dir or BRAINS_DIR)
    brains = []
    if base.is_dir():
        for p in sorted(base.glob("*.json")):
            try:
                brains.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    buckets = load_quota_buckets(snapshot_path)
    quota_summary = {
        k: {
            "weekly_remaining": v.get("weekly_remaining"),
            "daily_remaining": v.get("daily_remaining"),
        }
        for k, v in buckets.items()
        if isinstance(v, dict)
    }
    return {
        "brains": brains,
        "quotas": quota_summary,
        "recommended_model": select_model_chain(snapshot_path=snapshot_path)[0],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_turn = sub.add_parser("turn", help="Run a turn on a Project Head's persistent AGY brain")
    p_turn.add_argument("--ph", required=True, help="PH session id (e.g. 7cf12345)")
    p_turn.add_argument("--project", help="Project name (e.g. LungNote)")
    p_turn.add_argument("--lane", default="cto", help="Lane (cto/cmo/cgo/cfo/coo)")
    p_turn.add_argument("--owner", help="Owner C-level session (e.g. cto-d405e3e2)")
    p_turn.add_argument("--message", "-m", required=True, help="Prompt or message for this turn")
    p_turn.add_argument("--model", help="Override primary AGY model")
    p_turn.add_argument('--brain', choices=tuple(BRAIN_RUNNERS), default='agy')
    p_turn.add_argument("--force-fallback", action="store_true", help="Force fallback to Gemini 4 Argon High on the same conversation")
    p_turn.add_argument("--add-dir", action="append", default=[], help="Additional directory to grant AGY access to")
    p_turn.add_argument("--json", action="store_true", help="Emit JSON output")

    p_status = sub.add_parser("status", help="Show active PH brains and AGY quota status")
    p_status.add_argument("--ph", help="Filter to a single PH id")
    p_status.add_argument("--json", action="store_true", help="Emit JSON output")

    p_wait = sub.add_parser('wait', help='Record a worker task or card wait (zero model calls)')
    p_wait.add_argument('--ph', required=True)
    p_wait.add_argument('--ref', required=True)
    sub.add_parser('observe', help='Sample this host PH panes/PIDs into the hub (zero model calls)')

    p_del = sub.add_parser("delegate", help="Create and dispatch an AGY worker task from a PH brain")
    p_del.add_argument("--ph", required=True)
    p_del.add_argument("--project", required=True)
    p_del.add_argument("--role", required=True)
    p_del.add_argument("--title", required=True)
    p_del.add_argument("--brief", required=True)
    p_del.add_argument("--touches", default="[]", help="JSON array of touched paths")
    p_del.add_argument("--host", default=None, help="Target host (e.g. winbox)")
    p_del.add_argument("--runner", default="agy")
    p_del.add_argument("--runner-model", default=FALLBACK_MODEL)
    p_del.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.cmd == 'wait':
            ph_state.require_hub()
            ph_state.wait(args.ph, args.ref)
            return 0
        if args.cmd == 'observe':
            from tools.run_watch_driver import ph_snapshot
            import time
            return 1 if ph_snapshot(ph_state.host_name(), time.time()).get('error') else 0
        if args.cmd == "turn":
            extra_dirs = [ROOT] + [Path(d) for d in args.add_dir]
            res = run_turn(
                ph_id=args.ph,
                project=args.project,
                lane=args.lane,
                owner=args.owner,
                message=args.message,
                preferred_model=args.model,
                brain=args.brain,
                force_fallback=args.force_fallback,
                add_dirs=extra_dirs,
            )
            if args.json:
                print(json.dumps(res, ensure_ascii=False))
            elif not res.get("ok"):
                # A timed-out turn has no bucket/turn_count; say so instead of a KeyError.
                print(f"[PH#{res['ph_id']} | brain turn FAILED: model={res.get('model_used')} timed out | "
                      f"conv={res.get('conversation_id')}]\n{res.get('response') or ''}")
                return 1
            else:
                fb = f" [FALLBACK -> {res['model_used']}]" if res.get("fallback_triggered") else ""
                print(
                    f"[PH#{res['ph_id']} | model={res['model_used']} ({res['bucket_used']}){fb} | "
                    f"conv={res['conversation_id']} | turn={res['turn_count']} | claude_code=0 tok]\n"
                    f"{res['response']}"
                )
            return 0

        if args.cmd == "status":
            info = list_brains()
            if args.ph:
                info["brains"] = [b for b in info["brains"] if b.get("ph_id") == args.ph]
            if args.json:
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print(f"Recommended primary brain model: {info['recommended_model']}")
                for k, q in info["quotas"].items():
                    print(f"  Quota {k}: weekly={q['weekly_remaining']} daily={q['daily_remaining']}")
                for b in info["brains"]:
                    print(
                        f"  PH#{b.get('ph_id')} ({b.get('project')}): model={b.get('active_model')} "
                        f"conv={b.get('conversation_id')} turns={b.get('turn_count')}"
                    )
            return 0

        if args.cmd == "delegate":
            touches = json.loads(args.touches)
            res = delegate_from_ph(
                ph_id=args.ph,
                project=args.project,
                role=args.role,
                title=args.title,
                brief=args.brief,
                touches=touches,
                host=args.host,
                runner=args.runner,
                runner_model=args.runner_model,
                dry_run=args.dry_run,
            )
            print(json.dumps(res, ensure_ascii=False))
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ph_brain error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
