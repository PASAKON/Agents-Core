---
question: Which official APIs let a model-free spend monitor read balance/usage and cut spend on OpenRouter, fal.ai and Google Cloud, with what key type?
date: 2026-10-13
sources: [https://openrouter.ai/docs/openapi/openapi.yaml, https://openrouter.ai/docs/api/api-reference/credits/get-credits, https://openrouter.ai/docs/api-reference/limits, https://openrouter.ai/docs/guides/overview/auth/management-api-keys, https://openrouter.ai/docs/cookbook/administration/analytics-cost-control.md, https://fal.ai/docs/platform-apis/v1/account/billing, https://fal.ai/docs/platform-apis/v1/models/usage.md, https://fal.ai/docs/platform-apis/v1/keys/create.md, https://fal.ai/docs/platform-apis/v1/keys/revoke.md, https://fal.ai/docs/api-reference/platform-apis/authentication.md, https://fal.ai/docs/documentation/model-apis/faq, https://docs.cloud.google.com/billing/docs/how-to/budgets-programmatic-notifications, https://docs.cloud.google.com/billing/docs/how-to/disable-billing-with-notifications]
measured_by_us: no — docs + OpenRouter OpenAPI spec read 2026-10-13 (no key, no call made)
refresh_after: 2027-01-11
confidence: high (OpenRouter from the spec itself), medium (fal, GCP from WebFetch page summaries)
---

# Spend-monitor APIs — OpenRouter, fal.ai, Google Cloud (docs only)

## OpenRouter — base https://openrouter.ai/api/v1, `Authorization: Bearer <key>`
"Management key" = the old "provisioning key" (spec keeps `is_provisioning_key`, described "Whether this is a management key"). Management keys cannot run inference.
- `GET /credits` — MANAGEMENT key; normal key → 403 "Only management keys can perform this operation". `{data:{total_credits, total_usage}}`; no remaining field (compute total_credits − total_usage). Unit not stated on page (USD by convention). Whether it once accepted normal keys: UNCONFIRMED.
- `GET /key` — any key (reports on itself). Fields: label, limit, limit_remaining, limit_reset, include_byok_in_limit, usage, usage_daily/weekly/monthly, byok_usage(+_daily/_weekly/_monthly), is_free_tier, is_management_key, is_provisioning_key, free_model_daily_requests{used,limit,remaining}, budgets[] + effective_budget {scope, guardrail_id, budget_id, limit_usd, spend_usd, remaining_usd, reset_interval, resets_at, include_byok}, expires_at, creator_user_id, organization_id, workspace_id, allowed_data_regions, rate_limit (deprecated). All USD. Windows = UTC calendar (day; week Mon–Sun; month), not rolling.
- `GET /keys` — MANAGEMENT. Query: include_disabled, include_expired, offset (no page-size param), workspace_id (default workspace only by default). Per key: hash, name, label, disabled, limit, limit_remaining, limit_reset, include_byok_in_limit, usage(+daily/weekly/monthly), byok_usage(+…), created_at, updated_at, last_used_at, expires_at, external_user, creator_user_id, workspace_id. USD, UTC calendar windows. Documents 429, no numbers.
- `PATCH /keys/{hash}` — MANAGEMENT. Body (unknown fields ignored; none → 400 "No update fields provided"): disabled, limit (USD|null), limit_reset (daily|weekly|monthly|null, resets 00:00 UTC), include_byok_in_limit, name, workspace_id. Returns `{data:{<key object>}}`. Also GET/DELETE /keys/{hash}. 429 documented, limits not published.
- Burn rate: `POST /analytics/query` (MANAGEMENT) metrics e.g. total_usage (USD), granularity minute|hour|day|week|month, time_range ISO with seconds, ≤2 dimensions (model, api_key_id …); `GET /analytics/meta` lists metrics. `GET /activity` (MANAGEMENT) = daily rows, last 30 completed UTC days only. `GET /generation?id=` = one generation's total_cost; no management-key note.

## fal.ai — base https://api.fal.ai/v1, `Authorization: Key <key>`
Keys carry permission presets (FULL, AGENT, API, DEPLOY, READONLY, BILLING, COMPUTE, SERVERLESS) or explicit permissions; default API.
- `GET /account/billing?expand=credits` → `{username, credits:{current_balance, currency}}`. Needs billing:usage:read (BILLING, READONLY, FULL).
- `GET /models/usage` — needs billing:usage:read + auth:keys:read + account:users:read (BILLING or FULL). Query start/end (default last 24 h), timeframe minute|hour|day|week|month, timezone, endpoint_id, api_key_id, login_username, source estimate|tagged-estimate, expand time_series|summary|auth_method|auth_method_structured, limit, cursor. Rows: endpoint_id, unit, quantity, unit_price, percent_discount, cost_subtotal, cost_discount, cost_total, currency. Lag of `estimate`: UNCONFIRMED.
- Keys: `POST /keys` (auth:keys:write, FULL only) body alias, description, preset|permissions, expires_at — no spend-limit field. `POST /keys/{key_id}/revoke` → 204, irreversible, no disable/pause.
- Spend limit: none in the API. Prepaid credits; account locks below a "lock threshold" (enterprise invoice accounts exempt). A dashboard spend cap or auto top-up: UNCONFIRMED.

## Google Cloud
Budget on a billing account + Pub/Sub topic connected to it. Roles: Billing Account Costs Manager or Administrator (billing.budgets.*) + Pub/Sub Admin on the topic project (pubsub.topics.setIamPolicy). Messages several times a day (not only on threshold), at-least-once: costAmount, budgetAmount, alertThresholdExceeded, forecastThresholdExceeded, currencyCode, costIntervalStart, budgetDisplayName. Budgets only notify. Cap = documented Cloud Run function that unlinks the project's billing account via the Cloud Billing API (sample grants roles/billing.admin); stops every service, resources may be deleted, cost data lags so spend can overshoot.
