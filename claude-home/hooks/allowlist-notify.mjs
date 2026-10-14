#!/usr/bin/env node
// UserPromptSubmit: read candidates.json. If any unnotified pattern with count >= THRESHOLD,
// inject context telling Claude to ask user about adding to allowlist.
import { readFileSync, writeFileSync, existsSync } from "fs";
import { homedir } from "os";
import { join } from "path";

const STATE = join(homedir(), ".claude", ".allowlist-candidates.json");
// CEO 2026-10-07: "อันไหนใช้เกิน 3 ครั้งเพิ่มเองได้เลย ไม่ต้องถาม" — more than 3 uses.
const THRESHOLD = 4;

function emit(text) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: text
    }
  }));
}

try {
  if (!existsSync(STATE)) process.exit(0);
  const state = JSON.parse(readFileSync(STATE, "utf8"));
  const ready = Object.entries(state)
    .filter(([_, v]) => v.count >= THRESHOLD && !v.notified)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 10);
  if (!ready.length) process.exit(0);

  const lines = ready.map(([p, v]) => `  - \`${p}\` (used ${v.count}x)`).join("\n");
  // Rule (CEO 2026-10-07): only a C-level session adds; safe + lasting patterns without asking;
  // risky ones asked as before, each with what the command is for and what the risk is.
  emit(
    `ALLOWLIST CANDIDATES detected (Bash patterns used more than 3 times, not in the allowlist):\n${lines}\n\n` +
    `RULE (CEO 2026-10-07): only a C-level session (CTO/CMO/CGO/CFO/COO) edits permissions.allow; a worker ` +
    `leaves this notice alone. For each pattern:\n` +
    `  - SAFE and lasting (a real command or project script that only reads, or writes inside a repo or ` +
    `scratchpad; no delete, no push/deploy, no other machine, no secret, no money, no install; and it will ` +
    `keep being used, not a one-off folder or task id): add it yourself, no question — append via jq to ` +
    `\`~/.claude/settings.json\` permissions.allow, then say in one line which you added.\n` +
    `  - RISKY (anything outside SAFE): ask the CEO first, once, and for each pattern say what the command ` +
    `is for and what the risk is.\n` +
    `  - NOT A COMMAND (a folder, file or task name that cannot run): skip it.\n` +
    `Mark every listed entry notified=true in ${STATE} whatever the outcome, so this notice does not repeat.`
  );

  // Auto-age: any candidate older than 7 days unnotified → mark notified to prevent nag.
  const cutoff = Date.now() - 7 * 24 * 3600 * 1000;
  let changed = false;
  for (const [p, v] of Object.entries(state)) {
    if (!v.notified && v.first < cutoff) {
      v.notified = true;
      changed = true;
    }
  }
  if (changed) writeFileSync(STATE, JSON.stringify(state, null, 2));
} catch {
  process.exit(0);
}
