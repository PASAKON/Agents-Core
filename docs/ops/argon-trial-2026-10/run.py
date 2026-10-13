"""Run one runner on one job of the Argon trial, in a clean worktree, and keep its diff.

    python3 run.py --job D2 --runner argon|sonnet

The worktree is cut once per repo from that repo's origin/main (recorded in DATA/bases.json),
reset to that base before every run, and reset again after the diff is saved, so both runners
start from identical files. A run is refused while `free -m` shows < 1 GB available
(one worker at a time on the 8 GB box).

argon  = agy 1.3.4 headless, --model gemini-4-argon-high, --mode accept-edits (file edits only).
sonnet = claude -p --model claude-sonnet-5-5 --effort high (the Sonnet worker standard), tools
         Read/Edit/Write/Glob/Grep only, no MCP, project hooks off (--setting-sources user).
Per run it records wall minutes, tokens, exit code, and the quota meters before and after
(agy /usage for both groups; /opt/claude-usage-monitor/usage.json plus the CLI's own
rate_limit_event for Claude).
"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from jobs import CONTRACT, JOBS_BY_ID

DATA = Path(os.environ.get("ARGON_DATA", "/opt/MoonieXHQ/Agents/Core/state/argon-trial-2026-10"))
WT_ROOT = Path(os.environ.get("ARGON_WT", "/tmp/claude-0/-opt-MoonieXHQ-Agents-Core/381826cd-bc49-487d-a946-08e0d1a121af/scratchpad/wt"))
AGY = str(Path.home() / ".local/bin/agy")
ARGON_MODEL = "gemini-4-argon-high"
SONNET_MODEL = "claude-sonnet-5-5"
TIMEOUT = 45 * 60
# Agents-Core's tracked files weigh ~1 GB and the box had 7.9 GB free: its worktree checks out only
# what the jobs read (both runners see the same view). Root files always come with cone mode.
SPARSE = {"Agents-Core": ["tools", "tests", "lib", "config", "docs/runbooks", "docs/ops/thai-inventory-2026-10-14",
                          ".claude/skills/session-worktree"]}


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def mem_available_mb() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return 0


def agy_usage() -> dict:
    p = sh([AGY, "-p", "/usage", "--output-format", "json"], timeout=120)
    try:
        d = json.loads(p.stdout)["command"]["data"]
        return {b["id"]: round(b["remaining_fraction"] * 100, 3) for g in d["groups"] for b in g["buckets"]}
    except (ValueError, KeyError, TypeError):
        return {"error": (p.stdout or p.stderr)[-300:]}


def claude_usage() -> dict:
    try:
        d = json.loads(Path("/opt/claude-usage-monitor/usage.json").read_text())
        return {"at": d.get("generated_at"), "five_hour_used": d["five_hour"]["utilization"],
                "seven_day_used": d["seven_day"]["utilization"]}
    except (OSError, ValueError, KeyError, TypeError) as e:
        return {"error": type(e).__name__}


def meters() -> dict:
    return {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "agy": agy_usage(), "claude": claude_usage()}


def bases() -> dict:
    f = DATA / "bases.json"
    return json.loads(f.read_text()) if f.exists() else {}


def worktree(job: dict) -> Path:
    """The repo's one trial worktree, reset to the recorded base."""
    b = bases()
    wt = WT_ROOT / job["repo"]
    if job["repo"] not in b:
        sh(["git", "-C", job["src"], "fetch", "-q", "origin"])
        b[job["repo"]] = sh(["git", "-C", job["src"], "rev-parse", "origin/main"]).stdout.strip()
        (DATA / "bases.json").write_text(json.dumps(b, indent=1))
    base = b[job["repo"]]
    if not wt.exists():
        WT_ROOT.mkdir(parents=True, exist_ok=True)
        sparse = SPARSE.get(job["repo"])
        p = sh(["git", "-C", job["src"], "worktree", "add", "-q", "--detach"]
               + (["--no-checkout"] if sparse else []) + [str(wt), base])
        if p.returncode:
            raise SystemExit(f"worktree add failed: {p.stderr}")
        if sparse:
            sh(["git", "-C", str(wt), "sparse-checkout", "set", "--cone"] + sparse)
            sh(["git", "-C", str(wt), "checkout", "-q", "--detach", base])
    reset(wt, base)
    nm = Path(job["src"]) / "node_modules"
    if nm.is_dir() and not (wt / "node_modules").exists():
        (wt / "node_modules").symlink_to(nm)
    return wt


def reset(wt: Path, base: str) -> None:
    sh(["git", "-C", str(wt), "checkout", "-q", "--detach", base])
    sh(["git", "-C", str(wt), "reset", "-q", "--hard", base])
    sh(["git", "-C", str(wt), "clean", "-qfd", "-e", "node_modules"])


def capture(wt: Path, base: str) -> tuple[str, str]:
    """(diff of everything but REPORT.md and run logs, REPORT.md text)."""
    rep = wt / "REPORT.md"
    report = rep.read_text(errors="replace") if rep.exists() else ""
    sh(["git", "-C", str(wt), "add", "-A", "--", ".", ":!REPORT.md", ":!node_modules"])
    diff = sh(["git", "-C", str(wt), "diff", "--cached", "--binary", base]).stdout
    sh(["git", "-C", str(wt), "reset", "-q"])
    return diff, report


def run_argon(prompt: str, wt: Path) -> dict:
    p = sh([AGY, "-p", prompt, "--model", ARGON_MODEL, "--mode", "accept-edits", "--add-dir", str(wt),
            "--output-format", "json"], cwd=wt, stdin=subprocess.DEVNULL, timeout=TIMEOUT)
    rec = {"exit": p.returncode, "stderr_tail": p.stderr[-1500:]}
    try:
        out = json.loads(p.stdout)
        u = out.get("usage") or {}
        rec.update(status=out.get("status"), error=out.get("error"), text=(out.get("response") or "")[-3000:],
                   num_turns=out.get("num_turns"), conversation_id=out.get("conversation_id"),
                   input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"),
                   thinking_tokens=u.get("thinking_tokens"), cache_read=u.get("cache_read_tokens"))
    except ValueError:
        rec["stdout_tail"] = p.stdout[-3000:]
    return rec


def run_sonnet(prompt: str, wt: Path) -> dict:
    p = sh(["claude", "-p", "--model", SONNET_MODEL, "--effort", "high", "--output-format", "stream-json",
            "--verbose", "--no-session-persistence", "--strict-mcp-config", "--setting-sources", "user",
            "--tools", "Read,Edit,Write,Glob,Grep", "--permission-mode", "acceptEdits"],
           input=prompt, cwd=wt, timeout=TIMEOUT)
    rec = {"exit": p.returncode, "stderr_tail": p.stderr[-1500:], "served": [], "rate": []}
    for line in p.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            rec["served"].append(ev["message"].get("model"))
        elif ev.get("type") == "rate_limit_event":
            w = ev.get("rate_limit_info", {}).get("unifiedWindows", {})
            rec["rate"].append({k: v.get("utilization") for k, v in w.items()})
        elif ev.get("type") == "result":
            mu = next(iter(ev.get("modelUsage", {}).values()), {})
            rec.update(text=(ev.get("result") or "")[-3000:], is_error=ev.get("is_error"),
                       num_turns=ev.get("num_turns"), api_ms=ev.get("duration_api_ms"),
                       input_tokens=mu.get("inputTokens", 0), output_tokens=mu.get("outputTokens", 0),
                       cache_read=mu.get("cacheReadInputTokens", 0),
                       cache_write=mu.get("cacheCreationInputTokens", 0),
                       thinking_tokens=mu.get("thinkingTokens", 0))
    rec["served"] = sorted(set(m for m in rec["served"] if m))
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--runner", choices=["argon", "sonnet"], required=True)
    ap.add_argument("--tag", default="", help="suffix for a redo, e.g. r1")
    ap.add_argument("--extra", default="", help="file with extra brief text for a redo")
    ap.add_argument("--from-run", default="", help="a redo starts from this earlier run's patch + REPORT.md")
    a = ap.parse_args()
    job = JOBS_BY_ID[a.job]
    out = DATA / "runs" / a.job
    out.mkdir(parents=True, exist_ok=True)
    name = a.runner + (f"-{a.tag}" if a.tag else "")
    # CEO 14 Oct ~03:40 via SomPong: real jobs only; where a Sonnet duplicate would waste quota, Argon runs
    # alone and is scored by the reviewer's pass/redo. Jobs listed in DATA/argon_only get no Sonnet run.
    only = DATA / "argon_only"
    if a.runner == "sonnet" and only.exists() and a.job in only.read_text().split():
        raise SystemExit(f"{a.job}/sonnet skipped: argon-only (CEO 14 Oct)")
    if (out / f"{name}.json").exists():
        raise SystemExit(f"{a.job}/{name} already ran")
    avail = mem_available_mb()
    if avail < 1024:
        raise SystemExit(f"refused: MemAvailable {avail} MB < 1024")
    wt = worktree(job)
    base = bases()[job["repo"]]
    if a.from_run:
        prev = out / f"{a.from_run}.patch"
        p = sh(["git", "-C", str(wt), "apply", "--binary", "--whitespace=nowarn", str(prev)])
        if p.returncode:
            raise SystemExit(f"could not lay in {prev}: {p.stderr}")
        (wt / "REPORT.md").write_text((out / f"{a.from_run}.report.md").read_text())
    brief = job["brief"]
    if a.extra:
        brief += "\n\n" + Path(a.extra).read_text()
    prompt = brief + "\n" + CONTRACT.format(wt=wt)
    rec = {"job": a.job, "runner": a.runner, "tag": a.tag, "base": base, "mem_available_mb": avail,
           "meters_before": meters()}
    t0 = time.time()
    try:
        rec.update(run_argon(prompt, wt) if a.runner == "argon" else run_sonnet(prompt, wt))
    except subprocess.TimeoutExpired:
        rec.update(exit=124, timeout=True)
    rec["minutes"] = round((time.time() - t0) / 60, 2)
    rec["meters_after"] = meters()
    diff, report = capture(wt, base)
    (out / f"{name}.patch").write_text(diff)
    (out / f"{name}.report.md").write_text(report)
    rec["diff_bytes"], rec["has_report"] = len(diff), bool(report)
    (out / f"{name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    reset(wt, base)
    print(json.dumps({k: rec.get(k) for k in ("job", "runner", "exit", "status", "minutes", "diff_bytes",
                                                "has_report", "input_tokens", "output_tokens", "served")}))


if __name__ == "__main__":
    main()
