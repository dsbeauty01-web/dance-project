# MAYA — THE FULL COMMERCIAL PRODUCT MAP (founder, 2026-08-08)

The 9-layer map of the complete smart AI seller, with build order. Status legend:
✅ built · 🔶 partial · ❌ missing. This file is the founder's original, kept verbatim as
the roadmap of record; progress notes at the bottom.

## L1 — CONTENT (the bakes) 🔶
Per-client library: idle ×2-3 · gestures (10-15) · per-product showcase (5-min, cut to 15s
segments) · generic segments (greetings, transitions, urgency, thank-you-buyer, BRB) ·
tablet/panel composite. Plus the SCRIPT FACTORY ❌: LLM writes the 5-part script from the
client's product page → approval → TTS → bake. One n8n workflow.

## L2 — SHOW RUNNER (playlist engine) ✅ mostly
Gapless 15s-segment playlist, loop, live insertion, kill switch — built.
Missing 🔶: the RUNDOWN — a JSON stream plan (product order, offer minutes, time-of-day
script variant) the player follows.

## L3 — SELLER BRAIN (n8n) — was ❌, now 🔶 (W4 built, see notes)
Reads classified chat (W2 ✅), answers by name with catalog truth, ≤15s spoken.

## L4 — HER HANDS (tool belt) — was ❌, now 🔶
post_link · show_product ✅ (W4→/scene) · gesture · pin_offer · capture_lead ✅ (W3) ·
alert_operator 🔶 (blocked-claim path in W4).

## L5 — STAGE CONTROL (auto-director) ❌ — the differentiator
Rule engine, not a model: cluster questions → extend product block + batch answers ·
purchase → thank-you-by-name insertion · viewer jump → greeting+hook · scheduled offer →
REAL countdown · dead chat → rotate early. 智能场控 in Hebrew — the demo "wow".

## L6 — COMMERCE — was ❌, now 🔶 (schema done)
payment_link / coupon / in_stock now in the catalog schema. Missing: actual links from the
founder, orders webhook → thank-you moment + daily report, sold-out rundown removal.

## L7 — COMPLIANCE ✅ mostly (the moat)
Label in pixels ✅ · platform map ✅ · forbidden-claims: switchboard alert ✅ + W4
post-model block ✅ · operator takeover: console ✅ / loop-mode one-key 🔶 ·
per-client category screening = onboarding checklist.

## L8 — OPERATIONS ❌ — this is the ₪2-4K/month
Stream calendar (scheduled pod wake/auto-stream/auto-stop) · automated pre-flight ·
dashboard (console ✅ + queue monitor 🔶) · POST-STREAM REPORT auto-emailed (the renewal
machine) · monthly review.

## L9 — CLIENT FACTORY ❌ — the ₪8-15K setup
Onboarding kit: sheet template → script factory → voice/avatar pick → brand scene →
platform setup → bake → dress rehearsal → go-live. New client = clone n8n set + sheet +
bakes. Target 3 working days. Build only when client #2 signs.

## BUILD ORDER
1. L3+L4 minimal (brain + post_link/show_product) → M2 → DEMO RECORDING ← **in progress**
2. L6 attribution (coupon + orders sheet)
3. L8 report (auto post-stream email)
4. L1 script factory + L2 rundown
5. L5 stage control
6. L9 factory (after client #2)

Rule: brain and ops live in n8n (per-client cloneable); the pod stays a dumb mouth+face.

---

## PROGRESS NOTES (kept by the CLI)

- **2026-08-08:** W4 "seller brain" built + imported to n8n (id dtiKI9wJAbk3lWuK, inactive):
  webhook → catalog fetch → LLM (playbook persona, JSON out) → POST-MODEL GUARDS (word cap,
  forbidden-claims block with operator fallback, catalog-existence check) → /say by name +
  show_product→/scene. post_link is CTA-speech only until liveChatId plumbing exists
  (needs W1's cached id — wired in build-order step 2). Needs: OpenAI credential (same as
  W2), live pod URL at activation. Catalog schema got payment_link/coupon/in_stock.
