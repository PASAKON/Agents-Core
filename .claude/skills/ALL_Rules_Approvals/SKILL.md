---
name: ALL_Rules_Approvals
kind: rules
owner: COO
description: RULES — What needs the CEO and what does not (CEO ruling 2026-09-27) — own-lane work and skills, cross-lane skills without asking, money / secrets / permanent deletion / speaking in his name need him, deploys and merges are the CTO's and PHs' call, and the four checks every card, relay request or alert passes before it reaches him (2026-10-26). Trigger on /ALL_Rules_Approvals, "ต้องขออนุมัติไหม", "ขออนุมัติ", "need approval", "can I deploy", "ใช้ skill สายอื่นได้ไหม", "ส่งการ์ดหา CEO", "raise a card".
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
   Exception (CEO 2026-10-26, Q-20261026-0814-e94a): a C-level creates or deletes a provider API key itself,
   with no card per key, in the key's own repo project, but only through `CTO_Procedure_KeyFetch`. A worker
   drives the provider page in a Browser Home and pipes the key straight into Infisical. No model sees the
   value, and each create or delete gets one ledger line. Org-Infra stays his to enter. On the free plan the
   project is the only wall, so nothing moves into Org-Infra (CEO 2026-10-26, Q-20261026-1118-4d3d: "ฟรี: แยก
   project ต่อ repo เป็นกำแพง, keyfetch-writer แทนที่นั่ง setup (แนะนำ)"). Moving, printing or pasting a value, and
   any change to who may read a secret, still wait for him.
   `[SUPERSEDED 2026-10-26]` "in every project including Org-Infra" (e94a, choice "ทุก project รวม Org-Infra"):
   the free plan cannot scope inside one project, and on 4d3d the CEO chose the free plan.
3. **HARD — Permanent deletion of data waits for his word.** Drive files, disk contents and datasets are
   deleted only after he says so for that deletion, with the backup shown (`CXO_Rules_GDrive_Filing`,
   `ALL_Rules_DiskHygiene`). Moving to an archive or a trash that can be restored is not deletion.
   Standing exception (CEO 2026-09-28, "งานเสร็จจบ สำรองแล้ว = ลบได้ Green เพราะถ้า เราต้องการข้อมูลเมื่อไหร่ เข้า Drive มาสำรองเสมอ"): the local copy of finished work whose
   every file md5-matches Drive, and Contabo's journal above 500 MB, are Green (`ALL_Rules_DiskHygiene`).
   Deleting on Drive itself still waits for his word.
   **Why hard:** irreversible.
4. **HARD — Speaking in his name to real people or in public needs a standing approval for that channel.**
   Replies to YouTube comments on his films are approved standing (`docs/promo/REPLY-VOICE.md`); a new
   channel, a new kind of message or a first contact asks him once. **Why hard:** scope — the words carry his
   name and cannot be unsent.
5. **Deploys are the CTO's call.** The CTO deploys when its checklist is green, announces it with a rollback
   line, and reports after. Another lane that needs a deploy hands it to the CTO rather than deploying.
   Code merges were already the CTO's (CEO 2026-09-19). Merges need no CEO card: the CTO and each PH merge
   their own after `CTO_Gate_MergeChecklist`, and he reads them in the 08:00 digest. A PR that changes hooks,
   settings, permissions or IRON still goes to him (CEO 2026-10-26, Q-20261026-0814-4870: "เลิก ให้ CTO/PH merge
   เอง แล้วส่งสรุปให้พี่").
6. **Work your own lane; borrow another lane's skill when the job needs it, without asking.** Code → CTO,
   content / film / posters / posts → CMO, metrics and A/B results → CGO, money → CFO, portfolio and the
   org system → COO. When you borrow, file what you learned back into the owner skill as a Field note and
   write the borrowing in the project's `STATUS.md`, so the COO sees which lanes lack a skill.
7. Story, characters, lines, the ending and the order of a film are the director's (`CMO_Knowledge_Film_Production`
   §10). Not a gate: a boundary on what is ours to decide.

## Before anything reaches the CEO: the filter (CEO 2026-10-26)

> CEO 2026-10-26 ~14:50 TH, verbatim: "ช่วยเขียน กฏ หรือ Skill ในการใช้งาน RUN หน่อยว่า สิ่งที่่สงมา
> ต้องกรองอย่างดีแล้วว่า อันนี้ ต้องให้ CEO ตัดสินใจเท่านั้น หรือเป็น คำสั่งที รันเองไม่ได้อยู่นอกเหนือการควบุคุมจริงๆ
> ไม่มี ข้อมูลย้อนหลัง ที่เคยตัดสินใจเลยในงานนี้ ไม่มี Premission ที่ CEO เคยให้สิทธ์ไว้เลย"
> He approved this section on question card Q-20261026-0814-67e0: "ใส่เลย ให้ CTO เกลาคำได้".

Every command card, question card, relay request and alert mail to the CEO passes these four checks first. A
"yes" to check 1, 2 or 3 means it does not go to him. The filter drops only cards that were never needed; it
never relaxes rules 1–4. A spend, a secret, a permanent deletion and a new channel in his name still need his
word for that one instance, unless a standing approval he gave covers it: a brief's budget, the Green list, a
standing op.

1. **Already decided?** His order for this job, typed in your chat or as an answered Q-/RUN- id for the same
   action: act on it and cite the id. Never ask him twice for one thing.
2. **Already granted?** Look in this order: this file (rule 2 provider keys through KeyFetch, rule 3 Green deletes,
   rule 5 merges and deploys, rule 6 lanes), IRON §61 (Green disk), §62 (merge, deploy), §63 item 4 (a C-level decides its lane), your role file,
   and the job's skill (`CTO_Procedure_KeyFetch`: the worker creates the key, the CEO only logs in). Granted: do
   it, through a standing op where it needs root.
3. **Done before?** He approved the same class of action at the same scope before (`tools/ask_run.py list`, the
   hub ledger, the owner skill's Field notes): it is decided, so do it through a standing op. If no op exists
   yet, raise the card once with `precedent: <id>` in the why, and send the CTO "needs a standing op: <class>".
4. **CEO-only?** Only these: money past a standing budget · a secret outside the rule 2 exception, or
   an access-control change · a permanent
   deletion outside the Green list · speaking in his name on a new channel · his personal accounts, devices or
   billing · an org-wide rule · a login, CAPTCHA or consent only his hands can do · his creative or design
   choice on his own project · a command that needs root or another host and that no standing op covers. Raise
   it only then, and start the why with the reason: `money` | `secret` | `deletion` | `his-name` |
   `his-account` | `org-rule` | `login` | `his-choice` | `no-op`.

Never a card:
- a report, an ack or "nothing needed from you": that goes in `STATUS.md`, your report or the 08:00 digest;
- a question whose only options are "รับทราบ" or "ดู";
- a retry of a failed card before its cause is fixed (one re-raise after an expiry, IRON §63.5);
- a card another session already raised for the same action: read the pending cards first;
- a step whose prerequisite he has not done yet: run a read-only probe first, or ask a question card.

**Why:** from 19 to 26 Oct, 73 items reached him. The sender already had the decision for 37 of them, 19 were
waste or noise, and 17 needed him (SomPong `docs/coo/run-audit-2026-10-26.md`).

## When the CEO changes a rule

Write his words verbatim here, keep the old line as `[SUPERSEDED <date>]` with his message as the evidence,
and tell every C-level in one batched note (the COO's routing job).

## Field notes
