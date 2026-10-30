# W2 report: owner relay, re-wake ladder and live owners (cto-night, 30 Oct 2026)

Branch cto/w2-owner-relay. Round 2: the review findings are fixed, except one sub-point (see Review, item 2).

## Files changed
- tools/owner_relay.py (new, C2): turns task events into one letter per owner box per tick. It holds the shared wake rule (try_wake, screen_ready, may_wake), the mode file and the state file, plus --stats and --set-mode dry|live|off.
- tools/escalation_watch.py (C3, C4):
  - rewake_scan runs before owner_relay.run, and rewake runs after it. relay_tick and owner_tick call them inside main() on the existing timer.
  - capture_e captures panes with -e.
  - with_lock_boxes gives one entry per pane.
  - local_sessions marks each record trusted or not.
  - C4 routing: live_box, live_c_levels, the owner_box fallback, and an idle PH with work going to its lane C-level.
- tools/wake_audit.py: owner_relay is in GATED and BACKOFF_GATED, and RUNS_INSIDE ties it to the escalation-watch unit.
- tests/test_owner_relay.py (new) and tests/test_escalation_watch_w2.py (new).
- tests/test_escalation_watch.py: one line, which stubs owner_tick in the old fixture.
- docs/reports/cto-night-w2/REPORT.md: this file.

## How it runs
- It runs inside escalation_watch.py --nudge. There is no new unit, no new timer and no model call.
- The mode file is missing, so the mode is dry: each tick prints "relay [dry] would send ..." and writes state.
- To go live, as root, after reading one dry tick: python tools/owner_relay.py --set-mode live. Never write a file under state/ with a shell redirect.
- One tick runs three steps:
  1. rewake_scan does the ladder bookkeeping and builds the owner lines.
  2. owner_relay.run sends at most one letter per box (up to 8 lines and 600 chars, at most 10 letters per run) and wakes each box at most once.
  3. rewake makes the ladder tries, at 5, 15 and 45 min times wake_interval.

## Tests
- The 4 test files of the changed modules: "120 passed in 2.40s".
- The 2 W2 test files: "55 passed in 1.41s".
- wake_audit exits 0: "13 sources; 0 flagged; 0 inventory errors".
- The fail-on-base proof is the same as the base_fail_proof field: base gives an ImportError and "2 errors in 0.80s", then the C4 and capture proof gives "4 failed in 0.31s" on base and "4 passed in 0.35s" on the branch. The run against the previous tip is described in the tests field.

## Review
1. Blocker: the wake gate read panes without -e. The high-severity finding is the same issue. Fixed.
   - capture_e (tmux capture-pane -p -e) is now the default panes for owner_tick, relay_tick and rewake.
   - find() and nudge() keep the plain capture, as the reviewer asked. This leaves the M11 paths unchanged.
   - Tests: test_a_ghost_suggestion_on_an_idle_ph_is_an_empty_box_one_wake_and_no_held_try and test_the_w2_gate_captures_with_escapes_and_find_keeps_the_plain_capture.
2. Medium: the synthetic box was marked idle, so a running turn spent ladder tries. Fixed.
   - screen_ready now returns "busy: turn running on screen". rewake spends no try on an owner_relay.NO_TRY hold (busy, day cap, woken this tick). Design C3 says the same: "A busy or compacting session just waits".
   - with_lock_boxes now maps a record whose tmux is a live C-level lock box onto that box, with the record's own status. When two records name the same pane, the busy one wins.
   - Tests: test_a_running_turn_on_a_box_with_no_record_spends_no_try and test_a_record_in_the_lock_box_tmux_is_that_box_with_its_own_status.
   - Not taken: the "(or has no input box)" part. A screen that is idle by its record but has no input box (copy mode, a crashed TUI) is a held try that the owner should hear about after 3 tries; C3 says "3rd failed or held try". A C-level box's ladder never escalates anyway.
3. Medium: rule 3, the rewake letters were not batched. Fixed.
   - rewake_scan no longer sends letters. It returns lines addressed to the owner box ("to", kinds rewake and ph_dead; the next step names the resume command).
   - owner_relay.run(extra=...) merges those lines into that box's single letter for the tick, within MAX_LETTERS and MAX_LINES.
   - Overflow lines and lines whose send fails wait in pending. Before this fix, a failed escalation letter was lost.
   - Test: test_dead_phs_and_a_task_event_for_one_owner_are_one_letter_and_one_wake.
4. Medium: REPORT.md missing. Fixed by this file.
5. High: the same issue as item 1.
6. Medium: letters bypassed MAX_LETTERS, and forged session records were accepted.
   - The batching and the MAX_LETTERS count are fixed by item 3.
   - local_sessions marks a record trusted only if it is a regular file owned by root (or the current user) in a root-owned dir, and neither is writable by group or other.
   - main() gives owner_tick only trusted records. On Contabo, /root/.claude/sessions is 0700 root and its records are 0644 root.
   - Tests: test_root_record_trusts_only_a_root_file_in_a_root_dir and test_main_hands_owner_tick_only_the_trusted_records.
7. Medium: nothing wrote the mode file safely. Fixed with owner_relay.py --set-mode dry|live|off.
   - It writes the state file first if that file is missing or not ours, then the mode file (0644). Both use mkstemp and os.replace, so a link planted at either name is replaced, never followed.
   - If a directory holds the state name, it exits 1, the mode stays dry, and nothing is removed.
   - Tests: test_set_mode_writes_both_files_and_never_through_a_planted_link and test_set_mode_refuses_when_the_state_name_is_a_directory.

## Not checked / risk
- No tick has run against the live hub or the real inboxes; the tests use fakes. Read one "relay [dry]" tick in the journal before going live.
- No live pane showed a ghost suggestion during the check, so the -e path is proven only by a test string.
- A session that stays busy never spends a try, so it never reaches the owner letter. The M11 idle and waiting findings still cover it.
- These screens all spend a try: a draft, a choice prompt, no input box, an unreadable screen. A PH with a draft left in its box therefore escalates after 3 tries. That is intended, but it is a new letter for the owner.
- A box with no record whose tmux session has a different name gives "screen unreadable"; after 3 tries that letter is not woken again.
- The trust filter fails closed: if the registry dir is not owned by root or is group-writable, W2 wakes nothing. Contabo was checked.
- unread() counts every letter in a box, whoever wrote it. The cost is bounded by one letter per box per tick and 12 wakes per box per Thai day, then hourly.
- The M11 nudge() letters are separate from W2. A box can get one of each in the same run.
- Ladder lines now come from watch-owner-relay. The old sender, watch-rewake, never reached main.
- If a directory already holds state/owner_relay.json, --set-mode refuses until someone removes it by hand.
