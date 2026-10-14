"""Fill ONE BL post in TikTok Studio (tiktok-bl Browser Home, CDP 127.0.0.1:9282) up to, NOT including, the final Schedule click:
attach the mp4 -> dismiss the content-checks dialog (Cancel, never 'Turn on' for that one) -> caption through Draft's own state (select-all + one paste)
-> Schedule radio + 'Allow' (saving for scheduled posting) -> time -> date -> 'AI-generated content' label ON + its 'Turn on' -> read everything back.
Authority (first-hand CEO answers on /run, operator passkey session): Q-20261013-2041-ae68 'Yes: post all three on schedule, 22:00 TH',
Q-20261013-2044-865f 'Post EP59 and EP60 as they are; I accept the risk', Q-20261013-2114-267a 'Label ON for all three'.
Input events from CDP (mouse/keyboard) are dead in this Chrome, so every action is a DOM click or Draft state change.
usage: tt_post_flow.py <mp4> <caption file> <YYYY-MM-DD> <HH> <MM>"""
import sys, time
from playwright.sync_api import sync_playwright

mp4, cap_file, date, hh, mm = sys.argv[1:6]
src = open(cap_file).read().rstrip("\n")
lines = src.split("\n")
day = str(int(date.split("-")[2]))

def jsq(page, js, arg=None):
    return page.evaluate(js, arg) if arg is not None else page.evaluate(js)

OVERLAY = "() => { const m = document.querySelector('.TUXModal.common-modal'); const o = document.querySelectorAll('.TUXModal-overlay[data-transition-status=open]').length; return {open: o, text: m ? (m.innerText || '').replace(/\\s+/g, ' ').slice(0, 200) : '', buttons: m ? [...m.querySelectorAll('button')].map(b => (b.innerText || '').trim()) : []}; }"
CLICK_BTN = "(label) => { const m = document.querySelector('.TUXModal.common-modal') || document; const b = [...m.querySelectorAll('button')].find(x => (x.innerText || '').trim() === label); if (!b) return false; b.click(); return true; }"
SELECT_ALL = r"""() => { const el = document.querySelector('.public-DraftEditor-content');
  const fk = Object.keys(el).find(k => k.startsWith('__reactFiber')); let f = el[fk];
  for (let i = 0; i < 60 && f; i++, f = f.return) { const p = f.memoizedProps; if (p && p.editorState && typeof p.onChange === 'function') break; }
  if (!f) return 'no editor';
  const es = f.memoizedProps.editorState, c = es.getCurrentContent(), a = c.getFirstBlock(), z = c.getLastBlock();
  f.memoizedProps.onChange(es.constructor.forceSelection(es, es.getSelection().merge({anchorKey: a.getKey(), anchorOffset: 0, focusKey: z.getKey(), focusOffset: z.getLength(), isBackward: false, hasFocus: true})));
  return 'selected ' + c.getBlockMap().size + ' blocks'; }"""
PASTE = "(txt) => { const e = document.querySelector('.public-DraftEditor-content'); e.focus(); const dt = new DataTransfer(); dt.setData('text/plain', txt); e.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); }"
BLOCKS = "() => [...document.querySelectorAll('.public-DraftEditor-content [data-block=true]')].map(b => b.innerText.replace(/\\u200b/g, '').replace(/\\n$/, ''))"
RADIO = "() => { const s = [...document.querySelectorAll('input[type=radio]')].find(e => e.value === 'schedule'); if (!s) return 'no radio'; s.click(); return 'clicked'; }"
RADIO_ON = "() => { const s = [...document.querySelectorAll('input[type=radio]')].find(e => e.value === 'schedule'); return !!(s && s.checked); }"
FIELDS = "() => [...document.querySelectorAll('input[readonly]')].map(e => e.value)"
PICK_TIME = "([idx, t]) => { const mk = ty => new MouseEvent(ty, {bubbles: true, cancelable: true, view: window, button: 0}); const l = document.querySelectorAll('.tiktok-timepicker-option-list')[idx]; if (!l) return 'no list'; const sp = [...l.querySelectorAll('.tiktok-timepicker-option-text')].find(x => (x.innerText || '').trim() === t); if (!sp) return 'no span ' + t; for (const ty of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) sp.dispatchEvent(mk(ty)); return 'ok'; }"
OPEN_DATE = "() => { const mk = ty => new MouseEvent(ty, {bubbles: true, cancelable: true, view: window, button: 0}); const i = [...document.querySelectorAll('input[readonly]')].find(e => /^\\d{4}-\\d\\d-\\d\\d$/.test(e.value)); if (!i) return 'no date input'; for (const ty of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) i.dispatchEvent(mk(ty)); return 'ok'; }"
PICK_DAY = "(d) => { const mk = ty => new MouseEvent(ty, {bubbles: true, cancelable: true, view: window, button: 0}); const sp = [...document.querySelectorAll('.calendar-wrapper .day.valid')].find(x => (x.innerText || '').trim() === d); if (!sp) return 'no valid day ' + d; for (const ty of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) sp.dispatchEvent(mk(ty)); return 'ok'; }"
AI_CLICK = "() => { const e = [...document.querySelectorAll('input[role=switch]')].find(x => { let l = x; for (let k = 0; k < 6 && l; k++) { l = l.parentElement; const t = l ? (l.innerText || '').replace(/\\s+/g, ' ').trim() : ''; if (t.length > 4 && t.length < 120) return /AI-generated content/.test(t); } return false; }); if (!e) return 'no AI switch'; if (e.checked) return 'already on'; e.click(); return 'clicked'; }"
AI_ON = "() => { const e = [...document.querySelectorAll('input[role=switch]')].find(x => { let l = x; for (let k = 0; k < 6 && l; k++) { l = l.parentElement; const t = l ? (l.innerText || '').replace(/\\s+/g, ' ').trim() : ''; if (t.length > 4 && t.length < 120) return /AI-generated content/.test(t); } return false; }); return !!(e && e.checked); }"

def say(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)

def dismiss_overlays(page, tries=4):
    for _ in range(tries):
        o = jsq(page, OVERLAY)
        if not o["open"]:
            return True
        say("overlay:", o["text"][:90], o["buttons"])
        if "automatic content checks" in o["text"] and "Cancel" in o["buttons"]:
            jsq(page, CLICK_BTN, "Cancel")
        elif "Got it" in o["buttons"]:
            jsq(page, CLICK_BTN, "Got it")
        else:
            say("UNKNOWN overlay, stopping"); return False
        time.sleep(2.5)
    return not jsq(page, OVERLAY)["open"]

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9282")
    page = b.contexts[0].pages[0]
    page.on("dialog", lambda d: d.accept())
    page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("input[type=file]", state="attached", timeout=90000)
    time.sleep(2)
    page.set_input_files("input[type=file]", mp4, timeout=240000)
    say("attached", mp4.rsplit("/", 1)[-1])
    page.wait_for_selector(".public-DraftEditor-content", state="visible", timeout=240000)
    time.sleep(20)
    say("uploaded text present:", jsq(page, "() => /Uploaded/.test(document.body.innerText)"))
    if not dismiss_overlays(page): sys.exit(4)
    # caption
    say(jsq(page, SELECT_ALL)); time.sleep(1.0)
    page.evaluate(PASTE, src); time.sleep(2)
    bl = jsq(page, BLOCKS)
    say("caption blocks", len(bl), "of", len(lines), "equal:", bl == lines)
    if bl != lines: sys.exit(5)
    jsq(page, "() => document.activeElement && document.activeElement.blur()")
    # schedule
    say("schedule radio:", jsq(page, RADIO)); time.sleep(2.5)
    o = jsq(page, OVERLAY)
    if o["open"] and "scheduled posting" in o["text"]:
        say("allow dialog:", jsq(page, CLICK_BTN, "Allow")); time.sleep(3)
    elif o["open"]:
        say("UNEXPECTED overlay after radio:", o["text"], o["buttons"]); sys.exit(6)
    if not jsq(page, RADIO_ON): say("schedule not selected"); sys.exit(7)
    say("time", jsq(page, PICK_TIME, [0, hh]), jsq(page, FIELDS)); time.sleep(1.5)
    say("minute", jsq(page, PICK_TIME, [1, mm]), jsq(page, FIELDS)); time.sleep(1.5)
    say("open date", jsq(page, OPEN_DATE)); time.sleep(2)
    say("pick day", jsq(page, PICK_DAY, day)); time.sleep(2)
    f = jsq(page, FIELDS); say("fields", f)
    if f[:2] != [f"{hh}:{mm}", date]: say("MISMATCH time/date"); sys.exit(8)
    # AI label
    r = jsq(page, AI_CLICK); say("AI switch:", r); time.sleep(2.5)
    o = jsq(page, OVERLAY)
    if o["open"] and "Labeling AI-generated content" in o["text"]:
        say("AI dialog:", jsq(page, CLICK_BTN, "Turn on")); time.sleep(3)
    elif o["open"]:
        say("UNEXPECTED overlay after AI click:", o["text"], o["buttons"]); sys.exit(9)
    say("AI label ON:", jsq(page, AI_ON))
    if not jsq(page, AI_ON): sys.exit(10)
    say("READY - form filled, nothing submitted")
