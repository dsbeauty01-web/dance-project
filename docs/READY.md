# READY — FREEZE FULL FIX (all 8 errors · natural transitions · complete code · self-QA'd · FREEZE-APPROVED)

The approved sound design (array 12-14s gaps, strip-to-beat, sting, WebAudio scheduling) is LAW — untouched. This file fixes the experience around it. CLI: deploy exactly this; ambiguity = QUESTION, never improvisation.

═══════════════════════════════════════════════
## PART 0 — THE PHASE MACHINE (the spine)
═══════════════════════════════════════════════
```js
const PHASE = { INTRO:'intro', GAME:'game', HOLD:'hold', ENDING:'ending' };
let phase = null;
function setPhase(p){
  phase = p; log('[PHASE]', p);
  if (p===PHASE.INTRO || p===PHASE.ENDING){ routeVoice('engine'); }   // lips ON (MuseTalk), calm body
  if (p===PHASE.GAME){ routeVoice('air'); }                            // live V2V played by the page, engine gets NO audio
  if (p===PHASE.HOLD){ routeVoice('mute'); }                           // absolute silence, no generations
}
// routeVoice is the ONLY function allowed to change audio routing. Grep-proof required.
```

## PART 1 — INTRO = FULL MUSETALK CONVERSATION (fix the deaf bug)
```js
window.addEventListener('load', async () => {
  setPhase(PHASE.INTRO);                    // BEFORE the realtime session opens — no game muting exists yet
  await openRealtimeSession();              // standard INPUT-LOCK rules; engine path; calm body nova_idle
  // She greets: "Hi! I'm Nova — FREEZE time! What's your name?"
  // Then a REAL conversation: she listens and ANSWERS ANYTHING the user says —
  // name → warm echo with THE TRANSCRIPT NAME; questions → real answers; chit-chat → she chats.
  // The intro prompt block allows free conversation + steers gently: after the name (or 2 exchanges),
  // she explains: "when the music plays DANCE — when it stops... FREEZE! Ready?"
  // consent gate (real yes / tap) → startGame()
});
```
**Probe ×3 (must pass):** "I'm Rafy" → she answers with Rafy ≤2s, lips moving · a random question ("do you like pizza?") → real in-character answer · silence 20s → ONE re-invite → quiet · garble → `[INPUT-LOCK] dropped`, no invented name (grep prompt: zero example names).

## PART 2 — THE NEUTRAL-CROSSING TRANSITION SYSTEM (the natural-switch design)
**Design law: never teleport between mismatched poses. Cut bodies only at matched frames; music stays sample-exact.**

**2a. OFFLINE (build step, once):** scan the groove bake for its neutral crossings:
```python
# tools/find_neutrals.py — run on nova_idlegroove_v2's source frames
# pose-estimate every frame (MoveNet on the bake); score each frame's distance to the
# freeze clips' FIRST frame pose (the standing start). Output the N best-matching timestamps:
# neutrals.json = [1.9, 5.6, 9.4, 13.2, ...]   (expect one every ~2-4s in a bouncy loop)
```
Also trim each freeze pose clip to start at ARRIVAL, not stillness: find the first frame where motion-energy < threshold, then set the clip's in-point **0.3s BEFORE it** — she lands into the pose on screen (momentum reads natural), then holds.

**2b. RUNTIME — the swap scheduler:**
```js
const NEUTRALS = await (await fetch('neutrals.json')).json();  // groove-loop timestamps
function nearestNeutral(){                                      // in LOOP-time
  const lt = grooveLoopTime();                                  // current position inside the loop
  let best = NEUTRALS.reduce((a,b)=> Math.abs(b-lt)<Math.abs(a-lt)?b:a);
  return (best - lt + loopDur) % loopDur;                       // seconds until that neutral
}
// At each freeze: MUSIC cuts EXACTLY at f.at (WebAudio, already scheduled — the law).
// The BODY swaps at the nearest neutral within a ±0.6s window around f.at:
scheduleAt(gameT0 + f.at - 0.6, () => {
  const wait = nearestNeutral();
  const swapIn = Math.min(wait, 1.2);                           // never later than +0.6 past the cut
  setTimeout(()=> {
    flash(160); snowBurst();                                    // the mask = a game event, not a cover-up
    engineSwitchAvatar(FREEZE_CLIP[f.clip]);                    // clip starts at its ARRIVAL in-point
  }, swapIn*1000);
});
// The MELT (return): at f.at+f.hold the music slams back (exact); the body returns to the groove
// at the groove's loop START (a neutral by construction) with flash(120) + the release ding.
```
**Geometry law:** every freeze clip renders at IDENTICAL scale/position to the groove (LAW-FRAME-FULL). Verify: overlay-diff screenshot, head/feet anchors within 2%. If a pose clip's room/scale visibly differs → screenshot + QUESTION to the founder (bake-source decision, not a CSS hack).
**The kid's clock is the MUSIC:** stillness detection begins at f.at exactly (the kid freezes on the sound, not on her body swap).

## PART 3 — THE PRE-FREEZE WARNING (live, in the air)
```js
for (const f of FREEZES){
  if (!f.fakeout){                                              // the trap gets NO warning
    scheduleAt(gameT0 + f.at - 4.5, () => {
      if (phase!==PHASE.GAME) return;
      producerNote('warn: freeze in 3s. Say a SHORT playful warning, 3-5 words, like "get ready to freeeeze!" Nothing else.');
    });                                                          // LLM+TTS ≈1.5s → lands ~-3s
  }
  scheduleAt(gameT0 + f.at,           () => setPhase(PHASE.HOLD));
  scheduleAt(gameT0 + f.at + f.hold,  () => { setPhase(PHASE.GAME); fireVerdict(f); });
}
```
Speak-gate: the warning REPLACES the gap's one allowed line (no double-talk in a gap).

## PART 4 — CANNED-VOICE PURGE
Grep page+brain for every pre-rendered speech trigger ("wiggle", coaching WAV/mp3s, playCanned/voiceClip paths) → DELETE triggers + references → list every removed line in the report. Survivors (ear-approved sound design ONLY): `sting_freeze.mp3` + the release ding. Grep-proof: no other voice-content audio loads.

## PART 5 — VERDICT FAST
```js
function fireVerdict(f){
  const v = verdict(f);
  playDing(); scoreFreeze(f, v); hud.update(score, streak);      // instant at the melt
  producerNote(`verdict:${v} clip:${f.clip} streak:${streak}. React 4-6 words, specific, NOW.`);
  markLatency(v);                                                // log [VERDICT-LATENCY] ms; target ≤1500 median
}
```
If median latency >2500ms after tuning: REPORT it. Never re-introduce canned praise (founder's law).

## PART 6 — PERSONA (assistant-talk kill)
Game prompt fully REPLACES the base persona (log the active system-prompt hash at session open — prove the replace). Append: "NEVER assistant phrases ('I'd be happy to help', 'How can I assist', 'Sure!'). You are Nova the dance friend, never an assistant." Log-watch `/happy to help|assist you|as an AI/i` → `[PERSONA-LEAK]` counter (expected: 0).

## PART 7 — ENDING = MUSETALK TRIO
After the final verdict: `setPhase(ENDING)` (calm body, lips on) → celebration from REAL numbers ("«name», «held» freezes, «score» points!") → "Did you have fun? Tell me anything!" (feedback_text + emoji) → "Bye «name» — same time tomorrow?" → PULSE POST (paste the row).

## SELF-QA (the architect ran this on the file — the CLI re-verifies each at build)
✓ E1 deaf intro → Part 1 (phase machine guarantees no muting before GAME) · ✓ E2 warning → Part 3 (live, -4.5s, fake-out excluded) · ✓ E3 canned purge → Part 4 (sting+ding only survivors) · ✓ E4 transitions → Part 2 (matched cuts + arrival in-points + mask; teleports impossible) · ✓ late verdict → Part 5 · ✓ assistant-talk → Part 6 · ✓ mid-game voice = live-in-air only, holds = mute → Parts 0/3 · ✓ ending trio + PULSE → Part 7 · ✓ laws: INPUT-LOCK untouched, no pre-rendered SPEECH anywhere, music timing stays WebAudio-exact, FREEZE-APPROVED commits, sound design unmodified · ✓ code consistency: setPhase/routeVoice/scheduleAt/engineSwitchAvatar names align across parts.

## GATE
Build → self-test full run via claude-in-chrome → 🔔 recording to Downloads **freeze-ready-video** + 3 beeps 🔔🔔🔔 → HOLD for the founder's live test → merge only on his word.
Evidence: intro probes ×3 · neutrals.json + arrival in-points listed · removed canned lines · seam screenshots (geometry diff ≤2%) · [VERDICT-LATENCY] per round · [PERSONA-LEAK]=0 · phase log of one session · PULSE row.
