/* test/clips/synth.mjs — edge cases a stranger's camera will throw at us, made from real tracked clips.
   node test/clips/synth.mjs  →  test/clips/edge/<base>.<variant>.json
     half-body      hips, knees, ankles cut off (conf 0)
     too-close      body scaled up about the shoulders until the shoulders are 60 % of the frame width; joints pushed
                    out of the picture get conf 0 (the camera can't see them)
     too-far        scaled down until the shoulders are 10 % of the frame width
     dark           every confidence × 0.5 (a dim room)
     jitter         ±3 px of random noise on every joint, every frame (a cheap webcam)
     one-arm-hidden the player's own LEFT elbow + wrist at conf 0.1 (behind the back / out of frame)
   Deterministic (seeded) so CI always tests the same clips. Base clips: the replay set in test/clips/. */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
export const BASES = ['frozen-body', 'still-sway', 'dance-hype', 'pose-armsup', 'pose-star', 'own-left-up', 'own-right-up'];
export const VARIANTS = ['half-body', 'too-close', 'too-far', 'dark', 'jitter', 'one-arm-hidden'];
const LOWER = ['lHip', 'rHip', 'lKnee', 'rKnee', 'lAnkle', 'rAnkle'];

function rng(seed){ let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

function scaleTo(rec, target){              // scale about the clip's median shoulder-mid so median shoulder width = target
  const ws = [], cx = [], cy = [];
  for (const f of rec.frames) if (f.lShoulder && f.rShoulder){ ws.push(Math.abs(f.lShoulder[0] - f.rShoulder[0])); cx.push((f.lShoulder[0] + f.rShoulder[0]) / 2); cy.push((f.lShoulder[1] + f.rShoulder[1]) / 2); }
  const med = a => [...a].sort((x, y) => x - y)[a.length >> 1];
  const k = target / med(ws), X = med(cx), Y = med(cy);
  return f => { const o = { t: f.t };
    for (const [n, p] of Object.entries(f)) if (n !== 't'){ const x = X + (p[0] - X) * k, y = Y + (p[1] - Y) * k;
      o[n] = [+x.toFixed(4), +y.toFixed(4), (x < 0 || x > 1 || y < 0 || y > 1) ? 0 : p[2]]; }
    return o; };
}

export function variant(rec, v){
  const r = rng(v.length * 977 + rec.frames.length);
  let map;
  if (v === 'half-body') map = f => { const o = { ...f }; for (const n of LOWER) if (o[n]) o[n] = [o[n][0], o[n][1], 0]; return o; };
  if (v === 'too-close') map = scaleTo(rec, 0.60);
  if (v === 'too-far') map = scaleTo(rec, 0.10);
  if (v === 'dark') map = f => { const o = { t: f.t }; for (const [n, p] of Object.entries(f)) if (n !== 't') o[n] = [p[0], p[1], +(p[2] * 0.5).toFixed(3)]; return o; };
  if (v === 'jitter') map = f => { const o = { t: f.t }; for (const [n, p] of Object.entries(f)) if (n !== 't')
      o[n] = [+(p[0] + (r() * 2 - 1) * 3 / rec.w).toFixed(4), +(p[1] + (r() * 2 - 1) * 3 / rec.h).toFixed(4), p[2]]; return o; };
  if (v === 'one-arm-hidden') map = f => { const o = { ...f }; for (const n of ['lElbow', 'lWrist']) if (o[n]) o[n] = [o[n][0], o[n][1], 0.1]; return o; };
  return { ...rec, edge: v, frames: rec.frames.map(map) };
}

if (import.meta.url === `file://${process.argv[1]}`){
  mkdirSync(join(ROOT, 'test/clips/edge'), { recursive: true });
  let n = 0;
  for (const b of BASES){
    const p = join(ROOT, `test/clips/${b}.json`); if (!existsSync(p)) continue;
    const rec = JSON.parse(readFileSync(p, 'utf8'));
    for (const v of VARIANTS){ writeFileSync(join(ROOT, `test/clips/edge/${b}.${v}.json`), JSON.stringify(variant(rec, v))); n++; }
  }
  console.log(`${n} edge clips → test/clips/edge/`);
}
