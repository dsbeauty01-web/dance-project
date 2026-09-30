/* test/move_judges_test.mjs — node test/move_judges_test.mjs */
import { judgePose, judgeShape, judgeShoulder, ChestSlide, HelloWave, judgePresence, PartMotion, body, KeypointSmoother } from '../shared/move-judges.js';
import { kid } from './kid.mjs';
let pass = 0, fail = 0; const out = [];
function check(name, n, fn, minPct = 95){ let ok = 0; for (let i = 0; i < n; i++) if (fn()) ok++; const good = ok / n * 100 >= minPct; good ? pass++ : fail++; out.push(`${good ? 'PASS' : 'FAIL'}  ${name.padEnd(64)} ${ok}/${n}`); }
const far = { sw: 0.08, jit: 0.003 };

// ── Nova Says poses
check('arms up → ok', 50, () => judgePose(kid({ lArm: 170, rArm: 168 }), 'armsUp').ok);
check('arms up, far child → ok', 50, () => judgePose(kid({ lArm: 170, rArm: 168, ...far }), 'armsUp').ok, 90);
check('arms out (T) is NOT arms up', 50, () => !judgePose(kid({ lArm: 90, rArm: 90 }), 'armsUp').ok);
check('only one arm up is NOT arms up', 50, () => !judgePose(kid({ lArm: 170, rArm: 10 }), 'armsUp').ok);
check('arms up progress grows as the arms rise (so the light fills)', 30, () => { const a = [20, 70, 120, 170].map(x => judgePose(kid({ lArm: x, rArm: x, jit: 0 }), 'armsUp').progress); return a[0] < a[1] && a[1] < a[2] && a[2] <= a[3]; });
check('arms in a V (135°) counts as arms up', 50, () => judgePose(kid({ lArm: 138, rArm: 135 }), 'armsUp').ok);
check('arms out → ok', 50, () => judgePose(kid({ lArm: 92, rArm: 88 }), 'armsOut').ok);
check('arms out, far child → ok', 50, () => judgePose(kid({ lArm: 92, rArm: 88, ...far }), 'armsOut').ok, 90);
check('arms up is NOT arms out', 50, () => !judgePose(kid({ lArm: 170, rArm: 170 }), 'armsOut').ok);
check('arms half out (40°) is NOT arms out', 50, () => !judgePose(kid({ lArm: 40, rArm: 40 }), 'armsOut').ok);
check('hands on head → ok', 50, () => judgePose(kid({ hands: 'head' }), 'handsHead').ok);
check('arms straight up is NOT hands on head', 50, () => !judgePose(kid({ lArm: 175, rArm: 175 }), 'handsHead').ok);
check('arms down is NOT hands on head', 50, () => !judgePose(kid({}), 'handsHead').ok);
check('left arm up (right down) → ok', 50, () => judgePose(kid({ lArm: 170, rArm: 10 }), 'leftUp').ok);
check('both arms up is NOT "left arm up" (and flags the right arm)', 50, () => { const r = judgePose(kid({ lArm: 170, rArm: 170 }), 'leftUp'); return !r.ok && r.wrong === 'r'; });
check('right arm up is NOT "left arm up"', 50, () => !judgePose(kid({ lArm: 10, rArm: 170 }), 'leftUp').ok);
check('right arm up (left down) → ok', 50, () => judgePose(kid({ lArm: 10, rArm: 170 }), 'rightUp').ok);

// ── Freeze animal shapes
check('star: arms up + feet apart → ok', 50, () => judgeShape(kid({ lArm: 150, rArm: 150, feet: 2.6 }), 'star').ok);
check('star: standing plain is NOT a star', 50, () => !judgeShape(kid({}), 'star').ok);
check('flamingo: one knee up → ok', 50, () => judgeShape(kid({ lKnee: 80 }), 'flamingo').ok);
check('flamingo: two feet down is NOT a flamingo', 50, () => !judgeShape(kid({}), 'flamingo').ok);
check('frog: squat → ok', 50, () => judgeShape(kid({ squat: 1 }), 'frog').ok);
check('frog: standing is NOT a frog', 50, () => !judgeShape(kid({}), 'frog').ok);
check('bear: big arms out → ok', 50, () => judgeShape(kid({ lArm: 95, rArm: 95 }), 'bear').ok);

// ── Shoulder lift (intro, Upper Body)
function smoothed(opts, frames = 8){ const S = new KeypointSmoother(); let k, t = 0; for (let f = 0; f < frames; f++){ t += 1 / 15; k = S.update(kid(opts), t); } return k; }
check('left shoulder lifted → ok', 50, () => judgeShoulder(smoothed({ lift: { l: 0.2, r: 0 } }), 'l').ok);
check('left shoulder lifted, far child → ok', 50, () => judgeShoulder(smoothed({ lift: { l: 0.2, r: 0 }, ...far }), 'l').ok, 90);
check('tiny tilt (0.05) is NOT a lift', 50, () => !judgeShoulder(smoothed({ lift: { l: 0.05, r: 0 } }), 'l').ok);
check('tiny tilt, far child, is NOT a lift', 50, () => !judgeShoulder(smoothed({ lift: { l: 0.05, r: 0 }, ...far }), 'l').ok);
check('the OTHER shoulder lifted does NOT count', 50, () => !judgeShoulder(kid({ lift: { l: 0, r: 0.25 } }), 'l').ok);

// ── Chest slide (Upper Body)
function slideRun(fn, frames = 30){ const C = new ChestSlide(); let r = null, t = 0; for (let f = 0; f < frames; f++){ t += 1 / 15; r = C.update(kid(fn(f)), t); } return r; }
check('chest slides right over still hips → ok', 40, () => { const r = slideRun(f => ({ slide: f < 10 ? 0 : 0.34 })); return r.ok && r.slide > 0; });
check('chest slides left → ok (other direction)', 40, () => { const r = slideRun(f => ({ slide: f < 10 ? 0 : -0.34 })); return r.ok && r.slide < 0; });
check('whole body steps sideways is NOT a chest slide', 40, () => !slideRun(f => ({ cx: f < 10 ? 0.5 : 0.56 })).ok);
check('hips swaying while the chest slides → hips flagged not still', 40, () => { const r = slideRun(f => ({ slide: f < 10 ? 0 : 0.34, cx: f < 10 ? 0.5 : 0.47 })); return !r.hipsStill; });

// ── Hello wave (greeting)
function helloRun(fn, secs = 1.8){ const H = new HelloWave(); let r = null, t = 0; for (let f = 0; f < secs * 15; f++){ t += 1 / 15; r = H.update(kid(fn(t)), t); } return r; }
check('hand up, swinging side to side → hello', 40, () => helloRun(t => ({ rArm: 150 + 25 * Math.sin(t * 2 * Math.PI * 1.4), rBend: 10 })).ok);
check('hand up but still is NOT hello', 40, () => !helloRun(() => ({ rArm: 160 })).ok);
check('hand down swinging is NOT hello', 40, () => !helloRun(t => ({ rArm: 20 + 20 * Math.sin(t * 9) })).ok);

// ── Presence
check('too close → "tooClose"', 20, () => judgePresence(kid({ sw: 0.4 })).state === 'tooClose');
check('too far → "tooFar"', 20, () => judgePresence(kid({ sw: 0.07 })).state === 'tooFar');
check('standing off to the side → off-side', 20, () => judgePresence(kid({ cx: 0.2 })).state.startsWith('off'));
check('good spot → "ok"', 20, () => judgePresence(kid({})).state === 'ok');

// ── Which part broke a freeze
function partRun(move){ const P = new PartMotion(); let r = null, t = 0; for (let f = 0; f < 20; f++){ t += 1 / 15; r = P.update(kid(move(f)), t); } return r; }
check('left arm wobbling during a freeze → "lArm" is the moving part', 40, () => partRun(f => ({ lArm: 30 + 25 * Math.sin(f) })).top === 'lArm');
check('right knee moving → "rLeg" is the moving part', 40, () => partRun(f => ({ rKnee: 30 + 30 * Math.abs(Math.sin(f)) })).top === 'rLeg');

console.log(out.join('\n')); console.log(`\n${pass} pass · ${fail} fail`); process.exit(fail ? 1 : 0);
