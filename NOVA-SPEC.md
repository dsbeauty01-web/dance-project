# NOVA — Full System Spec (as of 2026-06-22)

A single source of truth for the **brain**, the **intro**, the **game settings**, the
**ending**, and how it all connects. Hand this to any chat/cloud session to continue work.

> **Product:** Nova is a warm "big-sister" AI dance companion for kids ~6–10. A short
> ritual: she appears, greets, the kid copies her moves on camera, she reacts live, and
> she ends with a hook to come back. ~8 months in; tech works, no real kid tests yet.

---

## 1. ARCHITECTURE (two halves)

```
 BROWSER (frontend game)                         CLOUD (the brain)
 ─────────────────────────                       ─────────────────────────────
 nova-join.html  (canonical)                     novapython  (Render web service)
  • MoveNet pose detection (TF.js)   ── HTTPS ──>  server.py  (FastAPI)
  • cue timeline + scoring                          POST /v2/create-session -> LiveKit token
  • prerendered Nova video (music)                  POST /v2/vision-observe  -> Gemini caption
  • LiveKit client  ◄── WebRTC ──►  LiveKit room ◄── agent.py (LiveKit Agent worker)
       Nova's live Runway face + voice                STT->LLM->TTS->Runway avatar
       game events over data channel
```

- **Frontend:** static HTML on GitHub Pages (`dsbeauty01-web.github.io/dance-project/`).
- **Brain:** `novapython` repo → Render. **Free tier spins down (~50s cold start) and has been crash-looping** — see §9.
- **Runway avatar = HEAD + FACE ONLY** (no body). The prerendered MP4 supplies the dancing body + music; Runway supplies her live reacting face.

---

## 2. THE BRAIN (novapython) — LOCKED components

| Piece | Value |
|---|---|
| **Voice** | ElevenLabs **Flash v2.5**, Loora voice `P6xfJudBtfcB1BM5ZWR7` — stability 0.65, similarity 0.90, style 0.30, speed 0.88–0.92, speaker_boost on |
| **STT** | **Deepgram Nova-3** server-side (browser SpeechRecognition disabled). lang en, smart_format, endpointing 250ms |
| **LLM** | OpenAI **gpt-4o-mini**, temp 0.85, **5-layer system prompt** (`personality.py`) |
| **Avatar** | Runway custom Pixar Nova `e976bbb2-de60-4da6-845e-4b754050e55b` — head/face only, ~500ms lipsync tax |
| **Vision** | **Gemini 2.5 Flash Lite** via `/v2/vision-observe` (SDK `google.genai`) — one warm visual detail |
| **Latency (warm)** | STT-final → first audio **~855ms** (700–1100). Floor = Runway lipsync ~500ms. "Magic" <500ms unreachable with the avatar |
| **Persona** | Cool magical big-sister (11–12 feel), 110% more excited than the kid, smile-in-voice every reply |

**Files:** `agent.py` (LiveKit worker brain + filler system), `server.py` (FastAPI: tokens, vision, memory), `personality.py` (5-layer prompt + phrase banks), `memory.py` (per-kid Postgres/RAM), `vision.py` (Gemini), `knowledge.py` (fact base).

**DO NOT TOUCH:** Loora voice/settings · Deepgram STT · `/v2/vision-observe` · Runway UUID `e976bbb2` · 5-layer prompt · `agent_v222` (suspended; OpenAI is the brain).

**Voice filler fix (done in code, deploy-gated):** the "ooo ooo"/Parkinson stutter is fixed on `main` — atomic `claim()`, `ahh` clip removed, `NOVA_FILLERS` defaults **off**, LLM pre-warm. Action remaining: ensure Render env `NOVA_FILLERS` ≠ 1 + redeploy. See `novapython/VOICE-FIX-DEPLOY.md`.

**Key env vars (Render):** LIVEKIT_URL/API_KEY/API_SECRET, OPENAI_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, GEMINI_API_KEY, RUNWAYML_API_SECRET, DATABASE_URL (optional), NOVA_FILLERS=0.

---

## 3. THE 3 CONTEXT PHASES (experience arc)

1. **Intro · Greet · Prep** — cinematic intro video covers the worker cold-start; Nova greets (by name if remembered), light prep, then the game. *Rule: never reveal Nova until BOTH her audio+video tracks arrive.*
2. **The Play** — Nova shrinks to a reacting **orb/face**; the big screen is her prerendered body dancing; she reacts to the kid's hits/misses over the data channel. Anticipation calls each move.
3. **Ending + Hook** — stars + score + a **specific** callback goodbye + a "come back tomorrow, I'll teach you the SPIN" hook. Memory saved for next time.

(See `NOVA-3-PHASES.md`.)

---

## 4. CANONICAL GAME — `nova-join.html`

Self-contained, frontend-only engine **with optional live Nova**. This is the one to ship to testers.

### 4.1 Media / timing
- **Video+music:** `nova-joined-small.mp4` (~90s, 6.2 MB, faststart) — single source, game clock = `video.currentTime` (zero A/V drift).
- **Dynamic focus:** Nova starts far/small, walks close by ~26s → CSS `scale 1.55→1.0` over first 26s so she's always well-framed.
- **VIDEO_START = 0** (plays from the top so the kid anticipates).
- **SONG_END = 56s.**

### 4.2 Moves & detection (MoveNet SINGLEPOSE_LIGHTNING, mirrored, flipHorizontal:true)
Detection is **calibrated** (neutral stance captured on "GO") and **forgiving** (head/shoulder score on *any* direction — the arrow just guides).

| Move | Signal (normalised by shoulder width) | Threshold | Reliability |
|---|---|---|---|
| head-left / head-right | nose-X vs shoulder centre | `|headDX| > 0.09` | ✅ strong |
| shoulder-left / -right | shoulder-line tilt | `|shTilt| > 0.045` | ⚠️ subtle (2D limit) |
| hips | hip-X sway vs shoulders | `|hipDX| > 0.06` | ⚠️ needs hips in frame |
| knee | knee lift vs baseline | `kneeLift > 0.10` | ⚠️ needs legs in frame |
| free (freestyle) | overall motion | `motion > 0.06` | ✅ strong |

**THRESH** = `{ head:0.09, sh:0.045, hip:0.06, knee:0.10, motion:0.06 }` (tuned from real session data).

**Framing grace:** moves tagged `needs:'lower'` (hips, knee) are **not penalised** when legs/hips aren't visible — Nova coaches *"stand back so I can see your legs."*

**Data-proven reality (seated upper-body session):** head ✅, freestyle ✅, shoulder marginal, hips/knee fail only because legs were off-camera. Not a system limit for upper body; lower-body moves need the kid standing & fully framed.

### 4.3 Detection zones (left/right split coloring)
The cued **side glows from that edge** and fades to center (so it never hides the kid):
- `head/shoulder -left` → **left half** glows + `←`; `-right` → **right half** + `→`.
- `hips/knee/free` → **full frame** glow.
- States: **armed = yellow → hit = green → miss = red**, with a shrinking timer bar.

### 4.4 Cue timeline (cards drive it; on `video.currentTime`)
- **Slow build** from **t=6s**, every 1.22s (window ~1.05s): head ×4 → shoulder ×4 → hips ×4 → knee ×4.
- **Double-speed** every 0.61s, reversed: knee → hips → shoulder → head.
- **Freestyle** ×3 long windows (any motion scores).
- ~3.5s before the first cue: "get ready… first move!"

### 4.5 Scoring
- Base points: head 100, shoulder 120, hips 130, knee 140, free 60.
- **Speed bonus** ×1.5 if hit in the first ~45% of the window.
- **Combo multiplier**: +10% per combo step (cap ×8). Miss resets combo.
- End **stars**: hit-rate ≥85%=5, ≥65%=4, ≥45%=3, ≥25%=2, else 1.

### 4.6 Live Nova session (optional, graceful)
- On Start → `POST /v2/create-session {kidId}` → LiveKit room (warms during intro+countdown; ~30–50s cold).
- Subscribes Nova's **video** (live Runway face, circle on her panel, glows green + lip-syncs when talking) + **audio** (ducks the music while she speaks).
- **No mic published** — she reacts to *dancing*, not noise.
- **Events sent** (data channel): `phase:dance` (start), `move_cue {action}` (each cue), `first_hit / hit / streak {action,streak,fast}`, `miss {action}`, `phase:goodbye` (end).
- Answers worker `request-vision` with a cam snapshot → specific reactions.
- **Offline fallback:** if the worker is down, the game runs unchanged and Nova **cheers/encourages locally** (voice + bubble: "yes!", "you're on fire!", "almost!"). Status chip: waking / here / offline.

### 4.7 Layout
Split screen — **Nova left, You right** (both fill); stacks vertically on portrait phones. Live skeleton overlay on the camera. Top-left debug panel (present, joints/17, headDX/shTilt/hipDX/knee/motion, which moves fire — tap to dim).

---

## 5. SECOND GAME — `nova-wave.html`
Same engine; arm-isolation wave. Moves: **shoulder-roll → elbow-pump → wrist-wave (hand up)** → freestyle, with `handywave.mp4` (~28.5s, 1.6 MB). Calibrated arm-raise tiers; picks the kid's more-raised arm. Inherits live Nova, intro, zones, debug.

---

## 6. ENDING
- Stars + score + `X of Y moves · best combo`.
- Worker goodbye (specific callback) when online; local fallback line otherwise.
- Persistent **hook** line ("tomorrow I'll teach you the SPIN 🌀").
- (Memory save TODO in clean engine — present in legacy v113-live.)

---

## 7. TELEMETRY (for debugging detection)
- `logserver.js` (node) serves the project **and** records every session to `sessions.jsonl`.
- Open `http://localhost:8787/nova-join.html` (not Pages) to record.
- Logs: session start, ~1.5s detection snapshots, every cue hit/miss with values, end summary.
- End screen also has **📋 Copy debug log**; data persists to `localStorage` (last 10).

---

## 8. URLS
- Canonical game: `https://dsbeauty01-web.github.io/dance-project/nova-join.html`
- Wave game: `…/nova-wave.html`
- Original full game: `…/v113-live.html` · Cinematic intro version: `…/v300.html`
- Worker: `https://novapython.onrender.com`

---

## 9. KNOWN ISSUES / PENDING
- **Worker crash-loops on Render** ("Instance failed" repeatedly). Prime suspect: open dependency ranges (`google-genai>=1.0.0`, `livekit-agents>=1.5.0`) pulled a breaking version on rebuild → import crash on boot. **Fix:** read boot traceback, pin the broken dep, redeploy. Free tier also spins down (~50s).
- **Worker `move_cue` handler:** the game sends it but `agent.py` doesn't yet act on it — so Nova doesn't *name* moves in her own voice (local voice does). Add a handler in `agent.py`.
- **Shoulder / hips / knee** detection is near MoveNet's 2D limit; head + freestyle are solid. Needs on-device threshold tuning per environment.
- **File sprawl:** 7 game HTMLs (nova-join, nova-joined, nova-wave, handwave, v300, v113-live, nova-test). Recommend: keep **nova-join** (+ nova-wave), retire the rest, add a landing page.
- **Not yet built:** sound juice (beeps/chimes), "fit in frame" helper, mobile QA, memory-save in clean engine.

---

## 10. TECH NOTES
- Pose: TF.js + `@tensorflow-models/pose-detection` MoveNet SINGLEPOSE_LIGHTNING, joint confidence ≥0.25.
- LiveKit client `livekit-client@2.13.3` (UMD, deferred).
- Videos re-encoded H.264 1280p CRF28 + AAC + faststart; originals kept as `*-orig.mp4` (gitignored).
