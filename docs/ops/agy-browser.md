# agy browser lane: `tools/agy_browse.py`

GH #188 (CEO 2026-09-30): most browse work moves to **agy** (Antigravity CLI,
Gemini), which drives the Console's **Browser Homes** (headless Chromes, one
profile per account, CDP on `127.0.0.1:92xx`) through **one strict command**,
never an open tool. The MCP route (`chrome-devtools-mcp` in agy) was refused
by the Claude Code auto-mode classifier on 2026-09-30 and is not coming back.

```
<Core>/.venv/bin/python tools/agy_browse.py [--port N] [--tab ID] <verb> [args]
exit 0 ok · 2 refused by policy · 1 error        output: short text or one JSON line, <= 2000 chars
```

Policy: `config/agy-browse.yaml`, one row per port (hosts, upload dirs, rate
limit, fire cooldown, fire label). Adding a site = adding a row. Log: one JSON
line per call in `state/agy-browse.jsonl` (under `$ORG_ROOT` when set).

## Verbs (closed set; anything else exits 2)

| verb | args | does | refuses |
|---|---|---|---|
| `tabs` | | tab id + title for tabs on allowed hosts, plus a count of other tabs | never prints a URL |
| `goto` | `<path-or-url>` | navigate the tab, then re-check the landing host | a target or landing host outside `allowed_hosts` |
| `text` | `<css>` | innerText of the first match | |
| `count` | `<css>` | number of matches | |
| `state` | | the BROWSER_OPERATOR page-state snippet: submit label + disabled, rights/sign-in/rate-limit/generating/failed markers | |
| `button-label` | | `{label, disabled}` of the port's `submit_selector` | |
| `click` | `<css>` | click | money-looking controls (own or surrounding button text); the submit button unless its label, re-read in the same call, matches `fire_label_regex` and `fire_cooldown_s` has passed |
| `type` | `<css> <text>` | fill a text field | password fields; any field whose label/name/id/autocomplete/placeholder/aria says pass, otp, card, cvv, 2fa or token; non-text targets |
| `key` | `Enter\|Tab\|Escape` | press one key | any other key or chord |
| `upload` | `<file-input-css> <path>` | set the file | a path whose realpath is outside `upload_dirs` (symlinks out included); a target that is not `input[type=file]` |
| `wait-text` | `<regex> <max_s>` | poll the body text, max 25 s | |
| `chips` | | count of bound reference chips (BROWSER_OPERATOR "Count the reference chips") | |
| `shot` | `<name>` | JPEG, at most 1280 px wide, to `$AGY_BROWSE_SHOT_DIR`, else `$WORK_DIR`, else the cwd, in `agy-shots/<name>.jpg`; prints path + bytes | a name outside `[A-Za-z0-9_-]{1,40}` |
| `mute` | | mute all media (also done on every attach) | |

There is no JavaScript verb, no cookie/storage/network-body access and no
shell. The CLI never launches a browser and never touches a tab on another host.

## The agy allow-rule (applied 2026-09-30, 16c4279f)

Exactly one rule. The CTO applies it after review to `config/agy-settings.json`
and to the installed copy `~/.gemini/antigravity-cli/settings.json` (the two
must stay identical). The deny rules (curl, ssh, rm, ...) stay as they are.

```diff
   "permissions": {
     "allow": [
       "command(regex:^(/Users/gob/MoonieXHQ/Agents/Core|/opt/MoonieXHQ/Agents/Core)/\\.venv/bin/python -m pytest( .*)?$)",
+      "command(regex:^(/Users/gob/MoonieXHQ/Agents/Core|/opt/MoonieXHQ/Agents/Core)/\\.venv/bin/python tools/agy_browse\\.py( --port [0-9]{4,5})?( --tab [A-Za-z0-9]{1,64})? (tabs|goto|text|count|state|button-label|click|type|key|upload|wait-text|chips|shot|mute)( [A-Za-z0-9 _./:#=@%+,'\"()\\[\\]-]*)?$)",
       "command(git status)",
```

The args class leaves out `;` `&` `|` backtick `$` `\` `<` `>` newline and the
shell's `*` `?` `~` expansions: nothing can be chained, substituted, redirected
or globbed (`tests/test_agy_browse.py::test_allow_rule_refuses_chained_redirected_or_foreign_commands`).
Consequences a brief must respect: a `wait-text` regex cannot use `|`, `*` or `?`
(pass a plain phrase), and typed text is ASCII (no Thai) through this rule.
A denied command ends a headless agy run (no retry), so reach a Thai-labelled
element by position instead: `count button`, `text ':nth-match(button, N)'`,
`click ':nth-match(button, N)'` (checked on champa 2026-10-01: button 2 reads
`สร้าง`). An attribute-substring selector (`[class*=x]`) is refused too.
`tools/agy_browse.ALLOW_RULE_REGEX` is the source; a test checks this page
carries the same string.

## Threat model (10 lines)

1. agy is steered by page content (prompt injection): the CLI never turns page text into a verb, path or command, and agy has no other tool.
2. Wrong site: the port must be in config, every verb re-checks the tab host, `goto` checks the target and the landing host.
3. Spending money: money-looking clicks are refused; the submit button needs a fire label read in the same call and a cooldown, so a paid control is never retried in a loop.
4. Credentials: password/OTP/card/token fields cannot be typed into; the CEO logs Homes in through the relay, never agy.
5. Data out: no cookies, storage, network bodies or JS; `tabs` never prints URLs; output is capped at 2000 chars.
6. Local files: uploads only from `upload_dirs` by realpath; screenshots only to the work dir.
7. Shell escape: one allow-rule whose arg class has no chaining, substitution, redirection or globbing characters.
8. Runaway loops: per-port calls/min limit and a 30 s cap per call.
9. Audit: every call, refused or not, is one redacted JSON line (typed text cut to 40 chars, uploads as basenames, no query strings, tokens masked).
10. Residual risk: anything a plain click can do on an allowed host that does not read like money; keep `allowed_hosts` tight and review the log.

## Briefing an agy browse task (CMO / CTO)

1. **Launch the Browser Home first** (from the Console checkout on that box:
   `node scripts/relay-home.mjs launch <id>`), and have the CEO log it in
   through the relay if needed (skill `relay-login`).
2. Put **both** of these in the brief, or the router keeps the task on Claude
   (`tools/route.class_for`, class `browser_agy` in `config/plans.yaml`):
   - the Home's CDP URL, e.g. `http://127.0.0.1:9280`;
   - the exact call form, e.g. `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python tools/agy_browse.py --port 9280 <verb>`.
3. **Every path in the brief is repo-relative** (`.claude/skills/...`,
   `config/...`). agy in headless mode cannot answer a permission prompt, so a
   read outside the worktree kills the run before it writes anything: that is
   the most likely cause of task-4ec8abff's `a tool required the "read_file"
   permission that headless mode cannot prompt for` (its brief pointed at
   `~/.claude/skills/...`). Confirm from the agy conversation log.
4. Screenshots: `shot` writes under `$WORK_DIR/agy-shots/`; make sure agy's
   workspace (`--add-dir`) covers that directory, or set
   `AGY_BROWSE_SHOT_DIR` to a folder inside the worktree.
5. Say what the task may click. A generation needs the port's
   `fire_label_regex` to match (champa: `Unlimited`); anything paid is refused.
6. The port must already be in `config/agy-browse.yaml`; a new site is a
   config row reviewed by the CTO, never an ad-hoc flag.

## Acceptance still to run (on the Mac, CTO)

- Live, read-only against `champa` mac:9280: `tabs`, `text h1`, `state`,
  `button-label`; `goto https://example.com` exits 2.
- One headless `agy -p` run that uses `agy_browse` with zero permission
  denials (after the allow-rule is applied), and one `shot` agy opens and
  describes correctly.
- No click, type or upload on a real paid control during testing.
