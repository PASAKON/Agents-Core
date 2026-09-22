#!/usr/bin/env python3
"""Measure MYPASAKON's real speaking-style signature from the transcribed corpus.
Produces the numbers demanded by TASK.md step 2. Run with the scratchpad venv
that has pythainlp installed (word segmentation needed for Thai n-grams, which
have no whitespace word boundaries).
"""
import glob
import json
import re
from collections import Counter
from pathlib import Path

from pythainlp.tokenize import word_tokenize

HERE = Path(__file__).resolve().parent

TARGET_TERMS = ["นะครับ", "ครับ", "ก็คือ", "เนี่ย", "นะฮะ", "ผม",
                "เพื่อนๆ", "ทุกคน", "คุณ", "จริงๆ", "เลย", "แบบ", "คือ"]

RAWCUT_FILES = sorted(
    glob.glob(str(HERE / "transcripts" / "*.txt")),
    key=lambda p: int(Path(p).name.split("-", 1)[0]),
)
CORPUS_FILES = RAWCUT_FILES + [str(HERE / "SPOKEN_A.txt"), str(HERE / "SPOKEN_C.txt")]


def load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=ครับ)|(?<=ฮะ)", text)
    return [p.strip() for p in parts if p.strip()]


def main() -> None:
    corpus_texts = [load(p) for p in CORPUS_FILES]
    full_text = "\n".join(corpus_texts)
    total_chars = len(full_text)

    # 1. frequency per 1000 chars
    freq = {}
    for term in TARGET_TERMS:
        n = full_text.count(term)
        freq[term] = round(n / total_chars * 1000, 2)

    # 2. n-gram 2-5 words, top 30
    ngram_counter: Counter[str] = Counter()
    for text in corpus_texts:
        tokens = [t for t in word_tokenize(text, engine="newmm") if t.strip()]
        for n in range(2, 6):
            for i in range(len(tokens) - n + 1):
                gram = "".join(tokens[i:i + n])
                if len(gram) < 3:
                    continue
                ngram_counter[gram] += 1
    top_ngrams = ngram_counter.most_common(30)

    # 3/4. openings and closings from the 19 rawcut clips only
    openings = []
    closings = []
    for p in RAWCUT_FILES:
        idx = Path(p).name.split("-", 1)[0]
        text = load(p)
        sents = sentence_split(text)
        if not sents:
            continue
        openings.append((idx, sents[0]))
        closings.append((idx, sents[-2:] if len(sents) >= 2 else sents))

    # 5. average sentence length (cut at นะครับ/ครับ)
    all_sent_lens = []
    for text in corpus_texts:
        for s in sentence_split(text):
            all_sent_lens.append(len(s))
    avg_sent_len = sum(all_sent_lens) / len(all_sent_lens) if all_sent_lens else 0

    # 6. immediate unintentional repetition (adjacent duplicate token runs)
    repeats = []
    for p, text in zip(CORPUS_FILES, corpus_texts):
        tokens = [t for t in word_tokenize(text, engine="newmm") if t.strip()]
        i = 0
        while i < len(tokens):
            found = False
            for L in range(8, 1, -1):  # longest run first to avoid double-count
                if i + 2 * L <= len(tokens) and tokens[i:i + L] == tokens[i + L:i + 2 * L]:
                    phrase = "".join(tokens[i:i + L])
                    repeats.append((Path(p).name, phrase))
                    i += 2 * L
                    found = True
                    break
            if not found:
                i += 1

    report = {
        "total_corpus_chars": total_chars,
        "n_files": len(CORPUS_FILES),
        "freq_per_1000_chars": freq,
        "top_ngrams": top_ngrams,
        "openings": openings,
        "closings": closings,
        "avg_sentence_len_chars": round(avg_sent_len, 1),
        "n_sentences": len(all_sent_lens),
        "immediate_repeats": repeats,
        "n_immediate_repeats": len(repeats),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
