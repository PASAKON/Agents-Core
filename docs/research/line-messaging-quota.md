# LINE Messaging API Quota, Rate Limits, and 80% Alert Calculation

## Overview

This document covers how the LINE Messaging API tracks monthly message quotas, how monthly limits vary by plan and region, which message types consume quota (and why `reply` messages do not), endpoint throughput rate limits and HTTP `429 Too Many Requests` handling, and how to compute a deterministic 80% quota alert.

- **Scope:** LINE Official Account (LINE OA) Messaging API (`https://api.line.me/v2/bot/message/...`).
- **Out of Scope:** Personal LINE desktop automation (`CXO_Knowledge_LINE_Messaging`) and retired LINE Notify.

---

## 1. Quota & Consumption Endpoints

Both endpoints require a valid Channel Access Token passed via the `Authorization: Bearer <channel_access_token>` HTTP header.

### 1.1 `GET /v2/bot/message/quota` — Get Target Monthly Limit

Retrieves the target message limit configured for the LINE Official Account in the current calendar month.

- **Method & URL:** `GET https://api.line.me/v2/bot/message/quota`
- **Official Reference:** <https://developers.line.biz/en/reference/messaging-api/#get-quota>
- **Rate Limit:** 2,000 requests/second (categorized under *Other API endpoints*).

#### Response Format (`200 OK`)

```json
{
  "type": "limited",
  "value": 15000
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `type` | `string` | `"limited"` if the account has a monthly numeric message limit; `"none"` if no target limit is set. |
| `value` | `integer` | *(Present only when `type` is `"limited"`)* The maximum number of quota-consuming messages allowed in the current month (base plan quota plus any additional-message cap configured in LINE Official Account Manager). |

> **Operational Note:** On paid plans that permit overage/additional messages (e.g., Thailand Basic/Pro, Japan Standard), `value` reflects the **target limit configured by the account administrator** in the LINE Official Account Manager (which equals the base free quota if additional messages are set to `0`, or Base + Additional Ceiling if overages are enabled).

---

### 1.2 `GET /v2/bot/message/quota/consumption` — Get Current Month Usage

Retrieves the cumulative number of quota-consuming messages sent by the channel during the current calendar month.

- **Method & URL:** `GET https://api.line.me/v2/bot/message/quota/consumption`
- **Official Reference:** <https://developers.line.biz/en/reference/messaging-api/#get-consumption>
- **Rate Limit:** 2,000 requests/second (categorized under *Other API endpoints*).

#### Response Format (`200 OK`)

```json
{
  "totalUsage": 12050
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `totalUsage` | `integer` | Total number of quota-consuming message deliveries sent month-to-date. |

---

## 2. Monthly Message Limits per Plan

LINE Official Account subscription plans and free message allowances are country-specific. Always query `GET /v2/bot/message/quota` at runtime rather than hardcoding plan constants.

- **Official Pricing Overview:** <https://developers.line.biz/en/docs/messaging-api/pricing/>
- **Thailand Official Plan Page:** <https://lineforbusiness.com/th/service/line-oa-features>
- **Japan Official Plan Page:** <https://www.lycbiz.com/jp/service/line-official-account/plan/>

### 2.1 Thailand (`THB`, excluding 7% VAT)

| Plan | Monthly Fee (THB) | Included Free Messages / Month | Additional Messages Beyond Quota |
| :--- | :--- | :--- | :--- |
| **Free** | 0 THB | **300** *(Note: legacy pre-revision docs cited 1,000; treat 1,000 as superseded/unverified unless returned by `GET /v2/bot/message/quota`)* | **Not allowed** (hard stop at 300) |
| **Basic** | 1,280 THB | **15,000** | **0.10 THB / message** (up to admin-configured target limit) |
| **Pro** | 1,780 THB | **35,000** | **0.06 THB / message** *(high-volume tiered discounts unverified without live OA Manager billing table)* |

### 2.2 Japan (`JPY`, excluding consumption tax)

| Plan | Monthly Fee (JPY) | Included Free Messages / Month | Additional Messages Beyond Quota |
| :--- | :--- | :--- | :--- |
| **Communication (Free)** | 0 JPY | **200** | **Not allowed** (hard stop at 200) |
| **Light** | 5,000 JPY | **5,000** | **Not allowed** (hard stop at 5,000) |
| **Standard** | 15,000 JPY | **30,000** | **Allowed** (tiered progressive pricing starting up to ~3.0 JPY/message; exact volume brackets unverified) |

### 2.3 Taiwan & Other Regions *(Secondary Reference)*

| Region | Plan Tiers & Included Monthly Messages | Additional Messages | Verification Status |
| :--- | :--- | :--- | :--- |
| **Taiwan (`TWD`)** | **Light (Free):** 200 msgs (NT$0)<br>**Medium:** 3,000 msgs (NT$1,000)<br>**High:** 6,000 msgs (NT$1,400) | Allowed on **High** plan only (~NT$0.2/msg tiered) | **Unverified** against live 2026 TW OA Manager portal |
| **Global / Other (US, SG, ID)** | **Free / Communication:** 200–500 msgs | Paid upgrades generally unavailable | **Unverified** (varies by account creation date and country) |

---

## 3. Do Reply Messages Count Toward the Monthly Quota?

**No. Reply messages (`POST /v2/bot/message/reply`) do NOT count toward the monthly message quota.**

### 3.1 Message Types and Quota Accounting

| Message Delivery Method | Endpoint / Surface | Counts Toward Monthly Quota? | Notes |
| :--- | :--- | :--- | :--- |
| **Reply Message** | `POST /v2/bot/message/reply` | **NO (Free)** | Requires a single-use webhook `replyToken` (expires shortly after webhook event generation). |
| **1-on-1 Manual Chat** | LINE OA Manager Chat UI | **NO (Free)** | Manual human agent responses in 1-to-1 chat. |
| **Greeting Message** | LINE OA Manager Settings | **NO (Free)** | Sent automatically when a user adds the OA as a friend. |
| **Auto-Response Message** | LINE OA Manager Settings | **NO (Free)** | Keyword/schedule rule-based replies configured in OA Manager. |
| **Push Message** | `POST /v2/bot/message/push` | **YES** | Consumes **1 message per recipient** (or per member in a group/multi-person room). |
| **Multicast Message** | `POST /v2/bot/message/multicast` | **YES** | Consumes **1 message per recipient** in the `to` array (up to 500 user IDs per request). |
| **Broadcast Message** | `POST /v2/bot/message/broadcast` | **YES** | Consumes **1 message per targeted friend** who receives the broadcast. |
| **Narrowcast Message** | `POST /v2/bot/message/narrowcast` | **YES** | Consumes **1 message per targeted recipient** matching the demographic/audience filter. |

- **Official Reference:** <https://developers.line.biz/en/docs/messaging-api/pricing/> and <https://developers.line.biz/en/reference/messaging-api/#send-reply-message>

### 3.2 Recipient vs. Bubble Counting Rule

- **1 API call with up to 5 message objects (bubbles) to 1 user = 1 quota unit consumed.**
  Batching up to 5 message objects into a single `messages` array in `POST /v2/bot/message/push` consumes only **1** message from the monthly quota per recipient.
- **Group / Multi-person Chats:** Sending a single `POST /v2/bot/message/push` to a `groupId` or `roomId` consumes quota equal to the **number of users in that group or room**, even though it is a single HTTP request (<https://developers.line.biz/en/reference/messaging-api/#send-push-message>).

---

## 4. Push Rate Limits and HTTP `429` Handling

### 4.1 Throughput Rate Limits per Endpoint

LINE enforces rate limits **per channel, per endpoint** using a **token bucket algorithm** (tokens refill continuously rather than resetting on a fixed clock boundary).

- **Official Rate Limits Table:** <https://developers.line.biz/en/reference/messaging-api/#rate-limits>

| Endpoint | HTTP Path | Official Rate Limit | Notes |
| :--- | :--- | :--- | :--- |
| **Send Push Message** | `POST /v2/bot/message/push` | **2,000 requests / second** | Covered under *"Other API endpoints"*. *(Per-recipient burst anti-spam threshold is undocumented/unverified.)* |
| **Send Reply Message** | `POST /v2/bot/message/reply` | **2,000 requests / second** | Covered under *"Other API endpoints"*. |
| **Get Quota / Consumption** | `GET /v2/bot/message/quota*` | **2,000 requests / second** | Covered under *"Other API endpoints"*. |
| **Send Multicast Message** | `POST /v2/bot/message/multicast` | **200 requests / second** | Up to 500 user IDs per request. *(One third-party source claims 10 req/s; treat 10 req/s as unverified/erroneous vs. LINE's 200 req/s table.)* |
| **Send Broadcast Message** | `POST /v2/bot/message/broadcast` | **60 requests / hour** | Stricter bucket; avoid rapid polling/retries. |
| **Send Narrowcast Message** | `POST /v2/bot/message/narrowcast` | **60 requests / hour** | Stricter bucket; shares the 60 req/hr tier. |

### 4.2 Two Distinct Causes of HTTP `429 Too Many Requests`

- **Official Status Codes & Error Responses:**
  - <https://developers.line.biz/en/reference/messaging-api/#status-codes>
  - <https://developers.line.biz/en/reference/messaging-api/#error-responses>

When the LINE Messaging API returns HTTP `429 Too Many Requests`, you **must inspect the JSON response body (`message`)** to distinguish between transient rate limiting and monthly quota exhaustion:

| Cause | Typical HTTP `429` JSON Body | Retryable? | Required Action |
| :--- | :--- | :--- | :--- |
| **1. Throughput Rate Limit (Token Bucket Depleted)** | `{"message": "The API rate limit has been exceeded. Try again later."}` | **Yes** | Back off with **exponential backoff + jitter** (e.g., 1s, 2s, 4s, 8s). LINE does **not** reliably send a `Retry-After` header. |
| **2. Monthly Quota Exhausted (Hard Monthly Cap Reached)** | `{"message": "You have reached your monthly limit."}` | **No** | **Stop sending quota-consuming messages immediately.** Retrying will fail until the monthly billing reset or plan/limit upgrade. Note that `reply` messages continue to work. |

### 4.3 Safe Retry & Idempotency (`X-Line-Retry-Key`)

- **Official Reference:** <https://developers.line.biz/en/reference/messaging-api/#retry-api-request>
- For `push`, `multicast`, `broadcast`, and `narrowcast`, LINE supports an optional header:
  ```http
  X-Line-Retry-Key: <UUIDv4>
  ```
- If a request times out or fails with a `5xx` error and is retried with the same UUID within 24 hours, LINE guarantees idempotency (returning `409 Conflict` if the earlier attempt actually succeeded).
- *Note (Unverified edge case):* LINE documents `X-Line-Retry-Key` primarily for `5xx` and network timeout recovery. Because a `429` rejects the request before delivery, generating a fresh retry key or reusing the same key after a `429` is not explicitly contrasted in the spec (mark `429` key-reuse semantics as **unverified**; handle `409 Conflict` as a successful duplicate suppression if reusing keys).

---

## 5. How to Compute an 80% Quota Alert

### 5.1 Alert Logic & Edge Cases

1. **Fetch current quota and consumption:**
   - Call `GET /v2/bot/message/quota` $\rightarrow$ parse `type` and `value`.
   - Call `GET /v2/bot/message/quota/consumption` $\rightarrow$ parse `totalUsage`.
2. **Guard against unlimited / unconfigured plans:**
   - If `type != "limited"` or `value <= 0`, percentage alerting does not apply.
3. **Exact integer math for the 80% threshold:**
   - Avoid floating-point drift by computing either:
     $$\text{is\_alert} = (\text{totalUsage} \times 100 \ge 80 \times \text{value})$$
     or the exact message count threshold:
     $$\text{threshold}_{80} = \lceil 0.80 \times \text{value} \rceil = \lfloor (\text{value} \times 80 + 99) / 100 \rfloor$$
   - **Examples by Thailand Plan:**
     - **Free (`value = 300`):** 80% threshold = **240 messages** (`60` remaining).
     - **Basic (`value = 15,000`):** 80% threshold = **12,000 messages** (`3,000` remaining).
     - **Pro (`value = 35,000`):** 80% threshold = **28,000 messages** (`7,000` remaining).
4. **Pre-send batch check (`projectedUsage`):**
   - Before sending a push/multicast to $N$ recipients, check `projectedUsage = totalUsage + N`.
   - If `projectedUsage >= threshold_80`, fire the 80% warning alert.
   - If `projectedUsage > value`, halt the batch before hitting HTTP `429` mid-flight.
5. **Deduplication (Fire Once per Billing Month):**
   - Key the alert state by `(channel_id, YYYY_MM, value, "80pct")` so the alert triggers once when crossing 80%, and re-arms automatically on the 1st of the next month or if the admin raises `value` in OA Manager. *(Note: Monthly quota resets on the 1st of the calendar month at 00:00 in the account's registered local timezone, e.g., ICT `UTC+7` for Thailand / JST `UTC+9` for Japan — mark exact reset second/timezone for non-TH/JP regions as unverified.)*

### 5.2 Reference Python Calculation (Token-Safe)

```python
from dataclasses import dataclass
import math
from typing import Any, Mapping


@dataclass(frozen=True)
class QuotaStatus:
    quota_type: str
    limit: int | None
    used: int
    projected_used: int
    threshold_80: int | None
    usage_pct: float | None
    projected_pct: float | None
    alert_80: bool
    would_exceed_100: bool


def evaluate_line_quota(
    quota_resp: Mapping[str, Any],
    consumption_resp: Mapping[str, Any],
    pending_recipients: int = 0,
) -> QuotaStatus:
    """Evaluate LINE Messaging API monthly quota and 80% alert threshold.

    Args:
        quota_resp: Parsed JSON from GET /v2/bot/message/quota
        consumption_resp: Parsed JSON from GET /v2/bot/message/quota/consumption
        pending_recipients: Number of recipients about to be messaged in the next batch.
    """
    if pending_recipients < 0:
        raise ValueError("pending_recipients must be >= 0")

    quota_type = str(quota_resp.get("type", "none"))
    used = int(consumption_resp.get("totalUsage", 0))
    projected_used = used + pending_recipients

    if quota_type != "limited" or not quota_resp.get("value"):
        return QuotaStatus(
            quota_type=quota_type,
            limit=None,
            used=used,
            projected_used=projected_used,
            threshold_80=None,
            usage_pct=None,
            projected_pct=None,
            alert_80=False,
            would_exceed_100=False,
        )

    limit = int(quota_resp["value"])
    threshold_80 = math.ceil(limit * 0.80)
    usage_pct = round((used / limit) * 100.0, 2)
    projected_pct = round((projected_used / limit) * 100.0, 2)

    # Exact integer comparison: projected_used * 100 >= 80 * limit
    alert_80 = (projected_used * 100) >= (80 * limit)
    would_exceed_100 = projected_used > limit

    return QuotaStatus(
        quota_type=quota_type,
        limit=limit,
        used=used,
        projected_used=projected_used,
        threshold_80=threshold_80,
        usage_pct=usage_pct,
        projected_pct=projected_pct,
        alert_80=alert_80,
        would_exceed_100=would_exceed_100,
    )
```

---

## 6. Cited Sources

1. **LINE Messaging API Reference — Get target limit for sending messages this month (`GET /v2/bot/message/quota`):**  
   <https://developers.line.biz/en/reference/messaging-api/#get-quota>
2. **LINE Messaging API Reference — Get number of messages sent this month (`GET /v2/bot/message/quota/consumption`):**  
   <https://developers.line.biz/en/reference/messaging-api/#get-consumption>
3. **LINE Messaging API Reference — Send reply message (`POST /v2/bot/message/reply`):**  
   <https://developers.line.biz/en/reference/messaging-api/#send-reply-message>
4. **LINE Messaging API Reference — Send push message (`POST /v2/bot/message/push`):**  
   <https://developers.line.biz/en/reference/messaging-api/#send-push-message>
5. **LINE Messaging API Reference — Rate limits (`#rate-limits`):**  
   <https://developers.line.biz/en/reference/messaging-api/#rate-limits>
6. **LINE Messaging API Reference — Status codes & Error responses (`#status-codes`, `#error-responses`):**  
   <https://developers.line.biz/en/reference/messaging-api/#status-codes>  
   <https://developers.line.biz/en/reference/messaging-api/#error-responses>
7. **LINE Messaging API Reference — Retry an API request (`X-Line-Retry-Key`):**  
   <https://developers.line.biz/en/reference/messaging-api/#retry-api-request>
8. **LINE Developers Documentation — Messaging API Pricing:**  
   <https://developers.line.biz/en/docs/messaging-api/pricing/>
9. **LINE for Business Thailand — LINE Official Account Packages (Free / Basic / Pro):**  
   <https://lineforbusiness.com/th/service/line-oa-features>
10. **LY Corporation (Japan) — LINE Official Account Pricing Plans (Communication / Light / Standard):**  
    <https://www.lycbiz.com/jp/service/line-official-account/plan/>
