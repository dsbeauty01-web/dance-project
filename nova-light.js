/* ============================================================================
 * nova-light.js — Nova Magic-Light SHARED engine  (CLI-BUILD-FULL spec)
 * One self-contained module; the three games import it and pass per-game config.
 * The GAME decides WHICH keypoints to light (anchors) + reads the sequence; this
 * module owns the RENDER: focus orb + top-strip chevron + undulating ribbon, plus
 * sparkles, success-bloom and outward-burst. No duplication across games.
 *
 * Hard rules baked in (auto-fail list, §8):
 *   • confidence gate ≥0.5 enforced by the caller; we only draw anchors we're given.
 *   • NO nose/face anchor — the caller never passes one; we never invent positions.
 *   • destination-out fade (never clearRect); radial gradients only (never hard arc fill).
 *   • additive 'lighter' blend; body-relative sizing via k = shoulderDist/220.
 *   • warm gold; green only mixed into gold for clean isolation.
 *
 * Shipped "impress me" extras (§9) — chosen because each makes the kid feel SEEN:
 *   ✓ Anticipation pre-glow  — faint orb on the target ~400ms before the cue (Nova "points").
 *   ✓ Success bloom          — clean hit flares the ribbon + releases a sparkle burst.
 *   ✓ Breathing idle         — barely-there warm shimmer between cues so it's never dead.
 *   ✓ Velocity hue shimmer   — faster motion pushes the core whiter/hotter (effort = heat).
 *   (Skipped: none — all four serve "the kid feels seen".)
 *
 * Per-game behavior is one engine + a `mode`:
 *   'isolation' (Up Groove)  — tight wrap on the cued joint + OUTWARD BURST on hit.
 *   'travel'    (Hand Wave)  — long river flowing a path + BLOOM as it passes each joint.
 *   'calm'      (Hello Hello)— shorter, gentler, slower; soft bursts/blooms (ages 4–7).
 * ========================================================================== */
(function (root) {
  'use strict';

  var COL = {
    core: '255,253,245',  // hot near-white center
    gold: '255,210,122',  // warm gold mid
    amber:'255,166,61',   // amber bloom
    deep: '242,115,12',   // deep ember (ribbon tail)
    clean:'191,255,200',  // #BFFFC8 clean-iso mint mixed into gold
    messy:'255,122,61'    // #FF7A3D "almost", never "wrong"
  };

  var BASE = {
    mode: 'isolation',
    nodes: 22,            // ribbon spine length
    smooth: 0.35,         // spine lerp
    waveAmp: 14, waveSpeed: 6.0, wavePhase: 0.55,  // undulation (flag-in-wind)
    headWidth: 16, fade: 0.16,
    refShoulder: 220,     // body unit baseline
    coreR: 16,            // focus-orb radius
    sparkPerVel: 0.6, sparkTTL: [400, 900], sparkSize: [1, 3], sparkScale: 1,
    burstOnHit: false,    // isolation: rays OUT from torso on hit
    bloomOnVertex: false, // travel: soft flare as the comet passes a joint
    chevron: true,        // top-strip direction chevron
    idleBreath: true,     // breathing shimmer between cues
    intensity: 1          // calm games dial this down
  };

  // ---- low-level helpers ---------------------------------------------------
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function mix(t1, t2, f) { var a = t1.split(',').map(Number), b = t2.split(',').map(Number);
    return a.map(function (v, i) { return Math.round(lerp(v, b[i], f)); }).join(','); }
  function rnd(seed) { var x = Math.sin(seed) * 10000; return x - Math.floor(x); }  // deterministic-ish

  function orb(ctx, x, y, r, trip, alpha) {
    if (r <= 0) return;
    var g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, 'rgba(' + trip + ',1)');
    g.addColorStop(0.45, 'rgba(' + trip + ',0.5)');
    g.addColorStop(1, 'rgba(' + COL.gold + ',0)');
    ctx.globalAlpha = alpha == null ? 1 : alpha;
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
    ctx.globalAlpha = 1;
  }

  function chevron(ctx, cx, cy, ang, k, trip, now) {
    var L = 46 * k, P = [[-L * 0.45, -L * 0.55], [L * 0.55, 0], [-L * 0.45, L * 0.55]],
        w = 5 * k * (1 + 0.2 * Math.sin(now / 300));
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    [[3.2, 0.16, COL.amber], [1.6, 0.5, trip], [0.7, 0.95, COL.core]].forEach(function (s) {
      ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]); ctx.lineTo(P[1][0], P[1][1]); ctx.lineTo(P[2][0], P[2][1]);
      ctx.strokeStyle = 'rgba(' + s[2] + ',' + s[1] + ')'; ctx.lineWidth = w * s[0]; ctx.stroke();
    });
    ctx.restore();
  }

  // quality 0..1 → ribbon/orb color (mint clean → gold → amber messy)
  function qcolor(q) {
    return q > 0.66 ? mix(COL.gold, COL.clean, (q - 0.66) / 0.34)
         : q < 0.4  ? mix(COL.gold, COL.messy, (0.4 - q) / 0.4)
         : COL.gold;
  }

  // ---- engine instance -----------------------------------------------------
  function create(ctx, config) {
    var cfg = Object.assign({}, BASE, config || {});
    var wraps = {};        // per-anchor spine (isolation/calm)
    var river = [];        // single travelling spine (travel)
    var sparks = [], bursts = [], blooms = [];
    var pendingBurst = null, lastVertex = -1, lastSpark = 0;
    var idlePhase = 0;

    function reset() { wraps = {}; river.length = 0; sparks.length = 0; bursts.length = 0; blooms.length = 0; pendingBurst = null; lastVertex = -1; }

    // caller signals a clean/strong hit → schedule the outward burst (isolation) at the anchors
    function hit(q) { pendingBurst = (q == null ? 0.85 : q); }

    function spawnBurst(a, center, q, k, trip, now) {
      var base = center ? Math.atan2(a.y - center.y, a.x - center.x) : -Math.PI / 2;
      var n = 5 + Math.round(clamp(q, 0, 1) * 4);
      var rays = [];
      for (var i = 0; i < n; i++) { var f = n > 1 ? (i / (n - 1) - 0.5) : 0;
        rays.push({ a: base + f * (70 * Math.PI / 180), lenMul: 0.8 + (i * 0.37) % 0.5, wMul: 0.6 + (i * 0.29) % 0.8 }); }
      bursts.push({ x: a.x, y: a.y, born: now, ttl: 430, maxLen: 72 * k, trip: trip, rays: rays });
      for (var s = 0; s < n; s++) { var ang = base + (((s * 0.41) % 1) - 0.5) * (70 * Math.PI / 180), sp = (1.4 + (s * 0.53) % 1.6) * k;
        sparks.push({ x: a.x, y: a.y, vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp - 0.2, born: now,
          ttl: lerp(cfg.sparkTTL[0], cfg.sparkTTL[1], (s * 0.17) % 1), r: lerp(cfg.sparkSize[0], cfg.sparkSize[1], (s * 0.23) % 1) * k * cfg.sparkScale }); }
    }

    function drawRibbon(spine, k, t, trip, intensity) {
      function pass(widthMul, alpha, c) {
        if (spine.length < 2) return;
        ctx.beginPath();
        for (var i = 0; i < spine.length; i++) {
          var A = spine[i], B = spine[Math.min(i + 1, spine.length - 1)];
          var ang = Math.atan2(B.y - A.y, B.x - A.x) + Math.PI / 2, taper = i / spine.length;
          var off = Math.sin(t * cfg.waveSpeed + i * cfg.wavePhase) * cfg.waveAmp * k * taper * intensity;
          var x = A.x + Math.cos(ang) * off, y = A.y + Math.sin(ang) * off;
          i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
        }
        var hd = spine[0], tl = spine[spine.length - 1];
        var g = ctx.createLinearGradient(hd.x, hd.y, tl.x, tl.y);
        g.addColorStop(0, 'rgba(' + c + ',' + alpha + ')'); g.addColorStop(1, 'rgba(' + COL.deep + ',0)');
        ctx.strokeStyle = g; ctx.lineWidth = cfg.headWidth * widthMul * k; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.stroke();
      }
      pass(3.5, 0.14 * intensity, COL.amber); pass(1.8, 0.45 * intensity, trip); pass(0.6, 0.95, COL.core);
    }

    /* The one render call. opts:
     *   anchors : [{x,y}]    screen points to light (caller already gated ≥0.5; [] = nothing)
     *   center  : {x,y}|null torso center (for outward burst direction)
     *   k       : body unit  (shoulderDist/220, clamped)
     *   W,H     : canvas size
     *   quality : 0..1       drives color
     *   velocity: px/frame   of the lead anchor (hue shimmer + sparkle rate)
     *   dir     : 'left'|'right'|'up'|null   chevron direction (top strip)
     *   travelHead, travelVertex : for mode:'travel' (river head pos + which joint index it just passed)
     *   now     : performance.now()
     *   active  : bool        a cue is live (false → idle breath only)
     */
    function render(opts) {
      var now = opts.now, W = opts.W, H = opts.H, k = opts.k || 1, q = (opts.quality == null ? 0.6 : opts.quality);
      var intensity = cfg.intensity;
      // velocity hue shimmer — effort reads as heat (push core hotter/whiter)
      var vel = opts.velocity || 0;
      var trip = qcolor(q);
      if (vel > 6) trip = mix(trip, COL.core, clamp((vel - 6) / 30, 0, 0.4));

      // 1) FADE (destination-out keeps the webcam clear; never clearRect)
      ctx.globalCompositeOperation = 'destination-out';
      ctx.fillStyle = 'rgba(0,0,0,' + cfg.fade + ')'; ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'source-over';

      var anchors = opts.anchors || [];

      // pending burst (isolation) fires outward from each lit anchor
      if (pendingBurst != null) { if (cfg.burstOnHit && anchors.length) anchors.forEach(function (a) { spawnBurst(a, opts.center, pendingBurst, k, trip, now); }); pendingBurst = null; }

      ctx.globalCompositeOperation = 'lighter';
      var t = now / 1000;

      if (cfg.mode === 'travel') {
        // ---- TRAVEL: one long river follows the supplied head along the path ----
        if (opts.travelHead) {
          river.unshift({ x: opts.travelHead.x, y: opts.travelHead.y });
          if (river.length > cfg.nodes) river.pop();
          for (var i = 1; i < river.length; i++) { river[i].x = lerp(river[i].x, river[i - 1].x, cfg.smooth); river[i].y = lerp(river[i].y, river[i - 1].y, cfg.smooth); }
          if (cfg.bloomOnVertex && opts.travelVertex != null && opts.travelVertex !== lastVertex) {
            lastVertex = opts.travelVertex; var jp = opts.travelHead;
            blooms.push({ x: jp.x, y: jp.y, born: now, ttl: 300, trip: trip });
            for (var s = 0; s < 5; s++) { var a2 = rnd(now + s) * 6.283, sp2 = (0.5 + rnd(now + s + 1) * 0.5) * k;
              sparks.push({ x: jp.x, y: jp.y, vx: Math.cos(a2) * sp2, vy: Math.sin(a2) * sp2 - 0.1, born: now, ttl: lerp(cfg.sparkTTL[0], cfg.sparkTTL[1], rnd(now + s + 2)), r: lerp(cfg.sparkSize[0], cfg.sparkSize[1], rnd(now + s + 3)) * k * cfg.sparkScale }); }
          }
          drawRibbon(river, k, t, trip, intensity);
          orb(ctx, opts.travelHead.x, opts.travelHead.y, cfg.coreR * k * 1.05, trip, 1);
        } else { river.length = 0; }
      } else {
        // ---- ISOLATION / CALM: tight wrap hugging each cued anchor ----
        anchors.forEach(function (a, idx) {
          var sp = wraps[idx] || (wraps[idx] = []);
          sp.unshift({ x: a.x, y: a.y }); if (sp.length > cfg.nodes) sp.pop();
          for (var i = 1; i < sp.length; i++) { sp[i].x = lerp(sp[i].x, sp[i - 1].x, cfg.smooth); sp[i].y = lerp(sp[i].y, sp[i - 1].y, cfg.smooth); }
          drawRibbon(sp, k, t, trip, intensity);
          orb(ctx, a.x, a.y, cfg.coreR * k * 1.4, COL.amber, 0.26 * intensity);  // soft halo
          orb(ctx, a.x, a.y, cfg.coreR * k, trip, 1);                            // focus orb ON the joint
          // velocity sparkles (still limb = none)
          if (vel > 0 && rnd(now + idx) < vel * cfg.sparkPerVel * 0.05) {
            sparks.push({ x: a.x, y: a.y, vx: (rnd(now) - 0.5) * 1.2, vy: -rnd(now + 1) * 0.4 - 0.2, born: now,
              ttl: lerp(cfg.sparkTTL[0], cfg.sparkTTL[1], rnd(now + 2)), r: lerp(cfg.sparkSize[0], cfg.sparkSize[1], rnd(now + 3)) * k * cfg.sparkScale });
          }
        });
        for (var key in wraps) { if (+key >= anchors.length) delete wraps[key]; }
      }

      // success-bloom blooms (travel vertices + isolation hit blooms) — soft flares
      blooms = blooms.filter(function (b) { var age = (now - b.born) / b.ttl; if (age >= 1) return false;
        var r = (9 + 16 * Math.sin(Math.min(1, age) * Math.PI)) * k; orb(ctx, b.x, b.y, r, b.trip, (1 - age) * 0.9 * intensity); return true; });

      // outward bursts (isolation hit) — rays narrow as they extend, gold→white
      bursts = bursts.filter(function (b) { var age = (now - b.born) / b.ttl; if (age >= 1) return false;
        var reach = b.maxLen * (age < 0.55 ? age / 0.55 : 1), al = 1 - age;
        b.rays.forEach(function (r) { var x1 = b.x + Math.cos(r.a) * reach * r.lenMul, y1 = b.y + Math.sin(r.a) * reach * r.lenMul;
          var g = ctx.createLinearGradient(b.x, b.y, x1, y1);
          g.addColorStop(0, 'rgba(' + b.trip + ',0)'); g.addColorStop(0.35, 'rgba(' + b.trip + ',' + (0.75 * al) + ')'); g.addColorStop(1, 'rgba(255,255,255,0)');
          ctx.strokeStyle = g; ctx.lineWidth = Math.max(1, 6 * k * al * r.wMul); ctx.lineCap = 'round';
          ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(x1, y1); ctx.stroke();
          orb(ctx, x1, y1, 3.2 * k * al, '255,255,255', al); });
        return true; });

      // sparkle freckles — own velocity, upward drift, twinkle, shrink
      sparks = sparks.filter(function (s) { var age = (now - s.born) / s.ttl; if (age >= 1) return false;
        s.x += s.vx; s.y += s.vy; s.vy -= 0.012; var tw = 0.6 + 0.4 * Math.sin(now / 80 + s.x);
        orb(ctx, s.x, s.y, s.r * (1 - age * 0.5), COL.core, (1 - age) * tw); return true; });

      // breathing idle — a barely-there warm shimmer on the torso between cues.
      // ONLY when the kid is present (center known) and idle; out-of-frame = center null = nothing.
      if (cfg.idleBreath && !opts.active && opts.center) {
        idlePhase += 0.02; var a = (0.035 + 0.025 * (0.5 + 0.5 * Math.sin(idlePhase))) * intensity;
        orb(ctx, opts.center.x, opts.center.y, cfg.coreR * k * 2.4, COL.gold, a);
      }

      ctx.globalCompositeOperation = 'source-over';

      // 2) DIRECTION CHEVRON — top 9% strip ONLY, never on the body
      if (cfg.chevron && opts.active && opts.dir) {
        var ang = opts.dir === 'left' ? Math.PI : opts.dir === 'right' ? 0 : -Math.PI / 2;
        ctx.globalCompositeOperation = 'lighter';
        chevron(ctx, W * 0.5, H * 0.09, ang, k, trip, now);
        ctx.globalCompositeOperation = 'source-over';
      }
    }

    // anticipation pre-glow — faint orb on a target ~400ms before the cue fires
    function preGlow(target, k, now) {
      if (!target) return;
      ctx.globalCompositeOperation = 'lighter';
      var a = 0.18 + 0.12 * Math.sin(now / 220);
      orb(ctx, target.x, target.y, cfg.coreR * k * 1.6, COL.gold, a);
      ctx.globalCompositeOperation = 'source-over';
    }

    return { render: render, hit: hit, reset: reset, preGlow: preGlow, cfg: cfg };
  }

  // per-game presets (same engine, different config)
  var PRESETS = {
    upgroove:   { mode: 'isolation', nodes: 8,  burstOnHit: true,  coreR: 15, intensity: 1.0 },
    handwave:   { mode: 'travel',    nodes: 22, bloomOnVertex: true, coreR: 16, intensity: 1.0 },
    hellohello: { mode: 'calm',      nodes: 12, burstOnHit: true,  coreR: 14, intensity: 0.62,
                  waveAmp: 9, sparkScale: 0.5, headWidth: 12, sparkPerVel: 0.35 }
  };

  root.NovaLight = { create: create, PRESETS: PRESETS, COL: COL, _qcolor: qcolor };
})(typeof window !== 'undefined' ? window : this);
