# Nova: swap MuseTalk for Ditto (handoff for the Nova project)

> **In this repo (nova-avatar, branch `ditto-from-maya`) everything below is already copied into `ditto_from_maya/`, so no access to the private maya-lt repo and no GitHub token are needed:**
> `code/` ditto_server.py, ditto_up.sh, ditto_wide.py (sits next to the server, imported from there), motion_bank.py, ditto_renderer.py (reference), prebake_gate.py ·
> `assets/` nova_idle.mp4 (+ .gate.json), nova_bank.mp4 (+ .json, .gate.json) · `profiles/` live_trio_nova.json, live_motion_nova.json · `proof/` nova_live_v2.mp4, nova_judge.md.
> Copied from maya-lt `lane/motion-transfer` on 2026-10-28. The paths in the table below are where they live in maya-lt.


**For:** the Claude session working in `dance-project` / `nova-avatar`.
**Goal:** Nova's live face engine moves from MuseTalk (LiveTalking) to **Ditto**, the engine already running Nova, Maya, Daniel and the Professor live in the Maya repo.

## Why Ditto
- **Her whole real body stays.** Ditto repaints only the lips, on top of her own idle video: body, hands, hair and eyes are untouched footage. MuseTalk repaints a face crop.
- **It already works on Nova.** Her Pixar-style face runs live in the Maya repo at 25 fps with 0 ms frozen. Lips track her voice at a correlation of +0.275; our best host scores +0.36. (Flat 2-D cartoons don't work. Nova's 3-D style does.)
- **License:** Ditto (antgroup/ditto-talkinghead) is Apache-2.0. The Maya code avoids InsightFace, which is non-commercial.

## Where everything is
Repo `dsbeauty01-web/maya-lt`, branch `lane/motion-transfer`:

| What | Path |
|---|---|
| Ditto server: standalone HTTP service, its own venv | `maya-ops/lt/ditto_server.py` |
| Installer + launcher: clones Ditto, downloads TRT weights, starts the server | `maya-ops/lt/ditto_up.sh` |
| Paste-back, silence gate, first-frame crop (imported by the server) | `bench/replace_musetalk_alt/ditto_wide.py` |
| Motion bank: long idle + gestures on demand (optional) | `maya-ops/lt/motion_bank.py` |
| Client side, how the Maya stream calls it (reference) | `maya-ops/lt/ditto_renderer.py` |
| **Nova's idle body video** (source) | `assets/live_trio/nova_idle.mp4` (+ `nova_idle.gate.json`) |
| **Nova's motion bank** (longer body + gestures) | `assets/live_motion/nova/nova_bank.mp4` + `nova_bank.json` |
| Nova's live settings (copy these values) | `profiles/live_trio_nova.json`, `profiles/live_motion_nova.json` |
| Proof videos of Nova live on Ditto | `bench/results/live-trio/nova_live.mp4`, `bench/results/live-motion/nova_live_v2.mp4` (+ `nova_judge.md`) |
| Body-video check (free, CPU) | `tools/prebake_gate.py` |
| Background reading | `release/LIVE-TRIO.md`, `release/LIVE-MOTION.md`, `release/MOTION-TRANSFER.md` |

Get a file without cloning everything: `git show origin/lane/motion-transfer:<path> > file`. Videos are stored as normal git blobs, not LFS.

## How it works (the contract)
1. On the GPU pod, run `DITTO_SRC=/path/nova_idle.mp4 bash ditto_up.sh`. The first run installs a Python 3.10 venv (torch 2.5.1 cu121 + TensorRT 8.6.1) and downloads the weights from HuggingFace, which takes 5–15 min. After that it starts in seconds. The server listens on `127.0.0.1:8031`.
2. Poll `GET /health` until `"ready": true`.
3. Feed audio with `POST /render`. The body is **float32 mono 16 kHz**, exactly `chunk_samples` long (16000 = 1 s by default). The reply is JSON `{"path": "/dev/shm/....npy", "n": 25, "h", "w"}`: 25 BGR frames, 1080×1920 or the source size, already the whole picture.
4. Send silence when she isn't talking. The stream never stops; in silence her own closed-mouth video plays.
5. **Delay the audio** by `DITTO_PRIME` frames (40 ms each). Every frame you get back is that far behind the audio you just sent, and the delay is constant, so lips and voice stay locked.

## Wiring it into Nova's stack
Today: OpenAI Realtime voice → `lk_bridge.py` → MuseTalk/LiveTalking frames → LiveKit.

New: OpenAI Realtime audio is **pcm16 at 24 kHz**. Resample it to 16 kHz float32, buffer it into 1-second chunks, `POST /render`, then publish the 25 returned frames to LiveKit at 25 fps, with the audio track delayed by `DITTO_PRIME × 40 ms`. Replace only the MuseTalk call; keep LiveKit, the brain and the games as they are.

## Settings that are known to work (from Nova's profiles)
`DITTO_AMP=0.6` lip strength for her: higher makes the lips bigger. Use 1.0 only for hosts whose mouth is hidden by a beard. `DITTO_CHUNK=25` · `DITTO_PRIME=35` · `DITTO_VAD=1` · `DITTO_THREADS=6` · `DITTO_EYE_HOLD=1` stops a crash when her head turns · `DITTO_WAIT_SEC=1500` (first boot).
GPU: Ampere or newer, because the TRT engines are "Ampere_Plus". An RTX 4090 or L40S on RunPod Secure works.

## Rules learned the hard way
- **The body is always a pre-made video, never a still.** A still gives a frozen body with a moving mouth. The idle video must have her **mouth closed** and her face about 200–470 px tall in frame. Run `prebake_gate.py` on any new body video; it should PASS or SOFTEN.
- **Don't cut or crossfade inside the body video.** Joins show up as jumps or flicker, and crossfades leave ghost faces. For gestures, use the motion bank. Every clip must start and end on the same rest pose.
- **Never `git lfs track` videos.** Pods clone without LFS, and a tracked video arrives as a 130-byte stub.
- Frames go through `/dev/shm`, because 155 MB/s is too much for HTTP. The pod needs enough shared memory.
- Cap the CPU threads. A RunPod pod reports 128 cores but only gets about 18.

## First step to try
Pull `nova_idle.mp4` and the four code files. On one pod, run `ditto_up.sh`, then send 10 s of any Nova voice WAV through `/render` and save the frames as an mp4. Compare it with `bench/results/live-trio/nova_live.mp4`. If it looks the same, wire it into `lk_bridge.py`.
