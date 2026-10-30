# DITTO-CLEAN-AB — does Ditto beat MuseTalk on a *clean* body?

**Session `novaditto-live`, 2026-10-30. Spend $0.00. Pods created 0, pods remaining 0.**

**The live run did not happen.** This container has no `RUNPOD_API_KEY`, no `FAL_KEY`, no
`MAYA_ASSETS_TOKEN` and no SSH key. No pod could be created and no fal Kling body could be
generated, so **no Ditto frames exist to measure**. Nothing below is simulated, estimated or
carried over as if it were new. One half of the A/B was re-measured here for real; the other
half is quoted from the previous pod run and labelled as such.

---

## The answer, stated honestly

| | corr @ lag 0 | best corr @ lag | measured where |
|---|---|---|---|
| **MuseTalk as aired** | **0.187** | 0.239 @ **−680 ms** | **this session, CPU, on the real file** |
| **Ditto on the "clean" body** | **0.271** | 0.281 @ **+40 ms** | prior pod run (`maya-lt bench/results/nova-ab/numbers.json`) — *not* this session |

On the only clean-body data anyone has, **Ditto wins: 0.271 vs 0.187 at lag 0, +0.084 (about
+45 % relative)**. The bigger win is the clock, not the correlation: Ditto's mouth sits **+40 ms**
behind the sound, MuseTalk's runs **680 ms ahead** of it. A mouth 0.7 s early is the thing a
viewer actually notices.

**But the question the mission asked is still not settled**, and it is important to say why:

> That "clean body" is the `idle_sway` ping-pong loop, and it **gates REJECT** on `mouth_p95`
> 0.059 — her resting mouth sits open. It is cleaner than the aired frames, not clean.
> **No Nova body has ever passed the gate.** The 0.271 is depressed by the body, not by the
> engine (silent-frame mouth opening 0.036, the highest of the three clips in that run).
> A genuinely closed-mouth body has never been put through Ditto. That measurement still
> does not exist.

So: **Ditto beats MuseTalk on every body measured so far, including the cleanest one.** Whether a
*properly gated* closed-mouth body pushes it past the 0.35 proof bar is the open question, and it
needs a fal generation and a GPU pod.

I did not look at any new Ditto frames this session, because none were produced. I will not say
whether "the Ditto mouth looks alive" on a clean body on the strength of someone else's screenshot.

---

## What was actually measured here

`lipcorr.py` (maya-lt `bench/results/nova-ab/tools/lipcorr.py`, mediapipe 0.10.32 face landmarker,
inner-lip gap 13→14 over face height vs audio RMS per 40 ms frame, Pearson at lag 0 and best over
±25 frames) on `beta/sources/talk-test/talk-90s.mp4`:

```
crop=626:1112:246:276,scale=1080:1920:flags=lanczos  -r 25   ->  1575 frames / 63.0 s
-vn -ac 1 -ar 16000 -f f32le                                 ->  1024341 samples / 64.021 s
```

| | this session | prior run | same? |
|---|---|---|---|
| frames | 1575 | 1575 | yes |
| face found | 99.2 % | 99.2 % | yes |
| voiced frames (RMS > 0.02) | 17.9 % | 18 % | yes |
| corr lag 0 | **0.187** | 0.189 | within re-encode noise |
| corr best | **0.239** @ −680 ms | 0.250 @ −680 ms | same lag |
| mouth speaking / silent | 0.0368 / 0.0230 | 0.0366 / 0.0226 | yes |

The delta is my `crf 18` re-encode against their `crf 16`. **The MuseTalk baseline is solid and
independently reproduced: ~0.19, mouth 680 ms early.**

---

## Step 0 — the probe

```
python3 tools/pod/ditto_bridge_patch.py --probe
== probe /workspace/lk_bridge.py
   MISSING -- /workspace/lk_bridge.py does not exist.
```

Expected without a pod: the file lives on the RunPod volume. **Assumptions A1 (the two patch
anchors) and A2 (whether `lk_bridge.py` publishes the audio track) both remain unkilled.** The
patch must not be applied until this probe runs on a real pod and reports both anchors present
exactly once and `AudioSource`/`AudioFrame` at 0.

---

## [CLI-FILL] The Kling seed still — the step-3 input, found and measured

Step 3 needs "the same clean knees-up Nova still, face ~280 px, mouth CLOSED, hands relaxed" for
`image_url` **and** `tail_image_url`. No such still was named anywhere in the repo, so I found one
by scanning every frame of the known-good body for the frame that is simultaneously mouth-closed
and eyes-open (a pure mouth-minimum frame lands mid-blink — I checked, frame 54 is half-lidded and
would have seeded a sleepy body).

**`docs/nova-ditto/kling_seed_closed_mouth.png`** — frame 263 of `docs/ditto-try/nova_body_ditto.mp4`:

| | value |
|---|---|
| mouth (inner gap / face height) | **0.0106** — closed |
| eye aperture | 0.121 (clip p75 = 0.113) — open |
| face | **289 px** (Ditto band 200–470) |
| frame | 1080×1920, already the proven knees-up crop |

Face crop for a look: `docs/nova-ditto/kling_seed_face.jpg`. Hands hang relaxed at her sides,
static room, closed-mouth smile. **This is the file to hand fal.** Prompt, unchanged from the
mission: *gentle breathing sway, tiny head motion, blink, static camera, same room, mouth closed*,
10 s, 1080×1920, `image_url` = `tail_image_url` = this still.

Worth knowing before the gate runs: the clip this frame came from has `mouth_p95` 0.0386 over its
314 frames, and gates **SOFTEN**, not PASS. The target is `mouth_p95 <= 0.025`. Seeding Kling from
a frame at 0.0106 is the best start available, but it does not guarantee the generated 10 s stays
closed-mouthed — the gate still decides.

---

## What is blocked, exactly

| step | needs | status |
|---|---|---|
| 1. probe `lk_bridge.py` | a pod | ran, reports MISSING — anchors unverified |
| 2. pod via `pod_up.py` | `RUNPOD_API_KEY` (+ `MAYA_ASSETS_TOKEN`) | **blocked** — the launcher itself raises `ProviderError: RUNPOD_API_KEY missing` |
| 3. clean body via fal Kling | `FAL_KEY` | **blocked** — seed still found and staged; the gate tool is ready and proven both ways |
| 4. `ditto_up.sh` + `/health` | the pod | **blocked** |
| 5. Ditto render + its correlation | the pod | **blocked** — this is the missing number |
| 5. side-by-side 45 s + mouth strip | Ditto frames | **blocked** — nothing to put on the right side |
| 6. MuseTalk correlation | nothing | **done, 0.187** |
| 7. terminate + prove 0 pods | — | 0 pods created, 0 remain |

The full-length renders from the previous run (`nova_ditto_clean.mp4`, `nova_ditto_aired.mp4`) did
**not** survive in any scratchpad — I looked. They would have to be re-rendered on a pod
(~6 min, ~$0.25 by that run's own costing) even just to rebuild the comparison video.

## Cost

$0.00. No pod, no fal, no GPU. CPU only, in this container.
