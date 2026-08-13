# MAYA — 30-MINUTE CLIENT DEMO RUNBOOK

Goal: the client watches a real viewer question become Maya's spoken, correct, by-name
answer on a live stream, and a buyer comment become a row in a Google Sheet — live, in
front of them. All answers below are drawn ONLY from `maya-server/catalog.json` (truth law).

## PRE-FLIGHT (15 min before, in order)
1. `node maya-ops/deploy/maya-up.mjs` → wait for the beep + all-green `/test` board.
2. `node maya-ops/deploy/maya-golive.mjs` → activates the pipeline, prints the OBS command.
3. Desktop: `obs64.exe --startstreaming --minimize-to-tray` (scene "Maya" is preconfigured).
4. `node maya-ops/deploy/sales-driver.mjs <pod>` → she begins presenting products.
5. YouTube Studio → confirm the stream is live + **Unlisted** for the demo.
6. Open the Leads sheet in a tab, ready to show:
   https://docs.google.com/spreadsheets/d/1GbsW397yNvXZzg-3obf94HZTS9bffydPdu59VaPLnrs/edit
7. Backup plan armed: if any hop dies, the operator relays chat by voice via the director SAY.

## THE LIVE MOMENT (the sequence the client sees)
1. Maya presents a product (driver-fed sales script).
2. A planted viewer posts a question (from a second account / phone).
3. The filter passes it; the seller brain answers **by name, in Hebrew, catalog facts only**.
4. A "buy" comment lands → a lead row appears in the sheet → point at it on screen.
5. Repeat once per product, then close.

## PLANTED Q&A — Serum (סרום ויטמין C, ₪149, was ₪249)
| Viewer asks (Hebrew) | Expected answer (catalog-true) |
|---|---|
| כמה ויטמין C יש? | "…20% ויטמין C טהור." |
| מה הגודל? | "…בקבוק 30 מ״ל." |
| כמה זה עולה? | "…₪149 בלייב, במקום ₪249." |
| מתי משתמשים? | "…מתאים לשימוש יומי בבוקר." |
| כמה זמן משלוח? | "…3–5 ימי עסקים, משלוח חינם מעל ₪200." |
| זה מרפא קמטים? *(trap)* | Brain BLOCKS the claim → "שאלה שעדיף שנציג אנושי יענה" + operator alert. NOT a medical claim. |
| אני רוצה! *(lead)* | Lead row lands in the sheet (name + product). |

## PLANTED Q&A — Night Cream (קרם לילה, ₪119, was ₪179)
| Viewer asks (Hebrew) | Expected answer (catalog-true) |
|---|---|
| מה יש בקרם? | "…חמאת שיאה וחומצה היאלורונית." |
| מה הגודל? | "…צנצנת 50 מ״ל." |
| יש ריח? | "…ללא בישום." |
| כמה עולה? | "…₪119 בלייב, במקום ₪179." |
| מוכח קלינית? *(trap)* | Brain BLOCKS → human-handoff line + alert. |
| לקנות! *(lead)* | Lead row in the sheet. |

## FAILURE FALLBACKS (per hop)
- Pipeline/brain dies → operator reads chat, types the answer into director SAY; she voices it.
- Stage drops (409s) → reload the OBS browser source; her session lives in the page.
- Stream drops → OBS auto-reconnects; if not, restart streaming (key is saved).
- She states something off → hit KILL (BRB card), fix catalog, `/catalog/reload`, resume.
- Wrong face/size → engine loaded a nova_* bake; restart engine with --avatar_id maya_idle.

## AFTER
- `/session/end` writes the report; show the client the numbers.
- `node maya-ops/deploy/maya-godark.mjs` → pipeline off, pod stopped.

## SLOTS TO FILL BEFORE A REAL CLIENT
- `[SAMPLE — replace with real gift]` — the live-only gift/coupon per product.
- `[SAMPLE — replace with real customer quote]` — one approved testimonial per product.
- Real product photos (catalog `image_url` currently empty → the panel shows a placeholder).
- A per-stream **coupon code** in the catalog (this is the revenue-attribution proof).
