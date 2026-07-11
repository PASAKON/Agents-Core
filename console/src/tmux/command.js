import { config } from '../config.js';

// TASK.md P1 spec: every agent session runs the existing CTO chat REPL
// (`python -m runners.cto_chat`), regardless of which role was picked at
// "Create New Session" — role-specific REPLs for cmo/cfo/cxo don't exist
// yet (only runners/cto_chat.py is wired up today). Role still drives the
// tmux session name / badge / routing; only the runtime command is shared
// for now. Extend this map when e.g. runners/cmo_chat.py ships.
const ROLE_MODULES = {
  cto: 'runners.cto_chat',
};

export function roleCommand(role) {
  const mod = ROLE_MODULES[role] || ROLE_MODULES.cto;
  return `${config.pythonBin} -m ${mod}`;
}
