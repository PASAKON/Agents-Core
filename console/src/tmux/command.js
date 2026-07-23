import { config } from '../config.js';

// Every agent session runs the SAME launcher the CEO gets on a real Mac
// iTerm CTO tab (scripts/spawn-cto.sh -> scripts/cto-claude.sh), i.e. the
// actual `claude` CLI with the CTO system prompt + MCP tools appended — not
// a custom hand-rolled REPL. This originally ran `python -m runners.cto_chat`
// (a bespoke rich/Live REPL via the Agent SDK), which is why the console felt
// nothing like real iTerm2: no native "thinking" indicator, and its own
// stdout logger unintentionally duplicated every line onto the same stream
// as rich's Live render (lib/logger.py's per-name logger singleton — cto.py
// imports first with a stdout handler attached, so cto_chat.py's later
// stdout=False request was silently ignored) — that's what produced the
// garbled/duplicated text. Launching the real CLI sidesteps all of that —
// role-specific launchers for cmo/cfo/cxo don't exist yet, so every role
// still maps to the CTO launcher for now.
const ROLE_SCRIPTS = {
  cto: 'scripts/cto-claude.sh',
};

export function roleCommand(role) {
  const script = ROLE_SCRIPTS[role] || ROLE_SCRIPTS.cto;
  return `bash ${config.orgRoot}/${script}`;
}
