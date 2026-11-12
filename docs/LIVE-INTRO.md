# LIVE-INTRO — there is a recording. Nova's commercial intro, her voice, her body, a kid answering her.

**Session `novarec`, 2026-11-02. Two pods, ~37 min of pod time. Account balance
$9.8113 → $9.2318, a measured delta of **$0.58** including storage on the network volumes.
Pods remaining: 0. The $3 cap was never approached.**

```
docs/nova-ditto/live/recordings/nova_live_intro.mp4       6,760,354 B   73.2 s   h264 540x960 + AAC
docs/nova-ditto/live/recordings/nova_live_intro_38s.mp4   3,822,734 B   38.1 s   the same take, cut to the brief
```

| the mission | state |
|---|---|
| **one video file, 30-60 s, she talks and a kid answers in the chat lane** | **DONE.** 73 s unedited, plus a 38 s cut of the same take |
| face engine = Ditto | **NO.** Ditto published video but never carried audio. Recorded on **MuseTalk**, as the mission allows |
| prove the live page over HTTP (`curl` + `JUDGE-TRUTH`) | **DONE.** `http=200`, 147542 bytes, `JUDGE-TRUTH=1` |
| her lips move in the live path | **YES, measured** — §4 |
| leave the production volume as found | **DONE.** `lk_bridge.py` back to `1c4448b4…`, no `.bak` left |

---

## 1. The exchange, played live off the brain websocket

Nothing here was sent blind. Each kid line was written after reading the line she had just
said, pulled off the page's own brain websocket
(`docs/nova-ditto/live/logs/novarec_take3_musetalk_transcript.jsonl` is the same loop on the
earlier take; the final take's console and status logs are beside it).

```
  3.1s  NOVA  Hi! I'm Nova - FREEZE time! What's your name?
 12.1s  NOAM  im Noam!
 14.4s  NOVA  Noam! Love it! When the music plays, dance like crazy — when it stops,
              freeze like an animal! Ready to go?
 31.7s  NOAM  can i be the frog?
 32.7s  NOVA  Frog mode: unlocked! Ready to hop in?
 51.4s  NOAM  yes! lets go!
 56.3s  NOVA  Froggy freeze coming soon!
 63.0s  NOVA  Oops, I lost you—step back
```

She asks for the name, **echoes the exact name she was given**, explains the game, answers a
real child's question in character, and takes "yes" as the cue to start. That is the intro
the persona in `beta/freeze.html` specifies, happening live.

The kid's lines go in through `#nova-chat-input`, the founder's 2026-08-09 typed lane, which
sends the brain the same `{"type":"text"}` a child's typed reply sends.

**After 36.4 s she is deliberately silent.** The audio is below -60 dB from 35.1 s to the end
because the game has started and the page's speak-gate mutes her — repo law 4, "game voice in
the air". The 38 s cut is therefore the whole voiced conversation, not a trim that hides
anything.

## 2. Three takes were worthless and I only found out by looking at a frame

This is the part worth reading, because the logs said everything was fine.

`live_intro_harness.py` picked its tracks with `__ms.find(x => x.getVideoTracks().length > 0)`
— **the first attached stream**. On this page that is the page's own camera preview, and the
camera on a headless pod is `--use-fake-device-for-media-stream`: Chromium's **green test
card** with a rotating wedge and a timecode. Takes 1-3 are 67-82 s of that test card. The
harness reported `RECORDING started`, `audio_track=True`, hundreds of frames and a valid mp4
every time.

The contradiction was in the logs from the first minute and nobody had read it:

```
bridge.log :  bridge: video track published 720x1288
harness    :  rec frames=495 ... src=960x720
```

720x1288 is Nova. 960x720 is the fake webcam. The page attaches **two** video streams:

```
VIDEO#cam               label fake_device_0   960x720    the fake camera
VIDEO#nova-live-video   label remote video    720x1288   Nova
```

`getSettings()` returns a `deviceId` for **both** in Chromium, so local-vs-remote does not
separate them — my first fix used that and blocked recording entirely. The pick is now scored
on the element id, the track label and portrait-vs-landscape, and **the chosen track is
logged on every run** (`chosen VIDEO#nova-live-video 720x1288, score 14` against the camera at
`-24`), so this cannot regress silently again.

The same class of bug was fixed for audio: every attached audio track is now mixed through
WebAudio rather than taking the first one.

> **The lesson, stated plainly: a recording is not evidence until somebody has looked at a
> frame of it.** `mp4_bytes > 0` proves a file, not a picture.

## 3. Ditto ran, and Ditto does not carry audio

Ditto is real and it works as far as it goes. It came ready in **70 s** on the full-body bank
(`src_frames 344`, `out_wh [1074, 1920]`), the bridge patch applied cleanly
(`1c4448b4… → e9be0f4f…`, probe 4/4), and the patched bridge published her at 720x1288 and
drove Ditto from her speech: **`renders 211`** audio-driven chunks, `late 0`.

And yet **two full takes, 67 s and 82 s, came back with an audio track at
`max_volume -84.3 dB`** — silence. The engine was genuinely speaking at the time
(`app.log`: `put audio stream 16000: (3200,)` repeatedly, MuseTalk inference 242 frames).

The difference is one line that appears in `bridge.log` only when the bridge is unpatched:

```
NOVA_FACE=ditto    (no such line, ever)
NOVA_FACE unset    bridge: audio published 100 frames (320 samples @ 16000Hz)   ... 13200 ...
```

and on the page the remote audio track goes from `track.muted=true` under Ditto to
`muted=false` without it. So under `NOVA_FACE=ditto` **nothing reaches the LiveKit audio
track**: Ditto consumes the PCM for lip-sync and the publish side never gets it. That is the
next bug for this lane, and it is in `nova_ditto.py` / the A3-A4 anchors of
`ditto_bridge_patch.py`, not in Ditto itself.

`recordings/ditto_take1_silent_audio.mp4` is kept as the evidence.

## 4. Her lips move, and here is how that was checked

`logs/novarec_lips_speech_vs_silence.png`. The windows are **chosen by the audio, not by eye**:
per-0.5 s RMS over the file gives speech at 3.6-7.2, 13.9-21.3, 27.5-30.0, 33.4-36.4 s and
silence at 7.2-13.9, 20.5-27.5, 30.0-33.6, 35.1-73.3 s. Four frames are sampled from two
speech windows and two silence windows:

* **in both speech windows** her mouth is open, teeth visible, and the shape changes frame to
  frame — articulation;
* **in both silence windows** it is a closed-lip smile and stays closed.

A first attempt measured mean frame-to-frame difference in a fixed mouth box and **failed to
separate speech from silence** (ratios 0.91-1.34 speaking, 0.85-0.99 silent): the avatar's
head moves far enough under the idle animation that a fixed box is measuring the body, not
the mouth. That number is reported here rather than dropped, because it is the one that looks
like a result and is not.

**This is MuseTalk's lip-sync, not Ditto's.** Whether Ditto's lips move in the live path is
still unmeasured, and will stay unmeasured until §3 is fixed.

## 5. `torchfix/README.md` was wrong, and it cost a pod

The previous session's handover said the volume's torch was missing **one** 17 KB file and
gave the cp. The cp cannot work:

```
cp: cannot create regular file '.../torch/lib/libtorch_global_deps.so': No such file or directory
```

ENOENT on create means the **parent directory is gone**. Measured, 3 seconds of `ls`:
`torch/lib` does not exist, **1** `.so` survives under `torch` (`_C.cpython-311…so`), and the
tree is **878 MB** of a ~2.9 GB install. The interrupted `pip install --upgrade torch` removed
every shared library, ~2 GB of them. `import torch` names `libtorch_global_deps.so` only
because `_load_global_deps()` is the first thing `torch/__init__.py` does — first casualty
reported, not only casualty. That diagnosis was taken from the error string instead of the
directory, and it cost this session pod 1.

The ~2 GB cannot go back on the volume (a 2 GB write still fails). So torch goes on the
**container disk** and the volume is never written:

```bash
env -u PYTHONPATH python3 -m pip install --target /root/torchfix \
  --index-url https://download.pytorch.org/whl/cu129 "torch==2.9.1+cu129" "torchvision==0.24.1+cu129"
```

**84 seconds**, 7.4 GB on an 80 GB container disk, both import. `/root/torchfix` goes first on
`PYTHONPATH`. `boot.sh` hardcodes its own `PYTHONPATH`, so the run uses `/root/boot_novarec.sh`
— boot.sh with that **one line** rewritten, verified by `diff` in the job log. This is a
per-pod cost, not a repair: every new pod pays 84 s until somebody clears ~3 GB on the volume.
Corrected in full in `docs/nova-ditto/live/torchfix/README.md`.

Two more things the volume still needs, both found the same way:

* **`resampy`** had lost `resampy/core` — another legacy-sourceless `.pyc` casualty. `app.py`
  died on it instantly. Healed into `/root/torchfix`; one package was the whole fix and the
  import chain then ran clean (`logs/novarec_HEAL`).
* **`aiortc`** is the trap `boot.sh` cannot see: its pip step is gated on
  `import flask,edge_tts,websockets`, which **passes** on this volume, so boot.sh never
  installs aiortc and the bridge dies on it. Installed explicitly before boot.

## 6. What this cost, honestly

| pod | min | $ | what it bought | what it cost |
|---|---|---|---|---|
| `jv11u2az32t4gx` | ~4 | 0.05 | proved the handover's one-file torch fix is impossible | I trusted a README instead of `ls`, and the job `exit`ed on failure with no way back in |
| `wscjtne84igvji` | ~37 | 0.53 | torch, the stack, the page assertion, **five takes, the recording** | three takes wasted on the fake webcam |
| | **~41** | **$0.58** | | |

The one thing that stopped this being a fourth empty session was a **CMD channel** in the job
script: a background loop that runs any shell script PUT to `/root/in/CMD`. Pod 1 died useless
because a one-line question needed a whole new pod. With the channel, pod 2 absorbed a failed
Ditto launch, a missing package, a bridge restarted with the wrong environment, two harness
bugs and five takes **without a single extra pod**. Keep it.

## 7. What the next session should do, in order

1. **Fix Ditto's audio** (§3). The bridge never logs `audio published` under
   `NOVA_FACE=ditto`. Start at the A3/A4 anchors in `tools/pod/ditto_bridge_patch.py` and the
   publish side of `tools/pod/nova_ditto.py`: the PCM is reaching Ditto, it is not reaching
   `asrc.capture_frame`. Then re-measure §4 on Ditto.
2. **Order matters when restarting the stack by hand**: bridge first, then `app.py`. Replacing
   the bridge under a live `app.py` drops the engine
   (`BRIDGE_DROP ... frames_this_conn=0`) and it does not reattach.
3. `/workspace/.env` **does not exist** on this volume, so `boot.sh`'s `[ -f /workspace/.env ]`
   is a no-op and `LIVEKIT_URL` and the rest come from the pod environment. A hand-restarted
   service must inherit them (this session read them from `/proc/<rt_lk pid>/environ`).
4. The volume's torch is still broken. Either clear ~3 GB and reinstall it there, or accept
   the 84 s `/root/torchfix` cost per pod and keep `/root/boot_novarec.sh`.
5. The security item from the previous session is **still open**: `boot.sh`'s deploy prints the
   full remote URL on a failed deploy and that URL carries the volume's GitHub deploy token.
   **Rotate it.** Every log committed here was passed through a redactor and scanned again
   before the commit; nothing is known to have leaked.
