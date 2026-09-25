#!/usr/bin/env node
/**
 * mooniex-coord — minimal MCP server (stdio) that exposes the Office
 * Simulator messaging surface as Claude Code tools. Each ClaudeCode
 * session spawns its own copy; state is shared via the Supabase
 * `webapp_office_messages` table. No central process required.
 *
 * Tools:
 *   send_message      send a DM / role / desk / channel broadcast
 *   read_inbox        pull unread for current agent
 *   read_thread       fetch all messages in a thread
 *   list_active_agents  who's at which desk right now
 *
 * Config file: ~/.claude/office.json — { api_base, token }.
 * Cwd-cache:   ~/.claude/office-state-<cwdHash>.json — { agent_id, desk_id, ... }
 *
 * Protocol: MCP 2024-11-05, JSON-RPC 2.0 over stdio. Implemented inline
 * (no @modelcontextprotocol/sdk dep) to keep this hot-pluggable.
 *
 * See LLMs/IRON-RULES.md §17 + playbooks/agent-messaging.md.
 */

import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import readline from "node:readline";

const CWD = process.cwd();
const CWD_HASH = crypto.createHash("sha256").update(CWD).digest("hex").slice(0, 12);
const CACHE_PATH = path.join(os.homedir(), ".claude", `office-state-${CWD_HASH}.json`);
const CONFIG_PATH = path.join(os.homedir(), ".claude", "office.json");
const DEVICE_PATH = path.join(os.homedir(), ".claude", "device.json");
const CTO_AGENT_ID = "claude-cto-cross-desk";

async function loadDevice() {
  return readJson(DEVICE_PATH);
}

async function readJson(p) {
  try {
    return JSON.parse(await fs.readFile(p, "utf8"));
  } catch {
    return null;
  }
}

async function loadConfig() {
  const config = await readJson(CONFIG_PATH);
  return {
    apiBase:
      config?.api_base ?? process.env.OFFICE_API_BASE ?? "https://www.mooniex.com",
    token: config?.token ?? process.env.OFFICE_TOKEN ?? null,
  };
}

async function resolveSelfAgentId() {
  const cache = await readJson(CACHE_PATH);
  if (cache?.agent_id) return cache.agent_id;
  if (CWD === "/Users/gob/MoonieXHQ/Agents/Wikis" || CWD.startsWith("/Users/gob/MoonieXHQ/Agents/Wikis/")) {
    return CTO_AGENT_ID;
  }
  return null;
}

async function api(method, p, body) {
  const { apiBase, token } = await loadConfig();
  if (!token) {
    return { ok: false, status: 0, body: { error: "OFFICE_TOKEN not configured" } };
  }
  const headers = { Authorization: `Bearer ${token}` };
  const opts = { method, headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  try {
    const res = await fetch(`${apiBase}${p}`, opts);
    let parsed = null;
    try {
      parsed = await res.json();
    } catch {
      /* ignore */
    }
    return { ok: res.ok, status: res.status, body: parsed };
  } catch (err) {
    return { ok: false, status: 0, body: { error: err?.message ?? "network_fail" } };
  }
}

// ─────────────────────────────────────────────────────────────────────
// Tool definitions
// ─────────────────────────────────────────────────────────────────────

const TOOLS = [
  {
    name: "send_message",
    description:
      "Send a message to another agent / role / desk / channel. Exactly one of to_agent_id, to_role, to_desk, channel must be set. Body 1-4000 chars. Returns the new message id and thread_root.",
    inputSchema: {
      type: "object",
      properties: {
        to_agent_id: { type: "string", description: "Direct DM target (e.g. 'claude-abc123')" },
        to_role: { type: "string", description: "Role broadcast (e.g. 'Senior Developer')" },
        to_desk: { type: "string", description: "Desk broadcast (e.g. 'Desk-A')" },
        channel: { type: "string", description: "Pub/sub channel (e.g. '#deploys')" },
        body: { type: "string", description: "Message body" },
        replied_to: { type: "string", description: "Optional parent message id (uuid) to thread into" },
        metadata: { type: "object", description: "Optional structured metadata" },
      },
      required: ["body"],
    },
  },
  {
    name: "read_inbox",
    description:
      "Read unread messages for the current agent (direct + role + desk broadcasts). Returns each message's id, from, body, sent_at. Reading via this tool does NOT auto-ack — pass auto_ack: true to mark read in the same call.",
    inputSchema: {
      type: "object",
      properties: {
        since: { type: "string", description: "Optional ISO timestamp lower bound (exclusive)" },
        limit: { type: "number", description: "Max rows (default 50, max 200)" },
        auto_ack: { type: "boolean", description: "Mark fetched messages as read (default false)" },
      },
    },
  },
  {
    name: "read_thread",
    description: "Fetch all messages in a thread by root_id, ordered oldest first.",
    inputSchema: {
      type: "object",
      properties: {
        root_id: { type: "string", description: "Thread root message id (uuid)" },
      },
      required: ["root_id"],
    },
  },
  {
    name: "list_active_agents",
    description:
      "List currently-claimed desks + occupants + role. Use to discover who to DM. Returns desks[], active map (desk_id → claim or null), and agents map (agent_id → role row).",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "directory",
    description:
      "List known roles + devices online via /api/office/directory. Use to discover who/where to address (preferred over list_active_agents for cross-device routing). Returns rows with role, messaging_uuid, device_id, last_seen.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "register_device",
    description:
      "Heartbeat this device into the office directory so peers can address it via to_device. Reads ~/.claude/device.json for {device_id, device_label, host_kind, os, hostname}. No-op if endpoint not deployed.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "claim_message",
    description:
      "Atomically claim a message for this device before processing. Prevents double-handling when multiple devices share a to_role inbox. Returns {claimed: bool, by: device_id}. Use BEFORE sending a reply.",
    inputSchema: {
      type: "object",
      properties: {
        msg_id: { type: "string", description: "Message uuid to claim" },
        device_id: { type: "string", description: "Override device_id (defaults to ~/.claude/device.json)" },
      },
      required: ["msg_id"],
    },
  },
];

// ─────────────────────────────────────────────────────────────────────
// Tool implementations
// ─────────────────────────────────────────────────────────────────────

async function tool_send_message(args) {
  const targets = [
    args.to_agent_id ? { kind: "agent", v: args.to_agent_id } : null,
    args.to_role ? { kind: "role", v: args.to_role } : null,
    args.to_desk ? { kind: "desk", v: args.to_desk } : null,
    args.channel ? { kind: "channel", v: args.channel } : null,
  ].filter(Boolean);
  if (targets.length !== 1) {
    return text("error: exactly one of to_agent_id | to_role | to_desk | channel required");
  }
  if (!args.body || typeof args.body !== "string") {
    return text("error: body required");
  }
  const from = await resolveSelfAgentId();
  if (!from) {
    return text(
      "error: cannot resolve sender agent_id (no office cache + cwd is not /Users/gob/MoonieXHQ/Agents/Wikis)",
    );
  }
  const payload = {
    from_agent_id: from,
    body: args.body,
    replied_to: args.replied_to,
    metadata: args.metadata,
  };
  if (args.to_agent_id) payload.to_agent_id = args.to_agent_id;
  if (args.to_role) payload.to_role = args.to_role;
  if (args.to_desk) payload.to_desk = args.to_desk;
  if (args.channel) payload.channel = args.channel;

  const r = await api("POST", "/api/office/messages/send", payload);
  if (!r.ok) return text(`error: send failed (${r.status}) ${JSON.stringify(r.body)}`);
  return text(
    `ok: sent message ${r.body?.id} (thread ${r.body?.thread_root}) ` +
      `from ${from} to ${targets[0].kind}=${targets[0].v}`,
  );
}

async function tool_read_inbox(args = {}) {
  const me = await resolveSelfAgentId();
  if (!me) return text("error: cannot resolve self agent_id");
  const params = new URLSearchParams({ for_agent: me });
  if (args.since) params.set("since", args.since);
  if (args.limit) params.set("limit", String(args.limit));
  const r = await api("GET", `/api/office/messages/inbox?${params.toString()}`);
  if (!r.ok) return text(`error: inbox read failed (${r.status})`);
  const messages = r.body?.messages ?? [];
  if (args.auto_ack && messages.length > 0) {
    await Promise.all(
      messages.map((m) =>
        api("POST", `/api/office/messages/${m.id}/ack`, { agent_id: me }),
      ),
    );
  }
  return text(JSON.stringify({ count: messages.length, messages, fetched_at: r.body?.fetched_at }, null, 2));
}

async function tool_read_thread(args) {
  if (!args.root_id) return text("error: root_id required");
  const r = await api("GET", `/api/office/messages/thread/${encodeURIComponent(args.root_id)}`);
  if (!r.ok) return text(`error: thread read failed (${r.status})`);
  return text(JSON.stringify(r.body, null, 2));
}

async function tool_list_active_agents() {
  const r = await api("GET", "/api/office/state");
  if (!r.ok) return text(`error: state read failed (${r.status})`);
  return text(JSON.stringify(r.body, null, 2));
}

async function tool_directory() {
  const r = await api("GET", "/api/office/directory");
  if (r.status === 404) {
    return text(
      "warn: /api/office/directory not deployed yet — falling back to list_active_agents.\n" +
        "Phase 0 dependency: DevOps must ship endpoint. Tracking thread c12c1d46-bf59-44e7-9c19-ea355bb8c3af.",
    );
  }
  if (!r.ok) return text(`error: directory read failed (${r.status})`);
  return text(JSON.stringify(r.body, null, 2));
}

async function tool_register_device() {
  const device = await loadDevice();
  if (!device) {
    return text(
      "error: ~/.claude/device.json missing — run setup or create file per plan claudecode-desktop-fuzzy-bee.md",
    );
  }
  const r = await api("POST", "/api/office/devices/heartbeat", {
    device_id: device.device_id,
    device_label: device.device_label,
    host_kind: device.host_kind,
    os: device.os,
    hostname: device.hostname,
  });
  if (r.status === 404) {
    return text(
      `ok (stub): endpoint not deployed yet. Local device.json valid: device_id=${device.device_id}`,
    );
  }
  if (!r.ok) return text(`error: heartbeat failed (${r.status}) ${JSON.stringify(r.body)}`);
  return text(`ok: registered device ${device.device_id}`);
}

async function tool_claim_message(args) {
  if (!args.msg_id) return text("error: msg_id required");
  const device = await loadDevice();
  const deviceId = args.device_id ?? device?.device_id;
  if (!deviceId) return text("error: device_id missing (no override + no ~/.claude/device.json)");
  const r = await api("POST", "/api/office/messages/claim", {
    msg_id: args.msg_id,
    device_id: deviceId,
  });
  if (r.status === 404) {
    return text(
      `ok (stub): /api/office/messages/claim not deployed. Optimistic claim by ${deviceId}. ` +
        "Real atomicity will activate when Desk-D ships endpoint.",
    );
  }
  if (!r.ok) return text(`error: claim failed (${r.status}) ${JSON.stringify(r.body)}`);
  return text(JSON.stringify(r.body, null, 2));
}

function text(s) {
  return { content: [{ type: "text", text: s }] };
}

// ─────────────────────────────────────────────────────────────────────
// JSON-RPC 2.0 stdio loop
// ─────────────────────────────────────────────────────────────────────

const RPC = {
  initialize: () => ({
    protocolVersion: "2024-11-05",
    capabilities: { tools: {} },
    serverInfo: { name: "mooniex-coord", version: "0.1.0" },
  }),
  "tools/list": () => ({ tools: TOOLS }),
  "tools/call": async (params) => {
    const { name, arguments: args = {} } = params ?? {};
    switch (name) {
      case "send_message":
        return tool_send_message(args);
      case "read_inbox":
        return tool_read_inbox(args);
      case "read_thread":
        return tool_read_thread(args);
      case "list_active_agents":
        return tool_list_active_agents();
      case "directory":
        return tool_directory();
      case "register_device":
        return tool_register_device();
      case "claim_message":
        return tool_claim_message(args);
      default:
        throw new Error(`unknown tool: ${name}`);
    }
  },
};

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + "\n");
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on("line", async (line) => {
  if (!line.trim()) return;
  let req;
  try {
    req = JSON.parse(line);
  } catch {
    return;
  }
  const handler = RPC[req.method];
  // Respond only to requests (have id); notifications are silent.
  if (req.id === undefined || req.id === null) return;
  if (!handler) {
    send({
      jsonrpc: "2.0",
      id: req.id,
      error: { code: -32601, message: `method not found: ${req.method}` },
    });
    return;
  }
  try {
    const result = await handler(req.params);
    send({ jsonrpc: "2.0", id: req.id, result });
  } catch (err) {
    send({
      jsonrpc: "2.0",
      id: req.id,
      error: { code: -32603, message: err?.message ?? "internal" },
    });
  }
});

rl.on("close", () => process.exit(0));
