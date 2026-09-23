#!/usr/bin/env python3
"""cookierun_teachers.py -- the teacher ladder for Cookie Run's own model.

CEO 2026-09-23: the bot's own model does the work; when it is unsure, cheap
teachers check its guess, and their answers become training labels for the
next version. Every teacher answers one YES/NO question: "is the bot's guess
right?" -- checking a guess is easier and more accurate than naming a screen
from scratch.

    T1  google/gemma-4-26b-a4b-it (OpenRouter) -- replaced gpt-5-nano after the A/B, see T1 below
    T2  qwen/qwen3.7-flash       (OpenRouter)
        agree              -> accept
        disagree (1:1)     -> T3
    T3  Claude Sonnet 5 on the CEO's Claude subscription (`claude -p`), one
        image, casting vote. Capped at SONNET_DAY_USD a day -- emergencies
        only, never at the scale of the whole corpus.
        still unclear      -> human review: YES/NO plus the reason, which is
                              fed back into the questions and the weights.

    python tools/cookierun_teachers.py build-gold      # gold set from the pulled frames
    python tools/cookierun_teachers.py smoke           # 1 item per teacher, prints raw usage
    python tools/cookierun_teachers.py ab              # T1 vs T2 on the whole gold set, T3 on splits
    python tools/cookierun_teachers.py report          # re-score the saved run, no calls

Both caps live here, in code: OR_RUN_USD stops a run on OpenRouter spend
(summed usage.cost), SONNET_DAY_USD refuses T3 once today's Sonnet spend
(summed total_cost_usd from the CLI) would pass it.
"""
import argparse
import base64
import concurrent.futures as cf
import json
import os
import random
import statistics as st
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = Path(os.environ.get("TEACHER_GOLD", "/opt/MoonieXHQ/Assets/MoonieX/CookierunBot/cookierun-gold"))
STATE = ROOT / "state" / "cookierun_teachers"
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
ENV_FILE = "/home/secretary/.secretary.env"

# The CEO named gpt-5-nano:batch. OpenRouter's batch variant is refused on
# /chat/completions (404, "OpenAIBatchAdapter") and its Batch API takes image
# parts only as PUBLIC http(s) URLs -- base64/data URIs are rejected -- with a
# 24 h completion window (openrouter.ai/docs/batch-quickstart, read 2026-09-23).
# Same weights either way, so accuracy is measured on the realtime endpoint;
# batch is a 50% price switch for volume once frames have a public URL.
T1_NANO = "openai/gpt-5-nano"
# A/B on the 186-question gold set, 2026-09-23 (state/cookierun_teachers/):
#   gpt-5-nano            109/186  said YES to 67 of 93 WRONG guesses -> useless
#   qwen3.7-flash         184/186  0 yes-to-wrong   $0.0000114/q
#   gemma-4-26b-a4b-it    183/186  2 yes-to-wrong   $0.0000278/q  fastest
#   gemini-2.5-flash-lite 173/186                   $0.000168/q
#   seed-1.6-flash        153/186  33 unusable replies
# gemma + qwen agreed on 181/186, all 181 right; Sonnet settled the 5 splits,
# 5/5 right. Two families (Google, Alibaba) so their mistakes do not line up.
T1 = os.environ.get("TEACHER_T1", "google/gemma-4-26b-a4b-it")
T2 = "qwen/qwen3.7-flash"
T3 = "claude-sonnet-5"
OR_RUN_USD = float(os.environ.get("TEACHER_OR_RUN_USD", "0.10"))
SONNET_DAY_USD = float(os.environ.get("TEACHER_SONNET_DAY_USD", "1.0"))

SYSTEM = ("You check screenshots from the mobile game Cookie Run for a game bot. "
          "Look carefully at the image and answer the question about it. "
          "Reply with exactly one word: YES, NO, or UNSURE.")
SYSTEM_T3 = ("You check screenshots from the mobile game Cookie Run for a game bot. "
             "Two cheaper checkers disagreed about this image, so your answer decides. "
             "Reply with YES, NO, or UNSURE on the first line, then one short sentence "
             "saying what in the image decided it.")

# What each screen looks like, in words a teacher can check against. Only the
# screens that actually turned up in the navigator's unknown pile, 09-21/23.
SCREENS = {
    "lobby": "the main lobby: a friends leaderboard on the left, the chosen cookie in "
             "the middle, and a big green 'Play!' button at the bottom right",
    "result": "the end-of-run Result panel: a large score, Coins and XP rows, and two "
              "buttons 'OK' and 'Show Off'",
    "mystery": "the Mystery Box screen: one or more treasure boxes with question marks "
               "on a dark glowing background, and an 'Open all' button",
    "card_tries": "a card-picking mini game: a grid of cards and 'Tries left' at the top",
    "showoff_list": "a list of friends, each with a green 'Show off' button",
    "playerprofile": "a player's profile panel showing their recent and best cookie and "
                     "pet combination",
    "launcher": "the BlueStacks Android home screen with app icons - not inside the game",
    "in_run": "gameplay in progress: the cookie running through a level with Jump and "
              "Slide buttons at the bottom",
    "boost": "the pre-run shop: 'Buy Upgrades!' and 'Buy some Boosts!' items and a "
             "green 'Play!' button",
    "ad": "a full-screen advertisement for a different game - not Cookie Run",
}
# The wrong guess used for the NO half of the gold set: the screen a matcher
# would most plausibly confuse it with.
CONFUSABLE = {"lobby": "boost", "boost": "lobby", "result": "mystery", "mystery": "result",
              "card_tries": "mystery", "showoff_list": "lobby", "playerprofile": "lobby",
              "launcher": "ad", "ad": "launcher", "in_run": "lobby"}
# Cluster -> truth, labelled by eye 2026-09-23 from sheet_0.jpg and purity.jpg
# (every sampled member of the five big clusters matched its representative).
CLUSTER_TRUTH = {0: "lobby", 1: "result", 2: "mystery", 3: "card_tries", 4: "lobby",
                 5: "showoff_list", 6: "playerprofile", 7: "launcher", 8: "in_run",
                 9: "boost", 10: "mystery", 11: "ad"}
# Box badge on each of the 53 Result frames of cluster 1, in member order,
# read by eye from badges.jpg 2026-09-23.
BADGES = [2, 2, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 2, 2,
          2, 2, 2, 3, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 2, 2, 1, 1, 1, 1, 2]
BADGE_CROP = (95, 170, 560, 720)   # y0, y1, x0, x1 on the 800-wide Result frame


def load_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    for line in Path(ENV_FILE).read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def parse_word(text: str) -> str:
    w = (text or "").strip().split()
    w = w[0].strip(".,:;!*\"'").upper() if w else ""
    return w if w in ("YES", "NO", "UNSURE") else "INVALID"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


# ---------------------------------------------------------------- gold set
def cmd_build_gold(_a) -> int:
    import cv2
    frames = GOLD / "frames"
    clusters = json.loads((GOLD / "clusters.json").read_text())
    crops = GOLD / "crops"
    crops.mkdir(exist_ok=True)
    items = []
    for c in clusters:
        truth = CLUSTER_TRUTH[c["cluster"]]
        mem = c["members"][:]
        random.Random(c["cluster"]).shuffle(mem)
        for f in mem[:12]:
            for guess, ans in ((truth, True), (CONFUSABLE[truth], False)):
                items.append({"id": f"S-{f[:-4]}-{guess}", "kind": "screen", "image": f"frames/{f}",
                              "truth_screen": truth, "guess": guess, "truth": ans,
                              "question": f"The bot thinks this is {SCREENS[guess]}. Is that right?"})
    res = clusters[1]["members"]
    assert len(res) == len(BADGES)
    by_n = {1: [], 2: [], 3: []}
    for f, n in zip(res, BADGES):
        by_n[n].append(f)
    y0, y1, x0, x1 = BADGE_CROP
    for n, fs in by_n.items():
        random.Random(n).shuffle(fs)
        for f in fs[:8]:
            im = cv2.imread(str(frames / f))
            crop = cv2.resize(im[y0:y1, x0:x1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            out = crops / f"badge-{f}"
            cv2.imwrite(str(out), crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
            wrong = {1: 2, 2: 3, 3: 2}[n]
            for guess, ans in ((n, True), (wrong, False)):
                items.append({"id": f"B-{f[:-4]}-x{guess}", "kind": "badge", "image": f"crops/{out.name}",
                              "truth_n": n, "guess": guess, "truth": ans,
                              "question": (f"This is the treasure-box badge from a Cookie Run result "
                                           f"screen. The bot reads it as x{guess} ({guess} "
                                           f"box{'es' if guess > 1 else ''}). Is that right?")})
    (GOLD / "gold.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
    kinds = {k: sum(1 for i in items if i["kind"] == k) for k in ("screen", "badge")}
    print(f"gold: {len(items)} questions {kinds}, YES {sum(i['truth'] for i in items)} / "
          f"NO {sum(not i['truth'] for i in items)} -> {GOLD / 'gold.jsonl'}")
    return 0


def gold_items() -> list[dict]:
    return [json.loads(l) for l in (GOLD / "gold.jsonl").read_text().splitlines() if l.strip()]


# ---------------------------------------------------------------- teachers
class OpenRouterTeacher:
    PARAMS = {T1_NANO: {"reasoning": {"effort": "minimal"}},
              T2: {"reasoning": {"enabled": False}}}

    def __init__(self, model: str, key: str, spend: dict):
        import requests
        self.requests = requests
        self.model, self.spend = model, spend
        self.s = requests.Session()
        self.h = {"Authorization": f"Bearer {key}"}

    def ask(self, item: dict) -> dict:
        with self.spend["lock"]:
            if self.spend["usd"] >= OR_RUN_USD:
                return {"answer": "SKIPPED", "why": f"run cap ${OR_RUN_USD} reached"}
        body = {"model": self.model, "max_tokens": 400, "usage": {"include": True},
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": [
                                 {"type": "text", "text": item["question"]},
                                 {"type": "image_url", "image_url": {
                                     "url": "data:image/jpeg;base64," + b64(GOLD / item["image"])}}]}],
                **self.PARAMS.get(self.model, {})}
        # 429 is the provider's own rate limit (7 of 186 qwen calls at 8
        # threads, 2026-09-23) -- a pause and a retry, not a wrong answer.
        for attempt in range(4):
            t0 = time.perf_counter()
            try:
                r = self.s.post(OR_URL, headers=self.h, json=body, timeout=120)
            except self.requests.RequestException as e:
                return {"answer": "ERROR", "why": str(e)[:200]}
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code != 429 and '"code": 429' not in r.text[:400] and '"code":429' not in r.text[:400]:
                break
            time.sleep(2 + 3 * attempt)
        try:
            d = r.json()
        except ValueError:
            return {"answer": "ERROR", "why": f"HTTP {r.status_code} non-JSON", "ms": ms}
        if r.status_code != 200 or "choices" not in d:
            return {"answer": "ERROR", "why": json.dumps(d.get("error", d))[:300], "ms": ms}
        u = d.get("usage") or {}
        cost = float(u.get("cost") or 0)
        with self.spend["lock"]:
            self.spend["usd"] += cost
        text = (d["choices"][0].get("message") or {}).get("content") or ""
        return {"answer": parse_word(text), "text": text[:120], "ms": round(ms),
                "tok_in": u.get("prompt_tokens"), "tok_out": u.get("completion_tokens"),
                "tok_reason": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                "cost": cost}


def sonnet_spent_today() -> float:
    p = STATE / "sonnet_ledger.jsonl"
    if not p.exists():
        return 0.0
    day = datetime.now().strftime("%Y-%m-%d")
    return sum(json.loads(l).get("usd", 0) for l in p.read_text().splitlines()
               if l.strip() and json.loads(l).get("day") == day)


def ask_sonnet(item: dict) -> dict:
    """T3 on the Claude subscription. One user message carrying the image, no
    tools, no settings, no MCP: the call is the image and the question only."""
    spent = sonnet_spent_today()
    if spent >= SONNET_DAY_USD:
        return {"answer": "SKIPPED", "why": f"Sonnet day cap ${SONNET_DAY_USD} reached (spent ${spent:.4f})"}
    msg = {"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": item["question"]},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": b64(GOLD / item["image"])}}]}}
    cmd = ["claude", "-p", "--model", T3, "--input-format", "stream-json",
           "--output-format", "stream-json", "--verbose", "--system-prompt", SYSTEM_T3,
           "--tools", "", "--strict-mcp-config", "--setting-sources", "",
           "--no-session-persistence", "--max-turns", "1",
           "--max-budget-usd", f"{max(0.01, SONNET_DAY_USD - spent):.4f}"]
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, input=json.dumps(msg) + "\n", capture_output=True, text=True,
                           timeout=180, cwd=str(GOLD))
    except subprocess.TimeoutExpired:
        return {"answer": "ERROR", "why": "claude -p timed out"}
    ms = (time.perf_counter() - t0) * 1000
    result = None
    for line in p.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            result = ev
    if not result:
        return {"answer": "ERROR", "why": (p.stderr or p.stdout)[-300:], "ms": round(ms)}
    usd = float(result.get("total_cost_usd") or 0)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "sonnet_ledger.jsonl").open("a") as fh:
        fh.write(json.dumps({"day": datetime.now().strftime("%Y-%m-%d"), "t": time.time(),
                             "item": item["id"], "usd": usd}) + "\n")
    text = result.get("result") or ""
    u = result.get("usage") or {}
    return {"answer": parse_word(text), "text": text[:300], "ms": round(ms), "cost": usd,
            "tok_in": (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
                      + (u.get("cache_creation_input_tokens") or 0),
            "tok_out": u.get("output_tokens")}


def verdict(t1: str, t2: str, t3: str | None) -> tuple[str, str]:
    """(label, how). The ladder the CEO set, as code."""
    if t1 in ("YES", "NO") and t1 == t2:
        return t1, "t1+t2 agree"
    if t3 in ("YES", "NO"):
        votes = [v for v in (t1, t2, t3) if v in ("YES", "NO")]
        if votes.count(t3) >= 2:
            return t3, "t3 broke the tie"
        return t3, "t3 alone (t1/t2 unusable)"
    return "HUMAN", "still unclear after the teachers"


# ---------------------------------------------------------------- verbs
def cmd_smoke(_a) -> int:
    key = load_key()
    spend = {"usd": 0.0, "lock": threading.Lock()}
    items = gold_items()
    for it in (items[0], next(i for i in items if i["kind"] == "badge")):
        for m in (T1, T2):
            print(m, it["id"], json.dumps(OpenRouterTeacher(m, key, spend).ask(it)))
    print(T3, items[0]["id"], json.dumps(ask_sonnet(items[0])))
    print(f"openrouter spend ${spend['usd']:.6f}")
    return 0


def cmd_ab(a) -> int:
    key = load_key()
    spend = {"usd": 0.0, "lock": threading.Lock()}
    items = gold_items()
    if a.limit:
        items = items[:a.limit]
    teachers = {m: OpenRouterTeacher(m, key, spend) for m in (T1, T2)}
    rows = {i["id"]: {**i} for i in items}
    t0 = time.time()
    with cf.ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(teachers[m].ask, i): (i["id"], m) for i in items for m in (T1, T2)}
        for f in cf.as_completed(futs):
            iid, m = futs[f]
            rows[iid]["t1" if m == T1 else "t2"] = f.result()
    splits = [r for r in rows.values() if not (r["t1"]["answer"] in ("YES", "NO")
                                               and r["t1"]["answer"] == r["t2"]["answer"])]
    print(f"T1+T2 done in {time.time() - t0:.0f}s, openrouter ${spend['usd']:.6f}; "
          f"{len(splits)} splits -> T3", flush=True)
    for r in splits[:a.t3_max]:
        r["t3"] = ask_sonnet(r)
    for r in rows.values():
        r["label"], r["how"] = verdict(r["t1"]["answer"], r["t2"]["answer"],
                                       (r.get("t3") or {}).get("answer"))
    STATE.mkdir(parents=True, exist_ok=True)
    out = STATE / f"ab-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "t1": T1, "t2": T2,
                               "t3": T3, "openrouter_usd": spend["usd"],
                               "rows": list(rows.values())}, indent=1))
    print(f"-> {out}")
    report(out)
    return 0


def report(path: Path) -> None:
    d = json.loads(path.read_text())
    rows = d["rows"]

    def acc(key, sub=None):
        rs = [r for r in rows if (sub is None or r["kind"] == sub) and key in r]
        ok = sum((r[key]["answer"] == ("YES" if r["truth"] else "NO")) for r in rs)
        bad = sum(r[key]["answer"] not in ("YES", "NO") for r in rs)
        return ok, len(rs), bad

    print(f"\n{'teacher':<28}{'all':>10}{'screen':>10}{'badge':>10}{'invalid':>9}"
          f"{'tok_in':>8}{'$/q':>11}{'ms p50':>8}")
    for k, name in (("t1", d["t1"]), ("t2", d["t2"]), ("t3", d["t3"] + " (splits)")):
        a, n, bad = acc(k)
        if not n:
            continue
        s = acc(k, "screen")
        b = acc(k, "badge")
        rs = [r[k] for r in rows if k in r and r[k].get("cost") is not None]
        print(f"{name:<28}{a:>5}/{n:<4}{s[0]:>5}/{s[1]:<4}{b[0]:>5}/{b[1]:<4}{bad:>9}"
              f"{st.mean([x.get('tok_in') or 0 for x in rs]) if rs else 0:>8.0f}"
              f"{st.mean([x['cost'] for x in rs]) if rs else 0:>11.7f}"
              f"{st.median([x.get('ms') or 0 for x in rs]) if rs else 0:>8.0f}")
    lab = [r for r in rows if r["label"] in ("YES", "NO")]
    right = sum(r["label"] == ("YES" if r["truth"] else "NO") for r in lab)
    hows = {}
    for r in rows:
        hows[r["how"]] = hows.get(r["how"], 0) + 1
    print(f"\nLADDER: {right}/{len(lab)} labels right, {len(rows) - len(lab)} to human; {hows}")
    agree = [r for r in rows if r["how"] == "t1+t2 agree"]
    print(f"  when T1 and T2 agree: {sum(r['label'] == ('YES' if r['truth'] else 'NO') for r in agree)}"
          f"/{len(agree)} right")
    print(f"openrouter spend ${d['openrouter_usd']:.6f}; Sonnet today ${sonnet_spent_today():.4f}")
    wrong = [r for r in rows if r["label"] in ("YES", "NO") and r["label"] != ("YES" if r["truth"] else "NO")]
    for r in wrong[:12]:
        print(f"  WRONG {r['id']:<34} truth={r['truth']} t1={r['t1']['answer']} t2={r['t2']['answer']} "
              f"t3={(r.get('t3') or {}).get('answer')}")


def cmd_candidates(a) -> int:
    """Try other models as a teacher on the same gold set: accuracy, how often
    they say YES to a wrong guess (the failure that makes a teacher useless),
    and price. gpt-5-nano said YES to 67 of 93 wrong guesses on 2026-09-23."""
    key = load_key()
    spend = {"usd": 0.0, "lock": threading.Lock()}
    items = gold_items()
    out = {}
    for m in a.models:
        t = OpenRouterTeacher(m, key, spend)
        with cf.ThreadPoolExecutor(4) as ex:
            res = list(ex.map(t.ask, items))
        out[m] = [{**{k: i[k] for k in ("id", "kind", "truth")}, "r": r} for i, r in zip(items, res)]
        ok = sum(r["answer"] == ("YES" if i["truth"] else "NO") for i, r in zip(items, res))
        fyes = sum(r["answer"] == "YES" for i, r in zip(items, res) if not i["truth"])
        fno = sum(r["answer"] == "NO" for i, r in zip(items, res) if i["truth"])
        bad = sum(r["answer"] not in ("YES", "NO") for r in res)
        scr = [(i, r) for i, r in zip(items, res) if i["kind"] == "screen"]
        bdg = [(i, r) for i, r in zip(items, res) if i["kind"] == "badge"]
        acc = lambda pr: sum(r["answer"] == ("YES" if i["truth"] else "NO") for i, r in pr)
        costs = [r["cost"] for r in res if r.get("cost") is not None]
        ms = [r["ms"] for r in res if r.get("ms")]
        print(f"{m:<36} right {ok}/{len(items)}  screen {acc(scr)}/{len(scr)}  badge {acc(bdg)}/{len(bdg)}  "
              f"yes-to-wrong {fyes}  no-to-right {fno}  unusable {bad}  "
              f"$/q {st.mean(costs) if costs else 0:.7f}  ms p50 {st.median(ms) if ms else 0:.0f}", flush=True)
    STATE.mkdir(parents=True, exist_ok=True)
    p = STATE / f"candidates-{time.strftime('%Y%m%d-%H%M%S')}.json"
    p.write_text(json.dumps({"openrouter_usd": spend["usd"], "models": out}, indent=1))
    print(f"openrouter spend ${spend['usd']:.6f} -> {p}")
    return 0


WINBOX_BOT = "C:/Users/UsEr/cookierun-bot"


def human_payload(r: dict) -> dict:
    """The last rung: one question in the CEO's existing review queue
    (vision/ask_human.py on winbox, kind 'verify'). He answers YES/NO and
    writes WHY in the note box; the reason is what improves the questions."""
    votes = [f"T1 {r['t1']['answer']}", f"T2 {r['t2']['answer']}"]
    if r.get("t3"):
        votes.append(f"T3 {r['t3']['answer']} ({(r['t3'].get('text') or '').splitlines()[-1][:120]})")
    return {"kind": "verify",
            "prompt": (f"{r['question']}\nครูตอบ: {' · '.join(votes)}\n"
                       "ตอบ ใช่/ไม่ใช่ แล้วพิมพ์เหตุผลในช่องหมายเหตุ (ใช่ เพราะ… / ไม่ใช่ เพราะ…)"),
            "choices": [{"k": "yes", "label": "ใช่"}, {"k": "no", "label": "ไม่ใช่"}],
            "image": r["image"], "src": {"from": "teacher_ladder", "item": r["id"]}}


def cmd_human_push(a) -> int:
    d = json.loads(Path(a.file).read_text())
    todo = [r for r in d["rows"] if r.get("label") == "HUMAN"]
    print(f"{len(todo)} item(s) need the human rung")
    for r in todo:
        pl = human_payload(r)
        if a.dry_run:
            print(json.dumps(pl, ensure_ascii=False)[:400])
            continue
        remote_img = f"{WINBOX_BOT}/label_review/teacher/{Path(r['image']).name}"
        subprocess.run(["ssh", "winbox", f"mkdir \"{WINBOX_BOT}/label_review/teacher\" 2>nul"],
                       capture_output=True)
        subprocess.run(["scp", "-q", str(GOLD / r["image"]), f"winbox:{remote_img}"], check=True)
        add = ("import json,sys; sys.path.insert(0, r'" + WINBOX_BOT + "'); from vision import ask_human; "
               "p=json.load(open(sys.argv[1], encoding='utf-8')); "
               "print(ask_human.add(p['kind'], p['prompt'], p['choices'], [p['img']], src=p['src'])['id'])")
        pl["img"] = remote_img
        tmp = STATE / "human_push.json"
        tmp.write_text(json.dumps(pl, ensure_ascii=False), encoding="utf-8")
        subprocess.run(["scp", "-q", str(tmp), "winbox:C:/mooniex/pclease/human_push.json"], check=True)
        out = subprocess.run(["ssh", "winbox", f"{WINBOX_BOT}/.venv/Scripts/python.exe -c \"{add}\" "
                              "C:/mooniex/pclease/human_push.json"], capture_output=True, text=True)
        print(r["id"], "->", out.stdout.strip() or out.stderr.strip()[-200:])
    return 0


def cmd_report(a) -> int:
    runs = sorted(STATE.glob("ab-*.json"))
    report(Path(a.file) if a.file else runs[-1])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="verb", required=True)
    sp.add_parser("build-gold")
    sp.add_parser("smoke")
    p = sp.add_parser("ab")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--t3-max", type=int, default=40)
    p = sp.add_parser("human-push")
    p.add_argument("file")
    p.add_argument("--dry-run", action="store_true")
    p = sp.add_parser("candidates")
    p.add_argument("models", nargs="+")
    p = sp.add_parser("report")
    p.add_argument("--file")
    a = ap.parse_args()
    return {"build-gold": cmd_build_gold, "smoke": cmd_smoke, "ab": cmd_ab,
            "report": cmd_report, "candidates": cmd_candidates,
            "human-push": cmd_human_push}[a.verb](a)


if __name__ == "__main__":
    raise SystemExit(main())
