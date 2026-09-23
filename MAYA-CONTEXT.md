# MAYA — project context (read first, every session: laptop, cloud, or phone)

## What Maya is
An AI live-selling host: a talking avatar that streams to Facebook (and YouTube), reads live comments, answers every
viewer BY NAME in her own voice, gestures, and runs a selling "show" when chat is quiet. Owner: Refael (non-coder;
directs, tests, decides). Product goal: better behaviour than BocaLive, cheaper than Anam/HeyGen, fully self-owned.
Managed avatars (HeyGen etc.) are REJECTED — do not propose them.

## Stack (what runs where)
- GPU pod on RunPod (image ghcr.io/dsbeauty01-web/maya-lt, registry cred ghcr-maya-lt) with network volume
  maya-persist: face bakes, gesture clips, host.env with keys. The image self-starts (MAYA_AUTOSTART=1) and has a
  self-stop guard.
- Face: LiveTalking + wav2lip. Talking faces: maya_w2l (warm room, serum in hand) and — after v4 — maya_white
  (white studio, same set as every gesture clip → no room jumps).
- Transport: engine → WebRTC (WHIP) → SRS → RTMP → ffmpeg tee → Facebook (+ YouTube). Scene overlays in the push.
- Voice: OpenAI TTS (coral) through the engine; 24 kHz to the stream, 16 kHz to the lips; soft-knee loudness;
  ONE voice path (voice_cache.py shared by engine + warm_voice.py).
- Brain: brain_server.py (catalog truth gate, instant answers w/ fuzzy typos, LLM fallback), host loop maya_lt.py
  (showrunner program, gestures by meaning with a budget, callbacks, polls, empty-room close).
- Code: repo dance-project, branch maya-p1-finish, folder maya-ops/lt/.

## Rules that cost a month to learn — never break them
1. ONE agent touches the RunPod account/pod at a time. Stop pods by explicit id only; never sweep (other projects).
2. Nothing restarts during a live. Tune on a recording; apply to the next live.
3. Patches merge on top of the latest green code — never overwrite whole files from an older package.
4. "Healthy" = frames AND audio measured on the pushed stream (dBFS/LUFS), never "a process exists".
5. Judge by a recording Refael watches; mock QA proves code, not how she looks or sounds.
6. Keys live in host.env / cloud environment variables — never in the repo, never in chat.

## Secrets (names only — values live in env, never committed)
OPENAI_API_KEY · RUNPOD_API_KEY · FB_PAGE_ID · FB_PAGE_TOKEN · (YT_CLIENT_ID · YT_CLIENT_SECRET · YT_REFRESH_TOKEN) ·
ELEVENLABS_API_KEY (optional) · BUY_URL · GITHUB token only for the image registry

## Skills (in skills/): streamer · runpod · runpod-serverless · live-engine-blueprint · live-host-script ·
baked-gestures · commercial-gestures · live-avatar-gestures · voice · channels · youtube-live-api · bocalive-playbook ·
host-controller · tool · ai-host · money-avatar …  Read the relevant one before acting.

## Where we are (2026-09-23)
Proven on air: face 30 fps, full-band loud voice (−19 dBFS), answers by name in 0.2–3.7 s, gestures by meaning,
showrunner program, callbacks, questions. Refael's feedback: rooms jump every ~10 s (warm talking face vs white
gestures), gestures too short to see, voice changed on his name. Fix = v4 (maya-white-room-v4.zip): white talking
face, 30-s white showcase, gestures 2.5–4 s, one voice path, "Refael" said "Rafael", brain thinks during the gesture.
Next: merge v4 → bake_white.sh → warm_voice.py → 3-minute recording → Refael watches → first real live.
