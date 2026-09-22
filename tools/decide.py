"""Typed-decision tool (task-2a29d27e, CEO ruling 2026-09-22).

decide(site, state) answers a fixed-schema question — "what state is this
page in", "which skill fires", "route this message" — from unstructured
text, the way TypeSafe's Jev ("System One" models) does it: a probability
per option, from a declared schema, never free text. See
docs/design/decision-layer.md for the full spec (what a decision site is,
the provider ladder, the budget rule, and the cost rule this replaces —
tools/flow_shoot.py:149 is_refusal_text and
scripts/higgsfield/gen_loop.py's inline state-text checks are the ad hoc
heuristics this generalizes, not code this file imports).

Provider ladder per site's provider_policy:
  rules-only      -> [rules]
  rules-then-llm  -> [rules, jev, openrouter]

`rules` is free and always available. `jev` and `openrouter` are gated off
by default (a decide() call is safe-by-default, matching the org's "ask
before paid API" rule) — `DECIDE_PROVIDER` is the switch an operator sets
to name the HIGHEST paid rung allowed:
  DECIDE_PROVIDER unset / "rules" -> no paid rung runs
  DECIDE_PROVIDER=jev             -> jev only
  DECIDE_PROVIDER=openrouter      -> jev, then openrouter/haiku if jev errors
Jev runs before openrouter/haiku because it is ~25x cheaper on input, free
on output, and returns a calibrated probability distribution (TypeSafe's
Jev on OpenRouter, measured 2026-09-22 — see
research/2026-09-22-typesafe-jev-system-one-models.md); haiku is the
LLM-judgment fallback for when jev errors or is off. `OPENROUTER_API_KEY`
serves both rungs (Jev is served over OpenRouter's alpha decisions API,
not a separate vendor endpoint).

`OPENROUTER_API_KEY`, `DECIDE_PROVIDER`, `DECIDE_BUDGET_USD` and
`DECIDE_JEV_MODEL` are read from os.environ first, then from the
gitignored repo-root .env (lib.config._read_dotenv_var) — a var present
but empty counts as absent, same as unset. The monthly budget gate
(DECIDE_BUDGET_USD) applies to every paid rung, summed across providers.

CLI:
    python tools/decide.py <site> --state-file f.txt [--provider rules|openrouter|jev]
    python tools/decide.py sites
    python tools/decide.py report [--month 2026-09]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `python tools/decide.py ...` finds lib/

from lib import decision_ledger  # noqa: E402
from lib.config import _read_dotenv_var  # noqa: E402

DECISIONS_DIR = ROOT / "config" / "decisions"
PROVIDERS_FILE = DECISIONS_DIR / "_providers.yaml"

MAX_OPTIONS = 255  # Jev's cardinality cap (research/2026-09-22-typesafe-jev-system-one-models.md)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
JEV_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
# typesafe/jev-1.13, served over OpenRouter (config/decisions/_providers.yaml
# openrouter."typesafe/jev-1.13") — measured 2026-09-22, see
# research/2026-09-22-typesafe-jev-system-one-models.md.
DEFAULT_JEV_MODEL = "typesafe/jev-1.13"

LADDERS = {
    "rules-only": ["rules"],
    "rules-then-llm": ["rules", "jev", "openrouter"],
}

# DECIDE_PROVIDER names the HIGHEST paid rung an operator has turned on;
# the value maps to every rung that's allowed to run. Anything else
# (unset, "rules", a typo) allows no paid rung — safe by default.
_PAID_RUNGS_ALLOWED = {
    "jev": {"jev"},
    "openrouter": {"jev", "openrouter"},
}


def _env(name: str) -> str | None:
    """os.environ first, then the gitignored repo-root .env. A value that
    is present but empty (`FOO=`) counts as absent, same as unset —
    matches how a human clearing a var in .env expects it to behave."""
    val = os.environ.get(name)
    if not val:
        val = _read_dotenv_var(name)
    return val or None


def _provider_gate(rung: str) -> None:
    setting = (_env("DECIDE_PROVIDER") or "").strip().lower()
    if rung not in _PAID_RUNGS_ALLOWED.get(setting, set()):
        raise ProviderUnavailable(
            f"{rung} disabled (DECIDE_PROVIDER="
            f"{setting or '(unset)'!r}; set DECIDE_PROVIDER=jev or "
            f"openrouter to enable {rung})"
        )


class DecisionError(Exception):
    """A caller/config mistake — unknown site, bad schema. Never caught by
    the provider ladder; these fail loudly before any ledger row is written."""


class ProviderUnavailable(Exception):
    """A provider cannot run right now (no key, gated off, over budget, no
    verified endpoint). The ladder catches this and falls through."""


@dataclass
class Decision:
    choice: str | None
    probs: dict[str, float]
    provider: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float
    counterfactual_usd: float
    ledger_id: str
    calibrated: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------- site config

def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def _provider_prices() -> dict:
    return _load_yaml(PROVIDERS_FILE)


def list_sites() -> list[str]:
    if not DECISIONS_DIR.exists():
        return []
    return sorted(
        p.stem for p in DECISIONS_DIR.glob("*.yaml") if not p.name.startswith("_")
    )


def load_site(site: str) -> dict:
    path = DECISIONS_DIR / f"{site}.yaml"
    if not path.exists():
        known = ", ".join(list_sites()) or "(none configured)"
        raise DecisionError(f"unknown decision site: {site!r} (known: {known})")
    cfg = _load_yaml(path)
    _validate_site(site, cfg)
    return cfg


def _validate_site(site: str, cfg: dict) -> None:
    if cfg.get("site") and cfg["site"] != site:
        raise DecisionError(
            f"{site}.yaml declares site={cfg['site']!r}, filename says {site!r}"
        )
    if not cfg.get("question"):
        raise DecisionError(f"{site}.yaml missing required field: question")
    policy = cfg.get("provider_policy")
    if policy not in LADDERS:
        raise DecisionError(
            f"{site}.yaml has invalid provider_policy: {policy!r} "
            f"(must be one of {sorted(LADDERS)})"
        )
    options = _resolve_options(cfg)
    if not options:
        raise DecisionError(f"{site}.yaml resolves to zero options")
    if len(options) > MAX_OPTIONS:
        raise DecisionError(
            f"{site}.yaml declares {len(options)} options, over Jev's "
            f"{MAX_OPTIONS}-option cap"
        )


def _resolve_options(cfg: dict) -> list[dict]:
    """Static `options:` list, or a dynamic loader (skill.route.yaml's
    `options_source: skills_dir` — the option set is the live skill list,
    which would drift the moment it was copied statically into a yaml)."""
    if cfg.get("options_source") == "skills_dir":
        return _load_skill_options(ROOT / cfg.get("skills_dir", ".claude/skills"))
    return cfg.get("options") or []


def _read_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _load_skill_options(skills_dir: Path) -> list[dict]:
    out = []
    if not skills_dir.exists():
        return out
    for md in sorted(skills_dir.glob("*/SKILL.md")):
        fm = _read_frontmatter(md)
        if fm.get("name") and fm.get("description"):
            out.append({"id": fm["name"], "meaning": fm["description"]})
    return out[:MAX_OPTIONS]


# Pulls the literal, already-written trigger clause out of a skill's own
# frontmatter description ("Trigger on X, Y, and Z.") rather than us
# re-typing trigger phrases by hand, which would drift from the skill.
_TRIGGER_RE = re.compile(r"trigger on ([^.]*)\.", re.IGNORECASE)
_TRIGGER_STRIP_RE = re.compile(
    r"^(the user (says|asks)|proactively whenever)\s*", re.IGNORECASE
)


def extract_trigger_patterns(description: str) -> list[str]:
    """"Trigger on /foo, X, and Y." -> ["/foo", "X", "Y"]. Empty list if the
    description has no "Trigger on" clause (some skills don't)."""
    m = _TRIGGER_RE.search(description or "")
    if not m:
        return []
    out = []
    for part in re.split(r",| and ", m.group(1)):
        part = part.strip().strip('"').strip("`")
        part = _TRIGGER_STRIP_RE.sub("", part).strip()
        if len(part) >= 3:
            out.append(part)
    return out


def _load_skill_rules(skills_dir: Path) -> list[dict]:
    out = []
    if not skills_dir.exists():
        return out
    for md in sorted(skills_dir.glob("*/SKILL.md")):
        fm = _read_frontmatter(md)
        name, desc = fm.get("name"), fm.get("description")
        if not name or not desc:
            continue
        for pattern in extract_trigger_patterns(desc):
            out.append({"pattern": re.escape(pattern), "option": name})
    return out


def _site_rules(cfg: dict) -> list[dict]:
    if cfg.get("rules_source") == "skill_description":
        return _load_skill_rules(ROOT / cfg.get("skills_dir", ".claude/skills"))
    return cfg.get("rules") or []


# ---------------------------------------------------------------- providers
# Each returns a plain dict (never a Decision — ledger_id/counterfactual_usd
# are stamped once, centrally, in decide()) or raises ProviderUnavailable.
# `rules` alone may also return None, meaning "ran, no rule matched" — a
# normal outcome for a fallthrough policy, not an error.

def _rules_provider(cfg: dict, state_text: str) -> dict | None:
    t0 = time.monotonic()
    for rule in _site_rules(cfg):
        try:
            hit = re.search(rule["pattern"], state_text, re.IGNORECASE)
        except re.error:
            continue
        if hit:
            return {
                "choice": rule["option"], "probs": {rule["option"]: 1.0},
                "provider": "rules", "tokens_in": 0, "tokens_out": 0,
                "latency_ms": (time.monotonic() - t0) * 1000,
                "cost_usd": 0.0, "calibrated": True, "error": None,
            }
    return None


def _openrouter_provider(
    cfg: dict, state_text: str, *, http_post: Callable[..., Any] | None = None,
) -> dict:
    _provider_gate("openrouter")
    api_key = _env("OPENROUTER_API_KEY")
    if not api_key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")

    prices = _provider_prices()["openrouter"]["anthropic/claude-haiku-4-5"]
    options = _resolve_options(cfg)
    est_tokens_in = len(state_text) // 4 + 200  # +schema/system overhead, rough
    est_cost = (est_tokens_in / 1_000_000) * prices["in"]

    budget = float(_env("DECIDE_BUDGET_USD") or 0)
    spent = decision_ledger.month_paid_cost_usd()
    if spent + est_cost > budget:
        raise ProviderUnavailable(
            f"decision_budget_refused: spent=${spent:.4f} + est=${est_cost:.4f} "
            f"> cap=${budget:.4f} (DECIDE_BUDGET_USD)"
        )

    options_desc = "\n".join(f'- {o["id"]}: {o["meaning"]}' for o in options)
    system = (
        f"{cfg['question']}\nOptions:\n{options_desc}\n\n"
        'Answer ONLY with JSON {"choice": <option id>, "confidence": <0-1 float>}. '
        "No other text."
    )
    payload = {
        "model": "anthropic/claude-haiku-4-5",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": state_text},
        ],
    }
    post = http_post or (
        lambda url, **kw: requests.post(url, timeout=20, **kw)
    )
    t0 = time.monotonic()
    resp = post(OPENROUTER_URL, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
    latency_ms = (time.monotonic() - t0) * 1000
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage") or {}
    tokens_in = int(usage.get("prompt_tokens", est_tokens_in))
    tokens_out = int(usage.get("completion_tokens", 0))
    cost_usd = (tokens_in / 1_000_000) * prices["in"] + (tokens_out / 1_000_000) * prices["out"]

    base = {
        "provider": "openrouter", "tokens_in": tokens_in, "tokens_out": tokens_out,
        "latency_ms": latency_ms, "cost_usd": cost_usd, "calibrated": False,
    }
    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        choice = parsed["choice"]
        confidence = float(parsed.get("confidence", 1.0))
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as e:
        return {**base, "choice": None, "probs": {},
                "error": f"openrouter: bad/off-schema response: {e}"}

    valid_ids = {o["id"] for o in options}
    if choice not in valid_ids:
        return {**base, "choice": None, "probs": {},
                "error": f"openrouter: choice {choice!r} not in site options"}

    return {**base, "choice": choice, "probs": {choice: confidence}, "error": None}


def _jev_model_id() -> str:
    return _env("DECIDE_JEV_MODEL") or DEFAULT_JEV_MODEL


def _jev_price_in(model_id: str) -> float:
    table = _provider_prices().get("openrouter", {})
    entry = table.get(model_id) or table.get(DEFAULT_JEV_MODEL) or {}
    return float(entry.get("in", 0.042))


def _response_error_text(resp: Any) -> str:
    """Best-effort extraction of a provider's error message, zod-style or
    otherwise — whatever body it sent back, never a guessed reason."""
    try:
        data = resp.json()
    except Exception:
        return (getattr(resp, "text", "") or "")[:300]
    if isinstance(data, dict):
        err = data.get("error", data)
        if isinstance(err, dict):
            return str(err.get("message") or err)[:300]
        return str(err)[:300]
    return str(data)[:300]


def _jev_provider(
    cfg: dict, state_text: str, *, site: str = "decision",
    http_post: Callable[..., Any] | None = None,
) -> dict:
    """Real endpoint, measured 2026-09-22 (research/2026-09-22-typesafe-
    jev-system-one-models.md): POST https://openrouter.ai/api/alpha/decisions
    with the site's question as a single `choice` question. `usage.cost` is
    exact (provider-reported) and always preferred over the price-table
    estimate when present."""
    _provider_gate("jev")
    api_key = _env("OPENROUTER_API_KEY")
    if not api_key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")

    options = _resolve_options(cfg)
    model_id = _jev_model_id()
    price_in = _jev_price_in(model_id)

    est_tokens_in = len(state_text) // 4 + 200  # +schema/criteria overhead, rough
    est_cost = (est_tokens_in / 1_000_000) * price_in
    budget = float(_env("DECIDE_BUDGET_USD") or 0)
    spent = decision_ledger.month_paid_cost_usd()
    if spent + est_cost > budget:
        raise ProviderUnavailable(
            f"decision_budget_refused: spent=${spent:.4f} + est=${est_cost:.4f} "
            f"> cap=${budget:.4f} (DECIDE_BUDGET_USD)"
        )

    payload = {
        "model": model_id,
        "state": state_text,
        "questions": {
            site: {
                "type": "choice",
                "instructions": cfg["question"],
                "criteria": {o["id"]: o["meaning"] for o in options},
            }
        },
    }
    post = http_post or (lambda url, **kw: requests.post(url, timeout=15, **kw))
    t0 = time.monotonic()
    resp = post(JEV_DECISIONS_URL, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
    latency_ms = (time.monotonic() - t0) * 1000

    status = getattr(resp, "status_code", 200)
    if status != 200:
        raise ProviderUnavailable(f"jev: HTTP {status}: {_response_error_text(resp)}")

    try:
        data = resp.json()
    except Exception as e:  # noqa: BLE001 - any malformed body is a provider failure
        raise ProviderUnavailable(f"jev: non-JSON response: {e}") from e

    answer = (data.get("answers") or {}).get(site) or {}
    probs = answer.get("probabilities")
    choice = answer.get("choice")
    if not probs or choice is None:
        raise ProviderUnavailable(
            f"jev: off-schema response (no answers.{site}.choice/probabilities): "
            f"{_response_error_text(resp) if status != 200 else data}"
        )

    usage = data.get("usage") or {}
    tokens_in = int(usage.get("input_tokens", est_tokens_in))
    tokens_out = int(usage.get("output_tokens", 0))
    cost = usage.get("cost")
    cost_usd = float(cost) if cost is not None else (tokens_in / 1_000_000) * price_in

    return {
        "choice": choice, "probs": dict(probs), "provider": "jev",
        "tokens_in": tokens_in, "tokens_out": tokens_out, "latency_ms": latency_ms,
        "cost_usd": cost_usd, "calibrated": True, "error": None,
        "extra": {"confidence": answer.get("confidence")},
    }


_PROVIDER_NAMES = ("rules", "openrouter", "jev")


# ------------------------------------------------------------- counterfactual

def _counterfactual_usd(cfg: dict, state_chars: int) -> tuple[float, str]:
    cf = cfg.get("counterfactual") or {}
    images = cf.get("images", 0)
    tokens_out = cf.get("big_model_tokens_out", 0)
    extra_chars = cf.get("extra_input_chars", 0)
    prices = _provider_prices()["counterfactual"]["claude-fable-5-1"]
    tokens_in = (state_chars + extra_chars) / 4 + images * 814
    usd = (tokens_in / 1_000_000) * prices["in"] + (tokens_out / 1_000_000) * prices["out"]
    extra_note = f" + extra_input_chars={extra_chars}" if extra_chars else ""
    basis = (
        f"ESTIMATE: fable-5.1 counterfactual = (state_chars={state_chars}"
        f"{extra_note})/4 + images={images}*814 tokens_in, "
        f"tokens_out={tokens_out}, @ ${prices['in']}/${prices['out']} per MTok "
        f"(config/decisions/_providers.yaml, asof {prices.get('asof', '?')})"
    )
    return usd, basis


# ---------------------------------------------------------------------- decide

def decide(
    site: str,
    state: str | dict,
    *,
    provider: str | None = None,
    _http_post: Callable[..., Any] | None = None,
) -> Decision:
    """Answer `site`'s typed question from `state`. Always writes exactly
    one ledger row (lib/decision_ledger.py), whatever the outcome —
    including a refused/failed call, so nothing is lost silently.

    `provider` forces one rung of the ladder (used by the CLI's
    --provider flag and by tests); omit it to run the site's declared
    provider_policy ladder in order.
    """
    cfg = load_site(site)

    state_text = state if isinstance(state, str) else json.dumps(state, sort_keys=True)
    max_chars = cfg.get("max_state_chars")
    if max_chars:
        state_text = state_text[:max_chars]

    if provider:
        if provider not in _PROVIDER_NAMES:
            raise DecisionError(f"unknown provider: {provider!r} (one of {_PROVIDER_NAMES})")
        ladder = [provider]
    else:
        ladder = LADDERS[cfg["provider_policy"]]

    result: dict | None = None
    errors: list[str] = []
    last_provider = ladder[0] if ladder else "none"
    for name in ladder:
        last_provider = name
        try:
            if name == "rules":
                r = _rules_provider(cfg, state_text)
            elif name == "openrouter":
                r = _openrouter_provider(cfg, state_text, http_post=_http_post)
            else:  # jev
                r = _jev_provider(cfg, state_text, site=site, http_post=_http_post)
        except ProviderUnavailable as e:
            errors.append(f"{name}: {e}")
            continue
        if r is None:
            errors.append(f"{name}: no rule matched")
            continue
        # A provider that RAN (even with choice=None, e.g. bad JSON) stops
        # the ladder here — falling through to the next paid provider would
        # silently spend twice for one decision.
        result = r
        break

    if result is None:
        result = {
            "choice": None, "probs": {}, "provider": last_provider,
            "tokens_in": 0, "tokens_out": 0, "latency_ms": 0.0, "cost_usd": 0.0,
            "calibrated": False, "error": "; ".join(errors) or "no provider available",
        }

    counterfactual_usd, counterfactual_basis = _counterfactual_usd(cfg, len(state_text))
    ledger_id = uuid.uuid4().hex[:16]
    row = {
        "ledger_id": ledger_id,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site": site,
        "provider": result["provider"],
        "choice": result["choice"],
        "probs": result["probs"],
        "calibrated": result.get("calibrated", False),
        "tokens_in": result["tokens_in"],
        "tokens_out": result["tokens_out"],
        "cost_usd": result["cost_usd"],
        "latency_ms": result["latency_ms"],
        "state_chars": len(state_text),
        "counterfactual_usd": counterfactual_usd,
        "counterfactual_basis": counterfactual_basis,
        "session_id": os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID"),
        "task_id": os.environ.get("WORKER_TASK_ID"),
        "error": result.get("error"),
        "extra": result.get("extra"),
    }
    decision_ledger.append(row)

    return Decision(
        choice=result["choice"],
        probs=result["probs"],
        provider=result["provider"],
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        latency_ms=result["latency_ms"],
        cost_usd=result["cost_usd"],
        counterfactual_usd=counterfactual_usd,
        ledger_id=ledger_id,
        calibrated=result.get("calibrated", False),
        error=result.get("error"),
    )


# --------------------------------------------------------------------- report

def report_text(month: str | None = None) -> str:
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    summary = decision_ledger.summarize_month(month)
    header = f"decision report {month} (counterfactual_usd is an ESTIMATE, see config/decisions/_providers.yaml)"
    if not summary:
        return f"{header}\n(no decisions logged this month)"
    cols = ["site", "calls", "provider_mix", "tokens_in", "tokens_out", "cost_usd",
            "counterfactual_usd", "saved_usd"]
    lines = [header, "\t".join(cols)]
    for site in sorted(summary):
        s = summary[site]
        mix = ",".join(f"{k}:{v}" for k, v in sorted(s["provider_mix"].items()))
        lines.append("\t".join(str(x) for x in [
            site, s["calls"], mix, s["tokens_in"], s["tokens_out"],
            f"{s['cost_usd']:.4f}", f"{s['counterfactual_usd']:.4f}", f"{s['saved_usd']:.4f}",
        ]))
    return "\n".join(lines)


# ------------------------------------------------------------------------ CLI

def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="tools/decide.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sites", help="list declared decision sites")

    p_report = sub.add_parser("report", help="per-site rollup for a month")
    p_report.add_argument("--month", default=None, help="YYYY-MM, default current month")

    p_decide = sub.add_parser("decide", help=argparse.SUPPRESS)
    p_decide.add_argument("site")
    p_decide.add_argument("--state-file", required=True)
    p_decide.add_argument("--provider", choices=_PROVIDER_NAMES, default=None)

    # Bare `python tools/decide.py <site> --state-file f` (no `decide`
    # subcommand keyword) per the task's CLI spec — reroute here.
    if argv and argv[0] not in ("sites", "report", "decide", "-h", "--help"):
        argv = ["decide", *argv]

    args = parser.parse_args(argv)

    if args.cmd == "sites":
        for s in list_sites():
            print(s)
        return 0

    if args.cmd == "report":
        print(report_text(args.month))
        return 0

    state_text = Path(args.state_file).read_text()
    d = decide(args.site, state_text, provider=args.provider)
    print(json.dumps(d.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
