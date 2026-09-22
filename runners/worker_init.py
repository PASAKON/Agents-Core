"""DEV launcher — claims a task, then execs the right viewer for it.

Invoked from inside an iTerm tab spawned by tools/delegate.py:
    python -m runners.worker_init <role> <task_id>

Two modes:

* **Default (developer/tester/devops/…):** exec the Claude Code TUI in
  the worktree. Tab becomes an interactive claude session with the task
  description as the first prompt and `submit_report` MCP wired. This is
  the same TUI regardless of backend — on a `spawn_backend: iterm`
  project (`config/projects.yaml`) it runs directly in the iTerm tab's
  shell; on `spawn_backend: tmux` (task-2f04a8ca, CEO 2026-08-14 — most
  projects as of this task) it runs inside a tmux pane that the iTerm tab
  attaches to (`tmux attach -t <session>`, wired by
  `tools/delegate.py:_spawn_iterm_tab`) instead. IRON-RULES §29 holds
  either way: the tab is still visibly attached. tmux backend exists so
  `tools.send_to_worker`'s wake has something to type into — a wake only
  fires against `task["tmux_session"]`, which only a tmux-backend project
  ever sets; on iterm backend the wake silently no-ops (mailbox delivery
  still succeeds, but nothing prompts the DEV to read it before its next
  turn).

* **web_designer on a `spawn_backend: tmux` project:** the agent loop
  is driven by claudesign daemon (Web UI chat → `mooniex-tmux` adapter
  → bridge `tools/claudesign_tmux_bin.py` → spawns real claude per
  message). The tmux pane is a **passive viewer** that tails the bridge
  mirror file so the iTerm tab + ttyd browser see every stream-json
  line claude emits. We never spawn the TUI for this role. Unchanged by
  task-2f04a8ca — this is the claudesign Web-UI path, not the general
  tmux-backend rollout above; `config/projects.yaml` deliberately leaves
  mooniex-claudesign on `spawn_backend: iterm` so this branch stays dead
  there (see that file's comment on the `mooniex-claudesign` entry).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import (
    get_project,
    host as get_host,
    role as get_role,
    worker_provider_overrides,
    worker_session_name,
)

ROOT = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = ROOT / "scripts" / "hook-log-dev-reply.py"

# Tools every worker DEV may call, regardless of role. Skill is here (not a
# per-role add-on) because every role now carries a skills_profile (ADR 0022
# §2) -- a role with visibility configured and no tool to use it with would
# be pointless. Before this, only web_designer and browser_operator granted
# it explicitly.
_BASE_WORKER_TOOLS = (
    "mcp__org__wiki_read mcp__org__wiki_list mcp__org__wiki_search "
    "mcp__org__submit_report mcp__org__dev_message "
    "mcp__org__file_blocker_issue mcp__org__request_human_handoff "
    "mcp__org__skill_objection mcp__org__decide "
    "mcp__lungnote__list_todos mcp__lungnote__add_todo "
    "Read Write Edit Bash Glob Grep Skill"
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
    "mcp__claude-in-chrome__read_network_requests "
    # Browser selection: with several Chromes paired to the account the CLI
    # refuses every browser action until one is chosen (2026-09-07, winbox).
    "mcp__claude-in-chrome__list_connected_browsers "
    "mcp__claude-in-chrome__select_browser "
    "mcp__claude-in-chrome__switch_browser"
).split()


def clean_title(title: str | None) -> str:
    """Collapse a task title to a single line for use in a session name.

    `lib.config.worker_session_name` truncates to ~40 chars but does not
    strip embedded newlines (a title pasted from chat can carry one) --
    left in, one would break both the `-n` argv token's readability and
    the AppleScript title escape a resumed tab reasserts.
    """
    return " ".join((title or "").split())


def current_host() -> str:
    """Host key (config/hosts.yaml) this runtime is on.

    Defaults to 'mac' -- this launcher was Mac-only through task-af5268b3.
    ORG_HOST lets the identical code run unchanged on Contabo later (ADDENDUM
    1, CTO 2026-09-07): the CEO only ever talks to a session from the Claude
    app, so every worker's name has to say which machine spawned it.
    """
    return (os.environ.get("ORG_HOST") or "mac").strip().lower() or "mac"


def remote_control_args(host_name: str) -> list[str]:
    """``["--remote-control"]`` if `host_name` opts in, else ``[]``.

    Reads `config/hosts.yaml`'s per-host `remote_control` flag, defaulting
    to True (every host opts in today) so an unlisted or not-yet-declared
    host still gets Remote Control rather than silently losing it. Fails
    open the same way on an unknown host key -- never let a config typo
    strand a worker unreachable from the Claude app.
    """
    try:
        enabled = get_host(host_name).get("remote_control", True)
    except ValueError:
        enabled = True
    return ["--remote-control"] if enabled else []


def worker_claude_argv(
    *,
    prompt: str,
    session_name: str,
    model: str,
    effort_args: list[str],
    role_doc: str,
    mcp_config: Path,
    chrome_args: list[str],
    allowed: list[str],
    host_name: str,
    extra_flags: list[str] | None = None,
) -> list[str]:
    """Shared claude argv assembly for worker_init and worker_resume.

    Single source of truth -- the two launchers used to hand-duplicate this
    (worker_resume's docstring already warned they must not drift, and they
    already had: worker_init's `-n` was `<display> (<task_id>)`, worker_resume's
    was `<role>:<task_id>`). Positional `prompt` goes FIRST, before any flag,
    and `--allowed-tools` goes LAST with nothing after it -- that flag is
    variadic and swallows every following argv element (see the note at the
    execvpe call site).
    """
    return [
        "claude",
        prompt,
        "-n", session_name,
        "--model", model,
        *effort_args,
        *(extra_flags or []),
        "--permission-mode", "auto",
        "--append-system-prompt", role_doc,
        "--mcp-config", str(mcp_config),
        "--strict-mcp-config",
        *chrome_args,
        *remote_control_args(host_name),
        "--allowed-tools", ",".join(allowed),
    ]


def worker_tool_grants(role: str) -> tuple[list[str], list[str]]:
    """Return (allowed_tools, extra_claude_flags) for a worker role.

    Single source of truth because runners/worker_resume.py rebuilds the same
    argv: when the two lists drift, a resumed DEV silently loses capabilities
    its task depends on and the failure looks like the model being lazy.

    Chrome is gated on the `--chrome` flag, not on MCP config — Claude in
    Chrome is a built-in CLI integration, not an entry in worker.mcp.json.
    Verified 2026-08-10: with `--strict-mcp-config` and no `--chrome`, the
    Chrome tools are absent ("tool not found in available deferred tools");
    adding `--chrome` makes them resolve while strict MCP stays on.
    """
    allowed = list(_BASE_WORKER_TOOLS)
    flags: list[str] = []
    if role == "browser_operator":
        allowed.extend(_CHROME_TOOLS)
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


def skill_visibility_overlay(role: str) -> dict[str, bool] | None:
    """Return the `enabledPlugins` map for role's skills_profile, or None.

    ADR 0022 §2 / playbook Wave 3 Phase 1: `skillOverrides` short-circuits
    to "on" for plugin-sourced skills (`e.source === "plugin"`), so the only
    lever for them is `enabledPlugins`, keyed `<plugin>@<marketplace>`.

    None means "all" (or an unregistered role) -- the CEO's CTO-sees-
    everything decision costs zero code: no key is added to the settings
    dict, so `_write_dev_settings` writes exactly what it always wrote.

    Measured 2026-09-01 on Claude Code 2.1.252: a `.claude/settings.local.json`
    (localSettings) `enabledPlugins: false` entry DOES override an explicit
    `true` for the same plugin in `~/.claude/settings.json` (userSettings),
    even though userSettings outranks localSettings in the documented
    precedence -- so the file `_write_dev_settings` already writes is
    sufficient; no `--settings` flag is needed for Phase 1. See
    docs/WAVE3-SKILL-VISIBILITY.md for the measurement.

    `ecc@ecc` must never appear here: its hooks.json (GateGuard's
    gateguard-fact-force among others) ships inside the plugin bundle, and
    `enabledPlugins: false` disables the whole bundle, hooks included, not
    just its skills -- verified live 2026-09-01 (see the doc). Excluding it
    is enforced by scripts/test_skill_visibility.py, not just this comment.
    """
    try:
        profile = get_role(role).get("skills_profile") or "all"
    except ValueError:
        profile = "all"
    if profile == "all":
        return None
    profile_path = ROOT / "policies" / "skill-visibility" / f"{profile}.json"
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    return data.get("enabledPlugins") or {}


def _write_dev_settings(worktree: str, role: str | None = None) -> None:
    """Drop .claude/settings.local.json into the worktree so claude wires
    the Stop hook that relays DEV replies into cto.log, explicitly disables
    any project-scoped MCP servers inherited from Agents/.mcp.json (see
    _root_mcp_server_names) so DEV spawns never hit the interactive approval
    screen for servers they were never meant to use — DEVs get MCP access
    only via --mcp-config config/worker.mcp.json — and applies role's
    skill-visibility profile (see skill_visibility_overlay).

    role defaults to None (no overlay applied) rather than being required:
    runners/worker_resume.py calls this with the one-arg form and is outside
    this task's declared touches (self_repo_guard, ADR 0020), so a resumed
    worker falls back to pre-task behaviour (all skills visible) until that
    file gets the matching one-line update in a follow-up task. Flagged to
    the CTO -- see docs/WAVE3-SKILL-VISIBILITY.md."""
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
    overlay = skill_visibility_overlay(role) if role else None
    if overlay:
        cfg["enabledPlugins"] = overlay
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

If a skill you followed gave HARD-tagged rules, follow them as written. If it
gave advice (not HARD) and you judged the situation called for something
else, that's fine — just record it in your report as one line per override:
`SKILL-OVERRIDE: <skill> :: <rule> :: <did instead> :: <why>`

Begin.
"""


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: python -m runners.worker_init <role> <task_id>", file=sys.stderr)
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

    # Runner (task-adbc6f43): NULL on the row means "claude" (every
    # pre-migration/local task, unchanged). This launcher only ever execs
    # claude.exe/claude — codex and agy are winbox-only today
    # (windows/spawn-worker.ps1's job), gated at config/hosts.yaml's `mac`
    # entry (`runners: [claude]`) so tools.delegate._validate_runner already
    # refuses a codex/agy task before it reaches this file. This is a second,
    # local check — never trust a runner blind at exec time either.
    runner = (task.get("runner") or "claude").strip().lower()
    if runner != "claude":
        db.update_status(
            task_id, "failed",
            report=f"runner={runner!r} not supported by local Mac spawn "
                    f"(runners/worker_init.py) — winbox-only today",
            actor=role,
        )
        print(f"runner {runner!r} not supported for local spawn", file=sys.stderr)
        sys.exit(5)

    project = get_project(task["project"])
    backend = (project.get("spawn_backend") or "iterm").lower()

    # web_designer on a tmux/Web-UI-bridge project is driven by the
    # claudesign daemon (Web UI chat → bridge → real claude per message),
    # so the pane is just a passive tail of the bridge mirror. Every other
    # role+backend combination instead runs as an autonomous claude TUI
    # exactly like any other DEV — whether that TUI lives directly in the
    # iTerm tab (spawn_backend: iterm) or inside a tmux pane the tab
    # attaches to (spawn_backend: tmux, task-2f04a8ca) makes no difference
    # here — so the CTO's `delegate_task` behaves the same as for
    # `developer`, only with the web_designer role doc + the design source
    # resolved from the project UUID (CEO 2026-06-15). The CEO-driven Web
    # UI flow is a separate path (scripts/spawn-web-designer.sh).
    # ONLY mooniex-claudesign runs the Web-UI daemon that drives this passive
    # viewer. The tmux rollout (task-2f04a8ca, 2026-08-14) moved most projects
    # to spawn_backend=tmux, which made their web_designer wrongly fall into this
    # dead-tail branch (no daemon → 0-byte mirror, nothing runs). Gate it to the
    # claudesign project so a CTO-delegated web_designer runs AUTONOMOUS (a real
    # claude TUI) on every other project, exactly like a developer.
    if role == "web_designer" and backend == "tmux" and project.get("key") == "mooniex-claudesign":
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

    shared_doc = (ROOT / "roles" / "_worker_shared.md").read_text()
    role_doc = shared_doc + "\n\n" + (ROOT / "roles" / f"{role}.md").read_text()
    prompt = _build_prompt(task, project, worktree)
    # web_designer's worktree omits the gitignored .od/, so resolve the
    # design source (project UUID → absolute read-only path + skill) from
    # the task description and append it so the autonomous agent knows which
    # brand/theme to match — the same context the CEO's Web UI flow has.
    if role == "web_designer":
        prompt += db.designer_kickoff_suffix(task.get("description") or "")
    try:
        model = get_role(role).get("model") or "claude-opus-5-5"
    except ValueError:
        # role file exists in roles/ but not registered in policies/agents.yaml
        # fall back to worker-tier default
        model = "claude-opus-5-5"

    env = os.environ.copy()
    # An "update available" prompt is a startup-level interrupt, not a tool
    # permission check, so neither --permission-mode nor --allowed-tools
    # reaches it -- it would block a worker nobody is watching on a keypress
    # nobody is there to press (IRON-RULES §45). Verified 2026-08-14 by
    # grepping the installed binary's strings for the name, not assuming it.
    env["DISABLE_AUTOUPDATER"] = "1"
    env["WORKER_TASK_ID"] = task_id
    env["WORKER_ROLE"] = role
    # Hub checkout root (never the worktree). lib/mailbox.py and lib/db.py
    # read this to resolve state/ paths -- GH #154: a worker's own __file__
    # points at its worktree, which has no state/ of its own, so those
    # modules silently talked to a directory that doesn't exist.
    env["ORG_ROOT"] = str(ROOT)
    if task.get("owner_cto"):
        env["WORKER_CTO_ID"] = task["owner_cto"]
        # owner_role picks which <role>-<id>.winid lock send_to_cto reads so
        # CFO/CMO-spawned reports route to the CXO tab, not a CTO tab. Pre-
        # migration rows have owner_cto but NULL owner_role → default cto.
        env["WORKER_CTO_ROLE"] = task.get("owner_role") or "cto"

    # PID survives os.execvpe — record now so the watchdog can probe the
    # claude TUI's liveness directly instead of guessing from log mtime.
    try:
        db.update_status(task_id, "in_progress", pid=os.getpid(), actor=role)
    except Exception as e:
        print(f"warn: could not record pid for {task_id}: {e}", file=sys.stderr)

    _write_dev_settings(worktree, role)
    _symlink_knowledge(worktree, role)

    task_md = Path(worktree) / "TASK.md"
    task_md.write_text(prompt, encoding="utf-8")

    # Auto Browser (docker + noVNC) was removed 2026-05-19 in favour of
    # Claude in Chrome (native messaging extension). Until 2026-08-10 that
    # left browser work with nowhere to run but a C-level tab; the
    # browser_operator role now carries it, and worker_tool_grants() decides
    # which roles get the Chrome surface + the --chrome flag. Still no
    # per-role MCP config branch — all DEVs share worker.mcp.json.
    allowed, chrome_args = worker_tool_grants(role)
    mcp_config = ROOT / "config" / "worker.mcp.json"

    # DEV model provider override (flag-gated, reversible). When
    # WORKER_MODEL_PROVIDER is set, worker DEVs run on a cheaper Anthropic-
    # compatible endpoint (Z.ai -> GLM-5.2) instead of
    # C-level orchestration is unaffected. Unset -> original behaviour.
    # tasks.model_hint='claude' overrides the quota router for this one task —
    # see lib.config.worker_provider_overrides. Set by the CTO when a cheap miss
    # would be expensive (reviewing/repairing someone else's work, security).
    _ov = worker_provider_overrides(role, task.get("model_hint"))
    effort_args = ["--effort", get_role(role).get("effort") or "high"]
    if _ov:
        model = _ov["model"]
        env.update(_ov["env"])
        if _ov["effort"] is None:
            effort_args = []

    host_name = current_host()
    session_name = worker_session_name(host_name, role, task_id, clean_title(task.get("title")))

    os.chdir(worktree)
    os.execvpe(
        "claude",
        # Prompt goes FIRST, before any flag, and --allowed-tools goes
        # LAST with nothing after it. Both halves are load-bearing:
        # --allowed-tools is variadic, so it consumes every following
        # argv element until the next flag -- a trailing positional
        # prompt gets eaten whole and the worker launches with its brief
        # parsed as ~1200 bogus tool names and no prompt at all.
        # Comma-joining the tool list does NOT fix this on its own
        # (measured 2026-08-15: the swallow still happens, because the
        # flag takes the *next element* regardless of the first one's
        # shape). Do not "fix" it with `-p` either -- that turns claude
        # headless (print-and-exit) and kills the interactive TUI that
        # kickoff pings, ttyd attach and dev_message all depend on.
        # Joined into one element (matches runners/secretary_server.py)
        # and kept LAST in the argv -- see worker_claude_argv.
        worker_claude_argv(
            prompt=prompt,
            session_name=session_name,
            model=model,
            effort_args=effort_args,
            role_doc=role_doc,
            mcp_config=mcp_config,
            chrome_args=chrome_args,
            allowed=allowed,
            host_name=host_name,
        ),
        env,
    )


if __name__ == "__main__":
    main()
