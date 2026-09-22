# SomPong lane routing via decide() — task-3de56f59

Status: implemented, **not yet deployed to Contabo** — until deployed,
nothing changes for live traffic; the box keeps running the full lane on
every message, same as before this task.

## Lane table

`run_secretary_turn` calls `decide("sompong.route", prompt)` before any
`claude` subprocess. Only a confident result (`provider == "rules"`, or a
paid provider's own reported confidence `>= 0.9` — see `_decision_is_confident`)
can move a message off the full lane:

| outcome (confident only) | lane |
|---|---|
| `chitchat` | **light** — haiku, zero tools, `--max-turns 1`, no `--resume` |
| `spam`, profile `claude-code-family` | **silent** — fixed Thai reply, no `claude` call at all |
| `spam`, profile `secretary` | full (the CEO is never spam) |
| `order_for_cto` / `order_for_other_cxo` / `question` | full — unchanged |
| not confident, `choice: null`, or `decide()` raised | full — routing never makes a turn worse than today |

Kill switch: `SOMPONG_ROUTE=off` (env or `.env`, read via `tools.decide._env`)
forces the full lane unconditionally and skips `decide()` entirely. Default
is on.

## Reading the numbers

Per-message decision rows:

    python tools/decide.py report          # per-site rollup, current month
    python tools/decide.py sompong.route --state-file <(echo "test message")

Light-lane usage (`lib.db.log_event(kind="sompong_lane", ...)`, written only
for light-lane turns — full-lane turns are unchanged behaviour with nothing
new to track):

    sqlite3 state/tasks.db "select ts, payload from events where kind='sompong_lane' order by id desc limit 20;"

Compare `sompong_lane.payload.tokens_in/out` against `decide.py report`'s
`counterfactual_usd` column for `sompong.route` to check the estimate
against reality.

## Deploy to Contabo (NOT run by this task)

The service runs on Contabo under systemd as unit `mooniex-secretary`,
user `secretary`, with `EnvironmentFile /home/secretary/.secretary.env`
(`scripts/install-secretary-waker.sh`).

1. The CTO/CEO adds three keys to that env file by hand — **never commit
   values to the repo or this doc**:
   `OPENROUTER_API_KEY`, `DECIDE_PROVIDER=jev`, `DECIDE_BUDGET_USD=5`
2. Deploy:

       ssh mooniex-vps
       cd /opt/mooniex-agents && git pull && sudo systemctl restart mooniex-secretary

Until step 1+2 both happen, `DECIDE_PROVIDER` is unset on that box, so
`decide()` resolves through the free `rules` rung only — routing still runs,
but `chitchat`/`spam` only fire on the literal patterns in
`config/decisions/sompong.route.yaml`, never on an LLM judgment call.
