# Session report — choppy-while-dancing, solved (2026-10-21 → 10-22)

**Outcome: BETTER (founder-confirmed).** Nova's live video is no longer choppy during the dance.

## The problem
Founder, far from the pod (EU-RO-1 Romania → US LiveKit edge → Asia), saw the dance stutter —
not a load delay, not frozen frames. Loading and the engine were fine.

## How we found the real cause (three wrong turns, then the fix)
1. **Blur fix made it worse.** Raising the top layer to 10 Mbit and removing the 360p/180p simulcast
   layers gave a far viewer no lighter option, so it buffered. Reverted.
2. **adaptiveStream + one body.** Flipped adaptiveStream ON and dropped the A/B body swap (one body,
   no seam hitch). Helped the hitch, but the dance was still choppy.
3. **The actual cause — bitrate starvation (founder's measurement).** The recording had 0 frozen frames,
   but 1076×1924 @ 3 Mbit = **0.06 bits/pixel** (needs ≥0.12). Too big a picture through too thin a pipe.

## The fix that worked
Publish-side **downscale to 720×1288** in /workspace/lk_bridge.py (numpy nearest-neighbour, cached index
maps), top layer 3 Mbit, simulcast ON. 720×1288 @ 3 Mbit = **0.129 bpp** — over the floor.
Measured live: pub 720×1288, received top ~3.0 Mbit → bpp **0.13–0.14**, avg QP **39 → 22** (per-pixel
quality ~doubled). Simulcast still gives 180×322 / 360×644 fallbacks for a weak link.

## Also shipped this session (all on beta, none merged)
- ONE game body for the whole round (no mid-game setAvatar, no seam swap).
- adaptiveStream + dynacast ON (?adapt=0 to force the top layer for testing).
- On-screen ?report readout (received layer, fps, freezes, dropped) so the founder reads his own stream.
- Talk self-test (docs/TALK-TEST.md): she feels live — ~1.04 s median reply, INPUT-LOCK drops garble.
- Corrections recorded: freeze poses are PoseClip page overlays (not engine swaps); "lips-on = heavy
  MuseTalk" was unmeasured (GPU sampled ~0–1 %).

## Commits on beta
408c71f downscale 720×1288 · 05f88b0 talk-test · 376c3c0 choppy findings · a997e2d one-body+adaptiveStream
· 1f09f71 ?report overlay. Plus the GROOVE-1080 bodies and the deploy-branch fix (d65a228) from before.

## Pods & spend
All test/bake pods terminated via REST; proactive-kill watchdogs (45 min) + reminders enforced it.
Pods of mine running at session end: **0**. RunPod balance now: **$20.48**.

## Next (not done — awaiting founder)
- If 720×1288 is still not smooth enough on his path: 540×966 @ 3 Mbit (0.23 bpp).
- A game-phase talk-test to verify the 4 laws that stayed silent (holds mute / no-negative-on-break /
  consent / truth-gate).
- When the founder calls it good: PROMOTE v1.4 PR (must include the deploy fix d65a228). The lk_bridge
  downscale lives on the volume (reproducible via tools/pod/downscale_lk_bridge.py), not in the page.
