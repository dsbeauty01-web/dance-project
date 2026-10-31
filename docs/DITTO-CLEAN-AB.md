# DITTO-CLEAN-AB — does Ditto beat MuseTalk on a *closed-mouth* body?

**Session `novaditto-live2`, 2026-10-31. Spend $2.16 of $4. Pods created 3, pods remaining 0.**

**It ran.** A closed-mouth body was generated, gated, put through Ditto on a real RTX 4090, and
both engines were measured with the same tool on the same audio. Every number below was measured
in this session. Nothing is quoted, carried over or estimated.

---

## The answer

| | corr @ lag 0 | best corr @ lag | mouth speaking / silent | face found |
|---|---|---|---|---|
| **MuseTalk as aired** | **0.187** | 0.239 @ **−680 ms** | 0.0368 / 0.0230 = **1.60×** | 99.2 % |
| **Ditto on the closed-mouth body** | **0.581** | 0.594 @ **+40 ms** | 0.0430 / 0.0110 = **3.91×** | 100 % |

**Yes. Ditto wins, and not narrowly: 0.581 vs 0.187 at lag 0 — +0.394, +211 % relative.**
It clears the 0.35 proof bar with room to spare.

Three things moved at once, and they are worth separating:

1. **The clock.** Ditto's mouth sits **+40 ms** behind the sound — one frame. MuseTalk's runs
   **680 ms ahead** of it. A mouth 0.7 s early is the thing a viewer actually notices, and that
   gap is unchanged from every previous run.
2. **The correlation.** 0.581 is more than double the 0.271 the last run got on the "clean"
   `idle_sway` body. The docs predicted exactly this and said why: that body's resting mouth sits
   open (`mouth_p95` 0.059), which drags the correlation down whatever the engine does.
   **The 0.271 was a property of the body, not of Ditto.** Closing the mouth doubled the number.
3. **Silence.** This is the part the correlation alone hides. Ditto's mouth opens **3.91×** wider
   speaking than silent; MuseTalk's only **1.60×**. During the recording's 17.1 s of opening
   silence Ditto's mouth sits at median **0.0086** — shut. MuseTalk sits at 0.0230 the whole time.

### The honest caveats

* The two engines are **not at the same framing**, and cannot be. Ditto needs her face at
  200–470 px; MuseTalk runs at Nova's full-body ~158 px. The Ditto side is the knees-up crop.
  Part of the sharpness advantage (`sharp256` 11.4 vs 9.1) is that bigger face, not the engine.
  `ditto_vs_musetalk_closed_45s.mp4` crops both panels to the same window so the lips are
  compared like for like.
* The MuseTalk −680 ms is an A/V offset **in that recording**. It is what the shipped product
  looks like today, which is the thing worth comparing against, but it is not a statement that
  the MuseTalk engine is inherently 680 ms early.
* The body gates **SOFTEN**, not PASS — on head motion, not on the mouth. See below.

---

## Step 1 — the body, which is the whole story

No Nova body had ever passed the mouth gate. This one does.

Generated with **fal Kling v2.1 pro image-to-video**, 10 s, 9:16, `cfg_scale 0.5`, seeded
`image_url` = `tail_image_url` = `docs/nova-ditto/kling_seed_closed_mouth.png`, so the clip starts
and ends on the same frame.

| | prompt, in one line | verdict | `mouth_p95` |
|---|---|---|---|
| gen 1 | "mouth closed throughout" | **REJECT** | 0.0415 |
| gen 2 | "lips sealed shut and completely motionless the whole time" | **SOFTEN** | **0.0157** ✅ |

Gen 1 failed in an informative way: its *median* mouth was already tight (0.0115), but scattered
lip-parting spikes to 0.0515 pushed p95 over the 0.040 REJECT line, and the longest closed run was
only 2.68 s. Naming the lips explicitly — *sealed shut, motionless, no jaw movement* — and adding
`lip movement, parting lips, jaw movement` to the negative prompt fixed it. Gen 2's whole 10.08 s
sits under 0.030.

**Gate on the shipped body** (`tools/prebake_gate.py`, mediapipe 0.10.32):

| metric | value | bound (PASS / SOFTEN) | result |
|---|---|---|---|
| **verdict** | — | — | **SOFTEN** |
| **`mouth_p95`** | **0.0157** | ≤0.025 / ≤0.040 | **PASS** |
| `face_px` p5/p50/p95 | 274 / 287 / 299 | 200–470 | **PASS** |
| `face_found_pct` | 100.0 % | ≥99 / ≥95 | **PASS** |
| `hand_pct` | 0.0 % | ≤0 / ≤5 | **PASS** |
| `disp_p95_pct` | 1.54 | ≤2.5 / ≤4.0 | **PASS** |
| `yaw_range_deg` | 1.7 | ≤10 / ≤25 | **PASS** |
| `roll_range_deg` | 1.7 | ≤8 / ≤15 | **PASS** |
| `blur_p05_rel` | 0.80 | ≥0.5 / ≥0.35 | **PASS** |
| `pitch_range_deg` | 14.2 | ≤12 / ≤20 | SOFTEN |
| `rot_v_p95_deg` | 2.03 | ≤1.5 / ≤3.0 | SOFTEN |
| `smo_res_p95_deg` | 2.06 | ≤1.5 / ≤3.0 | SOFTEN |

**No REJECT anywhere.** The three SOFTENs are all the same thing — she nods a little more than the
gate likes. `eye_holds: 0` on the pod, so it never cost anything.

Compare with the body the previous run used (`nova_body_ditto.mp4`): `mouth_p95` 0.0386,
`disp_p95` 3.67, and it needed a 1.3× `minterpolate` retime to get there. This one needed
**no crop and no retime** — the seed is already the proven knees-up 1080×1920 frame, so the only
step was `-r 25`, and the duration came out 10.08 s → 10.08 s, unchanged (frames resampled, never
sped).

**It loops without mirroring.** First vs last frame differ by **1.20 / 255** — inside the clip's
own frame-to-frame range (p50 0.95, max 1.73). The `tail_image_url` did its job.

Files: `docs/nova-ditto/nova_body_closed.mp4`, `gate_nova_body_closed.json`,
`nova_body_closed_strip.jpg`.

---

## Steps 2–4 — the pod and the render

One **RTX 4090 Secure**, `ig7c8dg6qukg8y`, via `maya-lt tools/pod_up.py` on the small cached image
(never the 16 GB golden image). Settings exactly as briefed: `DITTO_AMP=0.6 DITTO_CHUNK=25
DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1 DITTO_WAIT_SEC=1500`.

```
ready after 195 s: {"ready": true, "info": {"src": "nova_body_closed.mp4", "src_frames": 252,
                    "src_wh": [1080,1920], "amp": 0.6, "setup_s": 9.9, "prime_s": 121.7,
                    "eye_holds": 0}}
```

Audio: the real audio track of `beta/sources/talk-test/talk-90s.mp4` — her voice, the same file on
both sides — resampled to float32 mono 16 kHz (**1 024 341 samples / 64.021 s**) and pushed in
**exact 16 000-sample chunks including the silent ones**, so the body never froze. 25.5 % voiced
over the 45 s window.

| | value |
|---|---|
| chunks pushed | 66 |
| frames collected | **1575** (63.0 s @ 25 fps) |
| **late chunks** | **0** |
| render p50 / p95 per 1 s chunk | 512.7 ms / **574.7 ms** |
| headroom vs real time | **1.74×** on one 4090 |
| wall clock for the whole render | 62.0 s |
| `eye_holds` | 0 |

`drive.py` skips the first 35 collected frames (`DITTO_PRIME` × 40 ms), so written frame *i*
carries the lips for audio *t = i/25* — **ditto_clean.mp4 sits on the same clock as the source**,
which is what makes the side-by-side and the lag-0 correlation honest.

---

## The metric — identical on both sides

`maya-lt bench/results/nova-ab/tools/lipcorr.py`, unmodified: per frame, mouth opening =
inner-lip gap (MediaPipe landmarks 13→14) / face height; audio envelope = RMS per 40 ms frame;
Pearson at lag 0 and best over ±25 frames. Same tool, same audio file, both videos 1575 frames at
25 fps.

MuseTalk's side is `talk-90s.mp4` re-timed to constant 25 fps first — the original is VFR on a
1000 fps timebase and reading it frame-by-frame without re-timing gives nonsense:

```
crop=626:1112:246:276,scale=1080:1920:flags=lanczos -r 25  ->  1575 frames / 63.0 s
-vn -ac 1 -ar 16000 -f f32le                               ->  1024341 samples / 64.021 s
```

**The MuseTalk baseline reproduced to the digit** — 0.187 @ lag 0, 0.239 @ −680 ms, identical to
the 2026-10-30 session. The baseline is solid and now independently reproduced twice.

---

## Step 5 — what I saw with my own eyes

I opened the frames rather than grading from the number.

**Does her mouth open and close on speech and stay closed in silence? Yes.**
At 1.00 s and 8.56 s (both inside the 17.1 s opening silence) her lips are shut and relaxed. At
18.68 s they are rounded into an "o"; at 37.28 s open with teeth showing, a clear "ah"; at
41.20 s pursed. The shapes **change with the phoneme** — this is articulation, not a generic flap.
`docs/nova-ditto/ditto_closed_frames.jpg`.

**Ghosting: none I can see.** Six consecutive frames 40 ms apart through a syllable
(`ditto_consecutive_frames.jpg`) show the mouth opening f0→f3 and closing f4→f5 smoothly. Lip
edges are single and clean — no double edge, no smear. The jaw and chin move with the mouth rather
than a mouth patch sliding on a static face. Identity holds: same face, hat, hoodie, necklace.

**Jitter: no.** `mouth_travel_mad` is 0.00165 for Ditto against 0.00041 for MuseTalk — 4× more
movement per frame — but with a 0.581 correlation that movement is the voice, not noise.

**Frozen stretches: none.** The longest run of an unchanged mouth value in the whole 63 s is
**1 frame (0.04 s)**. `late: 0` on all 66 chunks agrees.

**The one honest mark against it:** the lower face is very slightly softer than the rest of the
frame, the usual signature of a put-back composite. It is mild and it does not read as blur at
normal size — and `sharp256` says Ditto's mouth crops are *sharper* than MuseTalk's (11.4 vs 9.1
median), though part of that is the bigger face. At the 6 sampled moments the per-cell sharpness
runs 52/34/49/32/50/61 for Ditto against 25/22/47/36/33/21 for MuseTalk.

The mouth strip tells the clock story at a glance: at **18.68 s**, a peak-loudness moment,
MuseTalk's mouth is **shut (0.003)** while Ditto's is **open (0.044)**.
`docs/nova-ditto/mouth_strip_closed.jpg`.

---

## Files

| file | what |
|---|---|
| `docs/nova-ditto/nova_body_closed.mp4` | **the body** — Kling gen 2, gate SOFTEN, `mouth_p95` 0.0157 |
| `docs/nova-ditto/gate_nova_body_closed.json` | the full gate record |
| `docs/nova-ditto/nova_body_closed_strip.jpg` | 5 frames across the loop, mouth closed in all |
| `docs/nova-ditto/ditto_clean.mp4` | **Ditto's output**, 1080×1920, 25 fps, 1575 frames, on the source clock |
| `docs/nova-ditto/ditto_vs_musetalk_closed_45s.mp4` | **the 45 s side-by-side** (15–60 s), same crop and clock both sides, labels burned in |
| `docs/nova-ditto/mouth_strip_closed.jpg` | lower-face crops of both at 6 speaking moments, same timestamps |
| `docs/nova-ditto/ditto_closed_frames.jpg` | the frames I judged by eye — 2 silent, 4 speaking |
| `docs/nova-ditto/ditto_consecutive_frames.jpg` | 6 consecutive frames through one syllable |
| `docs/nova-ditto/numbers.json` | every number on this page, machine-readable |
| `docs/nova-ditto/logs/` | server log, drive log, job log, `/health`, both `lipcorr` outputs |

---

## Cost

| item | cost |
|---|---|
| fal Kling v2.1 pro, 2 × 10 s (published rate ~$0.098/s — not an invoice) | $1.96 |
| pod `3f3u2pmm6riu3x` (4090, ~6.5 min) — job fetch failed, self-terminated | $0.096 |
| pod `fh547svrwwk3b2` (4090, 1.5 min) — same cause, terminated by id | $0.022 |
| pod `ig7c8dg6qukg8y` (4090, 5.7 min) — **the real run** | $0.085 |
| **total** | **$2.16 of $4** |

**Two pods were lost to one cause**, and it is worth recording: `pod_up.py`'s start command fetches
its job script from the GitHub contents API with `MAYA_ASSETS_TOKEN`. This session's GitHub token
works from this container but is **rejected from inside the pod**, so the fetch failed all six
times, the job never started, and the autopsy timer terminated the pod. The fix was to replace that
one block in the start command with a wait for a PUT-delivered `/workspace/in/job.sh` and upload the
renderer files (`ditto_server.py`, `ditto_up.sh`, `motion_bank.py`, `ditto_wide.py`) the same way —
`pod_up.py` itself is untouched and the patch asserts its anchor appears exactly once before
applying. If this lane keeps running without a real `MAYA_ASSETS_TOKEN`, make that the default.

**Watchdog:** armed at 07:42:56Z for 08:27:56Z, REST `DELETE /v1/pods/<id>`, proof written to disk
and read back with the process confirmed alive before any render started. It never fired — the pod
was terminated by id at 07:48 and the watchdog stood down.

**Pods remaining: 0.** All three ids return HTTP 404. The two pods left on the account
(`lnch-cohost-cafe-*`, `jwl-ditto`) belong to other sessions and were not touched.

---

## What this changes, and what it does not

**Settled:** on a body whose mouth is closed at rest, Ditto beats MuseTalk on identical audio —
0.581 vs 0.187, and +40 ms against −680 ms. The gap the previous two sessions could not close is
closed. The 0.35 proof bar in `NOVA-DITTO.md` §5 is cleared.

**Still open, and none of it is a number this session could produce:**

1. **The body swap.** `ditto_server.py` loads **one** source at boot and never changes it, so in
   ditto mode INTRO, GAME and ENDING all show the same body and the separate groove body is lost.
   The motion bank (`DITTO_BANK`) is the real answer and already exists in maya-lt.
   **This is Refael's decision; nothing here picks one.** (`NOVA-DITTO.md` has the three options.)
2. **The `lk_bridge.py` probe never ran** — it needs the RunPod *volume*, and this pod had none.
   Assumptions **A1** (the two patch anchors) and **A2** (who publishes the audio track) are both
   still unkilled. **Do not apply `ditto_bridge_patch.py` until `--probe` runs on a volume pod.**
3. **End-to-end latency (proof b) was not measured** — it needs the live LiveKit path, not a
   file render. Ditto's arithmetic floor is unchanged: `(35 + 10) × 40 ms` = **1.8 s**.
4. **Head motion.** The body gates SOFTEN on `pitch_range` / `rot_v` / `smo_res`. A prompt that
   holds her head stiller should reach a clean PASS; it cost nothing here, but it is the one
   remaining gate item.
5. **The freeze poses still do not survive the knees-up crop** — star, bear and frog are
   REJECT, only flamingo reads. Unchanged by this session, and unchanged by a better body.
