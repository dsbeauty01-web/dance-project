# MAYA on LiveTalking — the commercial live host, built from what failed on OpenTalking (2026-09-18)

## Why this exists
OpenTalking was a per-user chat widget forced to be a broadcaster: CPU render, ~5-char chunked speech
(hardcoded), no avatar switch, MuseTalk not even installed. LiveTalking is the opposite — its README
lists "24-hour unmanned live selling" as a use case, MuseTalk runs on GPU by default, gestures switch by
API, external audio is a supported path, and RTMP egress is documented (via SRS, no private repo).

## What this delivers (all offline-QA'd, 16/16 in qa_lt.py — no GPU needed to prove the logic)
- LIVE VOICE: ElevenLabs as a LiveTalking TTS module (ttsreal_elevenlabs.py) streaming pcm_16000 straight into
  the engine's audio frames — whole sentences, ~75 ms first audio, NO mp3 decode / resample / chunk gaps.
- LIVE BEHAVIOR: your brain on /human — name-first, catalog-true, instant answers, medical deflection, leads,
  buy link in the text reply. presence (edge, noise, price said once), cocreate (polls/VIP), room (joins/hearts).
- SMART GESTURES (the "hi maya→wave, how much→point, show me→both hands, thinking→nod" you asked for):
  free-edition rule is gesture-only-while-silent, so maya_lt waits for silence, fires the clip, leads 0.6 s,
  then speaks, then returns to idle. On camera: "Rafael —" (name, live) with the wave/point already up. Medical
  answers fire NO gesture and stay still. A viewer never waits behind a beat (answers interrupt the script only).
- SMART BAKES ON DEMAND: gesture clips → LiveTalking custom_config (lt_assets.py): audiotype 1 idle (auto),
  2 wave, 3 point, 4 show, 5 nod, 6 goodbye. Each validated as one continuous take (stitched clips rejected).

## Files (maya-ops/lt/)
lt_boot.sh (install|check|live|planted|down) · maya_lt.py (host) · lt_client.py (API + timing) · lt_assets.py
(clips→custom_config) · ttsreal_elevenlabs.py (voice module) · qa_lt.py + mock_lt.py + mock_elevenlabs.py (offline QA)
· brain_server/instant/presence/cocreate/room_awareness/maya_host/fb_tool · serum-c.en.json · persona_maya.md ·
beats.json · planted.json · gesture_mode/gm_*.mp4 (6 prepped clips)

## Run order (on the pod, one watcher for a GPU, UDP 8000 open — RunPod/Vast, NOT AutoDL)
1. Put in ~/.maya/host.env: ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID (voice D yd3FYOmSLO39myWHIQXq),
   FB_PAGE_ID, FB_PAGE_TOKEN, RUNPOD_API_KEY, RUNPOD_POD_ID, and the LT_AT_* lines lt_assets.py prints.
2. bash lt_boot.sh install          # ~25 min, persisted to the volume; restores the maya_serum bake from
                                     # maya-bakes-backup or re-bakes it; builds SRS; wires ElevenLabs + gestures.
3. bash lt_boot.sh check            # HOUR-ONE GATE, no Facebook: pulls the local RTMP and asserts fps>=24 and
                                     # real audio (dBFS>-40). If this fails, fix before spending on a live.
4. bash lt_boot.sh planted 3        # unattended: she waves/points/answers to 5 planted comments, 60 s recording.
5. bash lt_boot.sh live 15          # real Facebook live; I comment; pod down after.

## THE PROOF (what "done" means)
The 60 s recording (lt_60s.flv) shows: viewer "can i see it closer?" → "Rafael —" (name, her voice) → she raises
the product (SHOW clip) → whole-sentence answer → back to idle → text reply with the link. fps>=24, audio >-40 dBFS.

## Honest unknowns (only two)
1. The rtcpush→SRS→RTMP bridge and CANDIDATE/public-IP/UDP-8000 — documented, never run by us. The check gate
   catches it in hour one instead of mid-live.
2. The ElevenLabs TTS factory line: lt_boot patches the common `opt.tts == 'edgetts'` switch; on a newer registry
   build wire ElevenLabsTTS by hand (6 lines, header of ttsreal_elevenlabs.py). Everything else is proven.
Free edition adds a LiveTalking watermark on public platforms unless licensed; gesture-WHILE-talking is the paid
¥3000 model — buy only after this demo lands.
