/* beta/lib/shoulder-beat.js — the SHOULDER LIGHT beat of Nova's approved intro, ported to Freeze v4 (NOVA-AUDIT 2026-11-22).
   Pure (no DOM): the page feeds it the judge keypoints (beta/lib/kp.js toJudge), it says what to show and what to say.
   Node tests: test/shoulder_beat_f4_test.mjs.

   WHERE IT COMES FROM (the intro Refael approved, quoted, not reinvented):
   · origin/main nova-commercial.html L4016-4077 introShoulderChallenge() (INTRO-V2V, 75396a4, FREEZE-APPROVED 2026-09-14,
     promoted to main in d29b13f "PROMOTE v1.0.4"): a light on the child's RIGHT shoulder, a REAL MoveNet shrug check,
     two endings — a real detected lift (the win) or a warm release after 20 s that never claims a lift (TRUTH LAW).
   · detection = that file's isoPulse (L4738): peak-to-peak of (lShoulder.y − rShoulder.y) over ISO.win = 1100 ms,
     normalised by shoulder width, above ISO.thr.shrug = 0.15, two hits in a row (L4063-4069, MINK 0.3 = kp.js GATE.min).
   · her words = SHOULDER-BEAT §4b (33f83fe, FREEZE-APPROVED 2026-09-20, founder spec): the EXACT lines sayLightArm /
     sayLightRetry, the retry at 8 s, the release at 20 s.
   · the win line: factShrug = "celebrate in five words" -> one exact ≤ 5-word line, said only after a REAL detection.
   law-shoulder (LAWS.md): never clock-gated into a win — a timeout only RELEASES, and on release she says nothing about it. */

export const SHOULDER = {
  joint: 'rShoulder',            // main L4024: window.__introCueJoint = 'right_shoulder' (kp.js: MoveNet's own label = the player's own right)
  winMs: 1100,                   // main L4733 ISO.win
  thr: 0.15,                     // main L4735 ISO.thr.shrug
  hits: 2,                       // main L4067 ++hits >= 2
  retryMs: 8000,                 // 33f83fe law-shoulderbeat: "the retry is 8s"
  releaseMs: 20000,              // main L4056 / 33f83fe: "RELEASE stays at 20s"
};

export const LINES = {
  en: { arm: 'Look — a magic light on your shoulder! Lift that shoulder up high, just that one!',     // 33f83fe sayLightArm (en)
        retry: "I haven't seen it yet — try lifting the shoulder with the light, high!",             // 33f83fe sayLightRetry (en)
        win: 'Yes! The light caught it!' },                                                         // factShrug: ≤ 5 words [CLI-FILL] exact words
  he: { arm: 'תראה — אור קסם על הכתף שלך! תרים אותה גבוה, רק אותה!',                                 // 33f83fe sayLightArm (he)
        retry: 'עוד לא ראיתי — נסה להרים את הכתף עם האור, גבוה!',                                     // 33f83fe sayLightRetry (he)
        win: 'יש! האור תפס את זה!' },                                                                // factShrug: ≤ 5 words [CLI-FILL]
};

/* createShoulderBeat({ aspect }) — aspect = camera height / width (normalised x and y have different pixel sizes).
   start(tMs) · feed(k, tMs) -> null | 'win'  · tick(tMs) -> null | 'retry' | 'release' · progress() 0..1 for the light's meter */
export function createShoulderBeat({ aspect = 16 / 9 } = {}){
  let t0 = null, buf = [], hits = 0, done = null, retried = false, last = 0;
  return {
    start(tMs){ t0 = tMs; buf = []; hits = 0; done = null; retried = false; last = 0; },
    get done(){ return done; },
    progress(){ return Math.max(0, Math.min(1, last / SHOULDER.thr)); },
    feed(k, tMs){
      if (t0 === null || done) return null;
      const ls = k?.lShoulder, rs = k?.rShoulder;
      if (!ls || !rs) { hits = Math.max(0, hits - 1); return null; }
      const sw = Math.abs(ls.x - rs.x);                          // in width units
      if (sw < 1e-3) return null;
      buf.push({ t: tMs, v: (ls.y - rs.y) * aspect });            // y converted to width units (main used pixels for both)
      while (buf.length && tMs - buf[0].t > SHOULDER.winMs) buf.shift();
      if (buf.length < 5) { last = 0; return null; }              // main L4742: b.length < 5 → 0
      let mn = Infinity, mx = -Infinity; for (const s of buf){ if (s.v < mn) mn = s.v; if (s.v > mx) mx = s.v; }
      last = (mx - mn) / sw;
      if (last > SHOULDER.thr){ if (++hits >= SHOULDER.hits){ done = 'win'; return 'win'; } }
      else hits = Math.max(0, hits - 1);
      return null;
    },
    tick(tMs){
      if (t0 === null || done) return null;
      const age = tMs - t0;
      if (age > SHOULDER.releaseMs){ done = 'release'; return 'release'; }
      if (!retried && age > SHOULDER.retryMs){ retried = true; return 'retry'; }
      return null;
    },
  };
}
