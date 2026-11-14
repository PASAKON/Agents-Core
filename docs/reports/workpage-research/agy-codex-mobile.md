# Mobile Monitoring for Headless AGY and Codex CLI Runs

## Short Answer
1. **No official mobile app or web view exists for either Google Antigravity (`agy -p`) or OpenAI Codex CLI (`codex exec`) that displays standalone, local headless CLI runs.**
2. Official remote tools (Antigravity Remote Control web dashboard, ChatGPT mobile Codex tab) require interactive sessions, cloud tasks, or paired desktop GUI apps; headless CLI jobs exit to stdout without registering.
3. Third-party iOS companion apps only connect to desktop IDEs or cloud workspaces and expose repository context to third-party developers.
4. Public terminal relays (e.g. `tmate`) stream terminal output over third-party cloud servers, risking credential, token, and transcript leakage.
5. The only secure way to watch local headless runs on mobile is using self-hosted terminal/log viewers over the org's private Tailscale network.
6. The CEO can view live headless runs via mobile SSH (Prompt 3, Blink Shell, Termius) running read-only `tmux attach -r` or `run_watch.py tail <task>`, or via Tailscale Web SSH.
7. Long-term, surfacing headless run logs natively in MoonieX Console / Run Inbox (`terminal.mooniex.com/run`) provides a zero-leak, zero-install mobile view.

## Comparison Table

| Option | Works for local headless runs (yes/no/unknown) | Cost | Setup | Risk | Source |
|---|---|---|---|---|---|
| **Google Antigravity Remote Control Web View** | **No** (supports interactive sessions via `agy --remote-control` or `agy remote-control start`; `agy -p` print mode runs one-shot non-interactively to stdout and exits without registering in the dashboard) | $0 (included with Google account) | Sign in with Google account at `https://antigravity.google`; requires running `agy remote-control start` background daemon on host. No open ports (outbound tunnel). | Exposes workspace context, agent conversations, and diffs to Google Cloud relay servers. | [antigravity.google/docs](https://antigravity.google/docs) (Nov 2026); [antigravity.google](https://antigravity.google) (Nov 2026) |
| **Google Antigravity Android App** (`com.google.android.apps.antigravity`) | **No** (targeted at Googlebooks/Chromebooks and enterprise desktop hardware, not standard smartphones; does not capture raw `agy -p` CLI runs) | $0 | Google Play Store install; Google account login; requires compatible hardware. | Transcripts and code context stored and processed on Google Cloud infrastructure. | [play.google.com](https://play.google.com/store/apps/details?id=com.google.android.apps.antigravity) (Nov 2026); [9to5google.com](https://9to5google.com) (Nov 2026) |
| **Third-Party iOS Antigravity Companions** (e.g. Mobile IDE for Antigravity AI, ZeroG, Spacesuit) | **No** (connects only to desktop IDE plugins or cloud workspaces; unsupported for headless `agy -p` CLI) | $0 to freemium / in-app purchases | Install from Apple App Store; requires pairing bridge/API token to desktop IDE or cloud tasks. | **High**: Unvetted third-party developers receive repository file paths, session tokens, and prompt/response transcripts. | [apps.apple.com](https://apps.apple.com) (Nov 2026) |
| **OpenAI ChatGPT Mobile App (Codex Remote Control)** | **No** (only connects to Codex Cloud or ChatGPT Desktop App paired via QR code under *Settings > Connections*; independent CLI `codex exec` terminal runs are not mirrored) | Included with ChatGPT Plus/Pro ($20–$200/mo) | OpenAI account; requires ChatGPT desktop app running on Mac/Windows; scan pairing QR code from mobile app; host must stay awake and online. | Repository code, file diffs, and executed commands pass through OpenAI cloud servers. | [chatgpt.com](https://chatgpt.com) (Nov 2026); [deployhq.com](https://deployhq.com) (Nov 2026) |
| **Mobile SSH Client over Tailscale** (Prompt 3 by Panic, Blink Shell, Termius) | **Yes** (attaches to host `tmux` session in read-only mode `tmux attach -r` or tails task logs via `python tools/run_watch.py tail <task>`) | Free (Termius Free, ConnectBot) or $19.99/yr (Prompt 3, Blink Shell) | Install mobile SSH app; connect to host using Tailscale MagicDNS / IP (100.x.y.z); authenticate via SSH key. No open public ports. | **Minimal**: Direct peer-to-peer WireGuard encrypted connection; zero third-party transcript exposure; access guarded by private SSH keys. | [tailscale.com/kb/1152/tailscale-ssh](https://tailscale.com/kb/1152/tailscale-ssh) (Nov 2026); [panic.com/prompt](https://panic.com/prompt) (Nov 2026); [blink.sh](https://blink.sh) (Nov 2026) |
| **Tailscale Web SSH Console** | **Yes** (browser-based Wasm SSH terminal inside Tailscale Admin Console; attach to `tmux` or run `run_watch.py status`) | $0 (included with Tailscale) | Enable Tailscale SSH on host (`tailscale up --ssh`); log into Tailscale Admin Console in mobile browser; click SSH next to host. No open public ports. | **Very Low**: Authenticated via Tailscale identity; browser executes Wasm SSH client directly to node; no third-party log inspection. | [tailscale.com/blog/web-client](https://tailscale.com/blog/web-client) (Nov 2026) |
| **`ttyd` Web Terminal Daemon** (`tsl0922/ttyd`) | **Yes** (streams a read-only terminal or `run_watch.py follow` via web browser) | $0 (Open-source, MIT license) | Run lightweight daemon on host: `ttyd -c <user>:<pass> -p 7681 tmux attach -r -t <session>` (read-only by default without `-W`); bind to Tailscale IP (100.x.y.z). Open port only on tailnet interface. | **Low** if bound strictly to Tailnet IP with credential auth (`-c`) and read-only mode. **High** if exposed to public internet without authentication. | [github.com/tsl0922/ttyd](https://github.com/tsl0922/ttyd) (Nov 2026) |
| **`tmate` Instant Terminal Sharing** (`tmate-io/tmate`) | **Yes** (wraps terminal or tmux session and generates a shareable web viewer URL) | $0 (Open-source) | Run `tmate -F` on host; open generated web link (`https://tmate.io/t/...`) on mobile browser. | **Critical**: Terminal session streams through public `tmate.io` cloud infrastructure; anyone with the URL can view stdout/stderr, exposing code, secrets, and transcripts. | [github.com/tmate-io/tmate](https://github.com/tmate-io/tmate) (Nov 2026); [tmate.io](https://tmate.io) (Nov 2026) |
| **MoonieX Native Hub & RunWatch** (`terminal.mooniex.com/run` & `tools/run_watch.py`) | **Yes** (native tracking of task states, heartbeats, and worker stdout logs from AGY and Codex in Postgres hub) | $0 (existing org infrastructure) | Use existing mobile-accessible MoonieX Console / Run Inbox; pull live status via `tools/run_watch.py` or hub API. | **Zero External Risk**: 100% self-hosted; authenticated via existing MoonieX session token; no third-party exposure. | Local MoonieX codebase (`tools/run_watch.py`, `docs/ops/mesh-check.md`, Nov 2026) |

## Recommendation

1. **Immediate Zero-Install, Zero-Cost Solution (Mobile SSH over Tailscale):**
   - The CEO should use a native mobile SSH client (such as **Prompt 3 by Panic** on iOS, **Blink Shell**, or **Termius**) connecting directly over the existing **Tailscale** private network.
   - To watch active headless worker runs without risk of interfering with the execution or killing the session, run:
     ```bash
     tmux attach -r -t <session_name>
     ```
     Or tail the specific task transcript without attaching to tmux:
     ```bash
     bash scripts/hub/org-python.sh tools/run_watch.py tail <task_id>
     ```
   - Alternatively, use **Tailscale Web SSH** directly in mobile Safari by logging into the Tailscale Admin Console—this requires zero app installations on the phone.

2. **Long-Term Native Web View (MoonieX Console / Run Inbox):**
   - Headless runs managed by the org already register heartbeats and status events in the Postgres hub ledger.
   - The cleanest and safest long-term solution is to expose a read-only log streaming / tail endpoint in `terminal.mooniex.com/run` (backed by `tools/run_watch.py tail <task>`). This gives the CEO a single, mobile-optimized dashboard for all headless runs (AGY, Codex, and Claude) without opening external ports or installing third-party daemons.

3. **What NOT to Do:**
   - **Do NOT rely on Antigravity Remote Control or ChatGPT Mobile App** for headless CLI monitoring: neither supports non-interactive `agy -p` or `codex exec` jobs, and both require routing traffic through external cloud servers.
   - **Do NOT use public `tmate`**: it streams full terminal screens to third-party public servers, creating a major risk of leaking credentials (`.env`, Infisical secrets, API tokens) and proprietary code.
   - **Do NOT install unverified third-party iOS wrappers** claiming Antigravity support, as they require passing workspace contexts or credentials to untrusted developers.
