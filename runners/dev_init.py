"""DEV launcher — claims a task, then execs the right viewer for it.

Invoked from inside an iTerm tab spawned by tools/delegate.py:
    python -m runners.dev_init <role> <task_id>

Two modes:

* **Default (developer/tester/devops/…):** exec the Claude Code TUI in
  the worktree. Tab becomes an interactive claude session with the task
  description as the first prompt and `submit_report` MCP wired.

* **web_designer on a `spawn_backend: tmux` project:** the agent loop
  is driven by claudesign daemon (Web UI chat → `mooniex-tmux` adapter
  → bridge `tools/claudesign_tmux_bin.py` → spawns real claude per
  message). The tmux pane is a **passive viewer** that tails the bridge
  mirror file so the iTerm tab + ttyd browser see every stream-json
  line claude emits. We never spawn the TUI for this role.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import display_for, get_project, role as get_role, dev_provider_overrides

ROOT = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = ROOT / "scripts" / "hook-log-dev-reply.py"

# Tools every worker DEV may call, regardless of role.
_BASE_DEV_TOOLS = (
    "mcp__org__wiki_read mcp__org__wiki_list mcp__org__wiki_search "
    "mcp__org__submit_report mcp__org__dev_message "
    "mcp__org__file_blocker_issue mcp__org__request_human_handoff "
    "mcp__lungnote__list_todos mcp__lungnote__add_todo "
    "Read Write Edit Bash Glob Grep"
).split()

# browser_operator only. Still narrower than the full Chrome surface: no
# gif_creator, no shortcuts_execute, no browser switching.
#
# Upload was withheld at first on exfiltration grounds and granted 2026-08-10
# (CEO) because reference images are the job — the C-level names the path in
# the task. Two guardrails make that safe enough: file_upload is restricted by
# the harness itself to files shared with the session, and the role doc forbids
# uploading any path the task did not name.
#
# resize_window is load-bearing, not optional — an image costs
# ceil(w/28) * ceil(h/28) visual tokens with no client-side cap (measured
# 2026-08-10: neither MAX_MCP_OUTPUT_TOKENS nor
# CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS truncates an image result), so
# shrinking the window is the only lever that bounds screenshot cost. It works
# — a 1024x768 resize produced a 1024x591 screenshot — but it can silently
# no-op on a window the OS will not resize (a fullscreen one) while still
# returning success, so the skill requires verifying the result.
_CHROME_TOOLS = (
    "mcp__claude-in-chrome__tabs_context_mcp "
    "mcp__claude-in-chrome__tabs_create_mcp "
    "mcp__claude-in-chrome__tabs_close_mcp "
    "mcp__claude-in-chrome__navigate "
    "mcp__claude-in-chrome__read_page "
    "mcp__claude-in-chrome__get_page_text "
    "mcp__claude-in-chrome__find "
    "mcp__claude-in-chrome__resize_window "
    "mcp__claude-in-chrome__computer "
    "mcp__claude-in-chrome__form_input "
    "mcp__claude-in-chrome__file_upload "
    "mcp__claude-in-chrome__upload_image "
    "mcp__claude-in-chrome__javascript_tool "
    "mcp__claude-in-chrome__browser_batch "
    "mcp__claude-in-chrome__read_console_messages "
    "mcp__claude-in-chrome__read_network_requests"
).split()


def dev_tool_grants(role: str) -> tuple[list[str], list[str]]:
    """Return (allowed_tools, extra_claude_flags) for a worker role.

    Single source of truth because runners/dev_resume.py rebuilds the same
    argv: when the two lists drift, a resumed DEV silently loses capabilities
    its task depends on and the failure looks like the model being lazy.

    Chrome is gated on the `--chrome` flag, not on MCP config — Claude in
    Chrome is a built-in CLI integration, not an entry in dev.mcp.json.
    Verified 2026-08-10: with `--strict-mcp-config` and no `--chrome`, the
    Chrome tools are absent ("tool not found in available deferred tools");
    adding `--chrome` makes them resolve while strict MCP stays on.
    """
    allowed = list(_BASE_DEV_TOOLS)
    flags: list[str] = []
    if role == "web_designer":
        # design skills (frontend-design / mooniex-tool-builder) are
        # invocable so the agent can lean on the org's UI craft skill.
        allowed.append("Skill")
    if role == "browser_operator":
        allowed.extend(_CHROME_TOOLS)
        allowed.append("Skill")  # loads the browser-operator skill
        flags.append("--chrome")
    return allowed, flags

# Role → the knowledge banks (paths under knowledge/) symlinked into that
# role's DEV worktree.  A role may carry more than one bank: web_designer
# owns the design bank but has to execute against the theme the CMO set, so
# it also gets brand-knowledge — read it, don't redefine it.  Listing both
# here keeps that dependency visible instead of hiding it behind a symlink
# buried inside a bank.  Roles without an entry (developer, tester,
# devops_engineer, …) get nothing — no error.
KNOWLEDGE_MAP: dict[str, list[str]] = {
    "ads_manager": ["knowledge/ads-knowledge"],
    "content_strategist": ["knowledge/content-knowledge"],
    "data_analyst": ["knowledge/data-knowledge"],
    "cfo": ["knowledge/finance-knowledge"],
    "finance": ["knowledge/finance-knowledge"],
    # CMO owns the brand: positioning, theme, voice, and the brief that goes
    # to the designer.
    "cmo": ["knowledge/brand-knowledge"],
    # Designer owns craft and the design system; brand-knowledge rides along
    # so the theme and brand gates are at hand without a second lookup.
    "web_designer": ["knowledge/design-knowledge", "knowledge/brand-knowledge"],
}


def _symlink_knowledge(worktree: str, role: str) -> None:
    """Symlink every knowledge bank mapped to this role into the worktree,
    read-only by intent.  No-op for an unmapped role, and any bank missing
    from disk is skipped (scaffolded-but-empty is fine).  knowledge/ is only
    created once a real bank is about to land in it."""
    for rel in KNOWLEDGE_MAP.get(role, ()):
        src = ROOT / rel
        if not src.is_dir():
            continue
        dst = Path(worktree) / "knowledge" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() or dst.is_symlink():
            dst.unlink()  # stale link from a prior run
        dst.symlink_to(src)


def _root_mcp_server_names() -> list[str]:
    """Server names declared in Agents/.mcp.json (CTO-only servers, e.g.
    Supabase). DEV worktrees live physically under Agents/worktrees/, so
    Claude Code discovers this ancestor .mcp.json and shows an interactive
    trust/approval TUI screen before the chat even starts — which blocks
    the automated kickoff ping (it types into a chat prompt that doesn't
    exist yet). Returns [] if the file is missing or malformed."""
    root_mcp = ROOT / ".mcp.json"
    if not root_mcp.is_file():
        return []
    try:
        data = json.loads(root_mcp.read_text(encoding="utf-8"))
        return list((data.get("mcpServers") or {}).keys())
    except (json.JSONDecodeError, OSError):
        return []


def _write_dev_settings(worktree: str) -> None:
    """Drop .claude/settings.local.json into the worktree so claude wires
    the Stop hook that relays DEV replies into cto.log, and explicitly
    disables any project-scoped MCP servers inherited from Agents/.mcp.json
    (see _root_mcp_server_names) so DEV spawns never hit the interactive
    approval screen for servers they were never meant to use — DEVs get
    MCP access only via --mcp-config config/dev.mcp.json."""
    settings_dir = Path(worktree) / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "permissionMode": "auto",
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"python3 {HOOK_SCRIPT}",
                        }
                    ]
                }
            ]
        },
    }
    inherited = _root_mcp_server_names()
    if inherited:
        cfg["disabledMcpjsonServers"] = inherited
    (settings_dir / "settings.local.json").write_text(
        json.dumps(cfg, indent=2), encoding="utf-8"
    )


def _build_prompt(task, project, worktree) -> str:
    return f"""# Task {task['id']}

Project: {project['name']} ({project['key']})
Stack: {', '.join(project.get('stack', []))}
Repo path (your worktree, work ONLY here): {worktree}
Branch: {task['branch']}
Default branch (do NOT touch): {project['default_branch']}

## Description

{task['description']}

---

## Instructions

1. Read your role doc (already in your system prompt).
2. Read relevant wiki pages (use mcp__org__wiki_read).
3. Inspect the codebase you've been given (your cwd is the worktree).
4. Implement the task incrementally with commits inside your worktree.
5. Run tests if patterns exist.
6. When done, call `mcp__org__submit_report` with your final report
   (files changed, tests run, blockers). This is how the CTO learns
   you finished — without it the task stays in_progress forever.

Begin.
"""


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: python -m runners.dev_init <role> <task_id>", file=sys.stderr)
        sys.exit(1)
    role = sys.argv[1]
    task_id = sys.argv[2]

    db.init()
    task = db.get_task(task_id)
    if not task:
        print(f"task {task_id} not found", file=sys.stderr)
        sys.exit(2)
    if not db.claim_task(task_id, agent=role):
        print(f"could not claim task {task_id}", file=sys.stderr)
        sys.exit(3)

    worktree = task.get("worktree")
    if not worktree or not Path(worktree).exists():
        db.update_status(task_id, "failed", report="worktree missing", actor=role)
        print(f"worktree missing for task {task_id}", file=sys.stderr)
        sys.exit(4)

    project = get_project(task["project"])
    backend = (project.get("spawn_backend") or "iterm").lower()

    # web_designer on a tmux/Web-UI-bridge project is driven by the
    # claudesign daemon (Web UI chat → bridge → real claude per message),
    # so the pane is just a passive tail of the bridge mirror. On the
    # default iTerm backend it instead runs as an autonomous claude TUI
    # exactly like any other DEV — so the CTO's `delegate_task` behaves the
    # same as for `developer`, only with the web_designer role doc + the
    # design source resolved from the project UUID (CEO 2026-06-15). The
    # CEO-driven Web UI flow is a separate path (scripts/spawn-web-designer.sh).
    if role == "web_designer" and backend == "tmux":
        try:
            db.update_status(task_id, "in_progress", pid=os.getpid(), actor=role)
        except Exception as e:
            print(f"warn: could not record pid for {task_id}: {e}", file=sys.stderr)
        mirror = Path("/tmp") / f"mooniex-mirror-{task_id}.log"
        mirror.touch(exist_ok=True)
        banner = (
            f"\\033[1mWeb Designer viewer\\033[0m — task={task_id}\\n"
            f"worktree: {worktree}\\n"
            f"mirror:   {mirror}\\n"
            "Type prompts in the claudesign Web UI. "
            "Output streams here as JSONL.\\n"
            f"------------------------------------------------------------\\n"
        )
        os.execvp("/bin/zsh", [
            "/bin/zsh", "-lc",
            f"printf '{banner}' && tail -F {mirror}",
        ])
        return  # unreachable

    shared_doc = (ROOT / "roles" / "_dev_shared.md").read_text()
    role_doc = shared_doc + "\n\n" + (ROOT / "roles" / f"{role}.md").read_text()
    prompt = _build_prompt(task, project, worktree)
    # web_designer's worktree omits the gitignored .od/, so resolve the
    # design source (project UUID → absolute read-only path + skill) from
    # the task description and append it so the autonomous agent knows which
    # brand/theme to match — the same context the CEO's Web UI flow has.
    if role == "web_designer":
        prompt += db.designer_kickoff_suffix(task.get("description") or "")
    try:
        model = get_role(role).get("model") or "claude-opus-5"
    except ValueError:
        # role file exists in roles/ but not registered in policies/agents.yaml
        # fall back to worker-tier default
        model = "claude-opus-5"

    env = os.environ.copy()
    env["DEV_TASK_ID"] = task_id
    env["DEV_ROLE"] = role
    if task.get("owner_cto"):
        env["DEV_CTO_ID"] = task["owner_cto"]
        # owner_role picks which <role>-<id>.winid lock send_to_cto reads so
        # CFO/CMO-spawned reports route to the CXO tab, not a CTO tab. Pre-
        # migration rows have owner_cto but NULL owner_role → default cto.
        env["DEV_CTO_ROLE"] = task.get("owner_role") or "cto"

    # PID survives os.execvpe — record now so the watchdog can probe the
    # claude TUI's liveness directly instead of guessing from log mtime.
    try:
        db.update_status(task_id, "in_progress", pid=os.getpid(), actor=role)
    except Exception as e:
        print(f"warn: could not record pid for {task_id}: {e}", file=sys.stderr)

    _write_dev_settings(worktree)
    _symlink_knowledge(worktree, role)

    task_md = Path(worktree) / "TASK.md"
    task_md.write_text(prompt, encoding="utf-8")

    # Auto Browser (docker + noVNC) was removed 2026-05-19 in favour of
    # Claude in Chrome (native messaging extension). Until 2026-08-10 that
    # left browser work with nowhere to run but a C-level tab; the
    # browser_operator role now carries it, and dev_tool_grants() decides
    # which roles get the Chrome surface + the --chrome flag. Still no
    # per-role MCP config branch — all DEVs share dev.mcp.json.
    allowed, chrome_args = dev_tool_grants(role)
    mcp_config = ROOT / "config" / "dev.mcp.json"

    # DEV model provider override (flag-gated, reversible). When
    # DEV_MODEL_PROVIDER is set, worker DEVs run on a cheaper Anthropic-
    # compatible endpoint (Z.ai -> GLM-5.2) instead of
    # C-level orchestration is unaffected. Unset -> original behaviour.
    # tasks.model_hint='claude' overrides the quota router for this one task —
    # see lib.config.dev_provider_overrides. Set by the CTO when a cheap miss
    # would be expensive (reviewing/repairing someone else's work, security).
    _ov = dev_provider_overrides(role, task.get("model_hint"))
    effort_args = ["--effort", get_role(role).get("effort") or "high"]
    if _ov:
        model = _ov["model"]
        env.update(_ov["env"])
        if _ov["effort"] is None:
            effort_args = []

    os.chdir(worktree)
    os.execvpe(
        "claude",
        [
            "claude",
            "-n", f"{display_for(role)} ({task_id})",
            "--model", model,
            *effort_args,
            "--permission-mode", "auto",
            "--append-system-prompt", role_doc,
            "--mcp-config", str(mcp_config),
            "--strict-mcp-config",
            *chrome_args,
            "--allowed-tools", *allowed,
            prompt,
        ],
        env,
    )


if __name__ == "__main__":
    main()
