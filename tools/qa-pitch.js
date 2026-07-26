// Verify the in-game pitch scheduler: lines fire at beats on the game clock; clips suppressed under musetalk.
const { chromium } = require('playwright-core');
const fs = require('fs');
const ROOT = 'C:/Users/ADMIN/projects/dance-project';
const CHROME = [process.env['ProgramFiles'] + '\\Google\\Chrome\\Application\\chrome.exe'].find(p => fs.existsSync(p));
const args = ['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required','--use-file-for-fake-video-capture=' + ROOT + '/tools/fakecam.y4m'];
let pass=0, fail=0; const ok=(n,c,d='')=>{c?pass++:fail++;console.log(`${c?'PASS':'FAIL'}  ${n}${d?'  — '+d:''}`);};
(async () => {
  const b = await chromium.launch({ executablePath: CHROME, headless: true, args });
  const p = await b.newPage();
  await p.goto('file:///' + ROOT + '/nova-commercial.html?nonova&game=freeze', { waitUntil: 'load', timeout: 30000 });
  await p.waitForTimeout(1500);
  // arm the scheduler manually with a controllable clock
  await p.evaluate(() => {
    window.__MUSETALK = true;
    window.__testPos = 0;
    window.__gamePos = () => window.__testPos;
    window.__novaSpeakingNow = false;
    window.__pitchLog = [];
    window.__pitchStart('freeze');
  });
  ok('PITCH_PLANS has 5 games', await p.evaluate(() => Object.keys(window.__PITCH_PLANS).length === 5),
     await p.evaluate(()=>Object.keys(window.__PITCH_PLANS).join(',')));

  // drive the clock forward through the freeze beats and collect what fired
  const beats = await p.evaluate(() => window.__PITCH_PLANS.freeze.map(x=>x.t));
  for (const t of beats) { await p.evaluate(tt => { window.__testPos = tt + 0.1; }, t); await p.waitForTimeout(600); }
  const log = await p.evaluate(() => window.__pitchLog.map(x=>x.text));
  ok('every freeze beat fired once (6 lines)', log.length === 6, 'fired=' + log.length);
  ok('first line is the intro beat', /Dance big/.test(log[0]||''), log[0]||'(none)');
  ok('freeze cue line present', log.some(l=>/Freeze! Hold it/.test(l)), log.join(' | '));

  // clips suppressed under musetalk
  const suppressed = await p.evaluate(() => {
    window.__clipQueue = []; window.playClip('ug-warm2', 1);
    return window.__clipQueue.length === 0;
  });
  ok('playClip suppressed under musetalk (no queue)', suppressed);

  // one-mouth: while she is speaking, a beat does NOT double-fire immediately
  const held = await p.evaluate(async () => {
    window.__pitchLog = []; window.__novaSpeakingNow = true;
    window.__pitchStart('wave'); window.__testPos = 2.1;
    await new Promise(r=>setTimeout(r,700));
    return window.__pitchLog.length;   // should be 0 while speaking
  });
  ok('one-mouth: no line fired while she is already speaking', held === 0, 'fired=' + held);

  await b.close();
  console.log(`\nPITCH TEST: ${pass} pass / ${fail} fail`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('ERR', e.message); process.exit(2); });
