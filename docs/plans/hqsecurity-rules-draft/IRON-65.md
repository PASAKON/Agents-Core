# DRAFT: IRON-RULES Section 65. Not in force until the CTO merges it into Agents-Rules

Prepared by security_engineer task-0d3ec506 for PH HQSecurity #0de446ff (order O-20261027-1347-4e62). The PH
sends the text below to the CTO as a separate Agents-Rules PR. It goes after Section 64 in `IRON-RULES.md`. A PR
that changes IRON also goes to the CEO (`ALL_Rules_Approvals` rule 5).

Also in that PR: **amend §34 item 5.** It still reads "in every project including Org-Infra … Every project's keys
move into Org-Infra". The CEO replaced that on 2026-10-26 at 18:53 TH (Q-20261026-1118-4d3d: stay on the free plan,
each repo's project is the wall, nothing moves into Org-Infra). Proposed new text for item 5: "… in the key's own
repo project, never Org-Infra (Q-20261026-1118-4d3d) …". Keep the old line as `[SUPERSEDED 2026-10-26]`.

---

## Section 65 — Secrets: one home, named, scoped, expiring; a leak is rotated (CEO 2026-10-27, owner CTO)

> CEO 2026-10-27, order O-20261027-1347-4e62: *(the PH quotes his words verbatim from the order record here)*

> **The rule, every session and worker, every machine:**
> 1. **One home.** A key lives in the Infisical project named after its GitHub repo. `Org-Infra` holds only
>    org-wide account keys, and only the CEO enters them. Tools refuse Org-Infra, and nothing moves into it
>    on the free plan (Q-20261026-1118-4d3d). No new `.env`, and no new line in an old one.
> 2. **Named before it exists.** Variable `<PROVIDER>_[<WHICH>_]<KIND>[_<ACCESS>]`. Provider page
>    `<brand>-<project>-<env>-<access>-exp<YYYY-MM-DD>`, at most 40 characters. Metadata: purpose,
>    `provider_name`, `console_url`, `scope`, `expires`, `owner`. The KeyFetch script refuses a write without
>    them before it clicks.
> 3. **Scoped.** The smallest scope the provider offers. Read-only unless the job writes. One key per
>    project, never one value shared across projects.
> 4. **Expiring.** The expiry is set at the provider whenever it offers one. Otherwise `expires=none-offered`
>    and a rotate-by date in the page name. The date reaches the CEO's deadline feed 14 days early.
> 5. **Read only by the process that uses it**, through `infisical run` or the org wrappers. Never from
>    `/etc/infisical/*`, `/proc/*/environ` or a printed environment. A stub under a wrapper prints argc only.
> 6. **Fetched only through `CTO_Procedure_KeyFetch`.** The login goes through the relay (§60). The value goes
>    from the page into Infisical, and no model sees it.
> 7. **A leak is rotated forward at once.** A leak is a value in chat, a screenshot, a log, a commit, a card,
>    a letter, a prompt or a transcript. The steps: tag `leaked` → new key → Infisical → verify the consumer
>    → revoke the old key → a look-back of who saw it, plus one registry Changelog line (§34).
> 8. **Revoke only after the replacement is verified.** If another lane uses the key, tell that lane first.
>    A key that is being abused right now is revoked first.
> 9. **Leak guards stay on, and none is bypassed:** gitleaks before commit and push, GitHub secret scanning
>    and push protection on the public repos, the session hook, Run card redaction.
>
> The full text, with what each rule protects: Agents-Core skill `ALL_Rules_Secrets`.

**Why.** `CLAUDE.md` §Secrets and PLAN.md already held these rules, spread over four documents, and §34 item
5 still pointed at Org-Infra after the CEO's free-plan ruling. Measured on 2026-09-25 (PLAN §1):
- one variable name held three different bots' tokens;
- at least seven values were shared between two projects;
- seven leaked keys were still live;
- three keys expired with no warning.

On 2026-10-26 a fake binary under the hub wrapper printed the real database URL, and the password had to be
rotated. On 2026-10-27 both public repos had GitHub secret scanning and push protection off. Recorded by
security_engineer task-0d3ec506 for PH HQSecurity #0de446ff.
