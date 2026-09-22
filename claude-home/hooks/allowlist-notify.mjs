#!/usr/bin/env node
// UserPromptSubmit: read candidates.json. If any unnotified pattern with count >= THRESHOLD,
// inject context telling Claude to ask user about adding to allowlist.
import { readFileSync, writeFileSync, existsSync } from "fs";
import { homedir } from "os";
import { join } from "path";

const STATE = join(homedir(), ".claude", ".allowlist-candidates.json");
const THRESHOLD = 3;

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
  emit(
    `ALLOWLIST CANDIDATES detected (repeated Bash patterns not in allowlist):\n${lines}\n\n` +
    `IMPORTANT: Ask the user once, listing these patterns, whether to add to \`~/.claude/settings.json\` permissions.allow. ` +
    `If user agrees, append via jq and mark each entry as notified=true in ${STATE}. ` +
    `If user declines, just mark notified=true without adding. Either way, update the state file so this notice does not repeat.`
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
