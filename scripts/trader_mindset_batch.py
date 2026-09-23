#!/usr/bin/env python3
"""TraderMindset batch generator (permanent, reusable every round).

Refactor of the proven throwaway recipe scripts/_tmp_gen_pb_v9.py into a
durable pipeline per the CEO-approved operating model (LLMs wiki
projects/trader-mindset-automation.md): 10 items/round -> Gmail approve
-> FB post queue. THIS script owns the GENERATE side only.

Pipeline per item:
  [1] TOPIC    pick unused topics from data/trader-mindset-topics.json
  [2] CAPTION  OpenRouter LLM -> Thai caption + short poster sub-line + tags
  [3] POSTER   fal gpt-image-2/edit bakes ONLY the short hero word (navy+gold,
               identity ref, top-right + lower band kept clean) -- hybrid
               policy wiki section 3.5: long lines are NEVER baked.
  [4] COMPOSITE  Pillow (libraqm) draws the sub-line in the clean lower band
               with the pinned IBM Plex Sans Thai font -> 100% correct Thai.
  [5] STAMP    composite moon+MOONIEX lockup top-right (+shadow) -- v9 logic.
  [6] OUTPUT   output/trader-mindset/round-<NNN>/ : <slug>.png x N, captions.md,
               meta.json (claudeflow parses meta.json on the approval side).

HARD RULE: no paid API is touched during development. Prove everything with
  --dry (no network, no key needed) and the composite unit test
  (scripts/test_trader_mindset_batch.py). The first real run is executed by
  the CTO after the CEO confirms budget (ASK-before-paid).

Usage:
  PY=/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python
  $PY scripts/trader_mindset_batch.py --dry                 # no API, prints plan
  $PY scripts/trader_mindset_batch.py --dry --count 3
  $PY scripts/trader_mindset_batch.py                       # REAL run (CTO only)
  $PY scripts/trader_mindset_batch.py --lessons lessons.json
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

# Prompt text lives in versioned files under prompts/trader-mindset/, loaded via
# the local tm_prompts registry module (no network/key — safe under --dry).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tm_prompts  # noqa: E402  (local module; sys.path set on the line above)

# --------------------------------------------------------------------------- #
# Paths & constants
# --------------------------------------------------------------------------- #
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_PATH = os.path.join(REPO, "data", "trader-mindset-topics.json")
OUT_ROOT = os.path.join(REPO, "output", "trader-mindset")
FONT_SEMIBOLD = os.path.join(REPO, "assets", "fonts", "IBMPlexSansThai-SemiBold.ttf")
FONT_REGULAR = os.path.join(REPO, "assets", "fonts", "IBMPlexSansThai-Regular.ttf")

# Identity reference + transparent lockup come from the proven v9 asset set.
# Overridable so the script is portable across machines / CI.
REF_CROP = os.environ.get(
    "TM_REF_CROP", "/Users/gob/MoonieXHQ/Agents/Core/output/personal-brand/_ref_crop.png")
LOCKUP = os.environ.get(
    "TM_LOCKUP", "/Users/gob/MoonieXHQ/Agents/Core/output/personal-brand/lockup-vertical.png")

# Secrets live in the claudeflow .env (same file v9 reads), never in this repo.
ENV_PATH = os.environ.get("TM_ENV_PATH", "/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env")

# fal image endpoint (identical to v9) + OpenRouter for the caption text.
FAL_ENDPOINT = "https://fal.run/openai/gpt-image-2/edit"
FAL_IMAGE_SIZE = "square_hd"          # match v9 (1:1). Composite adapts to any size.
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
CAPTION_MODEL = os.environ.get("TM_CAPTION_MODEL", "anthropic/claude-sonnet-4-6")

NAVY = (12, 28, 43)        # #0c1c2b
NAVY_DEEP = (10, 22, 34)   # #0a1622
GOLD = (205, 172, 101)     # #cdac65
WHITE = (245, 245, 245)

# Poster art styles + scenes, the identity/palette preamble, and the caption
# hard-rules were externalized to prompts/trader-mindset/{poster,caption}-v1.md
# (registry-driven, loaded via tm_prompts). build_poster_prompt /
# build_caption_messages assemble from the ACTIVE versions. NAVY/GOLD above stay
# here — they are composite colors, not prompt text.


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    """Current UTC time as ISO-8601, e.g. 2026-06-11T12:00:00Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_env_key(name: str) -> str:
    """Read a single KEY=value from the claudeflow .env (same approach as v9)."""
    try:
        text = open(ENV_PATH, encoding="utf-8").read()
    except OSError as e:
        sys.exit(f"cannot read env file {ENV_PATH}: {e}")
    m = re.search(rf"^{re.escape(name)}=(.+)$", text, re.M)
    if not m:
        sys.exit(f"{name} not found in {ENV_PATH}")
    return m.group(1).strip().strip('"').strip("'")


def load_topics() -> dict:
    with open(TOPICS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_topics(doc: dict) -> None:
    with open(TOPICS_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def pick_topics(doc: dict, count: int) -> list[dict]:
    """Unused (used_at == null) first, preserving file order for stable rotation."""
    topics = doc["topics"]
    unused = [t for t in topics if not t.get("used_at")]
    chosen = unused[:count]
    if len(chosen) < count:  # pool exhausted -> top up with least-recently-used
        used = sorted((t for t in topics if t.get("used_at")), key=lambda t: t["used_at"])
        chosen += used[: count - len(chosen)]
    return chosen


def next_round_dir() -> tuple[int, str]:
    """Return (round_number, abspath) for the next round-<NNN> folder."""
    os.makedirs(OUT_ROOT, exist_ok=True)
    existing = [d for d in os.listdir(OUT_ROOT) if re.fullmatch(r"round-\d+", d)]
    nums = [int(d.split("-")[1]) for d in existing]
    n = (max(nums) + 1) if nums else 1
    return n, os.path.join(OUT_ROOT, f"round-{n:03d}")


def lessons_block(lessons_path: str | None) -> str:
    """Format prior-round reject reasons into a 'do-not-repeat' block, or ''."""
    if not lessons_path:
        return ""
    with open(lessons_path, encoding="utf-8") as f:
        lessons = json.load(f)
    if not lessons:
        return ""
    lines = [f"- ({l.get('date', '?')}) {l.get('slug', '?')}: {l.get('reason', '')}".rstrip()
             for l in lessons]
    return "ข้อห้ามจากรอบก่อน (อย่าทำผิดซ้ำ):\n" + "\n".join(lines)


# --------------------------------------------------------------------------- #
# Prompt builders (pure -- exercised by --dry, no network)
# --------------------------------------------------------------------------- #
def build_poster_prompt(topic: dict, idx: int, lessons: str = "") -> str:
    """fal prompt: bake ONLY the short hero word; keep lower band + top-right clean.

    Assembled from the ACTIVE poster prompt (prompts/trader-mindset/poster-v<N>.md):
    rotate art_styles[idx] + scenes[idx], fill the template, then append the
    non-rendering lessons guidance when prior-round rejects are supplied.
    """
    p = tm_prompts.load_prompt("poster")
    styles, scenes = tm_prompts.as_list(p["art_styles"]), tm_prompts.as_list(p["scenes"])
    prompt = tm_prompts.render(
        p["template"], preamble=p["preamble"],
        scene=scenes[idx % len(scenes)], style=styles[idx % len(styles)],
        hero_word=topic["hero_word"])
    if lessons:
        # Prior-round reject reasons steer this round too (wiki learning loop). Marked
        # non-rendering so the image model treats it as art direction, not text to draw.
        prompt += " " + tm_prompts.render(p["lessons_guidance"], lessons=lessons.replace("\n", " "))
    return prompt


def build_caption_messages(topic: dict, lessons: str) -> list[dict]:
    """OpenRouter chat messages -> strict JSON {caption, sub_line, tags}.

    Assembled from the ACTIVE caption prompt (prompts/trader-mindset/caption-v<N>.md):
    the `system` section carries the persona + hard-rules; the `user` section is the
    topic framing + voice spec + JSON schema with {{theme}}/{{hero_word}}/{{seed_idea}}
    filled, and {{lessons}} expanded to the prior-round "do-not-repeat" block (or empty).
    """
    p = tm_prompts.load_prompt("caption")
    lessons_slot = ("\n" + lessons + "\n") if lessons else ""
    user_msg = tm_prompts.render(
        p["user"], theme=topic["theme"], hero_word=topic["hero_word"],
        seed_idea=topic["seed_idea"], lessons=lessons_slot)
    return [{"role": "system", "content": p["system"]}, {"role": "user", "content": user_msg}]


# --------------------------------------------------------------------------- #
# API calls (only reached on a REAL run, never under --dry)
# --------------------------------------------------------------------------- #
def gen_caption(topic: dict, lessons: str) -> dict:
    """Call OpenRouter -> dict(caption, sub_line, tags). Raises on hard failure."""
    key = load_env_key("OPENROUTER_API_KEY")
    payload = {
        "model": CAPTION_MODEL,
        "messages": build_caption_messages(topic, lessons),
        "temperature": 0.8,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        OPENROUTER_ENDPOINT, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://mooniex.com", "X-Title": "MoonieX TraderMindset"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    content = data["choices"][0]["message"]["content"]
    obj = _parse_json_object(content)
    caption = obj["caption"].strip()
    sub_line = obj["sub_line"].strip()
    tags = obj.get("tags") or []
    if isinstance(tags, str):
        tags = tags.split()
    _assert_caption_clean(caption, sub_line)
    return {"caption": caption, "sub_line": sub_line, "tags": tags}


def _parse_json_object(content: str) -> dict:
    """Tolerant JSON extraction (handles ```json fences or stray prose)."""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", content).strip()
    try:
        # strict=False: tolerate literal newlines/control chars inside strings
        # (Sonnet sometimes emits real newlines in caption values — round-003).
        return json.loads(content, strict=False)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            raise
        return json.loads(m.group(0), strict=False)


_EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF" "\U00002B00-\U00002BFF" "️" "]")


def _assert_caption_clean(caption: str, sub_line: str) -> None:
    """Guard the CEO hard-rules before an item is accepted."""
    blob = caption + "\n" + sub_line
    if _EMOJI_RE.search(blob):
        raise ValueError("caption contains emoji (violates hard rule)")
    banned = ["การันตี", "การันตีกำไร", "รับรองกำไร", "รวยแน่", "ได้แน่นอน"]
    for b in banned:
        if b in blob:
            raise ValueError(f"caption contains banned guarantee phrase: {b}")


def gen_poster_base(prompt: str, dest: str) -> None:
    """Call fal gpt-image-2/edit with the identity ref -> save base png at dest."""
    key = load_env_key("FAL_API_KEY")
    uri = "data:image/png;base64," + base64.b64encode(open(REF_CROP, "rb").read()).decode()
    payload = {"prompt": prompt, "image_urls": [uri], "image_size": FAL_IMAGE_SIZE,
               "quality": "high", "num_images": 1, "output_format": "png"}
    req = urllib.request.Request(
        FAL_ENDPOINT, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"fal HTTP {e.code}: {e.read().decode()[:300]}") from e
    imgs = data.get("images") or []
    if not imgs:
        raise RuntimeError(f"fal returned no images: {json.dumps(data)[:200]}")
    urllib.request.urlretrieve(imgs[0]["url"], dest)


# --------------------------------------------------------------------------- #
# Image composition (pure Pillow -- unit tested with dummy images, no network)
# --------------------------------------------------------------------------- #
def _font(path: str, size: int):
    from PIL import ImageFont
    # RAQM layout engine = correct Thai shaping (vowels/tone marks positioned right).
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def _fit_lines(draw, text: str, font_path: str, max_width: int,
               max_size: int, min_size: int, max_lines: int = 2):
    """Largest font size (<= max_size) that fits text in <= max_lines of max_width.

    Returns (font, [lines]). Wraps on spaces when present; otherwise keeps the
    text on one shaped line and shrinks until it fits (or hits min_size).
    """
    words = text.split(" ")
    for size in range(max_size, min_size - 1, -2):
        font = _font(font_path, size)
        if len(words) == 1:
            if draw.textlength(text, font=font) <= max_width:
                return font, [text]
            continue
        # greedy word wrap at this size
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if draw.textlength(trial, font=font) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) <= max_lines and all(draw.textlength(l, font=font) <= max_width for l in lines):
            return font, lines
    # fallback: smallest size, single shaped line (sub-lines are short by spec)
    return _font(font_path, min_size), [text]


def composite_subline(img, sub_line: str):
    """Draw the poster sub-line into the reserved clean lower band.

    Adds a soft navy gradient scrim for legibility, then renders the Thai
    sub-line (IBM Plex Sans Thai SemiBold, gold) centered. Pure + deterministic
    so the unit test can exercise it on a dummy image with no network.
    """
    from PIL import Image, ImageDraw
    img = img.convert("RGBA")
    W, H = img.size

    # lower-band scrim: transparent -> deep navy, bottom ~30% of the poster.
    # poster-v3 fills the whole frame with the real scene (no baked navy band),
    # so this scrim is now the ONLY darkening — keep it soft (peak ~150) so the
    # cinematic scene stays visible behind the gold sub-line (CEO C2 look).
    band_top = int(H * 0.70)
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(scrim)
    for y in range(band_top, H):
        a = int(150 * (y - band_top) / max(1, H - band_top))
        sdraw.line([(0, y), (W, y)], fill=(NAVY_DEEP[0], NAVY_DEEP[1], NAVY_DEEP[2], a))
    img.alpha_composite(scrim)

    draw = ImageDraw.Draw(img)
    max_width = int(W * 0.86)
    font, lines = _fit_lines(draw, sub_line, FONT_SEMIBOLD, max_width,
                             max_size=int(W * 0.058), min_size=int(W * 0.030))

    # vertical layout centered inside the band
    ascent, descent = font.getmetrics()
    line_h = int((ascent + descent) * 1.18)
    total_h = line_h * len(lines)
    y = int(H * 0.80) - total_h // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (W - w) // 2
        # 2px soft shadow for contrast on any baked art
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 170))
        draw.text((x, y), line, font=font, fill=GOLD + (255,))
        y += line_h
    return img


def stamp_lockup(img):
    """Composite moon+MOONIEX lockup top-right with a 2-3px shadow (v9 logic)."""
    from PIL import Image, ImageFilter
    lk0 = Image.open(LOCKUP).convert("RGBA")
    lk0 = lk0.crop(lk0.getbbox())
    im = img.convert("RGBA")
    W, H = im.size
    lw = int(W * 0.0775)
    lh = int(lw * lk0.height / lk0.width)
    lk = lk0.resize((lw, lh))
    x = W - lw - int(W * 0.0225)
    y = int(H * 0.02)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sil = Image.composite(Image.new("RGBA", lk.size, (0, 0, 0, 255)),
                          Image.new("RGBA", lk.size, (0, 0, 0, 0)),
                          lk.getchannel("A")).filter(ImageFilter.GaussianBlur(3))
    for off in [(3, 3), (2, 2)]:
        layer.paste(sil, (x + off[0], y + off[1]), sil)
        layer.paste(sil, (x + off[0], y + off[1]), sil)
    layer.paste(lk, (x, y), lk)
    im.alpha_composite(layer)
    return im


def render_poster(topic: dict, sub_line: str, prompt: str, dest_png: str) -> None:
    """Full poster: fal base -> composite sub-line -> stamp lockup -> save <slug>.png."""
    from PIL import Image
    base_tmp = dest_png + ".base.png"
    gen_poster_base(prompt, base_tmp)
    img = Image.open(base_tmp)
    img = composite_subline(img, sub_line)
    img = stamp_lockup(img)
    img.convert("RGB").save(dest_png)
    try:
        os.remove(base_tmp)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Output writers
# --------------------------------------------------------------------------- #
def write_captions_md(round_dir: str, round_n: int, items: list[dict]) -> None:
    lines = [f"# TraderMindset — Round {round_n:03d} ({len(items)} posts)", "",
             "Review each item below, then reply Approve / Reject <reason> per Gmail item.",
             "Caption format = claudeflow convention: a line containing only \".\" is a "
             "paragraph break; hashtags live in the `tags` line.", ""]
    for i, it in enumerate(items, 1):
        lines += [f"## {i}. {it['slug']} — {it['hero_word']} ({it['theme']})",
                  f"poster: `{os.path.basename(it['img'])}`", "", "```", it["caption"], "```",
                  "tags: " + " ".join(it["tags"]), ""]
    with open(os.path.join(round_dir, "captions.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_meta_json(round_dir: str, round_n: int, items: list[dict]) -> None:
    meta = {"round": round_n, "generated_at": now_iso(),
            "items": [{"id": it["id"], "slug": it["slug"], "theme": it["theme"],
                       "hero_word": it["hero_word"], "caption": it["caption"],
                       "sub_line": it["sub_line"], "tags": it["tags"],
                       "img": os.path.basename(it["img"]), "status": "generated"}
                      for it in items]}
    with open(os.path.join(round_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")


# --------------------------------------------------------------------------- #
# Modes
# --------------------------------------------------------------------------- #
def run_dry(topics_doc: dict, count: int, lessons: str) -> None:
    chosen = pick_topics(topics_doc, count)
    round_n, round_dir = next_round_dir()
    print(f"[DRY] no API calls. round={round_n:03d} dir={round_dir}")
    print(f"[DRY] env file would be: {ENV_PATH} (keys: OPENROUTER_API_KEY, FAL_API_KEY)")
    if lessons:
        print(f"[DRY] lessons block injected into prompts:\n{lessons}\n")
    for i, t in enumerate(chosen):
        slug = t["slug"]
        print("=" * 78)
        print(f"[{i+1}/{len(chosen)}] {t['id']} {slug}  theme={t['theme']}  hero={t['hero_word']}")
        print(f"  seed_idea : {t['seed_idea']}")
        print(f"  -> caption LLM ({CAPTION_MODEL}) messages:")
        for m in build_caption_messages(t, lessons):
            print(f"     [{m['role']}] {m['content']}")
        print(f"  -> poster fal prompt ({FAL_IMAGE_SIZE}):")
        print(f"     {build_poster_prompt(t, i, lessons)}")
        print(f"  -> would write: {os.path.join(round_dir, slug + '.png')}")
    print("=" * 78)
    print(f"[DRY] would also write: {os.path.join(round_dir, 'captions.md')}")
    print(f"[DRY] would also write: {os.path.join(round_dir, 'meta.json')}")
    print(f"[DRY] would mark used_at on {len(chosen)} topics. NO files written, NO topics marked.")


def run_real(topics_doc: dict, count: int, lessons: str) -> None:
    chosen = pick_topics(topics_doc, count)
    round_n, round_dir = next_round_dir()
    os.makedirs(round_dir, exist_ok=True)
    print(f"[REAL] round={round_n:03d} dir={round_dir} count={len(chosen)}")
    stamp = now_iso()
    items: list[dict] = []
    for i, t in enumerate(chosen):
        slug = t["slug"]
        print(f"[{i+1}/{len(chosen)}] {slug} ...")
        cap = gen_caption(t, lessons)
        dest_png = os.path.join(round_dir, slug + ".png")
        prompt = build_poster_prompt(t, i, lessons)
        render_poster(t, cap["sub_line"], prompt, dest_png)
        t["used_at"] = stamp                       # mark only on full success
        items.append({**t, "caption": cap["caption"], "sub_line": cap["sub_line"],
                      "tags": cap["tags"], "img": dest_png})
        save_topics(topics_doc)                    # persist incrementally
        print(f"   ok -> {dest_png}")
    write_captions_md(round_dir, round_n, items)
    write_meta_json(round_dir, round_n, items)
    print(f"[REAL] done. {len(items)} items in {round_dir}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TraderMindset batch generator")
    ap.add_argument("--dry", action="store_true",
                    help="no API calls: print chosen topics, prompts, and target paths")
    ap.add_argument("--count", type=int, default=10, help="items per round (default 10)")
    ap.add_argument("--lessons", metavar="PATH",
                    help="JSON [{slug,reason,date}] of prior-round rejects to avoid")
    args = ap.parse_args(argv)

    topics_doc = load_topics()
    lessons = lessons_block(args.lessons)
    if args.dry:
        run_dry(topics_doc, args.count, lessons)
    else:
        run_real(topics_doc, args.count, lessons)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
