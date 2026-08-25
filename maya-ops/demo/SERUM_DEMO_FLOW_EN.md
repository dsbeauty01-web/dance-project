# SERUM DEMO FLOW — ONE BLOCK, ~6.5 MIN, REPEATABLE (EN)

Avatar: `maya_serum` (MuseTalk live lips) · AI label burned in · KILL switch armed
Scenes: PRESENT (baked base) · CUT_APPLY · CUT_EXAMINE · price banner overlay
Price: **₪149 live (was ₪249)** — single source of truth: `maya-ops/loop/scripts/serum-c.en.json`.
Answer rule: name first, catalog facts only, max 2 answers/min (8s cue rate-limit).

> STATUS 2026-08-25: `maya_serum` bake is **pending STEP 2 pod session** (source `serum_present_src.mp4`
> is QC'd BAKE-READY). Until it exists, run this flow on `maya_rapa` as a dry rehearsal, or hold.
> Planted questions go in via the proven direct-injection path (single-name whitelist, 08-11 spec).

| Time | Scene | She says (live voice over baked video) | Mechanics |
|---|---|---|---|
| 0:00–0:20 | PRESENT | "Hey, I'm Maya — and yes, I'm an AI host, live right now. Ask me anything in the chat, I actually answer. Today: our vitamin C serum — twenty percent." | Hook + AI transparency up front (trust + compliance) |
| 0:20–1:30 | PRESENT | "Twenty percent vitamin C. One drop, every morning, on clean skin — that's the whole routine. Light texture, absorbs fast, no stickiness." | Product story, catalog facts only. Price beat #1: "It's ₪149 today, regular ₪249." |
| 1:30–2:00 | CUT_APPLY | "Watch this — one drop on the back of the hand. See how it spreads? That's all you need. Bottle lasts about two months." | Cutaway plays, voice keeps narrating = the 'she demos while talking' wow |
| 2:00–2:30 | PRESENT + price banner | "So: twenty percent vitamin C, one drop a day, ₪149 — the link is right below this video. And if you type ME in the chat, I'll make sure you get the link personally." | Price beat #2 + lead-capture hook (W3 catches 'ME' → sheet) |
| 2:30–5:30 | PRESENT (+CUT_EXAMINE on q1) | LIVE Q&A — planted seeds, real ones mixed in: | Seller brain W4 answers by name |
| | | q1 "What does it feel like?" → "Dana — light, almost like water, absorbs in seconds." + switch CUT_EXAMINE 15s | texture Q triggers examine cutaway |
| | | q2 "How often do I use it?" → "Tom — once a day, one drop, mornings on clean skin, before moisturizer." | usage |
| | | q3 "How much is it?" → "Maya K — ₪149 live today, regular ₪249, link below. Free shipping over ₪200." | price beat #3 |
| | | q4 TRAP: "Will it cure my acne?" → "Honest answer, Lior — I can't make medical claims, it's a cosmetic serum. For skin conditions, a dermatologist is the right address. What it does do: twenty percent vitamin C for glow." | THE client wow: guardrails live on air |
| | | q5 "Is this AI??" → "One hundred percent — I'm Maya, an AI host. Everything I say about the product comes from the catalog, nothing invented." | transparency feature as a selling point |
| 5:30–6:10 | PRESENT + banner | "Wrapping this round: twenty percent vitamin C serum, one drop every morning, ₪149 — price beat #4 — link below, or type ME and I'll sort you out personally." | Price beat #4 (playbook: price ×4 per block) |
| 6:10–6:30 | PRESENT | "I'm staying live — new round starting right now. Joined mid-way? Perfect timing. Ask me anything." | Re-entry bridge → block restarts seamlessly |

## RULES THAT MAKE IT SMART
1. Cutaways NEVER interrupt an answer — if a question lands mid-cutaway, finish the clip, then answer on PRESENT.
2. If chat is silent in the Q&A window, she fills with catalog micro-facts ("small thing people miss: clean skin first, serum before moisturizer") — never dead air, never invented claims.
3. Any medical/forbidden question = the q4 deflection pattern, always.
4. Operator keeps KILL switch + can inject a scene change one keypress away.
5. Block repeats verbatim-safe: all lines are evergreen, only price is a variable — kept at ₪149/₪249 from `serum-c.en.json`. 3-min version for tight demos: 0:00–2:30 + q3 + q4 + wrap.

## TO RUN IT
- Price already filled from `serum-c.en.json` (₪149 live / ₪249 reg, free ship >₪200). If the catalog price changes, this doc must be re-synced from it — catalog is the single source of truth.
- Pre-load planted questions q1–q5 from `maya-ops/demo/planted-questions-serum.json` in the injection console (whitelisted single-name format, per the 08-11 spec).
- Cutaway scenes CUT_APPLY / CUT_EXAMINE: see `maya-ops/demo/OBS-CUTAWAYS.md`.
- Full pre-flight + avatar switching: see `maya-ops/demo/DEMO_RUNBOOK.md`.
- Record on unlisted YouTube per M2 runbook → that recording = client demo.

## STILL MISSING (later Kling sessions, do not block)
- CTA/pointing scene on the new background.
- Hands-free idle on the new background (current idle candidates all hold the bottle).
