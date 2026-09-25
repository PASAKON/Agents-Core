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
 *   ask_run           Run Inbox: put one command on the CEO's phone for a tap
 *   ask_run_wait      Run Inbox: wait for an ask to end, return its record
 *
 * Config file: ~/.claude/office.json — { api_base, token }.
 * Cwd-cache:   ~/.claude/office-state-<cwdHash>.json — { agent_id, desk_id, ... }
 * Run Inbox:   RUN_INBOX_URL (default https://terminal.mooniex.com) + token from
 *              RUN_INBOX_TOKEN, else ~/.config/mooniex/run-inbox.token (0600).
 *              Same contract and refusals as tools/ask_run.py
 *              (docs/design/run-inbox/DESIGN.md §6, §13).
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
  {
    name: "ask_run",
    description:
      "Ask the CEO to run one command on a host via the Run Inbox (a card on his phone). The CEO's tap is the only authority; the tool never approves. Workers send script='repo@sha:path' at a pushed commit; command is for C-level roles only. Returns {id, url, risk, expires_at} at once.",
    inputSchema: {
      type: "object",
      properties: {
        host: { type: "string", description: "Target host id: contabo | mac | winbox" },
        script: {
          type: "string",
          description: "repo@sha:path at a pushed commit, e.g. Agents-Core@9df4e185:scripts/contabo_blueprint.sh",
        },
        args: { type: "array", items: { type: "string" }, description: "Arguments for script" },
        command: { type: "string", description: "Freeform command line, sent byte-for-byte (C-level roles only)" },
        why: { type: "string", description: "One line for the card: why this has to run" },
        expected: { type: "string", description: "One line for the card: what a good result looks like" },
        risk: { type: "string", enum: ["green", "amber", "red"], description: "Your claim (default amber); the hub can only raise it" },
        timeout_s: { type: "number", description: "Run timeout once approved (default 300)" },
        expects_input: { type: "boolean", description: "The process will wait on stdin (typed on the phone)" },
        shell: { type: "string", enum: ["bash", "powershell", "cmd"], description: "Override the host's default shell" },
        cwd: { type: "string", description: "Working directory on the host" },
        env_keys: { type: "array", items: { type: "string" }, description: "Env var NAMES the executor may pass through" },
        session: { type: "string", description: "Your mailbox name <role>-<id> (default: from env)" },
        role: { type: "string", description: "Your role (default: CXO_ROLE / WORKER_ROLE)" },
        task: { type: "string", description: "Task id (default: WORKER_TASK_ID)" },
        dry_run: { type: "boolean", description: "Return the JSON body without sending it" },
      },
      required: ["host", "why"],
    },
  },
  {
    name: "ask_run_wait",
    description:
      "Wait for a Run Inbox ask to end (polls every 5 s) and return its record. The CEO's tap is the only authority; the tool never approves.",
    inputSchema: {
      type: "object",
      properties: {
        id: { type: "string", description: "RUN-YYYYMMDD-HHMM-xxxx (or its /run#... URL)" },
        max_wait_s: { type: "number", description: "Give up after this long and return terminal:false (default 600, max 3600)" },
        interval_s: { type: "number", description: "Poll interval (default 5, min 1)" },
        tail_lines: { type: "number", description: "Output tail lines to return (default 40, 0 = all)" },
      },
      required: ["id"],
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

// ─────────────────────────────────────────────────────────────────────
// Run Inbox: ask_run / ask_run_wait (docs/design/run-inbox/DESIGN.md §6, §13).
// Same API contract and the same local refusals as tools/ask_run.py; keep the
// two in step (tests/test_ask_run.py runs one table of cases through both).
// The CEO's tap on the phone is the only authority: nothing here approves, and
// the org token cannot approve (the hub refuses it). The token is never put in
// a result or a message, and a redirect is refused so it only goes to the hub.
// ─────────────────────────────────────────────────────────────────────

const RUN_DEFAULT_URL = "https://terminal.mooniex.com";
const RUN_TOKEN_FILE = path.join(".config", "mooniex", "run-inbox.token");
const RUN_C_LEVEL = ["cto", "cfo", "cxo", "ceo"]; // CEO decision 1 (DESIGN §11); the hub checks the same list
const RUN_RISKS = ["green", "amber", "red"];
const RUN_SHELLS = ["bash", "powershell", "cmd"];
const RUN_TERMINAL = ["done", "failed", "denied", "expired", "cancelled"];
const RUN_POLL_S = 5;
const RUN_MIN_POLL_S = 1;
const RUN_WAIT_DEFAULT_S = 600;
const RUN_WAIT_MAX_S = 3600;
const RUN_HTTP_TIMEOUT_MS = 20000;
const RUN_MAX_POLL_FAILURES = 12;
const RUN_TAIL_LINES = 40;

const RUN_HOST_RE = /^[a-z0-9][a-z0-9-]{0,31}$/;
const RUN_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const RUN_ENV_NAME_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const RUN_REPO_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const RUN_SHA_RE = /^[0-9a-f]{7,40}$/;
const RUN_ID_RE = /^RUN-[A-Za-z0-9][A-Za-z0-9-]{3,63}$/;

// Secret shapes: the key family and the private-key marker of
// scripts/contabo_blueprint.sh step 10, identical to tools/ask_run.py's
// SECRET_KEY_WORDS / PRIVATE_KEY_MARKER, plus the same well-known token shapes.
const RUN_SECRET_KEY_WORDS =
  "(?:token|secret|passw(?:or)?d|api[_-]?key|private[_-]?key|client[_-]?secret|access[_-]?key)";
const RUN_KEY = "[A-Za-z0-9_.\\-]*" + RUN_SECRET_KEY_WORDS + "[A-Za-z0-9_.\\-]*";
const RUN_ASSIGN_LINE = new RegExp("^\\s*[-\"']?(" + RUN_KEY + ")[\"']?\\s*[:=]\\s*(\\S.*)$", "i");
const RUN_WORD_SPLIT = /[\s[\]()<>,;&|?`]+/; // not {}: it would cut ${NAME} in half
const RUN_ASSIGN_WORD = new RegExp("^[-\"']*(" + RUN_KEY + ")[\"']?[:=](.+)$", "i");
const RUN_QUOTED_KEY = "[\"'](" + RUN_KEY + ")[\"']\\s*:\\s*(\"[^\"]*\"|'[^']*'|[^\\s,}\\]]+)";
const RUN_KEYMAT = /BEGIN [A-Z ]*PRIVATE KEY/;
const RUN_ENV_REF =
  /^["']?(?:\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[A-Za-z_][A-Za-z0-9_]*%|\$env:[A-Za-z_][A-Za-z0-9_]*)["']?[,;]?$/;
const RUN_EMPTY_VALUES = new Set(["", "''", '""', "<redacted>", "'<redacted>'", '"<redacted>"']);
// Python's str.splitlines() boundaries, so both sides see the same lines.
const RUN_LINE_SPLIT = /\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]/;
const RUN_TOKEN_SHAPES = [
  ["a GitHub token", /\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})/],
  ["an sk-... API key", /\bsk-(?:ant-|or-v1-|proj-)?[A-Za-z0-9_-]{30,}/],
  ["a Slack token", /\bxox[abposr]-[A-Za-z0-9-]{10,}/],
  ["an AWS access key id", /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/],
  ["a Google API key", /\bAIza[0-9A-Za-z_-]{35}/],
  ["a GitLab token", /\bglpat-[A-Za-z0-9_-]{20,}/],
  ["a JWT", /\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/],
  ["a Bearer credential", /\bBearer\s+[A-Za-z0-9._~+\/-]{16,}=*/i],
];

const RUN_HINTS = {
  secret_shaped_value: "remove the value; reference an env var name or an Infisical path",
  freeform_needs_c_level: "workers ask with script repo@sha:path at a pushed commit",
  peer_exec_not_yet: "that host has no executor yet (P2); only the hub's own host runs cards today",
  401: "the hub did not accept the org token (RUN_INBOX_TOKEN or ~/.config/mooniex/run-inbox.token)",
  403: "the org token may not do that (it can create, read its own asks and cancel its own pending ask)",
  404: "no such ask, or not yours (the org token only sees its own asks)",
  409: "not possible in the ask's current state (only a pending ask can be cancelled)",
};

function runFail(msg) {
  return { content: [{ type: "text", text: `error: ${msg}` }], isError: true };
}

// Only the first word of what follows key= / key: counts (a shell assignment
// ends at whitespace): in GH_TOKEN="$GH_TOKEN" ./deploy.sh the value is a reference.
function runLiteral(val) {
  const first = String(val).trim().split(/\s+/)[0] || "";
  return !RUN_EMPTY_VALUES.has(first) && !RUN_ENV_REF.test(first);
}

function* runStrings(obj, where = "") {
  if (typeof obj === "string") {
    yield [where || "value", obj];
  } else if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) yield* runStrings(obj[i], `${where}[${i}]`);
  } else if (obj && typeof obj === "object") {
    for (const [k, v] of Object.entries(obj)) yield* runStrings(v, where ? `${where}.${k}` : k);
  }
}

// `field: what` for every secret-shaped value, the key NAME only, never the value.
function runSecretShapes(payload) {
  const hits = [];
  for (const [field, text] of runStrings(payload)) {
    if (RUN_KEYMAT.test(text)) {
      hits.push(`${field}: private key material`);
      continue;
    }
    for (const line of text.split(RUN_LINE_SPLIT)) {
      const m = RUN_ASSIGN_LINE.exec(line);
      if (m && runLiteral(m[2])) hits.push(`${field}: ${m[1]}=<value>`);
      for (const q of line.matchAll(new RegExp(RUN_QUOTED_KEY, "gi"))) {
        if (runLiteral(q[2])) hits.push(`${field}: ${q[1]}=<value>`);
      }
      for (const word of line.split(RUN_WORD_SPLIT)) {
        const w = RUN_ASSIGN_WORD.exec(word);
        if (w && runLiteral(w[2])) hits.push(`${field}: ${w[1]}=<value>`);
      }
    }
    for (const [label, rx] of RUN_TOKEN_SHAPES) {
      if (rx.test(text)) hits.push(`${field}: looks like ${label}`);
    }
  }
  return [...new Set(hits)];
}

// (role, session id) of the mailbox this process drains: scripts/hook-inbox.py
// `_current_box`, plus tools/agent_transport.py's bare CTO_SESSION_ID fallback.
function runEnvBox(env) {
  if (env.CXO_ROLE) return [env.CXO_ROLE, env.CXO_SESSION_ID || env.CTO_SESSION_ID || null];
  if (env.WORKER_TASK_ID) return [env.WORKER_ROLE || "dev", env.WORKER_TASK_ID];
  if (env.CTO_SESSION_ID) return ["cto", env.CTO_SESSION_ID];
  return [null, null];
}

// requester.session is the mailbox box name <role>-<id>: the hub drops the
// result letter into state/inbox/<requester.session>/.
function runRequester(args, env = process.env) {
  const [envRole, envSid] = runEnvBox(env);
  const role = String(args.role || envRole || "").trim().toLowerCase();
  if (!role) {
    throw new Error("cannot tell this session's role: pass role (cto/cfo/cxo/ceo for a C-level session, dev for a worker)");
  }
  const worker = env.WORKER_TASK_ID;
  if (worker && !env.CXO_ROLE && RUN_C_LEVEL.includes(role)) {
    throw new Error(`this process is worker ${worker} (WORKER_TASK_ID is set); a worker cannot claim role '${role}'`);
  }
  let session = String(args.session || "").trim();
  if (!session) {
    const sid = String(env.ORG_SESSION_ID || envSid || "").trim();
    const boxRole = envRole || role;
    if (sid) session = sid.startsWith(`${boxRole}-`) ? sid : `${boxRole}-${sid}`;
  }
  if (!session) {
    throw new Error("cannot tell this session's mailbox: pass session as <role>-<id> (e.g. cto-6ebacd0e) so the result letter reaches you");
  }
  if (!RUN_NAME_RE.test(session)) throw new Error(`session must be a mailbox name like cto-6ebacd0e (got '${session}')`);
  const requester = { session, role };
  const task = String(args.task || env.WORKER_TASK_ID || "").trim();
  if (task) {
    if (!RUN_NAME_RE.test(task)) throw new Error(`task must be a task id like task-8669cf28 (got '${task}')`);
    requester.task = task;
  }
  return requester;
}

function runParseScript(spec) {
  const usage = "script takes repo@sha:path at a pushed commit, e.g. Agents-Core@9df4e185:scripts/contabo_blueprint.sh";
  const s = String(spec).trim();
  const at = s.indexOf("@");
  const rest = at >= 0 ? s.slice(at + 1) : "";
  const colon = rest.indexOf(":");
  const repo = at >= 0 ? s.slice(0, at) : s;
  const sha = (colon >= 0 ? rest.slice(0, colon) : rest).toLowerCase();
  const p = colon >= 0 ? rest.slice(colon + 1) : "";
  if (at < 0 || colon < 0 || !RUN_REPO_RE.test(repo) || !RUN_SHA_RE.test(sha) || !p) {
    throw new Error(`${usage} (got '${spec}')`);
  }
  if (/^[\/\\]/.test(p) || /^[A-Za-z]:/.test(p) || p.includes("\\")) {
    throw new Error(`script path must be relative to the repo root, with / separators (got '${p}')`);
  }
  if (p.split("/").includes("..")) throw new Error(`script path must stay inside the repo (got '${p}')`);
  return { repo, sha, path: p };
}

function runOneLine(name, value) {
  const v = String(value ?? "").trim();
  if (!v) throw new Error(`${name} is empty`);
  if (/[\r\n]/.test(v)) throw new Error(`${name} is one line (it is shown on the card)`);
  return v;
}

// The POST /api/run/asks body, in the contract's field order (same as tools/ask_run.py).
function runBuildPayload(args, env = process.env) {
  const host = String(args.host ?? "").trim().toLowerCase();
  if (!RUN_HOST_RE.test(host)) throw new Error(`host must be a host id like contabo / mac / winbox (got '${args.host ?? ""}')`);
  const hasScript = typeof args.script === "string" && args.script !== "";
  const hasCommand = typeof args.command === "string" && args.command !== "";
  if (hasScript === hasCommand) throw new Error("give exactly one of script (repo@sha:path) or command");
  const payload = { host };
  if (hasScript) {
    const { repo, sha, path: p } = runParseScript(args.script);
    const sargs = args.args ?? [];
    if (!Array.isArray(sargs) || sargs.some((a) => typeof a !== "string")) throw new Error("args must be an array of strings");
    payload.kind = "script";
    payload.script = { repo, sha, path: p, args: [...sargs] };
  } else {
    if (Array.isArray(args.args) && args.args.length) {
      throw new Error("args go with script; with command put the whole line in command");
    }
    if (!args.command.trim()) throw new Error("command is empty");
    payload.kind = "command";
    payload.command = args.command; // byte-for-byte: what the CEO reads is what runs
  }
  if (args.shell) {
    if (!RUN_SHELLS.includes(args.shell)) throw new Error(`shell must be one of ${RUN_SHELLS.join("/")}`);
    payload.shell = args.shell;
  }
  if (args.cwd) payload.cwd = String(args.cwd);
  if (Array.isArray(args.env_keys) && args.env_keys.length) {
    const bad = args.env_keys.filter((k) => typeof k !== "string" || !RUN_ENV_NAME_RE.test(k));
    if (bad.length) throw new Error(`env_keys take variable NAMES, never NAME=value (got '${bad[0]}')`);
    payload.env_keys = [...new Set(args.env_keys)];
  }
  payload.why = runOneLine("why", args.why);
  if (args.expected !== undefined && args.expected !== null) payload.expected = runOneLine("expected", args.expected);
  const risk = args.risk ?? "amber";
  if (!RUN_RISKS.includes(risk)) throw new Error(`risk must be one of ${RUN_RISKS.join("/")}`);
  const timeout = args.timeout_s ?? 300;
  if (!Number.isInteger(timeout) || timeout <= 0) throw new Error("timeout_s must be a positive whole number of seconds");
  payload.risk = risk;
  payload.timeout_s = timeout;
  payload.expects_input = Boolean(args.expects_input);
  payload.requester = runRequester(args, env);
  return payload;
}

function runRoleGate(payload) {
  if (payload.kind === "command" && !RUN_C_LEVEL.includes(payload.requester.role)) {
    return (
      `freeform_needs_c_level: command is for C-level sessions (${RUN_C_LEVEL.join("/")}); ` +
      `this requester is role '${payload.requester.role}'. Commit the script, push it, and ask with ` +
      "script repo@sha:path (DESIGN §6, CEO decision 1)."
    );
  }
  return null;
}

function runBase() {
  const url = (process.env.RUN_INBOX_URL || "").trim() || RUN_DEFAULT_URL;
  let u = null;
  try {
    u = new URL(url);
  } catch {
    /* handled below */
  }
  if (!u || (u.protocol !== "http:" && u.protocol !== "https:")) {
    throw new Error(`RUN_INBOX_URL must be an http(s) URL (got '${url}')`);
  }
  return url.replace(/\/+$/, "");
}

async function runToken() {
  const fromEnv = (process.env.RUN_INBOX_TOKEN || "").trim();
  if (fromEnv) return { token: fromEnv };
  const p = path.join(os.homedir(), RUN_TOKEN_FILE);
  let st;
  try {
    st = await fs.stat(p);
  } catch (e) {
    if (e?.code === "ENOENT") return { error: `no token: set RUN_INBOX_TOKEN or create ${p} (mode 0600)` };
    return { error: `cannot read ${p}: ${e?.code ?? e?.message}` };
  }
  if (process.platform !== "win32" && st.mode & 0o077) {
    const mode = (st.mode & 0o777).toString(8).padStart(4, "0");
    return { error: `${p} is readable by other users (mode ${mode}); run: chmod 600 ${p}` };
  }
  let t = "";
  try {
    t = (await fs.readFile(p, "utf8")).trim();
  } catch (e) {
    return { error: `cannot read ${p}: ${e?.code ?? e?.message}` };
  }
  if (!t) return { error: `${p} is empty` };
  return { token: t };
}

// -> {ok, status, body} from the hub, or {ok:false, error, transient} for a local
// failure (no token, unreachable, a refused redirect, a non-JSON answer).
async function runApi(method, p, body) {
  const tk = await runToken();
  if (tk.error) return { ok: false, status: 0, error: tk.error, transient: false };
  let base;
  try {
    base = runBase();
  } catch (e) {
    return { ok: false, status: 0, error: e.message, transient: false };
  }
  const headers = { Authorization: `Bearer ${tk.token}`, Accept: "application/json", "User-Agent": "mooniex-ask-run/1" };
  const opts = { method, headers, redirect: "manual", signal: AbortSignal.timeout(RUN_HTTP_TIMEOUT_MS) };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json; charset=utf-8";
    opts.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(base + p, opts);
  } catch (err) {
    const why = err?.cause?.code ?? err?.cause?.message ?? err?.message ?? String(err);
    return { ok: false, status: 0, error: `hub unreachable at ${base}: ${why}`, transient: true };
  }
  if (res.status >= 300 && res.status < 400) {
    return {
      ok: false,
      status: res.status,
      error: `hub answered ${res.status} redirect to ${res.headers.get("location") ?? "?"}: not followed (the token only goes to ${base}); check RUN_INBOX_URL`,
      transient: false,
    };
  }
  const raw = await res.text().catch(() => "");
  let parsed = null;
  try {
    parsed = raw.trim() ? JSON.parse(raw) : {};
  } catch {
    parsed = null;
  }
  if (res.ok && parsed === null) {
    return { ok: false, status: res.status, error: `hub answered non-JSON: ${raw.slice(0, 120)}`, transient: false };
  }
  return {
    ok: res.ok,
    status: res.status,
    body: parsed ?? { detail: raw.slice(0, 200) },
    transient: res.status >= 500 || res.status === 429,
  };
}

function runHubMessage(r) {
  if (r.error) return r.error;
  const code = typeof r.body?.error === "string" ? r.body.error : null;
  const detail = r.body?.message ?? r.body?.detail ?? null;
  let msg = `hub refused (${r.status}${code ? ": " + code : ""})`;
  if (detail) msg += ` ${detail}`;
  const hint = (code && RUN_HINTS[code]) || RUN_HINTS[r.status];
  if (hint) msg += `: ${hint}`;
  return msg;
}

function runUnwrap(rec) {
  if (rec && typeof rec === "object" && rec.ask && typeof rec.ask === "object") return rec.ask;
  return rec && typeof rec === "object" ? rec : {};
}

function runNormalizeId(raw) {
  let s = String(raw ?? "").trim();
  if (s.includes("#")) s = s.slice(s.lastIndexOf("#") + 1); // the phone URL .../run#RUN-...
  return RUN_ID_RE.test(s) ? s : null;
}

function runTrimTail(rec, lines) {
  if (typeof rec.output_tail !== "string" || !lines) return rec;
  const all = rec.output_tail.split(RUN_LINE_SPLIT);
  if (all.length && all[all.length - 1] === "") all.pop();
  if (all.length <= lines) return rec;
  return { ...rec, output_tail: all.slice(-lines).join("\n"), output_tail_shown: `last ${lines} of ${all.length} lines` };
}

async function tool_ask_run(args = {}) {
  let payload;
  try {
    payload = runBuildPayload(args);
  } catch (e) {
    return runFail(`refused: ${e.message}`);
  }
  const hits = runSecretShapes(payload);
  if (hits.length) {
    return runFail(
      `refused: secret_shaped_value; nothing was sent:\n  ${hits.join("\n  ")}\n` +
        "Reference an env var by name ($NAME, env_keys) or an Infisical path instead (DESIGN §6).",
    );
  }
  const gate = runRoleGate(payload);
  if (gate) return runFail(`refused: ${gate}`);
  if (args.dry_run) {
    let base;
    try {
      base = runBase();
    } catch (e) {
      return runFail(e.message);
    }
    return text(JSON.stringify({ dry_run: true, would_post: `${base}/api/run/asks`, payload }, null, 2));
  }
  const r = await runApi("POST", "/api/run/asks", payload);
  if (!r.ok) return runFail(runHubMessage(r));
  const rec = runUnwrap(r.body);
  if (typeof rec.id !== "string" || !rec.id) return runFail(`hub accepted the ask but returned no id (${r.status})`);
  return text(
    JSON.stringify(
      { id: rec.id, url: `${runBase()}/run#${rec.id}`, risk: rec.risk ?? null, expires_at: rec.expires_at ?? null },
      null,
      2,
    ),
  );
}

async function tool_ask_run_wait(args = {}) {
  const id = runNormalizeId(args.id);
  if (!id) return runFail(`not a Run Inbox id: '${args.id ?? ""}' (expected RUN-YYYYMMDD-HHMM-xxxx or its /run#... URL)`);
  const interval = Math.max(Number(args.interval_s) || RUN_POLL_S, RUN_MIN_POLL_S);
  const maxWait = Math.min(Math.max(Number(args.max_wait_s) || RUN_WAIT_DEFAULT_S, 1), RUN_WAIT_MAX_S);
  const lines = args.tail_lines === undefined || args.tail_lines === null ? RUN_TAIL_LINES : Number(args.tail_lines);
  const deadline = Date.now() + maxWait * 1000;
  let last = null;
  let failures = 0;
  for (;;) {
    const r = await runApi("GET", `/api/run/asks/${encodeURIComponent(id)}`);
    if (r.ok) {
      failures = 0;
      last = { id, ...runUnwrap(r.body) };
      if (RUN_TERMINAL.includes(last.status)) {
        return text(JSON.stringify({ terminal: true, ...runTrimTail(last, lines) }, null, 2));
      }
    } else if (!r.transient || ++failures > RUN_MAX_POLL_FAILURES) {
      return runFail(runHubMessage(r));
    }
    const left = deadline - Date.now();
    if (left <= 0) {
      const note = `still ${last?.status ?? "unknown"} after ${maxWait} s; call ask_run_wait again`;
      return text(JSON.stringify({ terminal: false, note, ...(last ? runTrimTail(last, lines) : { id }) }, null, 2));
    }
    await new Promise((resolve) => setTimeout(resolve, Math.min(interval * 1000, left)));
  }
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
    serverInfo: { name: "mooniex-coord", version: "0.2.0" },
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
      case "ask_run":
        return tool_ask_run(args);
      case "ask_run_wait":
        return tool_ask_run_wait(args);
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
