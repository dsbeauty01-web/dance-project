// LIVE 4-GAME TEST (2026-07-06): real Nova (voiceonly), fake cam person who barely moves.
// Per game: auto-tap, let the DIRECT-GAME flow run the FULL song + goodbye; record
// layout metrics, Nova speaking windows, duck levels, phase timings, screenshots.
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', Y4M = path.join(__dirname, 'fakecam.y4m');
const OUT = 'C:/Users/ADMIN/projects/dance-project/tools/live-out';
fs.mkdirSync(OUT, { recursive: true });
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.css':'text/css','.mp3':'audio/mpeg','.riv':'application/octet-stream','.wav':'audio/wav' };
const GAMES = [ { id:'wave', dur:28.5 }, { id:'joined', dur:84 }, { id:'hello', dur:111 } ];

(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-app.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const results = [];

  for (const g of GAMES) {
    console.log(`\n═══ GAME: ${g.id} ═══`);
    const b = await chromium.launch({ channel: 'chrome', headless: false, args: ['--start-maximized','--mute-audio=false',
      '--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
      '--use-file-for-fake-video-capture=' + Y4M,
      '--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });
    const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1600, height: 900 } });
    const pg = await ctx.newPage();
    const rec = { game: g.id, phases: [], speakWindows: [], shots: [], layout: null, duck: [], t0: Date.now() };
    try {
      await pg.goto(`http://localhost:${port}/nova-app.html?voiceonly&game=${g.id}`, { waitUntil: 'domcontentloaded' });
      await pg.waitForTimeout(3500);
      await pg.click('#arrival-start-btn', { force: true }).catch(()=>{});
      // watcher loop: sample every 500ms until end screen or hard timeout
      const cap = (g.dur + 150) * 1000;
      let lastPhase = '', speakOn = null, songT0 = null, sawEnd = false, shotMid = false, shotLate = false;
      const t0 = Date.now();
      while (Date.now() - t0 < cap) {
        const s = await pg.evaluate(() => ({
          phase: (window.memory && memory.phase) || '?',
          speaking: !!window.__novaSpeakingNow,
          vol: (window._audio && window._audio.volume) || null,
          endShown: !!window.__endScreenShown,
          songT: (window._audio && window._audio.currentTime) || 0,
        })).catch(() => null);
        if (!s) break;
        const el = ((Date.now() - t0) / 1000).toFixed(1);
        if (s.phase !== lastPhase) { rec.phases.push({ t: +el, phase: s.phase }); console.log(`  [${el}s] phase → ${s.phase}`); lastPhase = s.phase; }
        if (s.phase === 'song' && songT0 === null && s.songT > 0.1) songT0 = +el;
        if (s.speaking && speakOn === null) speakOn = +el;
        if (!s.speaking && speakOn !== null) { rec.speakWindows.push([speakOn, +el]); speakOn = null; }
        if (s.speaking && s.vol !== null) rec.duck.push(+s.vol.toFixed(2));
        if (s.phase === 'song' && songT0 !== null) {
          const st = s.songT;
          if (!shotMid && st > g.dur * 0.3) { shotMid = true;
            const f = `${g.id}-mid.png`; await pg.screenshot({ path: path.join(OUT, f) }); rec.shots.push(f);
            rec.layout = await pg.evaluate(() => { const n = document.getElementById('nova-side'), c = document.getElementById('cam-side');
              return { novaW: n && n.clientWidth, camW: c && c.clientWidth }; });
            console.log(`  [${el}s] mid screenshot · layout ${JSON.stringify(rec.layout)}`); }
          if (!shotLate && st > g.dur * 0.8) { shotLate = true;
            const f = `${g.id}-late.png`; await pg.screenshot({ path: path.join(OUT, f) }); rec.shots.push(f); }
        }
        if (s.endShown && !sawEnd) { sawEnd = true;
          rec.phases.push({ t: +el, phase: 'END-SCREEN-SHOWN' });
          const f = `${g.id}-end.png`; await pg.screenshot({ path: path.join(OUT, f) }); rec.shots.push(f);
          console.log(`  [${el}s] END SCREEN visible → shot`);
          await pg.waitForTimeout(3000); break; }
        await pg.waitForTimeout(500);
      }
      if (!sawEnd) { const f = `${g.id}-timeout.png`; await pg.screenshot({ path: path.join(OUT, f) }).catch(()=>{}); rec.shots.push(f); console.log('  (no end screen before timeout)'); }
      rec.duckMin = rec.duck.length ? Math.min(...rec.duck) : null;
      rec.speakCount = rec.speakWindows.length;
      console.log(`  speak windows: ${rec.speakWindows.length} · min song volume: ${rec.duckMin}`);
    } catch (e) { console.log('  ERROR:', e.message); rec.error = e.message; }
    results.push(rec);
    await b.close();
    await new Promise(r => setTimeout(r, 4000));   // let the worker session close cleanly
  }
  fs.writeFileSync(path.join(OUT, 'browser-results.json'), JSON.stringify(results, null, 1));
  console.log('\nDONE — browser-results.json written');
  server.close(); process.exit(0);
})();
