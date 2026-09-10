# CONTEXT — Nova, everything a fresh CLI must know (read fully before any action · Sept 2026)

## WHO / WHAT
Founder: Refael — solo, non-coder, builds through CLIs like you. He approves plans BEFORE builds, hates guessing, wants evidence (screenshots, logs, recordings to Downloads + 3 beeps 🔔🔔🔔), and rules by his own eyes. One bounded task per session; report, then HOLD.
Product: **Nova Dance** — a browser dance companion: a live avatar (pre-baked video bodies + MuseTalk live lips, streamed from a RunPod 4090 via LiveKit), OpenAI Realtime voice-to-voice brain, MediaPipe/MoveNet camera detection (the witnessing: she reacts to the user's REAL moves), games with cues, lights, scoring. Kids AND adults (two coach tiers). Second line: Maya (same stack, live sales host) — NOT your concern; never touch Maya pods/files.

## CODE NAMES (use them in reports)
BODY = the page's HTML/CSS · LIGHTS = joint lights (light-engine) · CUES = what the user must do — windows, score, success · DETECTION = the pose code (pose-engine + mover-engine + rules) · BRAIN = her talking/encouraging/correcting (rt_lk prompts, notes).

## REPOS / PODS
`dance-project` (GitHub Pages product pages + `beta/` + `shared/` + `pod/`), `novapython` (Render worker, PULSE `/pulse`), `nova-avatar` (private pod repo). Branch **`beta`** = all new work (tags `beta-b0.x-<name>`); **`main` = the live commercial game, FROZEN** — only PRs titled `PROMOTE vX.Y` (freeze files need `FREEZE-APPROVED` in the body) pass CI. Pods: RunPod Secure 4090 in EU-RO-1 on volume `1ditrne6cb` (Nova's own `nova-vol` `pqbavl4mct` exists — migration pending); **one pod on a volume at a time**; pods self-stop (watchdog); a merge to main auto-deploys at boot (`deploy_from_git`). Launcher `maya-ops/tester/runrtlk.sh`; `boot-nova.sh`. If a pod "dies at 15 min" → check RunPod BALANCE first (that was the real cause), then volume contention, then capacity. Volume-less static pods can serve detection-only games for watching (no voice).

## THE LAWS (each paid for in blood — untouchable)
- **LAW-INPUT-LOCK:** server-VAD auto-response DISABLED. She generates ONLY on validated user turns (2+ words / whitelisted singles EN+HE / a detection FACT / a tap). One-shot per turn. Notes never unlock generation on their own; scheduled game cues go through the page cue engine (rate-limited, one per ≥7s / one per gap).
- **Phase machine:** INTRO/BETWEEN/ENDING = engine path (MuseTalk lips on the calm body `nova_idle2`) · GAME = her live voice IN THE AIR over the dancing/gesture body (engine gets NO audio — lips never attempt fast bodies) · HOLDS = hard mute. `routeVoice()` is the only function that changes routing.
- **Voice = live V2V only.** No pre-rendered speech. Only canned audio: the "FREEZE!" sting, dings/ticks, sfx.
- **Truth-gate:** praise only on detection facts. **One-attempt:** her question + silence = ONE re-invite then quiet. **Consent gate:** she never self-advances. **Never negative words** to the user. Light magic once per session.
- **Clock law:** cues fire off `music.currentTime` / `video.currentTime` / WebAudio time — never setTimeout. Video-led games: the mp4 is the clock (`__mp4Leads`).
- **Body map (Freeze):** talk = `nova_idle2` · dance = `nova_idlegroove_v2` (the WHOLE loop from beat one) · holds = pose clips. Silent fallbacks are forbidden — a missing avatar = red banner, refuse to start.
- **Framing:** full figure, never cropped (LAW-FRAME-FULL), face ≤30% of panel height, zero black bars; room-stretch = blurred self-copy behind her.
- Bake Factory only for bakes (clip_scan → trim → bake → `bake_verify.sh` → registry). Named-file git adds. Every value cited (ORIGINS / a spec / measured) or `QUESTION:` — never invented. A genuine gap you fill = `[CLI-FILL] what & why` in the report, never contradicting a written value.

## THE ENGINES (on beta — build games ON them, never around them)
- `shared/pose-adapter.js` + `shared/pose-engine.js` (b0.10): MediaPipe Pose Landmarker (GPU→CPU→MoveNet fallback), emits `toNova()` named joints (lShoulder, rShoulder, lElbow…, lIndex/rIndex + feet on MediaPipe), optional segmentation mask.
- `shared/mover-engine.js` + `shared/mover-rules.js` + `shared/cue-window.js` (b0.11): per joint per frame → position (EMA), velocity→direction (L/R/UP/DOWN), magnitude in the user's calibrated body-units, isolation (reference joints still). Rules: shoulderPop, shoulderSlide, ribSlide (hips+head still), hipSlide/hipBounce, headSlide/headNod, armRaise, freeze, clap (audio-fused), jump, WaveRule (traveling peaks + `phase()`), + grade() PERFECT/GOOD/OK. Calibrate per user in a no-score window (`startCal/finishCal`).
- `shared/light-engine.js` (b0.16→b0.19): body-scaled, bloomed. **The approved light language:** move cue = bloomed orb + closing ring (PERFECT band) + direction ribbon · **wave = the phase-driven comet** (sleeve-of-light ribbon on the bones, capped head, path guard) · **ribs/hips = the hoop** (perspective ring, slides/swells; dashed anchor hoop) · **freeze = ice glow on the silhouette only** · **clap = the snap** (hand glows + thin line → 4-point star). Gold is the only color that glows; ice only at freezes; warm for wobble; never red; labels above the head, never on the face; kids tier = full juice, adult = cool amber. Skill: game-vfx-juice (anticipation → impact → follow-through, easing, tapered ribbons, offscreen bloom).
- `shared/nova-bridge.js` (attachNova / setBody / routeVoice / note / onHerAudio / `nova:consent`), `shared/pulse.js`, `beta/tiers.js` (kids/adult voice prompts + params).
- Template page: `beta/wave.html` (stage 60/40, phase machine, pose loop, HUD, start gate, pause/exit, PULSE) — clone it for every new game.

## THE TWO COACH TIERS
KIDS (Freeze, Up Groove, Hello, Nova Says): 110% energy, ≤6 words mid-game, praise 4:1, silence on misses, stars, choices at every edge, memory references, grace miss, full gold juice. ADULT (Wave, Upper Body): calm coach, ≤10 words, praise 2:1 with one external-focus correction per round, numbers, tight windows, no grace, cool amber.

## WHAT EXISTS (Sept 10, 2026)
- **Freeze**: certified EN+HE, live on main (v1.0.1 camera fix); beta has lights/engine refinements; pending hotfix `FREEZE-FIX-GROOVE-START` (groove from beat one).
- **Upper Body**: re-based on the engines (`beta-b0.19-upperbody`), awaiting a live play-test.
- **Wave**: built on the engines with the accurate comet (`beta-b0.19` lights CLI); LOOK problems found in the live test: black bars, hard 50/50, cover-cropped webcam (arms out of frame), comet not remapped to the crop, pink+gold low contrast, and `handywave.mp4` is an idle not an arm-wave → fix list in CONTEXT §"Wave look".
- **Up Groove / Hello**: NOT built (freeze clones deleted from plan) — GAMES-3 specs gate them on measured section maps + founder approval.
- **Nova Says**: NOT built — this pack's primary job (NOVA-SAYS.md).
- Gesture bank (verified bakes, check the registry): `gest_bear/star/flamingo/frog` (freeze poses), `nova_wave_a` (52s wave), `nova_upgroove` + a/b/c, `nova_idlegroove_v2` (28s groove), `nova_idle2` (calm talk), possibly the GESTURE-BAKE set (hello/lefthand/righthand/point/bothhands/goodbye) — inventory before use; never assume.
- Tester package live (locked URL, waking-up state, consent gate HE+EN, 16:30 schedule). Hebrew live voice works (`?lang=he`, sticky-Hebrew). Machine-certify harness exists (`test/run_session.js`, graders G1-G6).

## WAVE LOOK — the approved fix list (do before any Wave play-test)
Webcam-hero layout on a dark stage, Nova as a small coach panel, no black bars · remap the lights canvas to the cover-cropped webcam so lights sit ON the body · presence gate before the game ("step back — I need to see your arms": shoulders+elbows+wrists visible ≥1s) · replace `handywave.mp4` with a real arm-wave source or the wave bake · fonts self-hosted.

## OWNERSHIP (two Nova CLIs may run — never collide)
Lights CLI owns `shared/light-engine.js`, `shared/mover-rules.js`, `beta/wave.html`. Games CLI owns `beta/upperbody.html`, `beta/upgroove.html`, `beta/hello.html`, `beta/novasays.html` + section-map measuring. Requests across the line go through a CHANGELOG note. Tags `beta-b0.x-<name>`. If you are the only CLI, you own everything.

## HOW TO WIN WITH THIS FOUNDER
Mirror an error list first for approval when he reports problems. Never let a value be guessed. Gate everything through his eyes (Downloads + 3 beeps). Protect his money (pods self-stop, one pod at a time, check balance) and his treasure (the bakes: never delete, archive tars exist). When he rages the work is usually 90% done — find the 10%. "TMI" = halve it.
