# DITTO-LIVE — the Ditto recording exists. Her commercial intro, her voice, a kid answering.

**Session `novaditto-final`, 2026-11-02. One pod, 23.7 min, `m9ydr71tq7pvs1`, RTX 4090 Secure
EU-RO-1 on volume `1ditrne6cb`. Pods remaining: 0 of mine. The $3 cap was never approached.**

```
docs/nova-ditto/live/recordings/nova_commercial_ditto.mp4             2,665,814 B  88.5 s  540x960 h264 + AAC
docs/nova-ditto/live/recordings/nova_commercial_ditto_69s.mp4         2,326,801 B  69.5 s  the same take, 3.5-73.0 s
docs/nova-ditto/live/recordings/nova_commercial_ditto_audioproof.mp4  2,068,368 B  43.4 s  take 0, nobody answers her
```

| the mission | state |
|---|---|
| **face engine = DITTO, no MuseTalk fallback** | **DONE** — §2 |
| **her voice audible** | **DONE.** `max_volume -4.0 dB`. The two 2026-11-01 Ditto takes were `-84.3 dB` — §3 |
| **the COMMERCIAL intro, not the freeze one** | **DONE** — §4 |
| a kid answering her in the chat lane | **DONE** — §5 |
| the body is `from_maya/assets/nova_idle.mp4`, gated | **DONE** — §1 |
| duplicate frames, measured | **DONE, and it is bad: 70.8%** — §6. The recorder is not the cause this time; the delivered stream is. This is the one thing this session did not fix. |
| leave the production volume as found | **DONE.** `lk_bridge.py 1c4448b4…`, `rt_lk.py 9f64d1e6…`, `beta/freeze.html 428907f1…` — all three back to what they were |

Evidence: `docs/nova-ditto/ditto-live/logs/` (35 files), `docs/nova-ditto/ditto-live/frames/`.

---

## 1. The body: the Maya one, gated off-pod, unchanged

`from_maya/assets/nova_idle.mp4` — 1080x1920 @25, 69 frames, 2.76 s. No new body was generated
and no fal money was spent. `prebake_gate.py` was run on it **here, on CPU, before the pod
existed**, so the gate cost nothing:

```
verdict SOFTEN            (the bar is PASS or SOFTEN)
face_found_pct 100.0      face_px p50 316        (the 200-470 band)
mouth_p50 0.0085          mouth_p95 0.0199       (closed)
hand_pct 0.0              disp_p95 2.1 %         yaw_range 1.4 deg
non-PASS: rot_v_p95_deg 1.93 SOFTEN, smo_res_p95_deg 2.07 SOFTEN
```

The server took it as given: `/health` reports `src nova_idle.mp4, src_frames 69,
src_wh [1080,1920], out_wh [1080,1920], amp 0.6, prime 35, bank null, gate_frames 0`.
No motion bank, no full-body shim.

## 2. It is Ditto, three ways

**The logs.** `logs/bridge.take1.log` opens with `[NOVA_FACE] ditto` and the server banner
above; `logs/apply.txt` shows the bridge patched 5/5 anchors
(`1c4448b475ae0cdd719aef4edaa90337 -> …`); `logs/ditto_stats.take1.json` records **201 render
chunks, 194 of them speech, 5000 frames, 0 errors** during the take. MuseTalk's `app.py` was
running — it has to, it is what carries her voice to the bridge — but not one of its frames
was published: anchor A2 takes the publish loop's frames from `nova_ditto` instead.

**The flag reached only the bridge.** `stage 7: 'NOVA_FACE] ditto' lines — bridge=2, brain=0`.

**The picture.** `frames/ditto_vs_musetalk.jpg` — the 2026-11-01 MuseTalk take is Nova standing
in the purple dance studio; this take is the `nova_idle` kitchen body, cupcakes and the SCIENCE
KID volcano on the counter. Different source footage entirely. Nobody has to trust a log line.

## 3. The audio bug, and what it actually was

The brief's hypothesis — that the bridge never published audio under `NOVA_FACE=ditto` — is
not what the log says. `docs/nova-ditto/live/logs/novarec_bridge.log` from 2026-11-01:

```
bridge: published 2300 frames
bridge: audio published 100 frames      <- 100 x 20 ms = 2.0 s of sound
bridge: published 3300 frames
bridge: audio published 200 frames      <- the next 2.0 s took 1000 video frames = 40 s
```

The audio *was* published. It was published **about 18x slower than real time**, so a 72 s take
carried a few scattered seconds of sound and measured as silence. The cause is one line. A3
stamped `_nf_arrived` **after** `await aq.get()` returned — at DEQUEUE, not at arrival.
`aq.get()` returns instantly on a non-empty queue, so every frame was dequeued, stamped *now*,
and then held a full `av_delay_ms` again: each frame paying the whole offset instead of the
stream paying it once. Simulated both ways at real speed, 50 frames of 20 ms audio, 1800 ms
offset: **old** published 11 of 50 in 20 s and stretched 1.00 s of sound over 18.02 s; **new**
published 50 of 50, 1.00 s of sound in 0.99 s, offset by exactly 1.80 s.

The second half of the same silence: `nova_ditto.boot()` ran in **both** processes. `rt_lk.py`
fed one `DittoFace`; `lk_bridge.py` published frames from a **different** one that nobody ever
fed, so it posted nothing but silence to the server while two pumps fought over one stateful
body video.

The fix is a fifth anchor, **A5**, at the engine socket's `'A'` branch — the place the audio
actually arrives. It stamps the real arrival time and carries it with the samples, and it feeds
Ditto *there*, in the publishing process, from the same `pcm16` mono 16 kHz the audio track
publishes (`AUDIO_SR` is already 16000 — exactly what Ditto wants, no resampling). It only
reads; the publish path is untouched, which is what `from_maya/code/ditto_renderer.py` says the
contract is. A4 now caps its sleep at `av_delay_ms` so no future stamping mistake can compound.
The brain runs **without** `NOVA_FACE` so it never boots a second face.

**Proved before recording, not after.** Take 0 is a 45 s run with nobody answering, whose only
job was to make the counters move:

```
AUDIO_PROOF (take 0)   audio_IN=950    audio_published=900
AUDIO_PROOF (take 1)   audio_IN=9400   audio_published=9400     aq depth 3-119, dropped 0
take 1 max_volume      -4.0 dB         mean -32.8 dB
```

9400 in, 9400 out. The queue depth oscillating between 3 and 119 entries *is* the 1800 ms
offset, held once by the stream. The delay applied is `(PRIME 35 + SLACK 10) x 40 ms = 1800 ms`,
not the reference renderer's `PRIME x 40 = 1400 ms`: our publisher drains Ditto's 25-frame
bursts one per 40 ms and `nova_ditto` banks 10 frames of slack before it starts its clock, so
the picture is 10 frames further behind than the reference shim's. The number is logged by the
code that applies it.

## 4. The commercial intro, and exactly how it was obtained

The brain runs its commercial greeting only when **no** `intro=` reaches `/rt`
(`/workspace/rt_lk.py` L745, read off the volume and logged in `logs/rtlk_greet.txt` *before*
anything was recorded). `beta/freeze.html` hardcodes `intro=freeze` in two places and registers
the `[GAME-MODE]` persona plus `nova-pick`, which together **replace** the intro script.

So the page was served with one query flag, `?commercial=1`, which suppresses exactly those
three things and nothing else. Without the flag the page is byte-identical to before. **The
brain's words were not touched** — the whole point was to stop telling it we are a game.
`stage 8: PAGE_ASSERT PASS 148832 bytes JUDGE-TRUTH x1 COMMERCIAL x6`.

Her first line, verbatim off the brain websocket (`logs/take1.transcript.jsonl`):

> **Hi! I'm Nova, your magical AI dance teacher! What's your name?**

not `Hi! I'm Nova - FREEZE time!`. (The brief quoted "magical dance teacher"; the line the
brain actually ships says "magical **AI** dance teacher". Reported as spoken.)

The page was installed over the volume's copy atomically, with the original kept at
`/root/freeze.html.orig`, and put back in stage 10 — `428907f1b56a5f63ce210196840dc8f9`, the
md5 it had before.

## 5. The exchange

Every kid line was typed after reading the line she had just said, off the page's own brain
websocket, into `#nova-chat-input` — the founder's 2026-08-09 typed lane, which sends the brain
the same `{"type":"text"}` a child's typed reply sends.

```
   4.0s  NOVA  Hi! I'm Nova, your magical AI dance teacher! What's your name?
  17.3s  NOVA  I'm right here, no rush at all.
  26.8s  NOAM  im Noam!
  28.7s  NOVA  Noam—so awesome to meet you! What's your favorite animal?
  42.5s  NOVA  Still right here.
  47.7s  NOAM  a tiger! i like how it jumps
  49.2s  NOVA  Tigers are epic jumpers—love that!
  67.7s  NOAM  can you dance like a tiger?
  70.5s  NOVA  I can't dance myself, but I can help you dance with tiger energy—want to try?
```

She asks for the name, echoes the **exact** name, asks a real question back, and answers a
child's question in character without claiming a body she does not have. The conversation needed
69 s, not the 30-60 s the brief asked for; the 69 s cut is the whole of it and the 88.5 s file
is the unedited take.

## 6. The duplicate frames — 70.8%, and the recorder is not the cause this time

Measured on the deliverable, and the method is calibrated rather than guessed. Consecutive
frames are decoded to 135x240 gray and compared by mean absolute difference; a transition below
**0.1** counts as a duplicate. On a 240-frame clip built with exactly 79 known duplicate
transitions (33.05%) and re-encoded with these same x264 settings, the threshold recovered
**33.05%** (77 true, 2 false, 2 missed). `framemd5` was tried and rejected — it reads 0% on any
lossy re-encode, because x264 gives a repeated input frame a slightly different residual — and
so was ffmpeg's `mpdecimate`, which calls 68% of a real talking-head take duplicate.

```
                                   frames   duration   fps    duplicates   median MAD
take 1 (the deliverable, Ditto)       350      89.3s   3.92      70.8%        0.0283
take 0 (Ditto, nobody answers)        190      43.8s   4.34      22.2%        0.5178
2026-11-01 take (MuseTalk, timer)    1830      73.2s  25.01      60.8%        0.0537
```

and inside take 1, by window:

```
   0- 20s  119 fr (5.95 fps)  dup 45.4%   medMAD 0.1246
  20- 40s   72 fr (3.60 fps)  dup 79.2%   medMAD 0.0203
  40- 60s   81 fr (4.05 fps)  dup 85.2%   medMAD 0.0073
  60- 80s   53 fr (2.65 fps)  dup 81.1%   medMAD 0.0000      <- bit-identical pictures
  80-100s   24 fr (1.20 fps)  dup 100.0%  medMAD 0.0281
```

**The recorder was fixed and the fix works.** It no longer repaints on a 40 ms timer: it paints
once per new decoded frame, pushed by hand with `captureStream(0)` + `requestFrame()`, gated on
`getVideoPlaybackQuality().totalVideoFrames`. The take's own counters show the gate doing its
job — **323 frames painted, 747 poll ticks skipped** because no new frame had arrived. Under the
old recorder every one of those 747 would have been written to the file as a copy. That is why
this take is 3.92 fps instead of a padded 25: it reports what arrived.

**What arrived was bad, and worse than last session.** The frames were there to be had —
`ditto_stats.take1.json` says the bridge produced 5000 frames with 0 errors — but the browser
received about 4 per second, and in the 60-80 s window the pictures it received were bit-identical
after downscale. Two things are visible in the logs and neither was fixed:

* **the subscriber fell to the lowest simulcast layer.** The harness logs the chosen track's
  size every 15 s: `src=360x644` for most of the take and `src=180x322` by 78.7 s, against the
  720x1288 the bridge publishes. The duplicate percentage tracks that fall exactly.
* **the publish clock over-ran.** `ditto_stats.take1.json`: 5000 frames popped in a ~112 s
  window is **44 fps**, not 25, so `nova_ditto.next_frame_bgr`'s pacing is not holding under
  `run_in_executor`. The pump then renders faster than she speaks, and `_take_chunk` pads each
  partial chunk to a full second — which is why 194 of 201 chunks are marked "speech" in a take
  where she spoke for about 25 s. `held 166`, `longest_hold_s 1.52`, one `picture held 2.0s`
  alarm.

Take 0 is the control: same recorder, same engine, 22.2% duplicates and a median MAD of 0.52 —
a lively picture — because the stream had not yet degraded. So the number to carry forward is
not "the recorder duplicates frames"; it is **"the live video path delivers ~4 fps to the
subscriber and collapses to the bottom simulcast layer"**, and that is the next lane's problem.

## 7. Two traps this session paid for

**`/workspace/boot.sh` is not `tools/pod/boot.sh`.** The job built its boot wrapper with a sed
written against the repo's single-line deploy. The volume's copy is an older variant with
**three** deploy invocations — an inline `deploy_from_git()` plus a bare call to it, and an
if/elif running two more scripts — so the sed matched none of them, and the job correctly
**refused to boot** rather than run the step that truncated `/workspace/pages` on 2026-11-01.
That cost ~6 minutes and no pod. `tools/pod/boot_wrap.py` now rewrites by rule and asserts the
result: every deploy invocation neutralised (the function *definition* is left alone so the file
stays valid bash), every `lk_bridge.py` launch tagged `NOVA_FACE=ditto`, the `rt_lk.py` launch
*not* tagged, `bash -n` before anything is written.

**`resampy/core` is still missing from the volume** — the legacy-sourceless `.pyc` casualty from
2026-11-01, unfixed. `app.py` dies on it in 20 seconds. It must be healed into a directory
**earlier on `PYTHONPATH` than the volume tree**, because the broken copy shadows a good one:
`pip install --target /root/torchfix resampy`. Four lines through the CMD channel, no new pod.

> **A secret is sitting in the clear.** `/workspace/boot.sh` carries `HUME_API_KEY`,
> `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` and `OPENAI_API_KEY` as plaintext `export` lines in a
> world-readable file on the shared volume. Nothing in this session printed, logged or committed
> that file — `boot_wrap.py` redacts its diff and the raw copy was never committed — but the keys
> should be rotated and moved into `/workspace/.nova.env`, which `boot.sh` already sources. The
> deploy-token item from the previous two sessions is **still open** as well.

## 8. What it cost

| | |
|---|---|
| pod `m9ydr71tq7pvs1` | RTX 4090 Secure EU-RO-1, created 08:28:43Z, terminated 08:52:2xZ |
| runtime | **23.7 min** at **$0.89/h** = **$0.35** |
| network volume | $0.032/h, already running before and after |
| pods of mine remaining | **0** (verified by re-listing) |
| watchdog | armed 45 min, proof file read back `ARMED`, then `STOOD_DOWN (pod already gone)` at 08:52:38Z |

The account balance moved $9.0592 → $8.2669 over the window, but **that delta is not all mine**:
another session's pod, `jsvzmyf0baihmk` / `clat-body`, was created at 08:42:43Z at $0.89/h and is
still running. It was not touched.

## 9. What the next session should do, in order

1. **The 4 fps.** §6. Start with the two measurements already in hand: the subscriber's simulcast
   layer (`src=360x644`, then `180x322`, against 720x1288 published) and the 44 fps pop rate in
   `ditto_stats.take1.json`. Fixing `next_frame_bgr`'s pacing is a local change in
   `tools/pod/nova_ditto.py`; the simulcast fall may just be the headless subscriber's bandwidth
   estimate, in which case pin the layer or drop the publish resolution.
2. **`_take_chunk` pads partial chunks to a full second and marks them speech.** With the pump
   over-running, most of what Ditto is driven by is zero padding. That is probably why the lip
   movement in `frames/take1_strip_29to34s.jpg` is real but small.
3. **Heal `resampy` on the volume for good**, or keep paying 4 lines per pod.
4. **Rotate the keys in `/workspace/boot.sh`** and move them into `/workspace/.nova.env`.
