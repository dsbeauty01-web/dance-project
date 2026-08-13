# Pipeline — REAL fix + proof, 2026-08-13 (pod-free)

## TL;DR
The pipeline was **activated but silently broken**. Three real bugs would have made
every live message vanish — even with the pod up. All three are **found, fixed, and
proven pod-free**. Only the two hops that physically need the GPU (deliver-to-brain,
director toast) remain to confirm on next bring-up; their payloads are verified correct.

## The three bugs (all fixed)
1. **W3 "Append to Sheets" was a placeholder** — `resource: spreadsheet`, no documentId,
   no append op, no mapping. Leads never wrote to the sheet, ever.
   → Rewrote as a proper append (documentId = leads sheet id, tab `Leads`, autoMap of
   `ts/platform/name/handle/product/message`). **Proven: a test lead wrote row 3.**
2. **W3 "Lead?" never saw the message** — the CONFIG (Set) node between the webhook and
   Lead? drops incoming fields, so `j.text` was empty → every lead returned `[]`.
   → Lead? now reads `$('Webhook').first().json.body` directly. **Proven: buy-intent detected.**
3. **W2 "Filter spam/abuse" dropped ALL messages** — same CONFIG-strips-body cause; the
   filter read `$input` (= CONFIG output, no messages) → `raw = []` → nothing ever reached
   the classifier or the brain. This is why earlier tests showed "0 in."
   → Filter now reads `$('Webhook').first().json.body`. **Proven: 3 msgs classified + ranked.**

Plus: **W2 webhook 500 fixed** — `responseMode: lastNode` on a two-terminal flow can't
pick a node to respond with → 500. Changed to `onReceived` (respond immediately; correct
for a fire-and-forget ingest). Webhook now returns 200.
Plus: **W3 director-toast hardened** (`continueOnFail`) so a pod/director hiccup can never
block a lead from being recorded.

## What was PROVEN this session (no pod, real n8n executions)
- **W2 front half:** webhook 200 → Filter passes clean msgs → OpenAI Classify ok →
  Prioritize output (exec 39987):
  - `buy_intent` — "אני רוצה את הסרום!" (רות)
  - `question_shipping_price` — "כמה עולה הסרום?" (יוסי)
  - `question_product` — "כמה ויטמין C יש בסרום?" (דנה)
  - spam ("זבל www.spam.com") correctly dropped.
- **W3 leads:** POST to `/webhook/maya-lead` → Lead? detects buy-intent → Append to Sheets
  **ok** → confirmed by reading the sheet back: row 3 = `רות בדיקה | serum-c | אני רוצה את הסרום!`.
- **Links verified:** W2 `→ W3 lead capture` posts the full item; W2 `→ /chat-in` posts
  `{platform,msg_id,name,text,lang,priority}` — both correct.
- Sheet cleaned afterward (junk + test rows removed; headers kept). Sheet is pristine.

## Remaining (needs pod — high confidence, payloads verified)
- W2 `→ maya-server /chat-in` — deliver ranked msg to the brain (404 now only because pod off).
- W4 seller-brain answer-by-name in Hebrew.
- W3 `→ director toast` — the on-screen lead toast (hardened; won't block the row).

## To finish on next bring-up (~10 min)
1. `maya-up` → `maya-golive` (activates W2/W3/W4, re-points CONFIG to the new pod).
2. `node scratchpad/fire-test.mjs` (update POD id first).
3. Expect: brain answers דנה/יוסי by name in Hebrew + a `רות` row in the Leads sheet.

## Source of truth
Fixed workflow definitions exported to `maya-ops/n8n/*.json` (importable).
Pre-fix backups: `scratchpad/wf-backup/*.json`.
