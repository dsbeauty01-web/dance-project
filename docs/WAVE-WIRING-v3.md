# WAVE — rewire for the ONE-ARM wave (replaces the wiring from WAVE-LIGHTS.md §2)

The detector now defaults to the game's real wave: ONE arm, shoulder→elbow→wrist ("out") or wrist→shoulder ("in"),
either arm. The result object changed, so the existing wiring in beta/wave.html (wave-lights branch) MUST change —
otherwise the comet rides the wrong joints and the burst always lands on the left hand.

## New result shape
`wave.update(k, t)` → `{ front, arm, chain, lifts, done }`
- `front`: 0..2 along `chain` (0 = shoulder, 1 = elbow, 2 = wrist), or null
- `arm`: 'left' | 'right' (the moving arm), `chain`: that arm's 3 joint names
- `done`: null, or `{ arm, dir: 'out' | 'in', ms, joints? }` (joints: 2 = elbow→wrist wave without a shoulder pop)

## The wiring (replace the old block)
```js
const wave = new WaveDetector();                                   // mode 'arm' is the default now
// keypoint callback — ADD, don't replace:
lights.feed(k);
if (turnOn){
  const r = wave.update(k, performance.now() / 1000);
  lights.comet.follow(r.front, r.chain);                          // rides the arm that is actually moving
  if (r.done){
    const hand = r.done.arm === 'left' ? 'lWrist' : 'rWrist';
    const end  = r.done.dir === 'out' ? hand : (r.done.arm === 'left' ? 'lShoulder' : 'rShoulder');
    lights.comet.end(); lights.burst(end, 'gold'); lights.word('YES!', end);
    // → the page's existing success path (the old judge still scores until the founder decides)
  }
}
// when Nova's demo wave plays — the cue on the child's matching arm, mirrored (Nova's right arm = the child's left on a mirror):
lights.waveCue(DEMO_ARM === 'right' ? ['lShoulder','lElbow','lWrist'] : ['rShoulder','rElbow','rWrist'], DEMO_MS);   // [ADAPT] DEMO_ARM, DEMO_MS from handywave.mp4; reverse the array if her wave goes wrist→shoulder
// when the child's turn starts / ends:
wave.reset(); lights.comet.start(); turnOn = true;
lights.comet.end(); turnOn = false;
```

## Tested behavior (node test/motion_detect_test.mjs → 35/35)
| one-arm case | result |
|---|---|
| right arm out · left arm in | 60/60 · 59/60 caught |
| slow 1.8s · fast 0.5s · 8 fps laptop · far child | 40/40 · 40/40 · 40/40 · 40/40 |
| wave without a shoulder pop (elbow→wrist) | 40/40 caught |
| arm raise (normal · slow · fast · 8fps · far child) · shoulder shrug | never a wave (60/60 each) |
