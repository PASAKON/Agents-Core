#!/usr/bin/env bash
# Borrow ONE MCP server for ONE question — from inside a session that does not
# have that server loaded.
#
# The problem this solves: a CXO session launches with --strict-mcp-config, so
# its MCP set is frozen at spawn time. `claude mcp add` writes to a config file
# that strict mode ignores, so there is no way to attach a server mid-session.
# The alternatives all cost something real: relaunching drops the tab, turning
# strict off reloads ~13 servers, and delegating spins up a whole other C-level.
#
# This runs a throwaway headless `claude -p` with exactly one server and exactly
# the tools that server contributes. It answers, prints to stdout, and dies —
# the MCP server is its child, so it dies too. The calling session keeps its
# conversation and never pays for the server.
#
# Token economy is the whole point, so the subprocess is stripped to the studs:
#   --tools ""                  no built-in tools (no Bash/Read/Edit schemas)
#   --setting-sources ""        no user/project/local settings, so no hooks, no
#                               plugins, no skill catalog, no CLAUDE.md
#   --system-prompt             REPLACES Claude Code's system prompt with two
#                               lines (the single biggest saving)
#   --exclude-dynamic-system-prompt-sections
#   --no-chrome                 the Chrome connector is built-in and survives
#                               --strict-mcp-config, so it must be named to go
#   --no-session-persistence    no transcript on disk for a one-shot
#   --model sonnet-5 (default)  CEO call 2026-08-07 on the bench evidence below:
#                               haiku's savings are not worth a wrong answer
#
# PREFER --raw FOR DATA. --raw skips the model entirely and speaks MCP over
# stdio, so it costs zero tokens and returns exactly what the tool returned.
# The bench that built this script is the argument: asked "how many open
# todos", the two models produced 50, 53, 7 and 193 across two runs — the
# answer was 193, and --raw gets it in ~2s. A model in the loop is worth it
# only when the task needs judgment (pick the best reference, summarize a
# thread), not when it needs a number.
#
# The mechanism behind that flakiness, measured: a large tool result never
# reaches the model. list_todos with limit=500 returns ~91k characters, which
# Claude Code spills to a file and replaces with "exceeds maximum allowed
# tokens" — so a model-mediated borrow over a big payload is unreliable by
# construction, not merely imprecise. --raw has no such ceiling.
#
# Usage:
#   # zero-token data fetch (preferred)
#   scripts/mcp-borrow.sh --server lungnote --raw list_todos '{"limit":500}'
#   scripts/mcp-borrow.sh --server supabase --list
#
#   # model-mediated, for judgment tasks
#   scripts/mcp-borrow.sh --server meigen "find navy+gold poster references"
#   scripts/mcp-borrow.sh --server meigen --model claude-sonnet-5 "pick the best 3"
#   scripts/mcp-borrow.sh --server lungnote --bench "count open todos"
#
# Flags:
#   --server NAME   one of cxo_mcp_config.py's known servers (required)
#   --raw TOOL JSON call TOOL directly with JSON arguments; no model, no tokens
#   --list          list the tools that server exposes, then exit
#   --tools LIST    space/comma list of mcp__ tool names the model may call;
#                   default = every tool that server contributes per SERVER_TOOLS
#   --model M       default claude-sonnet-5. Pass haiku only for a passthrough
#                   you will eyeball — it cannot be trusted to count or
#                   aggregate over a payload (see --bench).
#   --json          emit the raw result JSON (usage + cost) instead of the answer
#   --bench         run the SAME prompt on haiku and sonnet, print a comparison
#   --keep-config   leave the temp MCP config on disk (debugging)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GEN="$ROOT/scripts/lib/cxo_mcp_config.py"

HAIKU="claude-haiku-4-5-20251001"
SONNET="claude-sonnet-5"

SERVER=""
TOOLS=""
# Sonnet 5, not haiku: the bench that shipped with this script had haiku answer
# 7 to a question whose answer was 193. A borrow that needs a model at all is a
# borrow that needs the answer right, and the cheap path for plain data is
# --raw (no model), not a weaker model. CEO decision 2026-08-07.
MODEL="$SONNET"
FMT="text"
BENCH=0
KEEP=0
PROMPT=""
RAW_TOOL=""
RAW_ARGS="{}"
LIST=0

usage() { sed -n '2,58p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --server) SERVER="${2:-}"; shift 2 ;;
    --tools)  TOOLS="${2:-}"; shift 2 ;;
    --model)  MODEL="${2:-}"; shift 2 ;;
    --json)   FMT="json"; shift ;;
    --bench)  BENCH=1; shift ;;
    --list)   LIST=1; shift ;;
    --raw)
      RAW_TOOL="${2:-}"
      # The JSON argument is optional; only consume it when it looks like one,
      # so `--raw list_todos` alone means "no arguments".
      case "${3:-}" in
        \{*) RAW_ARGS="$3"; shift 3 ;;
        *) shift 2 ;;
      esac
      ;;
    --keep-config) KEEP=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; PROMPT="$*"; break ;;
    -*) echo "mcp-borrow: unknown flag $1 (try --help)" >&2; exit 2 ;;
    *)  PROMPT="$*"; break ;;
  esac
done

[ -n "$SERVER" ] || { echo "mcp-borrow: --server is required (try --help)" >&2; exit 2; }

# --raw / --list need no model, no temp config, and no prompt: hand straight
# off to the protocol client. This is the cheap path and the default advice.
if [ "$LIST" = "1" ] || [ -n "$RAW_TOOL" ]; then
  if [ "$LIST" = "1" ]; then
    exec python3 "$ROOT/scripts/lib/mcp_call.py" --server "$SERVER" --root "$ROOT" --list
  fi
  exec python3 "$ROOT/scripts/lib/mcp_call.py" --server "$SERVER" --root "$ROOT" \
    --tool "$RAW_TOOL" --args "$RAW_ARGS"
fi

[ -n "$PROMPT" ] || { echo "mcp-borrow: no prompt given (try --help)" >&2; exit 2; }

# The server entry and its tool list both come from cxo_mcp_config.py, so a
# borrow gets the same command line, flags, and read-only guards a role launch
# would give that server — one source of truth, no second copy to drift.
CFG="$(mktemp "${TMPDIR:-/tmp}/mcp-borrow-XXXXXX")"
mv "$CFG" "$CFG.json"
CFG="$CFG.json"
BENCH_OUT=""
cleanup() {
  [ "$KEEP" = "1" ] || rm -f "$CFG"
  [ -z "$BENCH_OUT" ] || rm -rf "$BENCH_OUT"
}
trap cleanup EXIT INT TERM

python3 "$GEN" --servers "$SERVER" --root "$ROOT" --out "$CFG"
if [ -z "$TOOLS" ]; then
  TOOLS="$(python3 "$GEN" --servers "$SERVER" --root "$ROOT" --print-allowed --no-builtins)"
fi
[ -n "$TOOLS" ] || {
  echo "mcp-borrow: no pre-approved tools known for '$SERVER' — pass --tools explicitly" >&2
  exit 3
}
TOOLS="$(printf '%s' "$TOOLS" | tr ',' ' ')"

# Replaces Claude Code's system prompt entirely. Deliberately blunt: a borrow is
# a data fetch, and every sentence here is billed on every call.
SIDECAR_PROMPT="You are a data-fetch worker with one job: call the MCP tool you have been given and report what it returned.
Output ONLY the requested data, as compact plain text. No preamble, no explanation, no markdown, no restating the question. If a tool call fails, output the error verbatim on one line."

run_one() {  # run_one <model> <output-format> -> stdout
  claude -p "$PROMPT" \
    --mcp-config "$CFG" --strict-mcp-config \
    --tools "" --allowed-tools $TOOLS \
    --no-chrome --no-session-persistence \
    --setting-sources "" --exclude-dynamic-system-prompt-sections \
    --system-prompt "$SIDECAR_PROMPT" \
    --model "$1" --output-format "$2" < /dev/null
}

if [ "$BENCH" = "0" ]; then
  run_one "$MODEL" "$FMT"
  exit 0
fi

# --bench: same prompt, same server, same tools, two models. Answers the one
# question that decides the default model — does the cheap one return the same
# data? The comparison prints both answers in full, so a mismatch is visible
# rather than asserted.
echo "mcp-borrow --bench: server=$SERVER tools=$(printf '%s' "$TOOLS" | wc -w | tr -d ' ')" >&2
echo "prompt: $PROMPT" >&2
BENCH_OUT="$(mktemp -d "${TMPDIR:-/tmp}/mcp-bench-XXXXXX")"

for m in "$HAIKU" "$SONNET"; do
  echo >&2
  echo "-- running $m ..." >&2
  START=$(python3 -c 'import time;print(int(time.time()*1000))')
  run_one "$m" json > "$BENCH_OUT/$m.json" 2>"$BENCH_OUT/$m.err" || {
    echo "   FAILED — stderr tail:" >&2
    tail -3 "$BENCH_OUT/$m.err" >&2
  }
  END=$(python3 -c 'import time;print(int(time.time()*1000))')
  echo "$((END - START))" > "$BENCH_OUT/$m.wall"
done

python3 - "$BENCH_OUT" "$HAIKU" "$SONNET" <<'PY'
import json, sys
from pathlib import Path

out = Path(sys.argv[1])
models = sys.argv[2:]
rows, results = [], {}
for m in models:
    p = out / f"{m}.json"
    wall = out / f"{m}.wall"
    if not p.exists() or not p.read_text().strip():
        rows.append((m, "<no output>", 0, 0, 0, 0.0, 0))
        continue
    d = json.loads(p.read_text())
    u = d.get("usage", {})
    results[m] = (d.get("result") or "").strip()
    rows.append((
        m,
        results[m],
        u.get("input_tokens", 0),
        u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0),
        u.get("output_tokens", 0),
        d.get("total_cost_usd", 0.0),
        int(wall.read_text().strip() or 0) if wall.exists() else 0,
    ))

print()
print(f"{'model':<28} {'in':>6} {'cache':>8} {'out':>6} {'cost USD':>10} {'wall s':>7}")
print("-" * 70)
for m, _res, i, c, o, cost, wall in rows:
    print(f"{m:<28} {i:>6} {c:>8} {o:>6} {cost:>10.4f} {wall / 1000:>7.1f}")

print()
for m, res, *_ in rows:
    print(f"[{m}] {res[:400]}{'...' if len(res) > 400 else ''}")

if len(results) == 2:
    a, b = (results[m] for m in models)
    print()
    print("IDENTICAL ANSWER" if a == b
          else "DIFFERENT ANSWER — read both above before trusting the cheap model")
    if rows[0][5] and rows[1][5]:
        print(f"cost ratio: sonnet is {rows[1][5] / rows[0][5]:.1f}x haiku")
PY
