# FB Page to CREATE — ละครสั้นคุณธรรม by ILAG Studio

## 0. THE JOB IS TO CREATE A NEW PAGE. IT DOES NOT EXIST YET.

Read this before anything else, because the previous attempt (task-81437a70)
failed exactly here. That worker quietly changed the job from *create a page*
to *confirm a page exists*, found the unrelated `facebook.com/ILAGStudio`,
declared the task complete, and created nothing.

The CTO checked the account's own page list by hand at 11:40 on 2026-09-18.
This account manages exactly six pages, and **none of them is the one we want**:

```
ILAG Studio                          <- NOT it. Different page. Business page.
Chatudo                              <- NOT it.
BrandPrompt TH                       <- NOT it.
MoonieX TradeTech                    <- NOT it.
Mine-TH Network                      <- NOT it.
กอล์ฟ พัสกร : จิตวิทยาการเทรด          <- NOT it.
```

If at any point you catch yourself about to report "the page already exists",
you have matched the wrong page. The only name that counts is the exact string
in §2. Nothing similar, nothing related, nothing that merely contains "ILAG".

Every value below is **pre-verified** on a real Facebook page-creation form
(task-6c877cb0, 2026-09-17). Copy them EXACTLY. Do not improve, translate,
shorten or re-word anything. If a field rejects a value, stop and report the
exact rejection text — do not substitute.

## 1. The account — read it, do not gate on it

The logged-in Facebook account on this machine is named **Dorsine Gobb**.

(The CTO's earlier brief mis-spelled this as "Dorsign Gob". That was the CTO's
error, not a different account. Verified on the live page list: the header
reads `เพจที่ Dorsine Gobb จัดการ`.)

Report the name you actually read. If it is NOT `Dorsine Gobb`, stop and say
which account is logged in — a different identity in this household
(**PASAKON**) is banned from running ads, and a page created under it is
worthless to this business. Do not log anybody in or out; credentials are a
hard stop for this role.

## 2. Page name — paste verbatim, one line

```
ละครสั้นคุณธรรม by ILAG Studio
```

Verified: Facebook accepted this name with **no** duplicate/format warning.

## 3. Category

Type `Film` and pick the exact suggestion **Film**.

Already ruled out on the real form: `TV Show`, `Video Creator`, `Film Studio`
do not appear as selectable categories on this account's form. `Film` does.

## 4. Bio / คำอธิบาย — paste all three lines, 129 characters

```
ละครสั้นสะท้อนชีวิต เรื่องเงิน หนี้ และการถูกโกง
ทุกเรื่องเขียนขึ้นเองจากชีวิตจริง ผลิตด้วยเครื่องมือ AI
ตอนใหม่สัปดาห์ละ 1-2 ตอน
```

129 / 255 characters — under the cap, nothing gets truncated.

## 5. Do NOT do

- Do not upload a profile picture or cover photo. The brand art is not chosen
  yet (five concepts are still with the CEO). A page with the wrong art is
  worse than a page with none.
- Do not invite anyone, do not post anything, do not run any setup wizard step
  past creation.
- Do not add a website, phone number, or address.
- Do not touch any OTHER page on this account — above all not `ILAG Studio`.

## 6. What already failed, so you recognise it

On the Mac, under the PASAKON identity, this same form filled correctly and the
FINAL create click was refused with this exact banner:

```
We noticed suspicious activity: Finish SMS verification on mobile app before
creating a new page.
```

If the same banner appears on this machine, that is a real answer — quote it
verbatim and stop. It tells us the gate is account-wide rather than per-machine.
Do not attempt SMS verification and do not type a phone number anywhere.

## 7. Proof the page exists

A "created" toast is not proof, and neither is a page you merely found. After
creation, open the account's own page list at
`https://www.facebook.com/pages/?category=your_pages` and report:

- the **seventh** page name as it renders there (the six above, plus yours), and
- the new page's URL.

Six pages still listed = the page was not created, whatever the UI said.
