# NOVA-DITTO — moving Nova's live face from MuseTalk to Ditto, behind a flag

Branch `nova-ditto` (cut from `beta`). Nothing merged. Nothing ran on a pod in this session:
this container has no `RUNPOD_API_KEY`, no `FAL_KEY` and no SSH key, so every pod, every fal
generation and every live proof below is work **Refael's own CLI must run** — see RUN-ME.

The flag is `NOVA_FACE`. `musetalk` (the default, and anything that is not `ditto`) leaves
every path exactly as it is today. `ditto` switches the face engine.

---

# RUN-ME — what only Refael's CLI can do

Everything here needs a key or a GPU this session did not have. In order.

**Budget: $4 of RunPod, hard cap. Nothing merges to `main`.**

### 0. Before anything — the probe (free, 10 seconds, no pod)
`lk_bridge.py` lives on the RunPod **volume**, not in git. This session could not read it, so
the patch is anchored on snippets quoted in `docs/GROOVE-1080-REPORT.md` and in the patch that
already worked (`tools/pod/downscale_lk_bridge.py`). Prove the anchors before trusting them:

```bash
python3 /workspace/_repo/tools/pod/ditto_bridge_patch.py --probe
```

It prints the file's md5, whether both anchors are present exactly once, and every
`publish_track` / `VideoSource` / `AudioSource` / queue line it found.
**If `AudioSource` or `AudioFrame` is not 0, stop and say so** — that would mean lk_bridge
publishes the audio track itself, and the audio delay belongs there instead of in `rt_lk.py`
(see "What was assumed", assumption A2).

### 1. The pod
Use maya-lt's launcher, **never the 16 GB golden image** (7 of 7 golden pods sat `runtime: null`
on 2026-10-30; the small cached image boots in ~90 s):

```bash
cd /path/to/maya-lt            # dsbeauty01-web/maya-lt @ lane/motion-transfer
python3 tools/pod_up.py up --job novaditto --cmd deploy/small/novaditto_job.sh \
        --gpu-ladder "4090,L40S,6000Ada" --cloud secure --disk 60 --minutes 60
```
`pod_up.py` caps at $1.50/h, writes a `release/PRESS-TABLE.md` line per create, and
self-terminates after `--minutes` whatever happens.

### 2. The new clean body (fal Kling) — this is the step that decides everything
The gate rejects **every** body Nova has today, and not for face size: her resting mouth is
open and her head moves too fast (numbers in "What was measured"). Generate a fresh one:

* image **and** tail = the same clean knees-up Nova still, face ~280 px in a 1080x1920 frame,
  **closed-mouth smile**
* prompt: *gentle breathing sway, tiny head motion, blink, static camera, same room*
* 10–15 s, no cut, no crossfade, starts and ends on the same rest pose
* plus **one gesture clip** (a wave) from the same still, same room, returning to the same rest pose

Then gate it — free, CPU, no pod:

```bash
python3 tools/pod/ditto_body_prep.py nova_idle_clean_raw.mp4 \
        -o nova_body_ditto.mp4 \
        --gate /path/to/maya-lt/tools/prebake_gate.py
```
It measures her face, cuts the 9:16 knees-up crop to 1080x1920 at 25 fps (`-r 25` resamples
frames only — it checks the duration afterwards and refuses anything that changed speed),
runs the gate and prints the verdict, `face_px` p5/p50/p95 and every non-PASS check.
**It exits non-zero on REJECT.** Target: `mouth_p95 <= 0.025`, PASS or SOFTEN overall.

If the clip is already cropped, pass `--crop W:H:X:Y` to skip the measuring step.

### 3. Start Ditto on the pod
```bash
DITTO_SRC=/workspace/nova_body_ditto.mp4 \
DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 \
DITTO_THREADS=6 DITTO_EYE_HOLD=1 DITTO_WAIT_SEC=1500 \
bash /workspace/_repo/maya-ops/lt/ditto_up.sh        # or maya-lt's copy
curl -s 127.0.0.1:8031/health                        # until {"ready": true}
```
First run installs a py3.10 venv (torch 2.5.1 cu121 + TensorRT 8.6.1) and pulls ~2 GB of TRT
weights: 5–15 min. DITTO-TRY measured install 78 s, ready at 211 s, on a 4090.

### 4. Apply the patch
```bash
python3 /workspace/_repo/tools/pod/ditto_bridge_patch.py --apply
pkill -f lk_bridge.py; cd /workspace
NOVA_FACE=ditto setsid nohup python -u lk_bridge.py >/root/bridge.log 2>&1 </dev/null &
pkill -f rt_lk.py
NOVA_FACE=ditto setsid nohup python -u rt_lk.py >/root/rtlk.log 2>&1 </dev/null &
```
`--apply` backs up first, refuses if the patched file does not compile, logs the md5 before and
after, and is idempotent. `--revert` restores the newest backup. Both logs land in
`/workspace/gallery/wd/ditto_patch.log`.

### 5. Proof (a) — 90 s self-test in a LiveKit room
Assert, from the subscriber side: **25 fps**, **no frozen stretch > 2 s**, and
**lip/audio correlation >= 0.35**. Plus a **30 s egress mp4**.
The correlation tool is maya-lt `bench/results/nova-ab/tools/lipcorr.py` (mouth opening
landmarks 13→14 over face height vs audio RMS, Pearson at lag 0 and best lag).
The engine's own counters are at `/workspace/gallery/wd/ditto_stats.json`:
`held`, `longest_hold_s`, `alarm`, `render_ms_p50/p95`. `longest_hold_s` must stay under 2.0
and `alarm` must stay `null`.

> **Read the 0.35 bar honestly before you run it.** On a *clean* body Ditto measured **0.271**,
> not 0.46 — see "What was measured". 0.35 is only reachable with a body whose resting mouth is
> actually closed. If the new body gates `mouth_p95 <= 0.025` and the correlation still comes in
> under 0.35, the body is the thing to fix, not the engine.

### 6. Proof (b) — end-to-end latency
Kid stops speaking → first audio of her reply. **6 turns with `NOVA_FACE=musetalk`, 6 with
`NOVA_FACE=ditto`**, report both medians.
Ditto's floor is arithmetic: `(DITTO_PRIME + slack) x 40 ms` = `(35 + 10) x 40` = **1.8 s**.
If ditto adds more than ~1.5 s, retry with `DITTO_PRIME=25` (1.4 s) then `20` (1.2 s) and report
the lowest value that still keeps the lips locked. Lower `NOVA_DITTO_SLACK` only if
`ditto_stats.json` shows `held = 0` at the lower value — slack is the only thing standing
between a burst of 25 frames and a visible stutter.

### 7. Close out
```bash
python3 tools/pod_up.py kill <pod-id>
python3 tools/pod_up.py list          # must show 0 pods running or stopped
```
Terminate by id, prove 0 pods after, log every pod with its cost in
`release/PRESS-TABLE.md`. **Nothing merges to `main`.**

---

## What this branch contains

| file | what |
|---|---|
| `tools/pod/nova_ditto.py` | the sidecar: audio in → frames out. Resamples, chunks, drives `/render`, paces 25 fps, keeps the body alive with silence, counts held frames. Has a self-test. |
| `tools/pod/ditto_bridge_patch.py` | probe / apply / revert for the volume's `lk_bridge.py`. Installs the sidecar, swaps the frame source behind the flag. |
| `tools/pod/ditto_body_prep.py` | crop + gate a body video. CPU only. Refuses REJECT. |
| `pod/rt_lk.py` | **(edited)** flag-gated: feeds Ditto her audio and holds `/humanaudio` back by the A/V delay. |
| `beta/freeze.html` | **(edited)** flag-gated pose-clip set + the block that refuses an unapproved one. |
| `freezegame/knees/` | the four pose clips at the body's crop + `manifest.json` with the per-pose verdict. |
| `docs/nova-ditto/freeze-crop-check.jpg` | the evidence: four poses full-frame (top) vs knees-up (bottom). |

### How the pieces fit

```
OpenAI Realtime (pcm16 @ 24 kHz)
        │
        ▼
  rt_lk.py  engine_worker
        ├──► nova_ditto.feed(pcm)  ──► 24k→16k float32, exact 16000-sample chunks
        │                              ──► POST :8031/render ──► 25 BGR frames
        │                                      (silence chunks while she is quiet)
        └──► /humanaudio, HELD BACK (prime+slack)x40 ms ──► LiveTalking publishes the AUDIO
                                                                    │
  lk_bridge.py publish loop ◄── nova_ditto.next_frame_rgba() ───────┘ (video)
        └──► the existing 720x1288 downscale ──► the existing 3 Mbit + simulcast publish_track
```

**MuseTalk keeps running in ditto mode, as the audio pump.** Its video is dropped. That is on
purpose: it means the audio track, the publish settings and the LiveKit wiring are all
untouched, so the only new thing on screen is the picture. The GPU cost of keeping it is real
and is the obvious next thing to remove once the probe says who publishes the audio.

### The flag, exactly

| | `NOVA_FACE=musetalk` (default) | `NOVA_FACE=ditto` |
|---|---|---|
| `lk_bridge.py` | `w, h, rgba = await vq.get()` — the original line | frames from `nova_ditto` |
| `rt_lk.py` | `/humanaudio` immediately | Ditto fed now, `/humanaudio` held `(prime+slack)x40 ms` |
| `beta/freeze.html` (`?face=ditto`) | `freezegame/*.mp4` | `freezegame/knees/*.mp4` + manifest gate |
| publish settings | 720x1288, 3 Mbit, simulcast | **identical — not touched** |

---

## The phase machine — what it does now, stated, not changed

The game laws are unchanged on this branch. What Ditto *does* change is which body is on
screen, and that is a real change, so here it is in plain words.

| phase | voice | lips | body today (MuseTalk) | body with `NOVA_FACE=ditto` |
|---|---|---|---|---|
| INTRO | through the **engine** | **on** | `nova_idle2` (`setAvatar(TALK_BODY)`) | **the one Ditto source** |
| GAME | in the **air** (page plays it; the engine gets no audio) | **off** — her mouth never moves on the groove body | `nova_groove_a_1080`, set once on entry | **the one Ditto source** |
| HOLD | **muted**, absolute silence, no generations | off | the pose clip overlay (`PoseClip`) | the pose clip overlay |
| ENDING | through the **engine** | **on** | `nova_idle2` | **the one Ditto source** |

* **Voice routing is untouched.** `routeVoice()` is still the only function that changes audio
  routing; GAME is still `air`, HOLD is still `hard` mute. In GAME nothing reaches `engine_q`,
  so Ditto receives only silence and her mouth stays closed on the body — which is exactly what
  the law asks for, reached by the same road.
* **Holds still mute.** Unchanged.
* **The body swap is the casualty.** `ditto_server.py` loads ONE source video at boot
  (`DITTO_SRC`) and never changes it. There is no `set_avatar` in Ditto. So in ditto mode the
  `setAvatar(TALK_BODY)` / `setAvatar(GAME_BODY)` calls no longer change the picture: the same
  Ditto body is on screen for INTRO, GAME and ENDING. **The separate groove body is lost.**
  Three ways out, none of them silent:
  1. accept one body for the whole show (a gentle groove idle that reads as both);
  2. use the **motion bank** (`DITTO_BANK`, `maya-ops/lt/motion_bank.py`) — one mp4 holding
     several idle segments plus gesture clips, with a scheduler. The groove becomes the idle
     segments. This is the real answer and it is already built in maya-lt;
  3. restart the Ditto server between phases — ~3 min, not viable live.

  **This decision is Refael's, not mine.** Nothing on this branch picks one.

## Gestures — `/gesture` works, with one gap

`POST /gesture {"clip"|"action"|"cue", "hold_s"}` is real and `nova_ditto.gesture(name)` calls
it. **It only answers `ok` when the server was started with `DITTO_BANK=<bank.json>`** —
without a bank it returns `{"ok": false, "why": "no motion bank (DITTO_BANK unset)"}`, which
the sidecar logs loudly and counts in `ditto_stats.json` as `gesture_refused`.

Nova's bank already exists: `assets/live_motion/nova/nova_bank.json` in maya-lt. Its aliases:

| cue | clip |
|---|---|
| `wave` | `nova_wave` |
| `nod`, `laugh` | `nova_nod` |
| `point` | `nova_point` |
| `hold_up`, `show_closer` | `kit_closer` |
| `open`, `show_inside` | `kit_open` |
| `demo` | `kit_eruption` |
| `zoom`, `detail_zoom` | the product cut-in |

So **the greeting gesture is covered** (`wave`).

> **[TODO — a real gap, not a guess]** There is **no freeze-cue clip in that bank.** The
> `kit_*` clips are the volcano-kit commerce gestures from Maya's live, and they are framed for
> maya-lt's show, not for Nova Dance. A freeze cue (an arms-up "and… FREEZE!") would have to be
> generated and a Nova-Dance bank built with `bench/live_motion/build_bank.py`. Until then
> `nova_ditto.gesture('freeze')` will be refused and logged — it will not fail quietly.

---

## What was measured (by me, in this session)

All of this ran here, on CPU, on the real files.

**The freeze poses do not survive the knees-up crop.** Measured with MediaPipe PoseLandmarker on
the exact frame the page holds (`pauseAt`), against the crop box DITTO-TRY proved
(`628:1126+218+257` of a 1076x1924 frame). Evidence: `docs/nova-ditto/freeze-crop-check.jpg`,
numbers in `freezegame/knees/manifest.json`.

| pose | held at | verdict | what the crop cuts |
|---|---|---|---|
| **star** | 3.00 s | **REJECT** | both wrists (178 px, 13 px) and both index fingers (230 px, 61 px) — the star's points are her hands |
| **frog** | 2.40 s | **REJECT** | both knees (89 px, 43 px) and a hand (39 px) below the box — the squat is gone |
| **bear** | 2.20 s | **REJECT** | a raised paw out right 29 px **and above the top of the frame by 35 px** |
| **flamingo** | 2.90 s | **OK** | only the toe tip of the raised foot (68 px) and her far hand (50 px); the raised bent knee and the shoe stay — it still reads |

The star's hands measure at x = 20 and x = 1087 in a **1076**-wide frame — they are at the frame
edge *before any crop*. No zoom that satisfies Ditto's 200 px face floor can keep them. This is
not a tuning problem.

**The body gate, reproduced independently.** `ditto_body_prep.py` on `freezegame/idle_sway.mp4`:
face measured at 163 px delivered, crop `626:1112:220:209` (zoom 1.716x) → face 275/290/316 px,
duration 5.04 s → 5.04 s (frames resampled, not sped), verdict **REJECT** on `mouth_p95` 0.0632,
`disp_p95` 6.01, `roll_range` 16.2°, `rot_v_p95` 3.92, `smo_res_p95` 5.5. Exit code 5.
On the known-good `docs/ditto-try/nova_body_ditto.mp4` it returns **SOFTEN** (face 279/299/326,
`mouth_p95` 0.0397) and exit 0. Both branches of the tool are proven.

**`nova_ditto.py` self-test: 19 checks, all PASS** (`python3 tools/pod/nova_ditto.py --selftest`)
— flag off by default, 24k→16k resample length and amplitude, chunk-join buffering, exactly
16000 samples per `/render` every time, silence sent while quiet, speech picked up after a feed,
bounded picture buffer, 25 frames in 0.99 s, BGR→RGBA channel order, zero held frames, no freeze
alarm, gesture refusal reported, stats file written.

**`ditto_bridge_patch.py`** proven against a reconstructed `lk_bridge.py` carrying the real
snippets: probe finds both anchors, apply inserts the ditto branch **above** the downscale line
and leaves `publish_track` untouched, a second apply changes nothing, revert is byte-identical
to the original, and a file with a changed anchor is **refused with nothing written**.

**The law suite is green** after every edit: `tools/laws/run-all.sh` 14 passing / 0 failing,
`test/replay_all.mjs` all green, `tools/laws/kid-screen-guard.mjs` clean. `beta/freeze.html`
parses (both inline script blocks) and gains zero new kid-screen-guard hits.

## What was assumed (and how to kill each assumption)

* **A1 — the two `lk_bridge.py` anchors.** Quoted from `tools/pod/downscale_lk_bridge.py` (which
  applied them and was measured on air, 2026-10-22) and `docs/GROOVE-1080-REPORT.md`. I could not
  read the file. **Killed by:** `--probe`, step 0. The patch refuses rather than guessing.
* **A2 — the audio track is published by the LiveTalking engine, not by `lk_bridge.py`.** This is
  why the A/V delay lives in `rt_lk.py`. It follows from `pod/rt_lk.py`'s own header ("the SAME
  audio is what the engine publishes to LiveKit") and from the fact that every lk_bridge document
  in this repo discusses video only. **Killed by:** the `AudioSource` / `AudioFrame` count in the
  probe. If it is non-zero, move the delay into the bridge.
* **A3 — slack of 10 frames.** Ditto returns frames in bursts of 25; the publisher drains one per
  40 ms. Slack is the cushion, paid once as a constant extra picture delay, which is why the audio
  delay is `(prime + slack) x 40 ms` and not `prime x 40 ms`. 10 is a starting value, not a
  measurement. **Killed by:** `ditto_stats.json` — lower it while `held` stays 0.
* **A4 — the 24k→16k resampler** is a 3-tap anti-alias plus linear interpolation (numpy only, no
  scipy on the pod). Correct in direction, crude in the stopband; HuBERT is robust to it.
  **Killed by:** the lip/audio correlation in proof (a). If it is low *and* the body gates clean,
  suspect this first.
* **A5 — the pose-clip framing jump.** `docs/CHOPPY-FIX-2026-10-21.md` states the opposite ("a
  different-framed groove body would therefore NOT make every freeze jump — I was wrong to say
  that"). That correction is itself wrong for *this* change: `PoseClip` overlays are
  `inset:0; width:100%; height:100%; object-fit:contain; z-index:6` over the live video at
  `z-index:3`, so they replace the whole picture. At a different framing the figure changes size
  on screen across a 0.18 s crossfade. It is a scale jump, not a body-swap hitch — but it is a
  jump. **Killed by:** looking at `docs/nova-ditto/freeze-crop-check.jpg`.

## Where the brief and the files disagree — the files won

1. **"On identical audio Ditto beat MuseTalk (0.46 vs 0.19)."** True, but that 0.461 is **Ditto
   driven on the aired MuseTalk frames**. On a **clean idle body** the same run measured
   **0.271** (maya-lt `bench/results/nova-ab/README.md`), and the README says why: the idle
   body's resting smile leaves her mouth open in silence, which drags the correlation down.
   dance-project's own DITTO-TRY measured 0.266 → **0.516** on *its* audio. So Ditto is clearly
   better on lip timing (+40 ms vs −680 ms), but **0.46 is not the number a clean body will
   produce**, and the proof-(a) bar of 0.35 sits *above* the only clean-body measurement anyone
   has. Flagged, not silently accepted.
2. **"The flamingo's raised leg especially."** The flamingo is the **only** pose that survives.
   Star, bear and frog are the casualties.
3. **"Take the OpenAI Realtime audio … in `lk_bridge.py`."** The Realtime audio never enters
   `lk_bridge.py`. It goes Realtime → `rt_lk.py` → `POST /humanaudio` → the engine. The resample
   to 16 kHz already happens there (`pcm24_to_wav16`). That is why the audio work is in
   `rt_lk.py`, which is in git and reviewable, rather than guessed into a file nobody can read.
4. **`DITTO_EYE_HOLD=1`** is in the brief's known-good list but is **not** in
   `profiles/live_trio_nova.json`; `ditto_server.py` defaults it to `0`. DITTO-TRY ran it `=1`
   and measured `eye_holds: 0` — it was never needed on that body. Keep it on; it costs nothing
   and prevents a hard crash when her head turns.
5. **The gate rejects everything Nova has.** Not a contradiction with the brief, but worth saying
   plainly: `nova-ab` rendered its A/B on bodies that both gate **REJECT**, deliberately. Do not
   read "Ditto works on Nova" as "a Nova body has ever passed the gate". None has.

## Cost

$0.00. No pod, no fal, no GPU. Everything above is CPU work in this container.
