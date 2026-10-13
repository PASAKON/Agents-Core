"""FINAL step of one BL post: re-check the open form against the plan, abort on ANY mismatch, else click the 'Schedule' button once and report what TikTok shows.
Authority (first-hand CEO answers on /run, operator passkey session): Q-20261013-2041-ae68 'Yes: post all three on schedule, 22:00 TH',
Q-20261013-2044-865f 'Post EP59 and EP60 as they are; I accept the risk', Q-20261013-2114-267a 'Label ON for all three'.
usage: tt_schedule_confirm.py <caption file> <mp4 basename> <YYYY-MM-DD> <HH:MM CEST>"""
import sys, time
from playwright.sync_api import sync_playwright
cap_file, mp4name, date, hhmm = sys.argv[1:5]
src = open(cap_file).read().rstrip("\n").split("\n")
CHECK = r"""() => ({
  blocks: [...document.querySelectorAll('.public-DraftEditor-content [data-block=true]')].map(b => b.innerText.replace(/​/g, '').replace(/\n$/, '')),
  radios: Object.fromEntries([...document.querySelectorAll('input[type=radio]')].map(e => [e.value, e.checked])),
  fields: [...document.querySelectorAll('input[readonly]')].map(e => e.value),
  sw: Object.fromEntries([...document.querySelectorAll('input[role=switch]')].map(e => { let l = e; for (let k = 0; k < 6 && l; k++) { l = l.parentElement; const t = l ? (l.innerText || '').replace(/\s+/g, ' ').trim() : ''; if (t.length > 4 && t.length < 120) return [t.slice(0, 22), e.checked]; } return ['?', e.checked]; })),
  who: (document.body.innerText.match(/Who can see this post\s+(\w+)/) || [])[1],
  file: (document.body.innerText.match(/BL-EP\d+_[^\s]+\.mp4/) || [])[0],
  overlays: document.querySelectorAll('.TUXModal-overlay[data-transition-status=open]').length })"""
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9282")
    page = [pg for pg in b.contexts[0].pages if "/tiktokstudio/upload" in pg.url][0]
    c = page.evaluate(CHECK)
    sw = c["sw"]
    problems = []
    if c["file"] != mp4name: problems.append(f"file {c['file']} != {mp4name}")
    if c["blocks"] != src: problems.append("caption differs from source")
    if not c["radios"].get("schedule"): problems.append("schedule radio not selected")
    if c["fields"][:2] != [hhmm, date]: problems.append(f"time/date {c['fields'][:2]} != {[hhmm, date]}")
    if not sw.get("AI-generated content"): problems.append("AI label not ON")
    if sw.get("Disclose post content"): problems.append("Disclose is ON")
    if sw.get("Audience control"): problems.append("Audience control is ON")
    if c["who"] != "Everyone": problems.append(f"privacy {c['who']}")
    if c["overlays"]: problems.append("an overlay is open")
    print("checks:", "ALL MATCH" if not problems else problems)
    if problems:
        sys.exit(2)
    n = page.evaluate(r"""() => { const bs = [...document.querySelectorAll('button')].filter(x => (x.innerText || '').trim() === 'Schedule'); return bs.length; }""")
    print("Schedule buttons:", n)
    if n != 1:
        sys.exit(3)
    page.evaluate(r"""() => { [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === 'Schedule').click(); }""")
    print("clicked Schedule at", time.strftime("%H:%M:%S"), "(Contabo CEST)")
    for i in range(12):
        time.sleep(5)
        s = page.evaluate(r"""() => { const m = document.querySelector('.TUXModal.common-modal'); return {url: location.pathname, modal: m ? (m.innerText || '').replace(/\s+/g, ' ').slice(0, 260) : null, buttons: m ? [...m.querySelectorAll('button')].map(b => (b.innerText || '').trim()) : [], head: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 160)}; }""")
        print(i, s["url"], "| modal:", s["modal"], s["buttons"])
        if s["url"] != "/tiktokstudio/upload" or s["modal"]:
            break
    print("head:", s["head"])
