#!/usr/bin/env node
/**
 * PreToolUse hook on Write|Edit|Bash that claims the desk before the
 * agent's first edit. If the desk is occupied, blocks the tool with a
 * deny decision and tells the user.
 *
 * Config: ~/.claude/office.json
 *   { "api_base": "https://www.mooniex.com", "token": "xxx" }
 *
 * Cache: ~/.claude/office-state-<cwdHash>.json
 *   { "claim_id": "...", "desk_id": "Desk-1", "last_heartbeat": <ms>,
 *     "agent_id": "..." }
 *
 * No-op if cwd isn't a `mooniex-webapp (Desk-*)` folder.
 *
 * Backed by /api/office/claim + /api/office/heartbeat in mooniex-webapp.
 * See org:IRON-RULES.md §1 desk model (Agents-Wikis, not LLMs — moved
 * there by the ADR-0013 wiki split).
 */

import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";

const CWD = process.cwd();
const FOLDER = path.basename(CWD);
const CONFIG_PATH = path.join(os.homedir(), ".claude", "office.json");
const CWD_HASH = crypto.createHash("sha256").update(CWD).digest("hex").slice(0, 12);
const CACHE_PATH = path.join(os.homedir(), ".claude", `office-state-${CWD_HASH}.json`);
const HEARTBEAT_MIN_INTERVAL_MS = 60_000;

// Parse "Desk-X" from "mooniex-webapp (Desk-X)" OR detect special cwds
// that map to a fixed desk:
//   /Users/gob/projects/LLMs        → Desk-CTO  (CTO works on the wiki)
// Returns the desk_id string or null if cwd is not a desk.
function deskFromFolder(folder, cwd) {
  if (cwd === "/Users/gob/projects/LLMs" || cwd.startsWith("/Users/gob/projects/LLMs/")) {
    return "Desk-CTO";
  }
  const m = folder.match(/^mooniex-webapp \(([^)]+)\)$/);
  return m ? m[1] : null;
}

/** Env override — `export MOONIEX_DESK=Desk-CTO` in shell rc. */
function deskFromEnv() {
  const v = process.env.MOONIEX_DESK?.trim();
  if (!v) return null;
  return /^Desk-[A-Z0-9_]+$/.test(v) ? v : null;
}

/** Walk PWD + ≤ 6 ancestors looking for `.claude/desk` marker. */
async function deskFromAncestorMarker() {
  let dir = CWD;
  for (let i = 0; i < 6; i++) {
    try {
      const text = await fs.readFile(path.join(dir, ".claude", "desk"), "utf8");
      const line = text.split("\n").find((l) => l.trim()) ?? "";
      const m = line.match(/(Desk-[A-Z0-9_]+)/);
      if (m) return m[1];
    } catch {
      /* not present at this level */
    }
    const parent = path.dirname(dir);
    if (parent === dir || parent === "/Users/gob") break;
    dir = parent;
  }
  return null;
}

async function readJson(p) {
  try {
    const text = await fs.readFile(p, "utf8");
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function writeJson(p, obj) {
  await fs.writeFile(p, JSON.stringify(obj, null, 2), "utf8");
}

function emitOutput(obj) {
  process.stdout.write(JSON.stringify(obj));
}

async function fetchJson(url, opts) {
  const res = await fetch(url, opts);
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* ignore */
  }
  return { status: res.status, ok: res.ok, body };
}

/**
 * Desk resolution priority (highest first):
 *   1. MOONIEX_DESK env var
 *   2. .claude/desk ancestor file
 *   3. Folder regex / LLMs path
 * Memory file fallback handled by office-userprompt.mjs only.
 */
async function resolveDesk() {
  return (
    deskFromEnv() ??
    (await deskFromAncestorMarker()) ??
    deskFromFolder(FOLDER, CWD)
  );
}

async function main() {
  const desk = await resolveDesk();
  if (!desk) {
    // Not a webapp desk folder — silently no-op
    return;
  }

  const config = await readJson(CONFIG_PATH);
  const apiBase =
    config?.api_base ?? process.env.OFFICE_API_BASE ?? "https://www.mooniex.com";
  const token = config?.token ?? process.env.OFFICE_TOKEN;
  if (!token) {
    // No token configured — fall back to silent no-op so the user isn't
    // blocked. Setup steps land in /admin/office-simulator.
    return;
  }

  const auth = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  const now = Date.now();
  const cache = await readJson(CACHE_PATH);

  // If we already hold the claim AND heartbeat is fresh, throttle: just
  // heartbeat (cheap) and let the tool through.
  if (cache?.claim_id && cache.desk_id === desk) {
    if (now - (cache.last_heartbeat ?? 0) < HEARTBEAT_MIN_INTERVAL_MS) {
      return;
    }
    const r = await fetchJson(`${apiBase}/api/office/heartbeat`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ claim_id: cache.claim_id }),
    });
    if (r.ok) {
      await writeJson(CACHE_PATH, { ...cache, last_heartbeat: now });
      return;
    }
    // 404 = stale or released → fall through to re-claim
  }

  // Build agent_id. Desk-CTO uses the canonical "claude-cto-cross-desk"
  // identifier so /api/office/claim joins the CTO role from
  // webapp_office_agents (seeded migration). All other desks use a
  // deterministic per (host + cwd + day) hash; the day component scopes
  // audits to a calendar day, and tryAdoptOrphan() below handles UTC
  // midnight rollover by recognising the previous day's hash as ours.
  const day = new Date().toISOString().slice(0, 10);
  let agentId;
  let agentLabel;
  if (desk === "Desk-CTO") {
    agentId = "claude-cto-cross-desk";
    agentLabel = `Claude Opus 4.7 — CTO (cross-desk) · ${day}`;
  } else {
    const agentSeed = `${os.hostname()}|${CWD}|${day}`;
    agentId = `claude-${crypto
      .createHash("sha256")
      .update(agentSeed)
      .digest("hex")
      .slice(0, 12)}`;
    agentLabel = `Claude · ${os.hostname()} · ${day}`;
  }

  const claimReq = {
    desk_id: desk,
    agent_id: agentId,
    agent_kind: "claude",
    agent_label: agentLabel,
  };
  const r = await fetchJson(`${apiBase}/api/office/claim`, {
    method: "POST",
    headers: auth,
    body: JSON.stringify(claimReq),
  });

  if (r.ok && r.body?.ok) {
    await writeJson(CACHE_PATH, {
      claim_id: r.body.claim_id,
      desk_id: desk,
      agent_id: agentId,
      last_heartbeat: now,
    });
    return;
  }

  if (r.status === 409 && r.body?.code === "occupied") {
    const cur = r.body.current ?? {};
    if (await tryAdoptOrphan(apiBase, auth, desk, cur, now)) {
      return;
    }
    const since = cur.claimed_at
      ? new Date(cur.claimed_at).toLocaleString()
      : "?";
    const occupant = cur.agent_label ?? cur.agent_id ?? "another agent";
    const reason =
      `Desk ${desk} is occupied by ${occupant} since ${since}. ` +
      `Switch to a free desk (see /admin/office-simulator) before editing.`;
    emitOutput({
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: reason,
      },
      systemMessage: reason,
    });
    return;
  }

  // Any other failure (auth, network, 5xx) → no-op so the tool isn't
  // blocked by an offline coordinator. Coordination is best-effort.
}

/**
 * Day-rollover + folder-rename recovery. When /claim returns 409, the
 * existing claim might actually be ours from a previous day or before
 * the desk folder was renamed (cache invalidated). If the claim's
 * agent_id matches any (host + cwd + day) hash we'd compute for today,
 * yesterday, or the day before, adopt it: heartbeat the existing
 * claim_id, update the cache, and return success. The session doesn't
 * see a deadlock; the audit trail keeps the original claim_id.
 */
async function tryAdoptOrphan(apiBase, auth, desk, cur, now) {
  if (!cur?.id || !cur?.agent_id) return false;
  const candidates = candidateAgentIds(3);
  // Desk-CTO uses a fixed canonical id (not a host|cwd|day hash). Add
  // it explicitly so 409 from our own prior CTO claim is recognised
  // and adopted instead of blocking.
  if (desk === "Desk-CTO") {
    candidates.push("claude-cto-cross-desk");
  }
  if (!candidates.includes(cur.agent_id)) return false;

  // 2026-05-17 — two-session rival guard.
  // Two Claude sessions on the same Mac with same cwd compute identical
  // agent_id. If a rival session has an actively-heartbeating claim AND
  // we have no local cache, we are the OTHER session arriving second —
  // refuse to adopt + let main() show a clear deny. Adopting would
  // hijack the rival's claim_id and corrupt the audit trail.
  const heartbeatFreshMs = 60_000;
  const hbStr = cur.last_heartbeat_at;
  const hbMs = hbStr ? Date.parse(hbStr) : null;
  const isFresh = hbMs && now - hbMs < heartbeatFreshMs;
  const cacheExists = (await readJson(CACHE_PATH)) != null;
  if (isFresh && !cacheExists) {
    return false;
  }

  // Same host+cwd hash on a recent day → claim is ours from yesterday
  // (or post-folder-rename). Heartbeat to confirm still alive, then
  // adopt into the cache.
  const r = await fetchJson(`${apiBase}/api/office/heartbeat`, {
    method: "POST",
    headers: auth,
    body: JSON.stringify({ claim_id: cur.id }),
  });
  if (!r.ok) return false;

  await writeJson(CACHE_PATH, {
    claim_id: cur.id,
    desk_id: desk,
    agent_id: cur.agent_id,
    last_heartbeat: now,
  });
  return true;
}

/**
 * Compute the (host + cwd + day) hashes the hook would have produced
 * for today and the previous N-1 days. Used by the orphan-adoption
 * path on 409 to recognise our own stale claims after UTC midnight or
 * a folder rename.
 */
function candidateAgentIds(numDays) {
  const out = [];
  for (let offset = 0; offset < numDays; offset++) {
    const d = new Date(Date.now() - offset * 24 * 60 * 60_000);
    const day = d.toISOString().slice(0, 10);
    const seed = `${os.hostname()}|${CWD}|${day}`;
    const hash = crypto.createHash("sha256").update(seed).digest("hex").slice(0, 12);
    out.push(`claude-${hash}`);
  }
  return out;
}

main().catch(() => {
  /* swallow — never block the tool on hook crash */
});
