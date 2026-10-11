---
question: What can a fal.ai API key be limited to when it is created (scope, models, expiry, spend), and what shape is the key?
date: 2026-10-12
sources: [https://fal.ai/docs/documentation/model-apis/authentication/key-based.md, https://fal.ai/docs/platform-apis/v1/keys/create.md, https://fal.ai/docs/platform-apis/v1/keys/list.md, https://fal.ai/docs/llms.txt]
measured_by_us: no
refresh_after: 2027-01-10
confidence: high
---

# fal.ai API key options (docs, read 2026-10-12, task-494414fc)

Asked while preparing a per-project fal key for MoonieX-Bedrock (skill `CTO_Procedure_KeyFetch`).
What the live key page actually showed is in `docs/ops/keyfetch/fal.md`, once a run has used it.

## What the docs say

- **Key page:** `https://fal.ai/dashboard/keys`. The secret is shown once, at creation.
- **Key shape:** the create API returns `key_id` and `key_secret` as two fields. Clients send
  `Authorization: Key <key_id>:<key_secret>` (the `FAL_KEY` form). The list shows aliases and
  creation dates. No doc page says the list shows any part of the secret.
- **Permissions:** pick a **preset** or a **custom** list of permissions (names like
  `models:requests:submit`). Presets: `API` (submit/read/cancel/share model requests, catalog,
  files, short-lived tokens), `SERVERLESS`, `DEPLOY`, `COMPUTE`, `BILLING`, `READONLY`, `FULL`.
  `API` is the docs' choice for calling ready-made models.
- **Allowed models:** a tab in the create dialog. It limits the key to listed models, and the
  list cannot be changed after creation. Adding a model limit to a preset stores the key as a
  custom policy (a snapshot taken at creation).
- **Expiration:** from 1 hour to 1 year, or never. The list marks keys "Expiring soon" and "Expired".
- **Spend cap per key:** none of the docs pages mention one. Billing pages cover usage reports
  only. Treat it as "not offered" until the live page shows otherwise.
- **Platform API** (`https://api.fal.ai/v1/keys`): list, create and delete, `API`-preset keys
  only. Create needs `auth:keys:write`, which only the `FULL` preset has. So a script cannot
  mint a model-limited key through this API without a FULL key, and a FULL key is a wider
  credential than the task needs. The dashboard is the route.

## Durable

- The narrowest key that can run one hosted model through the queue is the `API` preset plus
  **Allowed models** holding just that model. That beats `API` on its own, which can call
  every model on the account.
