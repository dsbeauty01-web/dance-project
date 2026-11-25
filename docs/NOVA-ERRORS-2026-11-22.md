# NOVA-ERRORS — deep audit of the Freeze v4 live build (2026-11-22, branch `nova-audit`)

Trigger: Refael on `/tmp/claude-0/nova_approve.mp4` (47 s, the new entry flow, origin/nova-play-fix 1a0670a..7e8e1d4):
"Nova video looks slow like shit, and not the correct intro. The ORIGINAL intro is with the LIGHT ON HER SHOULDER. She needs
to be more calm, not move much. Search all the errors."

Everything below is measured or quoted with its source. Fixes are behind flags, default OFF in the code, turned ON for this
build only in `tools/pod/nova_final_pod.sh` (`NF_AUDIT=1`; `NF_AUDIT=0` = the old build).

## 1. The original intro (what Refael approved)

| | the approved intro | what freeze4 / NOVA-FINAL plays now |
|---|---|---|
| where | `nova-commercial.html` on **origin/main** — INTRO-V2V `75396a4` (FREEZE-APPROVED, 2026-09-14), promoted in `d29b13f` "PROMOTE v1.0.4 - nephew fixes + INTRO-V2V (#48)", kept through `f3a43be` PROMOTE v1.0.6. Code: `introShoulderChallenge()` L4016-4077, arming L7520-7560, persona L1907-1925, LAWS.md `law-shoulder` L74 | `beta/freeze4.html` L426-439 (`mindReact('intro')`), never promoted |
| the light | a golden light on the child's **right shoulder** (`window.__introCueJoint = 'right_shoulder'`, `#rec-cam-glow`), armed only after the child's name (law-shoulder), a REAL MoveNet shrug check (isoPulse, 1.1 s window, thr 0.15, 2 hits); win = the glow pops and she celebrates in ≤ 5 words; nobody lifts = warm release after 20 s, she never claims she saw it | **no light at all**. `beta/freeze.html` L399-408 even tells the brain "no magic light on anyone's shoulder" (that was for the in-game prompt) |
| her words | greet + ask the name, then (SHOULDER-BEAT §4b, `33f83fe`, founder spec 2026-09-20, branch `truthgate-namebeat`, never promoted) the EXACT line "Look — a magic light on your shoulder! Lift that shoulder up high, just that one!", one retry at 8 s "I haven't seen it yet — try lifting the shoulder with the light, high!", then she invites to Freeze | one line: "Dance when the music plays. When it stops — freeze like the animal I show you! Ready?" (`beta/lib/brain-local.js` L25) |
| her body | the calm talk body: MuseTalk lips on `nova_idle` / `nova_idle2` (`6088fb3` "Intro/ending stay nova_idle"; CONTEXT.md phase machine "lips on the calm body `nova_idle2`") | Ditto on `tools/pod/assets/nova_talk_wide.mp4` = `freezegame/idle_sway.mp4` zoomed 1.3x (`53c5f0e`), DITTO_AMP 0.6 — a swaying body: lipcheck "head sway 28 % of face height, prebake head-motion REJECT" (docs/NOVA-FINAL.md) |
| her face size | waist-up closeup (`__sarayFrameMode('closeup')`) | wide, cut at the shins |

Note: the code comment says "light **her** shoulder" (main L4016) — "her" is the child. The light was never on Nova's own body.
If Refael meant a light drawn on NOVA's shoulder, that never existed in git: QUESTION.

The audio files under `audio/intro/` (`nova-arrival.mp4`, `-he.mp4`, `f47c45f`/`ee4a391`/`1ddc305`) are the Nov-2 Ditto
"arrival" clip of the commercial page (Nova on the forest bridge, "Hi! I'm Nova…") — not the shoulder intro; freeze4 uses
them only as stage-W test voice.

## 2. The errors, most serious first

| # | error | evidence | status |
|---|---|---|---|
| 1 | **Wrong intro** — the shoulder light beat is gone | §1. freeze4.html L428 asks only the Freeze line | **FIXED** (flag `shoulder`): `beta/lib/shoulder-beat.js` + freeze4.html — light on his right shoulder, exact §4b lines, real shrug check, retry 8 s, silent release 20 s, then the Freeze line. `test/shoulder_beat_f4_test.mjs` 7/7 on real clips (frozen-body, idle-sway, empty-room = no win; pre-upgroove = win; clock never wins) |
| 2 | **She moves too much** (phase law "lips only on the calm body") | her pane in the mp4, mean frame difference: intro 3.4, answer 3.1 (game clip 4.7). The talk body itself: `nova_talk_wide.mp4` 4.30 per frame vs `nova_idle`-style calm body 0.17 | **FIXED** (flag `NF_CALM`): `tools/pod/assets/nova_talk_calm.mp4` = `docs/nova-ditto/fullbody/nova_fullbody_calm.mp4` (aa7ce41, gates passed except face size) framed 1.3x like the old one → 0.17 per frame, **25x calmer**, face ≈ 234 px. Pod: Ditto ran on it in real time; her recorded pane moves 0.12 (was 3.4). Gold gate (W) NOT run |
| 3 | **Choppy picture** (what Refael saw) | Nova's pane after 10 s: 12.9 % bit-exact repeats, 28.9 % near-repeats (< 0.2), 41.6 % < 0.5. Per segment (< 0.2): intro 31 %, You-line + answer 33 %, game 20 %. Frozen runs of 5-7 frames **every 2.0 s** (15.88, 17.88, 19.80 … 33.84 s) — and the SAME 2-s freezes appear on her **local clip** in the game (39.8, 44.9 s) and in the earlier pod run (19.84, 21.80, 23.88 … no WebRTC there) | **cause found for the 2-s freezes: the proof recorder**, not her stream (a local mp4 cannot stall on the network). Fix `NF_REC_FIX` — **FIXED, proven** (local clip 20 % → 8 % repeats, no 2-s freezes). The rest is REAL: the pod publishes 25 fps, the browser shows 9-15 of her live pictures a second (§3) — **NOT FIXED**; candidate flags `FACE_WIDE_SOURCE=camera`, `FACE_WIDE_TS` written, not yet run. The calm body makes it far less visible (she hardly moves) |
| 4 | **Publisher bursts** — after a late chunk the face server sends up to 0.5 s of frames with no wait | `tools/pod/nova_face.py` L291-293 (`dt < -0.5` is the only re-anchor) | **FIXED** (flag `FACE_PUB_STEADY`) + counters `pub_late_frames`, `pub_max_lag_ms`, `pub_reanchors` |
| 5 | **The proof recording runs inside the live loop** — FACE_RECORD=1 writes every 1080x1920 frame (6.2 MB) to an ffmpeg pipe in the 25 fps publish loop; a slow encoder blocks the live picture and voice | nova_face.py L341-343; nova_final_pod.sh starts the face server with `FACE_RECORD=1` on every pod, Refael's play pods too | **FIXED** (flag `FACE_REC_THREAD`): a writer thread; a full queue drops a RECORDING frame (`rec_dropped`), never a live one |
| 6 | **Voice holes** — 8 holes of exactly 0.16-0.20 s inside one 8 s sentence | `/tmp/claude-0/nova/B/live7.wav` 926.6-932.4 s: 8 exact-silence runs of 0.16-0.2 s on the 0.4 s grid; cause `pending_take()` zero-pads a half-arrived chunk (nova_face.py L154-169) | **FIXED, proven on the pod** (flag `FACE_VOICE_PREBUF_MS=400`; `voice_holes 0`): a line starts from a 0.4 s cushion. Simulation `test/nova_face_voice_test.py`: jittery real-time voice 1.38 → 0.05 holes per line; cost +0.56 s before her first word. If her voice ARRIVES slower than real time no cushion can fix it — the new `voice_lines` counter measures the arrival speed |
| 7 | **Black face tile** at the first round | mp4 35.6 s grey empty tile, 36.0 s black square, 36.4 s her face | **FIXED, proven** (flag `pipfresh`; pod: covered 1.0 s, then her face): the tile stays covered until a real non-black frame of her face arrives |
| 8 | **The size jump** wide → game: the intro body is a 1.3x close shot cut at the shins, the game clips are the whole figure, so at the switch she shrinks and her feet appear | mp4 35.6 s; LAW-FRAME-FULL "full figure, never cropped" (CONTEXT.md) | NOT FIXED (the 1.3x zoom is what lets Ditto find her face: 158 px full body = gold gate BLOCK). The calm body is cut at the ankles, smaller jump |
| 9 | **She talked in the intro under an "ending" note** | `/tmp/claude-0/nova/D/rtlk.log`: first brain line in the intro = "[REMEMBER] system: [phase] The game section just ended. The ending has the floor now" | fixed earlier behind `NOVA_INTRO_ANSWER=1` (6c391b7, on in this build); the default (flag off) is still wrong |
| 10 | **Lips: every live Ditto take is BLOCK** on the Gold gate and shipped anyway | docs/NOVA-FINAL.md: Freeze v4 corr 0.661, pause jitter 2.90, 106 pucker frames — "Per the lock this take is NOT a result" | NOT FIXED (QUESTION in that doc still open). The calm body should lower the silence numbers (they were measured as her swaying body's own noise); needs a W run |
| 11 | **Pod self-stop does not work** | nova_final_pod.sh L24-26: `runpodctl remove pod` / REST v1 DELETE with `$RUNPOD_API_KEY`, but nova_final_ctl.py passes no RunPod key in the pod env and REST v1 is retired (skill nova-live-check §2) | NOT FIXED — always use an outside timer (done for this audit's pod) |
| 12 | **Clock law** — Freeze v4 drives the game with `setInterval(…,100)` + `performance.now()` and her lines with `setTimeout`, not the music's `currentTime` | freeze4.html L446, L206-208; CONTEXT.md "Clock law … never setTimeout" | NOT FIXED — inherited unchanged from the promoted `beta/freeze-nova.html` (main v1.1-1.3), which Refael approved |
| 13 | **Docs that contradict the code** | freeze4.html header L8-9 "her FACE … in a panel on the SIDE of the screen" (the side rail was removed, NOVA-FINAL); L347-348 "her answer … said WIDE, on the calm body" (the body was the swaying one); CONTEXT.md body map "talk = `nova_idle2`" vs freeze4's Ditto body; `law-shoulderbeat` (33f83fe) exists only on `truthgate-namebeat`, LAWS.md on main does not have it | NOT FIXED (documented here) |
| 14 | **Hebrew shoulder lines are masculine only** ("תראה", "תרים") | 33f83fe L223-224; freeze4 has `?g=m|f` for her other Hebrew lines | NOT FIXED — the approved words are kept verbatim; QUESTION: feminine variants |
| 16 | **Intro lines after the first are never said in the intro** — the brain only speaks a staged line at a boundary (PRODUCER-SILENT); the intro has one (speak-gate off). Any second intro line waits for the next boundary = the game | pod rtlk.log: "[SPEAK] queued (not a boundary): Yes! The light caught it!" … later "[SPEAK] (air-credit) Yes! The light caught it!" in the game | **FIXED after the run** (`introSay`: a speak-gate-off boundary before each intro line), NOT re-run |
| 15 | **Silent catches** (no-silent-fallback law) | freeze4.html `music.play().catch(() => {})`, `novaV.play().catch(() => {})`; nova_face.py "pip warm frame failed" only logged | NOT FIXED (minor: the music is not Nova; a dead body clip still raises the red banner via `error`) |

## 3. Proof pod (this audit)

Pod `exarcvmcwq6czb` (nova-final, Secure RTX 4090, 48 cores, $0.89/h), commit `0dea4a9`, 12:00:23-12:18:16 UTC
(17.9 min, ~$0.27), terminated by ID, `mine` = []. Flags on: calm body, prebuf 400, rec thread, steady publish, recorder
fix, page `shoulder` + `fpsprobe` + `pipfresh`. W skipped. Clip: `/tmp/claude-0/nova_approve2.mp4` (67 s, Play → first
freeze, H.264+AAC, 7.3 MB), looked at frame by frame.

| check | result |
|---|---|
| speed (silence, calm body) | wide p50 123 / p95 131 ms per 0.4 s chunk, late 0/112, underruns 0 — PASS (Ditto found her face on the calm body) |
| the shoulder light | light on at the reveal; the shrug check fired on the replayed child's real lifted arm 1.1 s later; gold flash + burst on his shoulder (frames rec 9.6-10.4 s) — WORKS. Two faults found and fixed after the run (not re-run): the check was armed before she had said the light line, and the win line + her Freeze explanation were queued by the brain ("[SPEAK] queued (not a boundary)") and came out later IN THE GAME. Fix: the check arms after her line ends; each later intro line is staged after a speak-gate-off boundary (`introSay`) |
| calm | her pane, recorded, intro: mean frame difference 0.12 (was 3.4 in nova_approve.mp4) — she stands still |
| voice holes | face server: `voice_holes 0`, `voice_pads 4` (= ends of lines), arrival speed per line 8.35 s of voice in 8.01 s, 3.0 in 2.62, 2.2 in 0.89 = faster than real time, so the cushion holds |
| what the pod PUBLISHED | `wide_published_A`: 1962 frames in ~78 s of wide = 25 fps, 11 % bit-exact repeats (the calm source itself has 4 %: still Kling frames) |
| what the browser SHOWED (fpsprobe) | her live wide body: **9-15 new pictures a second** (local clip in the same page: 21-24), Chrome's own dropped-frame count +4-5 a second → **the choppiness is real and it is on the way from the pod to the browser**, not in Ditto or the publisher. Publisher still late at times: `pub_late_frames 198`, `pub_max_lag_ms 202`, `pub_reanchors 45`, `rec_dropped 0` |
| the proof recorder | her local clip in the game: 8 % repeats and no frozen runs ≥ 4 frames (old recorder: 20 % and the 2-s freezes) → recorder FIXED |
| PiP | covered (room colour) for 1013 ms, then her face — no black square |
| answered the child | "You: Hi, Nova. Can you hear me?" → "Yes, I hear you loud and clear, superstar!" (intro) |

After the run, untested: `FACE_WIDE_SOURCE=camera` (the wide track was published as a SCREEN SHARE, which WebRTC lets drop
frame rate to keep sharpness) and `FACE_WIDE_TS=1` (frames stamped on the publish clock) — both on in nova_final_pod.sh,
the next pod's fpsprobe line ("wide" ≈ 25) is the test.

## 4. Flags added (all default off)

| flag | where | on in this build |
|---|---|---|
| `shoulder` | beta/freeze4.html (`?shoulder=1` or `beta/freeze4-flags.js`) | yes |
| `fpsprobe` | beta/freeze4.html | yes |
| `pipfresh` | beta/freeze4.html | yes |
| `NF_CALM` (`NF_AUDIT`) | tools/pod/nova_final_pod.sh → DITTO_SRC | yes |
| `FACE_VOICE_PREBUF_MS` | tools/pod/nova_face.py | 400 |
| `FACE_REC_THREAD` | tools/pod/nova_face.py | yes |
| `FACE_PUB_STEADY` | tools/pod/nova_face.py | yes |
| `FACE_WIDE_SOURCE=camera`, `FACE_WIDE_TS` | tools/pod/nova_face.py | yes (not yet run) |
| `NF_REC_FIX` | tools/pod/freeze4_proof.py | yes |
| `NF_PROOF_REPLAY`, `NF_PAGE_FLAGS` | tools/pod/nova_final_proof.py | own-right-up first (shows the WIN path) |

[CLI-FILL] the win line "Yes! The light caught it!" / "יש! האור תפס את זה!" (spec: factShrug "celebrate in five words");
the Hebrew greeting words; FACE_VOICE_PREBUF_MS = 400 (one Ditto chunk); pipfresh brightness 24/255.
