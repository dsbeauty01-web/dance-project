# DITTO-FULLBODY — Ditto on Nova at FULL-BODY framing, and the live-path probe

**Session `novaditto-fullbody`, 2026-10-31. Spend $2.17 of $4. Pods created 3, pods remaining 0.**

Two things were proven here, both measured in this session, nothing carried over or estimated:

1. **Ditto runs at full-body framing.** It was a hard blocker before ("Ditto cannot start on these
   sources at all" — DITTO-TRY §1). It is not any more, and the fix is ten lines.
2. **The live path's second assumption is false.** `ditto_bridge_patch.py --probe` ran on the real
   `/workspace/lk_bridge.py` for the first time. Anchors **A1 confirmed**, **A2 killed and wrong**.

What was **not** done: the live LiveKit recording. Why, exactly, is in §7.

---

## 1. The key insight — tested first, for free, before any money

The claim: full-body "fails" not because of Ditto and not because of resolution, but because
MediaPipe's short-range detector works on the face's **fraction** of the image, and at full-body
framing Nova's ~158 px face is 8 % of a 1924-high frame.

`tools/pod/ditto_fullbody.py` + `roi_probe.py`, MediaPipe 0.10.32, 3 clips × 3 frames:

| pass | `idle_sway` | `D-take2` | `E-take1` | total |
|---|---|---|---|---|
| **the whole frame** (what Ditto does today) | 0/3 | 0/3 | 0/3 | **0/9 found** |
| **the whole frame upscaled 3×** | 0/3 | 0/3 | 0/3 | **0/9 found** |
| **top third of the frame, upscaled 3×** | 3/3 | 3/3 | 3/3 | **9/9 found** |

Face height where it was found: **154–172 px**, mapped back to full-frame coordinates.
On the whole of `idle_sway.mp4` the ROI path finds her in **121/121 frames**.

**The insight is correct, and the 3× line is the proof.** Upscaling the whole frame 3× gives
MediaPipe exactly the same pixels at 3× the resolution and it still finds nothing; cropping to the
top third at the same 3× finds her every time. It is the fraction, not the pixels.

---

## 2. What the code can and cannot be told — with the code quoted

### Can a crop box be supplied explicitly? **No, not as the code stands.**

`bench/replace_musetalk_alt/ditto_wide.py`, the whole of the relevant function:

```python
def patch_first_frame_crop(lm_model):
    """Source2Info._crop without InsightFace (non-commercial): MediaPipe 478 -> 5 points -> Ditto's own crop + 203 lmk."""
    from core.atomic_components import source2info as S
    from core.utils.crop import crop_image
    det = mp_landmarker(lm_model)
    orig = S.Source2Info._crop

    def _crop(self, img, last_lmk=None, **kw):
        if last_lmk is not None:
            return orig(self, img, last_lmk=last_lmk, **kw)
        p = det(img)                                        # <-- THE WHOLE FRAME
        if p is None: raise RuntimeError("mediapipe: no face in the first source frame")
        pt5 = np.stack([p[[33, 133]].mean(0), p[[362, 263]].mean(0), p[1], p[61], p[291]]).astype(np.float32)
        ext = float(np.ptp(pt5[:, 1])); oval_h = float(p[152][1] - p[10][1])
        cd = crop_image(img, pt5, dsize=self.landmark203.dsize, scale=1.5 * oval_h / max(ext, 1.0), vy_ratio=-0.1, pt_crop_flag=False)
        lmk203 = self.landmark203(cd["img_crop"], cd["M_c2o"])
        return orig(self, img, last_lmk=lmk203, **kw)
    S.Source2Info._crop = _crop
```

It takes `lm_model` and nothing else — no `roi`, no `box`, no `pt5` argument anywhere in the chain,
and `ditto_server.py` line 88 calls it as `DW.patch_first_frame_crop(lm)`. So a box cannot be
handed in today.

**But the geometry channel already exists.** The first line of `_crop` is an early return on
`last_lmk is not None`, and the last line is `orig(self, img, last_lmk=lmk203, **kw)`. Source frames
1..N already go down that path — Ditto's own 203-point tracker, no detection. **Only frame 0 needs a
detection, and the only thing wrong with it is the region `det` is given.**

### Does paste-back return the FULL original frame? **Yes — nothing to add.**

`DW.LowerPutBack.__call__`, the end of it:

```python
        m = cv2.warpAffine(self.mask, Mr, sz, flags=cv2.INTER_LINEAR)[..., None]
        r = cv2.warpAffine(render, Mr, sz, flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        f = frame_rgb[y0:y1, x0:x1].astype(np.float32)
        ...
        out = frame_rgb.copy()
        out[y0:y1, x0:x1] = np.clip(m * r + (1 - m) * f + 0.5, 0, 255).astype(np.uint8)
        return out
```

`frame_rgb` is the untouched source frame; `out` is a copy of it with only the warped
lower-face box blended in, and `m` is a Gaussian-feathered oval (`lower_face_mask`:
`cv2.GaussianBlur(m, (0,0), k/2.0)`, `feather=0.045` of face width) with a skin-ring colour match.
So it is a soft-edged oval composite, not a rectangle, and the returned frame is the full frame at
full size. Hand it a full-body frame and it gives back a full-body frame.

### The shim — `tools/pod/ditto_fullbody.py` (ours, 10 lines of real logic)

`patch_first_frame_crop` builds its detector with `det = mp_landmarker(lm_model)`, resolved from the
`ditto_wide` module namespace **at call time**. So replacing `DW.mp_landmarker` with a wrapper
*before* `patch_first_frame_crop` runs changes the detector and nothing else:

```python
def factory(model):
    base = orig_factory(model)
    def det(rgb):
        p = base(rgb)                      # pass 1: exactly the stock behaviour
        if p is not None: return p
        for r, u in tries:                 # pass 2: the explicit box (or the ROI ladder), upscaled
            q = _detect_in(base, rgb, r, u)
            if q is not None: return q     # ...mapped back to full-frame pixels
        return None
    return det
DW.mp_landmarker = factory
```

* **maya-lt is not touched** — no file there is edited, patched or copied over. `pod_up.py` is not
  modified either (its START is patched in memory by our own launcher, §6).
* It is a **no-op wherever detection already works**: the stock full-image pass runs first.
  `LowerPutBack._build` also uses `mp_landmarker`, on the 512 render crop, where the stock pass
  always succeeds — so that call site is unaffected. Knees-up sources behave exactly as before.
* It is injected on the pod by a `sitecustomize.py` on `PYTHONPATH`, guarded by `DITTO_FB_ON=1`,
  which imports `ditto_wide` into `sys.modules` first and installs the wrapper. `ditto_server.py`
  then reuses the patched module. Its log goes to **stderr**, never stdout, because `ditto_up.sh`
  captures the stdout of `python -c "import site; print(...)"` calls.
* `DITTO_FB_BOX="x0,y0,x1,y1"` supplies the explicit box, computed once on CPU off the pod by
  `ditto_fullbody.box_from_clip()`. `--selftest` passes 5/5.

On the pod the server logged, on the real body:

```
[ditto_fullbody] installed: explicit_box=[263.0, 215.0, 763.0, 715.0] up=3.0 rungs=5
[ditto_fullbody] ROI hit on a 1074x1920 frame: roi=[263, 215, 763, 715] up=3.0 face_px=156.9
                 (stock full-frame pass found nothing)
```

That one line is the whole story: the stock pass found nothing on the full-body frame, the explicit
box found her at 156.9 px, and Ditto started.

---

## 3. Does full-body paste-back work? **Yes.**

One RTX 4090 Secure in EU-RO-1, pod `ztxmaapx2qyrxl`, Nova's volume `1ditrne6cb` mounted.

```
ready after 181 s: {"src": "body_a.mp4", "src_frames": 252, "src_wh": [1076, 1924],
                    "amp": 0.6, "out_wh": [1076, 1924], "setup_s": 9.6, "prime_s": 121.7,
                    "eye_holds": 0}
```

| | calm full-body | dance full-body (`D-take2`) |
|---|---|---|
| source | 1076×1924, **uncropped** | 1076×1924, **uncropped** |
| frames written | **1599** (63.96 s) | 498 (19.92 s) |
| **late chunks** | **0** of 67 | **0** of 23 |
| render p50 / p95 per 1 s chunk | 370.3 / **480.6 ms** | 377.5 / 411.9 ms |
| headroom vs real time | **2.08× at p95** | 2.43× at p95 |
| `putback_ms_p95` | 5.4 ms | 5.5 ms |
| `eye_holds` | 0 | 0 |

### What I saw in the frames myself

`docs/nova-ditto/fullbody_face_sheet.jpg` — eight 500×500 windows of the full-body frame, same
window every time, three silent moments and five speaking ones:

* **Silent (1.0 s, 8.5 s, 30.0 s): her mouth is shut** and relaxed, a slight closed smile.
* **Speaking (18.7, 37.3, 41.2, 55.0, 58.0 s): open, and the shapes differ** — a rounded "o" at
  41.2 s, open with the jaw down at 37.3 s, barely parted at 55.0 s. Articulation, not a flap.
* **Seam: none that I can see.** No rectangle edge, no step in skin tone, no sharpness line around
  the mouth, chin or jaw. The lower face blends into the cheeks and neck continuously, and the chin
  moves with the mouth rather than a patch sliding over a static face. This is what the feathered
  oval mask plus the skin-ring colour match buys.
* **Placement: correct.** The mouth sits where her mouth is, at every frame checked.
* **Honest marks against it.** (a) At several speaking frames her eyes read as half-lowered — that
  is the *source body's* own blink, not Ditto (in video mode Ditto drives only the lip keypoints).
  (b) At full-body delivery her whole face is ~157 px, so the mouth detail is small on screen; it is
  sharp *for its size*, but it is not the knees-up picture.

`docs/nova-ditto/fullbody/fullbody_frame_speaking.jpg` is one whole 1074×1920 frame at a speaking
moment — the full figure, head to shoes, with the repainted mouth in place.

---

## 3b. Ditto vs MuseTalk, both at FULL-BODY framing — measured

`maya-lt/bench/results/nova-ab/tools/lipcorr.py`, **unmodified**, same tool and same audio on both
sides. The tool detects on the whole frame it is handed, and at full-body framing that finds
nothing — so **both videos were cropped to the same 500×500 face window** (a pure crop, no rescale,
face ~157 px in both), which is what makes the two columns comparable. MuseTalk's side is
`talk-90s.mp4` re-timed to constant 25 fps first (it is VFR on a 1000 fps timebase; reading it
frame-by-frame without re-timing gives nonsense).

| | **corr @ lag 0** | best corr @ lag | mouth speaking / silent | ratio | `sharp256` | face found |
|---|---|---|---|---|---|---|
| **MuseTalk as aired** | **0.206** | 0.279 @ **−960 ms** | 0.0367 / 0.0206 | 1.78× | **28.1** | 100 % |
| **Ditto, full body** | **0.563** | 0.577 @ **+40 ms** | 0.0494 / 0.0195 | **2.53×** | 16.8 | 100 % |

**Ditto wins on lip timing at full-body framing: 0.563 vs 0.206 at lag 0** — +0.357, +173 %
relative, and it clears the 0.35 proof bar of `NOVA-DITTO.md` §5.

* **The clock.** Ditto's mouth sits **+40 ms** behind the sound — one frame. MuseTalk's best
  correlation is at **−960 ms**: nearly a second early. Caveat: −24 frames is almost at the edge of
  lipcorr's ±25-frame search, so MuseTalk's true best lag may be further out still — the number is a
  floor on the offset, not a precise measurement of it. (This is an A/V offset **in that recording**,
  not a statement that the MuseTalk engine is inherently early.)
* **Silence.** Ditto opens 2.53× wider speaking than silent against MuseTalk's 1.78×, and sits at
  0.0195 while quiet. Her mouth shuts when she stops talking.
* **Movement.** `mouth_travel_mad` 0.00115 for Ditto against 0.00031 — 3.7× more lip movement per
  frame, and with a 0.563 correlation that movement is the voice, not noise.
* **No frozen stretches.** The longest run of an unchanged mouth value in the whole 63.96 s is
  **1 frame (0.04 s)**; `late: 0` on all 67 chunks agrees.

### The honest mark against Ditto here — it is SOFTER than MuseTalk at this framing

`sharp256` **16.8 for Ditto against 28.1 for MuseTalk**. This is the reverse of the knees-up result
(11.4 vs 9.1 in Ditto's favour on 2026-10-30), and it is the price of full-body: Ditto renders the
mouth in its own 512 crop and the paste-back resamples it **down** into a 157 px face, where
MuseTalk paints at the delivered resolution directly.

**It is not an artefact of the de-shear repair (§4).** Control: re-encoding the de-sheared crop one
more generation at the same crf changed `sharp256_all_median` by **0.0** (16.8 → 16.8) and the
correlation by 0.001. The softness is Ditto's paste-back at this scale, measured, not my repair.

So at full-body framing the trade is explicit: **Ditto's lips are locked to the voice and MuseTalk's
are a second out, but MuseTalk's mouth is the crisper picture.**

---

## 3c. The game-round audio does not exist — the briefed file is silent

The plan was: intro from `talk-90s.mp4`, game from `beta/sources/groove-1080/tests/rec70-beta/round-70s-beta.mp4`,
described as "85 s of a real round with her voice". **It has no voice. Measured: peak amplitude
1.0 × 10⁻⁴, RMS 1 × 10⁻⁵ over all 85.7 s — a digitally silent track**, 0 of 85 seconds above an
RMS of 0.01.

That is not a broken file, it is the phase machine working as written. `CONTEXT.md`: in GAME *"her
live voice IN THE AIR over the dancing body (engine gets NO audio)"*. The capture recorded the
LiveKit track; her game voice and the music were page-side and never entered it. The round's own
`console.log` confirms a real but headless round — 7 freeze rounds, `seen 0% held 0%`, no camera.

Everything else in the repo was checked: `round-60s-*` have **no audio stream at all**;
`nova-joined-small.mp4` is 90 s with **0 % silence** (continuous backing music, not isolated voice);
`audio/clips/*.mp3` are canned single lines from an older build, a different voice from the live
V2V one.

**So the drive track is the full 64.02 s of `talk-90s.mp4` — her real voice — split and labelled
INTRO (0–32 s) and GAME ROUND (32–64 s)**, both halves carrying real speech and real silence
(voiced 11.2 % and 30.1 % of frames respectively, 20.7 % overall). Using one coherent voice also
keeps these numbers directly comparable with the 0.581 / 0.187 already on record.
**No game-round audio of Nova's voice exists in this repo to render.** Getting one means recording a
live round with the page audio captured — which is the live-path work in §7, not a file render.

---

## 4. A bug found on the way — `out_wh` is reported from the wrong place

**`ditto_server.py` reports an output size that can be wrong, and it silently corrupts the render.**

```python
cap = cv2.VideoCapture(src); nsrc = ...; sw, sh = int(cap.get(3)), int(cap.get(4)); cap.release()
...
self.info = {..., "out_wh": list(self.col.out_wh) if self.col.out_wh else [sw, sh], ...}
```

`sw, sh` come from **the source file**. But Ditto resizes the source to `max_size = 1920` on the long
side before registering it — the pod logged `max_size <class 'int'> 1920`, and our shim logged the
frame it actually got as **1074×1920**, not 1076×1924. `/health` still advertised `[1076, 1924]`,
`drive.py` passed that to ffmpeg as `-s`, and every frame was read 2 px too wide: a progressive
diagonal shear through the whole file.

* It has never bitten before because every previous body was already 1080×1920 — inside the cap, so
  nothing was resized and the reported size happened to be right.
* **The pixel data was intact**; only the row length used to lay it out was wrong.
  `deshear.py` re-chunks the decoded byte stream at the true 1074×1920 and recovers **1599 clean
  frames / 63.96 s**. Nothing is interpolated: byte N goes to the pixel it always held. The cost is
  one extra encode generation, which is why the shipped file is `crf 14`.
* **Fixes, either alone is enough:** set `DITTO_OUT_W=1074 DITTO_OUT_H=1920` (stock env vars, no code
  change — `Collector.out_wh` then reports the truth), or pre-scale bodies to 1080×1920 so nothing is
  resized. The real repair is for `out_wh` to come from the first collected frame, not from cv2 on
  the file. **Not changed here — it is maya-lt's file.**

---

## 5. The gates — every body, with the unmodified tool

`maya-lt/tools/prebake_gate.py`, mediapipe 0.10.32, verdicts exactly as the tool printed them.
Run twice per body: plain, and with the tool's own documented `--track` flag (which retries a missed
frame on a crop around the last face — the same insight as §1, already built into the gate).

**Plain, at full-body framing, every body is `REJECT` with `face_found_pct = 0.0`** — the gate cannot
see her face at all, exactly like DITTO-TRY measured. That is the framing, not the body, and it is
why the `--track` column is the one with information in it.

| body | `--track` verdict | face_found | face_px p5/p50 | `mouth_p95` | non-PASS checks (`--track`) |
|---|---|---|---|---|---|
| **calm gen 1** | REJECT | 100 % | 154/159 | 0.0427 | `face_px_lo` **REJECT**, `mouth_p95` **REJECT**, `smo_res` SOFTEN |
| **calm gen 2 — the shipped body** | REJECT | 100 % | 151/156 | **0.0209** | **`face_px_lo` REJECT — and nothing else** |
| **`D-take2` (dance)** | REJECT | 100 % | 151/154 | 0.0423 | `face_px_lo` **REJECT**, `mouth_p95` **REJECT**, `disp_p95` SOFTEN, `smo_res` SOFTEN |
| **`E-take1` (dance)** | REJECT | 100 % | 145/155 | 0.0842 | 10 non-PASS: `yaw_range` 54.2° **REJECT**, `pitch_range` 30.3 **REJECT**, `disp_p95` 8.63 **REJECT**, `rot_v` 4.12 **REJECT**, `smo_res` 3.98 **REJECT**, `mouth_p95` **REJECT**, + 4 more |

### The shipped calm full-body body, in full

fal **Kling v2.1 pro image-to-video**, 10 s, 9:16, `cfg_scale 0.5`, `image_url = tail_image_url =`
a full-body still taken from `freezegame/idle_sway.mp4` frame 5 — chosen by scoring **mouth aperture
AND eye aperture** across all 121 frames and rejecting mid-blink (`mouth 0.0092`, `eye 0.1149`
against an eye p75 of 0.1102, both eyes open and symmetric, the sharpest of 17 candidates).

| metric | value | bound (PASS / SOFTEN) | result |
|---|---|---|---|
| **verdict** | — | — | **REJECT (on face size alone)** |
| `face_px` p5/p50/p95 | 151 / 156 / 160 | 200–470 / 180–520 | **REJECT** |
| **`mouth_p95`** | **0.0209** | ≤0.025 / ≤0.040 | **PASS** |
| `mouth_p50` | 0.0103 | — | — |
| `face_found_pct` | 100.0 % | ≥99 / ≥95 | PASS |
| `yaw_range_deg` | 1.4 | ≤10 / ≤25 | PASS |
| `pitch_range_deg` | 7.6 | ≤12 / ≤20 | PASS |
| `roll_range_deg` | 2.2 | ≤8 / ≤15 | PASS |
| `disp_p95_pct` | 0.95 | ≤2.5 / ≤4.0 | PASS |
| `rot_v_p95_deg` | 0.78 | ≤1.5 / ≤3.0 | PASS |
| `smo_res_p95_deg` | 0.84 | ≤1.5 / ≤3.0 | PASS |
| `hand_pct` | 0.0 % | ≤0 / ≤5 | PASS |
| `blur_p05_rel` | 0.85 | ≥0.5 / ≥0.35 | PASS |

**Every single check passes except face size.** Head motion is the calmest any Nova body has
measured — better than the knees-up `nova_body_closed` of 2026-10-30 on every motion metric
(`pitch_range` 7.6 vs 14.2, `rot_v` 0.78 vs 2.03, `smo_res` 0.84 vs 2.06, `disp_p95` 0.95 vs 1.54).

> **[CLI-FILL] Gen 2's prompt differs from the brief's, deliberately.** Gen 1 used the briefed prompt
> verbatim and came back `mouth_p95` 0.0427 — a REJECT, the same scattered lip-parting failure
> DITTO-CLEAN-AB hit on *its* gen 1. That session's fix was naming the lips explicitly, so gen 2 added
> "**completely motionless the whole time, no talking, no jaw movement**" and the negatives
> "parting lips, mouth opening". `mouth_p95` went 0.0427 → **0.0209**, a PASS. Both prompts are in
> `docs/nova-ditto/fullbody/`.

### Can a DANCING full-body body carry Ditto?

**Mechanically, yes — it was done here.** `D-take2`, uncropped and undoctored, registered and
rendered **498 frames with 0 late chunks and 0 eye_holds**. That is new: before this session a
dancing full-body clip could not get past frame 0.

**As a product body, `D-take2` yes-with-a-caveat, `E-take1` no.**

* The expectation in the brief was that a dancing body would break on **head motion**. For
  `D-take2` that is **wrong, measured**: `yaw_range` 5.2°, `pitch_range` 7.3°, `rot_v_p95` 1.07 —
  all **PASS**; only `disp_p95` 3.87 and `smo_res` 1.54 soften. Her head is calm while she grooves.
  What `D-take2` actually fails on is the same thing every Nova body fails on — **her mouth sits open
  while she dances** (`mouth_p95` 0.0423, over the 0.040 REJECT line) — plus face size.
* `E-take1` is the body that fails the way the brief expected, and far worse: **`yaw_range` 54.2°**
  (she turns her head away), `pitch_range` 30.3°, `disp_p95` 8.63. Not a candidate.

So the honest answer: **a dancing full-body Nova can carry Ditto, provided the dance clip is
generated with her lips sealed.** Nothing about the dancing breaks Ditto; the open resting mouth
does, and that is a prompt fix, not an engine limit — gen 2 proves the prompt fix works on a
standing body. The remaining hard limit is face size, which is framing, not the body (§8).

---

## 6. The pod, and the launcher trap that cost two pods last session

`pod_up.py`'s inline START fetches its job script from the GitHub contents API with
`MAYA_ASSETS_TOKEN`, which **fails from inside a pod** in this lane. The fix from the last run was
reused and **`pod_up.py` itself was not modified**: our launcher (`podup_fb.py`) replaces that one
block in `PU.START` in memory with a wait for a PUT-delivered `/workspace/in/job.sh`, after
asserting the anchor appears **exactly once** (a second apply is refused). Verified before booting:
anchor gone, `api.github.com` no longer in START, re-apply refused.

It worked first time: `job 08:23:10 PUT 3478 bytes`.

Attaching Nova's network volume also needed a field `pod_up.py` does not have
(`networkVolumeId` / `dataCenterIds` / `volumeMountPath`, as `dance-project/tools/pod/launch_pod.sh`
sets them). That too is wrapped in our launcher, not edited into `pod_up.py`.

**Two traps worth recording for the next session:**

1. **`/workspace/in` is on the shared volume, so a pod inherits the previous pod's `job.sh`.** Pod 2
   booted and immediately ran pod 1's stale job script — before our upload landed — and repeated its
   failure. Stage the job script on the volume *before* booting, or version it.
2. **Ditto needs the Python 3.10 C headers.** `core/utils/blend/blend.pyx` is compiled by pyximport
   at import; `runpod/pytorch:2.4.0-py3.11` has python3.10 but not `python3.10-dev`, so the server
   died with `fatal error: Python.h: No such file or directory` and `/health` reported
   `"error": "ImportError: Building module core.utils.blend.blend failed"`. One
   `apt-get install -y python3.10-dev build-essential` (5 s) fixes it. This cost pod 1.

Ditto's install itself is fast on this image: **45–52 s** for the venv, torch, TRT 8.6.1 and the
~2 GB of weights, then ~122 s of prime. Ditto was installed to `/root/ditto` (container disk), never
to the volume.

---

## 7. The live path — the probe, and why there is no live recording

The deliverable changed mid-session to: Ditto in the **real live game**, recorded. Here is exactly
how far that got and where it stopped.

### 7a. What the probe found — run on the real file, read-only

`tools/pod/ditto_bridge_patch.py --probe` on `/workspace/lk_bridge.py`
(md5 `1c4448b475ae0cdd719aef4edaa90337`, 8288 bytes, 182 lines), full output in
`docs/nova-ditto/fullbody/probe.txt`:

```
   anchors this patch needs (both must be exactly 1):
     OK   A1  return rgba.tobytes()  count=1
     OK   A2  w, h, rgba = await vq.get()  count=1
     VideoSource: 1      L138: vstate["src"] = rtc.VideoSource(w, h)
     AudioSource: 1      L120: asrc = rtc.AudioSource(AUDIO_SR, 1)
     publish_track: 2    L122 (atrack, SOURCE_MICROPHONE) · L140 (vt, SOURCE_CAMERA, simulcast)
     audio frame/capture: 3   L145 video capture · L159 AudioFrame.create · L174 asrc.capture_frame
     the downscale patch: 2   L42 def _downscale · L136 w,h,rgba = _downscale(w,h,rgba)
   already patched: no
```

**A1 — killed, and CORRECT.** Both anchors appear exactly once. The insertion points are right and
the patch would apply cleanly to this file.

**A2 — killed, and FALSE.** `NOVA-DITTO.md` assumed "the audio track is published by the LiveTalking
engine, not by `lk_bridge.py`". The probe's own stop condition is *"if `AudioSource`/`AudioFrame` is
not 0, the audio is published here and the delay belongs here instead"*. It is **not** 0.
Reading the real file confirms it — one engine socket carries both:

```python
            if kind == b'V':   ... vq.put_nowait((w, h, rgba))
            elif kind == b'A': ... aq.put_nowait(np.frombuffer(data, dtype=np.int16).copy())
```
```python
    asrc = rtc.AudioSource(AUDIO_SR, 1)
    atrack = rtc.LocalAudioTrack.create_audio_track("nova-audio", asrc)
    await room.local_participant.publish_track(atrack, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
```

**`lk_bridge.py` publishes BOTH tracks.** So the A/V delay for `NOVA_FACE=ditto` is in the wrong
place on purpose-built reasoning that turns out to be wrong. Holding `/humanaudio` back in
`rt_lk.py` does still delay the audio that reaches LiveKit (it travels engine → `'A'` → `aq` → the
bridge), but it *also* delays the engine itself and therefore the start of her turn — it adds
latency instead of applying a pure A/V offset. The correct place is **`drain_audio` / `aq` inside
`lk_bridge.py`**, holding `(prime + slack) × 40 ms` of audio frames there, where it offsets
picture-against-sound and nothing else.

**Per `NOVA-DITTO.md` §RUN-ME step 0 ("stop and say so") and the standing instruction not to apply
until the probe matches, `--apply` was NOT run. The production bridge is untouched** — the probe is
read-only and `already patched: no` is still true.

### 7b. Why there is no live recording

The live stack itself is **credential-feasible**: all four secrets `rt_lk.py` hard-requires
(`OPENAI_API_KEY`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` — bare `os.environ[...]`,
it raises without them) are **present on the volume in `/workspace/boot.sh`** (confirmed by name and
value length only; no value was read or printed). They are not in this container and not in any
RunPod template — the account has 14 templates, all stock, none carrying credentials. So the live run
*must* be driven from a volume-mounted pod, which is now a solved problem (§6).

It was not attempted because, with ~$1.8 of the $4 cap left, four things each had to work first time,
blind, with no SSH:

1. **The patch is known-wrong as written** (A2 above). Applying it unmodified would put her voice and
   lips up to 1.8 s apart on air, and it edits a **production file on the live volume**.
2. `boot.sh`'s own documented cold-load window is **15–25 min** before the stack is up.
3. A headless-Chromium harness with a fake camera and a fake mic, plus a LiveKit subscriber that
   records the received tracks to one mp4, does not exist in either repo — it would have to be
   written and debugged blind.
4. No SSH key, so every step is driven through a one-shot `dockerStartCmd` with no way to retry a
   stage without booting another pod.

Spending the remaining budget on that would most likely have ended with a half-patched production
bridge and no recording. The probe result is the thing that unblocks it, and it is now in hand.

**What the next session needs, in order:** adapt the delay into `lk_bridge.py`'s `drain_audio`
(A2 is now known, so this is no longer a guess) → boot one volume-mounted pod, run `boot.sh` from the
start command → `--probe`, then `--apply`, `NOVA_FACE=ditto` → record. Budget it as its own session;
it will not fit beside a body generation.

---

## 8. The one thing full-body cannot fix

`face_px` **151/156/160** against Ditto's PASS floor of 200 and SOFTEN floor of 180. **This is the
framing, and no body or prompt changes it** — it is the arithmetic of a full figure in a 1920-high
frame. Ditto renders her mouth at its internal crop resolution and pastes it back down into a 157 px
face, which is why the result is clean but small.

So the decision in front of Refael has not moved, and this session did not make it for him:

* **Full-body framing works now** (`LAW-FRAME-FULL` kept, the whole figure on screen, games and
  pose clips unchanged) — at a face Ditto considers undersized, with the lip detail that implies.
* **Knees-up framing** puts her face at ~298 px, inside Ditto's band, and measured **corr 0.581** on
  2026-10-30 — but it breaks `LAW-FRAME-FULL` and three of the four freeze poses (star, bear, frog)
  do not survive the crop.

What is new is that the first option now exists at all.

---

## 9. Files

| file | what |
|---|---|
| `tools/pod/ditto_fullbody.py` | **the shim** — ROI/explicit-box detector wrapper, `--selftest` 5/5, `--box` computes a box off the pod |
| `docs/nova-ditto/fullbody/nova_fullbody_calm.mp4` | **the body** — Kling gen 2, full-body, `mouth_p95` 0.0209 |
| `docs/nova-ditto/fullbody/ditto_fullbody_64s.mp4` | **the recording** — 1074×1920 full body, 1599 frames, 63.96 s, intro + game section |
| `docs/nova-ditto/fullbody/ditto_fullbody_dance_20s.mp4` | Ditto on the **dancing** full-body body, 498 frames |
| `docs/nova-ditto/fullbody/ditto_vs_musetalk_fullbody_30s.mp4` | the 30 s side-by-side, both at full-body framing, labels burned in |
| `docs/nova-ditto/fullbody/fullbody_face_sheet.jpg` | the 8 frames I judged by eye — 3 silent, 5 speaking |
| `docs/nova-ditto/fullbody/fullbody_frame_speaking.jpg` | one whole full-body frame at a speaking moment |
| `docs/nova-ditto/fullbody/probe.txt` | **the bridge probe** on the real `lk_bridge.py` |
| `docs/nova-ditto/fullbody/lk_bridge.real.py` | the real bridge, for the next session to adapt the patch against |
| `docs/nova-ditto/fullbody/gate_*.json` | every gate run, plain and `--track` |
| `docs/nova-ditto/fullbody/roi_probe.json` | the §1 key-insight measurement |
| `docs/nova-ditto/fullbody/numbers.json` | every number on this page, machine-readable |
| `docs/nova-ditto/fullbody/logs/` | server logs, drive logs, `/health`, recon, pod logs |

---

## 10. Cost, pods, and the volume

| item | cost |
|---|---|
| fal Kling v2.1 pro i2v, 2 × 10 s (published rate ~$0.098/s — **not an invoice**) | $1.96 |
| pod `rpc43y4l6kuem8` (4090 Secure, 3.1 min) — recon + probe; Ditto blocked on `Python.h` | $0.047 |
| pod `8u1hrfsy0oikuh` (4090 Secure, 3.5 min) — ran the stale `job.sh` off the shared volume | $0.052 |
| pod `ztxmaapx2qyrxl` (4090 Secure, 7.7 min) — **the real run**, both bodies | $0.114 |
| **total** | **$2.17 of $4** |

**Pods remaining: 0.** All three return HTTP 404. The only other pod on the account
(`lnch-cohost-cafe-0815-body`) belongs to another session, was never touched, and had ended on its
own by the final check.

**Watchdogs:** one per pod, 45 min, REST `DELETE /v1/pods/<id>`, proof written to disk and read back
with the process confirmed alive before any render started. All three **stood down** on finding
their pod already gone; none fired.

**The production volume was left as found.** Ditto installed to the container disk, not the volume.
Everything this session created on the volume lived in one uniquely-named directory
(`/workspace/novaditto_fb_out`) plus uploads in `/workspace/in`, and both were deleted at the end of
the job once the outputs were pulled — verified: the directory returns HTTP 404 and `in/` holds only
an auto-generated `__pycache__`. No pre-existing Nova file was read-modified, moved or deleted;
`lk_bridge.py` is byte-identical (`already patched: no`).
