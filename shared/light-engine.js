// shared/light-engine.js — the shared LIGHT engine (ENGINE-LIGHTS b0.12).
// One canvas engine for every game, driven by the mover-engine + the cue table.
// GOLD is the only thing that glows. cue = WHEN (orb one beat early + pulse) · WINDOW (ring
// closes to the orb) · WHERE (ribbon=direction / comet=path). hit = flare + fly-up + tick.
// Isolation = mover gold + a faint "stay still" ring on the reference. Never red.

export class LightEngine {
  constructor(canvas, opts = {}) {
    this.cv = canvas; this.cx = canvas.getContext('2d'); this.mirror = opts.mirror ?? true;
    this.tier = opts.tier ?? 'kids';                                  // 'kids' full juice · 'adult' cool
    this.col = this.tier === 'kids'
      ? { main: '#ffc23e', hot: '#ffdf7e', ice: '#aee8ff', warm: '#ffb27d' }
      : { main: '#e6a93a', hot: '#f2c66d', ice: '#aee8ff', warm: '#e0a57a' };
    this.joints = {}; this.cues = []; this.parts = []; this.rings = []; this.comets = []; this.stills = []; this.fire = false;
    this.claps = []; this.freezes = [];   // b0.14: clap + freeze have their own visual grammar
    this.streak = 0;
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
    const n = this.tier === 'kids' ? 16 : 7;
    for (let i = 0; i < n; i++) this.parts.push({ x: p.x, y: p.y, vx: (Math.random() - .5) * 7, vy: (Math.random() - .8) * 7, r: 3 + Math.random() * 3, a: 1, col });
    this.rings.push({ x: p.x, y: p.y, r: 8, a: 1, col, grow: 4 }); this.clearCue(joint); this.audio.tick(this.streak || 0);
    // the grade word floats up (PERFECT/GOOD/OK) with the points tucked under it — encourage, never punish
    if (gradeWord) { this.flyUp(p, gradeWord); if (pts != null) this.parts.push({ x: p.x, y: p.y + 20, vx: 0, vy: -1.3, r: 0, a: 1, text: `+${pts}`, col: this.col.main, small: true }); }
    else if (pts != null) this.flyUp(p, `+${pts}`);
  }
  isoShimmer() {
    for (const n of ['lHip', 'rHip']) {
      const p = this.P(n); if (!p) continue;
      for (let i = 0; i < (this.tier === 'kids' ? 10 : 4); i++) this.parts.push({ x: p.x, y: p.y, vx: (Math.random() - .5) * 3, vy: -Math.random() * 2, r: 2.5, a: 1, col: this.col.hot });
    }
  }
  warm(joint = 'hipC') { const p = this.P(joint); if (p) this.rings.push({ x: p.x, y: p.y, r: 26, a: .5, col: this.col.warm, grow: 1.2, soft: true }); }
  ice() { const c = this.P('shoulderC'); if (c) this.rings.push({ x: c.x, y: c.y, r: 40, a: .9, col: this.col.ice, grow: 9, soft: true }); }
  // ── CLAP: two hands come together. Orbs on both wrists + a dotted "bring together" bridge,
  //    the window ring at the midpoint, and on contact the burst happens BETWEEN the hands. ──
  clapCue({ left = 'lWrist', right = 'rWrist', windowMs = 900, leadMs = 900 } = {}) {
    this.claps = [{ left, right, born: performance.now(), windowMs, leadMs }]; this.audio.chime();
  }
  clapHit(quality = 'good', pts = null) {
    const c = this.claps[0]; const a = c && this.P(c.left), b = c && this.P(c.right);
    const mid = (a && b) ? { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 } : (a || b || this.P('shoulderC'));
    if (!mid) return;
    const n = this.tier === 'kids' ? 24 : 10;                         // the burst is AT the contact point
    for (let i = 0; i < n; i++) this.parts.push({ x: mid.x, y: mid.y, vx: (Math.random() - .5) * 12, vy: (Math.random() - .55) * 12, r: 3 + Math.random() * 4, a: 1, col: this.col.hot });
    this.rings.push({ x: mid.x, y: mid.y, r: 6, a: 1, col: this.col.hot, grow: 8 });   // a ring expands from the contact
    this.rings.push({ x: mid.x, y: mid.y, r: 6, a: .8, col: this.col.main, grow: 4 });
    this.flyUp({ x: mid.x, y: mid.y }, quality === 'perfect' ? 'PERFECT!' : 'CLAP!');
    if (pts != null) this.parts.push({ x: mid.x, y: mid.y + 20, vx: 0, vy: -1.3, r: 0, a: 1, text: `+${pts}`, col: this.col.main, small: true });
    this.claps = []; this.audio.clap();                               // real clap transient, not a sine blip
  }
  // ── FREEZE: an ice ring around the WHOLE body that closes over the hold = a visible countdown ──
  bodyBounds() {
    const ns = ['head', 'nose', 'shoulderC', 'hipC', 'lShoulder', 'rShoulder', 'lHip', 'rHip', 'lWrist', 'rWrist', 'lKnee', 'rKnee'];
    let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9, any = false;
    for (const n of ns) { const p = this.P(n); if (!p) continue; any = true; minX = Math.min(minX, p.x); minY = Math.min(minY, p.y); maxX = Math.max(maxX, p.x); maxY = Math.max(maxY, p.y); }
    if (!any) return null;
    const pad = (this.cv.width + this.cv.height) * 0.03;
    return { x: (minX + maxX) / 2, y: (minY + maxY) / 2, r: Math.max(maxX - minX, maxY - minY) / 2 + pad };
  }
  freezeCue(durationMs = 3000) { this.freezes = [{ born: performance.now(), durationMs, state: 'holding' }]; this.audio.chime(); }
  freezeHeld() {
    const f = this.freezes[0]; if (f) f.state = 'held';
    const b = this.bodyBounds(); if (b) { this.rings.push({ x: b.x, y: b.y, r: b.r * 0.5, a: 1, col: this.col.ice, grow: 7, soft: true }); this.flyUp({ x: b.x, y: b.y - b.r * 0.55 }, 'FROZEN!'); }
    this.audio.ding();
  }
  freezeBroke() { const b = this.bodyBounds(); if (b) this.rings.push({ x: b.x, y: b.y, r: b.r * 0.7, a: .6, col: this.col.warm, grow: 5, soft: true }); this.freezes = []; }
  clearFreeze() { this.freezes = []; }
  setFire(on) { this.fire = on && this.tier === 'kids'; }
  comet(chain, quality = 'good') {                                    // the WAVE light: a head + tail riding the chain
    const pts = chain.map(n => this.P(n)).filter(Boolean); if (pts.length < 3) return;
    this.comets.push({ pts, t0: performance.now(), dur: quality === 'smooth' ? 550 : quality === 'good' ? 700 : 900, col: quality === 'smooth' ? this.col.hot : this.col.main });
  }
  flyUp(p, text) { this.parts.push({ x: p.x, y: p.y - 10, vx: 0, vy: -1.6, r: 0, a: 1, text, col: this.col.hot }); }
  // ── DRAW ──
  draw() {
    const cx = this.cx, now = performance.now(); cx.clearRect(0, 0, this.cv.width, this.cv.height);
    this.cues = this.cues.filter(c => (now - c.born) < c.leadMs + c.windowMs + 400);       // window closes with no hit → soft fade, then gone (no punishment)
    for (const c of this.cues) {
      const p = this.P(c.joint); if (!p) continue;
      const age = (now - c.born), pulse = 8 + Math.sin(age / 160) * 3, R = (this.fire ? 26 : 20) + pulse;
      const total = c.leadMs + c.windowMs, over = age - total;
      const fade = over > 0 ? Math.max(0, 1 - over / 400) : 1;                              // gentle dim-out past the window
      cx.globalAlpha = fade;
      const g = cx.createRadialGradient(p.x, p.y, 2, p.x, p.y, R * 2.4); g.addColorStop(0, this.fire ? this.col.hot : this.col.main); g.addColorStop(1, 'rgba(255,194,62,0)');
      cx.fillStyle = g; cx.beginPath(); cx.arc(p.x, p.y, R * 2.4, 0, 7); cx.fill();
      const frac = Math.max(0, 1 - age / total);                                            // ring closes across lead+window
      const inPerfect = frac < 0.34;                                                        // ring has reached the PERFECT zone → brighten so the kid sees WHEN to hit
      cx.strokeStyle = inPerfect ? 'rgba(255,246,205,1)' : 'rgba(255,223,126,.9)'; cx.lineWidth = inPerfect ? 5 : 3;
      cx.beginPath(); cx.arc(p.x, p.y, R * 2.4 * frac + R, 0, 7); cx.stroke();
      cx.strokeStyle = 'rgba(255,240,190,.85)'; cx.lineWidth = 3;                            // the PERFECT zone itself: a static brighter inner-third ring
      cx.beginPath(); cx.arc(p.x, p.y, R * 2.4 * 0.33 + R, 0, 7); cx.stroke();
      if (c.dir === 'L' || c.dir === 'R') {
        const s = (c.dir === 'R') ^ this.mirror ? -1 : 1;                                   // ribbon in SCREEN space
        cx.strokeStyle = 'rgba(255,194,62,.8)'; cx.lineWidth = 6; cx.lineCap = 'round'; cx.beginPath(); cx.moveTo(p.x, p.y); cx.quadraticCurveTo(p.x + s * 46, p.y - 8, p.x + s * 82, p.y - 2); cx.stroke();
      }
      if (c.dir === 'UP' || c.dir === 'DOWN') { const s = c.dir === 'UP' ? -1 : 1; cx.strokeStyle = 'rgba(255,194,62,.8)'; cx.lineWidth = 6; cx.beginPath(); cx.moveTo(p.x, p.y); cx.quadraticCurveTo(p.x + 8, p.y + s * 46, p.x + 2, p.y + s * 82); cx.stroke(); }
      for (const sn of c.still) {
        const q = this.P(sn); if (!q) continue;                                             // the ISOLATION pair: faint "stay still" ring
        cx.strokeStyle = 'rgba(255,255,255,.35)'; cx.setLineDash([6, 6]); cx.lineWidth = 2; cx.beginPath(); cx.arc(q.x, q.y, 22, 0, 7); cx.stroke(); cx.setLineDash([]);
      }
      cx.globalAlpha = 1;
    }
    // ── CLAP cue: orbs on both wrists + dotted bridge + closing window ring at the midpoint ──
    for (const c of this.claps) {
      const a = this.P(c.left), b = this.P(c.right); if (!a || !b) continue;
      const age = now - c.born, total = c.leadMs + c.windowMs, frac = Math.max(0, 1 - age / total);
      const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, span = Math.hypot(b.x - a.x, b.y - a.y) / 2;
      for (const p of [a, b]) { const g = cx.createRadialGradient(p.x, p.y, 2, p.x, p.y, 46); g.addColorStop(0, this.col.main); g.addColorStop(1, 'rgba(255,194,62,0)'); cx.fillStyle = g; cx.beginPath(); cx.arc(p.x, p.y, 46, 0, 7); cx.fill(); }
      cx.strokeStyle = 'rgba(255,223,126,.8)'; cx.setLineDash([4, 9]); cx.lineWidth = 3; cx.beginPath(); cx.moveTo(a.x, a.y); cx.lineTo(b.x, b.y); cx.stroke(); cx.setLineDash([]);
      const inPerfect = frac < 0.34;
      cx.strokeStyle = inPerfect ? 'rgba(255,246,205,1)' : 'rgba(255,223,126,.9)'; cx.lineWidth = inPerfect ? 5 : 3;
      cx.beginPath(); cx.arc(mid.x, mid.y, 18 + span * frac, 0, 7); cx.stroke();
      cx.strokeStyle = 'rgba(255,240,190,.85)'; cx.lineWidth = 3; cx.beginPath(); cx.arc(mid.x, mid.y, 24, 0, 7); cx.stroke();  // PERFECT contact zone
    }
    // ── FREEZE cue: an ice ring around the whole body that CLOSES over the hold duration ──
    for (const f of this.freezes) {
      const b = this.bodyBounds(); if (!b) continue; const age = now - f.born;
      if (f.state === 'held') { cx.strokeStyle = this.col.ice; cx.globalAlpha = .9; cx.lineWidth = 5; cx.beginPath(); cx.arc(b.x, b.y, b.r, 0, 7); cx.stroke(); cx.globalAlpha = 1; continue; }
      const frac = Math.max(0, 1 - age / f.durationMs), rr = b.r * (0.5 + 0.5 * frac);        // shrinks toward the body = countdown of stay-still time
      cx.strokeStyle = this.col.ice; cx.globalAlpha = .9; cx.lineWidth = 4; cx.setLineDash([11, 8]); cx.beginPath(); cx.arc(b.x, b.y, rr, 0, 7); cx.stroke(); cx.setLineDash([]);
      cx.globalAlpha = .45; cx.lineWidth = 2; cx.beginPath(); cx.arc(b.x, b.y, b.r * 0.5, 0, 7); cx.stroke(); cx.globalAlpha = 1;   // the "fully frozen" target the ring closes onto
      if (frac <= 0) f.state = 'held';
    }
    for (const m of this.comets) {
      const u = Math.min(1, (now - m.t0) / m.dur);
      for (let k = 0; k < 12; k++) { const uu = Math.max(0, u - k * 0.035); const q = pathPoint(m.pts, uu); cx.globalAlpha = (1 - k / 12) * .9; cx.fillStyle = m.col; cx.beginPath(); cx.arc(q.x, q.y, 10 - k * 0.6, 0, 7); cx.fill(); }
      cx.globalAlpha = 1; if (u >= 1) m.done = true;
    }
    this.comets = this.comets.filter(m => !m.done);
    for (const q of this.parts) {
      q.x += q.vx; q.y += q.vy; if (!q.text) q.vy += .12; q.a -= q.text ? .018 : .03; cx.globalAlpha = Math.max(q.a, 0);
      if (q.text) { cx.fillStyle = q.col; cx.textAlign = 'center'; cx.font = `800 ${q.small ? 18 : 30}px "Baloo 2",system-ui`; cx.fillText(q.text, q.x, q.y); cx.textAlign = 'start'; } else { cx.fillStyle = q.col; cx.beginPath(); cx.arc(q.x, q.y, q.r, 0, 7); cx.fill(); }
    }
    this.parts = this.parts.filter(q => q.a > 0); cx.globalAlpha = 1;
    for (const r of this.rings) { r.r += r.grow; r.a -= r.soft ? .015 : .05; cx.strokeStyle = r.col; cx.globalAlpha = Math.max(r.a, 0); cx.lineWidth = r.soft ? 8 : 3; cx.beginPath(); cx.arc(r.x, r.y, r.r, 0, 7); cx.stroke(); }
    this.rings = this.rings.filter(r => r.a > 0); cx.globalAlpha = 1;
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
