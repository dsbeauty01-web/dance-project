const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', SCR = __dirname, Y4M = path.join(SCR, 'fakecam.y4m');
const CUES = [ {action:'shrug'}, {action:'headbob',dir:'L'}, {action:'headbob',dir:'R'}, {action:'hipbounce'}, {action:'clap'}, {action:'combo'} ];
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.json':'application/json','.css':'text/css','.mp3':'audio/mpeg','.wav':'audio/wav','.webm':'video/webm','.svg':'image/svg+xml' };
(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture=' + Y4M,'--autoplay-policy=no-user-gesture-required','--ignore-gpu-blocklist','--enable-unsafe-swiftshader','--use-gl=angle'] });
  const ctx = await b.newContext({ permissions: ['camera','microphone'], viewport: { width: 760, height: 980 } });
  const pg = await ctx.newPage();
  pg.on('pageerror', e => console.log('[pg-err]', e.message));
  await pg.goto(`http://localhost:${port}/nova-joined.html`, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(800);
  await pg.click('#arrival-start-btn').catch(() => {});
  // wait for fake cam on #webcam
  for (let i = 0; i < 20; i++) { await pg.waitForTimeout(700); const w = await pg.evaluate(() => document.getElementById('webcam')?.videoWidth || 0); if (w > 0) { console.log('cam up', w); break; } }

  // QA: force cam-side full-screen + run OUR OWN MoveNet feeding window.__lastPoseKeypoints
  const setup = await pg.evaluate(async () => {
    const cs = document.getElementById('cam-side');
    // un-hide every ancestor (game layout is display:none until the dance phase)
    let el = cs;
    while (el) { el.style.display = (el === cs ? 'block' : (el.style.display === 'none' || getComputedStyle(el).display === 'none' ? 'block' : el.style.display || '')); el.style.visibility = 'visible'; el.style.opacity = '1'; el = el.parentElement; }
    cs.style.position = 'fixed'; cs.style.left = '0'; cs.style.top = '0'; cs.style.width = '720px'; cs.style.height = '900px';
    cs.style.zIndex = '99999';
    if (typeof poseDetection === 'undefined') return 'NO poseDetection lib';
    const det = await poseDetection.createDetector(poseDetection.SupportedModels.MoveNet, { modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING });
    const v = document.getElementById('webcam');
    window.__qaTick = async () => { try { const ps = await det.estimatePoses(v, { flipHorizontal: false }); if (ps[0]) window.__lastPoseKeypoints = ps[0].keypoints; } catch (e) {} requestAnimationFrame(window.__qaTick); };
    window.__qaTick();
    return 'ok';
  });
  console.log('setup:', setup);
  // wait for keypoints
  for (let i = 0; i < 20; i++) { await pg.waitForTimeout(500); const ok = await pg.evaluate(() => !!window.__lastPoseKeypoints); if (ok) { console.log('keypoints flowing'); break; } }

  for (const cue of CUES) {
    let on = 0;
    for (let t = 0; t < 40; t++) { await pg.evaluate(c => { window.__cueAction = c; }, cue); await pg.waitForTimeout(150);
      on = await pg.evaluate(() => document.querySelectorAll('#aura-layer .aura.on').length + (document.querySelector('#aura-full.on') ? 1 : 0)); if (on > 0) break; }
    await pg.waitForTimeout(250);
    const out = path.join(SCR, 'shot_joined_' + cue.action + (cue.dir || '') + '.png');
    await pg.locator('#cam-side').screenshot({ path: out }).catch(e => console.log('shot fail', e.message));
    const diag = await pg.evaluate(() => ({ auras: [...document.querySelectorAll('#aura-layer .aura.on')].map(a => ({ x: a.style.getPropertyValue('--x'), y: a.style.getPropertyValue('--y'), size: a.style.getPropertyValue('--size'), arrow: a.querySelector('.arrow').textContent })), full: !!document.querySelector('#aura-full.on') }));
    console.log('CUE', JSON.stringify(cue), '->', JSON.stringify(diag));
  }
  await b.close(); server.close(); console.log('DONE');
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
