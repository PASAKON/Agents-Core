# TASK — finish shooting the film «จุดจบของเจ้าหนี้นอกระบบ» in Google Flow

You are working on a Windows machine called **winbox**. Everything you need is
in this brief. It does not assume any particular agent tool — read it, do the
work, report at the end. Ask before anything it tells you to ask about.

---

## 0. What this is

A Thai moral short drama, 7 acts, 173 shots, generated in Google Flow
(flow.google.com). Act 1 is finished. **139 shots remain.** Your job is to run
them through a Python runner that already exists and works — you are not writing
a generator, you are operating one and fixing it if it breaks.

The runner was proven on 2026-09-19: one shot, 4 credits, clip verified correct.

---

## 1. Set up (do this first, in order)

```powershell
# a. get the repo
git clone https://github.com/PASAKON/MoonieX-Agents.git C:\mooniex\agents
cd C:\mooniex\agents

# b. python env
python -m venv .venv
.venv\Scripts\pip install playwright
# NOTE: do NOT run `playwright install`. We attach to a real Chrome over CDP.

# c. ffmpeg must be on PATH (the runner verifies every clip with ffprobe)
ffmpeg -version
```

If the clone fails, the repo may be private — ask the CEO for access rather than
working around it.

---

## 2. Read these before touching anything

In the repo you just cloned, in this order:

| file | why |
|---|---|
| `docs/ops/flow-operator-design.md` | what the runner is and why it exists |
| `docs/reports/flow-runner-build/REPORT-iter3.md` | the last run: what works, what is still unverified |
| `docs/scripts/BANCHI-SHOOT-BRIEF.md` | every Google Flow trap, each one paid for in credits |
| `.claude/skills/google-flow-ops/SKILL.md` | the measured click path, costs, and the live-DOM findings |
| `tools/flow_shoot.py` | the runner itself |

**`.claude/skills/` is just a folder of markdown.** Read it as documentation;
nothing about it requires a particular tool.

---

## 3. ⛔ Borrow the screen before you open Chrome

**This machine has a resident tenant.** A bot plays a game on this desktop all
night collecting training data. It is lower priority than you, but it holds the
foreground, and a window of yours on top of it makes it stall *silently while
still reporting itself alive* — you get no error, the owner loses a night of data.

```powershell
# from the Mac, or via ssh to this box:
bash scripts/pc-lease.sh status
bash scripts/pc-lease.sh take --who "codex: shoot Act 2, ~60 min"
#   ... your work ...
bash scripts/pc-lease.sh give-back
```

**Never press ESC on this machine.** It writes a hold file that only a human can
clear, and the farm stays down until someone notices.

---

## 4. Start the automation Chrome and log in ONCE

```powershell
# Chrome with a debug port and a DEDICATED profile — never the CEO's main Chrome
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9223 ^
  --user-data-dir=C:\mooniex\flow-automation\chrome-profile ^
  --no-first-run --mute-audio
```

In that window: log into Google (the CEO's account), open flow.google.com, open
the project named **AI Film**, leave the tab open.

**You may not enter the password yourself.** If it is not already logged in, stop
and ask the CEO to log in. Credentials are never yours to type.

Verify: `curl http://127.0.0.1:9223/json/version` should return JSON.

---

## 5. Do a dry run first. Always.

```powershell
.venv\Scripts\python tools\flow_shoot.py run ^
  --sheet docs\scripts\banchi-ACT2.md ^
  --ledger state\banchi\ACT2.tsv ^
  --dest C:\mooniex\out\banchi-ACT2 ^
  --credit-cap 0 --dry-run
```

`--dry-run` is structurally incapable of submitting — `submit()` raises if it is
ever reached. It reads every setting back off the live DOM and prints them.

**Read the balance before and after the dry run. It must not move by one credit.**
If it moves, something is wrong that this brief does not know about — stop and
report, do not proceed to a paid run.

The credit balance is in Flow's account menu, shown as `เครดิต Google Flow N เครดิต`.

---

## 6. Then shoot, in batches, with a cap

```powershell
.venv\Scripts\python tools\flow_shoot.py run ^
  --sheet docs\scripts\banchi-ACT2.md ^
  --ledger state\banchi\ACT2.tsv ^
  --dest C:\mooniex\out\banchi-ACT2 ^
  --credit-cap 300
```

Then repeat for `banchi-ACT3.md` … `banchi-ACT7.md`, one act per run, each with
its own ledger file.

There is also a free retrieval mode for shots already generated and paid for —
**shots 53-58 of Act 2 are in Flow right now, paid, never downloaded**:

```powershell
.venv\Scripts\python tools\flow_shoot.py pull --sheet docs\scripts\banchi-ACT2.md ^
  --ledger state\banchi\ACT2.tsv --dest C:\mooniex\out\banchi-ACT2
```

### Money rules — these are hard
- **Credits are the CEO's money.** Current balance: **8,544**. A 720p/8s shot
  costs 20; a 360p/4s test shot costs 4.
- `--credit-cap` is enforced inside the runner and stops the whole run. **Never
  raise a cap to make a run finish.** If it stops, report and ask.
- **Never spend more than 300 credits without checking in.**
- A refused generation is refunded. The runner re-fires an identical prompt once,
  then records `refused` and moves on. **Never rewrite a prompt to get past a
  refusal** — the wording is the director's, not yours.

---

## 7. The ledger is the memory, not your context

One row per shot: `todo → submitted → generated → downloaded → verified`, or
`refused` / `needs_model` / `failed`. Writes are atomic.

- A run that dies mid-way: just run the same command again. Verified rows are
  never re-fired.
- `needs_model` rows are ones the script could not decide. Look at the note,
  fix that one thing, set the row back to `todo`, run again.
- `.\.venv\Scripts\python tools\flow_ledger.py status state\banchi\ACT2.tsv`
  prints where everything stands.

---

## 8. What "done" looks like for an act

```powershell
.venv\Scripts\python tools\clip_review.py C:\mooniex\out\banchi-ACT2 ^
  C:\mooniex\out\sheets docs\scripts\banchi-ACT2.data.py

.venv\Scripts\python tools\assemble_act.py C:\mooniex\out\banchi-ACT2 ^
  docs\scripts\banchi-ACT2.data.py C:\mooniex\out\ACT2.mp4
```

`assemble_act.py` refuses to build a cut with a missing shot unless you pass
`--partial`. That refusal is correct — a hole in a cut reads as a directing
choice, not an absence. Do not force it.

---

## 9. Report back with numbers, not adjectives

```
credits: start N -> end M (delta D)
ACT2: verified X / 24   refused: [shot numbers]   needs_model: [shot numbers]
files: C:\mooniex\out\banchi-ACT2\  (X files)
blockers: ...
```

**Report the credit delta first, every time.** It is the only number that cannot
be faked by a status message. A log line saying "submitted" and a card saying
"failed" have both been wrong on this project; the balance never has.

If you fix a bug in the runner, commit it on a branch named
`agent/codex-<what>` and push. Do not push to `main`.

---

## 10. Things that have already gone wrong here — do not rediscover them

- **A stray `cdk-overlay-backdrop` left open by an earlier script blocks every
  later click**, including attaching character references, while reporting the
  element as "visible, enabled and stable". Close what you open.
- **Every resolution/duration label is always in the DOM.** Checking "is '360p'
  in the page text" returns true no matter what is selected. Read the
  `mat-button-toggle-checked` class instead.
- **The credit estimate only exists while the settings panel is open.**
- **The submit button's label is `เริ่มสร้าง`**, never "Submit".
- **`[aria-label="Download"]` matches nothing.** The runner uses a CDN pull.
- The settings panel opens on the **Image** tab; select **วิดีโอ** first.
- Never play a clip with sound. You cannot hear it and the CEO can.

---

## 11. Ask the CEO before

- any spend beyond the cap you were given
- logging into anything
- touching `main`, anything under `~/Desktop/banchi-*` on the Mac, or any
  `banchi-ACT*.data.py` (those are the script — the director's, not yours)
- installing anything beyond step 1

**No secrets are needed for this task.** The runner uses a Chrome that is already
logged in; it calls no API that takes a key. If you think you need a credential,
you have misread something — ask first.
