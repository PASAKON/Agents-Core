#!/usr/bin/env python3
"""Claude Code transcript hygiene for the Mac: report, notify, archive, restore.

NOTHING RUNS AUTOMATICALLY EXCEPT --notify (CEO 2026-09-05: manual archive, alert
first). The daily launchd job only sends a summary to the CEO over Telegram
(SomPong) when something needs a decision. A human then runs --archive.

A session = <project>/<uuid>.jsonl + <project>/<uuid>/ (subagents, tool-results,
workflows) + satellites keyed by the uuid under ~/.claude (file-history,
session-env, image-cache, uploads, debug/<uuid>.txt, tasks/session-<uuid8>,
jobs/<uuid8>).

A session is a CANDIDATE when it is not live and one rule matches:
  missing_cwd  project directory is gone (deleted worktree), age > missing_cwd_keep_days
  old          age > keep_days
  big          size > big_mb and age > big_keep_days
Low-disk mode (free < low_disk_gb) uses low_disk_keep_days / low_disk_big_keep_days.
Live = pid in ~/.claude/sessions/<pid>.json alive, or uuid in a running process
argv, or written within grace_hours. keep-list, memory/ and anything outside
~/.claude are never touched.

Modes:
  (none) / --report   dry run; --report prints the candidate table
  --notify            send a summary to the CEO (Telegram via Agents lib, plus a
                      macOS notification); quiet unless a threshold trips or it is
                      the weekly digest day. --force sends regardless.
  --archive           tar.gz each candidate into archive_dir (Google Drive folder),
                      verify the archive, THEN delete the local copy. Manual.
  --restore <uuid>    pull a session back from archive_dir into ~/.claude
  --apply             delete candidates without archiving. Manual, last resort.
  --only a1b2c3d4,... restrict --archive/--apply to these uuid prefixes
Config: ~/.claude/prune-transcripts.json   Log: ~/.claude/logs/prune-transcripts.log
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
PROJECTS = os.path.join(CLAUDE, "projects")
CONFIG_PATH = os.path.join(CLAUDE, "prune-transcripts.json")
LOG_PATH = os.path.join(CLAUDE, "logs", "prune-transcripts.log")
AGENTS_ROOT = "/Users/gob/MoonieXHQ/Agents/Core"
DRIVE_ROOT = "/Users/gob/Library/CloudStorage/GoogleDrive-pass.gob1@gmail.com/ไดรฟ์ของฉัน"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ARGV_RE = re.compile(
    r"(?:--session-id|--resume|-r)[ =]"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)

DEFAULTS = {
    "enabled": True,
    "keep_days": 30,
    "big_mb": 150,
    "big_keep_days": 7,
    "missing_cwd_keep_days": 7,
    "grace_hours": 24,
    "low_disk_gb": 20,
    "low_disk_keep_days": 14,
    "low_disk_big_keep_days": 3,
    "keep": [],
    "archive_dir": os.path.join(DRIVE_ROOT, "Claude-Transcripts"),
    "drive_gate": [
        {"path": "~/Backups", "dest": "Archive/Backups"},
        {"path": "~/Projects/Agents/output", "dest": "Archive/Agents-output"},
    ],
    "notify": {
        "enabled": True,
        "min_free_gb": 20,
        "min_candidates_gb": 2,
        "min_gate_gb": 2,
        "digest_weekday": 0,
        "telegram": True,
        "macos_notification": True,
    },
}


# ----------------------------------------------------------------- helpers
def load_config():
    cfg = json.loads(json.dumps(DEFAULTS))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as fh:
                user = json.load(fh)
            if isinstance(user, dict):
                notify = dict(cfg["notify"])
                notify.update(user.get("notify") or {})
                cfg.update(user)
                cfg["notify"] = notify
        except Exception as exc:
            print("config unreadable, using defaults: %s" % exc, file=sys.stderr)
    cfg["archive_dir"] = os.path.expanduser(cfg["archive_dir"])
    return cfg


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True


def live_uuids():
    live = set()
    for path in glob.glob(os.path.join(CLAUDE, "sessions", "*.json")):
        try:
            with open(path) as fh:
                data = json.load(fh)
        except Exception:
            continue
        sid, pid = data.get("sessionId"), data.get("pid")
        if sid and pid and pid_alive(int(pid)):
            live.add(sid)
    try:
        out = subprocess.run(["ps", "-axo", "command"], capture_output=True,
                             text=True, timeout=30).stdout
    except Exception:
        out = ""
    live.update(ARGV_RE.findall(out))
    return live


def dir_size(path):
    total = 0
    for dirpath, _, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(dirpath, name)).st_size
            except OSError:
                pass
    return total


def path_size(path):
    if os.path.isdir(path) and not os.path.islink(path):
        return dir_size(path)
    try:
        return os.lstat(path).st_size
    except OSError:
        return 0


def session_cwd(jsonl):
    try:
        with open(jsonl, "rb") as fh:
            for i, line in enumerate(fh):
                if i > 50:
                    break
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                cwd = data.get("cwd")
                if cwd:
                    return cwd
    except OSError:
        pass
    return None


def satellites(uuid):
    u8 = uuid[:8]
    return [
        os.path.join(CLAUDE, "file-history", uuid),
        os.path.join(CLAUDE, "session-env", uuid),
        os.path.join(CLAUDE, "image-cache", uuid),
        os.path.join(CLAUDE, "uploads", uuid),
        os.path.join(CLAUDE, "debug", uuid + ".txt"),
        os.path.join(CLAUDE, "tasks", "session-" + u8),
        os.path.join(CLAUDE, "jobs", u8),
    ]


def inventory(live, now):
    sessions, orphans = [], []
    if not os.path.isdir(PROJECTS):
        return sessions, orphans
    for proj in sorted(os.listdir(PROJECTS)):
        pdir = os.path.join(PROJECTS, proj)
        if not os.path.isdir(pdir):
            continue
        jsonls = [f for f in os.listdir(pdir)
                  if f.endswith(".jsonl") and UUID_RE.match(f[:-6])]
        uuids = set(f[:-6] for f in jsonls)
        for name in jsonls:
            uuid = name[:-6]
            path = os.path.join(pdir, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            sub = os.path.join(pdir, uuid)
            parts = [path] + ([sub] if os.path.isdir(sub) else []) + \
                [s for s in satellites(uuid) if os.path.lexists(s)]
            size = sum(path_size(p) for p in parts)
            cwd = session_cwd(path)
            cwd_ok = True if cwd is None else os.path.isdir(cwd)
            sessions.append(dict(
                proj=proj, uuid=uuid, parts=parts, size=size, cwd=cwd,
                mtime=st.st_mtime, age=(now - st.st_mtime) / 86400.0,
                cwd_ok=cwd_ok, live=(uuid in live)))
        for name in os.listdir(pdir):
            dpath = os.path.join(pdir, name)
            if os.path.isdir(dpath) and UUID_RE.match(name) and name not in uuids:
                try:
                    mt = os.stat(dpath).st_mtime
                except OSError:
                    continue
                orphans.append(dict(
                    proj=proj, uuid=name, parts=[dpath], size=dir_size(dpath),
                    age=(now - mt) / 86400.0, live=(name in live), cwd=None))
    return sessions, orphans


def kept(uuid, keep_list):
    return any(uuid == k or uuid.startswith(k) for k in keep_list if k)


def decide(s, cfg, low_disk):
    if s["live"]:
        return None, "live"
    if kept(s["uuid"], cfg["keep"]):
        return None, "keep-list"
    if s["age"] * 24.0 < cfg["grace_hours"]:
        return None, "grace"
    keep_days = cfg["low_disk_keep_days"] if low_disk else cfg["keep_days"]
    big_keep = cfg["low_disk_big_keep_days"] if low_disk else cfg["big_keep_days"]
    if not s["cwd_ok"] and s["age"] > cfg["missing_cwd_keep_days"]:
        return "missing_cwd", None
    if s["age"] > keep_days:
        return "old", None
    if s["size"] > cfg["big_mb"] * 1e6 and s["age"] > big_keep:
        return "big", None
    return None, "kept"


def remove(path):
    real = os.path.abspath(path)
    if not real.startswith(CLAUDE + os.sep) or os.path.basename(real) == "memory":
        raise RuntimeError("refusing to delete: " + path)
    if os.path.isdir(real) and not os.path.islink(real):
        shutil.rmtree(real, ignore_errors=True)
    elif os.path.lexists(real):
        os.remove(real)


def gb(n):
    return n / 1073741824.0


def log(line):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as fh:
        fh.write("%s %s\n" % (stamp, line))


def free_bytes():
    return shutil.disk_usage(HOME).free


# ----------------------------------------------------------------- archive
def archive_session(s, archive_dir):
    """tar.gz the session into archive_dir/<proj>/<uuid>.tar.gz, verify, return path."""
    proj_dir = os.path.join(archive_dir, s["proj"])
    dest = os.path.join(proj_dir, s["uuid"] + ".tar.gz")
    part = dest + ".part"
    os.makedirs(proj_dir, exist_ok=True)
    expected = 0
    with tarfile.open(part, "w:gz") as tf:
        for p in s["parts"]:
            tf.add(p, arcname=os.path.relpath(p, CLAUDE))
            expected += 1
    with tarfile.open(part, "r:gz") as tf:
        names = tf.getnames()
    if not names or os.path.getsize(part) == 0:
        os.remove(part)
        raise RuntimeError("archive came out empty")
    os.replace(part, dest)
    return dest


def restore_session(prefix, archive_dir):
    hits = sorted(glob.glob(os.path.join(archive_dir, "*", prefix + "*.tar.gz")))
    if not hits:
        raise SystemExit("no archive matching %s under %s" % (prefix, archive_dir))
    if len(hits) > 1:
        raise SystemExit("ambiguous prefix, matches:\n  " + "\n  ".join(hits))
    path = hits[0]
    with tarfile.open(path, "r:gz") as tf:
        for m in tf.getmembers():
            parts = m.name.split("/")
            if m.name.startswith("/") or ".." in parts:
                raise SystemExit("unsafe member in archive: " + m.name)
        tf.extractall(CLAUDE)
    uuid = os.path.basename(path)[:-7]
    jsonl = glob.glob(os.path.join(PROJECTS, "*", uuid + ".jsonl"))
    cwd = session_cwd(jsonl[0]) if jsonl else None
    log("RESTORE %s from %s" % (uuid, path))
    print("restored %s" % uuid)
    if cwd:
        print("resume with:  cd %s && claude --resume %s" % (cwd, uuid))


# ----------------------------------------------------------------- notify
def gate_candidates(cfg):
    out = []
    for g in cfg.get("drive_gate") or []:
        p = os.path.expanduser(g["path"])
        if os.path.isdir(p):
            out.append(dict(path=g["path"], dest=g["dest"], size=dir_size(p)))
    return out


def build_message(summary, doomed, gate, cfg, tag=""):
    n = cfg["notify"]
    warn = " ⚠️" if summary["free_gb"] < n["min_free_gb"] else ""
    lines = ["🗄 Disk watch (Mac) %s%s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), tag),
             "Free: %.1f GB%s (เกณฑ์ %d GB)" % (summary["free_gb"], warn, n["min_free_gb"]),
             "Claude transcripts: %d sessions / %.1f GB" % (summary["sessions"], summary["total_gb"])]
    if doomed:
        by = summary["by_rule"]
        lines.append("พร้อม archive: %d sessions = %.2f GB (%s)" % (
            len(doomed), summary["freeing_gb"],
            ", ".join("%s %d" % (k, v["n"]) for k, v in sorted(by.items()))))
        for d in sorted(doomed, key=lambda x: -x["size"])[:5]:
            lines.append("  • %s %.0f MB %.0fd %s" % (d["uuid"][:8], d["size"] / 1048576.0, d["age"], d["rule"]))
    else:
        lines.append("พร้อม archive: ไม่มี")
    if gate:
        lines.append("Drive gate (รอ agent ย้ายตามกฎ drive-archive-gate.md):")
        for g in gate:
            lines.append("  • %s %.1f GB → ไดรฟ์ของฉัน/%s" % (g["path"], gb(g["size"]), g["dest"]))
    lines.append("Manual:")
    lines.append("  python3 ~/.claude/tools/prune_transcripts.py --report")
    lines.append("  python3 ~/.claude/tools/prune_transcripts.py --archive")
    return "\n".join(lines)


def send_telegram(text):
    code = ("import sys, json\n"
            "from lib.telegram_out import send_to_ceo\n"
            "print(json.dumps(send_to_ceo(sys.stdin.read())))\n")
    py = os.path.join(AGENTS_ROOT, ".venv", "bin", "python")
    if not os.path.exists(py):
        return {"ok": False, "reason": "Agents venv missing"}
    try:
        r = subprocess.run([py, "-c", code], cwd=AGENTS_ROOT, input=text,
                           capture_output=True, text=True, timeout=90)
        out = (r.stdout or "").strip().splitlines()
        return json.loads(out[-1]) if out else {"ok": False, "reason": (r.stderr or "no output")[-300:]}
    except Exception as exc:
        return {"ok": False, "reason": str(exc)[:300]}


def macos_notify(title, text):
    try:
        subprocess.run(["osascript", "-e",
                        'display notification "%s" with title "%s"' % (
                            text.replace('"', "'")[:200], title)],
                       timeout=10, capture_output=True)
    except Exception:
        pass


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="print the candidate table (dry run)")
    ap.add_argument("--notify", action="store_true", help="send summary to CEO if thresholds trip")
    ap.add_argument("--force", action="store_true", help="with --notify: send regardless of thresholds")
    ap.add_argument("--archive", action="store_true", help="archive candidates to Drive, then delete local")
    ap.add_argument("--restore", metavar="UUID", help="restore a session from the archive")
    ap.add_argument("--apply", action="store_true", help="delete candidates WITHOUT archiving")
    ap.add_argument("--only", metavar="PREFIXES", help="comma-separated uuid prefixes to act on")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--keep-days", type=float)
    ap.add_argument("--big-mb", type=float)
    ap.add_argument("--big-keep-days", type=float)
    args = ap.parse_args()

    cfg = load_config()
    if args.keep_days is not None:
        cfg["keep_days"] = args.keep_days
    if args.big_mb is not None:
        cfg["big_mb"] = args.big_mb
    if args.big_keep_days is not None:
        cfg["big_keep_days"] = args.big_keep_days
    if not cfg.get("enabled", True):
        print("disabled in %s" % CONFIG_PATH)
        return 0

    if args.restore:
        restore_session(args.restore, cfg["archive_dir"])
        return 0

    now = time.time()
    free_before = free_bytes()
    low_disk = gb(free_before) < float(cfg["low_disk_gb"])
    live = live_uuids()
    sessions, orphans = inventory(live, now)

    doomed, protected = [], {}
    for s in sessions:
        rule, why = decide(s, cfg, low_disk)
        if rule:
            s["rule"] = rule
            doomed.append(s)
        else:
            protected[why] = protected.get(why, 0) + 1
    for o in orphans:
        if not o["live"] and o["age"] > cfg["keep_days"]:
            o["rule"] = "orphan"
            doomed.append(o)
    if args.only:
        prefixes = [p.strip() for p in args.only.split(",") if p.strip()]
        doomed = [d for d in doomed if any(d["uuid"].startswith(p) for p in prefixes)]

    total = sum(s["size"] for s in sessions) + sum(o["size"] for o in orphans)
    freeing = sum(d["size"] for d in doomed)
    by_rule = {}
    for d in doomed:
        r = by_rule.setdefault(d["rule"], [0, 0])
        r[0] += 1
        r[1] += d["size"]
    mode = "ARCHIVE" if args.archive else "DELETE" if args.apply else "NOTIFY" if args.notify else "DRY-RUN"
    summary = dict(
        mode=mode, low_disk=low_disk, free_gb=round(gb(free_before), 2),
        sessions=len(sessions), total_gb=round(gb(total), 2), live=len(live),
        candidates=len(doomed), freeing_gb=round(gb(freeing), 2),
        by_rule={k: dict(n=v[0], gb=round(gb(v[1]), 2)) for k, v in by_rule.items()},
        protected=protected,
        thresholds=dict(keep_days=cfg["keep_days"], big_mb=cfg["big_mb"],
                        big_keep_days=cfg["big_keep_days"],
                        missing_cwd_keep_days=cfg["missing_cwd_keep_days"],
                        grace_hours=cfg["grace_hours"]))

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print("[%s] free %.1f GB%s | %d sessions, %.2f GB | live %d | candidates %d = %.2f GB"
              % (mode, gb(free_before), " LOW-DISK MODE" if low_disk else "",
                 len(sessions), gb(total), len(live), len(doomed), gb(freeing)))
        for k, v in sorted(by_rule.items()):
            print("  %-12s %3d  %.2f GB" % (k, v[0], gb(v[1])))
        print("  protected: " + ", ".join("%s=%d" % kv for kv in sorted(protected.items())))
        if args.report:
            print()
            print("%7s %6s %-11s %-9s %s" % ("MB", "age d", "rule", "uuid", "project"))
            for d in sorted(doomed, key=lambda x: -x["size"])[:args.top]:
                print("%7.0f %6.1f %-11s %-9s %s" % (
                    d["size"] / 1048576.0, d["age"], d["rule"], d["uuid"][:8], d["proj"][:70]))
            if len(doomed) > args.top:
                print("  ... %d more" % (len(doomed) - args.top))

    # ---- notify
    if args.notify:
        n = cfg["notify"]
        gate = gate_candidates(cfg)
        gate_gb = gb(sum(g["size"] for g in gate))
        weekday = datetime.date.today().weekday()
        trip = (summary["free_gb"] < n["min_free_gb"] or summary["freeing_gb"] >= n["min_candidates_gb"]
                or gate_gb >= n["min_gate_gb"] or weekday == n["digest_weekday"])
        if not (n.get("enabled", True) and (trip or args.force)):
            log("NOTIFY quiet free=%.1fGB candidates=%.2fGB gate=%.1fGB" % (summary["free_gb"], summary["freeing_gb"], gate_gb))
            print("notify: nothing tripped, quiet")
            return 0
        text = build_message(summary, doomed, gate, cfg, tag=" [forced]" if args.force else "")
        result = {"ok": False, "reason": "telegram disabled"}
        if n.get("telegram", True):
            result = send_telegram(text)
        if n.get("macos_notification", True):
            macos_notify("Disk watch", "free %.1f GB, %d sessions ready to archive (%.1f GB)" % (
                summary["free_gb"], len(doomed), summary["freeing_gb"]))
        log("NOTIFY sent=%s reason=%s free=%.1fGB candidates=%.2fGB gate=%.1fGB" % (
            result.get("ok"), result.get("reason"), summary["free_gb"], summary["freeing_gb"], gate_gb))
        print("telegram: %s" % json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1

    if not (args.archive or args.apply):
        return 0

    # ---- archive / delete (manual only)
    if args.archive:
        drive = cfg["archive_dir"]
        if not os.path.isdir(os.path.dirname(drive)):
            print("archive_dir parent not mounted: %s — nothing deleted" % os.path.dirname(drive))
            return 2
        os.makedirs(drive, exist_ok=True)
    log("%s start free=%.2fGB low_disk=%s candidates=%d bytes=%.2fGB thresholds=%s" % (
        mode, gb(free_before), low_disk, len(doomed), gb(freeing), json.dumps(summary["thresholds"])))
    done_n, done_bytes = 0, 0
    for d in doomed:
        try:
            dest = archive_session(d, cfg["archive_dir"]) if args.archive else None
            for p in d["parts"]:
                remove(p)
            done_n += 1
            done_bytes += d["size"]
            log("%s %-11s %7.0fMB %5.1fd %s %s%s" % (
                "archived" if dest else "rm", d["rule"], d["size"] / 1048576.0, d["age"],
                d["uuid"], d["proj"], (" -> " + dest) if dest else ""))
            print("%s %s %.0f MB" % ("archived" if dest else "deleted", d["uuid"][:8], d["size"] / 1048576.0))
        except Exception as exc:
            log("FAIL %s %s: %s" % (d["uuid"], d["proj"], exc))
            print("FAIL %s: %s" % (d["uuid"][:8], exc))
    for proj in os.listdir(PROJECTS):
        pdir = os.path.join(PROJECTS, proj)
        try:
            if os.path.isdir(pdir) and not os.listdir(pdir):
                os.rmdir(pdir)
        except OSError:
            pass
    free_after = free_bytes()
    log("%s done n=%d bytes=%.2fGB free=%.2fGB" % (mode, done_n, gb(done_bytes), gb(free_after)))
    print("%s %d sessions, %.2f GB; free now %.1f GB" % (
        "archived" if args.archive else "deleted", done_n, gb(done_bytes), gb(free_after)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
