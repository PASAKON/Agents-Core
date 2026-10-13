"""The CTO's checks on one runner's output: apply its patch to a clean test worktree, run the job's
checks, save the result for the judge, reset.

    python3 test.py --job D3 --runner argon

The test worktree (`test-<repo>`) is separate from the run worktree so a check never races a run.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

import checks
from jobs import JOBS_BY_ID
from run import DATA, SPARSE, WT_ROOT, bases, reset, sh

HERE = Path(__file__).resolve().parent
PY = "/opt/MoonieXHQ/Agents/Core/.venv/bin/python"
NODE22 = "/opt/node-v22/bin"


def test_worktree(job: dict) -> Path:
    base = bases()[job["repo"]]
    wt = WT_ROOT / f"test-{job['repo']}"
    if not wt.exists():
        sparse = SPARSE.get(job["repo"])
        p = sh(["git", "-C", job["src"], "worktree", "add", "-q", "--detach"]
               + (["--no-checkout"] if sparse else []) + [str(wt), base])
        if p.returncode:
            raise SystemExit(p.stderr)
        if sparse:
            sh(["git", "-C", str(wt), "sparse-checkout", "set", "--cone"] + sparse)
            sh(["git", "-C", str(wt), "checkout", "-q", "--detach", base])
    reset(wt, base)
    nm = Path(job["src"]) / "node_modules"
    if nm.is_dir() and not (wt / "node_modules").exists():
        (wt / "node_modules").symlink_to(nm)
    return wt


def cmd(args, wt, timeout=900, env=None):
    e = dict(os.environ, **(env or {}))
    try:
        p = subprocess.run(args, cwd=wt, capture_output=True, text=True, timeout=timeout, env=e)
        out = (p.stdout + p.stderr)
        return {"cmd": " ".join(args)[:200], "exit": p.returncode, "tail": out[-2500:]}
    except subprocess.TimeoutExpired:
        return {"cmd": " ".join(args)[:200], "exit": 124, "tail": "timeout"}


def new_files(patch: str) -> list[str]:
    return re.findall(r"^diff --git a/\S+ b/(\S+)\nnew file mode", patch, re.M)


def changed_files(patch: str) -> list[str]:
    return re.findall(r"^diff --git a/\S+ b/(\S+)$", patch, re.M)


def run_checks(job: dict, wt: Path, patch: str) -> list[dict]:
    jid, out = job["id"], []
    files = changed_files(patch)
    node_env = {"PATH": f"{NODE22}:{os.environ['PATH']}"}
    if jid == "D1":
        out.append(cmd([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_comment_only_check.py"], wt))
        out.append(cmd([PY, str(HERE / "hidden_d1.py"), str(wt)], wt))
    elif jid == "D2":
        out.append(cmd(["git", "grep", "-n", r"Projects/Agents\|/opt/mooniex-agents", "--", ".env.example", "src/"], wt))
        out[-1]["note"] = "done-when: exit 1 (no match) is the pass"
        out.append(cmd(["node", "--check", "src/config.js"], wt, env=node_env))
    elif jid == "D3":
        # Node 22.11 keeps node:sqlite behind a flag (the service runs `node --experimental-sqlite`); vitest
        # 2.1.9 needs min+max workers together on this loaded box (CTO_Gate_MergeChecklist §2).
        tests = sorted({f for f in files if f.startswith("test/") and f.endswith(".test.js")}
                       | {str(p.relative_to(wt)) for p in (wt / "test").glob("run-*.test.js")})
        out.append(cmd(["npx", "vitest", "run", "--minWorkers=1", "--maxWorkers=2", *tests], wt, timeout=1200,
                       env=dict(node_env, NODE_OPTIONS="--experimental-sqlite")))
    elif jid == "D4":
        for f in ("scripts/perf-lunar-vs-flash.js", "scripts/perf-lunar-vs-flash-v2.js"):
            out.append(cmd(["node", "--check", f], wt))
        out.append(cmd(["git", "grep", "-n", r"Projects/mooniex-claudeflow\|Projects/Agents/", "--",
                        "scripts/perf-lunar-vs-flash.js", "scripts/perf-lunar-vs-flash-v2.js", ".env.example"], wt))
        out[-1]["note"] = "exit 1 (no match) is the pass"
    elif jid == "D5":
        out.append(cmd(["bash", "-n", "scripts/deploy.sh"], wt))
        tests = [f for f in files if f.startswith("tests/") and f.endswith(".js")]
        if tests:
            out.append(cmd(["node", "--test", "--test-concurrency=1", *tests], wt))
            pkg = json.loads((wt / "package.json").read_text())
            missing = [t for t in tests if t not in pkg["scripts"]["test"]]
            out.append({"cmd": "package.json test script lists the new test files", "exit": 1 if missing else 0,
                        "tail": f"missing: {missing}" if missing else "all listed"})
        else:
            out.append({"cmd": "new or changed test file", "exit": 1, "tail": "none in the diff"})
        out.append(cmd(["grep", "-n", "sompong-session\\|infisical", "scripts/deploy.sh"], wt))
    elif job["kind"] == "doc":
        f = job["file"]
        old = sh(["git", "-C", job["src"], "show", f"{bases()[job['repo']]}:{f}"]).stdout
        new = (wt / f).read_text()
        r = checks.md_check(old, new, frontmatter_frozen=(jid == "T3"))
        others = [x for x in files if x != f]
        r["other_files_touched"] = others
        out.append({"cmd": "md_check (layout, non-Thai lines, Thai left)", "exit": 0, "tail": json.dumps(r, ensure_ascii=False, indent=1)})
    elif jid == "A1":
        d = wt / "docs/ops/thai-inventory-2026-10-14"
        bm = d / "batches.md"
        if bm.exists():
            r = checks.batch_check((d / "rows.jsonl").read_text(), bm.read_text())
            r["other_files_touched"] = [x for x in files if not x.endswith("batches.md")]
            out.append({"cmd": "batch_check (coverage vs rows.jsonl, batch sizes)", "exit": 0, "tail": json.dumps(r, ensure_ascii=False, indent=1)})
        else:
            out.append({"cmd": "batches.md exists", "exit": 1, "tail": "missing"})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--runner", required=True, help="argon | sonnet | argon-r1 ...")
    a = ap.parse_args()
    job = JOBS_BY_ID[a.job]
    d = DATA / "runs" / a.job
    patch = (d / f"{a.runner}.patch").read_text()
    wt = test_worktree(job)
    res = {"applied": True, "checks": []}
    if patch.strip():
        p = sh(["git", "-C", str(wt), "apply", "--binary", "--whitespace=nowarn", str(d / f"{a.runner}.patch")])
        if p.returncode:
            res = {"applied": False, "apply_error": p.stderr[-800:], "checks": []}
    else:
        res = {"applied": False, "apply_error": "empty diff: the worker changed nothing", "checks": []}
    if res["applied"]:
        res["checks"] = run_checks(job, wt, patch)
    reset(wt, bases()[job["repo"]])
    (d / f"{a.runner}.checks.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for c in res["checks"]:
        print(f"[exit {c['exit']}] {c['cmd']}\n{c['tail'][-1200:]}\n")
    if not res["applied"]:
        print("NOT APPLIED:", res.get("apply_error"))


if __name__ == "__main__":
    main()
