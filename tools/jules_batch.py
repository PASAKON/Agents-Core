#!/usr/bin/env python3
"""Minimal Jules batch runner — create sessions from brief files, poll, dump diffs.

Thin on purpose: it exists so the 2026-09-23 ten-task A/B could start the same
hour. The full client with review gates and tests is itself one of the ten
tasks (Jules builds tools/jules.py); if that passes review, this file retires.

Key: ~/.config/mooniex/jules.env (JULES_API_KEY) — read at runtime, never printed.

    tools/jules_batch.py create --batch b1 --task T01 --arm A --repo Agents-Core \
        --title "..." --brief state/jules/briefs/T01-A.md
    tools/jules_batch.py status --batch b1              # one line per session: state + PR url
    tools/jules_batch.py diff   --session <id> [--out f]  # cumulative unidiff from activities
    tools/jules_batch.py report --session <id>          # agent messages (questions, final report)
    tools/jules_batch.py list                           # recent sessions on the account

Ledger: state/jules/<batch>.jsonl — one JSON object per created session:
    {"batch","task","arm","repo","session","title","created_at"}   created_at = ISO-8601 UTC
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://jules.googleapis.com/v1alpha"
ROOT = Path(__file__).resolve().parent.parent
LEDGER_DIR = ROOT / "state" / "jules"
KEY_FILE = Path.home() / ".config/mooniex/jules.env"


def key() -> str:
    for line in KEY_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line.startswith("JULES_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit(f"JULES_API_KEY not found in {KEY_FILE}")


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        BASE + path, method=method,
        headers={"X-Goog-Api-Key": key(), "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:400]}")


def ledger(batch: str) -> list[dict]:
    p = LEDGER_DIR / f"{batch}.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def cmd_create(a) -> None:
    prompt = Path(a.brief).read_text()
    body = {
        "prompt": prompt, "title": a.title,
        "sourceContext": {"source": f"sources/github/PASAKON/{a.repo}",
                          "githubRepoContext": {"startingBranch": a.branch}},
        "automationMode": "AUTO_CREATE_PR", "requirePlanApproval": False,
    }
    s = call("POST", "/sessions", body)
    sid = s["name"].split("/")[-1]
    rec = {"batch": a.batch, "task": a.task, "arm": a.arm, "repo": a.repo, "session": sid,
           "title": a.title, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_DIR / f"{a.batch}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False))


def cmd_status(a) -> None:
    for rec in ledger(a.batch):
        s = call("GET", f"/sessions/{rec['session']}")
        prs = [o["pullRequest"].get("url", "") for o in s.get("outputs", []) if o.get("pullRequest")]
        print(f"{rec['task']}-{rec['arm']} {rec['repo']:<22} {s.get('state', '?'):<12} "
              f"{rec['session']} {' '.join(p for p in prs if p)}")


def activities(sid: str) -> list[dict]:
    out, token = [], None
    while True:
        q = f"/sessions/{sid}/activities?pageSize=100" + (f"&pageToken={token}" if token else "")
        d = call("GET", q)
        out += d.get("activities", [])
        token = d.get("nextPageToken")
        if not token:
            return out


def latest_patch(sid: str) -> str | None:
    patch = None
    for act in activities(sid):
        for art in act.get("artifacts", []):
            p = art.get("changeSet", {}).get("gitPatch", {}).get("unidiffPatch")
            if p:
                patch = p          # artifacts are cumulative; keep the last one
    return patch


def cmd_diff(a) -> None:
    patch = latest_patch(a.session)
    if patch is None:
        sys.exit("no changeSet in activities")
    if a.out:
        Path(a.out).write_text(patch)
        print(f"wrote {a.out} ({len(patch)} bytes)")
    else:
        sys.stdout.write(patch)


# Review gate — the script half of jules-ops §4. Applied to BOTH arms of the A/B
# with the allowlist taken from the disciplined brief, so the loose arm is
# measured against the same scope it was never told about.
FORBIDDEN_BASENAMES = ("*.log", "patch_*", "*.patch", "package.json", "package-lock.json",
                       "*.lock", "requirements*.txt")


def _diff_files(patch: str) -> list[str]:
    files = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            head, _, tail = line.partition(" b/")
            if tail:
                files.append(tail.strip())
    return files


def cmd_gate(a) -> None:
    tasks = json.loads(Path(a.tasks).read_text())
    for rec in ledger(a.batch):
        if a.task and rec["task"] != a.task:
            continue
        allow = tasks.get(rec["task"], {}).get("allow", [])
        s = call("GET", f"/sessions/{rec['session']}")
        prs = [o["pullRequest"].get("url", "") for o in s.get("outputs", []) if o.get("pullRequest")]
        patch = latest_patch(rec["session"])
        tag = f"{rec['task']}-{rec['arm']}"
        if patch is None:
            print(f"{tag} {s.get('state', '?'):<12} NO-DIFF  pr={len(prs)}")
            continue
        files = _diff_files(patch)
        viol = []
        for f in files:
            allowed = any(fnmatch.fnmatch(f, g) for g in allow)
            if allow and not allowed:
                viol.append(f"outside-allowlist: {f}")
            if not allowed and any(fnmatch.fnmatch(f.rsplit('/', 1)[-1], g) for g in FORBIDDEN_BASENAMES):
                viol.append(f"forbidden-pattern: {f}")
        if len(patch) > a.max_bytes:
            viol.append(f"too-big: {len(patch)} B > {a.max_bytes}")
        verdict = "GATE-OK  " if not viol else "GATE-FAIL"
        print(f"{tag} {s.get('state', '?'):<12} {verdict} files={len(files)} bytes={len(patch)} pr={len(prs)} {' '.join(prs)}")
        for v in viol:
            print("    ! " + v)
        if a.files:
            for f in files:
                print("    - " + f)


def cmd_report(a) -> None:
    skip = {"name", "id", "createTime", "originator", "artifacts", "sessionId", "description"}
    for act in activities(a.session):
        kinds = [k for k in act if k not in skip]
        text = ""
        for k in kinds:
            v = act[k]
            if isinstance(v, dict):
                for kk in ("message", "agentMessage", "planDescription", "text", "title"):
                    if isinstance(v.get(kk), str):
                        text = v[kk]
                        break
            elif isinstance(v, str):
                text = v
        print(f"--- {act.get('createTime', '')[:19]} {','.join(kinds)} | {act.get('description', '')[:120]}")
        if text:
            print(text[:2500])
        print()


def cmd_list(a) -> None:
    d = call("GET", f"/sessions?pageSize={a.n}")
    for s in d.get("sessions", []):
        print(f"{s.get('createTime', '')[:16]} {s.get('state', '?'):<12} {s['name'].split('/')[-1]} {s.get('title', '')[:80]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("--batch", required=True); c.add_argument("--task", required=True)
    c.add_argument("--arm", required=True); c.add_argument("--repo", required=True)
    c.add_argument("--title", required=True); c.add_argument("--brief", required=True)
    c.add_argument("--branch", default="main")
    c.set_defaults(fn=cmd_create)
    s = sub.add_parser("status"); s.add_argument("--batch", required=True); s.set_defaults(fn=cmd_status)
    d = sub.add_parser("diff"); d.add_argument("--session", required=True); d.add_argument("--out"); d.set_defaults(fn=cmd_diff)
    r = sub.add_parser("report"); r.add_argument("--session", required=True); r.set_defaults(fn=cmd_report)
    l = sub.add_parser("list"); l.add_argument("-n", type=int, default=20); l.set_defaults(fn=cmd_list)
    g = sub.add_parser("gate"); g.add_argument("--batch", required=True); g.add_argument("--task")
    g.add_argument("--tasks", default="docs/ops/jules-ab-2026-09-23/briefs/tasks.json")
    g.add_argument("--max-bytes", type=int, default=65536); g.add_argument("--files", action="store_true")
    g.set_defaults(fn=cmd_gate)
    a = ap.parse_args()
    a.fn(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
