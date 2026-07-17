// QA — ENDINGS (2026-07-17 Phase 2): the 3 ending paths on the fast game (wave, 28.5s)
// against the LIVE worker, plus the audit bug checks:
//   A) natural end  → her goodbye lines, goodbye-done → end screen, truthful stars,
//                     tease text (bug: "freeze" not pickable?), JSON auto-download?
//   B) early exit ✕ → what she says on an aborted game (tone), end screen state
//   C) play-again   → joy line + fast re-transition (no goodbye)
//   D) double-hype  → count her lines between pick and go-line
// Usage: node tools/qa-endings.js
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..');
const Y4M = path.join(__dirname, 'fakecam.y4m');
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.css':'text/css','.mp3':'audio/mpeg','.riv':'application/octet-stream','.wav':'audio/wav' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const say = s => { out.push(s); console.log(s); };

(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]);
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); return r.end(); }
      r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;

  const b = await chromium.launch({ channel: 'chrome', headless: false, args: ['--window-size=1500,860',
    '--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
    '--use-file-for-fake-video-capture=' + Y4M,
    '--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader'] });

  async function boot(tag) {
    const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1440, height: 800 } });
    const page = await ctx.newPage();
    const lines = [];       // her nova-said lines with timestamps
    const downloads = [];
    page.on('download', d => downloads.push(d.suggestedFilename()));
    page.on('console', m => { const t = m.text();
      const x = /\[NOVA-SAID\] "(.*)"/.exec(t); if (x) lines.push({ t: Date.now(), text: x[1] });
      if (/goodbye-done|end screen|ENDING|play-again/.test(t)) lines.push({ t: Date.now(), text: '<<' + t.slice(0, 90) });
    });
    // auto-accept the exit confirm() dialog
    page.on('dialog', d => d.accept());
    await page.goto(`http://localhost:${port}/nova-app.html?voiceonly&game=wave`, { waitUntil: 'domcontentloaded' });
    await sleep(3000);
    await page.click('#arrival-start-btn', { force: true }).catch(()=>{});
    // DIRECT-GAME flow: reveal → auto-pick wave → transition → game
    await page.waitForFunction(() => (document.querySelector('.phase.active')||{}).id === 'phase-game', undefined, { timeout: 120000 });
    say(`[${tag}] game started`);
    return { ctx, page, lines, downloads };
  }

  // ── A) NATURAL END ──────────────────────────────────────────────
  {
    const { ctx, page, lines, downloads } = await boot('A');
    const gameStartAt = Date.now();
    await page.waitForFunction(() => (document.querySelector('.phase.active')||{}).id === 'phase-end', undefined, { timeout: 120000 }).catch(()=>{});
    say('[A] reached end phase — waiting out the goodbye…');
    await sleep(32000);   // goodbye 16-26s + stars
    const end = await page.evaluate(() => ({
      title: (document.getElementById('end-title')||{}).textContent,
      stars: (document.getElementById('end-stars')||{}).textContent,
      pts: (document.getElementById('end-pts')||{}).textContent,
      detail: (document.getElementById('end-detail')||{}).textContent,
      shown: !!window.__endScreenShown,
    }));
    say('[A] end screen: ' + JSON.stringify(end));
    say('[A] her lines during song+goodbye:');
    for (const l of lines) say('    ' + l.text.slice(0, 100));
    say('[A] downloads fired: ' + (downloads.join(', ') || 'none'));
    await page.screenshot({ path: path.join(__dirname, 'shot-end-natural.png') });
    await ctx.close();
  }

  // ── B) EARLY EXIT ✕ at ~8s ──────────────────────────────────────
  {
    const { ctx, page, lines, downloads } = await boot('B');
    await sleep(8000);
    await page.click('#game-exit-btn', { force: true });
    say('[B] exit tapped at ~8s (confirm auto-accepted)');
    await sleep(30000);
    const end = await page.evaluate(() => ({
      phase: (document.querySelector('.phase.active')||{}).id,
      title: (document.getElementById('end-title')||{}).textContent,
      stars: (document.getElementById('end-stars')||{}).textContent,
      pts: (document.getElementById('end-pts')||{}).textContent,
      shown: !!window.__endScreenShown,
    }));
    say('[B] after exit: ' + JSON.stringify(end));
    say('[B] her lines after exit:');
    const exitAt = lines.length;
    for (const l of lines.slice(-8)) say('    ' + l.text.slice(0, 100));
    say('[B] downloads fired: ' + (downloads.join(', ') || 'none'));
    await page.screenshot({ path: path.join(__dirname, 'shot-end-abort.png') });
    await ctx.close();
  }

  // ── C) PLAY-AGAIN after natural end ─────────────────────────────
  {
    const { ctx, page, lines } = await boot('C');
    await page.waitForFunction(() => (document.querySelector('.phase.active')||{}).id === 'phase-end', undefined, { timeout: 120000 }).catch(()=>{});
    await page.waitForFunction(() => !!window.__endScreenShown, undefined, { timeout: 40000 }).catch(()=>{});
    const btn = await page.evaluate(() => { const b = document.getElementById('end-replay2') || document.querySelector('[onclick*="playAgainNow"]'); if (b) { b.click(); return true; } return false; });
    say('[C] play-again tapped: ' + btn);
    const backIn = await page.waitForFunction(() => (document.querySelector('.phase.active')||{}).id === 'phase-game', undefined, { timeout: 60000 }).then(()=>true).catch(()=>false);
    say('[C] back in game: ' + backIn);
    say('[C] her lines around play-again:');
    for (const l of lines.slice(-6)) say('    ' + l.text.slice(0, 100));
    await ctx.close();
  }

  await b.close(); server.close();
  fs.writeFileSync(path.join(__dirname, 'endings-report.txt'), out.join('\n'));
  console.log('\nreport → tools/endings-report.txt');
  process.exit(0);
})();
