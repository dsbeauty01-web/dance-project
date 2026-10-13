/* the simulated child for FOLLOW MODE v4 (single clock = her clip time): reacts to target_open events */
export { } from '../../shared/handwave-core.js';
let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const g = s => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * s; };
export const key = j => j[0] + (j.endsWith('Wrist') ? 'W' : j.endsWith('Elbow') ? 'E' : 'S');
export const AMT = { Wrist: 0.32, Elbow: 0.24, Shoulder: 0.13 };
export const kindOf = j => j.replace(/^[lr]/, '');
export const swap = j => (j[0] === 'l' ? 'r' : 'l') + j.slice(1);
export function child(pose, { sw = 160, cx = 640, sy = 300, jit = 1.2, vis = 0.9, wristVis = 0.9 } = {}){
  const k = {}, s = sw; const P = (n, x, y, v = vis) => { k[n] = { x: x + g(jit), y: y + g(jit), vis: v }; };
  const up = n => (pose[key(n)] || 0) * s;
  P('lShoulder', cx + s / 2, sy - up('lShoulder')); P('rShoulder', cx - s / 2, sy - up('rShoulder')); P('nose', cx, sy - 0.6 * s);
  P('lElbow', cx + 0.8 * s, sy + 0.5 * s - up('lElbow')); P('rElbow', cx - 0.8 * s, sy + 0.5 * s - up('rElbow'));
  P('lWrist', cx + 1.0 * s, sy + (pose.armsDown ? 1.4 : 1.1) * s - up('lWrist'), wristVis); P('rWrist', cx - 1.0 * s, sy + (pose.armsDown ? 1.4 : 1.1) * s - up('rWrist'), wristVis);
  return k;
}
/* FollowKid: `react` s after a target opens, lifts that joint with a 0.55 s bump.
   modes: react · still · wrongJoint · frozen [a,b] (no moves while t in that span) · armsUp (holds all arms high always) */
export class FollowKid {
  constructor(o = {}){ this.o = o; this.target = null; this.opened = 0; }
  onEvents(evs, t){ for (const e of evs){ if (e.type === 'target_open'){ this.target = e.target.joint; this.opened = t; this.targetHerT = e.target.t; } if (e.type === 'hit' || e.type === 'miss') this.target = null; } }
  pose(t){
    if (this.o.armsUp) return { lW: 1.6, rW: 1.6, lE: 1.0, rE: 1.0 };
    const p = {};
    if (this.o.still || !this.target) return p;
    if (this.o.frozen && t >= this.o.frozen[0] && t <= this.o.frozen[1]) return p;
    const j = this.o.wrongJoint ? swap(this.target) : this.target;
    const herPace = this.o.herPace ? Math.max(0, (this.targetHerT ?? 0) - this.opened) : 0;
    let dt = t - this.opened - herPace - (this.o.react ?? 0.35);
    if (dt > 0.55) dt = dt % 1.2;                     // a real kid RETRIES: if the first try passed, he lifts again
    if (dt > 0 && dt < 0.55) p[key(j)] = AMT[kindOf(j)] * Math.sin(Math.min(1, dt / 0.5) * Math.PI);
    return p;
  }
}
