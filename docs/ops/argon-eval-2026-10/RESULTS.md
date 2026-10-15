# ArgonEval: Gemini 4 Argon on real org work, by position (15–16 Oct 2026)

Order: CEO, 15 Oct ~16:35 TH. Score Argon on real, hard org work that lands, say which worker positions
can move off Claude, no guessing. Run by PH#506b879f (CTO lane) for CTO Main.

Runner under test: `agy:gemini-4-argon-high`, the production route (create_task → delegate →
`spawn-worker-remote.sh`). Baselines: `agy:claude-sonnet-5-5-high` (agy's Claude bucket, $0 Anthropic) on 5
jobs, and the Claude Code route (Opus 5.5) on 2. Every output was reviewed by the PH the way any worker's
is: tests run, numbers re-derived, citations re-fetched, file:line checked. A reviewer fix or a redo counts
against Argon's first pass.

**Shell mode not tested: launcher is edits-only (spawn-worker-remote.sh:264); a sandboxed shell trial
needs a CEO decision.** Argon never ran a command in these jobs: it could not run its own tests, and the
reviewer did. (CTO Main reported a CEO go for shell rights on 15 Oct; the launcher change was not live
during this run.)

## Scorecard

Score 0–10 = first-pass quality on this position's jobs, after review. Landed = merged PR, a PR ready in the
merge batch, or a report PR. "First pass" = no redo and no reviewer fix.

| Position | Jobs (outcome) | Argon first pass | Score | Verdict |
|---|---|---|---|---|
| data_analyst | A1 Claude worker load split (#371) pass · A2 credit ledger reconcile (#372) pass | 2/2 | 9 | **Argon + review** (reviewer re-derives the headline numbers) |
| tester | T1 tests for skill_rename (#362, merged) pass · T2 tests for resume_worker (#369) pass | 2/2 | 8 | **Argon + review** (reviewer runs the tests: Argon cannot) |
| content / translation | X1 names + Watch plan TH→EN (#373) pass | 1/1 | 8 | **Argon + review** (brief lists what stays Thai) |
| long-context | L1 task writes without an actor (#370) pass · L2 hook inventory (#374) pass | 2/2 | 8 | **Argon + review** (spot-check file:lines) |
| developer, big | B1 run-watch part B (#359, merged) redo + reviewer fix · B2 Console run-inbox hardening (Console #37) 1-line reviewer fix | 0/2 | 6 | **Argon + review** |
| developer, debug | G1 memory_sync pull on a diverged repo (#357, merged) redo + reviewer fix | 0/1 | 6 | **Argon + review** |
| developer S/M | D1 ClaudeFlow #81 drop aliases: fail (missed prompt strings; Sonnet landed it, ClaudeFlow #230) · D2: not scored (the fix was already on main; tests only, Console #36) | 0/1 | 4 | **Argon + review**, Sonnet next in line |
| devops_engineer | O1 secretary journal logging: redo (a global logger change; the Opus run landed it, #365) · O2 ClaudeFlow #225 CI red (ClaudeFlow #231) pass | 1/2 | 5 | **Keep on Claude**; Argon + review for scoped CI/config fixes |
| security_engineer | S1 org-mail identity fails closed: fail ×2 (run 0 ended on one denied read; run 1 missed ~40 callers; the Opus run landed it, #366) · S2 six LOW items of #279 (#368) pass | 1/3 runs | 4 | **Keep on Claude**; Argon + review only for a scoped list of LOW fixes |
| researcher | R1 fact-check of the Argon clip: fail · R2 WebAuthn excludeCredentials, Console #3: fail (Sonnet landed it, Console #38) | 0/2 | 3 | **Not Argon.** agy Sonnet (passed both) |
| video QC | V1 EP6 render defects | — | — | see "Video QC" below |

Argon totals over 18 scored runs, first pass: 9 pass (A1, A2, T1, T2, X1, L1, L2, S2, O2), 4 redo or
reviewer fix (G1, B1, B2, O1), 5 fail (D1, S1 run 0, S1 run 1, R1, R2). D2 is not scored.

### What the fails were
- **Researcher (R1, R2): invented sources.** R1 put two quotes on pages that do not carry them and gave a
  hallucination figure no source supports. R2 printed a "verbatim" code block that is not in the file and a
  spec sentence that is not in the spec. The conclusions were partly right; the evidence was made up. On the
  same briefs agy Sonnet quoted only what the pages say, and wrote "not confirmed" where it could not find
  a source.
- **Wide changes (S1, D1, O1): missed reach.** S1 changed a shared rule without finding its ~40 callers, so
  their tests broke. D1 removed aliases but left the prompt strings that used them. O1 changed the logging
  of every process instead of the two services. Each time the core idea was right and the edges were not.
- **Headless stop (S1 run 0):** one auto-denied tool call (a read outside the worktree) ended the agy run
  with no output after 9 minutes.
- **No shell:** B2 shipped a test that imported names the fixture does not export; Argon could not run it.
  T1 and T2 tests passed on the first run, but only the reviewer could know that.

### What the passes had in common
- Bounded input with a checkable answer: a file to reconcile, a module to test, a plan to translate, a
  repo to inventory. Every number in A1 and A2 matched the reviewer's own count; every seeded revert in T1
  (7) and T2 (4) turned a test red; all 12 file:lines checked in L2 were right.
- It flagged its own doubts: X1 marked 21 ambiguous places in the Thai plan, several of them real gaps.

## Baselines (agy Sonnet 5.5 and Claude Code Opus 5.5)

| Job | Argon | Baseline | Note |
|---|---|---|---|
| D1 dev S | fail, 20 min | agy Sonnet pass, 7 min → ClaudeFlow #230 | Sonnet caught the prompt strings |
| T1 tester | pass, 7 tests, 9 min | agy Sonnet pass, 46 tests, 8 min | Sonnet ran pytest inside agy and found a latent bug in the tool |
| L1 long-context | pass (score 8) | agy Sonnet pass (score 9) | both landed one report (#370) |
| R1 researcher | fail (score 3) | agy Sonnet pass (score 8) | every Sonnet figure matched the source |
| R2 researcher | fail (score 4), 13 min | agy Sonnet pass (score 9), 4 min → Console #38 | Sonnet also found the likelier cause in the code (the login path) |
| S1 security | fail ×2 | Claude Code Opus pass, 99 min → #366 | full caller inventory, 65 tests moved |
| O1 devops | redo | Claude Code Opus pass, 27 min → #365 | measured on the box read-only; credit: this run found the live 0600 letter-permission bug in the secretary, fixed in #367 |

agy Sonnet won 4 of the 5 paired jobs and tied 1 (T1). It was also faster on every pair. Judging was not
blind: the PH reviewed the Argon output first in each pair.

## The clip's claims, against these jobs
| Claim | What we saw |
|---|---|
| #1 at coding | Not on our work, edits-only: dev first pass 0 of 4 scored jobs; agy Sonnet beat it on D1. Shell mode untested |
| Lowest hallucination (15%) | Opposite on research: 2 of 2 jobs carried invented quotes; agy Sonnet 0 of 2. The 15% figure has no primary source (R1) |
| 1M context | Held up: two whole-repo jobs (L1, L2) passed with correct file:line evidence |
| Cyber, finds and patches | Good on a scoped list (S2, 6 of 6 fixed with tests); missed reach on a cross-cutting change (S1) |
| Dozens of agents ("Team Preview") | Not in agy 1.3.5 (no team or subagent flag; `agy agents` lists nothing). Not tested |
| Speed | 6–29 min per job; slower than agy Sonnet on every pair |

## Video QC
V1 (defects in a real 3-minute EP6 render) waits for the Gemini 5-hour bucket (below the 25% floor at
01:00 TH 16 Oct). The result is added here when it runs.

## Cost
Subscriptions only, $0 spent. Gemini weekly went from 87% to 43% between 16:46 TH 15 Oct and 01:00 TH 16 Oct
(other org work drew on the same bucket, so ~2.5 points per Argon job is an upper bound). The S1 run that
ended early used ~15 points of the 5-hour bucket.

## Routing proposal
Diff to `config/plans.yaml`, not applied (CTO Main reviews it): `routing-proposal.diff` next to this file.
- `research`: drop Argon; agy Sonnet second after Codex.
- New `tests_edit` class for `tester`: Argon first; the reviewer runs the tests. A brief that needs a shell
  inside the run still drops to a shell runner (`tools/forecast.needs_shell`).
- New `analysis` class for `data_analyst`: Argon first; the reviewer re-derives the headline numbers.
- `security_engineer`, `devops_engineer`: unchanged (Claude Opus).
- `dev_general` and `doc_text`: unchanged (Argon first already). Do not route wide refactors there.

## Records
- One `runner_fit` record per job (`tools/runner_fit.py`), PH comments included.
- Raw data (briefs, review notes, usage readings) stays in `state/argon-eval-2026-10/` on Contabo, not committed.
- Every job above landed as a PR or is counted as a fail.
