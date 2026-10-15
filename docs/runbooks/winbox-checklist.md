# winbox — Pipes tested live

**Drill completed 11 Sep 2026 23:45 — including one real reboot**
Every line **uses the real pipe** — it does not read config values and trust them

Re-check anytime: `bash scripts/winbox-drill.sh` (under a minute)

---

## ✅ All passed — 14 checks · none failed

| # | Pipe | Proven by |
|---|---|---|
| 1 | SSH into winbox | Machine answered with name `DESKTOP-3NQB2QO` |
| 2 | Tailscale survives reboot | **Tested with a real reboot; came back on its own** |
| 3 | sshd survives reboot | **Tested with a real reboot; came back on its own** |
| 4 | Machine does not sleep on its own | Sleep on AC = Never |
| 5 | **Machine boots to desktop on its own without typing anything** | **Real reboot → `UsEr` logged in, no one touched it** |
| 6 | Enough disk space | 174 GB |
| 7 | MACHINE-LOCK is free | Read the actual file |
| 8 | Codex is installed | `codex-cli 0.153.4` |
| 9 | ChatGPT login still present | `Logged in using ChatGPT` |
| 10 | **Can command Astra** | Answered `DRILL OK` |
| 11 | **Astra does not depend on the app** | Killed the app process and it still answered `APP CLOSED OK` |
| 12 | VNC survives reboot | **Real reboot → Running** |
| 13 | VNC connects within Tailscale | Probed port 5900 from Contabo; got through |
| 14 | **CEO can reach the screen from phone** | **CEO connected himself; mouse moved** |

**Real reboot result at 23:34 — SSH came back in 125 seconds, everything came up on its own, no human touched it**

---

## 🔴 Most important finding tonight — worker return pipe

**The CEO caught by watching the screen over VNC** that the worker had finished its work, even though the CTO saw "no report"

The system contract is: worker pushes branch with `REPORT.md` → `runners/branch_poller.py` on the hub side catches it →
changes status to `review`

| | |
|---|---|
| Can the worker push to GitHub? | ✅ **Yes** (`git ls-remote` passed) |
| `GITHUB_SSH_ROUTE=unreachable` warning at spawn | ❌ **False alarm** — buggy check, not broken network |
| `branch_poller.py` | ❌ **Never ran at all** ← the real culprit |

**If not caught, for all 7 days workers would have finished their work without anyone knowing about a single one**

**Fixed:** poller runs as a daemon · checks every 60 seconds · logs at `state/logs/branch_poller.log`

If you suspect it died:
```bash
pgrep -af "runners.branch_poller"
# If not running, restart:
cd /opt/mooniex-agents && setsid nohup python3 -m runners.branch_poller >> state/logs/branch_poller.log 2>&1 &
```

---

## Actual cost of talking to Astra

| | token |
|---|---|
| Codex's own baseline (cannot be reduced) | 3,839 |
| + old `AGENTS.md` 11 KB | 6,492 |
| **+ new `AGENTS.md` 3.3 KB** | **4,689** |

**Trimming the file saves 1,803 every time = 28%**
**The base cost is paid the same whether the question is short or long → batch questions and send at once to save up to 9x**

---

## Caution — one mouse

There is only one desktop — **if a worker is clicking and the CEO connects over VNC and moves the mouse at the same time, they collide**
`MACHINE-LOCK.txt` only coordinates between agents — **it does not control someone coming in via VNC**

Before entering VNC:
```bash
ssh -n winbox 'powershell -NoProfile -Command "Get-Content C:\mooniex\MACHINE-LOCK.txt"'
```
Name present = an agent is working → wait, or tell the CTO to stop it first

---

## Things that cannot be fixed from a phone

- **Power outage / machine off** → ask Mom to press the power button — **that's all, the machine boots to the desktop on its own**
- **Home internet down** → ask Mom to unplug the router, wait 10s, plug it back in
- **MFA code / first-time consent click / payment** → must be the CEO

---

## Emergency card — keep on phone

```
VNC      window-gob      password: CEO keeps it   (open Tailscale first)
Health   bash scripts/winbox-drill.sh
Recovery docs/runbooks/winbox-recovery.md
poller   pgrep -af "runners.branch_poller"
```
