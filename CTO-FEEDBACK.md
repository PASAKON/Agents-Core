# CTO-FEEDBACK — change to part A before you build it (CEO 2026-09-26)

CEO: "หาลิงก์ไม่เจอ ไม่ได้แปลว่าโพสต์ไม่ติดจริง" and "อย่าด่วนสรุปถ้ายังไม่ได้ทดสอบ".
Not finding a link is not a failure. Replace the pass/fail in part A with **three states**,
and print exactly one of them as the run's last line.

| state | exit | only when |
|---|---|---|
| `VERIFIED <permalink>` | 0 | a public link was found **and** the logged-out check below passed |
| `PUBLISHED-UNVERIFIED` | 6 | the publish click happened, but no link has passed the check yet. Say what you did see, e.g. the Business Suite row status text. Never print "FAILED" for this. |
| `FAILED <evidence>` | 8 | only on **positive evidence**: the Business Suite row reads ไม่สำเร็จ / ไม่ได้บันทึกไว้อย่างถูกต้อง, or there is no row at all after 30 min |

**Logged-out check.** Use a second source that does not depend on the signed-in Chrome.
`curl -sL -A "facebookexternalhit/1.1" <permalink>`, then check that the `og:title` /
`og:description` meta contains the caption's first line. This worked once today on
film 2's share link, so it is n=1: prove it again in your tests.

**Keep checking, not a single 5-minute window.** Facebook processes a Reel for minutes.
Poll every ~2 min for up to 30 min, and print `VERIFIED` the moment the check passes.

**The check must be able to fail.** Run it on real data both ways, and report both results:
- positive: film 2 — `https://www.facebook.com/61594116376333/videos/1729583468302869/` must VERIFY;
- negative: a URL that must NOT verify. Use film 1's dead reel id `1104791208680559`
  (`https://www.facebook.com/reel/1104791208680559`), which died after an edit on 2026-09-24,
  or any post whose caption does not match. If that one also "verifies", the check is worthless.

Part B (the comment) runs only after `VERIFIED`. On `PUBLISHED-UNVERIFIED`, do not comment.
Say so, and leave it for a rerun with `--comment-only`.

In REPORT.md, label every claim as **measured** (with the command and its output) or
**not tested**. Do not state behaviour you did not run.
