# Letter — Contabo CTO (session 14cc900f) → Mac CTO, 2026-09-27

The CEO approved seven skill kinds and a rename of every org skill to `<ROLE>_<Kind>_<Topic>`; phases 0–4 are
on origin/main (b68e3735 · f39faa93 · 1e818147 · e90df583 · 646341fd · 9cc80bbd). Record and full maps:
`docs/org/SKILL-KINDS-2026-09-27.md`, `docs/org/skill-rename/phase*.json`. Procedure: `ALL_Protocol_SkillAuthor`.
Four things only the Mac can do, in this order.

1. **Check `.venv` right after you pull.** 1e818147 committed a `.venv` SYMLINK by mistake (`.gitignore` had only
   `.venv/`, which matches a directory, not a link). A checkout that fast-forwarded exactly to 1e818147 had its real,
   ignored `.venv` replaced by that link — it happened to the Contabo checkout and was rebuilt. e90df583 untracks it
   and ignores `.venv` as a file too. If you pull straight past it you are safe; if `ls -la .venv` shows a symlink,
   rebuild: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
2. **Re-point `~/.claude/skills`.** 38 skill directories were renamed; the old names are 30-day stubs with
   `disable-model-invocation: true`. A symlink to an old directory now lands on a stub. `claude-home/skills.txt`
   carries the new names and paths; re-run the linker you use for it (`scripts/install-claude-home.sh` was
   swept too), then `ls -la ~/.claude/skills | grep -- '->'` and confirm no link points at a MOVED stub.
3. **Sweep the wikis.** Agents-Rules and Agents-Wikis are read-only on Contabo, so their pages still name the old
   skills. Run the same map over them (`tools/skill_rename.py` holds the matcher: whole-token, never a name
   followed by `.<ext>`), then rsync to Contabo as CLAUDE.md describes.
4. **Two things you own that changed under you:** the MiniMax H3 skill is now `CMO_Knowledge_MiniMax_H3` (film
   production moved to the CMO lane), and `gdrive-filing` is split into `CXO_Rules_GDrive_Filing` +
   `CXO_Knowledge_GDrive_FolderMap` + `CXO_Procedure_GDrive_BulkTransfer`; `scripts/hook-gdrive-skill-gate.py` now
   arms on reading `CXO_Rules_GDrive_Filing`.

Also new: `ALL_Rules_Approvals` (the CEO's 2026-09-27 ruling: money, secrets, permanent deletion and speaking in his
name need him; deploys are the CTO's call; cross-lane skills may be used without asking). The COO role is written
(`roles/coo.md`) but PARKED — SomPong takes it later (`docs/design/sompong-coo-prompt.md`).
