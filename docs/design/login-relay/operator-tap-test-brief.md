# TASK: prove taps and typing reach the remote page through the relay

**Fact wanted back:** after you click the email field on the relay's screencast and type a test string, does the remote Google page have that string in its email field? The CTO checks the remote side himself over CDP. You drive the relay page and report what you did, with the exact coordinates.

## What's known (don't rediscover)
- Relay page: `https://terminal.mooniex.com/relay` (this Chrome is already logged in to the Console, and no login is needed). It shows machine pills. Click the one whose text contains `Mac:9226` (class `machine-pill`).
  - If the pill doesn't respond to a click, run this in `javascript_tool`: `[...document.querySelectorAll('.machine-pill')].find(e=>/Mac:9226/.test(e.textContent)).click()`
- After ~5 s the page says `ระบบเลือก: ฟอร์ม`, and `#screencast-img` shows Google's mobile sign-in page (390×844 CSS on the remote).
- If the page says another session is active, wait 60 s and retry up to 5 times. A previous session times out after 5 idle minutes.
- The image is `object-fit: contain` (letterboxed). Get the **drawn** rect with `javascript_tool`:
  ```js
  const img=document.getElementById('screencast-img'); const r=img.getBoundingClientRect();
  const iw=img.naturalWidth, ih=img.naturalHeight, s=Math.min(r.width/iw, r.height/ih);
  const dw=iw*s, dh=ih*s, dl=r.left+(r.width-dw)/2, dt=r.top+(r.height-dh)/2;
  ({email:[Math.round(dl+0.5*dw), Math.round(dt+(268/844)*dh)], next:[Math.round(dl+(326/390)*dw), Math.round(dt+(402/844)*dh)]})
  ```
  The email field sits at CSS (195, 268) on the remote, and the Next button at (326, 402).

## Steps
1. Open the relay page and connect to Mac:9226 as above.
2. Compute the coordinates, then `left_click` the **email** point.
3. `type` exactly: `relaytest@example.com`. This is a fake address. Never type any real email or password.
4. `left_click` the **next** point.
5. **Stop.** Report in text: the coordinates you clicked, and whether the page text changed. `read_page`/`find` is enough. At most 1 screenshot, only if the text check is ambiguous.
6. Click `End Session` (`#btn-disconnect`), then close your tab.

## Budget / rules
- ≤15 steps, ≤1 screenshot, answer in text. Don't explore other pages.
- Touch nothing but the relay page. Never type real credentials.
- The replay script requirement doesn't apply: this is a one-off check.
- `PROGRESS.md`, if you write one, is never committed.

## Report
Clicked coordinates, typed string, what changed, any error text on the relay page, and a `## Skill learning` section.
