// HE-LIVE-PROBE — G2 evidence: drive ONE real Hebrew session against the DEPLOYED
// worker (novapython.onrender.com) and capture her actual spoken lines (NOVA-SAID
// packets) + the gender-chip flow. Local page, prod brain. Typed chat is the
// proven input path (fake mic carries no real speech).
// Usage: node tools/he-live-probe.js
const { chromium } = require('playwright-core');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(__dirname, 'he-shots');
const PORT = 8792;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mp4': 'video/mp4', '.mp3': 'audio/mpeg' };
const HEB = /[֐-׿]/;

function startServer() {
  return new Promise(resolve => {
    const s = http.createServer((req, res) => {
      const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]).replace(/^\//, ''));
      fs.readFile(p, (err, buf) => {
        if (err) { res.writeHead(404); res.end(); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
        res.end(buf);
      });
    });
    s.listen(PORT, () => resolve(s));
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function novaLines(page) {
  return page.evaluate(() => (window.__LOG_BUFFER || [])
    .filter(l => ['NOVA-SAID', 'HEARD', 'SAY', 'CLIP', 'UI', 'BADGE'].includes(l.tag))
    .map(l => `[${l.t}s] [${l.tag}] ${l.msg}`));
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const server = await startServer();
  const browser = await chromium.launch({ channel: 'chrome', headless: false,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
           '--autoplay-policy=no-user-gesture-required', '--window-position=40,40', '--window-size=1380,840'] });
  const ctx = await browser.newContext({ permissions: ['camera', 'microphone'], viewport: { width: 1366, height: 768 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => console.log('PAGEERROR', String(e).slice(0, 200)));

  console.log('>>> loading he page against PROD worker');
  await page.goto(`http://localhost:${PORT}/nova-joined.html?lang=he`, { waitUntil: 'domcontentloaded' });
  await sleep(4000); // prefetch create-session (cold start pre-warm fires too)

  // tap the orb → dispatch + connect
  await page.evaluate(() => window.onArrivalTap());
  console.log('>>> orb tapped — waiting for her first word (cold start can be 30-90s)');
  const spoke = await page.waitForFunction(
    () => !!window.__firstWordMs || !!window.__novaSpeakingNow,
    undefined, { timeout: 150000 }).then(() => true).catch(() => false);
  console.log('first word:', spoke);
  await sleep(6000); // let the greet finish
  await page.screenshot({ path: path.join(OUT, 'live-1-greet.png') });

  // typed name: שוקי
  await page.evaluate(() => {
    const inp = document.getElementById('rec-input');
    inp.value = 'שוקי';
    window.sendChat();
  });
  console.log('>>> typed name שוקי');
  await sleep(12000);
  await page.screenshot({ path: path.join(OUT, 'live-2-name.png') });

  // gender chip should appear (worker packet) — wait, then answer BOY
  const chip = await page.waitForSelector('#gender-chips', { timeout: 25000 }).then(() => true).catch(() => false);
  console.log('gender chips visible:', chip);
  await page.screenshot({ path: path.join(OUT, 'live-3-genderchip.png') });
  if (chip) {
    await sleep(5000);  // let her chip question land
    await page.evaluate(() => {
      const b = document.querySelector('#gender-chips button');   // first = boy
      if (b) b.click();
    });
    console.log('>>> tapped ילד');
    await sleep(12000);
  }
  await page.screenshot({ path: path.join(OUT, 'live-4-gendered.png') });

  // one more exchange to see the gendered register, then push to the picker
  await page.evaluate(() => { const i = document.getElementById('rec-input'); i.value = 'אני מוכן'; window.sendChat(); });
  await sleep(14000);
  await page.evaluate(() => window.goToPicker());
  await sleep(2500);
  await page.screenshot({ path: path.join(OUT, 'live-5-picker.png') });

  const lines = await novaLines(page);
  const transcript = lines.join('\n');
  fs.writeFileSync(path.join(OUT, 'live-transcript.txt'), transcript);
  console.log('───────── TRANSCRIPT (NOVA-SAID / HEARD) ─────────');
  console.log(lines.filter(l => l.includes('NOVA-SAID') || l.includes('HEARD') || l.includes('gender')).join('\n') || '(none captured)');
  console.log('──────────────────────────────────────────────────');
  const saidLines = lines.filter(l => l.includes('NOVA-SAID'));
  const hebSaid = saidLines.filter(l => HEB.test(l));
  const engSaid = saidLines.filter(l => !HEB.test(l) && /[a-zA-Z]{4,}/.test(l.split('] ').pop() || ''));
  console.log(`NOVA-SAID: ${saidLines.length} lines · Hebrew: ${hebSaid.length} · English-looking: ${engSaid.length}`);
  console.log('VERDICT:', (spoke && saidLines.length && hebSaid.length && !engSaid.length) ? 'PASS' : 'CHECK MANUALLY');

  await browser.close();
  server.close();
})();
