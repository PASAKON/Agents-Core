# Source

Vendored from https://github.com/blader/humanizer at commit 225a6f39ac85f76ee48dbad772ea4abe4ed6c9d8
(2026-09-28), MIT (see LICENSE). Only SKILL.md and LICENSE are copied; the repo's plugin manifests,
workflows and scripts are not. Installed 2026-10-14 on the CEO's order: every outside-facing text
(LINE groups, public posts, comment replies, chatbots) goes through this skill.

- Do not edit SKILL.md here. To update, copy SKILL.md + LICENSE from a newer upstream commit, read the
  whole diff first (it loads into every session), and change the sha above.
- Never install it with `npx skills add` or a plugin marketplace: those pull unpinned code.
- Byte-identical to SomPong's copy at Projects/MoonieX/SomPong/.claude/skills/humanizer/ on 2026-10-14.
- Thai tells live in a separate companion skill owned by the CMO (`CMO_Standard_HumanVoice_TH`).
- Chatbots never get the full skill in their system prompt (about 8k tokens per message). They get
  `CHATBOT-BLOCK.md`; the full skill is for reviewing reply samples offline.
