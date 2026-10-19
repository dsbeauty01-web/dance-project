# MACHINE-CERTIFY — she gets tested by machine until perfect (voice harness · skill graders · Hebrew mode · founder watches 5 minutes, ever)

CLI MANDATE: full authority — pods, deploys, [CLI-FILL] thinking on gaps. Loop fix→test until the bar is met. The founder is DONE testing; you are the tester now. Laws untouchable: INPUT-LOCK, live-V2V-only voice, FREEZE body map, the approved sound design.

═══════════════════════════════════════════
## PART 1 — THE VOICE TEST HARNESS (the key)
═══════════════════════════════════════════
The realtime API accepts audio input buffers — so pipe PRE-RECORDED phrases into her session as if a kid spoke. Build:
1. **`?test=1` mode** on the freeze page: exposes `window.__test = { sayWav(url), pose(frameJson), tap(sel), state() }` — sayWav decodes a wav and streams it into the session's input path exactly like mic audio (same encoder/track).
2. **The phrase bank** (generate ONCE with any TTS at kid-ish pitch, 16k mono wavs, commit under `test/phrases/`):
   - EN: `hi_im_shuki.wav` · `yes.wav` · `whats_your_name.wav` (a chat question) · `do_you_like_pizza.wav` · `ok.wav` · `im_ready.wav` · `bye.wav`
   - HE: `shalom_ani_shuki.wav` (שלום, אני שוקי) · `ken.wav` (כן) · `muchan.wav` (מוכן) · `ata_ohevet_pizza.wav` (את אוהבת פיצה?) · `sababa.wav` · `yalla.wav`
   - NOISE: `garble1.wav` (café noise) · `breath.wav` · `silence20s.wav` · `hum.wav`
3. **Synthetic poses:** a JSON pose-feed player (still kid / kid-does-freeze-hold / kid-moves-during-hold) driving the MoveNet hook in test mode.
4. **The session script runner:** `test/run_session.js` — plays a full scripted game: greet-wait → name phrase → 👂 check → a chat question → consent phrase → music → per-freeze pose behavior (hold 8 of them, break 2, absent 1) → ending answers → PULSE. Captures: full transcript (both sides), her audio (recorded), all log markers, timings.

═══════════════════════════════════════════
## PART 2 — THE GRADERS (the skills as law — every reply auto-checked)
═══════════════════════════════════════════
`test/grade.js` scores each session; ALL must pass:
- **G1 hears+answers:** every phrase gets exactly ONE response ≤3.5s; the name phrase's reply CONTAINS the name (Shuki/שוקי); the chat question gets an in-character real answer.
- **G2 presence:** mid-game replies ≤6 words; specific (references the fact/clip/streak — reject bare "great job"); NEVER negative words (no/wrong/bad/didn't); assistant-talk regex = 0 hits.
- **G3 silence law:** ZERO her-audio during freeze holds (measure her track's energy inside every hold window); ≤1 line per gap; warnings land 2-4s pre-freeze; NO warning before the fakeout.
- **G4 flow:** intro ≤40s to music; verdict line ≤2.5s post-melt (log median); ending trio complete (real score number spoken, fun-question, name in goodbye); PULSE row received with feedback_text.
- **G5 lock:** garble/breath/hum → `[INPUT-LOCK] dropped`, zero responses; silence20s → exactly one re-invite then quiet.
- **G6 body map:** `[BODY]` log lines match the law table exactly (idle2 talk / idlegroove_v2 dance / pose clips holds).

═══════════════════════════════════════════
## PART 3 — HEBREW MODE (`?lang=he`)
═══════════════════════════════════════════
1. Session config: `transcription.language='he'` when lang=he (else 'en' — the lock stays).
2. Prompt block appended (he): "דברי רק עברית פשוטה וחמה לילדים. משפטים קצרים. אנרגיה גבוהה. אל תערבבי אנגלית."
3. INPUT-LOCK whitelist += Hebrew singles: כן, לא, אוקיי, סבבה, מוכן, מוכנה, עוד, די, היי, יאללה, קפוא. Name-beat accepts Hebrew name tokens (any single Hebrew word ≥2 chars at the name beat = candidate).
4. UI strings bilingual via a tiny dict (banner/buttons/badges); detection+scoring untouched (language-blind).
5. The harness runs the FULL Part-1 script in Hebrew with the HE phrases; graders identical (name=שוקי, negativity list gets Hebrew words: לא נכון, רע, טעות).

═══════════════════════════════════════════
## PART 4 — THE LOOP + THE BAR
═══════════════════════════════════════════
Run EN session → grade → fix the top failure at CODE level → rerun. Same for HE. **The bar: 3 CONSECUTIVE fully-clean sessions per language.** Never weaken a grader to pass it; a grader change = [CLI-FILL] logged with reason. Pod self-stops between loops; batch fixes to minimize pod hours (report total $).

═══════════════════════════════════════════
## PART 5 — DELIVERY (the founder's 5 minutes)
═══════════════════════════════════════════
🔔 To Downloads + 3 beeps 🔔🔔🔔:
1. **nova-certified-EN.mp4** — one full clean session, screen+audio
2. **nova-certified-HE.mp4** — same in Hebrew
3. **CERT-TABLE.md** — G1-G6 × final results, latency medians, sessions-to-clean count, [CLI-FILL] list, pod cost
Then HOLD. The founder watches the two clips and rules: RELEASE or the fix list. (On RELEASE: merge everything, port one-tap/ear-chip/live-voice wins to the commercial page, tester package ready.)
