// shared/light-engine.js — the shared LIGHT engine (ENGINE-LIGHTS · LOOK pass b0.16).
// One canvas engine for every game, driven by the mover-engine + the cue table.
// GOLD is the only thing that glows. cue = WHEN (orb one beat early + pulse) · WINDOW (ring
// closes to the orb) · WHERE (ribbon=direction / comet=path). hit = flare + fly-up + tick.
// Isolation = mover gold + a faint "stay still" ring on the reference. Never red.
//
// LOOK (novapack4 LIGHTS-LOOK): every size is scaled to the live body (shoulder-width sw),
// every gold element is bloomed (3 additive layers) and never thin, labels ride ABOVE the head
// (the face is an exclusion zone), the freeze is a frosty glow hugging the torso, and the clap
// bursts between the hands with radial spokes. Adult tier = amber, fewer particles, still bloomed.
//
// TIMING: every fade/rise/grow is WALL-CLOCK (born + life in ms, movement scaled by frame dt) so
// the look is identical at 10fps (headless capture) and 60fps (a kid's device). Label sizes are
// FROZEN at birth (they never re-scale when the camera shot changes).

function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`; }

export class LightEngine {
  constructor(canvas, opts = {}) {
    this.cv = canvas; this.cx = canvas.getContext('2d'); this.mirror = opts.mirror ?? true;
    this.tier = opts.tier ?? 'kids';                                  // 'kids' full juice · 'adult' cool
    this.col = this.tier === 'kids'
      ? { main: '#ffc23e', hot: '#ffe27e', ice: '#bfeeff', warm: '#ffb27d' }
      : { main: '#e6a93a', hot: '#f2c66d', ice: '#bfeeff', warm: '#e0a57a' };
    this.pf = this.tier === 'kids' ? 1 : 0.4;                          // particle factor (adult ×0.4)
    this.joints = {}; this.cues = []; this.parts = []; this.rings = []; this.comets = []; this.fire = false;
    this.claps = []; this.freezes = [];
    this.streak = 0; this._last = performance.now();
    this.fit(); addEventListener('resize', () => this.fit()); this.audio = new LightAudio();
    requestAnimationFrame(() => this.draw());
  }
  fit() { this.cv.width = this.cv.clientWidth * devicePixelRatio; this.cv.height = this.cv.clientHeight * devicePixelRatio; }
  // ── joint feed: call every pose frame with mover-engine output (normalized 0..1 coords) ──
  setJoints(out) {
    for (const [n, j] of Object.entries(out)) {
      if (!j) continue;
      this.joints[n] = { x: (this.mirror ? 1 - j.x : j.x) * this.cv.width, y: j.y * this.cv.height, dir: j.dir };
    }
  }
  P(n) { return this.joints[n]; }
  // live shoulder width in canvas px — the unit every size is scaled to
  sw() {
    const a = this.P('lShoulder'), b = this.P('rShoulder');
    if (a && b) { const d = Math.hypot(a.x - b.x, a.y - b.y); if (d > 20) return d; }
    return this.cv.width * 0.16;
  }
  // a bloomed gold blob: 3 additive layers (wide soft → mid → hot core)
  bloom(x, y, r, col = this.col.main, coreA = 1) {
    const cx = this.cx; cx.save(); cx.globalCompositeOperation = 'lighter';
    for (const [m, a] of [[4, .20], [2, .38], [1, .95 * coreA]]) {
      const rr = Math.max(1, r * m), g = cx.createRadialGradient(x, y, 0, x, y, rr);
      g.addColorStop(0, hexA(col, 1)); g.addColorStop(1, hexA(col, 0));
      cx.globalAlpha = a; cx.fillStyle = g; cx.beginPath(); cx.arc(x, y, rr, 0, 7); cx.fill();
    }
    cx.restore();
  }
  _dust(x, y, { vx = 0, vy = 0, r = 4, col = this.col.main, life = 500, grav = false, spark = false, frost = false }) {
    this.parts.push({ x, y, vx, vy, r, col, born: performance.now(), life, grav, spark, frost });
  }
  _ring(x, y, { r0 = 8, rate = 300, life = 450, col = this.col.main, soft = false }) {
    this.rings.push({ x, y, r0, rate, life, col, soft, born: performance.now() });   // rate = px/sec growth
  }
  // ── CUES (from the cue table, one beat early) ──
  cue({ joint, dir = null, windowMs = 900, leadMs = 1000, still = [] }) {
    this.cues = this.cues.filter(c => c.joint !== joint);
    this.cues.push({ joint, dir, born: performance.now(), windowMs, leadMs, still });
    this.audio.chime();
  }
  clearCue(joint) { this.cues = this.cues.filter(c => c.joint !== joint); }
  // ── EVENTS (from detection) ──
  hit(joint, quality = 'good', pts = null, gradeWord = null) {
    const p = this.P(joint); if (!p) return;
    const col = quality === 'iso' ? this.col.hot : quality === 'wrong' ? '#cbb7e8' : this.col.main;
    const sw = this.sw(), n = Math.round((this.tier === 'kids' ? 16 : 7) * 1);
    for (let i = 0; i < n; i++) this._dust(p.x, p.y, { vx: (Math.random() - .5) * sw * .06, vy: (Math.random() - .8) * sw * .06, r: sw * .03 * (1 + Math.random()), col, life: 500, grav: true });
    this._ring(p.x, p.y, { r0: sw * .1, rate: sw * 1.9, life: 450, col }); this.clearCue(joint); this.audio.tick(this.streak || 0);
    // the grade word floats ABOVE THE HEAD (PERFECT/GOOD/OK); the points tuck under the joint
    if (gradeWord) { this.flyUp(p, gradeWord); if (pts != null) this._smallText(p.x, p.y + sw * .3, `+${pts}`, sw); }
    else if (pts != null) this.flyUp(p, `+${pts}`);
  }
  _smallText(x, y, text, sw) { this.parts.push({ x, y, vx: 0, vy: -sw * .012, born: performance.now(), life: 850, text, col: this.col.main, size: Math.max(16, sw * .13) }); }
  isoShimmer() {
    const sw = this.sw();
    for (const n of ['lHip', 'rHip']) {
      const p = this.P(n); if (!p) continue;
      for (let i = 0; i < Math.round(10 * this.pf); i++) this._dust(p.x, p.y, { vx: (Math.random() - .5) * sw * .03, vy: -Math.random() * sw * .025, r: sw * .02, col: this.col.hot, life: 450, spark: true });
    }
  }
  warm(joint = 'hipC') { const p = this.P(joint), sw = this.sw(); if (p) this._ring(p.x, p.y, { r0: sw * .3, rate: sw * .5, life: 1600, col: this.col.warm, soft: true }); }
  ice() { const c = this.P('shoulderC'), sw = this.sw(); if (c) this._ring(c.x, c.y, { r0: sw * .5, rate: sw * 3.6, life: 1000, col: this.col.ice, soft: true }); }
  // ── CLAP: two hands come together. Bloomed orbs on both wrists + a glowing dotted bridge
  //    pulsing toward the midpoint; on contact the burst is BETWEEN the hands (+8 radial spokes). ──
  clapCue({ left = 'lWrist', right = 'rWrist', windowMs = 900, leadMs = 900 } = {}) {
    this.claps = [{ left, right, born: performance.now(), windowMs, leadMs }]; this.audio.chime();
  }
  clapHit(quality = 'good', pts = null) {
    const c = this.claps[0]; const a = c && this.P(c.left), b = c && this.P(c.right);
    const mid = (a && b) ? { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 } : (a || b || this.P('shoulderC'));
    if (!mid) return; const sw = this.sw();
    for (let i = 0; i < Math.round(24 * this.pf); i++) this._dust(mid.x, mid.y, { vx: (Math.random() - .5) * sw * .11, vy: (Math.random() - .55) * sw * .11, r: sw * .035 * (1 + Math.random()), col: this.col.hot, life: 550, grav: true });
    for (let i = 0; i < 8; i++) { const ang = i * Math.PI / 4; this._dust(mid.x, mid.y, { vx: Math.cos(ang) * sw * .13, vy: Math.sin(ang) * sw * .13, r: sw * .05, col: this.col.hot, life: 380, spark: true }); }
    this._ring(mid.x, mid.y, { r0: sw * .08, rate: sw * 3.8, life: 500, col: this.col.hot });   // a ring expands from the contact
    this._ring(mid.x, mid.y, { r0: sw * .08, rate: sw * 1.9, life: 560, col: this.col.main });
    this.flyUp(mid, quality === 'perfect' ? 'PERFECT!' : 'CLAP!');
    if (pts != null) this._smallText(mid.x, mid.y + sw * .3, `+${pts}`, sw);
    this.claps = []; this.audio.clap();                               // real clap transient, not a sine blip
  }
  // ── FREEZE: a frosty glow hugging the torso + an ice ring that CLOSES over the hold = the countdown ──
  bodyBounds() {
    const ns = ['head', 'nose', 'shoulderC', 'hipC', 'lShoulder', 'rShoulder', 'lHip', 'rHip', 'lWrist', 'rWrist', 'lKnee', 'rKnee'];
    let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9, any = false;
    for (const n of ns) { const p = this.P(n); if (!p) continue; any = true; minX = Math.min(minX, p.x); minY = Math.min(minY, p.y); maxX = Math.max(maxX, p.x); maxY = Math.max(maxY, p.y); }
    if (!any) return null;
    const pad = (this.cv.width + this.cv.height) * 0.03;
    return { x: (minX + maxX) / 2, y: (minY + maxY) / 2, r: Math.max(maxX - minX, maxY - minY) / 2 + pad };
  }
  // an ellipse shoulders→hips, widened to hug the torso (falls back to bodyBounds)
  freezeShape() {
    const s = this.P('shoulderC'), h = this.P('hipC'), sw = this.sw();
    if (s && h) { const torso = Math.hypot(s.x - h.x, s.y - h.y); return { x: (s.x + h.x) / 2, y: (s.y + h.y) / 2, rx: sw * .78, ry: torso * .62 + sw * .55 }; }
    const b = this.bodyBounds(); return b ? { x: b.x, y: b.y, rx: b.r * .7, ry: b.r } : null;
  }
  freezeCue(durationMs = 3000) { this.freezes = [{ born: performance.now(), durationMs, state: 'holding' }]; this.audio.chime(); }
  freezeHeld() { const f = this.freezes[0]; if (f) f.state = 'held'; const b = this.freezeShape(); if (b) this.flyUp({ x: b.x, y: b.y }, 'FROZEN!'); this.audio.ding(); }
  freezeBroke() { const b = this.freezeShape(), sw = this.sw(); if (b) this._ring(b.x, b.y, { r0: b.rx, rate: sw * 2.6, life: 1000, col: this.col.warm, soft: true }); this.freezes = []; }
  clearFreeze() { this.freezes = []; }
  setFire(on) { this.fire = on && this.tier === 'kids'; }
  comet(chain, quality = 'good') {                                    // the WAVE light: a bloomed head + fading tail riding the chain
    const pts = chain.map(n => this.P(n)).filter(Boolean); if (pts.length < 3) return;
    this.comets.push({ pts, t0: performance.now(), dur: quality === 'smooth' ? 650 : quality === 'good' ? 800 : 1000, col: quality === 'smooth' ? this.col.hot : this.col.main });
  }
  flyUp(p, text) {                                                    // labels ride above the head, out of the face; size FROZEN at birth
    const h = this.P('head') || this.P('nose'), sw = this.sw();
    const size = Math.min(Math.max(sw * 0.30, 34), this.cv.width * 0.11);   // capped so words never fill the screen
    const x = h ? h.x : p.x, y = (h ? h.y : p.y) - size * 1.5;
    this.parts.push({ x, y, vx: 0, vy: -size * .04, born: performance.now(), life: 900, text, big: true, size, col: this.col.hot });
  }
  // ── DRAW ──
  draw() {
    const cx = this.cx, now = performance.now(), sw = this.sw();
    const df = Math.max(0.3, Math.min(3, (now - this._last) / 16.67)); this._last = now;   // frame-time scale (headless RAF is slow)
    cx.clearRect(0, 0, this.cv.width, this.cv.height);
    const lw = k => Math.max(2, k * (sw / 200));
    this.cues = this.cues.filter(c => (now - c.born) < c.leadMs + c.windowMs + 400);       // window closes with no hit → soft fade, then gone (no punishment)
    for (const c of this.cues) {
      const p = this.P(c.joint); if (!p) continue;
      const age = (now - c.born), total = c.leadMs + c.windowMs, over = age - total;
      const fade = over > 0 ? Math.max(0, 1 - over / 400) : 1;                              // gentle dim-out past the window
      cx.globalAlpha = fade;
      const orbR = sw * .30 * (this.fire ? 1.15 : 1) * (1 + .06 * Math.sin(age / 160));
      const ringMax = orbR * 2.0;
      this.bloom(p.x, p.y, orbR, this.fire ? this.col.hot : this.col.main);                 // the WHEN orb, bloomed
      for (let i = 0; i < 7; i++) { const ang = now / 520 + i * (6.283 / 7), rr = orbR * 1.5; this.bloom(p.x + Math.cos(ang) * rr, p.y + Math.sin(ang) * rr, orbR * .12, this.col.hot, .8); }
      const frac = Math.max(0, 1 - age / total);                                            // ring closes across lead+window
      // the PERFECT zone: a filled translucent gold BAND (inner third)
      cx.save(); cx.strokeStyle = hexA(this.col.hot, .16 * fade); cx.lineWidth = orbR * .7; cx.beginPath(); cx.arc(p.x, p.y, orbR + orbR * .35, 0, 7); cx.stroke(); cx.restore();
      // the closing ring: feathered, brightens as it enters the PERFECT zone
      const inPerfect = frac < 0.34;
      cx.save(); cx.shadowColor = hexA(this.col.hot, 1); cx.shadowBlur = 22; cx.globalAlpha = fade;
      cx.strokeStyle = inPerfect ? hexA(this.col.hot, 1) : hexA(this.col.main, .95); cx.lineWidth = inPerfect ? lw(9) : lw(6);
      cx.beginPath(); cx.arc(p.x, p.y, orbR + (ringMax - orbR) * frac, 0, 7); cx.stroke(); cx.restore();
      // WHERE ribbon (direction), bloomed line
      cx.save(); cx.shadowColor = hexA(this.col.main, 1); cx.shadowBlur = 16; cx.strokeStyle = hexA(this.col.main, .85); cx.lineWidth = lw(8); cx.lineCap = 'round';
      if (c.dir === 'L' || c.dir === 'R') { const s = (c.dir === 'R') ^ this.mirror ? -1 : 1; cx.beginPath(); cx.moveTo(p.x, p.y); cx.quadraticCurveTo(p.x + s * sw * .5, p.y - sw * .1, p.x + s * sw * .9, p.y - sw * .02); cx.stroke(); }
      if (c.dir === 'UP' || c.dir === 'DOWN') { const s = c.dir === 'UP' ? -1 : 1; cx.beginPath(); cx.moveTo(p.x, p.y); cx.quadraticCurveTo(p.x + sw * .08, p.y + s * sw * .5, p.x + sw * .02, p.y + s * sw * .9); cx.stroke(); }
      cx.restore();
      for (const sn of c.still) {                                                            // the ISOLATION pair: faint "stay still" ring
        const q = this.P(sn); if (!q) continue;
        cx.save(); cx.globalAlpha = fade * .5; cx.strokeStyle = 'rgba(255,255,255,.6)'; cx.setLineDash([sw * .06, sw * .06]); cx.lineWidth = lw(3); cx.beginPath(); cx.arc(q.x, q.y, sw * .28, 0, 7); cx.stroke(); cx.restore();
      }
      cx.globalAlpha = 1;
    }
    // ── CLAP cue: bloomed orbs on both wrists + a glowing dotted bridge pulsing to the midpoint ──
    for (const c of this.claps) {
      const a = this.P(c.left), b = this.P(c.right); if (!a || !b) continue;
      const age = now - c.born, total = c.leadMs + c.windowMs, frac = Math.max(0, 1 - age / total);
      const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, span = Math.hypot(b.x - a.x, b.y - a.y) / 2;
      this.bloom(a.x, a.y, sw * .26, this.col.main); this.bloom(b.x, b.y, sw * .26, this.col.main);
      cx.save(); cx.shadowColor = hexA(this.col.hot, 1); cx.shadowBlur = 16; cx.strokeStyle = hexA(this.col.hot, .85);
      cx.setLineDash([sw * .04, sw * .08]); cx.lineDashOffset = -(now / 12) % (sw * .12); cx.lineWidth = lw(5);
      cx.beginPath(); cx.moveTo(a.x, a.y); cx.lineTo(b.x, b.y); cx.stroke(); cx.setLineDash([]); cx.restore();
      cx.save(); cx.strokeStyle = hexA(this.col.hot, .16); cx.lineWidth = sw * .18; cx.beginPath(); cx.arc(mid.x, mid.y, sw * .16, 0, 7); cx.stroke(); cx.restore();   // PERFECT contact band
      const inPerfect = frac < 0.34;
      cx.save(); cx.shadowColor = hexA(this.col.hot, 1); cx.shadowBlur = 20; cx.strokeStyle = inPerfect ? hexA(this.col.hot, 1) : hexA(this.col.main, .95); cx.lineWidth = inPerfect ? lw(9) : lw(6);
      cx.beginPath(); cx.arc(mid.x, mid.y, sw * .12 + span * frac, 0, 7); cx.stroke(); cx.restore();
    }
    // ── FREEZE: frosty glow ellipse + drifting frost + a thick feathered ice ring closing in ──
    for (const f of this.freezes) {
      const sh = this.freezeShape(); if (!sh) continue; const age = now - f.born, held = f.state === 'held';
      cx.save(); cx.globalCompositeOperation = 'lighter'; cx.translate(sh.x, sh.y); cx.scale(sh.rx, sh.ry);
      const g = cx.createRadialGradient(0, 0, 0, 0, 0, 1); g.addColorStop(0, hexA(this.col.ice, .0)); g.addColorStop(.62, hexA(this.col.ice, held ? .22 : .12)); g.addColorStop(1, hexA(this.col.ice, 0));
      cx.fillStyle = g; cx.beginPath(); cx.arc(0, 0, 1, 0, 7); cx.fill(); cx.restore();
      if (Math.random() < .6) this._dust(sh.x + (Math.random() - .5) * sh.rx * 1.6, sh.y - sh.ry + Math.random() * sh.ry * 2, { vx: (Math.random() - .5) * sw * .006, vy: sw * .008 + Math.random() * sw * .008, r: sw * .012 * (1 + Math.random()), col: this.col.ice, life: 1400, frost: true });
      const frac = held ? 0 : Math.max(0, 1 - age / f.durationMs), scale = held ? 1 : (1 + .6 * frac);
      cx.save(); cx.shadowColor = hexA(this.col.ice, 1); cx.shadowBlur = 24; cx.strokeStyle = hexA(this.col.ice, held ? 1 : .9); cx.lineWidth = held ? lw(8) : lw(6);
      cx.setLineDash(held ? [] : [sw * .07, sw * .05]); cx.beginPath(); cx.ellipse(sh.x, sh.y, sh.rx * scale, sh.ry * scale, 0, 0, 7); cx.stroke(); cx.setLineDash([]); cx.restore();
      if (held) { const fl = .45 + .55 * Math.abs(Math.sin(age / 90)); cx.save(); cx.globalAlpha = fl; cx.strokeStyle = '#ffffff'; cx.shadowColor = '#fff'; cx.shadowBlur = 18; cx.lineWidth = lw(3); cx.beginPath(); cx.ellipse(sh.x, sh.y, sh.rx, sh.ry, 0, 0, 7); cx.stroke(); cx.restore(); }
      if (frac <= 0 && !held) f.state = 'held';
    }
    // ── COMET: bloomed head + fading tail + shed sparks along the chain ──
    for (const m of this.comets) {
      const u = Math.min(1, (now - m.t0) / m.dur), head = pathPoint(m.pts, u);
      for (let k = 0; k < 18; k++) { const uu = Math.max(0, u - k * 0.028), q = pathPoint(m.pts, uu); cx.save(); cx.globalCompositeOperation = 'lighter'; cx.globalAlpha = (1 - k / 18) * .85; cx.fillStyle = m.col; cx.beginPath(); cx.arc(q.x, q.y, sw * .25 * (1 - k / 24), 0, 7); cx.fill(); cx.restore(); }
      this.bloom(head.x, head.y, sw * .25, m.col);
      if (Math.random() < .5) this._dust(head.x, head.y, { vx: (Math.random() - .5) * sw * .03, vy: (Math.random() - .5) * sw * .03, r: sw * .02, col: this.col.hot, life: 350, spark: true });
      if (u >= 1) m.done = true;
    }
    this.comets = this.comets.filter(m => !m.done);
    // ── particles (sparks / frost / hit dust / text) — wall-clock life, dt-scaled motion ──
    for (const q of this.parts) {
      q.x += q.vx * df; q.y += q.vy * df; if (q.grav) q.vy += sw * .04 * df;
      const a = 1 - (now - q.born) / q.life; cx.globalAlpha = Math.max(a, 0);
      if (q.text) {
        cx.textAlign = 'center'; cx.font = `800 ${q.size}px "Baloo 2",system-ui`;
        if (q.big) { cx.save(); cx.shadowColor = hexA(this.col.hot, 1); cx.shadowBlur = 24; cx.lineWidth = Math.max(3, q.size * .06); cx.strokeStyle = 'rgba(28,18,48,.9)'; cx.strokeText(q.text, q.x, q.y); cx.fillStyle = hexA(this.col.hot, 1); cx.fillText(q.text, q.x, q.y); cx.restore(); }
        else { cx.fillStyle = q.col; cx.fillText(q.text, q.x, q.y); }
        cx.textAlign = 'start';
      } else { cx.save(); cx.globalCompositeOperation = 'lighter'; cx.fillStyle = q.col; cx.beginPath(); cx.arc(q.x, q.y, Math.max(.5, q.r), 0, 7); cx.fill(); cx.restore(); }
    }
    this.parts = this.parts.filter(q => (now - q.born) < q.life); cx.globalAlpha = 1;
    // ── rings (feathered) — wall-clock life + growth ──
    for (const r of this.rings) {
      const el = (now - r.born) / 1000, rad = r.r0 + r.rate * el, a = 1 - (now - r.born) / r.life;
      cx.save(); cx.globalAlpha = Math.max(a, 0); cx.strokeStyle = r.col; cx.shadowColor = r.col; cx.shadowBlur = r.soft ? 16 : 22; cx.lineWidth = r.soft ? lw(8) : lw(5); cx.beginPath(); cx.arc(r.x, r.y, rad, 0, 7); cx.stroke(); cx.restore();
    }
    this.rings = this.rings.filter(r => (now - r.born) < r.life); cx.globalAlpha = 1;
    requestAnimationFrame(() => this.draw());
  }
}
function pathPoint(pts, u) { const n = pts.length - 1, i = Math.min(n - 1, Math.floor(u * n)), f = u * n - i; const a = pts[i], b = pts[i + 1]; return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f }; }
class LightAudio {
  constructor() { this.ctx = null; }
  ensure() { this.ctx ||= new (window.AudioContext || window.webkitAudioContext)(); return this.ctx; }
  blip(freq, ms = 80, gain = .12) { const c = this.ensure(), o = c.createOscillator(), g = c.createGain(); o.frequency.value = freq; o.type = 'sine'; g.gain.value = gain; o.connect(g).connect(c.destination); o.start(); g.gain.exponentialRampToValueAtTime(.0001, c.currentTime + ms / 1000); o.stop(c.currentTime + ms / 1000); }
  tick(streak) { this.blip(Math.min(1100, 660 + streak * 40), 70); }  chime() { this.blip(880, 120, .05); }  ding() { this.blip(1320, 160, .14); }
  // a real clap = a short filtered NOISE transient, not a sine tone
  clap(gain = .5) {
    const c = this.ensure(), dur = 0.085, len = Math.floor(c.sampleRate * dur);
    const buf = c.createBuffer(1, len, c.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6);   // white noise with a fast decay envelope
    const src = c.createBufferSource(); src.buffer = buf;
    const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1900; bp.Q.value = 0.8;
    const g = c.createGain(); g.gain.value = gain;
    src.connect(bp).connect(g).connect(c.destination); src.start();
  }
}
