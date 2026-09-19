---
name: delegate-external-agent
description: Hand a task to an agent that is NOT Claude Code — Codex CLI, Antigravity, or a human — by writing a self-contained brief, shipping only what that machine needs, and reviewing the result afterwards. Trigger on /delegate-external-agent, and whenever the CEO says "ให้ Codex ทำ", "ส่งไป winbox", "ข้ามไป Antigravity", "สั่งงาน agent อื่น", or whenever the Claude weekly limit is low and the work is mechanical. Do NOT use it for the org's own Claude workers (that is dev-spawn-protocol) or for deciding whether a browser is needed (IRON-RULES §42).
---

# Delegating to an agent that is not Claude

**The CEO's reasoning, 2026-09-19:** a GPT model driven inside Claude Code
underperforms — "มันไม่เป็นตัวของตัวเอง" — because the harness, the tool-call
format and every skill are tuned for Claude. So stop moving the model into our
tool. **Move the task out to theirs.**

The unit of exchange becomes a **brief**, not a session. Claude writes the brief
and reviews the result; the other agent does the work in the tool it was built
for. Cheaper than running a foreign model through our harness, and it stops two
CLIs fighting over one conversation.

Claude's job here is **the two ends, not the middle**: specify precisely, then
verify honestly.

---

## 1. When this is the right move

| use it | do not |
|---|---|
| Mechanical work with a known procedure (shoot N clips, convert N files, run a script over a list) | Anything touching secrets, production, money, or a merge decision |
| The other agent's own tool is genuinely better (Codex CLI on Windows, Antigravity in an IDE) | Work needing the org's skills, wiki, MCP tools or task DB |
| Claude's quota is low and the work is long | Work where a wrong answer ships silently and nobody notices |
| The work runs on another machine anyway | A task you cannot describe without "you know what I mean" |

**The honest test:** if you cannot write the brief without referring to something
only a Claude session knows, the task is not ready to leave.

---

## 2. Write the brief so it survives without you

Put it in `docs/briefs/<AGENT>-<host>-<topic>.md` and commit it. It must read
correctly to someone who has never seen this repo.

**Required sections, in order:**

1. **What this is** — context in a paragraph, and what "finished" means.
2. **Set up** — exact commands for that OS. Name the interpreter
   (`.venv\Scripts\python`, not `python`).
3. **Read these first** — a table of paths with *why each matters*. A list of
   files without reasons gets skimmed.
4. **Machine-specific hazards** — the screen lease, a resident process, a shared
   Chrome profile. Anything that makes a correct command do damage.
5. **The commands**, in run order, dry-run first.
6. **Money rules** — the cap, the current balance, cost per unit, and "never
   raise a cap to make a run finish".
7. **Where the state lives** — the ledger/index file, so a crash resumes
   instead of restarting.
8. **What done looks like** — the verification command and the artefact.
9. **Report format** — see §5.
10. **Traps already paid for** — every trap this project learned the hard way.
    This section is the whole reason a brief beats a chat message.
11. **Ask before** — what needs the CEO, explicitly.

**Banned in a brief:** references to skills, MCP tools, `submit_report`,
`/commands`, or any Claude Code concept. If the brief mentions our harness, it
has failed its one job.

---

## 3. Ship only what that machine needs

```bash
COPYFILE_DISABLE=1 tar -czf /tmp/kit.tgz <explicit file list>   # never a whole tree
tar -tzf /tmp/kit.tgz | grep -iE '\.env$|secret|token|credential'   # must be empty
scp /tmp/kit.tgz winbox:C:/mooniex/kit.tgz                      # forward slashes for scp
ssh winbox 'cd /d C:\mooniex & tar -xzf kit.tgz -C agents & del kit.tgz'
```

Then **verify each required file landed, by name**, and that `.env` is absent. A
transfer that reports success is not the same as the file being there.

`COPYFILE_DISABLE=1` stops macOS shipping `._*` junk. `rsync` is not on Windows;
tar+scp is. scp wants `C:/path`, not `C:\path`. A whole-tree tar was 557 MB; the
explicit list was 160 KB.

**No secrets travel.** If the task seems to need a credential, say so and stop —
usually the target machine should already be logged in, or the task does not
belong out there. (The 2026-09-19 Flow shoot needed none: the runner drives a
Chrome that is already signed in.)

Future: secrets move to Infisical and this changes — see
`project_infisical_secrets_and_split_stack` in memory.

---

## 4. Hand the CEO one message to paste

He is the transport. Give him a block he can copy without editing:

```
อ่านไฟล์ <absolute path to the brief> แล้วทำตามทั้งหมด
งาน: <one sentence>
กฎที่ห้ามละเมิด:
1. <hazard — e.g. borrow the screen before opening Chrome>
2. dry-run ก่อนทุกครั้ง และ <the number that must not move> ต้องไม่ขยับ
3. ห้ามเกิน cap ห้ามขึ้นเพดานเอง
4. รายงานด้วย <the number> before/after เสมอ
5. ห้าม login เอง ห้ามแก้ <files that are not theirs> ห้าม push main
<current balance / state> · ถ้าติดอะไรถามก่อน
```

Under ~12 lines. A rule the agent scrolls past is not a rule.

---

## 5. The report format you demand back

```
credits: start N -> end M (delta D)      # or: files X, rows Y — the cumulative number
<unit>: verified X / N   failed: [...]   needs-human: [...]
artefacts: <path>  (X files)
blockers: ...
```

**The cumulative number comes first, always.** On 2026-09-19 a status card said
"not charged" while the balance said charged; a log line said "submitted" that a
unit test had written; a `grep -c` counted 22 clips where there were 16. Text
surfaces were wrong three times in one evening; the balance was right every time.
Ask for the number that can only move if the work actually happened.

---

## 6. Review — Claude's real job in this pattern

Treat the report as a claim, not a result.

1. **Re-measure the cumulative number yourself**, or have the CEO read it. Never
   accept it from the report alone.
2. **Open one artefact and look at it.** One clip, one file, one row. The
   2026-09-19 run was saved by someone opening frame 0 and seeing the right man
   in the right apron — after two agents reasoned their way to the wrong
   conclusion from logs.
3. **Check the state file against the artefacts.** Ledger says verified, disk
   says the file exists, durations match the sheet. Disagreement is the finding.
4. **Read the diff if they touched code, and run the tests on your side.** A
   guard nobody has seen stop something has not been tested — make the forbidden
   call and watch it fail.
5. **Then merge, or reopen with the specific thing that is wrong** — the exact
   row, the exact number, the exact line. Never "please improve".

Anything learned goes back into the brief's §10 so the next agent inherits it.

---

## 7. What never leaves

- Secrets, tokens, `.env`, anything under `~/.config/mooniex/`.
- Merge decisions on `main`. External agents push `agent/<tool>-<topic>`;
  Claude reviews and merges.
- The creative source of truth — scripts, prompts, brand decisions. An external
  agent executes them, never edits them.
- Anything where being wrong is expensive and invisible.

---

## Related

`dev-spawn-protocol` (the org's own Claude workers — a different thing),
`docs/ops/model-fallback.md` (which lane runs what when quota is gone),
`docs/briefs/CODEX-winbox-shoot.md` (the first real example, 2026-09-19),
IRON-RULES §53 (repeated browser work is a script, not a model).
