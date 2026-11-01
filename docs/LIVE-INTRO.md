# LIVE-INTRO — the live commercial intro was NOT recorded, and the reason is one line

**Session `novalive-intro`, 2026-11-01. Spend $0.78 of $2. Pods created 5, pods remaining 0.**

> **Nova's production volume `1ditrne6cb` is out of quota.** Every write to `/workspace` fails with
> `OSError: [Errno 122] Disk quota exceeded`. Nothing can be deployed, patched or repaired on that
> volume until space is freed. That single fact blocked the bridge patch, blocked Ditto in the live
> path, and — worse — caused `boot.sh`'s own deploy step to **truncate the live commercial page to
> 0 bytes**, so `/beta/freeze?intro=freeze` currently serves an empty body on this volume.

**This session did not fill the volume.** The very first pod, at 11:14 UTC, could not write
`/workspace/podsrv.py` — before a single byte of this session's work had run.

---

## 1. What the deliverable was, and exactly how far it got

| step | state |
|---|---|
| bridge patch corrected for the killed A2 assumption | **done, verified off-pod** (§2) |
| full-body motion bank with gestures | **done, and Ditto booted on it** (§3) |
| headless harness that records the LiveKit tracks and plays the kid | **done, proven end to end** (§4) |
| Ditto as the live face engine | **blocked** — `--apply` cannot write to the volume (§5) |
| **the recording of the real intro as a conversation** | **NOT MADE** — the page serves 0 bytes (§6) |

**No recording exists. She never spoke, because the page that starts her never loaded.**
There is no mp4 to point at and nothing was captured that could be dressed up as one.

---

## 2. The bridge patch is now correct — proven against the real file, for free

The 2026-10-31 probe killed assumption A2: `/workspace/lk_bridge.py` publishes **both** tracks
(`AudioSource` L120, `publish_track` L122 microphone + L140 camera). The shipped patch put the
A/V offset in `rt_lk.py`, which was the wrong place.

`tools/pod/ditto_bridge_patch.py` now carries two more anchors, both inside `drain_audio`:

* **A3** stamps each engine audio frame with its arrival time;
* **A4** holds it until `arrival + av_delay_ms` before `asrc.capture_frame(fr)`.

Measured from arrival, so it is a constant **offset**, not a per-frame cost — frame *i+1*'s due
time is never earlier than frame *i*'s, order and throughput are unchanged, and `aq` (maxsize 600)
absorbs ~90 entries of backlog at 20 ms frames.

Verified against `docs/nova-ditto/fullbody/lk_bridge.real.py`, md5
`1c4448b475ae0cdd719aef4edaa90337`, the byte-identical copy of the production file:

```
   anchors this patch needs (all four must be exactly 1):
     OK   A1  return rgba.tobytes()            count=1
     OK   A2  w, h, rgba = await vq.get()      count=1
     OK   A3  pcm = await aq.get() + n =       count=1
     OK   A4  await asrc.capture_frame(fr)     count=1
```

* apply inserts exactly four blocks and **nothing else** (full diff checked line by line);
* neither `publish_track` call nor the `_downscale` line is touched;
* a second apply changes nothing (`already patched: yes`);
* `--revert` is **byte-identical** to the original.

**And the same probe ran on the REAL file on the pod and passed, `probe rc=0`.** The patch is right.
It is `--apply` that died, and only because of the quota (§5).

`pod/rt_lk.py`'s own delay line is now **off by default** (`NOVA_DITTO_DELAY_SITE=bridge`). It still
feeds Ditto her voice the moment it exists. Holding `/humanaudio` back there delayed the **engine**
as well, which is added latency on the start of her turn, not a picture-against-sound offset.
`NOVA_FACE=musetalk` is untouched on both sides.

---

## 3. The first full-body Nova motion bank — built, and Ditto ran on it

`tools/pod/build_nova_fb_bank.py` → `docs/nova-ditto/live/nova_fb_bank.{mp4,json}`, in the shape
`maya-ops/lt/motion_bank.py` loads. 344 frames, 1076×1924, 25 fps.

| segment | kind | source | length | **loop_mae** (first frame vs last) |
|---|---|---|---|---|
| `nova_fb_idle` | idle | the calm full-body body, `mouth_p95` 0.0209 | 9.64 s | **0.738** |
| `nova_fb_groove` | gesture | best-looping window of `D-take2` | 3.68 s | **3.79** |

* The law is "every segment starts and ends on the same rest pose". The idle satisfies it by
  construction (generated with `image_url == tail_image_url`). For the gesture it was **measured**:
  every candidate window was scored by the pixel distance between its first and last frame and the
  best was taken. The number is in the bank json as `loop_mae`, not asserted.
* **Junction idle→gesture: 10.71.** That is a real visible change of pose, softened by the
  scheduler's `DITTO_GESTURE_XFADE` (8 frames), not hidden. Stated because it is the honest cost of
  building a gesture out of a dance take rather than generating one.
* The reference bank's trim (gesture +1/−5) was **tried and rejected on measurement**: it is meant
  for Kling clips with eased still ends, and on `D-take2` it made the loop worse (9.017 vs 3.301).
* **`wave` is deliberately NOT aliased to it.** There is no full-body wave clip in either repo, so
  `gesture('wave')` gets an honest refusal instead of a groove pretending to be a wave.
  Aliases that do resolve: `groove`, `greet`, `hello`, `dance`.

Loaded and scheduled correctly by the unmodified `motion_bank.py` off-pod, and **on the pod Ditto
booted on it**:

```
ready after 191 s: {"src": "nova_fb_bank.mp4", "src_frames": 344, "src_wh": [1076, 1924],
  "amp": 0.6, "out_wh": [1074, 1920], "setup_s": 7.2, "prime_s": 121.3, "eye_holds": 0,
  "bank": "/root/in/nova_fb_bank.json",
  "motion": {"cur": "nova_fb_idle", "kind": "idle", "mismatch": 0}}
[ditto_fullbody] installed: explicit_box=[263.0, 215.0, 763.0, 715.0] up=3.0 rungs=5
```

So **Ditto with a motion bank, at full-body framing, is live-ready.** It was never reached by audio,
because the bridge could not be patched and the page never opened — so **no gesture ever fired**,
and whether her lips move in the LIVE path is still unmeasured.

`DITTO_OUT_W=1074 DITTO_OUT_H=1920` was set, which is one of the two documented fixes for the
`out_wh` shear bug of DITTO-FULLBODY §4 — no code change needed.

---

## 4. The harness exists and works — it just had nothing to open

`tools/pod/live_intro_harness.py`. There is no X display on the pod, so the picture is composited
**in the page**: her remote video track is drawn to a canvas at 25 fps with the live transcript
burned in as captions, `canvas.captureStream(25)` is joined with her remote **audio** track, and one
`MediaRecorder` writes the pair. Chunks are POSTed to a 127.0.0.1 sink with a sequence number and
concatenated in order, so the result is one continuous take.

Kid replies are typed into the page's own chat lane (`#nova-chat-input`, the founder's 2026-08-09
typed path, which sends the brain the same `{"type":"text"}` a child's typed reply sends). The only
thing the harness accepts from off-pod is a line of text; it is not a remote-exec endpoint.

**Dry-run proven end to end in this container** against a fake page and a fake brain: her lines
captured, three kid lines typed and echoed back, 554 canvas frames, 23 chunks, and a valid
**h264 540×960 + aac mp4** whose caption band shows the real back-and-forth.

On the pod it ran twice and both times reported, correctly, that there was nothing to record:

```
goto http://127.0.0.1:8765/beta/freeze?intro=freeze
  body text 0 chars, html 39 bytes: ''
  no #start-btn here (TimeoutError)
goto http://127.0.0.1:8765/freeze?intro=freeze
  body text 0 chars, html 39 bytes: ''
NO PAGE SERVED the app on any candidate URL -- nothing to record
```

---

## 5. Why Ditto could not take the live path

```
File "/root/in/ditto_bridge_patch.py", line 234, in install_sidecar
    shutil.copyfile(sidecar_src, dst)
OSError: [Errno 122] Disk quota exceeded
```

`--apply` must write three things to the volume: `nova_ditto.py` next to the bridge, a
`.bak-ditto-*` backup, and the patched `lk_bridge.py`. None of them fit. The patch refused cleanly
and **the production `lk_bridge.py` was never modified** — `already patched: no` is still true, and
the run fell back to MuseTalk exactly as designed.

Running a patched copy from `/root` instead would mean killing the live bridge and restarting it by
hand with credentials extracted from `boot.sh`, on a pod with no shell access. That was not attempted
on a production stack with the page already broken.

---

## 6. The live commercial page is currently BROKEN ON THE VOLUME — and this is the headline

`boot.sh` step 0 runs `deploy_from_git.sh`, which copies the repo's pages onto the volume. On a
volume at quota, every `cp` **opens its destination, truncates it, and then fails to write**:

```
cp: failed to close '/workspace/pages/up-groove.html': Disk quota exceeded
cp: failed to close '/workspace/pages/shared/light-engine.js': Disk quota exceeded
cp: error writing '/workspace/pages/models/pose_landmarker_lite.task': Disk quota exceeded
[DEPLOY] pages synced from nova-ditto@05f88b0: none
```

The inventory taken the next boot, read-only — **every one of these is 0 bytes, stamped `Nov 1 11:33`**,
the minute that deploy ran:

```
/workspace/pages/beta/freeze.html            0 bytes   <- THE COMMERCIAL PAGE
/workspace/pages/upperbody.html              0 bytes
/workspace/pages/models/pose_landmarker_lite.task   0 bytes
/workspace/pages/shared/  cue-window.js freeze-fx.js game-kit.js light-engine.js
                          mover-engine.js mover-rules.js nova-bridge.js nova-lang.js
                          nova-lights.js pose-adapter.js pose-engine.js pulse.js   all 0 bytes
plus beta/ copy.html demo.html freeze-nova.html freeze3.html groove.html hello.html
         index.html lights-demo*.html novasays.html novasays.js play.css           all 0 bytes
```

and the brain, which is otherwise perfectly healthy, dutifully serves the emptiness:

```
/beta/freeze?intro=freeze    http=200  0 bytes
/freeze?intro=freeze         http=200  0 bytes
/                            http=200  19238 bytes
/health                      http=200  {"ok": true, "voice": "marin", "room": "nova-live"}
```

**Repair was attempted and refused.** The exact files were uploaded from `nova-ditto` and written
back atomically (temp file + `os.replace`, and only where the uploaded copy was larger, so a healthy
file could never be clobbered). All 14 failed:

```
page repair: restored 0, left alone 14
  . beta/freeze.html FAILED OSError: [Errno 122] Disk quota exceeded
  . shared/light-engine.js FAILED OSError: [Errno 122] Disk quota exceeded
  ...
```

> A 1-byte probe file writes fine; a 147 KB page does not. The volume has **bytes** of headroom, not
> kilobytes. `df` is useless here — it reports the 2.2 PB cluster at 79 %, not the volume's own quota.

**Nothing was deleted to make room.** Bakes are treasure (repo law 8) and this session has no basis
for deciding what on that volume is disposable. **That is Refael's call, and it is the one thing
standing between this branch and the recording.**

---

## 6b. One security note, in passing

`boot.sh`'s deploy prints the full remote URL on failure, and that URL carries the volume's GitHub
deploy token in the clear (`/workspace/.deploy-token`). It therefore ends up in `/root/boot.log`
verbatim. GitHub's own push protection caught it when this report's logs were first committed; the
value is **redacted to `<REDACTED-TOKEN>` in `logs/deploy_truncation.log`** and was never pushed.
Nothing is known to have leaked, but a token that writes itself into a log on every failed deploy
is worth rotating, and `deploy_from_git.sh` is worth teaching to print the URL without its userinfo.

---

## 7. The two traps this session hit, for whoever goes next

1. **podsrv cannot start from the volume.** Two pods died on "runtime but no BOOTED at 6 min" with
   port 8040 mapped and the proxy answering 502 forever. `pod_up.py`'s START writes `podsrv.py` to
   `/workspace` and runs it from there; on a volume at quota that write produces nothing and the
   server never exists. **Fix, applied in `docs/nova-ditto/live/podup_nl.py` without editing
   `pod_up.py`:** podsrv is written to `/root`, run with `python3 -I` (isolated — no CWD on
   `sys.path`, which also kills the risk of the volume's 34 loose top-level `.py` files shadowing a
   stdlib module), serves `/root`, takes uploads into `/root/in`, and `BOOTED`/`hb` are mirrored so
   the launcher's own boot guard still works. It then came up **in under 15 seconds, every time.**
   A `/diag` endpoint was added that reports df, the volume's entry count and any stdlib shadows.
2. **Do not stage a file onto the volume with `cp` when it might be at quota.** This session's own
   stage 5 copied `rt_lk.py` onto `/workspace/rt_lk.py`; the copy truncated it to 0 bytes and then
   failed — exactly the same failure mode as the deploy. `deploy_from_git.sh` repaired it in the
   same boot and the final md5 is `b57bd139…`, identical to the pre-session recon, so **no damage
   survived**. The stage was removed for the second attempt. Verified before and after:
   `b57bd139b24cde2890ae2bad54bdf247  /workspace/rt_lk.py` both times.

The unique-job-name fix for the stale `job.sh` trap (DITTO-FULLBODY §6 trap 1) worked: the pod waits
for `/root/in/novalive_job.sh`, a name no previous session can have left behind.

---

## 8. What the next session should do, in order

1. **Free quota on `1ditrne6cb`.** Nothing else on this list is possible first. Decide with Refael
   what goes; do not guess.
2. **Restore the truncated pages** — `beta/freeze.html`, the twelve `shared/*.js`,
   `models/pose_landmarker_lite.task`, `upperbody.html` and the rest of the 0-byte list above. They
   are all in git on `beta`/`nova-ditto`; a normal `boot.sh` will redeploy them once there is room.
   **Until then the live commercial page is down.**
3. Then the recording is a short job: `--apply` (the patch is correct and the probe passes),
   `NOVA_FACE=ditto`, Ditto on `nova_fb_bank.json`, and `live_intro_harness.py`. The stack boots in
   **105–115 s** on this volume and Ditto is ready in **191 s**, so the whole run fits in ~12 minutes
   of pod time.

---

## 9. Cost, pods, and what was left behind

| pod | GPU | min | cost | what it bought |
|---|---|---|---|---|
| `bdxdhhde06tv3a` | 4090 Secure | 6.1 | $0.090 | boot guard: runtime but no BOOTED (podsrv dead) |
| `yu8dzkrmd42att` | 4090 Secure | 6.1 | $0.090 | the same, confirming it was systematic |
| `e9g73hkgejjvm8` | 4090 Secure | 12.7 | $0.188 | proved port 8040 mapped + 502 = podsrv never started |
| `pm5hsvixyvilqh` | 4090 Secure | 22.8 | $0.338 | Ditto ready on the bank; probe passed; apply hit the quota; page empty |
| `wpl5l5zii24uut` | 4090 Secure | 5.2 | $0.077 | the read-only inventory and the refused repair |
| **total** | | **52.9** | **$0.78** | of a $2 cap. **fal: $0.00 — no generation was run.** |

**Pods remaining: 0.** All five return HTTP 404 by id. The only pod left on the account,
`clat--body`, belongs to another session and was never touched.

**Watchdogs:** one per pod, 45 min (30 on the last), REST `DELETE /v1/pods/<id>`, each verified from
its own proof file with the process confirmed alive before any work started. All four **stood down**
on finding their pod already gone. **None fired.**

**The volume was left as found**, with one unavoidable exception that was repaired by the stack
itself: `/workspace/rt_lk.py` is byte-identical to the pre-session recon (`b57bd139…`);
`/workspace/lk_bridge.py` was never modified (`already patched: no`); IN and OUT lived on the
container disk for the second attempt, so that job wrote nothing to the volume at all. **The 0-byte
pages were truncated by `boot.sh`'s own deploy step, not by this session's work** — but they are
broken now and §8 step 2 is how they come back.
