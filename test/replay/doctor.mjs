/* test/replay/doctor.mjs — night item B: the Camera Doctor (beta/lib/doctor.js) on the clips it exists for.
   For each clip: what the Doctor says most of the time (its arrow), and whether it reaches "I can see you ✓". */
import { doctorState, createDoctor, ARROW } from '../../beta/lib/doctor.js';
import { frameAt } from '../../beta/lib/kp.js';
import { json, table } from './sim.mjs';

const CASES = [
  { clip: 'test/clips/edge/frozen-body.too-close.json', want: 'tooClose' },
  { clip: 'test/clips/edge/frozen-body.too-far.json',   want: 'tooFar' },
  { clip: 'test/clips/edge/frozen-body.half-body.json', want: 'halfBody' },
  { clip: 'test/clips/frozen-body.json',                want: 'ok', ready: true },
  { clip: 'test/clips/still-sway.json',                 want: 'ok', ready: true },
  { clip: 'test/clips/empty-room.json',                 want: 'cantSee' },
  { clip: 'test/clips/edge/frozen-body.dark.json',      want: 'cantSee' },
  // real videos (zoomed / shrunk / cropped / moved with ffmpeg, then tracked by MoveNet — not edited keypoints)
  { clip: 'test/clips/doc-too-close.json',              want: 'tooClose' },
  { clip: 'test/clips/doc-too-far.json',                want: 'tooFar' },
  { clip: 'test/clips/doc-half-body.json',              want: 'halfBody' },
  { clip: 'test/clips/doc-off-side.json',               want: 'moveLeft' },
];

export function doctorReplay(){
  const rows = []; let fail = 0;
  for (const c of CASES){
    const rec = json(c.clip), count = {}; const D = createDoctor(0); let ready = null, done = null;
    for (let t = 0; t < 6.5; t += 1 / rec.fps){ const s = doctorState(frameAt(rec, t)); count[s] = (count[s] || 0) + 1;
      const r = D.feed(s, t); if (r.ready && ready == null) ready = t; if (r.done && done == null) done = t; }
    const top = Object.entries(count).sort((a, b) => b[1] - a[1])[0][0];
    const ok = top === c.want && (c.ready ? ready != null : ready == null) && done != null && done <= 6.01;
    if (!ok) fail++;
    rows.push({ clip: c.clip.replace('test/clips/', ''), says: top, arrow: ARROW[top] ?? '(none — caption only)', '✓ reached': ready == null ? 'no' : `yes, at ${ready.toFixed(1)} s`,
      'moves on': done == null ? 'NEVER' : `${done.toFixed(1)} s`, want: c.want + (c.ready ? ' + ✓' : ''), verdict: ok ? 'PASS' : 'FAIL' });
  }
  return { name: 'Doctor', fail, rows, text: table('CAMERA DOCTOR — what it tells the player, per clip', ['clip', 'says', 'arrow', '✓ reached', 'moves on', 'want', 'verdict'], rows) };
}
if (import.meta.url === `file://${process.argv[1]}`){ const r = doctorReplay(); console.log(r.text); process.exit(r.fail ? 1 : 0); }
