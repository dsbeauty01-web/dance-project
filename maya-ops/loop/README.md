# LOOP MODE — pre-generated playlist streaming (Ctrip pattern)

The cheap, hours-long version of Maya: 90%+ of the stream is pre-baked video of her
presenting products; live questions become one-shot answer clips inserted between
15-second segments. Full plan + founder/code split: `../LOOP-MODE-PLAN.md`.

## The pipeline

```
catalog.json ──> templater.mjs ──> scripts/<id>.he.json     (laptop, node — WORKS NOW)
                      │                 5-part script, playbook rules enforced,
                      │                 [NEEDS-FOUNDER] holes fail the build
                      ▼
              bake_playlist.py ──> bakes/<id>/NN-role.ts    (pod — TTS works; MuseTalk
                      │                 + manifest.json      render wired at first bake,
                      │                 AI label burned in   MAYA_BAKE_MODE=mux tests now)
                      ▼
              playlist_server.py ─> ONE ffmpeg -> RTMP      (pod — loops the playlist,
                        /insert = gapless one-shot answers,  /kill = BRB, /state)
```

## Status 2026-08-07

- templater: **working**, run against the real catalog — drafts generated with 3 founder
  holes per product (gift / usage scenario / testimonial).
- bake: TTS + label + TS segmenting written; **MuseTalk offline entrypoint must be
  confirmed on the pod at first bake** (fails loudly, never pretends). `mux` mode lets the
  whole chain run today without lipsync.
- player: written to the single-ffmpeg-stdin design (gapless insertion); **first pod run
  must verify YouTube tolerates the TS splice** — if not, fallback is filter-based concat.
- reply-insertion generator (question -> TTS clip -> /insert): NOT BUILT YET (Phase 3).
