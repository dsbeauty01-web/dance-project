const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');

const ROOT = 'C:/Users/ADMIN/projects/dance-project';
const SCR = __dirname;
const Y4M = path.join(SCR, 'fakecam.y4m');
const TARGET = process.argv[2] || 'nova-wave.html';
const CUES = (process.argv[3] || 'wrist-wave,elbow-pump,shoulder-roll,free').split(',');

const MIME = { '.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.mp4':'video/mp4',
  '.png':'image/png','.jpg':'image/jpeg','.riv':'application/octet-stream','.json':'application/json',
  '.css':'text/css','.wav':'audio/wav','.mp3':'audio/mpeg','.webm':'video/webm','.svg':'image/svg+xml' };

(async () => {
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p === '/') p = '/' + TARGET;
    const fp = path.join(ROOT, p);
    fs.readFile(fp, (e, d) => {
      if (e) { res.writeHead(404); res.end('nf'); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(fp).toLowerCase()] || 'application/octet-stream' });
      res.end(d);
    });
  });
  await new Promise(r => server.listen(0, r));
  const port = server.address().port;
  console.log('server on', port, 'target', TARGET);

  const browser = await chromium.launch({
    channel: 'chrome', headless: true,
    args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
      '--use-file-for-fake-video-capture=' + Y4M, '--autoplay-policy=no-user-gesture-required',
      '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--use-gl=angle']
  });
  const ctx = await browser.newContext({ permissions: ['camera', 'microphone'], viewport: { width: 1100, height: 780 } });
  const page = await ctx.newPage();
  page.on('console', m => { const t = m.text(); if (!/Download the React|favicon/.test(t)) console.log('[pg]', t); });
  page.on('pageerror', e => console.log('[pg-err]', e.message));

  await page.goto(`http://localhost:${port}/${TARGET}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(800);
  await page.click('#start-btn').catch(e => console.log('no start-btn', e.message));

  // wait for the pose model + fake camera to be live
  let ready = false;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1000);
    const s = await page.evaluate(() => ({
      pose: typeof poseLoop === 'function',
      camW: document.getElementById('cam') ? document.getElementById('cam').videoWidth : 0,
    }));
    if (s.camW > 0 && s.pose) { ready = true; console.log('ready after', i + 1, 's  camW=', s.camW); break; }
  }
  if (!ready) console.log('WARN: not fully ready, proceeding anyway');

  // force into the game view + start the pose loop, bypassing intro/greet/warmup
  await page.evaluate(() => {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    const g = document.getElementById('game'); if (g) g.classList.remove('hidden');
    try { if (typeof poseLoop === 'function') poseLoop(); } catch (e) {}
  });
  await page.waitForTimeout(1500);

  for (const cue of CUES) {
    // poll until tracking actually locks an aura on (cartoon loops; some frames lose her)
    let onCount = 0;
    for (let t = 0; t < 40; t++) {
      await page.evaluate(c => { window.__cuePart = c; }, cue);
      await page.waitForTimeout(150);
      onCount = await page.evaluate(() => document.querySelectorAll('#aura-layer .aura.on').length);
      if (onCount > 0) break;
    }
    await page.waitForTimeout(250);
    const el = await page.$('#cam-wrap');
    const out = path.join(SCR, 'shot_' + TARGET.replace('.html', '') + '_' + cue + '.png');
    if (el) await el.screenshot({ path: out });
    // read back what the overlay actually computed for this cue
    const diag = await page.evaluate(() => {
      const auras = [...document.querySelectorAll('#aura-layer .aura')].map(a => ({
        on: a.classList.contains('on'),
        x: a.style.getPropertyValue('--x'), y: a.style.getPropertyValue('--y'), size: a.style.getPropertyValue('--size'),
        arrow: a.querySelector('.arrow') ? a.querySelector('.arrow').textContent : ''
      })).filter(a => a.on);
      return { cuePart: window.__cuePart, auras };
    });
    console.log('CUE', cue, '->', JSON.stringify(diag));
  }

  await browser.close();
  server.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
