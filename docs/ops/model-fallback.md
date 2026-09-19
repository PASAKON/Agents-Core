# Model fallback — what runs on what when the subscription is spent

Written 2026-09-19, the day the weekly subscription limit reached 97 % with
three days left on the clock. Two lanes, decided by the CEO the same day:

| who | lane | why |
|---|---|---|
| **C-level (CTO/CMO/CGO/CFO)** | **Claude, billed to API credit** — not the subscription | orchestration, review and merges are where a cheap miss is expensive |
| **workers (developer, tester, …)** | **9Router** → whatever it is configured to forward to | mechanical work; a miss costs a re-run, not a bad merge |
| **anything touching secrets, production or money** | **Claude, always** | see the guards below |

## C-level on the credit lane

Claude Code bills the subscription when it is signed in, and bills the API
account when `ANTHROPIC_API_KEY` is set. So the switch is one environment
variable, set by the CEO:

```bash
# key created at console.anthropic.com → API keys
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> ~/.config/mooniex/anthropic.env
```

Then `scripts/cto-claude.sh` (and the other C-level launchers) export it. **The
CEO should confirm on the first session that the usage lands on the API account
and not the subscription** — `/usage` still reports subscription state, so the
authoritative check is the spend showing up in the Anthropic console. Do not
take this file's word for it.

Same model, same quality, separate meter. Nothing about how a C-level works
changes.

## Workers on 9Router

9Router (MIT, https://github.com/decolua/9router) is a **local** proxy on
127.0.0.1:20128 that forwards to whichever provider it is configured with.

```bash
npm install -g 9router && 9router          # CEO runs this once; see "Install" below
```

Then, in the repo's gitignored `.env`:

```
WORKER_MODEL_PROVIDER=ninerouter
NINEROUTER_API_KEY=local        # a local proxy needs no real key; this var is the on-switch
WORKER_PROVIDER_MODEL=...       # optional: whichever model 9Router is set to serve
```

Unset `WORKER_MODEL_PROVIDER` and every worker is back on Claude. That is the
whole rollback.

### Four guards, all verified 2026-09-19

1. **No key → Claude.** A missing `NINEROUTER_API_KEY` spawns Claude rather than
   a broken endpoint.
2. **`model_hint='claude'` → Claude**, whatever the flag says. The CTO sets this
   per task for review, repair and security work (dev-spawn-protocol §0).
3. **`security_engineer` and `devops` never offload** — they are outside
   `WORKER_PROVIDER_ROLES`' default list, so the flag cannot reach them.
4. **The automatic router can never choose 9Router.** `WORKER_MODEL_PROVIDER=auto`
   only ever decides between Claude and Z.ai; anything else degrades to Claude.
   Reaching 9Router takes a human typing its name. A prompt carries this repo's
   code, the wiki, business context and whatever files were just read — an
   automatic path may not send that to a provider nobody named.

### What this does NOT do — automatic switching on limit

**There is no working auto-fallback today.** `WORKER_MODEL_PROVIDER=auto` exists
and compares live headroom, but its Claude-side signal is the VPS usage monitor,
which has returned null since 2026-08-21 (LungNote 8bba985c). With no signal it
degrades to Claude — correctly, but that means it can never notice the limit is
spent. Z.ai, the other half of that comparison, was cancelled on 2026-09-19.

So: **flipping to the fallback is a human action today.** Making it automatic
needs the VPS monitor repaired first, and then a decision about whether 9Router
belongs in an automatic path at all (guard 4 above says no as written).

While fixing the crash that exposed this: both headroom fetchers promised to
"fail safe to claude" but caught `KeyError` and not `TypeError`, so a null block
in the JSON crashed the spawn instead of degrading. Fixed the same day.

## Install (the CEO runs this; the org's classifier refuses it)

Claude Code's auto-mode classifier blocks `npm install 9router` as
[Data Exfiltration] — correctly, for a tool whose job is to forward prompts to
third parties. So it is installed by hand, once:

```
! npm install -g 9router && 9router
```

The dashboard opens on http://localhost:20128. Configure providers there, then
set the two `.env` lines above and spawn a worker to test.

## The rule this serves

IRON-RULES Section 53 cut the org's biggest consumer (repeated browser work now
runs as a script, not a model). This file covers what is left: when the meter
still runs out, work continues — on a cheaper lane for mechanical work, and on
the credit lane for the judgement calls.
