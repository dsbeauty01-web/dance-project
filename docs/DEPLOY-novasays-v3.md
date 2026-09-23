# DEPLOY — Nova Says v3.2 (fresh CLI · the code is written · you adapt names, generate clips, deploy, prove)

Read first: docs/NOVA-SAYS-V3.1.md (the design) and .claude/skills/simon-says-rules + simon-says-digital + movement-tracking + game-cues-lights + game-vfx-juice + performance-feedback-ai.
Branch: `novasays-v3` from main. Beta only. Replaces V1/V2 (`beta/novasays.html`, `beta/novasays.js`, `beta/novasays-music.js` — delete the old ones on this branch). Tag `beta-novasays-v3`.

## FILES IN THIS PACK
- `beta/novasays.html` — the whole game (two engines, sequencer, two judges, stars, lights, handoffs, fallbacks). Parse-checked; every line id it uses exists in lines-en.json; every kit id/function it uses exists in the kit.
- `beta/novasays/script.json` — commands, practice, the 3 hand-tuned rounds, windows, timing, medals.
- `beta/novasays/lines-en.json` — every pre-recorded line (29 ids).
- `tools/capture_novasays_lines.py` — renders every line in her voice (2 takes), trims silence, writes manifest.json.
- `shared/game-kit.js` — the kit this page stands on (MUST be deployed — it 404s on the pod today).

## STEP 0 — ADAPT (the only places you may change code; log each as `[ADAPT] old→new`)
The page calls the bridge through these names. Map each to what `shared/nova-bridge.js` + `rt_lk.py` (PRODUCER-SILENT build) actually expose. If a capability is missing, add it to the bridge — do not change the page's logic.
| page call | must do |
|---|---|
| `K.bridge.attachNova({onVideo})` | attach her LiveKit video |
| `K.bridge.setBody(id)` | switch avatar (`/set_avatar`) |
| `K.bridge.onHerAudio({playing, ended})` | her live audio start/end events |
| `K.bridge.note({kind:'speak-gate', on:true/false})` | speak-gate ON during SHOW, OFF at handoffs |
| `K.bridge.note({kind:'remember', text})` | → rt_lk `remember()` (conversation.item.create, silent) |
| `K.bridge.note({kind:'section-end', speak:true, text})` | → a page-reported section END boundary + ONE `speak_now` with that text |
| `K.bridge.mic(bool)` | stop/start sending the kid's mic to the brain (closed during SHOW) |
| `K.bridge.speakClip(url)` → resolves on end | play a pre-recorded clip THROUGH the avatar for lip-sync (LiveTalking has an audio-file endpoint, e.g. `/humanaudio` — find it). **If impossible:** set `"lipMode": "air"` in script.json and say so in the report (lines play from the page; the game still works). |
Also: the kit's presence-gate messages are English — add a Hebrew version keyed on `lang` (kit only, 3 strings).

## STEP 1 — THE BRAIN (rt_lk.py, the `?intro=novasays` greet branch, EN + HE)
Replace the V2 "SNEAKY" greet with (keep the WAIT rule and gender forms):
- EN: "Hi! I'm Nova! What's your name?" → (after the name) "{name}! Let's play Nova Says! When I say *Nova says*, you do it. If I DON'T say it — you don't move! Ready?" → wait for a real yes.
- HE: the same meaning in kid Hebrew, gendered by `?g=`.
- Persona for this game (both languages): "a playful, silly game leader who loves to trick the child in a fun way — warm, laughs WITH them, never negative. Never use the word sneaky."
- A validated yes fires the existing `nova:consent` page event. After consent the brain is offstage until a `section-end` arrives.

## STEP 2 — THE LINES
1. Write `beta/novasays/lines-he-m.json` and `lines-he-f.json` — same ids as lines-en.json, natural kid Hebrew, same length or shorter, gendered for a boy / a girl. Command lines: "נובה אומרת…" + the command; bare = the command alone.
2. Capture (voice = the Realtime session voice from `/health`):
```
python3 tools/capture_novasays_lines.py --lines beta/novasays/lines-en.json   --out audio/novasays/en   --voice <voice>
python3 tools/capture_novasays_lines.py --lines beta/novasays/lines-he-m.json --out audio/novasays/he-m --voice <voice>
python3 tools/capture_novasays_lines.py --lines beta/novasays/lines-he-f.json --out audio/novasays/he-f --voice <voice>
```
3. Listen check: every command clip ≤ 1.4s; real and bare takes of the same command sound equally excited (the words are the only tell).

## STEP 3 — THE BODY
- Verify the 5 bakes exist: `gest_star, gest_lefthand, gest_righthand, gest_clap, gest_bear` + `nova_idle2`. Missing = red banner (the page refuses to start) — report it, don't substitute.
- Measure each bake's real length → `bakeMs` in script.json. Check first/last frame of each against `nova_idle2`'s standing pose (±4%). If a bake doesn't start/end standing, trim to its standing frames or report it.

## STEP 4 — DEPLOY
Routes on the pod: `/beta/novasays.html`, `/beta/novasays/*.json`, `/audio/novasays/**`, `/shared/game-kit.js` (+ mover-engine, mover-rules, cue-window, light-engine, nova-bridge). Deploy target = where the pod actually serves `/shared` (`/workspace/pages/shared`) — verify with curl 200, don't assume.

## STEP 4b — THRESHOLDS (no invented numbers)
The page calibrates on each child: a 2s "stand still like a statue" (their STILL level) and the practice arms-up (their MOVING level + REACH). Every threshold is a fraction between those two levels — the fractions live in `script.json → tune`. Your job: run the harness with a still kid and a moving kid (fake camera, 10 runs each), print the energy distributions, and set `moveFrac` / `freezeFrac` / `reachFrac` / `clapCloseFrac` / `clapOpenFrac` to values that separate them with margin. Log every change old→new WITH the numbers. The certified Freeze page's stillness threshold (0.045) is a sanity reference for `thr.freeze` on a normal kid — report both.

## STEP 5 — PROVE (paste all, then HOLD)
0. docs/SCENARIOS.md — run one harness case per row group (A2 late mover → never GOTCHA; B1 shy kid → "together" after 3 misses; B2 hyper kid → coach line after 2 gotchas; C1 leave mid-round → pause + comeback + void window; D2 kill the video track → reconnect banner, give-up ending after 20s; D3 hide the tab → pause). Paste one log line per case.
1. Headless run with the debug strip: the practice + 3 rounds + ending complete in **≤ 3:00**.
2. Judges via the harness (fake camera): each command 5× real → ≥ 90% `hit`; each trick 5× with a still kid → 100% `held`; 5× with a moving kid → 100% `gotcha`.
3. The brain log for a full game: **exactly 4 speak_now** (greet/consent, card 1, card 2, ending) and **zero `[SPEAK]` during rounds**; speak-gate ON for every round.
4. Every handoff: her line starts ≤ 3s, or the fallback clip plays — never a silence over 3s.
5. Music is silent whenever the mic is open (log both).
6. A recording of one full game (EN) → Downloads `novasays-v3.mp4` + 3 beeps 🔔🔔🔔. HOLD — the founder plays `?lang=he&g=m`.
