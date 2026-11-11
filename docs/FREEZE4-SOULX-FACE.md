# FREEZE v4 — Nova's live face in a side panel (SoulX-FlashHead), not lips on her body

Page: `beta/freeze4.html` · shared: `shared/face-panel.js` (new), `shared/nova-bridge.js` (one optional input added) ·
pod half: `tools/pod/nova_face.py` (SoulX → LiveKit `nova-face`), `/beta/freeze4` in `pod/rt_lk.py` ·
proof: `test/proof/freeze4.mjs` (offline) and `tools/pod/freeze4_*.{sh,py}` (real pod) → `docs/evidence/freeze4/` ·
proposed tag `beta-b0.27-freeze4` · 2026-11-10 / 2026-11-11

## In four lines
- **Ran on a real pod (2026-11-11):** Nova's live voice (OpenAI realtime, her `marin` voice) and her **real SoulX-FlashHead face** in the side panel, beside her original baked dancing clips, the child played by a recording. Recorded with sound: `docs/evidence/freeze4/pod/nova-freeze4-TAKE1-in-game-talking.mp4`.
- **Seen by eye:** the face is real SoulX (her head crop, mouth shapes change with the words); her mouth starts **~120–160 ms after** her voice (take 1, frame by frame); the face reaches the browser at **0.72×** the sharpness the pod rendered.
- **Not done:** one clean take that has BOTH the clean layout and her in-game lines. Take 1 talks in the game but has browser bars, two missing emoji and a hidden ending; take 2 is clean but a brain lock silenced her after the welcome. Both causes are fixed in code — no pod has run the fixed code (four more boots never pulled the 14 GB image).
- **Money:** ≈ $1.02 of pod time (68 min of RTX 4090 Secure at $0.89/h), every pod terminated and confirmed gone. Table below.

## How SoulX is served today (read from the repos, 2026-11-10)
| Question | Answer | Where it is written |
|---|---|---|
| Is SoulX wired into `dance-project`? | **No.** The only mention is five old Maya pod names in a spend table. No page, no bridge call, no pod route, no tier knows about it. | `docs/NIGHT-SPEND.md` lines 16–37 |
| Where does it run then? | In the **Maya** repo (`maya-lt`), on a rented GPU pod: image `Dockerfile.soulx`, server `maya-ops/lt/soulx_shim.py` (port 8010) with `flashhead_renderer.py`. FlashHead Lite on one RTX 4090 held 25 frames a second. | maya-lt `INVENTORY.md`, `release/ENGINE-DECISION.md`, `release/PROOF-NOVA.md` (read only — no Maya file was touched) |
| An endpoint? A baked asset? | Neither. It is a **pod process**. It takes speech audio in (`/humanaudio`, `/humanwav`) and pushes video out as **RTMP** (to YouTube/Facebook) or a file. It does not publish into LiveKit, which is how Nova's pages receive her. | `soulx_shim.py` header |
| Has it ever drawn Nova? | Yes, as a Maya-stack character ("PROOF-NOVA", a live ad clip, 21 Oct) with an ElevenLabs voice — not with Nova's voice-to-voice brain and not inside a game. | maya-lt `release/PROOF-NOVA.md`, `NOVA-V2.md` |
| Can it run live right now? | **No.** (1) no RunPod key in this session; (2) the account was under its $2 floor an hour before this work; (3) the pod-side link from SoulX into Nova's LiveKit room does not exist yet. | — |
| What does Nova's Freeze use today? | `beta/freeze-nova.html` (the launcher's Freeze) speaks with the browser's speech synthesis and recorded lines; the pod-served `beta/freeze.html` draws lips on her body with MuseTalk, or Ditto behind `NOVA_FACE=ditto` on branch `nova-ditto` (not merged). | `beta/index.html`, `docs/NOVA-DITTO.md` on `nova-ditto` |

**Open decision for the founder (not decided here):** the note on record from 2 Nov says Nova's face engine moves to Ditto and that this replaces the earlier SoulX plan. Freeze v4 is built on SoulX because this task asked for it. The page does not care which engine draws the face — it shows whatever video arrives as `nova-face`.

## What v4 is
The same honest Freeze as `freeze-nova.html` — same judge (`beta/lib/freeze-game.js` + `beta/freeze2`), same lights (`shared/nova-lights.js`), same stars, card, ring, captions, Nova's same body clips — with two changes:

1. **Voice = live V2V only**, through `shared/nova-bridge.js` (`attachNova`, `routeVoice`, `note`). No speech synthesis. No recorded speech. The only canned sound left is the FREEZE sting (CONTEXT: "Voice = live V2V only … Only canned audio: the FREEZE! sting").
   What she is asked to say still comes from the Truth-Law brain (`beta/lib/brain-local.js`, unchanged): only what the judge really saw. Each judge result also goes to her as a silent `fact:`.
2. **Face = a live video stream in a side panel** (`shared/face-panel.js`). Nothing is drawn on her body. There is no fallback picture.

### Phase machine (CONTEXT "Phase machine"; `routeVoice()` is the only router)
| Phase | Voice route | Badge when she is quiet |
|---|---|---|
| Intro, calibration | `engine` | Listening |
| Dance, result moment | `air` — one line per gap | Watching |
| Freeze hold | `mute` — nothing is even asked for | FREEZE! |
| Ending | `engine` | Listening |

Any phase, her voice sounding → **Talking** (panel grows). A line asked for and no voice yet after 0.5 s → **Thinking**.

### Layout — rules used
| Rule | Source | What the page does |
|---|---|---|
| Avatar size follows the moment: small in the game, "when she has something specific to say, she briefly grows" | lexi-ux-patterns **Pattern 1** | two panel widths: small (quiet), big (talking) |
| State badge "a small pill at the bottom of Nova's tile", Talking = green pulse, four states | lexi-ux-patterns **Pattern 2** | Watching / Listening / Talking / Thinking |
| Persistent badge incl. `FREEZE!`; "Adaptive width transition 0.5s"; "zero black anywhere"; full figure never cropped; ≤1 line per gap | game-cues-lights "Layout laws", "Juice checklist" | FREEZE! badge (ice blue), 0.5 s transition, blurred room copy behind her body (scaleX 2.2, blur 28px), body `object-fit:contain` |
| Gold is the only colour that glows; ice only at freezes; never red for the child | CONTEXT "light language" | gold ring on the tile while Talking, ice outline in the hold |
| Missing asset = red banner | CLAUDE.md law 4, colours of `beta/wave.html #banner` | see "No silent fallback" |

**The panel cannot cover the child or the lights:** the child's pane is a separate half of the screen with a fixed 50 % (the same share as `freeze-nova.html`). The face panel lives inside Nova's half only, and when it grows it takes room from Nova's body pane. Measured at 1280×720: panel x 0–230 px (small) / 0–307 px (big); child pane starts at x 640 and is 640×720 both times; the light canvas box does not change. Stacked on a phone (432×768): panel bottom 384, child pane top 384.

### No silent fallback
| Missing | When | What the screen shows |
|---|---|---|
| Face stream, live voice, or a body clip | at Start | whole-screen red banner naming it; **the game does not start** |
| Face stream stops | mid-game | the panel turns red ("Nova's live face is not streaming (SoulX)") within ~3 s, the stale last frame is hidden; the game goes on; clears by itself when frames return |

## The pod contract (built 2026-11-11 — see "Real pod runs")
1. Publish the SoulX face into Nova's LiveKit room as a **second participant, identity `nova-face`, one video track**. Her voice stays on `nova-avatar` (audio) exactly as today.
2. Feed the SoulX renderer the same live voice audio the room hears, in every voice route except `mute`, and keep rendering her calm face in silence (the shim already renders silence).
3. Serve the page from the pod origin (the bridge calls `/token` and `/rt` on the page's own origin): a `/beta/freeze4` route in `pod/rt_lk.py`, like `/beta/novasays`. **Not added here** — `rt_lk.py` is a pod file and nothing could be tested against it.
4. `?intro=freeze` is sent, so the brain's self-triggers stay off (`rt_lk.py` `_freeze_mode`).

## Values
| Value | Number | Status |
|---|---|---|
| Child pane share | 50 % | same as `beta/freeze-nova.html` |
| Hold, rounds, pacing, judge thresholds | unchanged | `beta/lib/freeze-game.js`, `beta/freeze2/script.json` |
| Width transition | 0.5 s | game-cues-lights layout law |
| Thinking badge delay | 0.5 s | lexi-ux-patterns Pattern 2 ("latency >500ms") |
| Room fill | scaleX 2.2, blur 28 px | game-cues-lights layout law |
| Panel width small / big, landscape | min(18vw, 32vh) / 24vw | **[CLI-FILL]** derived: her clips are 1076×1924 (ffprobe), so on 16:9 her full-height figure leaves 18.4vw free; big draws her whole figure at 82 % |
| Panel width small / big, stacked | 34vw / 46vw | **[CLI-FILL]** same derivation for a 9:16 phone |
| Face tile shape | square | **[CLI-FILL]** FlashHead renders a square head; **QUESTION:** the real track size from the pod |
| Stream counted as dead after | 3 s without a new frame | **[CLI-FILL]** 3 × the engine's chunk (24 frames = 0.96 s, `soulx_shim.py`); **QUESTION** |
| Wait for face + voice at Start | 15 s (`?facewait=`) | **[CLI-FILL]**; **QUESTION** |
| Thinking badge gives up after | 6 s | **[CLI-FILL]** reply latency 1.04 s median, 7.0 s worst (`docs/TALK-TEST.md`); **QUESTION** |
| Participant identity | `nova-face` | **[CLI-FILL]** nothing names it yet; one constant in `shared/nova-bridge.js` |

## [CLI-FILL] list
- `[CLI-FILL] file name freeze4.html` — the Freeze pages on beta are `freeze.html` → `freeze2/` → `freeze3.html` → `freeze-nova.html`; "v4" follows that line. Nothing existing was renamed or replaced.
- `[CLI-FILL] v4 is cloned from freeze-nova.html, not from the pod-served freeze.html` — CLAUDE.md law 3 says build on the shared engines; `freeze.html` carries its own inline copy of the bridge and cannot run without a pod, so nothing in it could have been tested here.
- `[CLI-FILL] recorded speech lines dropped in v4` (countdown, "held", "missed", end line) — two voices at once is the old conflict, and the law allows only the sting. The on-screen cues they went with are unchanged.
- `[CLI-FILL] one line per gap enforced on the page too` — `freeze-nova.html` cuts the earlier line off with speech synthesis; a live voice cannot be cut like that, so a second line in the same gap is held back (logged), never stacked.
- `[CLI-FILL] shared/nova-bridge.js gained onFace + bridgeState()` — optional; pages that do not pass `onFace` take the same path as before. Not yet run against a real pod.
- The width, timing and identity values marked above.
- `[CLI-FILL] air lines go to the face engine` (`NOVA_FACE_SOULX=1`): the law says "game voice in the air" so that no lips are drawn on her dancing body. Here the lips are on the side face only and the body clip is untouched, so her game line rides the face engine (voice + face from one renderer) instead of `voice_air`. Default off.
- `[CLI-FILL] intro=freeze4`: no name-asking greet, no silence invites, staged questions never lock her — the v4 page starts the game without waiting for an answer (pod takes 1 and 2).
- `[CLI-FILL] no fact notes in v4`: on the pod each `fact:` in air mode was credited as the gap's spoken line.
- `[CLI-FILL] she talks less`: game lines ≤ 6 words (first sentence or the clause before "—"), else not said; ending ≤ 2 lines; the speech bubble sits under the face, never over her body. Cited in `beta/freeze4.html`.
- `[CLI-FILL] the recap gets the real animals` (it always said "the statue").
- `[CLI-FILL] Talking held 700 ms` after her voice dips (badge and panel flickered between words).
- `[CLI-FILL] reference face`: a head crop of the nova-ditto closed-mouth seed (nothing else matched the Freeze body at ≥ 512 px).
- `[CLI-FILL] FACE_VIDEO_DELAY_FRAMES` exists, default 0 — judged by eye it should stay 0.

## Proof — what was actually seen (`node test/proof/freeze4.mjs`, Chrome 153 headless)
Real: the page, the bridge, the panel, the judge, the lights, Nova's body clips, a replayed recorded child. Stand-in: the whole pod (token, brain socket, LiveKit room, the face video, the voice — a hum).

| Run | Shows | Files in `docs/evidence/freeze4/` |
|---|---|---|
| A — full game 1280×720, recorded | face reaches the panel through the bridge; Talking = big, quiet = small; no overlap with the child pane; child pane and light canvas unchanged; body whole; FREEZE! badge; routing `engine → air → mute → air → … → engine`; nothing said or asked in a hold; one line per gap; no speech file fetched except the sting; medal reached | `freeze4-STANDIN-face-full-game.mp4` (55 s, silent), `A-1…6-*.png`, `A-console.log`, `A-rt.log`, `A-page-log.json` |
| B — no face stream | red banner naming SoulX; no round ever starts; panel empty | `B-1-red-banner-no-face.png`, `B-*.log` |
| C — face dies mid-game | panel red after ~3.1 s, stale frame hidden, clears on return, game ends normally | `C-1-face-lost-mid-game.png`, `C-*.log` |
| D — phone portrait, Hebrew | stacked layout, no overlap, Hebrew badge | `D-1…2-*.png` |
| E — scoring untouched | the same replay gives `hit miss hit miss`, 2 stars, bronze on **both** `freeze-nova.html` and `freeze4.html` | `E-*-medal.png`, `run.log` |

**Not proven by any of this:** SoulX lips, picture quality, delay between her voice and her face, whether a 4090 can run SoulX next to Nova's brain, the `nova-face` wiring on the pod, sound in a real browser with a real child, the real camera (the child was a recording). Evidence law gaps: no recording to Downloads and no beeps (headless cloud session); the recording has no sound.

## Real pod runs (2026-11-11)

### What runs on the pod
| Piece | What it is |
|---|---|
| Image | `ghcr.io/dsbeauty01-web/maya-lt:soulx-wide-v2` — the image Maya's v1 live booted SoulX from (14.3 GB). No network volume; the `soulx-base` volume was NOT attached (the documented SoulX runs use images; its use is not documented in the Maya repo I could read). Registry credential `ghcr-2026-10-30` (the Sept `ghcr-maya-lt` left 3 pods "Exited by Runpod" in 1–16 s). |
| Face | `tools/pod/nova_face.py`: Maya's `flashhead_renderer.py` imported unchanged from the image; weights fetched at boot by Maya's `soulx_fetch.py` (7.8 GB, ~3 min including compile); publishes `nova-face` (512×512 25 fps video + her voice audio) into LiveKit room `nova-freeze4`. |
| Brain | this branch's `pod/rt_lk.py` with `NOVA_FACE_SOULX=1` (her air lines go to the face engine) and `?intro=freeze4` (the page owns every beat). |
| Child | `test/clips` recordings (`frozen-body, dance-hype, still-sway`) — `NOVA_TEST_CLIPS=1` only. |
| Recording | real Chrome 157 on a virtual screen + PulseAudio, ffmpeg x11grab — the picture and the sound Chrome played. |
| Reference face | `tools/pod/assets/nova_face_ref.png` = 560×560 head crop of `docs/nova-ditto/kling_seed_closed_mouth.png` (branch `nova-ditto`): closed mouth, same outfit and room as the Freeze body clips. |

### The welcome
The Ditto welcome is not on this pod (another agent owns it). The welcome is the repo's: the page stages one of `beta/lib/brain-local.js`'s two `intro` lines, said in her live voice by the SoulX face. The brain's own name-asking greet is OFF in `intro=freeze4` (see take 1).

### Numbers (all seen, files in `docs/evidence/freeze4/pod/`)
| What | Take 1 | Take 2 | How measured |
|---|---|---|---|
| Face render time per 0.96 s chunk (p50 / p95) | 330 / 363 ms | 381 / 411 ms | face server, every chunk |
| Render stalls (underruns) | 1 of 75 chunks | 0 of 76 | face server |
| **Mouth start after her voice starts** | **~120–160 ms** (voice 5.10 s, lips part 5.22–5.26 s, open 5.30 s) | ~150–250 ms (3-frame video delay was ON — wrong direction, now default 0) | **by eye**, frame strips `nova-freeze4-sync-take*.jpg` (screen recording + the sound Chrome played) |
| In-page probe (mouth motion vs voice level) | −133 ms median, xcorr −140 ms | −131 ms, xcorr −320 ms | `tools/pod/freeze4_measure.py` — **not trusted**: it counts head motion in silence; the frames contradict it |
| Page asks for a line → her voice starts | 0.28 – 3.10 s (5 lines) | 0.13 – 2.45 s (2) | page log |
| Face sharpness, received ÷ published | **0.72×** (Laplacian var 17–19 vs 23–25) | 0.64× (1 frame) | browser frame vs pod frame, centre 320×320 |
| Red banner, no face at start | game never starts, banner names SoulX + voice | same | `B-result.json` |
| Face stream paused mid-game → panel red / clears | 3.33 s / 7.11 s | 3.07 s / 7.10 s | `C-result.json` |
| Lines she said in the game | Got you! · You held it! · The bear got away! | none after the welcome (ask-lock) | rt_lk log |

### What each take showed — and what was fixed after it
- **Take 1** (`vdrthfbwcayuc6`): she talks in the game through the SoulX face, one short line per gap. Faults: Chrome's tab/URL bar in the capture (cropped off in the delivered mp4), two emoji drawn as boxes (no emoji font on the pod), the medal screen hid her face during the ending, and the ending recap was not said — the brain's greet asked the child's name, its ASK-LOCK waited for an answer that never comes in a replay, and she said a re-invite ("I'm right here, no rush at all.") instead. The silent `fact:` notes were also credited as spoken lines in air mode.
  Fixed: `intro=freeze4` (no greet, no silence invites), no fact notes, medal screen leaves the face rail visible, kiosk window, emoji font.
- **Take 2** (`w6ozzhxkr89a4l`): clean layout — no browser bars, emoji, face visible over the medal screen. Fault: the welcome variant ending in "Ready?" set the ASK-LOCK, so every later line was refused. Fixed: in `intro=freeze4` a staged question never sets the lock (`rt_lk.py ask_lock_set`). Also seen: the badge flickered Talking↔Listening between words → `shared/face-panel.js` holds Talking 700 ms.
- **Not run:** the code with both fixes (commit after `e19ac6d`). Two boots of it sat 14 and 10 min without the image ever starting and were terminated.

### Pod ledger (RTX 4090 Secure, $0.89/h, all terminated by id and confirmed gone)
| Pod | Up (UTC) | Minutes | Cost | What happened |
|---|---|---|---|---|
| lrb2ez3dz3clg1 · 4vucjn466kune7 · wak59r5b1tls2m | 04:04 · 04:05 · 04:05 | < 0.5 total | ≈ $0.01 | "Exited by Runpod" in 1–16 s (old registry credential) |
| vdrthfbwcayuc6 | 04:07:34–04:20:31 | 12.95 | $0.19 | **take 1** |
| 8sjdlde3t9wg19 | 04:23:12–04:39:42 | 16.5 | $0.25 | image never started |
| w6ozzhxkr89a4l | 04:39:59–04:54:22 | 14.4 | $0.21 | **take 2** |
| lip8ab1k35hzro | 04:54:40–05:08:42 | 14.0 | $0.21 | image never started |
| flwcty7elf454i | 05:08:45–05:18:54 | 10.15 | $0.15 | image never started |
| **Total** | | **68.0** | **≈ $1.02** | balance read 9.96 → 8.20 (another session also ran pods in that window) |

**Lesson for the next run:** 3 of 5 boots never pulled the 14 GB SoulX image. Maya's own launcher moved to the small cached `runpod/pytorch` image for this reason (`tools/pod_up.py` header, 2026-10-30). The next freeze4 pod should do the same: small image + `soulx_fetch.py` + the image's pip set, or a smaller face-only image.

## Seen in passing (not changed)
- `brain-local.js` has the line "Oops, you kept moving. Freeze when it stops!" — close to the never-negative law now that her real voice will say it.
- The recap line named "the statue" as best freeze whatever the animal was — fixed in v4 only (the page passes the real animals); `freeze-nova.html` still has it.
- The speech bubble in Nova's body pane sits over her face on the body clip (same as `freeze-nova.html`).
