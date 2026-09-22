#!/usr/bin/env node
/**
 * UserPromptSubmit hook — claim-or-heartbeat.
 *
 * Per CTO IRON-RULES §15 (post-2026-04-27 update): every Claude turn
 * starts with a desk claim. If we already hold one, heartbeat. If
 * stale/released or no claim, claim fresh.
 *
 * Resolves desk via:
 *   1. cwd folder match `mooniex-webapp (Desk-X)` — desk = X
 *   2. role memory file at ~/.claude/projects/<sanitized>/memory/
 *      reference_office_role.md — parses "## Desk" line
 *
 * agent_id formula:
 *   - folder-bound desk (A-F): sha256(host|cwd|UTC-day) — same session
 *     across hook invocations gets same id
 *   - cross-desk role (CTO/CMO): sha256(host|"role:Desk-X"|UTC-day) —
 *     stable across cwd hops within the same day
 */

import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";

const CWD = process.cwd();
const FOLDER = path.basename(CWD);
const CWD_HASH = crypto.createHash("sha256").update(CWD).digest("hex").slice(0, 12);
const CACHE_PATH = path.join(os.homedir(), ".claude", `office-state-${CWD_HASH}.json`);
const CONFIG_PATH = path.join(os.homedir(), ".claude", "office.json");
const HEARTBEAT_MIN_INTERVAL_MS = 60_000;

function deskFromFolder(folder, cwd = CWD) {
  if (cwd === "/Users/gob/MoonieXHQ/Agents/Wikis" || cwd.startsWith("/Users/gob/MoonieXHQ/Agents/Wikis/")) {
    return "Desk-CTO";
  }
  const m = folder.match(/^mooniex-webapp \(([^)]+)\)$/);
  return m ? m[1] : null;
}

/**
 * Walk PWD + ancestors up to /Users/gob/projects looking for a
 * `.claude/desk` text file. First file's first non-blank line wins.
 * Returns Desk-X string or null. The walk caps at ~6 levels to keep
 * the hook cheap.
 */
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

/**
 * Env override (highest-priority intent signal). Shell rc can set
 * `export MOONIEX_DESK=Desk-CTO` to pin the claim regardless of
 * cwd or memory — useful when working from /Users/gob/projects on
 * cross-desk tasks.
 */
function deskFromEnv() {
  const v = process.env.MOONIEX_DESK?.trim();
  if (!v) return null;
  return /^Desk-[A-Z0-9_]+$/.test(v) ? v : null;
}

async function deskFromMemory() {
  // Look up THIS session's role memory file at canonical sanitized path.
  // Claude Code uses `~/.claude/projects/<cwd-with-slashes-as-dashes>/memory/`.
  // Try a few sanitization variants (Claude Code's exact rules vary across
  // versions: parens / spaces sometimes become "-", sometimes stay).
  const candidates = [
    CWD.replace(/[\/\\]/g, "-"),
    CWD.replace(/[\/\\]/g, "-").replace(/[() ]/g, "-").replace(/--+/g, "-"),
    CWD.replace(/[\/\\]/g, "-").replace(/[() ]/g, ""),
    CWD.replace(/[\/\\]/g, "-").replace(/ /g, "-").replace(/--+/g, "-"),
  ];
  const seen = new Set();
  for (const cand of candidates) {
    if (seen.has(cand)) continue;
    seen.add(cand);
    const p = path.join(
      os.homedir(),
      ".claude",
      "projects",
      cand,
      "memory",
      "reference_office_role.md",
    );
    try {
      const text = await fs.readFile(p, "utf8");
      const m =
        text.match(/^##\s*Desk\s*\n+`?(Desk-[A-Z0-9_]+)`?/m) ??
        text.match(/Desk:\s*`?(Desk-[A-Z0-9_]+)`?/) ??
        text.match(/^##\s*Display\s*name[\s\S]*?\(?(Desk-[A-Z0-9_]+)\)?/m) ??
        text.match(/`(Desk-[A-Z0-9_]+)`/);
      if (m) return m[1];
    } catch {
      /* try next candidate */
    }
  }
  return null;
}

/**
 * Desk resolution priority (highest first):
 *   1. MOONIEX_DESK env var      — explicit shell-rc pin
 *   2. .claude/desk ancestor file — per-folder pin
 *   3. Folder regex / LLMs path  — implicit cwd
 *   4. Role memory file          — final fallback
 */
async function resolveDesk() {
  return (
    deskFromEnv() ??
    (await deskFromAncestorMarker()) ??
    deskFromFolder(FOLDER) ??
    (await deskFromMemory())
  );
}

function computeAgentId(desk) {
  // Desk-CTO uses the canonical id seeded into webapp_office_agents
  // by the 202604270300 migration. Stable across all CTO sessions
  // regardless of cwd / day so the role joins consistently.
  if (desk === "Desk-CTO") return "claude-cto-cross-desk";

  const day = new Date().toISOString().slice(0, 10);
  const isFolderDesk = deskFromFolder(FOLDER) === desk;
  const seed = isFolderDesk
    ? `${os.hostname()}|${CWD}|${day}`
    : `${os.hostname()}|role:${desk}|${day}`;
  return (
    "claude-" +
    crypto.createHash("sha256").update(seed).digest("hex").slice(0, 12)
  );
}

async function readJson(p) {
  try {
    return JSON.parse(await fs.readFile(p, "utf8"));
  } catch {
    return null;
  }
}

async function writeJson(p, obj) {
  await fs.writeFile(p, JSON.stringify(obj, null, 2), "utf8");
}

async function main() {
  const desk = await resolveDesk();
  if (!desk) return;

  const config = await readJson(CONFIG_PATH);
  const apiBase =
    config?.api_base ?? process.env.OFFICE_API_BASE ?? "https://www.mooniex.com";
  const token = config?.token ?? process.env.OFFICE_TOKEN;
  if (!token) return;

  const auth = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  const now = Date.now();
  const cache = await readJson(CACHE_PATH);

  // 1. Try heartbeat if we already hold a claim for this desk
  if (cache?.claim_id && cache.desk_id === desk) {
    if (now - (cache.last_heartbeat ?? 0) < HEARTBEAT_MIN_INTERVAL_MS) {
      return; // recently beat — skip
    }
    const r = await fetch(`${apiBase}/api/office/heartbeat`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ claim_id: cache.claim_id }),
    }).catch(() => null);
    if (r?.ok) {
      await writeJson(CACHE_PATH, { ...cache, last_heartbeat: now });
      return;
    }
    // stale_or_released → fall through to re-claim
  }

  // 2. Claim fresh (turn-start, or post-stale)
  const agentId = computeAgentId(desk);
  const day = new Date().toISOString().slice(0, 10);
  const r = await fetch(`${apiBase}/api/office/claim`, {
    method: "POST",
    headers: auth,
    body: JSON.stringify({
      desk_id: desk,
      agent_id: agentId,
      agent_kind: "claude",
      agent_label: `Claude · ${os.hostname()} · ${day}`,
    }),
  }).catch(() => null);

  if (!r) return;
  const body = await r.json().catch(() => null);
  if (r.ok && body?.ok) {
    await writeJson(CACHE_PATH, {
      claim_id: body.claim_id,
      desk_id: desk,
      agent_id: agentId,
      last_heartbeat: now,
    });
  }
  // 409 occupied: silent — another agent owns this desk
}

main().catch(() => {});
