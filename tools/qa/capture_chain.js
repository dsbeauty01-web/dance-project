/**
 * Capture groove->freeze->groove chaining live (FINALFREEZE Part 4 evidence).
 * Loads /freeze, waits for the avatar to reveal, records the page video while driving
 * set_avatar transitions: groove (nova_idlegroove_v2) <-> freeze poses, ~30s.
 * Usage: node capture_chain.js <freeze-url> <out-dir>
 */
const { chromium } = require('playwright-core');
const fs = require('fs'), path = require('path');
const Y4M = path.join(__dirname, '..', 'fakecam.y4m');

(async () => {
  const url = process.argv[2];
  const outDir = process.argv[3];
  fs.mkdirSync(outDir, { recursive: true });
  const args = ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
    '--autoplay-policy=no-user-gesture-required','--enable-unsafe-swiftshader','--use-gl=angle'];
  if (fs.existsSync(Y4M)) args.push('--use-file-for-fake-video-capture=' + Y4M);
  const b = await chromium.launch({ channel: 'chrome', headless: true, args });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 1080, height: 1920 },
    recordVideo: { dir: outDir, size: { width: 1080, height: 1920 } } });
  const pg = await ctx.newPage();
  const t0 = Date.now();
  pg.on('console', m => { const t = m.text(); if (/REVEAL|mounted|alive|avatar|error/i.test(t)) console.log(`  +${((Date.now()-t0)/1000).toFixed(1)}s ${t.slice(0,110)}`); });

  console.log('LOAD', url);
  await pg.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  for (const sel of ['#start-btn','#arrival-start-btn','button']) { try { const el = await pg.$(sel); if (el) { await el.click({ timeout: 800 }); break; } } catch(_){} }

  // wait for the avatar to actually be on screen
  console.log('--- waiting for reveal ---');
  await pg.waitForTimeout(16000);

  const drive = (id) => pg.evaluate(i => { try { return fetch(location.origin+'/set_avatar?id='+i).then(r=>r.ok); } catch(_){ return false; } }, id);
  // groove -> freeze -> groove chain, ~30s, using the real bake + freeze poses
  const seq = [
    ['nova_idlegroove_v2', 4000], ['gest_star', 3000], ['nova_idlegroove_v2', 4000],
    ['gest_frog', 3000], ['nova_idlegroove_v2', 4000], ['gest_bear', 3000],
    ['nova_idlegroove_v2', 4000], ['gest_flamingo', 3000], ['nova_idlegroove_v2', 4000],
  ];
  for (const [id, ms] of seq) { console.log(`  drive ${id}`); await drive(id).catch(()=>{}); await pg.waitForTimeout(ms); }

  await pg.close(); await ctx.close();  // finalizes the video file
  const vids = fs.readdirSync(outDir).filter(f => f.endsWith('.webm'));
  console.log('VIDEO:', vids[0] || '(none)');
  await b.close();
})().catch(e => { console.error('CAPTURE ERROR', e.message); process.exit(2); });
