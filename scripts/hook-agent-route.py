#!/usr/bin/env python3
"""Audit Agent/Task routing; fail open on internal errors without leaking input."""
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
READ_ONLY = {"Explore", "Plan", "claude-code-guide", "statusline-setup"}


def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    path = Path(os.environ.get("AGENT_ROUTE_PATH", ROOT / "state/reports/agent-route.jsonl"))
    row = dict(ts=datetime.now(timezone.utc).isoformat(), session_id="",
               CXO_ROLE=os.environ.get("CXO_ROLE", ""), subagent_type="",
               has_reason=False, code=None, decision="error_allow")
    try:
        payload = json.load(sys.stdin)
        row["session_id"] = payload.get("session_id", "")
        inp = payload.get("tool_input", {})
        row["subagent_type"] = inp.get("subagent_type", "general-purpose")
        row["description"] = inp.get("description", "")[:60]
        from tools.route import reason_code, REASON_CODES
        import yaml
        row["code"] = reason_code(inp.get("prompt", ""))
        row["has_reason"] = row["code"] is not None
        cfg = yaml.safe_load(Path(os.environ.get(
            "AGENT_ROUTE_CONFIG", ROOT / "config/agent-route.yaml")).read_text())
        if cfg["mode"] not in {"log", "enforce"}:
            raise ValueError("mode")
        deadline = datetime.fromisoformat(str(cfg["enforce_after"]).replace("Z", "+00:00"))
        enforce = cfg["mode"] == "enforce" or datetime.now(timezone.utc) >= deadline
        missing = row["subagent_type"] not in READ_ONLY and not row["has_reason"]
        row["decision"] = "deny" if enforce and missing else "log" if missing else "allow"
        append(path, row)
        if row["decision"] == "deny":
            print("Use delegate_task (the router picks Codex/AGY first), or start the prompt with "
                  "override: <reason_code> — <why>; valid codes: " + ", ".join(REASON_CODES), file=sys.stderr)
            return 2
    except Exception as exc:
        row.update(decision="error_allow", error=type(exc).__name__)
        try:
            append(path, row)
        except Exception:
            print("agent-route: audit write failed; allowing", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
