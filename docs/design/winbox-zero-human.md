# winbox — Zero Human operation, and how a human gets pulled in when there is no choice

CEO 2026-09-11: *"ฉันจะให้ WINDOW ให้คุณเป็นคนดูแล โดยคนเปิดเครื่องจะเป็นคนในบ้านของฉัน ส่วนการ Close
หรือ Restart PC ฉันจะสั่งงานผ่านคุณ … WINDOW ต้องเป็น Zero Human เท่านั้น — Human ช่วยแต่ตอน Boot
เปิดเครื่องเมื่อเกิดฉุกเฉินเท่านั้น"*

Design by the CTO, from a live survey of the box. **Nothing here has been implemented.**

---

## What the box actually is today

| | State (measured 2026-09-11) |
|---|---|
| Tailscale | ✅ up — `desktop-3nqb2qo` `100.123.83.75` |
| **CEO's phones on the tailnet** | ✅ **`iphone-14-pro-max` `100.121.168.30`, `iphone-14-pro` `100.71.47.58`** |
| Contabo (me) on the tailnet | ✅ `100.118.171.23`, direct |
| Auto-logon | ❌ **`AutoAdminLogon = 0`** |
| RDP | ❌ disabled (`fDenyTSConnections = 1`) |
| VNC / AnyDesk / Parsec | ❌ none installed |
| SSH in | ✅ working, this is how everything above was read |

**The phones are already on the private network.** No server to build, no public link to expose,
no relay to trust. That decides most of the design.

---

## The real blocker, and it is the same one that broke Astra today

Windows gives an SSH command its own non-interactive session. Anything needing the **desktop**
fails there. That is exactly why Astra could neither read nor write:

```
exec_command failed: timed out after 15000ms connecting runner pipe-in
PowerShell: timed out connecting to the Windows sandbox runner
```

Resolve, Codex's computer-use tools, BlueStacks and any GUI automation have the same requirement.
So **Zero Human is not mainly about remote control — it is about there always being a live,
unlocked desktop session for me to work inside.** Fix that and today's Astra limitation
disappears with it.

---

## The design — three parts

### 1 · A desktop session that always exists (this is the whole game)

- **Auto-logon at boot**, so powering on produces a logged-in session 1 with no keyboard.
- **Never lock, never sleep, never blank**: disable the lock screen timeout, set power plan to
  never sleep, disable hibernate, disable "require sign-in on wakeup".
- Result: the household member presses the power button, walks away, and sixty seconds later the
  machine is fully mine.

**On the password — a real decision, two honest options:**

| | How | Trade-off |
|---|---|---|
| **A. Sysinternals `Autologon.exe`** | stores the credential **encrypted in LSA**, not as registry plaintext | needs running once on the box; best security of the automatic options |
| **B. Household member types it at boot** | nothing stored anywhere | not Zero Human at boot — but boot is already the one human step the CEO allowed |

The naive route — setting `DefaultPassword` in the Winlogon registry key — writes the password in
**plaintext readable by anything on the box**. Do not use it.

**Recommendation: B first, A later.** The CEO has already conceded a human at power-on; having
that same person type a password costs nothing extra and stores no secret. Move to A only if
unattended reboots become routine.

### 2 · A runner that executes *inside* that session

SSH still lands in the wrong session, so commands that need the desktop must be handed across.
A small always-on script in session 1 (Startup folder, or a scheduled task set to
*run only when the user is logged on*) watches a queue directory and executes what it finds,
writing results back. My SSH writes into the queue; the runner does the work where the GUI lives.

This is what will finally let Astra's own tools work, and what lets me start Resolve, Codex, or a
browser without anyone present.

### 3 · Eyes and fingers on demand — the phone

**Use VNC over Tailscale. Not RDP.**

RDP is the obvious choice and it is the wrong one here: connecting creates a *new* session and
**locks the console on disconnect**, destroying the always-live session part 1 just built. VNC
mirrors the existing console session — the CEO sees exactly what the machine is doing, touches it,
disconnects, and the session carries on untouched.

- Server: **TightVNC** or **UltraVNC** on winbox, bound to the Tailscale interface only, never
  to `0.0.0.0`.
- Phone: any VNC client (RealVNC Viewer, bVNC) → `100.123.83.75`.
- Exposure: **none.** Tailscale is already the only path in, and both phones are already on it.

Fallback if a VNC client proves awkward on iOS: Chrome Remote Desktop has the better phone app,
also mirrors the console session — but it relays through Google and needs a Google login on the
box. Try VNC first.

### The "come and press this" loop

When I hit something no automation may do — an OAuth consent, an MFA code, a CAPTCHA, a payment
confirmation — the sequence is:

1. I bring the exact window to the foreground and **leave nothing else in the way**, so the thing
   needing a human is the first thing on screen.
2. I capture it and send it to the CEO in chat, with one line: what it is, and what to press.
3. A push notification goes to his phone (this session can push).
4. He opens the VNC app, does ten seconds of tapping, disconnects.
5. I detect the state change and carry on.

**Answering the question directly:** a "button in the chat" is not the right shape for this. Login
flows need a real keyboard against a real field — passwords, 6-digit codes, sliding CAPTCHAs. A
screenshot-and-coordinates bridge would be slower and more error-prone than just showing him the
actual screen for twenty seconds. What *is* worth building is everything around it: getting the
right window in front of him, alerting him, and detecting when he is done.

---

## What stays human, permanently — and no design removes it

Being honest about the limit so nobody plans around a promise that cannot be kept:

- **MFA codes** that arrive on his phone or an authenticator.
- **First-time OAuth consent** — by design, the whole point is that a person agreed.
- **Payments and subscriptions** — org rule, not a technical limit.
- **CAPTCHA.**
- **Physical power-on after a hard power loss**, and a power-cycle if the machine wedges below
  the OS.

Everything else can be Zero Human.

## Risks worth stating before this is built

- **An always-unlocked machine is an unlocked machine.** Anyone with physical access is logged in
  as that user. Acceptable for a box in the CEO's home on a private tailnet; would not be
  elsewhere.
- **If Tailscale fails to start, the box is unreachable by anyone** and the only remedy is the
  household member. Worth a watchdog that restarts Tailscale and, failing that, reboots.
- **Reboots must go through the CTO** per the CEO's instruction — so a watchdog that reboots on
  its own needs his explicit sign-off first.

## Implementation order, once approved

1. Power/lock settings — never sleep, never lock. *(no secrets, reversible, do first)*
2. Verify a desktop session survives an SSH-triggered reboot with the household member logging in.
3. Session-1 runner + queue; prove it by having Astra read a file, which fails today.
4. VNC bound to Tailscale; the CEO tests from his phone once.
5. The alert-and-wait loop, tested on a real login.
6. Auto-logon via Sysinternals — **only if** the CEO decides unattended reboots are needed.
