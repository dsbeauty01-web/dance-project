# Ditto try — gate verdicts, face size, and a Ditto vs MuseTalk side-by-side

Lane: `DITTO-TRY`, 2026-10-29. Code pulled from `dsbeauty01-web/maya-lt` @ `lane/motion-transfer`
(`tools/prebake_gate.py`, `maya-ops/lt/ditto_server.py`, `maya-ops/lt/ditto_up.sh`,
`bench/replace_musetalk_alt/ditto_wide.py`). Nothing merged; nothing wired into `lk_bridge.py`.

## 1. Headline

The brief assumed our bodies are ~183 px face and that Ditto would answer SOFTEN or FAIL
because of that. Measured, it is worse and different:

* Her real face height is **~158 px**, not 183 (forehead landmark 10 → chin landmark 152,
  scaled to a 1920-high delivered frame).
* At our full-body framing the gate's verdict is **REJECT with `face_found_pct = 0.0`** —
  MediaPipe does not find her face in a single frame, even with the whole frame upscaled 3×.
  That matters beyond the gate: `ditto_server.py` takes its **first-frame crop from MediaPipe**
  (`DW.patch_first_frame_crop`), so **Ditto cannot start on these sources at all**. It is a hard
  blocker, not soft lips.
* The fix did **not** need a new generated body and did **not** cost anything: a 9:16 **crop**
  (knees-up, zoom ≈1.72×) puts her face at **~298 px**, inside Ditto's 200–470 band, and makes
  her detectable on 100% of frames.
* Once face size was out of the way, the **real** blockers appeared: her **mouth is open** in
  these clips, and her **head moves too fast between frames**. Those, not face size, are what
  the gate actually rejects.

MuseTalk is comfortable at today's full-body framing (its wide band is crisp ≤245 px, good
≤365 px — her 158 px sits well inside it). Ditto is not. **Moving Nova to Ditto forces a reframe.**

## 2. Gate verdicts — exactly as the tool printed them

`python3 tools/prebake_gate.py <clip> --face face_landmarker.task --hand hand_landmarker.task`
(mediapipe 0.10.14, the same pin `ditto_up.sh` installs). Verdicts are PASS / SOFTEN / REJECT —
the tool has no "FAIL".

### 2a. The two clips named in the brief, as they are today

| clip | verdict | face_found_pct | why |
|---|---|---|---|
| `freezegame/idle_sway.mp4` | **REJECT** | **0.0 %** | no face found in any of 121 frames |
| `beta/sources/groove-1080/round2/D-take2.mp4` | **REJECT** | **0.0 %** | no face found in any of 242 frames |

Both are 1076×1924 @ 24 fps (Ditto renders at a fixed 25 fps).

### 2b. Face height actually measured (detector run on a head-region crop)

| body | face px in source | delivered px (1920-high frame) |
|---|---|---|
| `idle_sway` | 158.3 | 158.0 |
| `D-take2` | 156.5 | 156.1 |
| `E-take1` | 157.3 | 156.9 |
| `C-take2` | 157.4 | 157.1 |

Ditto's band is 200–470 px (PASS), 180–520 px (SOFTEN). All four are below even the SOFTEN floor.

### 2c. After the free reframe (9:16 crop → 1080×1920, 25 fps)

| body | verdict | face p5/p50/p95 | non-PASS checks |
|---|---|---|---|
| `idle_sway` | REJECT | 272/283/321 | roll, disp_p95, rot_v, smo_res, mouth **REJECT**; pitch, disp_max SOFTEN |
| `D-take2` | REJECT | 279/299/325 | disp_p95 **REJECT** (4.69), mouth **REJECT** (0.0404); rot_v, smo_res SOFTEN |
| `E-take1` | REJECT | 269/289/325 | yaw_range 52.1° — she turns her head away; 8 further REJECTs |
| `C-take2` | REJECT | 282/300/321 | smo_res, mouth **REJECT** (0.0661 — mouth sits open); disp, rot_v SOFTEN |

Face size is solved for all four. The two best fail on **complementary** single metrics:
D-take2's head moves too much, C-take2's mouth is open.

### 2d. The body we shipped — `nova_body_ditto.mp4`

`D-take2` → 9:16 crop `622:1112:236:280` → **1.3× slower** (ffmpeg `minterpolate`, mci/aobmc/bidir)
→ `scale=1080:1920:lanczos` → 25 fps → first **315 frames = 12.60 s**.

| metric | value | bound | result |
|---|---|---|---|
| verdict | — | — | **SOFTEN** |
| face_found_pct | 99.7 % | ≥99 / ≥95 | SOFTEN |
| face_px p5/p50/p95 | 280 / 298 / 325 | 200–470 | **PASS** |
| disp_p95_pct | 3.67 | ≤2.5 / ≤4.0 | SOFTEN (was 4.69 = REJECT) |
| rot_v_p95_deg | 2.43 | ≤1.5 / ≤3.0 | SOFTEN |
| smo_res_p95_deg | 2.17 | ≤1.5 / ≤3.0 | SOFTEN |
| mouth_p95 | 0.0386 | ≤0.025 / ≤0.040 | SOFTEN |
| hand_pct | 0.0 % | ≤0 / ≤5 | PASS |

No REJECT anywhere — this clears the "PASS or SOFTEN" bar. Slowing her 1.3× is what moved
`disp_p95` under the line; the threshold's own provenance note says clips at ≥3.9 **lost the face**
in Ditto, so this was a real risk, not a cosmetic one.

## 3. What was NOT done

* **The fal / Kling v2.1 step was not run.** There is no `FAL_KEY` in this environment or in
  either repo, so fal could not be called at all. It also turned out not to be needed — the free
  reframe plus retime reached SOFTEN. If a new body is still wanted later, the brief's prompt
  (gentle groove, head steady, **mouth closed**) is aimed at the right targets — just note that
  the reason is mouth + head motion, not face size.
* Nothing wired into `lk_bridge.py`. Nothing merged.

## 4. Files

| file | what |
|---|---|
| `docs/ditto-try/ditto_vs_musetalk_45s.mp4` | **the side-by-side** — left MuseTalk at today's full-body framing, right Ditto knees-up, same 45 s of audio |
| `docs/ditto-try/ditto_vs_musetalk_face_45s.mp4` | same 45 s, both cropped to the **same face size** so the lips are judged on the engine |
| `docs/ditto-try/ditto_45s.mp4` | Ditto's raw output, 1080x1920, 25 fps, 44.84 s |
| `docs/ditto-try/nova_body_ditto.mp4` | the gated body (**SOFTEN**), ffmpeg 6.1.1 build |
| `docs/ditto-try/nova_body_ditto_as_rendered.mp4` | the pod's rebuild Ditto actually rendered from (**REJECT** by 0.0007 on mouth_p95) |
| `docs/ditto-try/gate_*_ORIGINAL.json` | gate output on the two clips named in the brief, untouched (REJECT, face_found 0.0%) |
| `docs/ditto-try/gate_*_z.json` | gate output on all four candidates after the reframe |
| `docs/ditto-try/gate_nova_body_ditto.json` | gate output on the shipped body (SOFTEN) |
| `docs/ditto-try/gate_nova_body_as_rendered.json` | the pod's own gate run on its own rebuild |
| `docs/ditto-try/reframe_plan.jsonl` | the crop box computed per clip (face px before/after, zoom) |
| `docs/ditto-try/drive.log` | the render log (chunk timings, 0 late) |

## 5. The run — Ditto live on the reframed body

One RunPod **RTX 4090 Secure**, pod `ux7hakwgkkjrda`. `ditto_up.sh` installed its own Python 3.10
venv (torch 2.5.1 cu121 + TensorRT 8.6.1) and pulled the TRT weights in **78 s**; the server was
`ready` **211 s** after start. Settings exactly as briefed:
`DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1`.

```
ready: {"src":"nova_body_ditto.mp4","src_frames":315,"src_wh":[1080,1920],"amp":0.6,
        "out_wh":[1080,1920],"setup_s":7.1,"prime_s":121.3,"eye_holds":0}
```

`eye_holds: 0` — her head never turned far enough to lose the eye landmarks, so the
`DITTO_EYE_HOLD` guard was never needed on this body.

Audio: the real audio track of `beta/sources/talk-test/talk-90s.mp4`, **15–60 s** (45 s, six
speech bursts, 40 % voiced — the silence also exercises Ditto's VAD gate), resampled to float32
mono 16 kHz and pushed in 1-second chunks (16 000 samples) to `POST /render`.

| | value |
|---|---|
| frames returned | 1121 (44.84 s @ 25 fps) |
| late chunks | **0** |
| render p50 / p95 per 1 s chunk | 351.7 ms / 389.2 ms |
| headroom vs real time | **2.84×** on one 4090 |

### Honest note on the body the render actually used
The pod rebuilt the body from the same recipe, but with **ffmpeg 4.4.2** (this container has
6.1.1), and `minterpolate` is not bit-identical across versions. The pod's own gate run on its own
rebuild came out **REJECT**, on one metric, by a hair: `mouth_p95 = 0.0407` against a 0.0400
bound (everything else SOFTEN, face 280/299/327). The locally built file that scored SOFTEN had
`mouth_p95 = 0.0386`. So: the shipped `nova_body_ditto.mp4` gates **SOFTEN**; the frames Ditto
actually rendered came from a near-identical rebuild that gates **REJECT by 0.0007** on mouth
opening. Pin one encoder before this becomes a real bake.

## 6. Ditto vs MuseTalk — measured, not eyeballed

Per frame: mouth opening = inner-lip gap (landmarks 13→14) / face height; audio envelope = RMS
per frame; Pearson correlation over lags −12…+12 frames. Same 45 s of the same audio for both.
MuseTalk was measured on a constant-25-fps copy (`talk-90s.mp4` is VFR on a 1000 fps timebase —
reading it frame-by-frame without re-timing gives nonsense).

| metric | MuseTalk (today) | Ditto (new) | |
|---|---|---|---|
| lip↔audio correlation at lag 0 | 0.266 | **0.516** | ~2× better |
| best correlation | 0.358 | **0.535** | |
| lag of best correlation | **−11 frames (−440 ms)** | **+1 frame (+40 ms)** | Ditto is locked |
| mouth open while speaking | 0.0377 | **0.0556** | |
| mouth open while silent | 0.0207 | 0.0227 | both close properly |
| speaking ÷ silent | 1.82× | **2.45×** | Ditto separates speech from silence better |
| mouth travel per frame (MAD) | 0.00322 | **0.00467** | +45 % more lip movement |
| face found | 100 % | 100 % | |
| delivered face height | 158.7 px | 302.5 px | different framing — see below |

**Read it this way:** Ditto's lips track the voice about twice as closely and land within one
frame of the audio. The −440 ms on the MuseTalk side is an A/V offset in *that recording*, not a
verdict on the engine, but it is what the existing clip actually looks like.

The two engines are **not at the same framing** — Ditto needs the knees-up reframe to work at
all, MuseTalk runs at full body. `ditto_vs_musetalk_45s.mp4` shows each at its real framing (the
actual product choice); `ditto_vs_musetalk_face_45s.mp4` crops both to the same face size so the
lips are judged on the engine, with MuseTalk's panel upscaled 1.9× from its native delivery.

## 7. Cost

| item | cost |
|---|---|
| pod `9rifh2o1o6gkww` (4090, 9.8 min) — unreachable, terminated | $0.145 |
| pod `ux7hakwgkkjrda` (4090, 7.5 min) — the real run | $0.112 |
| fal | $0.00 (no key; not needed) |
| **total** | **$0.26 of $4** |

Watchdog armed at 14:05:42Z for 14:50:42Z; pod terminated at 14:13:02Z and the watchdog stood
down. 0 of this lane's pods left running (`lkv2-body` belongs to another session and was not
touched).

## 8. What I'd do next

1. **Decide the framing question first** — it is the real decision, not the engine. Ditto requires
   her face at 200–470 px; today she is at ~158 px. Either Nova gets reframed knees-up, or Ditto
   is out.
2. If reframing is acceptable, **bake a proper body**: a 10–15 s loop, mouth closed throughout
   (`mouth_p95 ≤ 0.025`), gentle groove, head steady. That removes the retime hack and should
   reach a clean PASS. The brief's Kling prompt is the right prompt — the reason is mouth and
   head motion, not face size.
3. Pin one ffmpeg build for body bakes.
4. Only then wire `lk_bridge.py`.
