# task-c9a64255 — late milestones + shown due (lib/portfolio.py)

Status: **both fixes landed in `lib/portfolio.py`; the watch letter subject (`late: <project> M<n>`) is NOT done.**
`self_repo_guard` refused every write to `tools/portfolio_watch.py`: the task's declared touches are
`lib/portfolio.py`, `tests/test_projecttrack_p1.py`, `tests/test_portfolio_watch.py`. The patch is below; add the
path to `touches` (or apply it by hand) and drop one xfail marker.

## Diff summary

`lib/portfolio.py`
- `_shown_due(project_due, open_dues)` (new): the earlier of the project due and the latest open milestone due, or
  whichever exists. Used by `_v2_rows` (monitor v2 + `report`) and by `show()`, which carried its own copy of the old
  fallback and has an existing test that it equals the report row (`test_report_due_fallback_and_eta_stats`).
- `_v2_rows`: for a finite project, the late date is the EARLIEST of the project due and every open milestone due that
  is already past; `late_s` counts from it. A loop keeps its beat rule. It now returns a 4th value,
  `deadlines = {project id: (date, (n, title) | None)}`; `report` ignores it.
- `_monitor_v2`: the late attention item's `since` is that date (not the shown due, which can be in the future now), and
  its text is `เลยกำหนด: M<n> <title cut to 40>` when the earliest past date is a milestone's, else `เลยกำหนด` as before.
- **No `late_milestone` row field.** Console `src/portfolio/validate.js` checks every v2 row with `exact(row, V2_ROW_KEYS)`;
  an unknown key rejects the whole payload (verified with node: `projects[0]` refused). So the milestone lives only in the
  attention text (`text` is 1..80 chars there; this one is at most 62).

Interpretation to check: the milestone is named only when it is the earliest past date. Project due 20 Oct and a milestone
due 26 Oct, both past: late from 20 Oct, text plain `เลยกำหนด` (the project date is what makes it late). A tie goes to the
project date.

Where the brief's two instructions disagree: part 1 says "`due_at` shown stays as today"; part 2 (CTO Main, 11:18 TH) changes
the shown due. I applied part 2, since it is later and explicit.

`tools/portfolio.py`: no change (it prints `pf.report` rows; `render_report` prints `r["due_at"]`).

## Tests (new, 16 passing + 1 strict xfail)

`tests/test_projecttrack_p1.py` (14): open milestone 10 min overdue, project due tomorrow → `late_s` 600, attention item
with `M1 …`, `since` = the milestone's date, no `late_milestone` key; same after `replan` → not late, count 0; title cut
to 40 and one line; done overdue milestone → not late; 9 parametrized cases of "earliest past date" (project-due-past
unchanged, both past either way round, no project due, nothing past); loop unaffected by milestones; shown due = earlier
of project due and last open milestone in monitor v2, `report`, `render_report` and `show` (SafeRestart shape).

`tests/test_portfolio_watch.py` (2 + 1 xfail): through the real payload and `run()` — 10 min overdue milestone → 1 letter to
the PH, a second run sends nothing, `replan` of that milestone → no finding, episode removed; done milestone and loop
with an old milestone → no finding (loop keeps `due <next beat date>`); the subject test is `xfail(strict=True)`.

Red before the fix (same tests, `lib/` unchanged): `7 failed, 194 passed, 36 skipped` — `late_s None == 600`, shown due
`2026-10-29` instead of `2026-10-27`, etc. The unchanged cases (project-due-past, loop, done, nothing past) passed both times.

Test tail (`env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR .venv/bin/python -m pytest tests/test_projecttrack_p1.py tests/test_portfolio_watch.py tests/test_portfolio.py -q -p no:cacheprovider -o addopts=''`):

```
201 passed, 36 skipped, 1 xfailed in 4.29s        (baseline before: 185 passed, 36 skipped)
```

Console validator: a v2 payload with a milestone-late, a project-late, a loop-late (M12 + a 60-char title) and a
stale-import row passes `validatePayload` (read-only import of the Console file); adding a `late_milestone` key fails.

## The blocked part: `tools/portfolio_watch.py` (needs the path in `touches`)

Confirmed: the watch reads the flags from `monitor_payload(version=2)["attention"]`, so detection, episodes, the PH letter
and the 4 h owner step already follow the new rule with no change. Only the subject needs the milestone. The attention item
has no spare key, so the watch reads `M<n>` from the text. Three edits:

1. Before `_ROLE_RE = re.compile(...)`:
```python
_LATE_MILESTONE = re.compile(r"เลยกำหนด: M(\d+)\b")   # the text lib/portfolio.py gives a late milestone
```
2. In `findings()`, replace the line `what = {"late": f"due {_iso(since)[:10]}", "no_plan": "no dated milestone",` with:
```python
        late = _LATE_MILESTONE.match(a.get("text") or "")      # late because of a milestone: name it
        what = {"late": f"M{late[1]}" if late else f"due {_iso(since)[:10]}", "no_plan": "no dated milestone",
```
3. Docstring (optional), above "Never a letter for a parked or closed project": one line saying a late milestone is named in the subject.

Result: subject `late: Proj M1`, body `project Proj (proj) is late (M1; since 2026-10-27T02:50Z, 10 min ago) …`; a project-level
late stays `late: Proj due 2026-10-27`. Then delete the `@pytest.mark.xfail(...)` line on
`test_the_letter_about_a_late_milestone_names_it_in_the_subject` (strict: it fails with XPASS until you do).
The regex was checked against the real attention text (`M1`, `M12`, and no match on the plain text); the patched file
itself was not run.
