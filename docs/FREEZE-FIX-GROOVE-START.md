# FREEZE-FIX-GROOVE-START — she grooves from the FIRST beat (FREEZE-APPROVED · beta + main hotfix)

## THE BUG (founder-observed, last playthrough)
Music starts → Nova stays on the calm idle body (`nova_idle2`) → she only switches to the groove (`nova_idlegroove_v2`) when freeze #1 RELEASES — because the only `setBody(groove)` call lives in `release()`. Round 1 = a standing Nova. Wrong.

## THE FIX (3 places, ~10 lines)
```js
// 1 · startGame(): switch the body the moment the music starts (masked by the first-beat flash)
function startGame(){
  E.finishCal(); setPhase('game');
  setBody(BODY.groove);                        // ← the missing line. Groove from beat one.
  L.flash(140);                                // the existing first-beat ice-flash masks the cut
  music.play(); requestAnimationFrame(tick);
}
// 2 · setPhase('game') must ALSO guarantee the groove body (defense in depth — any path into GAME grooves):
case PHASE.GAME: routeVoice('air'); if (currentBody!==BODY.groove) setBody(BODY.groove); break;
// 3 · release(): keep its setBody(groove) — it's still right for freeze→groove returns.
```
Also verify the log: `[BODY] phase=game loaded=nova_idlegroove_v2` must appear BEFORE the first `[FREEZE]` line. If `setBody` is async (engine `/set_avatar`), call it 300ms BEFORE `music.play()` so the body is dancing on beat one, not a frame late.

## SCOPE
- `beta/freeze.html` (b0.x) and the live `pod/pages/animal-freeze.html` on main via a hotfix PR titled `PROMOTE v1.0.2 — groove from beat one`, body FREEZE-APPROVED. Nothing else changes.
- Evidence: one playthrough log showing the [BODY] order + a 10s recording of the intro→music transition (she grooves immediately). Hold.
