#!/usr/bin/env python3
"""
Fusion multi-model query — send one prompt to several LLMs via OpenRouter,
show every answer side by side, optional synthesis pass.

Idea source: GH mooniex-agents#22 (OpenRouter Fusion API concept, CEO 2026-06-15).

Usage:
    python3 scripts/fusion_query.py "prompt text"
    python3 scripts/fusion_query.py "prompt text" --models openai/gpt-4o,google/gemini-2.5-pro --confirm
    python3 scripts/fusion_query.py "prompt text" --confirm --synthesize

Guardrail (ASK-before-paid-API, IRON rule): without --confirm this only
prints the call plan and exits — zero spend. Pass --confirm after the CEO
has said OK to the cost.

Key: reads OPENROUTER_API_KEY from env. That key is already provisioned for
webapp + claudeflow (see LLMs/playbooks/api-key-registry.md) — copy the same
value into Agents/.env, do not mint a new one (IRON §34).
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DEFAULT_MODELS = [
    "openai/gpt-4o",
    "google/gemini-2.5-pro",
    "deepseek/deepseek-chat",
]
DEFAULT_SYNTHESIZER = "anthropic/claude-sonnet-4"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_model(model: str, prompt: str, api_key: str) -> str:
    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Query multiple LLMs via OpenRouter and compare answers")
    ap.add_argument("prompt")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS), help="comma-separated OpenRouter model ids")
    ap.add_argument("--synthesize", action="store_true", help="add one extra call that merges all answers")
    ap.add_argument("--synthesizer", default=DEFAULT_SYNTHESIZER, help="model id for the synthesis pass")
    ap.add_argument("--confirm", action="store_true", help="actually spend money — omit to just preview the plan")
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    n_calls = len(models) + (1 if args.synthesize else 0)

    if not args.confirm:
        print(f"[PLAN] would call {n_calls} model(s) via OpenRouter:")
        for m in models:
            print(f"  - {m}")
        if args.synthesize:
            print(f"  - {args.synthesizer} (synthesis pass)")
        print(f"\nPrompt: {args.prompt}")
        print("\nNo cost incurred. Re-run with --confirm once the CEO has OK'd the spend.")
        return

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "ERROR: OPENROUTER_API_KEY not set. Reuse the key already documented in "
            "LLMs/playbooks/api-key-registry.md (webapp + claudeflow) — copy that value "
            "into Agents/.env. Do not mint a new key.",
            file=sys.stderr,
        )
        sys.exit(1)

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(models)) as ex:
        futures = {ex.submit(call_model, m, args.prompt, api_key): m for m in models}
        for fut in as_completed(futures):
            m = futures[fut]
            try:
                results[m] = fut.result()
            except Exception as e:
                results[m] = f"[ERROR] {e}"

    for m in models:
        print(f"\n{'=' * 60}\n{m}\n{'=' * 60}")
        print(results[m])

    if args.synthesize:
        merged_prompt = f"Original question:\n{args.prompt}\n\n" \
            "Below are answers from multiple AI models. Compare them, note where " \
            "they agree or disagree, then give one final synthesized answer.\n\n"
        for m in models:
            merged_prompt += f"--- {m} ---\n{results[m]}\n\n"
        print(f"\n{'=' * 60}\nSYNTHESIS ({args.synthesizer})\n{'=' * 60}")
        try:
            print(call_model(args.synthesizer, merged_prompt, api_key))
        except Exception as e:
            print(f"[ERROR] synthesis failed: {e}")


if __name__ == "__main__":
    main()
