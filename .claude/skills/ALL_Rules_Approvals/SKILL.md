---
name: ALL_Rules_Approvals
kind: rules
owner: COO
description: RULES — What needs the CEO and what does not (CEO ruling 2026-09-27) — own-lane work and skills, cross-lane skills without asking, money / secrets / permanent deletion / speaking in his name need him, deploys are the CTO's call. Trigger on /ALL_Rules_Approvals, "ต้องขออนุมัติไหม", "ขออนุมัติ", "need approval", "can I deploy", "ใช้ skill สายอื่นได้ไหม".
created_by: agent
author: {role: cto, date: "2026-09-27"}
audience: [all]
---

# What needs the CEO, and what does not

Binds every session and every worker, on every machine. The CEO confirmed it on 2026-09-27 after the CTO
summarised it back to him ("OK เห็นด้วยทั้งหมด", then "ที่เหลือ เห็นด้วยทั้งหมด" for the two open points). His
own words for the core: each role does only its own kind of work and calls the skills of its own role;
when another role's skill is genuinely needed to finish the job, use it without asking first; only money and
secrets come to him; deploys are the CTO's decision ("อยากให้ CTO เป็นคนตัดสินใจ เมื่อเห็นสมควร ... มีเช็ค list
ในการ Deploy").

Platform-specific money rules (never press Rerun on Higgsfield, read the struck-through price, the Flow test
cap, the 4K upscale charge on TopView) stay in the platform's own skill, where the operator meets them at the
moment of spending; this file is the org rule they all point to.

## Rules

1. **HARD — Money: the CEO sees the exact amount first.** Any spend — a paid generation, a RunPod pod hour, a
   paid image, a purchase, a subscription, a top-up — waits for his OK with the exact credits and $. One
   capped round at a time; a second round needs a second OK. A refunded failure does not carry the old
   approval over: the refire is a new spend. Dry runs, prompt rendering and reading a balance are free.
   **Why hard:** money — a fired generation or a started pod cannot be taken back.
2. **HARD — Secrets go to the CEO.** Creating, moving, printing, rotating or pasting a credential, token,
   password or key, or putting one into a file, a chat or a worker, waits for him (Infisical is the target
   home). **Why hard:** safety — a leaked secret cannot be un-leaked.
3. **HARD — Permanent deletion of data waits for his word.** Drive files, disk contents and datasets are
   deleted only after he says so for that deletion, with the backup shown (`CXO_Rules_GDrive_Filing`,
   `ALL_Rules_DiskHygiene`). Moving to an archive or a trash that can be restored is not deletion.
   **Why hard:** irreversible.
4. **HARD — Speaking in his name to real people or in public needs a standing approval for that channel.**
   Replies to YouTube comments on his films are approved standing (`docs/promo/REPLY-VOICE.md`); a new
   channel, a new kind of message or a first contact asks him once. **Why hard:** scope — the words carry his
   name and cannot be unsent.
5. **Deploys are the CTO's call.** The CTO deploys when its checklist is green, announces it with a rollback
   line, and reports after. Another lane that needs a deploy hands it to the CTO rather than deploying.
   Code merges were already the CTO's (CEO 2026-09-19).
6. **Work your own lane; borrow another lane's skill when the job needs it, without asking.** Code → CTO,
   content / film / posters / posts → CMO, metrics and A/B results → CGO, money → CFO, portfolio and the
   org system → COO. When you borrow, file what you learned back into the owner skill as a Field note and
   write the borrowing in the project's `STATUS.md`, so the COO sees which lanes lack a skill.
7. Story, characters, lines, the ending and the order of a film are the director's (`CMO_Knowledge_Film_Production`
   §10). Not a gate: a boundary on what is ours to decide.

## When the CEO changes a rule

Write his words verbatim here, keep the old line as `[SUPERSEDED <date>]` with his message as the evidence,
and tell every C-level in one batched note (the COO's routing job).

## Field notes
