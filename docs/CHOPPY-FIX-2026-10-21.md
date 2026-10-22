# Choppy-during-dance fix (2026-10-21)

Symptom (founder): video choppy/laggy WHILE she dances (not slow to load).

## Diagnosis — it is the network path, not our render
Pod side, sampled every 10 s during a live round (gallery/wd/podstats.log):
- engine render **fps = 25, steady** · GPU util **~0-1 %** · mem ~12.7 GB.
→ The source stream is smooth and the 4090 is nearly idle. Choppy is NOT the engine/GPU.

Browser side, 60 s round from a well-connected (US) client:
| config | received layer | fps | freezeCount | framesDropped |
|---|---|---|---|---|
| adaptiveStream ON  | 1076×1924 (top) | 25 | 0 | 10 |
| adaptiveStream OFF | 1076×1924 (top) | 26 | 0 | 11 |

From a good connection both are smooth and full-res. The choppy only appears on the long
Romania(pod) → US(LiveKit edge) → Asia(viewer) path when the link can't sustain the forced top layer.

## Fix shipped (beta a997e2d)
1. **adaptiveStream + dynacast ON** (`?adapt=0` forces off for A/B testing). The client now
   subscribes to the simulcast layer its bandwidth can sustain instead of stuttering on the top one.
   WARNING checked: adaptiveStream picks the layer from the video element's rendered size, so a small
   panel could lock to a low layer and undo 1080p. **It did not** — on a good connection the received
   layer stayed 1076×1924. On a weak connection it will step down on purpose (that is the fix).
2. **ONE body for the whole game** — dropped the A/B swap + seam logic. No mid-game setAvatar, so the
   one swap hitch is gone. nova_groove_a_1080 from beat one to the medal. Intro/ending keep nova_idle2.
   Voice stays in the air in GAME. JUDGE-TRUTH v1.3 untouched.
   (The volume lk_bridge.py keeps simulcast ON with a 10 Mbit top + 360p/180p layers, so the layers
   adaptiveStream chooses from exist.)

## Corrections to the earlier report (founder)
- Freeze poses are **page-side mp4 overlays (PoseClip)**, NOT engine body swaps. A different-framed
  groove body would therefore NOT make "every freeze jump" — I was wrong to say that.
- "Lips-on = continuous MuseTalk load" was **unmeasured**; she is silent most of a round and the GPU
  sampled ~0-1 %. Not stated as fact.

## Still only the founder can confirm
Choppy is a property of the founder's own connection/path; a US test client sees it smooth either way.
The fix is the mechanism (graceful layer drop); the founder's live play is the proof.

## Update 2026-10-22 — bitrate starvation fix (downscale publish to 720×1288)
Founder measured the recording: 0 frozen frames, but 1076×1924 @ 3 Mbit = **0.06 bpp** (needs ≥0.12) —
starvation, not freezing. Fix on the volume /workspace/lk_bridge.py (tracked here as
tools/pod/downscale_lk_bridge.py; the bridge file itself is volume-only, not in git):
- publish-side nearest-neighbour downscale to **720×1288** before VideoSource/capture_frame (numpy only,
  index maps cached per source size), keep top layer 3 Mbit + simulcast ON.
- Verified on the live track: pub=720×1288, received top ~3.0 Mbit → **bpp 0.129–0.144** (≥0.12),
  avgQP ~22 (was ~39 starved). Layers: 180×322@160k · 360×644@450k · 720×1288@3M.
- Backup kept on the volume (lk_bridge.py.bak-downscale-*). Next step if still bad: 540×966 @ 3 Mbit (0.23 bpp).
