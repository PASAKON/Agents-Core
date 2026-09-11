# Verified on the live box — use this, do not re-derive it

The CTO ran the remote-orphan identity query against winbox read-only at
2026-09-11 23:2x. It works. Here is exactly what works and what it returned, so
`scripts/session_orphan_report.py` does not have to rediscover any of it.

## The query

Send it as `-EncodedCommand` (UTF-16LE base64), **not** as a quoted string —
PowerShell quoting through `ssh` is a known trap in this repo.

```powershell
Get-CimInstance Win32_Process -Filter "Name = 'claude.exe'" | ForEach-Object {
  $cl = $_.CommandLine
  $m  = [regex]::Match([string]$cl, 'task-[0-9a-f]{8}')
  [pscustomobject]@{
    Pid     = $_.ProcessId
    Task    = $(if ($m.Success) { $m.Value } else { '<none>' })
    Started = $_.CreationDate
  }
}
```

A working Python harness is at
`/private/tmp/claude-501/-Users-gob-Projects-Agents/ff2d2f4c-7947-44a3-ac38-03dccc7eea82/scratchpad/probe_winbox_workers.py`
— read it, reuse its base64 encoding, do not copy its hardcoded paths.

## What it returned (13 live `claude.exe` on winbox)

| pid | task id | in the Mac `tasks.db`? |
|---|---|---|
| 22072 | `task-34f1af72` | **no row — orphan** |
| 16352 | `task-e44097d8` | **no row — orphan** |
| 11 others | `<none>` | not org workers — see below |

## The finding that must shape your report

**Eleven of the thirteen have no task id in their command line at all**, and all
eleven started within ten seconds of each other (9/11 2:51:39–2:51:49 PM). They
are a Claude Code instance and its child processes, **not org workers.**

So the report must classify into three buckets, never two:

1. **known** — task id present and a row exists locally;
2. **orphan** — task id present, no row locally (the two above; they belong to
   the VPS's own separate `tasks.db`, see ADR 0024 in the org wiki);
3. **not ours** — no task id in the command line. **Never list these as
   orphans and never suggest killing them.** A report that calls these eleven
   "stale workers" invites someone to kill the CEO's own Claude session.

The CEO's instruction on the two real orphans is *"ปล่อยไว้ก่อน ทำระบบให้ตรวจจับได้"* —
detect, never kill. The report prints and exits; it takes no action.

## Why the two orphans have no local row

They were created by a CTO session running on the Contabo VPS, which has its own
`/opt/mooniex-agents/state/tasks.db` (4 rows, `owner_cto = e1e3d3ef`). `lib/db.py`
resolves `DB_PATH` from its own file location, so every checkout is its own
database. Both boxes ssh into the same winbox. Full write-up: ADR 0024
`decisions/0024-split-brain-task-database.md` in the org wiki. Cite it in the
report's output so whoever reads the orphan list knows where those rows live.
