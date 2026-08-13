# MAYA — FAST BRING-UP (next-session cheat sheet)

Everything below assumes you're in the repo root. Pod costs money — the 3-hour money-guard
auto-stops it. Bring up only when you'll use it.

## 1. Start her (one command, ~10–15 min cold)
```
node maya-ops/deploy/maya-up.mjs
```
Waits for green, prints the pod links. Confirms `room=maya-live` (never nova-live).

## 2. Activate the pipeline
```
node maya-ops/deploy/maya-golive.mjs
```
Activates W2/W3/W4, re-points CONFIG to the new pod, health-checks.
> Note: `engine_8010` (her face render) can lag a few min behind the brain on cold boot —
> re-run golive or check `/test`. The brain/pipeline don't need the engine.

## 3a. Broadcast her face — YouTube
On the pod (ssh from maya-up output):
```
RTMP_URL=rtmp://a.rtmp.youtube.com/live2/<YT_KEY> bash /workspace/maya-ops/deploy/yt-testcast.sh
```
Then YouTube Studio → Go Live.

## 3b. Broadcast her face — Facebook
1. https://www.facebook.com/live/producer/ → pick the **Page** → Go live → **Streaming software** → copy Stream Key (keys expire per session).
2. Push it (fb-testcast.sh is written to /tmp on the pod by this session; re-create if gone —
   it's yt-testcast.sh with the FB RTMP URL):
```
RTMP_URL='rtmps://live-api-s.facebook.com:443/rtmp/<FB_KEY>' bash /tmp/fb-testcast.sh
```
   (runs in tmux `fbcast`; `tmux kill-session -t fbcast` to stop)
3. Back in Live Producer, click **Go Live**.

## 4. Prove the answer-back pipeline (the leads + brain demo)
```
# edit scratchpad/fire-test.mjs → set POD to the new pod id, then:
node scratchpad/fire-test.mjs
```
Expect: brain answers דנה/יוסי by name in Hebrew + a `רות` buy-intent row in the Leads sheet:
https://docs.google.com/spreadsheets/d/1GbsW397yNvXZzg-3obf94HZTS9bffydPdu59VaPLnrs/edit
> The pipeline itself (filter/classify/prioritize/leads) is already fixed & proven —
> see evidence/2026-08-13-pipeline. This step just confirms the two pod hops.

## 5. Shut down (stop the money)
```
node maya-ops/deploy/maya-godark.mjs
```
Deactivates all workflows + stops the pod (also ends any ffmpeg broadcast — it runs on the pod).

## Gotchas learned
- FB/YT stream keys are per-session — always grab fresh.
- CONFIG (Set) nodes in W2/W3 strip the body; the fixed code reads `$('Webhook')` directly. Don't "simplify" it back.
- Never let her bridge into `nova-live`. maya-boot forces `LK_ROOM=maya-live` inside RUNSVC.
- YouTube/Facebook comment **ingest** is still OAuth/review-blocked — demo uses direct injection (step 4).
