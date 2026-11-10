# FREEZE v4 — Nova's live face in a side panel (SoulX-FlashHead), not lips on her body

Page: `beta/freeze4.html` · shared: `shared/face-panel.js` (new), `shared/nova-bridge.js` (one optional input added) ·
proof: `test/proof/freeze4.mjs` → `docs/evidence/freeze4/` · proposed tag `beta-b0.27-freeze4` · 2026-11-10

## In three lines
- **Built and proven offline:** the page, the side panel, the state badge, the two panel sizes, the red banners, the voice routing, and that the scoring is the same as `freeze-nova.html`. 24 checks pass (`docs/evidence/freeze4/run.log`).
- **Not proven — needs a pod:** SoulX itself. No real SoulX face and no real live voice ran. The face in every screenshot and in the recording is a labelled **stand-in** (a still picture with a yellow "STAND-IN FACE · NOT SoulX" strip).
- **Money:** $0.00. No pod was created. This session had no RunPod key, so the balance could not even be read.

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

## The pod contract (what a pod must do for v4 — none of it exists yet)
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

## The pod run still needed
One Secure RTX 4090 pod, `nova-` name, watchdog self-stop, ≤ 60 min. Rate cap $1.50/h; the Maya SoulX pods in `docs/NIGHT-SPEND.md` cost $0.89/h → **about $0.90, at most $1.50**. Before it: RunPod balance ≥ $5, and someone must first write the pod half of the contract above (SoulX → LiveKit `nova-face`, the `/beta/freeze4` route). That pod-side code is a separate task — it is not in this commit.

## Seen in passing (not changed)
- `brain-local.js` has the line "Oops, you kept moving. Freeze when it stops!" — close to the never-negative law now that her real voice will say it.
- The recap line names "the statue" as best freeze whatever the animal was (the result rows carry no animal).
- The speech bubble in Nova's body pane sits over her face on the body clip (same as `freeze-nova.html`).
