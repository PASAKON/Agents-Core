"""iTerm tab lifecycle helpers.

Spawn is owned by tools/delegate.py:_spawn_iterm_tab. This module owns the
close side: when a task reaches `done` (post-merge) git_ops.merge_task
calls close_tab(task_id) so the DEV tab disappears and the desktop stays
clean. Tabs for tasks that are still pending / in_progress / review /
blocked stay open.

Tab title set by delegate is `<RoleDisplay> (<full task_id>)`. We match
the full task_id substring, with a 6-char fallback for tabs spawned
before the full-id title change.

## Safety: which tabs we will close

close_tab only closes a tab whose title contains the requested `task_id`
substring AND that task_id starts with `task-`. Tabs we deliberately
never close:
  - CTO Chat / CTO Log / Dev Logs (spawn-cto.sh side tabs — no task_id).
  - User-opened terminals (shells without a task_id in title).
  - Tabs from a hypothetical interactive `spawn Web Designer` REPL whose
    title does not carry a task_id.

A tab is therefore only closeable when it was spawned by the delegate
path (`tools/delegate.py:_spawn_iterm_tab`) or by `tools/resume_dev.py:
_spawn_resume_tab`. Both set the title `<Role> (task-<id>)`.
"""
from __future__ import annotations

import subprocess


def close_tab(task_id: str) -> bool:
    """Close the iTerm tab whose title contains the given task id.

    Returns True if any tab was closed. Safe to call when no matching
    tab exists (returns False).
    """
    if not task_id or not task_id.startswith("task-"):
        # Refuse to operate on inputs that don't look like a real task id.
        # Protects against accidental empty/garbage matches reaching
        # iTerm and closing the wrong tab.
        return False
    fallback = task_id[:6]
    script = f'''
tell application "iTerm"
  set closedAny to false
  repeat with w in windows
    set tabsList to tabs of w
    repeat with t in tabsList
      tell t
        if name of current session contains "{task_id}" then
          close t
          set closedAny to true
        end if
      end tell
    end repeat
  end repeat
  if not closedAny then
    repeat with w in windows
      set tabsList to tabs of w
      repeat with t in tabsList
        tell t
          if name of current session contains "{fallback}" then
            close t
            set closedAny to true
          end if
        end tell
      end repeat
    end repeat
  end if
  if closedAny then
    return "1"
  else
    return "0"
  end if
end tell
'''
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "1"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python -m tools.itermtab <task_id>")
        sys.exit(1)
    ok = close_tab(sys.argv[1])
    print(f"closed: {ok}")
