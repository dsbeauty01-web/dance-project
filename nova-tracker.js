/* ============================================================================
 * nova-tracker.js — SMART SESSION TRACKER (the improve-each-session loop)
 * Add <script src="nova-tracker.js"></script> and open with ?track. It silently
 * records a real play session, then a 📊 button opens a report you DOWNLOAD and send me:
 *
 *   • per-cue VISUAL SNAPSHOTS — camera + the light overlay composited (so I can SEE
 *     exactly where the gold light landed on the real body for each move).
 *   • per-cue DATA — cue, hit/miss, quality, timing drift, the live detection values,
 *     and whether the cued joint was actually tracked (light shown) or dropped.
 *   • per-JOINT detection reliability — % of frames each joint was confidently seen
 *     (≥0.5). This is what tells us which moves the camera can/can't see in this room.
 *   • FRAMING quality — % present, shoulder-span fraction (too close / too far).
 *   • a SUMMARY + a contact-sheet PNG of all snapshots.
 *
 * Reads (exposed by the games): window.__lastPoseKeypoints, window.__novaDet(),
 *   window.__cuePart, window.__cueState, window.__anchorsDbg. Finds the camera (#cam/
 *   #webcam) + overlay (#overlay/#fx/#aura-canvas) itself. Local-only until you download.
 * ========================================================================== */
(function () {
  'use strict';
  if (!/[?&]track/.test(location.search)) return;

  var GAME = (document.title || location.pathname).replace(/[^a-z0-9]+/gi, '-').toLowerCase().slice(0, 40);
  var T0 = performance.now();
  var S = { game: GAME, url: location.href, started: new Date().toISOString(), cues: [], frames: 0, present: 0,
            jointSum: {}, jointSeen: {}, spanSum: 0, spanN: 0 };
  var JOINTS = ['nose','left_ear','right_ear','left_shoulder','right_shoulder','left_elbow','right_elbow',
                'left_wrist','right_wrist','left_hip','right_hip','left_knee','right_knee'];
  JOINTS.forEach(function (j) { S.jointSum[j] = 0; S.jointSeen[j] = 0; });

  function cam() { return document.getElementById('cam') || document.getElementById('webcam'); }
  function overlay() { return document.getElementById('overlay') || document.getElementById('fx') || document.getElementById('aura-canvas'); }

  // composite camera frame + light overlay into a small thumbnail dataURL (mirror like the game)
  function snapshot(maxW) {
    var v = cam(), ov = overlay(); if (!v || !v.videoWidth) return null;
    var w = maxW || 240, h = Math.round(w * (v.videoHeight / v.videoWidth));
    var c = document.createElement('canvas'); c.width = w; c.height = h; var x = c.getContext('2d');
    x.save(); x.translate(w, 0); x.scale(-1, 1);                 // selfie mirror
    try { x.drawImage(v, 0, 0, w, h); } catch (e) {}
    if (ov && ov.width) { try { x.drawImage(ov, 0, 0, w, h); } catch (e) {} }   // light on top
    x.restore();
    try { return c.toDataURL('image/jpeg', 0.55); } catch (e) { return null; }
  }

  // running per-joint confidence + framing, sampled every frame
  var lastCueKey = null, cueOpenT = 0, cueResolvedFor = null;
  function sample() {
    var kps = window.__lastPoseKeypoints, d = (typeof window.__novaDet === 'function') ? window.__novaDet() : null;
    if (kps) { S.frames++;
      var present = false;
      kps.forEach(function (k) { if (S.jointSum[k.name] != null) { S.jointSum[k.name] += (k.score || 0); if ((k.score || 0) >= 0.5) S.jointSeen[k.name]++; } });
      if (d) { if (d.present) { S.present++; present = true; } if (d.spanFrac) { S.spanSum += d.spanFrac; S.spanN++; } }
    }
    // cue lifecycle → capture on open + on resolve (hit/miss)
    var cue = window.__cuePart || '', state = window.__cueState || '';
    if (cue && cue !== lastCueKey) { lastCueKey = cue; cueOpenT = performance.now(); cueResolvedFor = null; }
    if (!cue) lastCueKey = null;
    if (cue && (state === 'hit' || state === 'streak' || state === 'miss') && cueResolvedFor !== cue + cueOpenT) {
      cueResolvedFor = cue + cueOpenT;
      var anchors = window.__anchorsDbg || [];
      var dd = (typeof window.__novaDet === 'function') ? window.__novaDet() : {};
      S.cues.push({
        t: +((performance.now() - T0) / 1000).toFixed(2),
        cue: cue, result: (state === 'miss' ? 'miss' : 'hit'), state: state,
        lightShown: anchors.length > 0,                 // was the cued joint tracked enough to light?
        anchors: anchors.length,
        det: dd ? { present: dd.present, joints: dd.joints, headDX: r2(dd.headDX), shTilt: r2(dd.shTilt), hipDX: r2(dd.hipDX), motion: r2(dd.motion), spanFrac: r2(dd.spanFrac) } : null,
        shot: S.cues.length < 40 ? snapshot(240) : null  // cap snapshots (size)
      });
      if (panelOpen) renderReport();
    }
  }
  function r2(v) { return v == null ? null : +(+v).toFixed(2); }
  setInterval(sample, 150);

  // ---------- analytics ----------
  function analyze() {
    var hits = S.cues.filter(function (c) { return c.result === 'hit'; }).length;
    var shown = S.cues.filter(function (c) { return c.lightShown; }).length;
    var byMove = {};
    S.cues.forEach(function (c) { var key = c.cue.replace(/-(left|right)$/, ''); (byMove[key] = byMove[key] || { n: 0, hit: 0, shown: 0 }); byMove[key].n++; if (c.result === 'hit') byMove[key].hit++; if (c.lightShown) byMove[key].shown++; });
    var joints = {}; JOINTS.forEach(function (j) { joints[j] = S.frames ? Math.round(100 * S.jointSeen[j] / S.frames) : 0; });
    return {
      cues: S.cues.length, hits: hits, hitRate: S.cues.length ? Math.round(100 * hits / S.cues.length) : 0,
      lightShownRate: S.cues.length ? Math.round(100 * shown / S.cues.length) : 0,
      presentRate: S.frames ? Math.round(100 * S.present / S.frames) : 0,
      avgSpanFrac: S.spanN ? +(S.spanSum / S.spanN).toFixed(3) : 0,
      byMove: byMove, jointSeenPct: joints
    };
  }

  // ---------- report panel ----------
  var panel, panelOpen = false, btn;
  function fab() { btn = document.createElement('button'); btn.id = 'nova-track-fab'; btn.textContent = '📊';
    btn.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:99998;width:54px;height:54px;border-radius:50%;border:2px solid #ffd27a;background:#1c1230;color:#fff;font-size:24px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.5)';
    btn.onclick = openReport; document.body.appendChild(btn);
  }
  function openReport() { panelOpen = true; if (!panel) { panel = document.createElement('div'); panel.id = 'nova-track-panel'; document.body.appendChild(panel); } renderReport(); }
  function renderReport() {
    var a = analyze();
    var pct = function (v) { return '<b style="color:' + (v >= 70 ? '#7CFFB0' : v >= 40 ? '#ffd27a' : '#ff7a6b') + '">' + v + '%</b>'; };
    var moves = Object.keys(a.byMove).map(function (k) { var m = a.byMove[k]; return '<tr><td>' + k + '</td><td>' + m.n + '</td><td>' + Math.round(100 * m.hit / m.n) + '%</td><td>' + Math.round(100 * m.shown / m.n) + '%</td></tr>'; }).join('');
    var jr = JOINTS.map(function (j) { var v = a.jointSeenPct[j]; return '<span style="display:inline-block;width:120px">' + j.replace('_', ' ') + ' ' + pct(v) + '</span>'; }).join('');
    var shots = S.cues.filter(function (c) { return c.shot; }).map(function (c) {
      return '<div style="display:inline-block;text-align:center;margin:3px"><img src="' + c.shot + '" style="width:120px;border:2px solid ' + (c.result === 'hit' ? '#7CFFB0' : '#ff7a6b') + ';border-radius:8px"><div style="font:11px system-ui;color:#aeb9cd">' + c.cue + (c.lightShown ? '' : ' ⚠️no-light') + '</div></div>';
    }).join('');
    panel.innerHTML =
      '<style>#nova-track-panel{position:fixed;inset:0;z-index:99999;background:#0a0612f5;color:#e7ecf5;font:13px/1.5 system-ui;overflow:auto;padding:14px 14px 80px}' +
      '#nova-track-panel h1{font-size:17px;color:#ffd27a;margin:0 0 8px}#nova-track-panel h2{font-size:13px;color:#9fd0ff;margin:14px 0 4px;text-transform:uppercase;letter-spacing:.5px}' +
      '#nova-track-panel table{border-collapse:collapse;width:100%;max-width:420px}#nova-track-panel td,#nova-track-panel th{border:1px solid #243049;padding:3px 8px;text-align:left}' +
      '#nova-track-panel .bar{position:fixed;left:0;right:0;bottom:0;background:#0d1320;border-top:1px solid #243049;padding:10px;display:flex;gap:8px;flex-wrap:wrap}' +
      '#nova-track-panel button{background:#1c2740;color:#fff;border:1px solid #34507e;border-radius:8px;padding:9px 13px;font:600 13px system-ui;cursor:pointer}</style>' +
      '<h1>📊 Nova session tracker</h1>' +
      '<div>game: <b>' + S.game + '</b> · cues recorded: <b>' + a.cues + '</b> · frames: ' + S.frames + '</div>' +
      '<h2>summary</h2>' +
      '<div>hit rate ' + pct(a.hitRate) + ' · light-on-body rate ' + pct(a.lightShownRate) + ' · in-frame ' + pct(a.presentRate) + ' · avg shoulder-span ' + a.avgSpanFrac + ' (0.15–0.35 ideal)</div>' +
      '<h2>per move (count · hit% · light-shown%)</h2><table><tr><th>move</th><th>n</th><th>hit</th><th>lit</th></tr>' + (moves || '<tr><td colspan=4>none yet</td></tr>') + '</table>' +
      '<h2>joint detection reliability (% frames seen ≥0.5)</h2><div>' + jr + '</div>' +
      '<h2>snapshots — you + the light, per cue</h2><div>' + (shots || '(play a bit, then reopen)') + '</div>' +
      '<div class="bar"><button id="ntk-json">⬇ Download bundle (JSON)</button><button id="ntk-sheet">⬇ Download snapshots (PNG)</button><button id="ntk-copy">📋 Copy summary</button><button id="ntk-close">✕ Close</button></div>';
    panel.querySelector('#ntk-close').onclick = function () { panel.remove(); panel = null; panelOpen = false; };
    panel.querySelector('#ntk-json').onclick = downloadJSON;
    panel.querySelector('#ntk-sheet').onclick = downloadSheet;
    panel.querySelector('#ntk-copy').onclick = function () { try { navigator.clipboard.writeText(summaryText(a)); this.textContent = '✓ copied'; } catch (e) {} };
  }
  function summaryText(a) { return 'NOVA SESSION ' + S.game + '\n' + S.url + '\ncues ' + a.cues + ' · hit ' + a.hitRate + '% · light-on-body ' + a.lightShownRate + '% · in-frame ' + a.presentRate + '% · span ' + a.avgSpanFrac +
    '\nper move: ' + Object.keys(a.byMove).map(function (k) { var m = a.byMove[k]; return k + '(' + m.n + ',' + Math.round(100 * m.hit / m.n) + '%hit,' + Math.round(100 * m.shown / m.n) + '%lit)'; }).join(' ') +
    '\njoint seen%: ' + JOINTS.map(function (j) { return j + ':' + a.jointSeenPct[j]; }).join(' '); }
  function dl(name, url) { var a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove(); }
  function downloadJSON() { var bundle = { meta: { game: S.game, url: S.url, started: S.started, frames: S.frames }, analysis: analyze(), cues: S.cues };
    dl('nova-track-' + S.game + '.json', URL.createObjectURL(new Blob([JSON.stringify(bundle)], { type: 'application/json' }))); }
  function downloadSheet() {
    var shots = S.cues.filter(function (c) { return c.shot; }); if (!shots.length) return;
    var cols = 4, tw = 240, th = 180, pad = 6, lab = 18, rows = Math.ceil(shots.length / cols);
    var c = document.createElement('canvas'); c.width = cols * (tw + pad) + pad; c.height = rows * (th + lab + pad) + pad;
    var x = c.getContext('2d'); x.fillStyle = '#0a0612'; x.fillRect(0, 0, c.width, c.height);
    var done = 0; shots.forEach(function (s, i) { var img = new Image(); img.onload = function () {
      var cx = pad + (i % cols) * (tw + pad), cy = pad + Math.floor(i / cols) * (th + lab + pad);
      x.drawImage(img, cx, cy, tw, th); x.fillStyle = s.result === 'hit' ? '#7CFFB0' : '#ff7a6b'; x.font = '12px system-ui';
      x.fillText(s.cue + (s.lightShown ? '' : ' ⚠no-light') + ' · ' + s.result, cx + 2, cy + th + 13);
      if (++done === shots.length) dl('nova-frames-' + S.game + '.png', c.toDataURL('image/png')); };
      img.src = s.shot; });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fab); else fab();
})();
