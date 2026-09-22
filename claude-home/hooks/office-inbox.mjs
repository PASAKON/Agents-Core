#!/usr/bin/env node
/**
 * UserPromptSubmit hook — fetches unread messages for this session's
 * agent_id (from the office cache file written by office-pretool.mjs)
 * and injects them into Claude's context via hookSpecificOutput.
 *
 * Targeting layers (server-side `readInbox()` aggregates):
 *   - direct DM            (to_agent_id = me)
 *   - role broadcast       (to_role = my role from webapp_office_agents)
 *   - desk broadcast       (to_desk = any of my held desks)
 *
 * Channels are NOT auto-pulled — agents subscribe via tool call.
 *
 * Side effect: every fetched message is ack'd before injection so the
 * next turn doesn't re-show it. If the inject fails, the hook still
 * exits silently — coordination is best-effort.
 *
 * No-op when:
 *   - Not in a Mooniex session (no office cache file)
 *   - No OFFICE_TOKEN configured
 *   - Network down (silent fail)
 *
 * See org:IRON-RULES.md §17 + org:playbooks/agent-messaging.md
 * (Agents-Wikis, not LLMs — moved there by the ADR-0013 wiki split).
 */

import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";

const CWD = process.cwd();
const CWD_HASH = crypto.createHash("sha256").update(CWD).digest("hex").slice(0, 12);
const CACHE_PATH = path.join(os.homedir(), ".claude", `office-state-${CWD_HASH}.json`);
const CONFIG_PATH = path.join(os.homedir(), ".claude", "office.json");
const CTO_AGENT_ID = "claude-cto-cross-desk";

async function readJson(p) {
  try {
    return JSON.parse(await fs.readFile(p, "utf8"));
  } catch {
    return null;
  }
}

async function fetchJson(url, opts) {
  try {
    const res = await fetch(url, opts);
    let body = null;
    try {
      body = await res.json();
    } catch {
      /* ignore */
    }
    return { ok: res.ok, status: res.status, body };
  } catch {
    return { ok: false, status: 0, body: null };
  }
}

function emit(obj) {
  process.stdout.write(JSON.stringify(obj));
}

function fmtMessage(m) {
  const ts = new Date(m.sent_at).toLocaleString("en-GB", {
    timeZone: "Asia/Bangkok",
    hour12: false,
  });
  const target = m.to_agent_id
    ? `→ you`
    : m.to_role
    ? `→ role:${m.to_role}`
    : m.to_desk
    ? `→ desk:${m.to_desk}`
    : m.channel
    ? `#${m.channel}`
    : "";
  const reply = m.replied_to ? ` (re: ${m.replied_to.slice(0, 8)})` : "";
  return `[${ts}] ${m.from_agent_id} ${target}${reply}\n  ${m.body}`;
}

async function main() {
  // Resolve agent_id: prefer office cache (per-cwd); fall back to CTO id when
  // sitting in /Users/gob/projects/LLMs (CTO cross-desk default per §15).
  let agentId = null;
  const cache = await readJson(CACHE_PATH);
  if (cache?.agent_id) {
    agentId = cache.agent_id;
  } else if (CWD === "/Users/gob/projects/LLMs" || CWD.startsWith("/Users/gob/projects/LLMs/")) {
    agentId = CTO_AGENT_ID;
  } else {
    return; // not in a known Mooniex context
  }

  const config = await readJson(CONFIG_PATH);
  const apiBase =
    config?.api_base ?? process.env.OFFICE_API_BASE ?? "https://www.mooniex.com";
  const token = config?.token ?? process.env.OFFICE_TOKEN;
  if (!token) return;

  const auth = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };

  // Fetch unread inbox
  const r = await fetchJson(
    `${apiBase}/api/office/messages/inbox?for_agent=${encodeURIComponent(agentId)}&limit=20`,
    { headers: auth },
  );
  if (!r.ok || !r.body?.ok) return;
  const messages = r.body.messages ?? [];
  if (messages.length === 0) return;

  // Format for context injection
  const lines = messages.map(fmtMessage);
  const additionalContext =
    `Office Simulator inbox — ${messages.length} unread message(s) ` +
    `for agent_id=${agentId}.\n\n${lines.join("\n\n")}\n\n` +
    `(Auto-injected by ~/.claude/hooks/office-inbox.mjs. To reply, use ` +
    `mcp__mooniex_coord__send_message tool or curl POST ` +
    `${apiBase}/api/office/messages/send with body { from_agent_id: "${agentId}", ` +
    `replied_to: "<message id>", body: "..." }. Messages above are now marked read.)`;

  // Ack each message (best-effort, in parallel)
  await Promise.all(
    messages.map((m) =>
      fetchJson(`${apiBase}/api/office/messages/${m.id}/ack`, {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ agent_id: agentId }),
      }),
    ),
  );

  emit({
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext,
    },
  });
}

main().catch(() => {
  /* swallow — never block the turn */
});
