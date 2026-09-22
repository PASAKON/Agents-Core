#!/usr/bin/env node
// PostToolUse(Bash): track command patterns. Bumps counter in candidates.json.
// Hook input: { tool_name, tool_input: { command }, tool_response, ... } via stdin.
import { readFileSync, writeFileSync, existsSync } from "fs";
import { homedir } from "os";
import { join } from "path";

const STATE = join(homedir(), ".claude", ".allowlist-candidates.json");
const SETTINGS = join(homedir(), ".claude", "settings.json");

const AUTO_ALLOWED = new Set([
  "cal","uptime","cat","head","tail","wc","stat","strings","hexdump","od","nl",
  "id","uname","free","df","du","locale","groups","nproc","basename","dirname",
  "realpath","cut","paste","tr","column","tac","rev","fold","expand","unexpand",
  "fmt","comm","cmp","numfmt","readlink","diff","true","false","sleep","which",
  "type","expr","test","getconf","seq","tsort","pr","echo","printf","ls","cd",
  "find","pwd","whoami","alias","xargs","file","sed","sort","man","help",
  "netstat","ps","base64","grep","egrep","fgrep","sha256sum","sha1sum","md5sum",
  "tree","date","hostname","info","lsof","pgrep","tput","ss","fd","fdfind",
  "aki","rg","jq","uniq","history","arch","ifconfig","pyright","mkdir","cp","mv"
]);

const GIT_READONLY = new Set([
  "status","log","diff","show","blame","branch","tag","remote","ls-files",
  "ls-remote","config","rev-parse","describe","reflog","shortlog","cat-file",
  "for-each-ref","worktree"
]);

const GH_READONLY = new Set([
  "pr","issue","run","workflow","repo","release","api","auth","search"
]);

const DANGER = new Set([
  "rm","sudo","ssh","sshpass","scp","curl","wget","kill","pkill","killall",
  "chmod","chown","dd","mkfs","fdisk","mount","umount","reboot","shutdown",
  "node","python","python3","ruby","perl","php","bash","sh","zsh","fish",
  "eval","exec","npx","bunx","uvx","deno","bun","docker","kubectl"
]);

function parseCommand(cmd) {
  if (!cmd) return null;
  cmd = cmd.split(/[|&;]/)[0].trim();
  // skip comments, heredocs, redirections-only
  if (cmd.startsWith("#")) return null;
  if (cmd.startsWith("<<")) return null;
  while (/^[A-Z_][A-Z0-9_]*=\S+\s+/.test(cmd)) cmd = cmd.replace(/^[A-Z_][A-Z0-9_]*=\S+\s+/, "");
  cmd = cmd.replace(/^sudo\s+/, "").replace(/^timeout\s+\S+\s+/, "");
  const toks = cmd.split(/\s+/);
  let c = (toks[0] || "").replace(/.*\//, "");
  if (!c) return null;
  if (!/^[a-zA-Z][\w-]*$/.test(c)) return null;
  if (DANGER.has(c)) return null;
  if (AUTO_ALLOWED.has(c)) return null;
  const s = toks[1] || "";
  if (c === "git" && GIT_READONLY.has(s)) return null;
  if (c === "gh" && GH_READONLY.has(s)) return null;
  const isWord = (x) => x && /^[a-zA-Z][\w-]*$/.test(x);
  if (isWord(s)) return `Bash(${c} ${s} *)`;
  return `Bash(${c} *)`;
}

function loadAllowed() {
  try {
    const s = JSON.parse(readFileSync(SETTINGS, "utf8"));
    return new Set((s.permissions?.allow) || []);
  } catch { return new Set(); }
}

let raw = "";
process.stdin.on("data", (d) => (raw += d));
process.stdin.on("end", () => {
  try {
    const input = JSON.parse(raw || "{}");
    if (input.tool_name !== "Bash") return;
    const pattern = parseCommand(input.tool_input?.command);
    if (!pattern) return;
    const allowed = loadAllowed();
    if (allowed.has(pattern)) return;

    let state = {};
    if (existsSync(STATE)) {
      try { state = JSON.parse(readFileSync(STATE, "utf8")); } catch {}
    }
    const entry = state[pattern] || { count: 0, first: Date.now(), last: 0, notified: false };
    entry.count += 1;
    entry.last = Date.now();
    state[pattern] = entry;
    writeFileSync(STATE, JSON.stringify(state, null, 2));
  } catch {}
});
