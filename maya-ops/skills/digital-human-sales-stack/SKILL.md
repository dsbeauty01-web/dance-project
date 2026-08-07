---
name: digital-human-sales-stack
description: Use this skill when building, architecting, or debugging Maya's streaming system or any AI digital-human livestream product — the video pipeline, reply insertion, GPU scheduling, comment ingestion, product display, or choosing open-source components. Triggers on Maya build, LiveTalking, MuseTalk, playlist queue, 播单, reply insertion, danmaku, chat ingestion, stream architecture, digital human live. Contains the copyable production architecture (Ctrip's published system) and the vetted open-source repo map (Aug 2026 deep research).
---

# Digital-Human Sales Stack — what to copy and from where

## THE architecture to copy: Ctrip's playlist-queue system (production-proven, published)

Ctrip runs thousands of digital-human shopping streams on this design. Cost −90% vs cloud
real-time generation. Copy it wholesale:

1. **播单 (playlist queue), not real-time generation.** 90%+ of stream time presents products
   known before the stream. Pre-generate each product's explainer video. The stream = a video
   queue pushed in order, looping from the head. Buffer a few segments before going live; keep
   generating while pushing so the stream never starves.
2. **Cut everything into ≤15-second segments**, each tagged {product_id, sequence_no}. This is
   THE trick: a reply can be inserted after the *currently playing* 15s segment, hitting the
   10–40s reply window. Without segmentation, insertion waits minutes for a block to end.
3. **Reply insertion flow:** viewer event (enter/question/CTA word) → strategy check → LLM writes
   answer → TTS+lipsync generates a temporary clip → compute insertion point from estimated
   generation time → seed generation from the last frame of the segment before the insertion
   point → insert into queue → **delete after playing once** (so it never recurs when the
   product loop comes around again).
4. **Frame continuity — mirrored circular buffer:** store anchor (tail) frames per segment;
   for a splice, take X/2 continuous frames after frame N (sequence Y), time-reverse into Z,
   splice Y+Z for a seamless loop, then background-replace/overlay before inserting. Kills the
   visible "jump" at insertion points.
5. **GPU scheduling — dual pools with priority:** pool A = real-time replies, pool B = offline
   generation. FIFO, bucketed by stream ID (keeps a stream's frames continuous). Flexible workers
   poll pool A first, fall back to pool B only when A is empty. Even on ONE rented pod this is
   just a queue-priority policy. Ctrip: GPU utilization +50%, cost −90%.
6. **Store the digital-human layer separately from backgrounds/stickers** — swap product panels
   and scenes without regenerating her (+30% video reuse).

Reply latency target: **10–40 seconds**. Do NOT chase sub-second for a selling loop; that's
conversation latency (a different, more expensive problem). Interactive-mode aspirational
target if ever needed: <500ms end-to-end; typical stacks 600–1000ms.

## Repo map (all open-source, all vetted Aug 2026)

**Backbone — `lipku/LiveTalking`** (Apache-2.0, active, v2.0.4 Jun 2026) — ALREADY OUR ENGINE.
Unused capabilities we should turn on rather than rebuild: RTMP out + virtual-camera out (the
path to OBS/Douyin/IG), action orchestration (plays custom idle video when not speaking = free
gesture system), interrupt-on-speak, multi-session concurrency, TTS plugins (gpt-sovits,
cosyvoice, edgetts, fishtts…), plugin registry (registry.py) for custom TTS/Avatar/Output.
Docs: doc.livetalking.ai. Perf reference: MuseTalk ~72fps on 4090.

**Minimal reference — `Henry-23/VideoChat`** (MIT) — cleanest cascade ASR→LLM→TTS→MuseTalk
template, ~3s first-packet on one GPU. Steal its module boundaries (src/thg.py, tts.py, llm.py).
Custom avatar = video in /data/video/ + avatar_list + bbox_shift. Voice clone = 3–10s wav.

**Sales brain — `xszyou/Fay`** — agent framework with an explicit 带货 (sales) controller mode,
auto-broadcast interface, business-system connectors, swappable LLM/TTS/ASR. Retail fork:
`MicroEngine/Fay_Sales`. Closest off-the-shelf "sales brain" to wire to our renderer.

**Chat/danmaku taps:** `skmcj/dycast` (Douyin live comments → WebSocket, forward anywhere);
hperfect danmaku service (self-hostable, Douyin `/dy` + TikTok `/tk` endpoints); TikHub paid API.
Pattern: comment WS → keyword/classifier → n8n → LLM → TTS → queue insertion.

**Avatar cloning (offline sibling):** `GuijiAI/HeyGem.ai` — clone face+voice from 10s–5min video,
fully offline, Docker. `GuijiAI/duix.ai` — on-device interactive SDK (Android/iOS, 1GB RAM).

## Product display + stream-out (the Chinese standard rig)

- OBS chroma key (green ~400–430 similarity) or obs-background-removal plugin; avatar layer on
  top, product media behind, overlay stickers as panels.
- **OBS virtual camera** = the universal workaround where RTMP requires follower minimums
  (Douyin ≥10k). LiveTalking outputs virtual camera natively.
- Output config: 1080p/30 (skip 4K), NVENC, bitrate ~4500/3000/2000 kbps by platform, and run
  virtual-camera + window-capture DOUBLE BACKUP so one crashed channel swaps instantly.
- Clone inputs for a new host: voice = 3–5 samples × 20–30s; image = 3–5min green-screen video,
  face ≥720p, frontal ±15°, face 40–60% of frame.

## How this maps onto Maya's existing stack

- Keep: MuseTalk engine, RunPod volume bakes, LiveKit, OpenAI Realtime (for the DIRECTOR/interactive
  path), n8n, FastAPI backend.
- Add: the playlist queue + segmenter + insertion service (new, small), dycast-style chat tap
  feeding n8n, LiveTalking's RTMP/virtual-cam out for OBS.
- Two modes, one system: **LOOP MODE** (playlist + insertions, cheap, 24/7-capable) and
  **LIVE MODE** (OpenAI Realtime, director-driven, for demos/high-touch moments). Sell loop mode;
  demo with live mode.
