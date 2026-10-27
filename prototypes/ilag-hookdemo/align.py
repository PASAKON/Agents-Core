"""Alignment parser for the ILAG hook demo (task-ee1dbcf0): map each phrase of phrases.json onto a character alignment.

Accepts ONE shape, the ElevenLabs alignment:
  {"characters": [...], "character_start_times_seconds": [...], "character_end_times_seconds": [...]}
Anything else, or a phrase that cannot be found in it, exits non-zero and says what and which phrase.  A phrase is
matched by character offset: spaces and punctuation are ignored on both sides (narration.txt has "เก็บแปดหมื่น!" where
phrases.json has "เก็บแปดหมื่น"), phrases are searched in order, each after the end of the one before.

Also accepts fal's ElevenLabs v4 file, {"audio": {...}, "timestamps": [chunk, ...]}, where every chunk is the shape above with
times already absolute (load_fal / load_alignment): the chunks are joined in order into one alignment.  It fails when a chunk lacks
a key, a time goes backwards, or the joined characters differ from narration.txt (whitespace and "..." ignored).

library:  phrase_times(align_dict, phrases) -> [[(start, end), ...] per line]   raises AlignError(message)
          load_alignment(path, narration_path) -> plain alignment dict (plain or fal file)
cli:      align.py <align.json> <phrases.json> [--narration narration.txt] [--out times.json]     prints one row per phrase
"""
import json
import sys
import unicodedata
from pathlib import Path

KEYS = ("characters", "character_start_times_seconds", "character_end_times_seconds")


class AlignError(Exception):
    pass


def keep(ch):
    """A character that counts when matching: not whitespace, not punctuation."""
    return not (ch.isspace() or unicodedata.category(ch)[0] in "ZPC")


def check_shape(a):
    if not isinstance(a, dict):
        raise AlignError(f"alignment must be a JSON object with {', '.join(KEYS)}; got {type(a).__name__}")
    missing = [k for k in KEYS if k not in a]
    if missing:
        raise AlignError(f"alignment is not the ElevenLabs shape: missing {', '.join(missing)}; top-level keys are "
                         f"{sorted(a)[:12]}")
    extra = [k for k in a if k not in KEYS]
    if extra:
        raise AlignError(f"alignment is not the plain ElevenLabs shape: unexpected key(s) {', '.join(map(str, extra))}")
    ch, st, en = (a[k] for k in KEYS)
    for k, v in zip(KEYS, (ch, st, en)):
        if not isinstance(v, list) or not v:
            raise AlignError(f"{k} must be a non-empty list")
    if not (len(ch) == len(st) == len(en)):
        raise AlignError(f"array lengths differ: characters {len(ch)}, starts {len(st)}, ends {len(en)}")
    for i, c in enumerate(ch):
        if not isinstance(c, str) or not c:
            raise AlignError(f"characters[{i}] is {c!r}, expected a non-empty string")
    for k, v in (("character_start_times_seconds", st), ("character_end_times_seconds", en)):
        for i, x in enumerate(v):
            if isinstance(x, bool) or not isinstance(x, (int, float)) or x != x or x < 0:
                raise AlignError(f"{k}[{i}] is {x!r}, expected a number of seconds >= 0")
    for i in range(len(ch)):
        if en[i] < st[i] - 1e-9:
            raise AlignError(f"character {i} {ch[i]!r} ends ({en[i]}) before it starts ({st[i]})")
    return ch, st, en


def phrase_times(a, phrases):
    ch, st, en = check_shape(a)
    flat, owner = [], []  # the kept characters, and the alignment index each came from
    for i, c in enumerate(ch):
        for u in c:
            if keep(u):
                flat.append(u)
                owner.append(i)
    text = "".join(flat)
    cur, out = 0, []
    for li, line in enumerate(phrases, 1):
        row = []
        for pi, ph in enumerate(line, 1):
            want = "".join(u for u in ph if keep(u))
            name = f"line {li} phrase {pi} {ph!r}"
            if not want:
                raise AlignError(f"{name}: nothing to match once spaces and punctuation are dropped")
            at = text.find(want, cur)
            if at < 0:
                after = owner[cur - 1] if 0 < cur <= len(owner) else 0
                raise AlignError(f"{name} cannot be found in the alignment text after character {after}")
            first, last = owner[at], owner[at + len(want) - 1]
            row.append((st[first], en[last]))
            cur = at + len(want)
        out.append(row)
    return out


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise AlignError(f"{path}: cannot read as JSON: {e}")


def squeeze(text):
    """Text as compared against the narration: no whitespace, no "..." or the one-character ellipsis."""
    return "".join(text.replace("...", "").replace("\u2026", "").split())


def join_fal(doc, narration):
    """fal's {"audio", "timestamps": [chunk...]} -> one plain alignment, chunks in order.  narration is the TTS input text."""
    if not isinstance(doc, dict) or "timestamps" not in doc:
        raise AlignError("not a fal file: no 'timestamps' key")
    chunks = doc["timestamps"]
    if not isinstance(chunks, list) or not chunks:
        raise AlignError("fal 'timestamps' must be a non-empty list of chunks")
    ch, st, en = [], [], []
    for n, c in enumerate(chunks):
        if not isinstance(c, dict):
            raise AlignError(f"fal chunk {n} is {type(c).__name__}, expected an object")
        for k in KEYS:
            if k not in c:
                raise AlignError(f"fal chunk {n} lacks '{k}' (has {sorted(c)})")
        try:
            check_shape({k: c[k] for k in KEYS})
        except AlignError as e:
            raise AlignError(f"fal chunk {n}: {e}")
        ch += c[KEYS[0]]
        st += c[KEYS[1]]
        en += c[KEYS[2]]
    for i in range(1, len(st)):
        if st[i] < st[i - 1] - 1e-9:
            raise AlignError(f"time goes backwards at character {i} {ch[i]!r}: starts {st[i]} after {ch[i - 1]!r} started {st[i - 1]}")
    got, want = squeeze("".join(ch)), squeeze(narration)
    if got != want:
        k = next((i for i, (x, y) in enumerate(zip(got, want)) if x != y), min(len(got), len(want)))
        raise AlignError(f"the fal characters do not match the narration (whitespace and '...' ignored) at offset {k}: "
                         f"alignment has {got[max(0, k - 8):k + 8]!r}, narration has {want[max(0, k - 8):k + 8]!r} "
                         f"(lengths {len(got)} vs {len(want)})")
    return {KEYS[0]: ch, KEYS[1]: st, KEYS[2]: en}


def load_alignment(path, narration_path=None):
    """A plain ElevenLabs alignment file, or a fal file (then narration_path is required and checked)."""
    doc = load(path)
    if isinstance(doc, dict) and "timestamps" in doc:
        if not narration_path:
            raise AlignError(f"{path} is a fal file: pass the narration text to check it against")
        try:
            narration = Path(narration_path).read_text(encoding="utf-8")
        except OSError as e:
            raise AlignError(f"cannot read the narration {narration_path}: {e}")
        return join_fal(doc, narration)
    return doc


if __name__ == "__main__":
    args = sys.argv[1:]
    out = narr = None
    for flag in ("--out", "--narration"):
        if flag in args:
            k = args.index(flag)
            val = args[k + 1]
            del args[k:k + 2]
            out, narr = (val, narr) if flag == "--out" else (out, val)
    if len(args) != 2:
        sys.exit(__doc__)
    try:
        ph = load(args[1])
        times = phrase_times(load_alignment(args[0], narr), ph)
    except AlignError as e:
        print(f"align.py ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    for li, (row, line) in enumerate(zip(times, ph), 1):
        for pi, ((s, e), t) in enumerate(zip(row, line), 1):
            print(f"{li}.{pi}  {s:7.3f} {e:7.3f}  {t}")
    if out:
        Path(out).write_text(json.dumps(times), encoding="utf-8")
