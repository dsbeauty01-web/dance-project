/**
 * Voice-proof (Guardian Part 4): load a live game page from the pod in headless Chrome
 * with a fake camera + fake mic, let the song run so Nova speaks, then export the
 * page's full-text Nova lines (window.__novaJSONL) to a JSONL file for audit_transcript.py.
 *
 * Usage: node voice_proof.js <url> <seconds> <out.jsonl>
 */
const { chromium } = require('playwright-core');
const fs = require('fs'), path = require('path');
const Y4M = path.join(__dirname, '..', 'fakecam.y4m');

(async () => {
  const url = process.argv[2];
  const secs = parseInt(process.argv[3] || '95', 10);
  const out = process.argv[4] || 'nova.jsonl';

  const args = ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
    '--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader','--use-gl=angle'];
  if (fs.existsSync(Y4M)) args.push('--use-file-for-fake-video-capture=' + Y4M);

  const b = await chromium.launch({ channel: 'chrome', headless: true, args });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1080, height: 1920 } });
  const pg = await ctx.newPage();
  const t0 = Date.now();
  pg.on('console', m => { const t = m.text();
    if (/INTRO|ACK|persona|nova-said|PERSONA|awake|alive|error|GATE/i.test(t))
      console.log(`  +${((Date.now()-t0)/1000).toFixed(1)}s ${t.slice(0,140)}`); });

  console.log('LOAD', url);
  await pg.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await pg.waitForTimeout(1500);

  // tap any obvious start/enter/ready control (best-effort; the page mostly auto-starts)
  for (const sel of ['#arrival-start-btn','#start','#start-btn','#play','#enter','button']) {
    try { const el = await pg.$(sel); if (el) { await el.click({ timeout: 800 }); console.log('clicked', sel); break; } } catch(_){}
  }
  console.log(`--- watching ${secs}s (forcing ready-gate until song runs) ---`);
  let started = false;
  for (let i = 0; i < secs; i += 5) {
    if (!started) {
      // the ready-gate waits for a spoken "yes"/tap; force it so the song starts headless
      await pg.click('#ready-btn').catch(()=>{});
      await pg.evaluate(() => { try { if (window.Ready && Ready.hit) Ready.hit(); } catch(_){} }).catch(()=>{});
    }
    await pg.waitForTimeout(5000);
    const st = await pg.evaluate(() => ({
      n: (window.__NOVA_LINES||[]).length,
      running: !!(window.G && window.G.running),
      songT: (window.Music && Music.t) ? +Music.t().toFixed(1) : -1,
    })).catch(()=>({n:0,running:false,songT:-1}));
    if (st.running) started = true;
    if (i % 15 === 0 || st.running) console.log(`  t=${i}s lines=${st.n} running=${st.running} songT=${st.songT}`);
  }

  const jsonl = await pg.evaluate(() => (window.__novaJSONL ? window.__novaJSONL() : '')).catch(()=> '');
  fs.writeFileSync(out, jsonl);
  const lines = jsonl.split('\n').filter(Boolean).length;
  console.log(`WROTE ${out} — ${lines} nova lines`);
  await pg.screenshot({ path: out.replace(/\.jsonl$/, '') + '.png' }).catch(()=>{});
  await b.close();
})().catch(e => { console.error('PROBE ERROR', e.message); process.exit(2); });
