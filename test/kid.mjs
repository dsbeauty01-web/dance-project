/* test/kid.mjs — a simulated child's skeleton (normalized, un-mirrored, like the kit) */
let seed = 3; export const reseed = v => { seed = v; }; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const g = s => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * s; };
const rad = d => d * Math.PI / 180;

/* a child's skeleton. Angles: arm 0 = hanging down, 90 = straight out to the side, 180 = straight up. bend = extra elbow angle. */
export function kid({ cx = 0.5, sy = 0.36, sw = 0.16, lArm = 10, rArm = 10, lBend = 0, rBend = 0, lKnee = 0, rKnee = 0, squat = 0, feet = 0.7,
  slide = 0, lift = { l: 0, r: 0 }, jit = 0.003, hands = null } = {}){
  const U = 0.66 * sw, F = 0.69 * sw, torso = 1.5 * sw, T = 0.8 * torso, S2 = 0.8 * torso;
  const sh = { l: { x: cx + slide * sw + sw / 2, y: sy - lift.l * sw }, r: { x: cx + slide * sw - sw / 2, y: sy - lift.r * sw } };
  const hipY = sy + torso + squat * torso * 0.6;
  const k = { nose: { x: cx + slide * sw, y: sy - 0.55 * sw }, lShoulder: sh.l, rShoulder: sh.r,
    lHip: { x: cx + 0.35 * sw, y: hipY }, rHip: { x: cx - 0.35 * sw, y: hipY } };
  for (const [s, a, b, out] of [['l', lArm, lBend, 1], ['r', rArm, rBend, -1]]){
    const S = k[s + 'Shoulder'], e = { x: S.x + Math.sin(rad(a)) * U * out, y: S.y + Math.cos(rad(a)) * U }, w = { x: e.x + Math.sin(rad(a + b)) * F * out, y: e.y + Math.cos(rad(a + b)) * F };
    k[s + 'Elbow'] = e; k[s + 'Wrist'] = w; }
  if (hands === 'head'){ const top = { x: k.nose.x, y: k.nose.y - 0.45 * sw };
    k.lWrist = { x: top.x + 0.12 * sw, y: top.y }; k.rWrist = { x: top.x - 0.12 * sw, y: top.y }; k.lElbow = { x: cx + 0.95 * sw, y: sy - 0.35 * sw }; k.rElbow = { x: cx - 0.95 * sw, y: sy - 0.35 * sw }; }
  for (const [s, lk, out] of [['l', lKnee, 1], ['r', rKnee, -1]]){
    const H = k[s + 'Hip'], spread = squat * 0.5 * sw * out, kn = { x: H.x + spread + (feet - 0.7) * 0.5 * sw * out, y: H.y + T * Math.cos(rad(lk)) * (1 - squat * 0.5) };
    k[s + 'Knee'] = kn; k[s + 'Ankle'] = { x: kn.x + (feet - 0.7) * 0.4 * sw * out, y: kn.y + S2 * (lk > 30 ? 0.3 : 1) }; }
  for (const n of Object.keys(k)) k[n] = { x: k[n].x + g(jit), y: k[n].y + g(jit), vis: 0.9 };
  return k;
}
