# WIRING — the same 4 lines in every game

```js
import { createLights } from '/shared/nova-lights.js';
import { createMoves } from '/shared/move-recipes.js';
const lights = createLights($('fx'), { video: $('usercam'), debug: Q.get('dots') === '1' });   // own layer; reads the video's object-fit (cover or letterbox)
const moves  = createMoves(lights, { mirror: true });                                           // [ADAPT] = the kit's mirror setting
K.onKid = (out, k) => { lights.feed(k); /* …the game's own logic… */ if (OPEN) moves.live(OPEN, k); };   // feed EVERY frame; live() only while an action is open
```
Per moment: `moves.cue(id, opts)` → each frame `moves.live(id, k)` → the game's referee decides → `moves.result(id, 'ok'|'near'|'miss', reading)` → `moves.clear(id)`.
**The referee that scores stays the game's own certified judge.** Recipes only show. Where a game has no judge yet (shapes, hello, slide, pops), `moves.live()` returns a reading with `.ok` that can be the judge.

| Game (branch) | Moments → recipe ids |
|---|---|
| **Intro** (shared) | step-back gate → `intro.presence` (every frame until ok) · the shoulder beat → `intro.shoulderL/R` (replaces the old shoulder light; keep the page-owned sting) · optional greeting → `intro.hello` |
| **Freeze v2** (stage-freeze2) | music on → `freeze.dance` · the stop → `freeze.stop` + live during the hold · Hold held/almost/missed → ok/near/miss · round 3's star freeze → also `freeze.shape.star` as a bonus |
| **Nova Says FAST** (novasays-fast) | a real command → `says.armsUp|armsOut|handsHead|leftUp|rightUp` · a trick → `says.trick` · judge result → ok/miss · [ADAPT] FAST's "one arm up" is side-free: cue `rightUp`, accept either arm |
| **Wave** (wave-lights) | Nova's demo → `wave.arm` cue {arm, dir, ms} · the child's turn → live · detector done → ok (move the direct lights calls into the recipe) |
| **Up Groove** (upgroove) | each round → `groove.bounce` cue {nextBeatAt, lead} · each graded bounce → ok/near/miss (replaces the direct beatRing/hit calls) |
| **Upper Body** (beta) | [ADAPT] its actions → `upper.slide`, `upper.popL/R` |

Rules: one open action at a time (speed glow can run under a cue). Clear on every phase change: `moves.clear()`.
