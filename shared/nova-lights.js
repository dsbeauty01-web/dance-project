/* shared/nova-lights.js — Nova's light layer for the camera overlay (#fx). One module, every game.
   What makes it look right (from the research): (1) One-Euro smoothing per joint, (2) its own 60fps loop that
   glides between detections and predicts slightly ahead, (3) additive glow sprites (light adds up), (4) time-based
   fading trails. Pure canvas 2D — no libraries.
   Usage:
     import { createLights } from '/shared/nova-lights.js';
     const L = createLights(document.getElementById('fx'), { video: $('usercam') });   // mirror defaults to the kit's (true)
     K.onKid = (out, k) => { L.feed(k); ... }                       // normalized keypoints from the kit
     L.speedGlow(true); L.waveCue(['rShoulder','rElbow','rWrist'], 1200); L.comet.start(); L.comet.follow(r.front, r.chain); L.burst('rWrist', 'gold'); ...
   Written by the architect. */

const NAMES = ['nose','lShoulder','rShoulder','lElbow','rElbow','lWrist','rWrist','lHip','rHip','lKnee','rKnee','lAnkle','rAnkle'];
export const CHAIN = ['lWrist','lElbow','lShoulder','rShoulder','rElbow','rWrist'];

class OneEuro { constructor(minC = 1.2, beta = 0.02, dC = 1){ this.minC = minC; this.beta = beta; this.dC = dC; this.x = null; this.dx = 0; this.t = null; }
  a(c, dt){ const tau = 1 / (2 * Math.PI * c); return 1 / (1 + tau / dt); }
  f(v, t){ if (this.x === null){ this.x = v; this.t = t; return v; } const dt = Math.max(1e-3, t - this.t); this.t = t;
    const dv = (v - this.x) / dt; this.dx += this.a(this.dC, dt) * (dv - this.dx); const c = this.minC + this.beta * Math.abs(this.dx); this.x += this.a(c, dt) * (v - this.x); return this.x; } }
class Joint { constructor(){ this.fx = new OneEuro(); this.fy = new OneEuro(); this.prev = null; this.cur = null; this.conf = 0; }
  feed(x, y, vis, t){ if (vis < 0.3){ this.conf *= 0.8; return; } this.prev = this.cur; this.cur = { x: this.fx.f(x, t), y: this.fy.f(y, t), t }; this.conf = Math.min(1, this.conf + 0.25); }
  at(now){ if (!this.cur || this.conf < 0.2) return null; if (!this.prev) return { x: this.cur.x, y: this.cur.y, vx: 0, vy: 0, speed: 0 };
    const dt = (this.cur.t - this.prev.t) || 1 / 30, vx = (this.cur.x - this.prev.x) / dt, vy = (this.cur.y - this.prev.y) / dt, ahead = Math.min(now - this.cur.t + 0.03, 0.08);
    return { x: this.cur.x + vx * ahead, y: this.cur.y + vy * ahead, vx, vy, speed: Math.hypot(vx, vy) }; } }

function sprite(r, stops){ const c = document.createElement('canvas'); c.width = c.height = r * 2; const g = c.getContext('2d'), gr = g.createRadialGradient(r, r, 0, r, r, r);
  stops.forEach(([o, col]) => gr.addColorStop(o, col)); g.fillStyle = gr; g.fillRect(0, 0, r * 2, r * 2); return c; }

export function createLights(host, opts = {}){
  /* host = the page's camera overlay canvas (#fx). The kit's own LightEngine already draws on it, so we draw on
     OUR OWN canvas stacked exactly on top of it (same parent, same box) — the two never clear each other. */
  const o = Object.assign({ video: null, mirror: true, debug: false, fit: 'cover' }, opts);   // mirror:true = same as the kit (keypoints come un-mirrored)
  /* [KEPT over pack v3, 2026-09-30] fit MUST match the displayed video's object-fit or every light sits off the
     body. v3 reverted map() to cover-only; beta/wave.html's #usercam is object-fit:CONTAIN (a 16:9 camera in a
     tall panel letterboxes hard), so without this the whole light layer misses the child.
     'cover' (default, unchanged for every other page) · 'contain' · 'fill'. */
  let canvas = host;
  if (host?.parentNode && typeof document !== 'undefined' && document.createElement){
    canvas = document.createElement('canvas'); canvas.className = 'nova-lights';
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:' + ((parseInt(getComputedStyle?.(host)?.zIndex) || 6) + 1);
    host.parentNode.insertBefore(canvas, host.nextSibling);
  }
  const cx = canvas.getContext('2d');
  const SP = {
    gold:  sprite(64, [[0, 'rgba(255,250,220,1)'], [.3, 'rgba(255,205,80,.8)'], [1, 'rgba(255,150,40,0)']]),
    cyan:  sprite(64, [[0, 'rgba(255,255,255,1)'], [.3, 'rgba(120,230,255,.7)'], [1, 'rgba(90,120,255,0)']]),
    halo:  sprite(128, [[0, 'rgba(120,230,255,.5)'], [.4, 'rgba(110,140,255,.16)'], [1, 'rgba(110,80,255,0)']]),
    green: sprite(64, [[0, 'rgba(240,255,240,1)'], [.3, 'rgba(120,240,150,.75)'], [1, 'rgba(60,200,120,0)']]),
  };
  const J = {}; for (const n of NAMES) J[n] = new Joint();
  let W = 0, H = 0, DPR = 1;
  function resize(){ DPR = Math.min(2, devicePixelRatio || 1); W = canvas.clientWidth; H = canvas.clientHeight; canvas.width = W * DPR; canvas.height = H * DPR; cx.setTransform(DPR, 0, 0, DPR, 0, 0); }
  addEventListener('resize', resize); resize();
  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null; ro?.observe?.(canvas);   // panels resize between phases

  // normalized video coords → canvas pixels, matching the displayed video's object-fit   [KEPT over pack v3]
  function map(x, y){
    const vw = o.video?.videoWidth || 640, vh = o.video?.videoHeight || 480;
    let sx, sy;
    if (o.fit === 'fill'){ sx = W / vw; sy = H / vh; }
    else sx = sy = o.fit === 'contain' ? Math.min(W / vw, H / vh) : Math.max(W / vw, H / vh);
    const ox = (W - vw * sx) / 2, oy = (H - vh * sy) / 2; let X = ox + x * vw * sx; const Y = oy + y * vh * sy;
    if (o.mirror) X = W - X; return { x: X, y: Y, s: Math.sqrt(sx * sy) };
  }
  const now = () => performance.now() / 1000;
  function glow(img, x, y, sz, a = 1){ cx.globalAlpha = Math.max(0, Math.min(1, a)); cx.drawImage(img, x - sz / 2, y - sz / 2, sz, sz); cx.globalAlpha = 1; }
  function pos(name, t){ const j = J[name]?.at(t); if (!j) return null; const p = map(j.x, j.y); return { x: p.x, y: p.y, speed: j.speed * p.s * (o.video?.videoWidth || 640), vx: j.vx, vy: j.vy }; }
  function bodyScale(t){ const a = pos('lShoulder', t), b = pos('rShoulder', t); return a && b ? Math.max(40, Math.hypot(a.x - b.x, a.y - b.y)) : 120; }

  // ───── state of each effect ─────
  const S = { speed: false, cue: null, comet: { on: false, f: null, tail: [], seen: 0, chain: CHAIN }, parts: [], rings: [], words: [], beat: { on: false, next: null, period: 1, lead: 0.6 }, ripples: [] };

  function feed(k, t = now()){ for (const n of NAMES){ const p = k?.[n]; if (p) J[n].feed(p.x, p.y, p.vis ?? p.score ?? 1, t); } }

  function burst(where, kind = 'gold', n = 70, speed = 420){ const t = now(); const p = typeof where === 'string' ? pos(where, t) : where; if (!p) return;
    const img = kind === 'green' ? SP.green : kind === 'cyan' ? SP.cyan : SP.gold;
    for (let i = 0; i < n; i++){ const a = Math.random() * Math.PI * 2, s = speed * (0.35 + Math.random()); S.parts.push({ x: p.x, y: p.y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, t: 0, life: 0.5 + Math.random() * 0.45, img, sz: 10 + Math.random() * 16 }); }
    S.rings.push({ x: p.x, y: p.y, t: 0, kind }); }
  function word(text, where, color = '#ffd65a'){ const p = typeof where === 'string' ? pos(where, now()) : where; if (p) S.words.push({ text, x: p.x, y: p.y - 60, t: 0, color }); }

  // ───── the frame ─────
  let last = now();
  function frame(){
    const t = now(), dt = Math.min(0.05, t - last); last = t;
    cx.clearRect(0, 0, W, H);
    const sc = bodyScale(t);
    cx.globalCompositeOperation = 'lighter';

    // 1 · speed glow: every joint glows brighter the faster it moves (EyeToy)
    if (S.speed) for (const n of NAMES){ const p = pos(n, t); if (!p) continue; const e = Math.min(1, p.speed / (sc * 6)); if (e > 0.05) glow(SP.gold, p.x, p.y, sc * (0.35 + 1.1 * e), 0.15 + 0.8 * e); }

    // 2 · wave cue: dots light up along the child's own arm chain, in wave order
    if (S.cue){ const k = (t - S.cue.t0) / S.cue.dur, order = S.cue.chain || (S.cue.dir === 'R→L' ? [...CHAIN].reverse() : CHAIN);
      order.forEach((n, i) => { const p = pos(n, t); if (!p) return; const lit = k * (order.length + 1) - i; const a = lit > 0 ? Math.max(0.35, 1 - (lit - 1) * 0.5) : 0.25;
        glow(SP.halo, p.x, p.y, sc * (lit > 0 && lit < 1.2 ? 1.6 : 0.9), a * 0.8); glow(SP.cyan, p.x, p.y, sc * 0.45, a); });
      if (k >= 1.25) S.cue = null; }

    // 3 · comet: rides the arm chain at the detected wave front, smooth, tapered fading tail (Snap trails)
    if (S.comet.on && S.comet.f != null && t - S.comet.seen < 0.4){   // the front vanished > 0.4s ago → no head where the child isn't
      const C = S.comet.chain, f = Math.max(0, Math.min(C.length - 1, S.comet.f)), i = Math.floor(f), u = f - i;
      const a = pos(C[i], t), b = pos(C[Math.min(i + 1, C.length - 1)], t);
      if (a && b){ const h = { x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u, t };
        S.comet.tail.push(h); while (S.comet.tail.length && t - S.comet.tail[0].t > 0.35) S.comet.tail.shift();
        const T = S.comet.tail; cx.lineCap = 'round';
        for (const [wm, col, am] of [[3.2, '110,140,255', .18], [1.6, '120,230,255', .45], [.55, '255,255,255', .9]])
          for (let n = 1; n < T.length; n++){ const p = n / (T.length - 1); cx.strokeStyle = `rgba(${col},${am * p * p})`; cx.lineWidth = Math.max(0.5, sc * 0.12 * wm * Math.pow(p, 1.4)); cx.beginPath(); cx.moveTo(T[n - 1].x, T[n - 1].y); cx.lineTo(T[n].x, T[n].y); cx.stroke(); }
        glow(SP.halo, h.x, h.y, sc * 1.4, .9); glow(SP.cyan, h.x, h.y, sc * 0.55, 1); } }
    else S.comet.tail.length = 0;

    // 4 · beat ring on the chest: an approach ring that closes EXACTLY on the beat (rhythm-game style)
    if (S.beat.on){ const ls = pos('lShoulder', t), rs = pos('rShoulder', t), lh = pos('lHip', t), rh = pos('rHip', t);
      if (ls && rs){ const c = { x: (ls.x + rs.x + (lh?.x ?? ls.x) + (rh?.x ?? rs.x)) / 4, y: (ls.y + rs.y) / 2 * 0.6 + ((lh?.y ?? ls.y + sc) + (rh?.y ?? rs.y + sc)) / 2 * 0.4 };
        const nb = S.beat.next?.(t); if (nb != null){ const k = (nb - t) / S.beat.lead;              // 1 → 0 as the beat arrives
          const r0 = sc * 0.45, r = r0 * (1 + 1.6 * Math.max(0, Math.min(1, k)));
          cx.strokeStyle = `rgba(255,215,100,${0.25 + 0.7 * (1 - Math.max(0, Math.min(1, k)))})`; cx.lineWidth = Math.max(2, sc * 0.05); cx.beginPath(); cx.arc(c.x, c.y, r, 0, 7); cx.stroke();
          cx.strokeStyle = 'rgba(255,255,255,.35)'; cx.lineWidth = 2; cx.beginPath(); cx.arc(c.x, c.y, r0, 0, 7); cx.stroke(); }
        S.beat.center = c; } }

    // 5 · floor ripples under the feet
    S.ripples = S.ripples.filter(r => (r.t += dt) < 0.6);
    for (const r of S.ripples){ const k = r.t / 0.6; cx.strokeStyle = `rgba(${r.gold ? '255,215,100' : '120,230,255'},${1 - k})`; cx.lineWidth = 3; cx.beginPath(); cx.ellipse(r.x, r.y, sc * (0.4 + 1.8 * k), sc * (0.1 + 0.35 * k), 0, 0, 7); cx.stroke(); }

    // 6 · particles + shockwave rings
    S.parts = S.parts.filter(p => (p.t += dt) < p.life);
    for (const p of S.parts){ p.vx *= 0.92; p.vy = p.vy * 0.92 + 380 * dt; p.x += p.vx * dt; p.y += p.vy * dt; const a = Math.pow(1 - p.t / p.life, 0.7); glow(p.img, p.x, p.y, p.sz * (0.6 + 0.4 * a), a); }
    S.rings = S.rings.filter(r => (r.t += dt) < 0.4);
    for (const r of S.rings){ const k = r.t / 0.4; cx.strokeStyle = r.kind === 'cyan' ? `rgba(150,235,255,${1 - k})` : `rgba(255,220,120,${1 - k})`; cx.lineWidth = 6 * (1 - k) + 1; cx.beginPath(); cx.arc(r.x, r.y, 18 + sc * 1.6 * k, 0, 7); cx.stroke(); }
    cx.globalCompositeOperation = 'source-over';

    // 7 · words ("+100", "YES!")
    S.words = S.words.filter(w => (w.t += dt) < 0.9);
    for (const w of S.words){ const k = w.t / 0.9, sc2 = k < .15 ? .6 + k / .15 * .55 : 1.15 - .15 * Math.min(1, (k - .15) / .2);
      cx.save(); cx.translate(w.x, w.y - 40 * k); cx.scale(sc2, sc2); cx.globalAlpha = 1 - Math.max(0, (k - .6) / .4); cx.font = '900 44px system-ui'; cx.textAlign = 'center';
      cx.lineWidth = 7; cx.strokeStyle = 'rgba(40,15,0,.8)'; cx.strokeText(w.text, 0, 0); cx.fillStyle = w.color; cx.fillText(w.text, 0, 0); cx.restore(); }

    if (o.debug){ cx.fillStyle = 'rgba(255,255,255,.8)'; for (const n of NAMES){ const p = pos(n, t); if (p){ cx.beginPath(); cx.arc(p.x, p.y, 4, 0, 7); cx.fill(); } } }
    raf = requestAnimationFrame(frame);
  }
  let raf = requestAnimationFrame(frame);

  return {
    feed, burst, word,
    speedGlow(on){ S.speed = !!on; },
    /* waveCue(chain, durMs): dots light up along `chain` in order — e.g. ['rShoulder','rElbow','rWrist'] for a one-arm wave.
       (legacy: waveCue('L→R'|'R→L', durMs) = the whole-body chain) */
    waveCue(chainOrDir = 'L→R', durMs = 1200){ const chain = Array.isArray(chainOrDir) ? chainOrDir : null; S.cue = { dir: chain ? null : chainOrDir, chain, t0: now(), dur: durMs / 1000 }; },
    /* comet.start(chain) → comet.follow(front index along that chain) → comet.end(). The chain can change mid-wave (the detector reports which arm). */
    comet: { start(chain){ S.comet.on = true; S.comet.f = null; S.comet.tail.length = 0; if (chain) S.comet.chain = chain; },
             follow(f, chain){ if (chain && chain !== S.comet.chain && chain.join() !== S.comet.chain.join()){ S.comet.chain = chain; S.comet.f = null; S.comet.tail.length = 0; }
                               if (f != null){ S.comet.f = S.comet.f == null ? f : S.comet.f + (f - S.comet.f) * 0.35; S.comet.seen = now(); } },
             end(){ S.comet.on = false; } },
    /* beat: nextBeatAt(tPerfSec) → the next target beat time (performance seconds) or null; lead = seconds the ring takes to close */
    beatRing(on, nextBeatAt = null, lead = 0.6){ S.beat.on = !!on; S.beat.next = nextBeatAt; S.beat.lead = lead; },
    hit(grade){ const c = S.beat.center; const la = pos('lAnkle', now()), ra = pos('rAnkle', now()); const foot = la && ra ? { x: (la.x + ra.x) / 2, y: Math.max(la.y, ra.y) } : c ? { x: c.x, y: c.y + bodyScale(now()) * 2.2 } : null;
      if (grade === 'on'){ if (c) burst(c, 'gold', 60, 380); if (foot) S.ripples.push({ ...foot, t: 0, gold: true }); if (c) word('+100', c); }
      else if (grade === 'near'){ if (foot) S.ripples.push({ ...foot, t: 0, gold: false }); if (c) S.rings.push({ x: c.x, y: c.y, t: 0, kind: 'cyan' }); } },
    debug(on){ o.debug = !!on; },
    destroy(){ cancelAnimationFrame(raf); removeEventListener('resize', resize); ro?.disconnect(); cx.clearRect(0, 0, W, H); if (canvas !== host) canvas.remove?.(); },
  };
}
