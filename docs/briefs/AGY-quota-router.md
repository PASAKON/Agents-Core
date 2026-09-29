# Brief: quota reader + runner router (Phase 2, part 1)

## What this is
The org pays three AI subscriptions and wants each worker task sent to the provider with the
most usage left. Build: a plans file (editable any time), a quota reader that normalises each
provider's live usage, and a router that ranks candidate runners. Pure Python 3, stdlib + PyYAML
(already used in this repo). No network calls in tests.

Finished = the 4 files below + tests exist. Nothing else changed.

## Work ONLY in this worktree
`/Users/gob/MoonieXHQ/Agents/Core/worktrees/quota-router`. File-editing tool only; do not run shell.

## Read these first
| path | why |
|---|---|
| `docs/ops/agent-runners.md` §7 | exact shape of Codex and agy quota data and the traps |
| `config/hosts.yaml` | host names and their `runners:` lists (router must respect them) |
| `tools/delegate.py` `_host_runners`, `KNOWN_RUNNERS` | reuse; do not duplicate |
| any `tests/test_*.py` | test style |

## 1. `config/plans.yaml` (new)
```yaml
# Subscriptions. Append a new entry when a plan changes; never delete old ones (history).
providers:
  anthropic: {runner: claude, plans: [{usd: 200, from: "2026-08-29"}, {usd: 20, from: "2026-09-29T10:00:00Z"}]}
  google:    {runner: agy,    plans: [{usd: 100, from: "2026-09-01"}]}
  openai:    {runner: codex,  plans: [{usd: 20,  from: "2026-09-01"}]}
# Free grants / surprise resets: {provider, from, to, note}. While active the provider is treated as weekly=1.0.
bonuses: []
# Candidate list per job class, in the CEO's order. "runner:model[:effort]".
roles:
  dev_general:    ["agy:gemini-3.8-flash-high", "claude:claude-sonnet-5"]
  c_level:        ["claude:claude-opus-5-5:xhigh"]
  c_level_openai: ["codex:sol:xhigh"]
  complex:        ["claude:claude-fable-5-1", "codex:astra:xhigh"]
router:
  tie_points: 5          # weekly remaining within 5 percentage points = tie, go to daily
  min_samples: 5         # skill score needs >= 5 reviewed tasks, else treated as unknown
quota_sources:           # where each reader looks; ssh host "" = local
  claude: {ssh: mooniex-vps, path: /opt/claude-usage-monitor/usage.json}
  codex:  {ssh: mooniex-vps, sessions_glob: "/root/.codex/sessions/*/*/*/rollout-*.jsonl"}
  agy:    {ssh: "", cmd: ["~/.local/bin/agy", "-p", "/usage", "--output-format", "json"]}
```

## 2. `tools/quota.py` (new)
Dataclass `Quota(provider: str, weekly_remaining: float|None, daily_remaining: float|None, weekly_resets_at: str|None, daily_resets_at: str|None, source: str, error: str|None)`. Fractions 0..1.
Three pure parser functions (tested with fixtures) plus thin fetchers (subprocess/ssh, not tested):
- `parse_claude(obj)`: input like
  `{"five_hour":{"utilization":17.0,"resets_at":"2026-09-29T03:10:00+00:00"},"seven_day":{"utilization":98.0,"resets_at":"2026-09-29T10:00:00+00:00"}}`
  utilization is PERCENT USED → remaining = (100 - u) / 100. five_hour = daily slot.
- `parse_codex(lines)`: iterate JSONL lines; keep the LAST object whose `payload.rate_limits` exists
  (`rate_limits` is a sibling of `info` under `payload`). Each of `primary`/`secondary` is
  `{"used_percent":96.0,"window_minutes":10080,"resets_at":1790593204}` or null. Label by
  `window_minutes`: >= 10080 → weekly, <= 1440 → daily (300 min counts as daily). Never label by
  the key name. `resets_at` is epoch seconds → ISO 8601 UTC.
- `parse_agy(obj)`: `obj["command"]["data"]["groups"][]` each `{"name": "Gemini Models"|"Claude and GPT models", "buckets":[{"window":"weekly"|"5h","remaining_fraction":1,"reset_time":"2026-10-06T00:05:38Z"}]}`.
  Use the "Gemini Models" group (workers run Gemini). "5h" = daily slot.
- Any parse or fetch failure → Quota with both fractions None and `error` set. Never guess.
- `apply_bonuses(quota, bonuses, now)`: active bonus → weekly_remaining = 1.0, note in source.
- CLI: `python tools/quota.py [--json]` prints one line per provider.

## 3. `tools/route.py` (new)
`rank(role: str, quotas: dict[str, Quota], skill: dict[tuple[str,str], float|None], host: str, cfg) -> list[Choice]`
where `Choice(candidate: str, runner: str, model: str, weekly: float|None, daily: float|None, skill: float|None, reason: str)`.
Rules, in order:
1. Only candidates from `roles[role]` whose runner is in the host's runners (use `tools.delegate._host_runners`).
2. Candidates whose provider quota is unknown (weekly None) go LAST, with reason "quota unknown".
3. Sort by weekly remaining, highest first.
4. If two candidates' weekly differ by <= tie_points/100 → compare daily remaining, highest first.
5. Still tied (daily within tie_points too) → higher skill score wins; None skill counts as lower than any number;
   if still tied keep the CEO's order from `roles`.
6. Weekly or daily == 0 → candidate moves to the end, reason "exhausted".
`reason` is a short human sentence with the numbers used.
CLI: `python tools/route.py --role dev_general --host mac --dry-run` prints the ranked list.
Skill scores come from a function `load_skill_scores()` that returns `{}` for now (filled in a later task).

## 4. Tests `tests/test_quota_route.py` (new)
Parser fixtures for all three (including codex with primary weekly + secondary 300-min daily, and a
file where the last rate_limits event is not the last line), a broken input → error set, and router
cases: weekly decides; weekly tie → daily decides; full tie → skill decides; unknown quota last;
exhausted last; host without the runner excludes it; active bonus lifts weekly to 1.0.

## Traps already paid for
- Codex `~/.codex/logs_2.sqlite` is a day stale; use the rollout JSONL only.
- Contabo may have no codex sessions yet → codex quota unknown, which is a valid result.

## Report
`REPORT.md` at worktree root: Files changed / What was done / Blockers.
