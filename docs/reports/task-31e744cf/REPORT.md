# REPORT task-31e744cf

## Summary

Updated `docs/design/mooniex-care.md` to add **§6 (`Care Session + Escalation`)** incorporating the design from `docs/plans/2026-11-19-mooniex-care-team.md` (§2–3, SomPong repo, read-only), while preserving **§1–5** and all existing **TBDs** unchanged (`+101 / -0` lines). No code files were created or modified.

## Files Changed

- `docs/design/mooniex-care.md` — Appended §6 (`## 6. Care Session + Escalation`) after line 207 (`+101 / -0` lines; lines 1–207 in §1–5 are untouched byte-for-byte).
- `docs/reports/task-31e744cf/REPORT.md` — Created task completion report with diff summary and risk section.

## Diff Summary (`docs/design/mooniex-care.md`)

- **Lines 1–207 (§1–5):** `0` deletions, `0` modifications. All existing sections and all §1–5 `TBD` entries (`CDP Port`, `Reply-Token Lifetime`, `Quota Reset Time`, `Exact Throttle Ceilings`) are preserved verbatim.
- **Lines 208–308 (§6 added, `+101` lines):**
  - **§6.1 `care` Role & LuNar Cutover:** Defines role `care` (persona **"น้องมูน" / Moon**, **Sonnet 5.5**, supervised by SomPong `coo` on Opus 5.5) running in its own tmux session with its **own Unix user and gate** (`docs/design/sompong-coo-session.md` / `family_gate` pattern). Specifies that `care` builds the answers and writes them to `care_outbox`, and that the **old LuNar chat flow is switched off only after `care` answers live**.
  - **§6.2 Inbound `care_queue`, Immediate Ack & Hourly Round (`08-22 TH`):** Covers webhook ingestion into `care_queue` with no model at ingest, immediate fixed acknowledgement via free webhook `replyToken` once per quiet thread per `N` hours (**TBD**), hourly batch rounds from **`08:00` to `22:00` TH** (`08-22 TH`, grouping all messages per customer thread into one wake event and enqueueing ≤5 bubbles per API call into `care_outbox`), and active-case live turns via free `replyToken`.
  - **§6.3 Escalation (`care -> coo -> CEO Card -> Goal + FAQ Rule`):** Covers mandatory escalation triggers (money, rebates, complaints, promises, and any unknown/unverified question), customer holding line (`"ขอเช็คให้ก่อนนะครับ"`), `coo` fact analysis, **3 ranked answers on one CEO Run Inbox question card**, and `coo` converting the CEO's response/instruction into **(a) a per-customer goal** and **(b) a permanent FAQ / playbook rule**.
  - **§6.4 Per-Customer Goal and Step State:** Covers persistent per-customer `goal` and `current_step` state driving short, turn-by-turn human-admin style progression across hourly batches, live turns, and session restarts.
  - **§6.5 `care` Gate Tool Allowlist & Security Rules:** Documents the strict allowlist (`reply`, `skip`, `history` for that customer only, `media`, `escalate`, **FAQ read**) and hard denylist (**no `Bash`, no `Edit`/`Write`, no web fetch of customer links, no org tools, no secrets**), treating customer text strictly as data, plus Phase 1 exclusion of XM/Exness partner account lookups.
  - **§6.6 Voice:** Reuses the CEO's admin voice from existing **LunarAgent AI skills (via the Lunar project owner)** rather than inventing a new voice, with `CMO_Standard_HumanVoice_TH` as the final pass on fixed texts.
  - **§6.7 Bug Route & Daily Digest:** Documents the **`care -> coo -> CTO`** bug/fix route (no CEO round-trip except money, secrets, or permanent deletion) and the **`21:00 TH` daily digest** to `coo` (total chats, answered/escalated/open breakdown, top questions -> FAQ updates).
  - **§6.8 Care Session & Escalation Risk Table and Additional TBDs:** Documents 5 session/escalation risks and preserves open §6 TBDs (instant-ack quiet window `N` hours, active-case live-turn window, and per-call vs. per-bubble LINE push quota counting).

## Risk Section

1. **Prompt Injection & Privilege Escalation via Customer Messages:**
   - *Risk:* Adversarial customer input attempts to trigger shell commands, file edits, cross-customer data leaks, or secret exfiltration.
   - *Mitigation:* Customer text is treated strictly as data. `care` runs under its **own Unix user** behind a dedicated gate that exposes only `reply`, `skip`, per-customer `history`, `media`, `escalate`, and read-only FAQ lookup — with **no `Bash`, `Edit`, web fetch, org tools, or secrets**.
2. **Cutover Gap or Duplicate Replies Between Old LuNar Flow and `care`:**
   - *Risk:* Disabling the old LuNar chat flow before `care` is verified in production could drop customer messages, while running both uncoordinated could double-reply.
   - *Mitigation:* The **old LuNar chat flow is switched off only after `care` answers live** in Phase 1 verification, with atomic cutover into `care_outbox` (`idempotency_key` deduplication).
3. **Ungrounded Promises or Financial/Rebate Misstatements:**
   - *Risk:* `care` hallucinates a rebate amount, payout promise, or policy rule not in the FAQ.
   - *Mitigation:* Hard policy and gate rule requiring `escalate` to `coo` for all money, rebates, complaints, promises, and unknown questions; `coo` presents **3 ranked answers on one CEO question card** and codifies the ruling into a customer goal and FAQ rule.
4. **State Loss Across Hourly Rounds or Restarts:**
   - *Risk:* Multi-turn goal resolution loses track of the customer's progress between hourly rounds (`08-22 TH`).
   - *Mitigation:* Persistent **per-customer goal and step state** stored in the hub so every round or session restart resumes at the exact step.
5. **Free Push Quota Burn (300/Month Limit):**
   - *Risk:* Multi-message turn-by-turn conversations exhaust the 300/month free push quota.
   - *Mitigation:* Immediate acks and active-case live turns use the free webhook `replyToken`; multi-line replies bundle up to 5 bubbles in one call; post-expiry 1-on-1 replies route through the `winbox` `chat.line.biz` browser sender (§3–4), reserving API push only for post-expiry important announcements.

## Validation Performed

- Verified via file read and edit diff that `docs/design/mooniex-care.md` lines 1–207 (§1–5 and all existing TBDs) were completely unmodified (`+101 / -0` lines).
- Verified every required item from `/opt/MoonieXHQ/Agents/SomPong/docs/plans/2026-11-19-mooniex-care-team.md` (§2–3) is covered in §6 of `docs/design/mooniex-care.md`.
- Confirmed no code files were touched.

## Limitations

- Read-only reference to `/opt/MoonieXHQ/Agents/SomPong/docs/plans/2026-11-19-mooniex-care-team.md`; no runtime or code changes were made per task brief ("Edit docs/design/mooniex-care.md ONLY ... No code").

## Blockers

- None.

## Skill learning

- (none)
