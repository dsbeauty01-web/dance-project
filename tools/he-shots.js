// HE-SHOTS — G1 evidence rig for the Hebrew layer on nova-joined.html.
// Serves the repo statically, BLOCKS the prod worker (no real sessions), walks every
// phase in ?lang=he and screenshots each at laptop (1366x768) and phone (412x915)
// widths. Also runs an English regression probe (default URL must render unchanged).
// Usage: node tools/he-shots.js
const { chromium } = require('playwright-core');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(__dirname, 'he-shots');
const PORT = 8791;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.mp4': 'video/mp4', '.mp3': 'audio/mpeg', '.png': 'image/png' };

function startServer() {
  return new Promise(resolve => {
    const s = http.createServer((req, res) => {
      const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]).replace(/^\//, '') || 'index.html');
      fs.readFile(p, (err, buf) => {
        if (err) { res.writeHead(404); res.end('nope'); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
        res.end(buf);
      });
    });
    s.listen(PORT, () => resolve(s));
  });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function prepPage(ctx, url) {
  const page = await ctx.newPage();
  page._errors = [];
  page.on('pageerror', e => page._errors.push(String(e)));
  // never touch prod from the QA rig
  await page.route('**novapython.onrender.com/**', r => r.abort());
  await page.route('**proxy.runpod.net/**', r => r.abort());
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await sleep(2500); // fonts + early cam
  return page;
}

async function shotPhases(ctx, lang, viewport, tag) {
  await ctx.newPage(); // keep ctx alive pattern
  const page = await prepPage(ctx, `http://localhost:${PORT}/nova-joined.html${lang ? '?lang=' + lang : ''}`);
  await page.setViewportSize(viewport);
  const snap = async name => {
    await sleep(500);
    await page.screenshot({ path: path.join(OUT, `${tag}-${name}.png`) });
    console.log(`  shot ${tag}-${name}.png`);
  };

  await snap('1-arrival');

  // intro overlay (the connect cover)
  await page.evaluate(() => { document.getElementById('intro-overlay').classList.add('show'); });
  await snap('2-intro-overlay');
  await page.evaluate(() => { document.getElementById('intro-overlay').classList.remove('show'); });

  // recognition + chat bubbles + name buttons + stt echo
  await page.evaluate(() => {
    window.showPhase('phase-recognition');
    window.memory.phase = 'recognition';
    const nb = window.NOVA_HE;
    const addB = (t, w) => { const d = document.createElement('div'); d.className = w === 'nova' ? 'bubble-nova' : 'bubble-kid'; d.textContent = t; document.getElementById('rec-chat-log').appendChild(d); };
    addB(nb ? 'היי היי! אני נובה — החברה הקסומה שלך! איך קוראים לך?' : "Hey hey! I'm Nova! What's your name?", 'nova');
    addB(nb ? 'שוקי' : 'Shuki', 'kid');
    addB(nb ? 'שוקי!! איזה שם מהמם! אני נובה!' : 'Shuki!! What a name! I am Nova!', 'nova');
    document.getElementById('rec-dance-btn').classList.add('ready');
    window.showNameCaptureButtons();
    document.getElementById('sees-you-tick').classList.add('show');
  });
  await page.evaluate(() => { try { window.__setNovaState && window.__setNovaState('listening'); } catch(_){} });
  await snap('3-recognition');

  // picker
  await page.evaluate(() => { window.goToPicker(); });
  await snap('4-picker');

  // transition (live bridge) — caption via TRANS beat
  await page.evaluate(() => {
    window.showPhase('phase-transition');
    try { window.transCaption ? window.transCaption('framing', 'wave') : null; } catch(_){}
    const el = document.getElementById('trans-cap'); el.classList.add('show');
  });
  await snap('5-transition');

  // countdown
  await page.evaluate(() => { window.showPhase('phase-countdown'); });
  await snap('6-countdown');

  // game + streak + reaction bubble + score
  await page.evaluate(() => {
    window.showPhase('phase-game');
    window.memory.phase = 'dance';
    document.getElementById('game-score').textContent = '1250';
    const st = document.getElementById('game-streak'); st.textContent = '🔥 x4'; st.classList.add('show');
    const rb = document.getElementById('reaction-bubble'); rb.classList.add('show');
    const cue = document.getElementById('action-cue'); cue.classList.add('show');
  });
  await snap('7-game');

  // pause overlay
  await page.evaluate(() => { document.getElementById('pause-overlay').classList.add('show'); });
  await snap('8-pause');
  await page.evaluate(() => { document.getElementById('pause-overlay').classList.remove('show'); });

  // freeze overlay
  await page.evaluate(() => { document.getElementById('freeze-overlay').classList.add('active'); });
  await snap('9-freeze');
  await page.evaluate(() => { document.getElementById('freeze-overlay').classList.remove('active'); });

  // end screen
  await page.evaluate(() => {
    window.showPhase('phase-end');
    document.getElementById('end-title').textContent = (window.TA ? window.TA('endTitles')[3] : 'Amazing dancer!');
    document.getElementById('end-stars').textContent = '⭐⭐⭐⭐☆';
    document.getElementById('end-pts').textContent = '1250' + (window.T ? window.T('pts') : ' pts');
    document.getElementById('end-detail').textContent = window.T ? window.T('endDetail', { hits: 7, attempts: 9, streak: 4 }) : '7 of 9';
    const who = window.NOVA_HE ? 'שוקי, ' : 'Shuki, ';
    const hooks = window.TA ? window.TA('hooks').map(h => h.split('{who}').join(who)) : ['hook'];
    document.getElementById('end-hook').textContent = hooks[0];
    document.getElementById('end-msg').textContent = window.NOVA_HE
      ? 'שוקי, הכתף שלך הייתה מהירה בטירוף! ביי ביי, כוכב שלי!' : 'Shuki, your shoulder was SO fast! Bye bye my star!';
  });
  await snap('10-end');

  // retry UI + audio unlock
  await page.evaluate(() => { window.__retryNova ? null : null; const f = document.createElement('div'); });
  await page.evaluate(() => { try { showNovaRetryUI(); } catch(_) { try { window.showNovaRetryUI(); } catch(__){} } });
  await page.evaluate(() => {
    const b = document.getElementById('audio-unlock-btn'); if (b) b.style.display = 'flex';
  });
  await snap('11-retry-unlock');

  const errors = page._errors.slice();
  const probe = await page.evaluate(() => ({
    dir: document.documentElement.getAttribute('dir'),
    lang: document.documentElement.getAttribute('lang'),
    title: document.title,
    tagline: document.getElementById('arrival-tagline').textContent,
    danceBtn: document.getElementById('rec-dance-btn').textContent,
    sttLang: (window.recognition && window.recognition.lang) || null,
    font: getComputedStyle(document.getElementById('arrival-tagline')).fontFamily,
  }));
  await page.close();
  return { errors, probe };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const server = await startServer();
  const browser = await chromium.launch({ channel: 'chrome', headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
           '--autoplay-policy=no-user-gesture-required', '--window-position=40,40', '--window-size=1400,860'] });
  const ctx = await browser.newContext({ permissions: ['camera', 'microphone'], viewport: { width: 1366, height: 768 } });

  console.log('>>> HEBREW laptop pass (1366x768)');
  const he = await shotPhases(ctx, 'he', { width: 1366, height: 768 }, 'he-laptop');
  console.log('HE probe:', JSON.stringify(he.probe, null, 1));
  console.log('HE page errors:', he.errors.length ? he.errors : 'none');

  console.log('>>> HEBREW 412px pass');
  const heM = await shotPhases(ctx, 'he', { width: 412, height: 915 }, 'he-412');
  console.log('HE-412 page errors:', heM.errors.length ? heM.errors : 'none');

  console.log('>>> ENGLISH regression pass (default URL, no ?lang)');
  // must clear the persisted localStorage from the he passes — default URL must be EN
  const pageClear = await ctx.newPage();
  await pageClear.goto(`http://localhost:${PORT}/nova-joined.html`, { waitUntil: 'domcontentloaded' }).catch(()=>{});
  await pageClear.evaluate(() => localStorage.removeItem('nova-lang')).catch(()=>{});
  await pageClear.close();
  const en = await shotPhases(ctx, '', { width: 1366, height: 768 }, 'en-laptop');
  console.log('EN probe:', JSON.stringify(en.probe, null, 1));
  console.log('EN page errors:', en.errors.length ? en.errors : 'none');

  const enOk = en.probe.dir !== 'rtl' && en.probe.title === 'Nova Joins! · 4-Point Isolation Game'
    && en.probe.tagline === 'Hey friend... ready to dance?' && en.probe.danceBtn.includes("Let's Dance!");
  const heOk = he.probe.dir === 'rtl' && he.probe.lang === 'he' && he.probe.title === 'נובה דאנס'
    && he.probe.tagline.includes('נובה') && he.probe.danceBtn.includes('יאללה');
  console.log('EN regression:', enOk ? 'PASS' : 'FAIL', '· HE apply:', heOk ? 'PASS' : 'FAIL');

  await browser.close();
  server.close();
  process.exit(enOk && heOk && !he.errors.length && !en.errors.length ? 0 : 1);
})();
