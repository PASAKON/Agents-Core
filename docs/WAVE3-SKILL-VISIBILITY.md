# Wave 3 Phase 1 — Plugin-Level Skill Visibility

Implements the plugin half of `org:decisions/0022-skill-governance-visibility-authorship-audit.md`
§2 / `org:playbooks/skill-governance-implementation.md` §"Wave 3". **Phase 1
only — plugins.** Phase 2 (per-skill allow-lists) deliberately waits two
weeks for `hook-skill-log.py`'s role column (Wave 0) to accumulate real
usage data. No other wave touched.

## Wiring branch taken, and why

The brief asked one question first: is `enabledPlugins` honoured in the
`.claude/settings.local.json` that `runners/worker_init.py:176`
`_write_dev_settings()` already writes into every worker's worktree
(**yes** branch: add keys there, done), or does a spawner need `--settings
<path>` instead because `localSettings` loses to a higher-precedence source
(**no** branch)?

**Answer: yes.** Measured live (Claude Code 2.1.252, 2026-09-01):

1. `~/.claude/settings.json` (userSettings) has an explicit
   `"enabledPlugins": {"ecc@ecc": true, "finance@knowledge-work-plugins":
   true, "cost-guardian@cost-guardian-marketplace": true,
   "meigen@meigen-marketplace": true}`.
2. A worktree's `.claude/settings.local.json` (localSettings — the file
   `_write_dev_settings()` writes) with `"enabledPlugins": {"ecc@ecc":
   false, ...}` for all four **did** flip `claude plugin list --json`'s
   `enabled` field to `false` for all four, despite localSettings ranking
   *below* userSettings in the documented precedence
   (`policySettings > flagSettings > userSettings > projectSettings >
   localSettings`).

So the documented precedence order doesn't behave as a naive "higher source
wins the whole key" merge for `enabledPlugins` the way it might for a
scalar — an explicit `false` at a lower-precedence source still disabled a
plugin explicitly `true` at a higher one. Conclusion: **add the keys to the
existing `settings.local.json`. No new flag, no `--settings`, no drift with
`runners/worker_resume.py`'s argv-rebuilding.** This is the "much better
outcome" branch the brief hoped for.

One caveat worth stating plainly: because the cage lives in a file the
worker itself can `Write`/`Edit` inside its own worktree, a worker *could*
lift its own cage by rewriting `settings.local.json` — nothing about
`localSettings` outranking anything prevents a direct edit of the file that
defines it. The `--settings` (flagSettings) alternative would have closed
that specific gap (a worker cannot out-rank a flag its spawner passed), but
the brief's own stated preference for the simpler outcome once `yes` was
confirmed is what's implemented here. Flagging this so it isn't rediscovered
as a surprise later — it's a real, if minor, gap, not an oversight.

## The most dangerous check — GateGuard survives, but only because ecc stays enabled

**This changed the deliverable's shape.** The brief's own Hard Constraint #4
asked: does `enabledPlugins: false` disable only a plugin's *skills*, or
its *hooks* too? `ecc` ships GateGuard (`gateguard-fact-force`) as a hook.

**Verified live, fresh session each time (a new claude process, not the
current one — GateGuard's per-session cache would otherwise mask the
result):**

| Run | `ecc@ecc` in `enabledPlugins` | First `Bash` call result |
|---|---|---|
| Control | not set (plugin enabled, default) | **Blocked** — `[Fact-Forcing Gate]` fires, exactly as expected |
| Test | `false` | **Not blocked** — command executes immediately, no gate at all |

Source-level confirmation, not just the A/B: `gateguard-fact-force.js` and
its registration are entirely inside the `ecc` plugin's own bundle
(`~/.claude/plugins/cache/ecc/ecc/2.0.0-rc.1/hooks/hooks.json`) — nothing
about GateGuard is registered directly in `~/.claude/settings.json`'s own
`hooks` key. Disabling the plugin disables the whole bundle it ships,
`hooks.json` included, not just its skills.

**Consequence: `ecc@ecc` must never appear in a worker-visibility profile.**
`policies/skill-visibility/worker-baseline.json` deliberately excludes it.
`scripts/test_skill_visibility.py::test_worker_baseline_never_disables_gateguard_bundle`
enforces this as a standing regression guard, not just a one-time check.

This is the "say so plainly rather than shipping a silent capability loss"
case the brief called out by name, and it materially shrinks Phase 1's
payoff (next section) — `ecc` is 92 of the 113 plugin skills the brief's
"most of the win" framing was counting on.

**A possible future improvement, not built here (out of scope for Phase
1):** GateGuard's hook could in principle be re-registered directly in
`~/.claude/settings.json`'s own `hooks` key (the way the Wave-0-era
`hook-gateguard-category-*.py` hooks already are), pointing at the same
`gateguard-fact-force.js` script path, which would let `ecc@ecc` itself be
disabled for workers without losing the hook. Not attempted here: it
requires a human edit to `~/.claude/settings.json` (a worker/agent cannot
write that file — the permission classifier blocks it), and reaching into
`ecc`'s own hook script from outside the plugin is a bigger, riskier change
than "Phase 1 — plugins only" was meant to authorize. Left for the CTO to
decide whether it's worth a dedicated follow-up task.

## Exact plugin keys, and where they came from

Read verbatim from `~/.claude/plugins/installed_plugins.json` (not
synthesized) via `cat ~/.claude/plugins/installed_plugins.json` — 4 plugins
installed on this machine, all `scope: "user"`:

| Key | In `worker-baseline.json`? | Why |
|---|---|---|
| `ecc@ecc` | **No** | Ships GateGuard's hook in its own bundle — see above |
| `finance@knowledge-work-plugins` | Yes, `false` | No worker role needs finance skills; CFO/finance already get `all` |
| `cost-guardian@cost-guardian-marketplace` | Yes, `false` | Budget-tracking skills, not worker-relevant |
| `meigen@meigen-marketplace` | Yes, `false` | Image-generation skills, not worker-relevant |

`policies/skill-visibility/worker-baseline.json` is a 3-key file (the brief
anticipated "a ~46-key file behaved correctly" as the size to aim for; ours
is smaller still because only 4 plugins are installed on this machine in
the first place, and one of the four is excluded for GateGuard).

## Measured before/after — real numbers, this session, Claude Code 2.1.252

Method: `claude -p "List every skill name you have access to via the Skill
tool, one name per line." --model claude-haiku-4-5 --output-format json
--strict-mcp-config`, run from this worktree's cwd (not a bare/empty
directory — the ADR's own "baseline, bare cwd" numbers were measured from a
different starting point, so ours differ in absolute terms but the same
methodology applies to both rows below, making the *delta* the meaningful
number). "Total context tokens" = `usage.input_tokens +
cache_creation_input_tokens + cache_read_input_tokens` from the CLI's own
`--output-format json` result — the full billed prompt size regardless of
cache hit/miss.

| Configuration | Skills listed | Total context tokens |
|---|---|---|
| Baseline (no `enabledPlugins` override) | **186** | **39,993** |
| All 4 plugins disabled (unsafe — GateGuard dies, shown only for comparison) | 76 | 34,915 |
| **Shipped `worker-baseline` profile** (3 plugins disabled, `ecc` kept) | **168** | **39,924** |

**The honest number: −9.7% skills listed, −0.2% tokens.** Once GateGuard
safety is respected, Phase 1's real savings are far smaller than the
brief's framing implied. The brief's "113 of 293 skills are plugin skills…
most of the win for one list per role" arithmetic is true only if `ecc`'s
92 skills are included in what gets disabled — and they can't be, per the
finding above. The three plugins that *are* safe to disable
(finance/cost-guardian/meigen) are small and their descriptions are short,
so removing them barely moves the token count even though it's a real,
double-digit cut in the skill list itself.

This is exactly the kind of thing this report is supposed to surface rather
than launder: the number in the brief's own table ("4 plugins disabled via
`enabledPlugins` → 57 skills") **is real and reproducible**, but it was
measured with all four plugins off, including `ecc` — a configuration this
task cannot ship once GateGuard is accounted for.

## `cto` profile — proven byte-identical

`skill_visibility_overlay("cto")` returns `None` (profile `all`), so
`_write_dev_settings()` never adds an `enabledPlugins` key at all — not an
empty dict, not every plugin listed `true`. `scripts/test_skill_visibility.py::test_write_dev_settings_cto_emits_no_enabledplugins_key`
writes settings for a `"cto"`-profile worktree and a plain no-role call
side by side and asserts the resulting files are byte-identical.

## Root derivation — never hardcoded

`runners/worker_init.py`'s `ROOT = Path(__file__).resolve().parent.parent`
was already portable (Contabo runs the same repo at `/opt/mooniex-agents`
with no code change needed). `skill_visibility_overlay()` resolves profile
files via that same `ROOT`, so it inherits the portability.
`scripts/test_skill_visibility.py::test_root_is_derived_not_hardcoded`
monkeypatches `worker_init.ROOT` to a fake, throwaway directory containing a
fabricated `worker-baseline.json` and asserts the fake content — not the
real repo's — comes back, proving the lookup is relative, not hardcoded.

## Version guard — what to do when it fires

`scripts/test_skill_visibility.py::test_enabledplugins_mechanism_still_honoured_in_local_settings`
does not check a version string. It exercises the real, installed `claude`
binary: writes a throwaway `settings.local.json` disabling one real
installed plugin (never `ecc@ecc`), runs `claude plugin list --json`
(no LLM call, no token cost), and asserts that plugin's `enabled` field is
`false`. This is the actual mechanism this whole feature depends on, not a
proxy for it.

**If it fails after a Claude Code upgrade:**

1. **Stop treating `worker-baseline.json` as load-bearing** — a worker may
   be seeing every skill again, silently, which is a context-cost
   regression, not a correctness bug, so nothing else will alert you to it.
2. Reproduce the "Reproducing the measurement" steps below by hand against
   the new version.
3. **Re-run the GateGuard A/B too, not just the `enabledPlugins` mechanism
   test** — a version bump could change plugin *bundling* behavior
   (whether hooks ship inside `enabledPlugins`'s blast radius) independently
   of the settings-merge precedence this automated test covers. The
   GateGuard finding was verified by hand (live A/B + source inspection);
   there's no automated regression test for it in CI, deliberately, because
   doing so would require a real LLM-costing session on every test run to
   fire the `Bash` tool through a live claude process — see the note in the
   next section on why this stays a manual step, and if you decide to
   automate it anyway, budget the token cost per CI run.
4. Update the version pin note below with the newly verified version before
   re-enabling.

**Verified working on:** Claude Code 2.1.252 (2026-09-01).

### Reproducing the measurement (manual — the GateGuard check specifically is not in CI)

```bash
# 1. Baseline plugin list (no override)
claude plugin list --json

# 2. Apply a test override in the worktree's OWN .claude/settings.local.json
#    (never ~/.claude/settings.json -- that's the user's global file)
python3 -c "
import json
p = '.claude/settings.local.json'
d = json.load(open(p))
d['enabledPlugins'] = {'ecc@ecc': False}
json.dump(d, open(p, 'w'))
"

# 3. Fresh-process GateGuard check (must be a NEW claude process --
#    the current session's own GateGuard cache would mask the result)
claude -p "Use the Bash tool to run: echo test" \
  --model claude-haiku-4-5 --output-format stream-json --verbose \
  --allowed-tools Bash --permission-mode auto
# Control (no override): first TOOL_RESULT should be the
# "[Fact-Forcing Gate]" text. Test (ecc@ecc: false): if the command's
# output appears with NO gate text first, GateGuard's hook died with the
# plugin -- ecc@ecc must stay out of every worker-visibility profile.

# 4. Restore the worktree's settings.local.json afterward (it's
#    regenerated by runners/worker_init.py on every real spawn anyway).
```

## Known gap: `runners/worker_resume.py` not updated

`_write_dev_settings()`'s signature gained a `role` parameter.
`runners/worker_resume.py:87` still calls it with the old one-arg form —
this task's declared touches (`policies/agents.yaml`,
`policies/skill-visibility`, `runners/worker_init.py`,
`scripts/test_skill_visibility.py`, `docs/WAVE3-SKILL-VISIBILITY.md`) do
not include `runners/worker_resume.py`, and `self_repo_guard` (ADR 0020)
refused the edit outright, correctly, with instructions to report it rather
than route around it.

The fix was made **backward-compatible** instead: `role` defaults to
`None`, and `None` means "no overlay" (same as profile `all`). Practical
effect: a **freshly spawned** worker gets its `skills_profile` correctly.
A **resumed** worker (`runners/worker_resume.py`) falls back to pre-task
behavior — every skill visible, same as before this task — rather than
crashing with a `TypeError`. This is a real, if minor, gap: resumed
workers don't get the context savings until `runners/worker_resume.py:87`
gets the matching one-line change
(`_write_dev_settings(worktree, role)`). Flagged to the CTO via
`dev_message`; needs its own declared-touches task or an amendment to this
one.
