#!/usr/bin/env python3
"""Replay script for Fastwork.co category price research (task-acb5e1ad).

Pulls listing counts, price percentiles, and top-10-by-review-count tables
for 6 Fastwork categories, straight from their Meilisearch-backed listing
API — no browser needed.

TOKEN: the Meilisearch search key is a PUBLIC "search-only" key. Fastwork
bakes it into every page's Next.js `runtimeConfig.MEILISEARCH.API_KEY`
(shipped in the HTML `__NEXT_DATA__` blob on every category page load —
view-source on any fastwork.co listing page and it's right there). It is
not a secret and cannot write/delete, only read the public search index.

Read it from env var FASTWORK_MEILI_KEY (required — not hardcoded here on
purpose, so no token literal sits in git history even though it's public).
To get it: open any fastwork.co category page, open devtools, run

    JSON.parse(document.getElementById('__NEXT_DATA__').textContent)
        .runtimeConfig.MEILISEARCH.API_KEY

and export it:

    export FASTWORK_MEILI_KEY=<the value>
    python3 tools/fastwork_prices.py

Captured 2026-09-17: 64 hex chars, starts `e22e`, ends `8069`. It may rotate
over time — if requests start 401ing, re-extract it the same way.

Usage:
    python3 tools/fastwork_prices.py                # prints tables to stdout
    python3 tools/fastwork_prices.py --md out.md     # also writes markdown

No model, no browser — just this script and the Python standard library
(`urllib`), so it needs no `pip install` to run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

MEILI_HOST = "https://search.fastwork.co"
MEILI_INDEX = "products_th_prod"
API_KEY = os.environ.get("FASTWORK_MEILI_KEY")
if not API_KEY:
    sys.exit(
        "FASTWORK_MEILI_KEY not set. Extract it from any fastwork.co category "
        "page's __NEXT_DATA__.runtimeConfig.MEILISEARCH.API_KEY (see this "
        "file's module docstring) and export it."
    )

CATEGORIES = [
    ("video-editing", "https://fastwork.co/video-editing"),
    ("ai-video-editing", "https://fastwork.co/ai-video-editing"),
    ("ai-video", "https://fastwork.co/ai-video"),
    ("ai-tool-and-saas", "https://fastwork.co/ai-tool-and-saas"),
    ("web-development", "https://fastwork.co/web-development"),
    ("seo", "https://fastwork.co/seo"),
]


def search(filter_expr: str, *, sort=None, limit=0, offset=0, facets=None, attributesToRetrieve=None):
    body = {"q": "", "filter": [filter_expr], "limit": limit, "offset": offset}
    if sort:
        body["sort"] = sort
    if facets:
        body["facets"] = facets
    if attributesToRetrieve:
        body["attributesToRetrieve"] = attributesToRetrieve
    req = urllib.request.Request(
        f"{MEILI_HOST}/indexes/{MEILI_INDEX}/search",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from Meilisearch: {e.read().decode('utf-8', 'replace')}") from e
    if "error" in data:
        raise RuntimeError(f"Meilisearch error: {data}")
    return data


@dataclass
class Row:
    price: int
    review_count: int
    rating: float
    title: str


def percentile(sorted_vals: list[int], frac: float) -> int:
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * frac))
    return sorted_vals[idx]


def category_report(slug: str, url: str) -> dict:
    # `review_count` isn't a sortable attribute on this index, and there is
    # no server-side cap on `limit`/`offset` (verified: a 6481-hit category
    # comes back whole in one call) — so pull every listing's cheap fields
    # in one shot and rank locally instead of asking Meilisearch to sort.
    data = search(
        f'subcategory.slug = "{slug}"',
        limit=20000,
        attributesToRetrieve=["base_price", "review_count", "rating", "title"],
    )
    hits = data["hits"]
    total = data["estimatedTotalHits"]

    prices = sorted(h.get("base_price", 0) for h in hits)
    percentiles = {
        p: percentile(prices, frac)
        for p, frac in [("min", 0.0), ("p25", 0.25), ("median", 0.5), ("p75", 0.75), ("max", 0.999999)]
    }

    ranked = sorted(hits, key=lambda h: h.get("review_count", 0), reverse=True)[:10]
    top = [
        Row(
            price=h.get("base_price", 0),
            review_count=h.get("review_count", 0),
            rating=h.get("rating") or 0.0,
            title=(h.get("title") or "")[:70],
        )
        for h in ranked
    ]

    return {"slug": slug, "url": url, "total": total, "fetched": len(hits), "percentiles": percentiles, "top10": top}


def render_markdown(reports: list[dict]) -> str:
    out = []
    out.append("# Fastwork.co category price research\n")
    out.append(
        "Pulled live from the Meilisearch listing API "
        f"(`{MEILI_HOST}/indexes/{MEILI_INDEX}/search`), not the marketing page.\n"
    )
    for r in reports:
        out.append(f"\n## {r['slug']} ({r['url']})\n")
        out.append(f"- total listings: **{r['total']}** (fetched {r['fetched']} for percentile/top-10 calc)\n")
        p = r["percentiles"]
        out.append(
            f"- price THB — min: {p['min']} | p25: {p['p25']} | median: {p['median']} "
            f"| p75: {p['p75']} | max: {p['max']}\n"
        )
        out.append("\n| price THB | review count | rating | delivery days | title |")
        out.append("|---|---|---|---|---|")
        for row in r["top10"]:
            out.append(
                f"| {row.price} | {row.review_count} | {row.rating:.2f} | n/a (not in API) | {row.title} |"
            )
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", help="also write markdown to this path")
    args = ap.parse_args()

    reports = []
    for slug, url in CATEGORIES:
        print(f"fetching {slug} ...", file=sys.stderr)
        reports.append(category_report(slug, url))

    md = render_markdown(reports)
    print(md)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\nwrote {args.md}", file=sys.stderr)


if __name__ == "__main__":
    main()
