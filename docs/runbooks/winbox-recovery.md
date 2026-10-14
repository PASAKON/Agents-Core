# winbox — System recovery from phone

**For 12–19 Sep 2026 while the CEO is away**
Machine: Tailscale `window-gob` (MagicDNS; the `winbox` ssh alias). Before the 2026-09-24 reset it was `DESKTOP-3NQB2QO`

---

## 👵 If you need to ask Mom for help — say only this

**Confirmed: Mom is home all 7 days.** That closes the "no one to press the button" gap.

**The only thing to ask:**

> "แม่ครับ ช่วยกดปุ่มเปิดคอมเครื่องใหญ่ในห้องให้หน่อย แล้วปล่อยไว้เฉย ๆ ไม่ต้องทำอะไรต่อ" (Mom, please press the power button on the big computer in the room, then leave it alone.)

Or if the internet has a problem:

> "แม่ครับ ช่วยถอดปลั๊กเราเตอร์ รอ 10 วินาที แล้วเสียบกลับ" (Mom, please unplug the router, wait 10 seconds, then plug it back in.)

**That is all — do not ask for more than this** — do not ask her to type commands, do not ask her to read the screen and tell you what it says,
do not ask her to click anything on the screen. The CTO can handle everything else remotely. **Just get power to the machine.**

⚠️ **If auto-logon is still off**, pressing the power button leaves the machine stuck at the Windows password screen.
That means someone has to type the password, which is what we do not want to ask Mom to do.
**Turn on auto-logon and this problem disappears — one button press is all it takes.**

## Root of every problem on this machine — Session 0 vs Session 1

Measured on 11 Sep at 22:05 while Astra was working:

| process | SessionId |
|---|---|
| `codex.exe` called by CTO via SSH | **0** |
| CTO's own SSH commands | **0** |
| User logged in on the physical screen | `DESKTOP-3NQB2QO\UsEr` (Session **1**) |
| Windows visible from the SSH side | **0 windows** |

**Windows has completely isolated these two sides since Vista (Session 0 Isolation)**
Session 0 is the service side — no desktop, cannot draw windows, cannot capture the screen.
**SSH always lands in Session 0.**

**This is the single explanation for every symptom seen:**
- Why Astra has no terminal window like other workers → it is on the side that cannot draw windows
- Why Astra's file read/write tools hang (`timed out connecting runner pipe-in`)
- Why Resolve and Chrome cannot be launched directly from SSH

**This is not a misconfiguration, and it cannot be fixed by configuration.**

### Crossing into Session 1 works — proven

An interactive scheduled task (`schtasks /Create ... /IT` then `/Run`) actually runs in Session 1.
Tested on 11 Sep at 22:08 with result `session=1 user=desktop-3nqb2qo\user`.

**This is the pipe that will let Astra use computer use and let us run Resolve/Chrome without a human**
But it is **not enabled yet** — it needs CEO approval first, because it gives AI full control of the desktop.

## Read this first — 10 seconds

**Pipes that survive a reboot on their own without a human:**

| Pipe | Survives? | Why |
|---|---|---|
| SSH from CTO | ✅ | `sshd` is an Automatic service |
| Tailscale | ✅ | Also an Automatic service |
| Calling Astra / Codex | ✅ | Works over SSH, needs no screen |
| Browser worker / Resolve | ❌ | Needs a desktop session |

**Meaning: power goes out and the machine comes back → I can still dispatch work and Astra can still work**
What is lost is **work that needs the screen** until someone logs in.

---

## Health check — one command

```bash
bash scripts/winbox-drill.sh
```

Can be run anytime and takes under a minute. It does not just read config values and trust them — **it tests every real pipe**,
because a service marked "Automatic" that is actually hung looks identical from the registry.

`--quick` = skip calling Astra (saves ChatGPT tokens)

---

## Symptoms → Fixes

### 1. Cannot connect via SSH

```
ssh: connect to host <winbox tailnet IP> port 22: Connection timed out
```

**Follow in order — do not skip:**

1. **Wait 5 minutes first** — if the machine just rebooted, Tailscale takes a moment to come up. We saw this on 11 Sep:
   at the time we thought the machine was dead, but it just had not finished booting.
2. Check whether the machine is still on the Tailscale network — from any machine on the network:
   ```bash
   tailscale status | grep desktop-3nqb2qo
   ```
   - **Listed as offline** = machine is off or home internet is down → someone at home must press power
   - **Not listed at all** = Tailscale was removed/logged out → someone must be at the physical machine
3. If someone is at home: have them press the power button and wait 3 minutes. **Nothing else needed.** Both SSH and Tailscale
   will come up on their own.

**⚠️ There is no fix from a phone if the machine is completely off** — this is a limit that software cannot solve.

### 2. SSH connects, but Astra does not respond

```bash
ssh -n winbox 'codex login status'
```

- **`Logged in using ChatGPT`** → pipe is fine; the problem is the prompt or quota
- **Anything else** → **token expired; must log in again, which requires a human to click**
  → must access the screen (see item 4) or wait for the CEO to return

**Codex app closed = fine, proven**
The CLI that the CTO calls (`AppData\Roaming\npm\codex.ps1`) is separate from the app
(`AppData\Local\OpenAI\Codex\bin\codex.exe`). **They only share the login file `~/.codex/auth.json`.**
Tested on 11 Sep at 21:59 — killed the app process and called Astra again: **responded normally**.
Also, **Codex is not in the startup list at login**, so after a reboot the app will not come back — which has no effect.
**Do not try to open the app; it is unnecessary.**

**Symptom that is not a problem:** Astra says it cannot read files
(`timed out connecting to the Windows sandbox runner`) — **this is normal**.
Its tools never worked over SSH in the first place, so `scripts/astra.sh` passes the prompt body directly
instead of having it read files itself. **Do not try to fix this; it is not broken.**

### 3. Disk full / machine slow

```bash
ssh -n winbox 'powershell -NoProfile -Command "[math]::Round((Get-PSDrive C).Free/1GB,1)"'
```

Under 30 GB = danger · What takes up space is Cookie Run data
(`play_rec`, `modelplay`, `playset`) — **read `cookierun-bot/docs/DATA-STEWARD.md` before deleting anything,
and get CEO approval; do not delete on your own.**

### 4. Someone must click on the screen (login, OAuth, MFA, CAPTCHA)

**⚠️ As of 11 Sep 21:50, this path does not exist yet — VNC is not installed**

Once installed, how to use from a phone:
1. Open the Tailscale app on the phone and make sure it is connected
2. Open the VNC app (RealVNC Viewer / bVNC) → connect to `window-gob` (MagicDNS)
3. Enter the password (kept by the CEO)
4. Click what is needed, then close the app

**No need to open ports to the internet, no public links** — the CEO's phones are already on the same Tailscale network
(`iphone-14-pro-max` `100.121.168.30`, `iphone-14-pro` `100.71.47.58`)

### 5. MACHINE-LOCK stuck

```bash
ssh -n winbox 'powershell -NoProfile -Command "Get-Content C:\mooniex\MACHINE-LOCK.txt"'
```

If a name is left behind but nothing is actually running (e.g. a worker died mid-run):

```bash
ssh -n winbox 'powershell -NoProfile -Command "Set-Content C:\mooniex\MACHINE-LOCK.txt -Value \"\""'
```

**Do not clear it if the timestamp is still fresh** — on 11 Sep, a worker refused to overwrite
Astra's lock even though its brief told it to overwrite. **It did the right thing.** Check first whether a real process is running:

```bash
ssh -n winbox 'powershell -NoProfile -Command "(Get-Process Resolve,chrome -ErrorAction SilentlyContinue).Count"'
```

---

## Things with no workaround, regardless of design

Stated plainly so we do not plan around the impossible:

- **Power outage / machine completely off** → someone must press the button
- **Home internet down** → someone must be at home
- **MFA code sent to the CEO's phone** → must be the CEO
- **First-time OAuth consent click** → must be a human, by design
- **Payments / renewals** → company rule, not a technical limit

---

## Latest drill result — 11 Sep 21:51

```
PASS 12 · WARN 1 · FAIL 1
✅ SSH · Tailscale(Auto) · sshd(Auto) · does not sleep · disk 175 GB · lock free
✅ codex-cli 0.153.4 · Logged in using ChatGPT · Astra replied "DRILL OK"
⚠️ auto-logon off — after reboot GUI tasks will pause until someone logs in
❌ no VNC — if a login screen appears, nobody can reach it from a phone
```
