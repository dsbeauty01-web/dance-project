# WAVE — put the new lights into the REAL Wave game (beta/wave.html) · modules written and tested

## 0 · What changes for the child
- **Before his turn (the cue):** while Nova's demo wave plays, dots light up **along his own arms**, one joint after another, in wave order (wrist → elbow → shoulder → shoulder → elbow → wrist). He sees the path on his body before he moves.
- **During his turn (the light follows him):** a glowing comet with a tapered fading tail rides **where his wave actually is** — the joint that is lifted highest right now, smoothed, 60 fps, drawn slightly ahead to hide the camera delay.
- **When the wave reaches the far hand:** gold burst + ring at that hand + "YES!".
- Nothing else changes: same video demo, same rounds, same music, same voice lines.

## 1 · The files
- `shared/motion-detect.js` → `WaveDetector` (tested — §5).
- `shared/nova-lights.js` → `createLights(canvas, {video, mirror})`: One-Euro smoothing per joint, own 60 fps loop, prediction, additive glow, `waveCue()`, `comet.start/follow/end()`, `burst()`, `word()`.
- `test/motion_detect_test.mjs` → run it first.

## 2 · Wiring it into beta/wave.html (the CLI adapts names — log every [ADAPT])
```js
import { WaveDetector } from '/shared/motion-detect.js';
import { createLights } from '/shared/nova-lights.js';

const lights = createLights($('fx'), { video: $('usercam'), debug: Q.get('dots') === '1' });   // draws on its OWN layer over #fx; mirror defaults to the kit's (true)
const wave = new WaveDetector();
let turnOn = false;

// in the page's existing keypoint callback (the kit's K.onKid) — ADD, don't replace:
lights.feed(k);
if (turnOn){
  const r = wave.update(k, performance.now() / 1000);
  lights.comet.follow(r.front);                      // the light rides the real wave
  if (r.done){                                       // the wave reached the far end, in order
    lights.comet.end();
    lights.burst(r.done.dir === 'L→R' ? 'rWrist' : 'lWrist', 'gold');
    lights.word('YES!', r.done.dir === 'L→R' ? 'rWrist' : 'lWrist');
    // → call the page's existing success path here (see §3)
  }
}

// when Nova's demo wave starts playing (handywave.mp4):
lights.waveCue('L→R', DEMO_MS);                      // [ADAPT] DEMO_MS = the demo clip's wave duration; direction = mirrored to the child's view
// when the child's turn starts:
wave.reset(); lights.comet.start(); turnOn = true;
// when the child's turn ends (success or timeout):
lights.comet.end(); turnOn = false;
```
- **Delete** the old comet drawing code (the rejected look). Keep the old judge — see §3.
- **Mirror check:** open with `?dots=1`. White dots must sit ON the child's joints. If they're on the wrong side, pass `mirror: false`.
- **Double lights check:** the kit's own LightEngine still draws on `#fx`. If the old comet/glow shows under the new one, remove those old `K.L…` calls from wave.html.

## 3 · Who decides "success" (don't break what's certified)
Run **both** the existing Wave judge and `WaveDetector` for the next 20 turns and log both results per turn (`[WAVE] old=pass new=pass dir=L→R ms=1180`). Report the agreement table. The founder decides which one scores. Until then the OLD judge scores; the new detector only drives the lights.

## 4 · Look rules (from the research)
- One color per meaning: **cyan = where to go / the moving light**, **gold = you did it**.
- The comet never draws where the child isn't: it only follows a detected front; no front → no comet.
- Light adds up (additive), soft halo + bright core + thin white center; tail fades out within 0.35s.

## 5 · The detector's tested behavior (node test/motion_detect_test.mjs)
| Case | Result |
|---|---|
| wave left→right / right→left | 59/60 · 59/60 caught |
| slow wave (2.6s) · slow laptop (8 fps) | 40/40 · 40/40 |
| raising one arm · both arms up · both up-and-down · standing still | never counted as a wave (60/60 each) |
| random bumps on random joints | 57/60 correctly ignored |
| **KNOWN LIMIT** small wave (0.2 shoulder widths) | ~65% caught |
| **KNOWN LIMIT** far child (half size) | ~75% caught → fix: a "come closer" cue when shoulder width is small |

A kid's normal wave is big (0.3–0.5 shoulder widths) — that's the 59/60 row.

## 6 · Proofs before the founder plays
1. `node test/motion_detect_test.mjs` → 21 pass.
2. `?dots=1` screenshot: dots on the joints.
3. A 20-turn log with old vs new judge.
4. One short screen recording: cue dots → comet following the arm → gold burst.
