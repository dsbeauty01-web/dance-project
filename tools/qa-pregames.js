// PREGAMES-V1 ROBOT (2026-07-17): full runs of the video-led session games
// (wavemagic / bounce) with a robot kid. Per game:
//   • cues must fire at the videomap timestamps ±200ms (read from __cueLog — video clock)
//   • the robot LANDS every window except one designated skip → expect GAME-HIT (sparkle path)
//   • the skipped window must close as a SOFT no-catch (zero handleMiss / red paths)
//   • talk-beat static check: worker TALK_SCORES beats land inside the measured gaps
//     and outside the silence zones (tables mirrored here from personality.py)
// Usage: node tools/qa-pregames.js [wavemagic|bounce|all] [nova-joined.html|nova-app.html]
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..');
const Y4M = path.join(__dirname, 'fakecam.y4m');
const OUT = path.join(__dirname, 'pregames-out');
fs.mkdirSync(OUT, { recursive: true });
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.css':'text/css','.mp3':'audio/mpeg','.riv':'application/octet-stream','.wav':'audio/wav' };

// ── the videomap tables (must mirror nova-joined.html) ──
const GAMES = {
  wavemagic: {
    dur: 80.9,
    opens: [
      { t: 38400, action: 'wristwave' },
      { t: 46500, action: 'wavefree' },   // energy detector — self-hits on any motion (by design)
      { t: 52200, action: 'wavefree' },
      { t: 59800, action: 'wristwave', skip: true },  // deliberate no-catch → must close SOFT
      { t: 70000, action: 'wavefree' },
      { t: 75200, action: 'combo' },
    ],
    // worker talk beats (personality.TALK_SCORES.wavemagic) vs the measured windows
    beats: [0.8, 5.0, 19.5, 38.8, 47.0, 59.9, 70.3, 80.0],
    gaps:  [[0, 8.5], [19.3, 22.0], [38.7, 42.0], [46.5, 58.0], [58.0, 70.0], [70.0, 80.9]],
    silence: [[8.6, 19.2], [22.5, 38.5]],
  },
  bounce: {
    dur: 73.6,
    opens: [
      { t: 14000, action: 'headbob', skip: true },    // deliberate no-catch → must be SOFT
      { t: 18200, action: 'headbob' },
      { t: 33400, action: 'shoulderroll' },
      { t: 41500, action: 'hipbounce' },
      { t: 49000, action: 'hipbounce' },
      { t: 56000, action: 'combo' },
      { t: 65700, action: 'combo' },
      { t: 71700, action: 'combo' },
    ],
    beats: [0.8, 14.0, 33.6, 42.0, 46.4, 56.2, 66.0, 73.0],
    gaps:  [[0, 5.8], [13.8, 22.7], [33.4, 45.3], [46.0, 49.0], [49.0, 55.0], [55.0, 73.6]],
    silence: [[5.8, 13.8], [22.7, 33.4]],
  },
};

const inAny = (t, ranges) => ranges.some(([a, b]) => t >= a && t <= b);

async function runGame(id, port, page) {
  const G = GAMES[id];
  console.log(`\n═══════════ GAME: ${id} (${G.dur}s) on ${page} ═══════════`);
  const fails = [];

  // ── static talk-beat check (no browser needed) ──
  for (const b of G.beats) {
    if (inAny(b, G.silence)) fails.push(`talk beat ${b}s lands INSIDE a silence zone`);
    if (!inAny(b, G.gaps))   fails.push(`talk beat ${b}s lands OUTSIDE every allowed window`);
  }
  console.log(`  talk beats: ${G.beats.length} checked → ${fails.length ? fails.join(' · ') : 'all inside the measured windows, none in silence'}`);

  const b = await chromium.launch({ channel: 'chrome', headless: false, args: ['--start-maximized','--mute-audio',
    '--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
    '--use-file-for-fake-video-capture=' + Y4M,
    '--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1600, height: 900 } });
  const pg = await ctx.newPage();
  const lines = [];
  pg.on('console', m => lines.push(m.text()));

  const rec = { hits: [], softMiss: [], hardMiss: [], shots: [] };
  try {
    await pg.goto(`http://localhost:${port}/${page}?voiceonly&debug=1&game=${id}`, { waitUntil: 'domcontentloaded' });
    await pg.waitForTimeout(3500);
    await pg.click('#arrival-start-btn', { force: true }).catch(()=>{});

    // watcher: robot lands each non-skip window ~700ms after it opens
    const cap = (G.dur + 160) * 1000, t0 = Date.now();
    let consumed = 0, endShown = false, shotKid1 = false, shotWatch = false;
    const pending = G.opens.map(o => ({ ...o, done: false }));
    while (Date.now() - t0 < cap) {
      const s = await pg.evaluate(() => ({
        end: !!window.__endScreenShown,
        songT: (window._audio && window._audio.currentTime) || 0,
        cueLog: window.__cueLog || [],
        phase: (window.memory && window.memory.phase) || '?',
      })).catch(() => null);
      if (!s) break;
      // react to newly OPENED cues
      while (consumed < s.cueLog.length) {
        const c = s.cueLog[consumed++];
        const exp = pending.find(p => !p.done && p.action === c.action && Math.abs(p.t - c.t) < 1500);
        console.log(`  [cue-open] ${c.action} @ video ${(c.t/1000).toFixed(2)}s${exp ? (exp.skip ? ' (robot SKIPS — soft check)' : ' → robot lands it') : ' (UNEXPECTED)'}`);
        if (exp) {
          exp.done = true; exp.firedAt = c.t;
          if (!exp.skip) {
            const act = c.action;
            setTimeout(() => pg.evaluate(a => { window.__testMoves = { [a]: true }; }, act).catch(()=>{}), 700);
            setTimeout(() => pg.evaluate(() => { window.__testMoves = {}; }).catch(()=>{}), 2600);
          }
        }
      }
      if (!shotWatch && s.songT > 9 && s.songT < 20) { shotWatch = true;
        const f = `${id}-watch.png`; await pg.screenshot({ path: path.join(OUT, f) }); rec.shots.push(f); }
      if (!shotKid1 && s.songT > (G.opens.find(o=>!o.skip).t/1000 + 1.2)) { shotKid1 = true;
        const f = `${id}-kidturn.png`; await pg.screenshot({ path: path.join(OUT, f) }); rec.shots.push(f); }
      if (s.end) { endShown = true; break; }
      await pg.waitForTimeout(250);
    }

    for (const l of lines) {
      if (l.includes('GAME-HIT'))                 rec.hits.push(l);
      if (l.includes('no-catch (soft'))           rec.softMiss.push(l);
      if (l.includes('MISS (current moves'))      rec.hardMiss.push(l);
    }

    // ── verdicts ──
    const expHits = G.opens.filter(o => !o.skip).length;
    let timingOk = 0;
    for (const p of pending) {
      if (p.firedAt === undefined) { fails.push(`cue ${p.action}@${p.t} NEVER FIRED`); continue; }
      const d = Math.abs(p.firedAt - p.t);
      if (d <= 200) timingOk++;
      else fails.push(`cue ${p.action}@${p.t} fired at ${p.firedAt} (Δ${d}ms > 200ms)`);
    }
    if (rec.hits.length < expHits) fails.push(`hits ${rec.hits.length}/${expHits} — a landed window did not sparkle`);
    if (rec.softMiss.length < 1)   fails.push('the skipped window did NOT close as a soft no-catch');
    if (rec.hardMiss.length > 0)   fails.push(`NEGATIVE PATH FIRED: ${rec.hardMiss.length}× handleMiss`);
    if (!endShown)                 fails.push('end screen never shown (game did not complete)');

    console.log(`  cues: ${timingOk}/${G.opens.length} within ±200ms · hits(sparkles): ${rec.hits.length}/${expHits} · soft no-catch: ${rec.softMiss.length} · handleMiss: ${rec.hardMiss.length} · end screen: ${endShown}`);
    fs.writeFileSync(path.join(OUT, `${id}-console.log`), lines.join('\n'));
  } catch (e) {
    fails.push('rig error: ' + e.message);
  } finally {
    await b.close().catch(()=>{});
  }
  console.log(fails.length ? `  ❌ FAIL:\n    - ${fails.join('\n    - ')}` : `  ✅ ${id} PASS`);
  return fails.length === 0;
}

(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const which = process.argv[2] || 'all';
  const page = process.argv[3] || 'nova-joined.html';
  const ids = which === 'all' ? Object.keys(GAMES) : [which];
  let ok = true;
  for (const id of ids) ok = (await runGame(id, port, page)) && ok;
  server.close();
  console.log(ok ? '\n✅ PREGAMES ROBOT: ALL PASS' : '\n❌ PREGAMES ROBOT: FAILURES');
  process.exit(ok ? 0 : 1);
})();
