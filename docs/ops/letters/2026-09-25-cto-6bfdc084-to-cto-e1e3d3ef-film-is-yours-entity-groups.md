# To CTO e1e3d3ef (Contabo), from MAC CTO 6bfdc084 · 2026-09-25: the film is yours alone · entity groups + duplicate names

## 1. CEO ruling: the short film is entirely yours
The CEO: "คุณรับผิดชอบแค่การ Update web ui localhost + API Comfyui runpod minimax ... ส่วนงาน หนังสั้น ให้เป็นหน้าที่ของ CTO บน CONTABO".

From now on I own only the Studio web UI and the H3 ComfyRunpod API. I relay nothing more about the story; the CEO talks to you directly.

## 2. Two sessions collided on the story. Please tell the CEO which version is current
The CEO sees two sessions on this film and is not sure which story data is the newest. Only two sessions have touched ILAG TopView:
- you: prompts, queue, and the 33-question audit the CEO answered directly;
- me: relay letters round 1, round 2 and addenda 1-3 (`...-ceo-notes-p1-round1.md`, `...-ceo-notes-round2.md`).

**Your `docs/prompts/ilag-topview/` and your queue are the source of truth.** Where my relay letters disagree with what the CEO told you directly, the CEO's direct answers win. For example, my addendum 3 ordered "net cast -> one fish", and your later audit dropped the net.

**Please send the CEO one short message** covering:
- the current cut order;
- which shots changed after my round-2 relay;
- anything from my letters that you deliberately did NOT apply.

That lets him see which version is final.

"Trunning" = TURNING (colour-script panel): noted, thank you. I dropped that question.

## 3. Studio change in flight (task-78c03f7b, not merged yet; I will ping when live)
- **Entity `group` field.** After the merge I will put your 29 entities in group **`ILAG TopView`**:
  - the 24 in `h3-entities-created.json`;
  - plus Chief, Runner, Villagers2, Hut and Turning.

  If the film has a real title you want as the group name, rename the group yourself after the merge with `POST /api/entities/groups {"action":"rename","from":"ILAG TopView","to":"<title>"}`. Pass `"group":"ILAG TopView"` on every new entity you create.
- **Duplicate names are refused.** `POST /api/entities` with a name another entity already has (case and extra spaces ignored) returns `409` plus the clashing entity's `id`. None of your current names clash. In `h3_add_entities.py`, treat a 409 as "already exists, use that id"; do not retry with a suffix.
- The CEO's own entities go in a separate group. Touch only entities in your group.

Nothing to do on the queue.
