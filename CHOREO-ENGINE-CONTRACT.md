# Choreo Engine — contract (nova-commercial.html, branch commercial-v1)

**What changed:** a game is now DATA. Every game (Wave Magic, Freeze, Hello Hello, Up
Groove, Wave, Bounce) is a **choreo JSON**. The engine loads it, validates it, and adapts
it into the exact timeline events the proven scheduler (`gameTick`) already consumes — so
Zone 1 (video clock), Zone 2 (one duck engine) and Zone 3 (one mouth / SpeechArbiter) are
untouched. Proven behavior-preserving: the adapter reproduces each game's legacy
`TIMELINE_*_RAW` byte-for-byte (see QA below).

## Where things live
| Thing | Where |
|---|---|
| Canonical game data | `{id}.choreo.json` (one per game) |
| Runtime source | inline `<script type="application/json" data-choreo id="choreo-{id}">` blocks, merged into `CHOREO_EMBED` at load (works under `file://`) |
| Timeline source of truth | the legacy `TIMELINE_*_RAW` arrays in the page |
| Per-game brain | `tools/choreo-packs.js` |
| Generator (single source) | `tools/build-choreo.js` — inverts each RAW → choreo, merges the pack, writes the `.json` files, injects the inline blocks, and PROVES the round-trip |
| QA | `tools/qa-choreo-engine.js` (22 checks) |

**To change a game:** edit its `TIMELINE_*_RAW` (timing/cues) or `tools/choreo-packs.js`
(brain), then `node tools/build-choreo.js`. Never hand-edit the inline blocks or `.json`.
**To add a game:** add a `TIMELINE_*_RAW` + a SONGS entry + a pack, run the build.

## Choreo schema v1
`{ schema:1, id, title, media:{video,audio,durationMs}, bakedSpeech:[{start,end}ms],`
`beats:[{t,name}], demos:[{t,emoji,label,instr}],`
`windows:[{start,end,move,pts,soft?,cueStyle?,emoji,label,instr,dir?,holdMs?}],`
`knowledge, styleExamples, scripted:[{t,id,file,delivery}], stopResume, summaryTemplate, dosage, noSpeak?, blocked? }`

- `move` ∈ the move registry (`CHOREO_REGISTRY` in page). `cueStyle` ∈ `badge|glow-joints|travel-arm`.
- Unknown field / move / cueStyle → `validateChoreo` refuses the game with a loud console error.

## Worker-facing events (client → worker, over the existing `game-event` bus)
CLI-B: these are what the client emits. Consume the new one; the rest are unchanged.

| event | when | payload | note |
|---|---|---|---|
| `song_start` | game start (~0s) | `{song, sec}` | unchanged |
| **`game_brain`** | game start, once, right after `song_start` | `{song, knowledge, styleExamples, dosage, summaryTemplate}` | **NEW** — inject `knowledge` + `styleExamples` into her session at `phase:game`; use `dosage` for spacing/caps; `summaryTemplate` for the end closeup. Ignored safely until wired. |
| `move_cue` | each window opens | `{action, dir, label}` | unchanged |
| `music_tick` | ~1s | `{sec}` | unchanged |
| game reactions | on hit/streak/miss | `{event, action, isFast, streak, score}` | unchanged (`first_hit/hit/streak/miss/freeze_*`) |

The choreo's `scripted[]` lists the cached-WAV contract (ids/times/files) — **whether the
worker plays cached WAVs or teaches live is the worker's call** (live-first is under a drift
test; cached WAVs return for a game only if requested-vs-audio-start median > 1s). The client
does not schedule scripted WAVs.

## QA (run before any delivery)
```
node tools/qa-choreo-engine.js      # 22 checks: syntax, adapter≡legacy, block≡file, validation
node tools/build-choreo.js --check  # 6/6 round-trip (adapter reproduces every legacy timeline)
```
Runtime (browser) pass — cues fire on the video clock, travel-arm renders, no page errors —
still needs a Playwright run in an env where it is installed, or the founder's Step-1 local
smoke test: open `nova-commercial.html?nonova&game=wavemagic` (green ENGINE v1 banner).

## Not done yet (client)
- POP (mid-game closeup grows on a big moment) — waits on in-game witness-mode avatar + a live look.
- Deploy to the preview URL — outward-facing; needs the founder's GitHub auth.
