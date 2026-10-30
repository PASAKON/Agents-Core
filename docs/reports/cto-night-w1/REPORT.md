# W1: the worker report hook reaches its owner, and the CEO's /run note arrives in full

Wake chain, CTO Main brief /root/cto-night/w1-w2-brief.md (design C1 and C6), 30 Oct 2026. Branch cto/w1-hook-root-full-note, base origin/main 3a5ea30a.

## What changed
- **C1** (scripts/hook-log-dev-reply.py): ROOT is always the script's own checkout, flag on or off. LEGACY_ROOT (the Mac path) is gone. With the flag off, the Contabo worker Stop hook used to import lib.db and tools.send_to_cto from a tree that has neither, so no Claude worker's report reached its owner.
- **C6** (scripts/hook-inbox.py): after the body of a letter from run-inbox, the hook prints the CEO's note in full, up to 2000 chars, flag on or off. That covers the answer of a question, each answer in a batch, and the question of an ask-back. No other field is printed.
- **Review round** (hook-log-dev-reply.py). Fixing the root made the flag-off path live on Contabo. All four problems the reviewers found are fixed:
  1. **Rate limit.** rate_limited comes only from this turn's API error records, flag on or off. Prose is no longer read. The UPDATE runs only `WHERE status='in_progress'`, so it never overwrites review, done or cancelled. The relay note no longer promises an auto-resume; it reads "rate limit hit this turn; retry after ~300s".
  2. **Relay gate.** Only a turn that called submit_report, dev_message or file_blocker_issue, or hit a rate limit, is logged and relayed, flag on or off.
     - send_to_cto gets the letter's kind and prio, so a report or a fyi never wakes a C-level box (lib.mailbox.quiet_for). A PH box wakes.
     - With the flag off, the body starts "<kind> · <prio> ·" (the plain-text kind lib.mailbox.body_kind reads).
     - The letter is at most 600 chars (token rule 5).
     - An ownerless task is logged but not relayed.
  3. **last_checkpoint.** The hub UPDATE sets only session_id and updated_at. dev_message keeps the worker's full message in tasks.last_checkpoint (GH #54), and the Stop hook used to write a timestamp over it.
  4. **Log append.**
     - Each directory is opened O_DIRECTORY|O_NOFOLLOW relative to its parent. Each log is opened O_WRONLY|O_APPEND|O_CREAT|O_NOFOLLOW|O_NONBLOCK, mode 0644, relative to its directory.
     - The line is written only when fstat shows a regular file with one link.
     - Any path other than state/logs/<name> is skipped.
     - A platform with no dir_fd (Windows) takes a plain append that still skips a symlink, as lib.mailbox does.

## Files changed
- scripts/hook-log-dev-reply.py: C1, then the review fixes.
- scripts/hook-inbox.py: C6.
- tests/test_hook_dev_reply_root.py (new): root with the flag on or off, compat link, 3 end-to-end runs of the real script against stub lib/tools.
- tests/test_hook_inbox_answer.py (new): C6.
- tests/test_org_mail_envelope.py: the flag-off tests now test the new rules.
- docs/reports/cto-night-w1/REPORT.md: this file.

## Tests run
`.venv/bin/python -m pytest tests/test_org_mail_envelope.py tests/test_hook_dev_reply_root.py tests/test_hook_inbox_answer.py` -> 52 passed in 12.13s.

## Fail on base, pass on branch
- Method 1: the base scripts checked out in the worktree, then restored from HEAD.
- base 37 failed, 15 passed in 6.75s; branch 52 passed in 12.13s.
- The 15 that pass on base are guards: the envelope tests that predate W1, the old-429 [True] case, and 3 hook-inbox guards.
- A flag-off test asserts the copy's ROOT before it runs the hook, so the base copy fails before it writes anything.
- Real-lib repro (the reviewers' driver, flag off, throwaway SQLite, stub tmux):
  - A: review, an earlier "1429", then a report turn. Stays review, one report letter in project_head-<owner>, one wake attempt.
  - A0: control, the same result.
  - B: a progress turn. No letter, no wake.
  - C: done, an earlier "HTTP 429". Stays done, no letter.
- gitleaks: exit 0. Invisible-character scan: nothing found.

## Review
The list I got was cut inside item 7. Items 1 and 6 are the same finding, and so are 5 and 7.
- **1/6 blocker (rate_limited from prose, no status guard):** real, fixed.
  - The pinned "legacy over-match" assertion now expects False.
  - New tests: test_old_429_prose_then_a_report_keeps_review (on/off); test_a_real_rate_limit_moves_only_a_task_at_work (4 statuses x on/off); e2e test_flag_off_old_429_prose_does_not_rate_limit_the_report.
- **2 high (flag off relays every turn, kind-less, wakes):** real, fixed.
  - test_flag_off_still_relays_every_turn is replaced by: _a_progress_turn_sends_nothing, _a_report_turn_names_its_kind, _a_report_wakes_a_ph_box_never_a_c_level_box (through the real send_to_cto), _the_letter_is_at_most_600_chars, and e2e _a_progress_turn_reaches_nobody.
  - The e2e report test pins kind and prio.
  - Rules 3, 6 and 8 (batching, busy pane, daily cap) belong to W2's ticks. The hook sends one letter per event turn, as envelope mode does.
- **3 high (REPORT.md missing):** real. The harness refused the file write from this subagent, so the parent commits this text.
- **4 medium (last_checkpoint overwritten):** real, fixed. A grep found no reader that uses it as a timestamp. Test: test_the_stop_hook_keeps_the_dev_message_text (on/off).
- **5/7 (symlink-following root append in state/logs):** real, fixed.
  - Tests: test_a_planted_link_in_state_logs_is_not_followed (symlink and second hard link, on/off); _a_planted_logs_directory_link_; _without_dir_fd_.
  - The writes fixture now sees os.open, so T16 still proves nothing is written outside the checkout.

**What W2 can rely on:**
- A submit_report turn sends one kind=report, prio=urgent letter from developer-<task>. It wakes a PH box at once and never a C-level box.
- W2's _reviewed_by_worker skip therefore gives a PH exactly one wake per review and a C-level owner none (rule 2). If a C-level owner should be woken for a review, W2 must not skip for C-level boxes.
- W2's rewake filter (`k not in mailbox.QUIET_KINDS`, escalation_watch.py:562 and :601 at 397ad70c) treats a report as quiet in every box. So if a PH's first wake for a report is held, nothing retries it. `mailbox.quiet_for(role, k)` would retry it. That is W2's call.
- last_checkpoint now keeps the dev_message text, so W2's blocked reason reads the worker's words.

## Not checked / risk
- **No live drill.** No real Claude worker has run the new hook on Contabo. The design's drill (one tiny PH-owned task; letters-meta shows developer-task-x -> project_head-<id>) comes after the merge.
- **The flag-off change reaches Mac and winbox workers too.** Progress turns no longer reach the owner's box or cto.log.
- **A CTO-owned task's report reaches the CTO twice:** as the letter and as the cto.log line (hook-log-prompt.py). This was already so on the Mac and is outside W1's touches.
- **A real rate limit on Contabo has no resumer.** Nothing runs runners/auto_resume.py there, so the task stays rate_limited until its owner acts or gc_stale_tasks cancels it. W1 only drops the false promise.
- **The rate_limited UPDATE writes no event row** (as before), so W2's cursor does not see it.
- **A slow hub can still hold the Stop.** The flag-off hub write uses get_conn()'s default (a 3 s connect timeout), so a hub that connects but answers slowly can hold the worker's Stop longer.
- **send_to_cto's own log writes were not checked against gate 2b.** tools/send_to_cto.py is outside W1's touches; the hook no longer reaches its ownerless path. That check is for CTO Main.
- **Not run here:** /security-review (CTO Main runs it at the gate) and the full suite (CI runs it).
