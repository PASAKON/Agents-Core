#!/usr/bin/env node
/**
 * Stop hook — releases the desk claim at the end of every assistant turn.
 *
 * Per CTO IRON-RULES §15 (post-2026-04-27 update): the desk lifecycle
 * follows turn boundaries. Stop fires when Claude finishes responding —
 * release immediately so /admin/office-simulator shows the agent as
 * idle until the next UserPromptSubmit fires the next claim.
 *
 * Also fires on /clear, /resume, compact, normal stop. Idempotent;
 * if no claim cached, exits silently.
 */

import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";

const CWD = process.cwd();
const CWD_HASH = crypto.createHash("sha256").update(CWD).digest("hex").slice(0, 12);
const CACHE_PATH = path.join(os.homedir(), ".claude", `office-state-${CWD_HASH}.json`);
const CONFIG_PATH = path.join(os.homedir(), ".claude", "office.json");

async function readJson(p) {
  try {
    return JSON.parse(await fs.readFile(p, "utf8"));
  } catch {
    return null;
  }
}

async function main() {
  const cache = await readJson(CACHE_PATH);
  if (!cache?.claim_id) return;

  const config = await readJson(CONFIG_PATH);
  const apiBase =
    config?.api_base ?? process.env.OFFICE_API_BASE ?? "https://www.mooniex.com";
  const token = config?.token ?? process.env.OFFICE_TOKEN;
  if (!token) return;

  await fetch(`${apiBase}/api/office/release`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ claim_id: cache.claim_id, reason: "turn_end" }),
  }).catch(() => {
    /* network fail = stale_sweep cron will release later */
  });

  await fs.unlink(CACHE_PATH).catch(() => {
    /* already gone */
  });
}

main().catch(() => {});
