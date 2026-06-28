/* ============================================================================
 * nova-engine.js — THE ONE-CLOCK LIGHT ENGINE  (NOVA-OPERATION-BOOK, Part 1)
 * Built to the operation book EXACTLY — no improvised visuals/timings/thresholds.
 *
 * THE LAW:
 *  • ONE clock: the song's audio.currentTime(ms) drives everything. No racing timers.
 *  • TWO inputs only: songmap (which joint + when + dir = the START) and MoveNet
 *    (did the NAMED joint do it = the REWARD). The body never initiates.
 *  • Draw nothing on doubt (below a joint's confidence floor → no light there).
 *  • No text on the body, no arrows — direction is shown by the light LEANING.
 *  • Coords passed in are already pixel-space + mirror-relabeled by the game.
 *
 * THE CUE LIFECYCLE (5 states, from cue start, exact):
 *  A PULSE  0→300ms   soft pulsing orb at the joint (GOLD) — "look here"
 *  B GUIDE  300ms→    a short ribbon LEANS 40*k px in the cue's direction (GOLD)
 *  C FLARE  on MoveNet confirm — bright + quality-colour + sparkle burst (reward)
 *  D TRAVEL wave-chain only — bright head advances to next joint (river of light)
 *  E FADE   at cue close — eases out via the trail (no hard cut, no red on miss)
 *
 * USAGE (game side):
 *   const eng = NovaEngine.create(ctx, { songmap, actions, songEndMs });
 *   // each rAF, with mirror+pixel keypoints m = {name:{x,y,score}} and the song clock:
 *   eng.frame(songMs, m);
 *   actions[action] = { anchor(m), leanVec(dir), check(m,k,now)->false|{q}, bar, chain?, holdMs? }
 * ========================================================================== */
(function (root) {
  'use strict';

  // §1.2 color constants — exact, no substitution
  var CORE = '255,253,245', GOLD = '255,210,122', AMBER = '255,166,61',
      DEEP = '242,115,12', CLEAN = '191,255,200', MESSY = '255,122,61';
  // §1.7 per-joint confidence floors
  var FLOOR = { wrist: 0.40, elbow: 0.45, shoulder: 0.50, hip: 0.45, nose: 0.40, ear: 0.40, knee: 0.45 };
  function floorFor(name) { for (var key in FLOOR) if (name.indexOf(key) >= 0) return FLOOR[key]; return 0.45; }

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }
  function mix(c1, c2, f) { var a = c1.split(',').map(Number), b = c2.split(',').map(Number);
    return a.map(function (v, i) { return Math.round(lerp(v, b[i], f)); }).join(','); }
  // §1.2 quality → colour
  function qColor(q) { return q >= 0.66 ? mix(GOLD, CLEAN, (q - 0.66) / 0.34) : q < 0.4 ? mix(GOLD, MESSY, (0.4 - q) / 0.4) : GOLD; }

  // §1.6 the 3-pass glow (radial gradients only, additive) — exact ratios
  function orb(ctx, x, y, r, trip, alpha) {
    if (r <= 0) return;
    var g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, 'rgba(' + trip + ',' + alpha + ')');
    g.addColorStop(0.45, 'rgba(' + trip + ',' + (alpha * 0.55) + ')');
    g.addColorStop(1, 'rgba(' + trip + ',0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
  }
  function glow3(ctx, x, y, baseR, k, trip) {       // bloom/body/core, widest+dimmest first
    orb(ctx, x, y, baseR * k * 3.5, AMBER, 0.14);
    orb(ctx, x, y, baseR * k * 1.8, trip, 0.45);
    orb(ctx, x, y, baseR * k * 0.6, CORE, 0.95);
  }

  function create(ctx, opts) {
    opts = opts || {};
    var songmap = (opts.songmap || []).slice().sort(function (a, b) { return a.t - b.t; });
    var actions = opts.actions || {};
    var songEndMs = opts.songEndMs || 999999;

    // per-cue runtime state
    var curIdx = -1, cueStartMs = 0, confirmed = false, flareMs = -1, confirmQ = 0.6;
    var spine = [], sparks = [], dispTrip = GOLD, chainStep = 0, holdStart = -1, holdFrac = 0;
    var lastNow = 0;

    function reset() { curIdx = -1; confirmed = false; flareMs = -1; spine = []; sparks = []; dispTrip = GOLD; chainStep = 0; holdStart = -1; holdFrac = 0; }

    // confidence-gated anchor (returns null below floor — draw nothing on doubt)
    function gated(kp) { return kp && kp.score >= floorFor(kp.name || '') ? kp : null; }

    // find the active cue for this song time (newest wins on overlap — §Part 4)
    function activeCue(songMs) {
      var found = -1;
      for (var i = 0; i < songmap.length; i++) {
        var c = songmap[i], close = c.close != null ? c.close : (c.t + (c.dur || 1080));
        if (songMs >= c.t && songMs < close) found = i;   // last match = newest
      }
      return found;
    }

    function frame(songMs, m) {
      var now = (root.performance && performance.now) ? performance.now() : songMs;
      var dt = lastNow ? (now - lastNow) : 16; lastNow = now;
      var W = ctx.canvas.width, H = ctx.canvas.height;

      // §1.1 trail persistence — destination-out fade (FADE = 0.18), never clearRect
      ctx.globalCompositeOperation = 'destination-out';
      ctx.fillStyle = 'rgba(0,0,0,0.18)'; ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'source-over';

      // §1.3 body-relative unit
      var ls = gated(m.left_shoulder), rs = gated(m.right_shoulder);
      var unit = (ls && rs) ? dist(ls, rs) : 180;
      var k = clamp(unit / 220, 0.4, 3.0);

      // resolve active cue + lifecycle bookkeeping
      var idx = activeCue(songMs);
      if (idx !== curIdx) { curIdx = idx; cueStartMs = songMs; confirmed = false; flareMs = -1; spine = []; chainStep = 0; holdStart = -1; holdFrac = 0; }

      var bar = null;
      if (idx >= 0) {
        var cue = songmap[idx], act = actions[cue.action];
        if (act) bar = runCue(cue, act, m, k, songMs, now, dt, W, H);
      }

      // sparkles always finish their life (even after the joint stops) — §1.4C
      ctx.globalCompositeOperation = 'lighter';
      sparks = sparks.filter(function (s) {
        var age = (now - s.born) / s.ttl; if (age >= 1) return false;
        s.x += s.vx; s.y += s.vy; s.vy -= 0.012;
        var tw = 0.6 + 0.4 * Math.sin(now / 80 + s.x);
        orb(ctx, s.x, s.y, s.r * (1 - age * 0.5), CORE, (1 - age) * tw); return true;
      });
      ctx.globalCompositeOperation = 'source-over';

      return { cueIndex: idx, action: idx >= 0 ? songmap[idx].action : null, confirmed: confirmed, quality: confirmed ? confirmQ : null, bar: bar };
    }

    function runCue(cue, act, m, k, songMs, now, dt, W, H) {
      var elapsed = songMs - cue.t;
      var close = cue.close != null ? cue.close : (cue.t + (cue.dur || 1080));
      var windowMs = close - cue.t;

      // anchor(s): screen points for this cue's joint(s); null if below floor
      var anchors = act.anchor ? act.anchor(m, gated) : null;
      if (anchors && !Array.isArray(anchors)) anchors = [anchors];
      anchors = (anchors || []).filter(Boolean);

      // ── MoveNet check → FLARE (state C). check returns false or {q}
      if (!confirmed && act.check) {
        var res = act.check(m, k, now);
        if (res) { confirmed = true; flareMs = now; confirmQ = (res.q != null ? res.q : 0.7);
          // sparkle burst along the lean direction, count ∝ quality
          var lv = act.leanVec ? act.leanVec(cue.dir) : [0, -1];
          var base = anchors[0] || { x: W / 2, y: H / 2 };
          var n = 5 + Math.round(clamp(confirmQ, 0, 1) * 4);
          for (var s = 0; s < n; s++) { var a = Math.atan2(lv[1], lv[0]) + (((s * 0.37) % 1) - 0.5) * 1.1, sp = (1.2 + (s * 0.5) % 1.6) * k;
            sparks.push({ x: base.x, y: base.y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 0.2, born: now,
              ttl: 400 + (s * 90) % 500, r: (1 + (s * 0.6) % 2) * k }); }
        }
      }

      // ── HOLD mechanic (freeze) — bar = hold fraction
      if (act.bar === 'hold' && act.holdMs) {
        var still = act.check ? !!act.check(m, k, now) : false;   // for hold, check = "is still"
        if (still) { if (holdStart < 0) holdStart = now; holdFrac = clamp((now - holdStart) / act.holdMs, 0, 1); }
        else { holdStart = -1; holdFrac = Math.max(0, holdFrac - dt / 600); }   // smooth reset, not jarring
        if (holdFrac >= 1 && !confirmed) { confirmed = true; flareMs = now; confirmQ = 0.95; }
      }

      // ── target display colour (crossfade ~0.12/frame, never snap) — §1.2
      var targetTrip = confirmed ? qColor(confirmQ) : GOLD;
      dispTrip = mix(dispTrip, targetTrip, 0.12);

      ctx.globalCompositeOperation = 'lighter';

      if (!anchors.length) { ctx.globalCompositeOperation = 'source-over'; return barInfo(act, elapsed, windowMs); }

      var flareT = flareMs >= 0 ? (now - flareMs) : -1;       // ms since flare
      var flareBump = (flareT >= 0 && flareT < 120) ? (1 + 0.4 * (1 - flareT / 120)) : 1;

      anchors.forEach(function (p, i) {
        if (!confirmed && elapsed < 300) {
          // STATE A — PULSE (0→300ms): radius 16k*(1+0.35 sin(t*12)), alpha 0.5→0.9
          var ph = elapsed / 1000;
          var r = 16 * k * (1 + 0.35 * Math.sin(ph * 12 * Math.PI));
          var al = lerp(0.5, 0.9, Math.min(1, elapsed / 300));
          orb(ctx, p.x, p.y, r * 3.5 / 16 * 16, AMBER, 0.14 * al); // bloom
          orb(ctx, p.x, p.y, r * 1.8, GOLD, 0.45 * al);
          orb(ctx, p.x, p.y, r * 0.6, CORE, 0.9 * al);
        } else {
          // STATE B — GUIDE/LEAN (and C flare brightens it): short ribbon leaning in dir
          var lv = act.leanVec ? act.leanVec(cue.dir) : [0, -1];
          var reachT = confirmed ? 1 : clamp((elapsed - 300) / 500, 0.25, 0.85);   // flare completes the stretch
          var reach = 40 * k * reachT;
          drawLean(p, lv, reach, k, now, confirmed ? dispTrip : GOLD, confirmed ? 0.9 : 0.55, flareBump, i);
          // bright core on the joint
          orb(ctx, p.x, p.y, 16 * k * (confirmed ? 1.0 : 0.7) * flareBump, confirmed ? dispTrip : GOLD, confirmed ? 0.95 : 0.6);
        }
      });

      ctx.globalCompositeOperation = 'source-over';
      return barInfo(act, elapsed, windowMs);
    }

    // a short leaning ribbon (spine of ~10 nodes) extending `reach` px along `lv`, sine shimmer
    function drawLean(p, lv, reach, k, now, trip, alpha, bump, idx) {
      var N = 10, t = now / 1000;
      var nx = lv[0], ny = lv[1], len = Math.hypot(nx, ny) || 1; nx /= len; ny /= len;
      var perpx = -ny, perpy = nx;
      ctx.beginPath();
      for (var i = 0; i < N; i++) {
        var f = i / (N - 1);
        var sh = Math.sin(t * 5 + i * 0.55 + idx) * 6 * k * f;   // shimmer amp 6k, speed 5
        var x = p.x + nx * reach * f + perpx * sh, y = p.y + ny * reach * f + perpy * sh;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      var tipx = p.x + nx * reach, tipy = p.y + ny * reach;
      var g = ctx.createLinearGradient(p.x, p.y, tipx, tipy);
      g.addColorStop(0, 'rgba(' + trip + ',' + alpha + ')'); g.addColorStop(1, 'rgba(' + DEEP + ',0)');
      ctx.strokeStyle = g; ctx.lineWidth = 13 * k * bump; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.stroke();
    }

    function barInfo(act, elapsed, windowMs) {
      // §1.5 timing bar — ONE meaning per game; returns {kind,value} the game draws in the top strip
      if (act.bar === 'hold') return { kind: 'hold', value: holdFrac };                 // fills as held
      if (act.bar === 'sequence') return { kind: 'sequence', value: clamp(chainStep / 6, 0, 1) };
      return { kind: 'window', value: clamp(1 - elapsed / windowMs, 0, 1) };            // drains over window
    }

    function advanceChain() { chainStep++; }   // wave 6-count travel hook

    return { frame: frame, reset: reset, advanceChain: advanceChain,
             get state() { return { curIdx: curIdx, confirmed: confirmed, q: confirmQ }; },
             colors: { CORE: CORE, GOLD: GOLD, AMBER: AMBER, CLEAN: CLEAN, MESSY: MESSY }, qColor: qColor, glow3: glow3, orb: orb };
  }

  root.NovaEngine = { create: create, FLOOR: FLOOR, qColor: qColor };
})(typeof window !== 'undefined' ? window : this);
