/* shared/handwave-core.js — HAND WAVE v4: FOLLOW MODE. The child leads, the light follows.
   Pure (no DOM) → tested in Node. Written by the architect.

   WHY v4 (founder, 3 Oct, after the real run WAVE-RUN-REPORT 2026-10-03_203356):
   v3 moved the light on HER clock — it arrived at a joint and left again whether or not the child got there, so a
   child even slightly behind missed everything ("the body was not moving at all" = the light had already moved on).
   v4: the light WAITS at each joint and advances ONLY when the child lifts that joint. Nova keeps dancing on her
   video; the light keeps to the child.

   THE RULES (founder-approved defaults, 3 Oct):
   · Fall behind → the light waits. It sticks at the joint (the page turns it amber after WAIT_AMBER s). It only
     jumps when Nova STARTS THE NEXT WAVE — the stuck wave's remaining steps are then missed — so each of the three
     waves is a fresh chance.
   · A star for EVERY joint you reach, whenever you reach it. Reaching it WITH her (≤ AFTER s after her move, not
     more than EARLY_OK s before) and with that joint doing the moving = clean (mint). Late, rushed, or dragged by
     another limb = messy (amber). The star counts either way. Wave bonus star unchanged: ≥ 80% of the wave.
   · Nothing fires without REAL movement. A joint that is merely already up (left there from the last step, or
     arms raised at the start) does not count; camera jitter does not count. See THE LIFT below.

   THE LIFT — what counts as "the child lifted that joint" (fixes every failure class in that report):
   · Each joint keeps its own RESTING HEIGHT: an envelope that follows the joint DOWN fast (REST_DOWN s) and UP very
     slowly (REST_UP s). Arms up at the start, or a joint still up from the previous step, can therefore never fake
     a rise — and can never block one either (once the arm comes down, rest is back under it in a quarter second).
   · lift = (rest − y) / shoulderWidth must reach the per-joint rise (CHAIN_LIFT: wrist 0.10 · elbow 0.08 ·
     shoulder 0.04 shoulder-widths — the original's gates, never the wrist above the shoulder).
   · AND the joint must have actually RISEN just now: its lift grew by ≥ RISE_FRACTION of the rise within the last
     RISE_WINDOW s. Standing with the arm already up does nothing; ±2 px camera jitter (smoothed) does nothing.

   THE WAVE (unchanged from v3 — her REAL wave, measured from handywave.mp4 frame by frame, confirmed by the
   founder 3 Oct): three passes, each wrist → elbow → shoulder → other shoulder → other elbow → other wrist.
   Seam steps that repeat the joint the previous wave just ended on are not scored twice (the light still flows
   through them). Keypoints in: { lShoulder, rShoulder, lElbow, rElbow, lWrist, rWrist, … } {x, y, vis} in PIXELS,
   un-mirrored, anatomical ('r' = the child's own right). */

export const SONG_END = 28.4;
export const GATES = { Shoulder: 0.5, Elbow: 0.45, Wrist: 0.40 };     // per-joint confidence floors (wrists are the weak joint)
export const CHAIN6 = ['rWrist', 'rElbow', 'rShoulder', 'lShoulder', 'lElbow', 'lWrist'];
export const CHAIN_LIFT = { Wrist: 0.10, Elbow: 0.08, Shoulder: 0.03 };   // shoulder 0.04→0.03 [v4.1]: her own shoulder ripple is ~0.08 — headroom for live jitter

/* [MIRROR FIX 12 Oct, founder] The child copies Nova like a MIRROR. Her first arm (her LEFT wrist) appears on the
   VIEWER'S RIGHT of the screen, and the child's self-view is mirrored — so the hand on the screen-right of HIS picture
   is his RIGHT hand. Therefore every joint is SWAPPED from her side to his: her left ↔ his right. The times are hers,
   measured; the sides below are already the CHILD'S. (Her original sides: lWrist 7.07 … rWrist 12.20 … lWrist 18.03.) */
const MIRROR = j => (j[0] === 'l' ? 'r' : 'l') + j.slice(1);
const NOVA_WAVES_HER = [
  // [v4.1, 12 Oct] times re-measured on the REAL handywave.mp4 (856 frames, pose-tracked): each value is where
  // that joint's ripple actually lives in her clip — w1 ends ~17s (not 18), w2 flows out of the held arm,
  // w3 is the quick both-arm finish starting 24.3.
  [[7.03, 'lWrist'], [7.53, 'lElbow'], [8.87, 'lShoulder'], [9.27, 'rShoulder'], [10.50, 'rElbow'], [12.13, 'rWrist'],
   [13.40, 'rElbow'], [14.60, 'rShoulder'], [15.17, 'lShoulder'], [16.23, 'lElbow'], [17.00, 'lWrist']],
  [[17.60, 'lWrist'], [18.95, 'lElbow'], [20.10, 'lShoulder'], [20.80, 'rShoulder'], [21.30, 'rElbow'], [21.90, 'rWrist']],
  [[24.30, 'rWrist'], [24.45, 'rElbow'], [24.70, 'rShoulder'], [25.00, 'lShoulder'], [25.60, 'lElbow'], [26.40, 'lWrist']],
];
export const NOVA_WAVES = NOVA_WAVES_HER.map(w => w.map(([t, j]) => [t, MIRROR(j)]));   // CHILD-space: mirror of her sides
export const WAVE_PATHS = NOVA_WAVES.map(w => w.map(([, j]) => j));
export const WAVE_START = NOVA_WAVES.map(w => w[0][0]);

export const LEAD = 0.25;            // a wave's first target opens this long before her first move
export const OPEN_EARLY = 0.65;       // [v4.1, 12 Oct] no target OPENS more than this before its own moment —
                                     // she waves continuously, so without this the chain raced seconds ahead of her beat
export const AFTER = 0.9;            // reach it within this of her move = "with her"
const EARLY_OK = 0.9;         // up to this much before her move is still "with her" (tightened 1.2→0.9, v4.1)
export const WAIT_AMBER = 1.5;       // waiting this long behind her move → the page turns the light amber
const REST_DOWN = 0.25;       // the resting height follows the joint DOWN this fast (seconds)
const REST_UP = 12;           // …and creeps UP this slowly — holding an arm up never becomes "rest"
const SMOOTH = 0.08;          // per-joint y smoothing (seconds) — kills single-frame jitter
const RISE_WINDOW = 0.7;      // the rise must have happened within this window
const RISE_FRACTION = 0.6;    // …and be at least this fraction of the joint's required lift
const RISE_MEMORY = 3.0;      // [v4.2, founder's real play 13 Oct] a joint that ROSE within the last 3s still counts even if
                              // it rose BEFORE its light opened — kids lift the whole arm, the wrist arrives early. His left
                              // wrist sat at 0.80 lift (8× the bar) and was unwinnable because it could no longer "freshly rise".
                              // Arms held up from the start stay dead: their rise is older than this memory.
const FRESH = 0.35;            // a lift reading older than this is stale (joint lost) — no hit on stale data
const CONFIRM = 2;            // [QA 12 Oct] a hit needs this many consecutive qualifying frames — single-frame jitter never fires
const UNSEEN_SKIP = 4;        // joint vanished mid-target
const UNSEEN_FAST = 1.5;      // joint not seen at all since the target opened — the camera clearly can't judge it        // [QA 12 Oct] a target whose joint the camera has not seen for this long SKIPS (no star) — the
                              // light waits for the CHILD, not for a joint the camera cannot judge; one bad joint never stalls a wave
const END_TAIL = 2.5;         // [QA 12 Oct] grace past the song's end so a step mid-reach still lands           // a lift reading older than this is stale (joint lost) — no hit on stale data

const kind = j => j.replace(/^[lr]/, '');
export const ok = (p, j) => !!p && (p.vis ?? 1) >= GATES[kind(j)];

/* the scored targets: every step of every wave, EXCEPT a step that repeats the joint the previous step ended on
   at (nearly) the same moment — the child is already there. The light still travels through it (WAVE_PATHS). */
export function scoredTargets(){
  const flat = [];
  NOVA_WAVES.forEach((w, wi) => w.forEach(([t, j], i) => flat.push({ t, joint: j, wave: wi, count: i, last: i === w.length - 1 })));
  const sc = flat.filter((c, k) => { const p = flat[k - 1]; return !(p && p.joint === c.joint && c.t - p.t < 1.0); });
  // if a wave's true last step was deduped away, the previous surviving step of that wave inherits `last`
  for (let w = 0; w < NOVA_WAVES.length; w++){ const mine = sc.filter(c => c.wave === w); mine.forEach(c => c.last = false); mine.at(-1).last = true; }
  return sc.map((c, idx) => ({ ...c, idx }));
}
export const TARGETS = scoredTargets();

/* body measures for one frame — shoulder width + whole-body/arm motion (for the run report) */
export function measure(k){
  const d = { present: false, sw: 0, midShY: 0 };
  if (!ok(k.lShoulder, 'lShoulder') || !ok(k.rShoulder, 'rShoulder')) return d;
  d.present = true;
  d.sw = Math.max(Math.abs(k.lShoulder.x - k.rShoulder.x), 20);
  d.midShY = (k.lShoulder.y + k.rShoulder.y) / 2;
  return d;
}

export class HandWave {
  constructor(){ this.reset(); }
  reset(){
    this.base = null; this.active = null; this.ti = 0; this.ended = false; this.started = false;
    this.stars = 0; this.hits = 0; this.streak = 0; this.bestStreak = 0; this.waveHits = NOVA_WAVES.map(() => 0); this.doneWaves = new Set();
    this._y = {}; this._rest = {}; this._hist = {}; this._riseAt = {}; for (const j of CHAIN6){ this._hist[j] = []; this._riseAt[j] = -99; }
    this._snaps = []; this.motion = 0; this._lastT = null;
    this.log = []; this.cam = {}; for (const j of CHAIN6) this.cam[j] = { n: 0, seen: 0, sum: 0 }; this._camAt = -1;
  }

  /* calibrate: the child standing still, arms down — seeds every joint's resting height */
  calibrate(k){
    const d = measure(k); if (!d.present) return false;
    this.base = { shoulderBaseY: d.midShY, sw: d.sw };
    for (const j of CHAIN6) if (ok(k[j], j)){ this._y[j] = k[j].y; this._rest[j] = k[j].y; }
    return true;
  }

  waiting(t){ return this.active ? { joint: this.active.joint, wave: this.active.wave, count: this.active.count, behind: +(t - this.active.t).toFixed(2) } : null; }
  /* the joint's current lift above its own resting height (shoulder-widths) — the page's fill-ring reads this live */
  liftOf(j){ const H = this._hist[j]; return H?.length ? Math.max(0, H.at(-1)[1]) : 0; }
  /* where the light is on the child: the active target's place along its wave's path (the page glides to it) */
  lightPos(){ return this.active ? { wave: this.active.wave, pos: this.active.count, joint: this.active.joint } : null; }

  /* one camera frame at HER clip time t (seconds). Returns this frame's events:
     target_open · hit · miss · wave_done · wave_jump · end */
  update(t, k){
    const ev = [];
    if (this.ended) return ev;
    const d = measure(k || {}); this.det = d;
    const dt = this._lastT == null ? 1 / 30 : Math.max(1e-3, Math.min(0.2, t - this._lastT));

    // ── motion over 0.2 s (for the report): real movement adds up, single-frame jitter does not.
    //    the larger of whole-body and ARMS — it's a hand game (QA 2026-10-03)
    if (d.present){
      this._snaps.push([t, k]); while (this._snaps.length > 2 && t - this._snaps[1][0] >= 0.2) this._snaps.shift();
      const old = this._snaps[0];
      if (old && t - old[0] >= 0.12){
        const avg = names => { let tot = 0, c = 0; for (const n of names){ const a = k[n], b = old[1][n]; if (a && b && (a.vis ?? 1) > 0.3 && (b.vis ?? 1) > 0.3){ tot += Math.hypot(a.x - b.x, a.y - b.y); c++; } } return c ? tot / c : 0; };
        const scale = 0.5 * (0.2 / (t - old[0])) / d.sw;
        this.motion = Math.min(1, Math.max(avg(Object.keys(k)), avg(['lElbow', 'rElbow', 'lWrist', 'rWrist'])) * scale);
      }
    }

    // ── each joint: smooth → resting-height envelope → lift history
    if (d.present) for (const j of CHAIN6){
      const p = k[j];
      this.cam[j].n++;
      if (!ok(p, j)) continue;
      this.cam[j].seen++; this.cam[j].sum += (p.vis ?? 1);
      const prev = this._y[j] ?? p.y;
      const y = prev + (p.y - prev) * Math.min(1, dt / SMOOTH); this._y[j] = y;
      let r = this._rest[j] ?? y;
      r += (y - r) * Math.min(1, dt / (y >= r ? REST_DOWN : REST_UP)); this._rest[j] = r;
      const lift = (r - y) / d.sw;
      const H = this._hist[j]; H.push([t, lift]); while (H.length && t - H[0][0] > RISE_WINDOW + 0.3) H.shift();
      // remember the last FULL rise of this joint (for the already-arrived rule) — a complete lift, not a jitter spike
      const winMin = Math.min(...H.map(([, v]) => v));
      if (lift - winMin >= CHAIN_LIFT[kind(j)]) this._riseAt[j] = t;
    }
    if (t - this._camAt >= 0.55){ this._camAt = t; } // cam counters above sample every frame; cadence kept for parity

    // ── waves on HER clock: when she starts the next wave, a stuck light jumps (its leftover steps are missed).
    //    [SEAM 2026-10-03] but a target always keeps its full "with her" window first — her wave 2 starts only
    //    0.42 s after wave 1's last wrist, and a child slightly behind IS lifting that wrist; never cut him mid-reach.
    const nowWave = WAVE_START.reduce((w, ws, i) => t >= ws - LEAD ? i : w, -1);
    if (this.active && nowWave > this.active.wave && t >= this.active.t + AFTER) this._abandon(t, nowWave, ev);

    // ── open the next target: the moment the previous resolved — but never before its wave has begun
    if (!this.active && this.ti < TARGETS.length){
      const n = TARGETS[this.ti];
      if (t >= Math.max(WAVE_START[n.wave] - LEAD, n.t - OPEN_EARLY)){
        this.active = { ...n, openedAt: t, best: 0 };
        this.started = true;
        ev.push({ type: 'target_open', target: this.active, newWave: n.count === TARGETS.find(x => x.wave === n.wave).count });
      }
    }

    // ── the one check that matters: did the child lift THIS joint, just now?
    const c = this.active;
    if (c && d.present){
      const j = c.joint, H = this._hist[j], last = H.at(-1);
      const seenAt = last ? last[0] : -1;
      const unseenFor = t - Math.max(c.openedAt, seenAt), unseenLimit = seenAt < c.openedAt ? UNSEEN_FAST : UNSEEN_SKIP;
      if (!(last && t - seenAt <= FRESH) && unseenFor >= unseenLimit){
        // the camera cannot see this joint — skip it (no star) rather than stall the wave on it
        this.streak = 0; this.log.push({ t: c.t, joint: j, wave: c.wave, result: 'miss', why: 'unseen' });
        ev.push({ type: 'miss', target: c, why: 'unseen' });
        if (c.last) this._waveDone(c.wave, ev);
        this.active = null; this.ti++;
        if (this.ti < TARGETS.length){ const n = TARGETS[this.ti];
          if ((n.wave === c.wave || t >= WAVE_START[n.wave] - LEAD) && t >= n.t - OPEN_EARLY){ this.active = { ...n, openedAt: t, best: 0 }; ev.push({ type: 'target_open', target: this.active, newWave: n.wave !== c.wave }); } }
      } else if (last && t - seenAt <= FRESH){
        const lift = last[1];
        if (lift > c.best) c.best = +lift.toFixed(2);
        const need = CHAIN_LIFT[kind(j)];
        const minRecent = Math.min(...H.filter(([tt]) => t - tt <= RISE_WINDOW).map(([, v]) => v));
        const rose = lift - minRecent;
        const roseRecently = t - this._riseAt[j] <= RISE_MEMORY;      // arrived early with the arm = still a real move
        c.q = (lift >= need && (rose >= RISE_FRACTION * need || roseRecently)) ? (c.q || 0) + 1 : 0;
        if (c.q >= CONFIRM){
          const at = +(t - c.t).toFixed(2);
          const withHer = at <= AFTER && at >= -EARLY_OK;
          // isolation: among the joints we can see, did THIS one do the most recent rising?
          let top = 0; for (const jj of CHAIN6){ const HH = this._hist[jj]; const win = HH.filter(([tt]) => t - tt <= RISE_WINDOW).map(([, v]) => v);
            if (win.length >= 2) top = Math.max(top, win.at(-1) - Math.min(...win)); }
          const isolated = rose >= 0.3 * top;   // [v4.1] a WAVE makes neighbors co-move — demand a real share, not dominance
          const quality = withHer && isolated ? 'clean' : 'messy';
          this.hits++; this.stars++; this.streak++; this.bestStreak = Math.max(this.bestStreak, this.streak); this.waveHits[c.wave]++;
          this.log.push({ t: c.t, joint: j, wave: c.wave, result: 'hit', quality, after: at, withHer, isolated });
          ev.push({ type: 'hit', target: c, quality, withHer, at, joints: [j] });
          if (c.last) this._waveDone(c.wave, ev);
          this.active = null; this.ti++;
          // the next target opens the moment the previous resolved — but never ahead of HER beat (OPEN_EARLY)
          if (this.ti < TARGETS.length){ const n = TARGETS[this.ti];
            if ((n.wave === c.wave || t >= WAVE_START[n.wave] - LEAD) && t >= n.t - OPEN_EARLY){ this.active = { ...n, openedAt: t, best: 0 }; ev.push({ type: 'target_open', target: this.active, newWave: n.wave !== c.wave }); } }
        }
      }
    }

    // ── the song ends: whatever the light was still waiting for is missed
    if (t >= SONG_END + (this.active ? END_TAIL : 0) && !this.ended){
      if (this.active || this.ti < TARGETS.length) this._abandon(t, NOVA_WAVES.length, ev, 'song_end');
      this.ended = true;
      ev.push({ type: 'end', summary: this.summary() });
    }
    this._lastT = t;
    return ev;
  }

  _abandon(t, uptoWave, ev, why = 'wave_over'){
    const missed = [];
    const drop = c => {
      this.streak = 0;
      this.log.push({ t: c.t, joint: c.joint, wave: c.wave, result: 'miss', why, best: c.best ?? 0, motion: +this.motion.toFixed(2) });
      ev.push({ type: 'miss', target: c, why }); missed.push(c);
      if (c.last) this._waveDone(c.wave, ev);
    };
    if (this.active){ drop(this.active); this.active = null; this.ti++; }
    while (this.ti < TARGETS.length && TARGETS[this.ti].wave < uptoWave){ drop({ ...TARGETS[this.ti], best: 0 }); this.ti++; }
    if (missed.length) ev.push({ type: 'wave_jump', missed: missed.length, toWave: uptoWave < NOVA_WAVES.length ? uptoWave : null });
  }

  _waveDone(w, ev){
    if (this.doneWaves.has(w)) return; this.doneWaves.add(w);
    const n = TARGETS.filter(c => c.wave === w).length, h = this.waveHits[w], bonus = h >= Math.ceil(0.8 * n);
    if (bonus) this.stars++;
    ev.push({ type: 'wave_done', wave: w, hits: h, of: n, bonus });
  }

  summary(){
    const max = TARGETS.length + NOVA_WAVES.length;
    return { stars: this.stars, maxStars: max, hits: this.hits, total: TARGETS.length, bestStreak: this.bestStreak,
      waveHits: [...this.waveHits], medal: this.stars / max >= 0.7 ? 'gold' : this.stars / max >= 0.4 ? 'silver' : 'bronze', log: this.log };
  }
}

