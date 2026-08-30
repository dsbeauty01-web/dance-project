#!/usr/bin/env node
/* MACHINE-CERTIFY test/run_session.js — plays ONE full scripted freeze session
   against a live pod, machine-only (the founder is done testing; this is the tester).

   Drives real Chrome over the DevTools protocol (raw CDP, Node>=22 built-in WebSocket,
   zero npm deps — the browser extension proved too flaky for a certification loop).
   The page-side hands+eyes are window.__test (?test=1 harness in animal-freeze.html).

   Usage: node test/run_session.js --lang en|he --pod <podid> --out test/sessions/<name>
   Chrome flags: --autoplay-policy=no-user-gesture-required (CDP clicks are not user
   gestures — without this the AudioContext stays suspended and the game clock never
   runs) and --deny-permission-prompts (mic/cam DENIED: the fake-device flag would
   stream a test TONE into her VAD and pollute every session; the harness say() is the
   only kid voice, the synthetic pose() the only kid body).

   Script (PART 1): greet-wait → [silence 25s: G5 re-invite check] → name → chat
   question → consent yes → music → per-freeze pose behavior (hold 8, break 2,
   absent 1) + noise injections in gaps → ending answers → collect evidence. */
'use strict';
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');

/* ---------- args ---------- */
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const LANG = arg('lang', 'en');
const POD  = arg('pod', 'gtdmu76ocpjjmu');
const OUT  = arg('out', path.join(__dirname, 'sessions', LANG + '-' + arg('n', '0')));
const PORT = +arg('port', 9333);
const URL0 = `https://${POD}-8765.proxy.runpod.net/freeze?test=1&nolog=1` + (LANG === 'he' ? '&lang=he' : '');
fs.mkdirSync(OUT, { recursive: true });

/* ---------- phrase bank ---------- */
const PH_DIR = path.join(__dirname, 'phrases');
const PH = LANG === 'he' ? {
  name: 'he/he_hi_im_shuki_24k.wav', chat: 'he/he_do_you_like_pizza_24k.wav',
  yes: 'he/he_yes_24k.wav', ready: 'he/he_im_ready_24k.wav',
  ok: 'he/he_ok_24k.wav', bye: 'he/he_bye_24k.wav',
} : {
  name: 'hi_im_shuki.wav', chat: 'do_you_like_pizza.wav',
  yes: 'yes.wav', ready: 'im_ready.wav', ok: 'ok.wav', bye: 'bye.wav',
};
const NOISE = { garble: 'garble1.wav', breath: 'breath.wav', hum: 'hum.wav' };

function wavPcmB64(file) {
  // strict RIFF parse: require pcm16 mono 24k (the bank is committed in exactly this format)
  const b = fs.readFileSync(path.join(PH_DIR, file));
  if (b.toString('ascii', 0, 4) !== 'RIFF') throw new Error(file + ': not RIFF');
  let off = 12, fmt = null, data = null;
  while (off + 8 <= b.length) {
    const id = b.toString('ascii', off, off + 4), sz = b.readUInt32LE(off + 4);
    if (id === 'fmt ') fmt = { codec: b.readUInt16LE(off + 8), ch: b.readUInt16LE(off + 10), sr: b.readUInt32LE(off + 12), bits: b.readUInt16LE(off + 22) };
    if (id === 'data') { data = b.subarray(off + 8, off + 8 + sz); break; }
    off += 8 + sz + (sz % 2);
  }
  if (!fmt || !data) throw new Error(file + ': bad wav');
  if (fmt.codec !== 1 || fmt.ch !== 1 || fmt.sr !== 24000 || fmt.bits !== 16)
    throw new Error(file + `: need pcm16 mono 24k, got codec${fmt.codec} ch${fmt.ch} ${fmt.sr}Hz ${fmt.bits}bit`);
  return { b64: data.toString('base64'), secs: data.length / 48000 };
}

/* ---------- CDP ---------- */
let ws, msgId = 0;
const pending = new Map();
const netReqs = [];                      // Network evidence (PULSE / session-rec posts)
function cdp(method, params) {
  return new Promise((res, rej) => {
    const id = ++msgId;
    pending.set(id, { res, rej });
    ws.send(JSON.stringify({ id, method, params: params || {} }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); rej(new Error('CDP timeout ' + method)); } }, 60000);
  });
}
async function evalJs(expr, awaitP) {
  const r = await cdp('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: !!awaitP });
  if (r.exceptionDetails) throw new Error('page threw: ' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description || r.exceptionDetails.text).slice(0, 300));
  return r.result && r.result.value;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, timeoutMs, everyMs, label) {
  const t0 = Date.now();
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() - t0 > timeoutMs) throw new Error('TIMEOUT waiting: ' + label);
    await sleep(everyMs || 500);
  }
}

/* ---------- event journal ---------- */
const T0 = Date.now();
const events = [];
function ev(name, detail) {
  const e = { t: Date.now() - T0, ev: name, detail: detail || null };
  events.push(e);
  console.log(`[${(e.t / 1000).toFixed(1)}s] ${name}${detail ? ' ' + JSON.stringify(detail).slice(0, 120) : ''}`);
}

async function state() { return evalJs('window.__test ? __test.state() : null'); }
async function say(phraseFile, label) {
  const { b64, secs } = wavPcmB64(phraseFile);
  ev('say:' + label, { file: phraseFile, secs: +secs.toFixed(2) });
  const r = await evalJs(`__test.say(${JSON.stringify(b64)})`, true);
  ev('say-done:' + label, { result: r });
  return r;
}
async function logCount() { const s = await state(); return s ? s.logCount : 0; }

/* wait for her NEXT reply: a [NOVA-SAID] log at index >= since */
async function waitReply(since, timeoutMs, label) {
  try {
    return await until(async () => {
      const logs = await evalJs(`__test.logs(${since})`);
      const hit = (logs || []).find(l => l.m.startsWith('[NOVA-SAID]'));
      return hit || null;
    }, timeoutMs, 400, 'reply:' + label);
  } catch (e) { ev('no-reply:' + label); return null; }
}

/* ---------- main ---------- */
let FR = null;   // freeze schedule — hoisted so collect() works even on early aborts
(async () => {
  /* 1. the browser. Node-spawned Chrome dies instantly with exit 21 on this machine
     (every flag combo, fresh profiles, even --no-sandbox), while Edge launched detached
     from bash proved reliable — so the loop script starts the browser and the runner
     ATTACHES (--attach). Self-spawn (Edge first) kept for direct invocation. */
  let proc = null;
  if (!process.argv.includes('--attach')) {
    const browser = ['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
                     'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
                     'C:/Program Files/Google/Chrome/Application/chrome.exe'].find(p => fs.existsSync(p));
    if (!browser) throw new Error('no chromium browser found');
    const profile = path.join(OUT, 'profile-' + process.pid);
    const flags = [
      `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
      '--autoplay-policy=no-user-gesture-required', '--deny-permission-prompts',
      '--no-first-run', '--no-default-browser-check', '--disable-features=Translate',
      '--window-size=1280,800', '--mute-audio',
    ];
    if (!process.argv.includes('--headed')) flags.push('--headless=new');
    const chromeLog = fs.openSync(path.join(OUT, 'chrome.log'), 'w');
    proc = spawn(browser, [...flags, URL0], { stdio: ['ignore', chromeLog, chromeLog], detached: true });
    proc.on('exit', c => ev('chrome-exited', { code: c }));
  }
  ev(proc ? 'browser-spawned' : 'attach-mode', { port: PORT, url: URL0 });

  /* 2. attach CDP to the page target. If the port answers but our page is missing
     (a stale browser already owned the port), open the tab in THAT browser. */
  let askedNew = false;
  const targets = await until(async () => {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await r.json();
      const hit = list.find(t => t.type === 'page' && t.url.includes('/freeze'));
      if (hit) return hit;
      if (!askedNew) { askedNew = true; await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(URL0)}`, { method: 'PUT' }).catch(() => {}); }
      return null;
    } catch (_) { return null; }
  }, 30000, 500, 'CDP target');
  ws = new WebSocket(targets.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = m => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { const p = pending.get(d.id); pending.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); }
    else if (d.method === 'Network.requestWillBeSent') {
      const u = d.params.request.url;
      if (/\/session\/|\/pulse|\/api\/v1\//.test(u))
        netReqs.push({ t: Date.now() - T0, url: u, method: d.params.request.method, postData: (d.params.request.postData || '').slice(0, 2000) });
    }
  };
  await cdp('Runtime.enable'); await cdp('Network.enable');
  ev('cdp-attached');

  /* 3. harness up → tap start */
  await until(async () => evalJs('typeof window.__test !== "undefined"').catch(() => false), 20000, 500, '__test harness');
  ev('harness-ready');
  const tap1 = await evalJs('__test.tap()');
  ev('tap', { hit: tap1 });

  /* 4. live + greet (Live.alive flips on her first spoken word) */
  await until(async () => { const s = await state(); return s && (s.liveOn || s.liveDead); }, 45000, 500, 'pod probe settled');
  const s0 = await state();
  if (s0.liveDead) { ev('ABORT', { reason: 'pod dead — clip fallback, nothing to certify' }); finish(1); return; }
  await until(async () => { const s = await state(); return s && s.liveAlive; }, 90000, 500, 'greet spoken');
  ev('greet-heard');

  /* 5. G5 silence window: say NOTHING for 25s — expect exactly ONE re-invite */
  const silence0 = await logCount();
  ev('silence-window-start', { logIdx: silence0 });
  await sleep(25000);
  ev('silence-window-end');

  /* 6. conversation: name → chat question */
  let idx = await logCount();
  await say(PH.name, 'name');
  await waitReply(idx, 12000, 'name');
  await sleep(1500);
  idx = await logCount();
  await say(PH.chat, 'chat');
  await waitReply(idx, 12000, 'chat');
  await sleep(1500);

  /* 7. consent: yes → music must start (countdown gates play) */
  idx = await logCount();
  await say(PH.yes, 'yes');
  let started = true;
  try {
    await until(async () => { const s = await state(); return s && s.phase === 'game'; }, 30000, 500, 'music start');
  } catch (e) {
    ev('yes-not-heard-fallback-ready-tap');       // grader G1 sees this event and can fail the yes-phrase
    await evalJs('__test.ready()');
    try { await until(async () => { const s = await state(); return s && s.phase === 'game'; }, 25000, 500, 'music start (tap)'); }
    catch (e2) { started = false; ev('ABORT', { reason: 'game never started' }); }
  }
  if (!started) { await collect(); finish(1); return; }
  ev('music-started');

  /* 8. the game: per-freeze pose behavior + gap noise. hold 8 · break 2 · absent 1 */
  FR = await evalJs('__test.freezes()');
  const BREAK_AT = new Set([2, 7]), ABSENT_AT = new Set([4]);
  const NOISE_AFTER = { 1: 'garble', 5: 'hum', 8: 'breath' };
  let inHold = false, round = -1, noiseSent = {};
  await evalJs('__test.pose(false)');              // dancing kid: moving
  for (;;) {
    const s = await state();
    if (!s) break;
    if (s.phase === 'ending') { ev('ending-phase'); break; }
    const mt = s.musicT || 0;
    const cur = FR.findIndex(f => mt >= f.at && mt < f.at + f.hold);
    if (cur >= 0 && !inHold) {
      inHold = true; round = cur;
      if (ABSENT_AT.has(cur)) { await evalJs('__test.poseOff()'); ev('hold:absent', { round: cur, mt }); }
      else if (BREAK_AT.has(cur)) { await evalJs('__test.pose(false)'); ev('hold:break', { round: cur, mt }); }
      else { await evalJs('__test.pose(true)'); ev('hold:still', { round: cur, mt }); }
    } else if (cur < 0 && inHold) {
      inHold = false;
      await evalJs('__test.pose(false)'); ev('melt', { round, mt });
      const nz = NOISE_AFTER[round];
      if (nz && !noiseSent[round]) { noiseSent[round] = 1; await sleep(2500); await say(NOISE[nz], 'noise-' + nz); }
    }
    if (mt > 135 && s.phase !== 'ending') { ev('post-music-wait', { mt }); await sleep(3000); }
    if (mt > 150) { ev('ending-never-came', { mt }); break; }
    await sleep(250);
  }

  /* 9. ending trio: she talks; kid answers ok → bye. A REAL kid waits for her to stop
     talking before answering — talking over her queued trio lines (he-2) piles the
     engine's sequential audio up and HER reply then airs seconds late. */
  const waitQuiet = async (maxMs) => {
    const t0 = Date.now();
    let seen = 0;
    for (;;) {
      const en = await evalJs(`__test.energy(-10)`).catch(() => []);
      const loud = (en || []).some(e => e.air > 0.01 || e.eng > 0.01);
      if (!loud) { if (++seen >= 2) return true; } else seen = 0;
      if (Date.now() - t0 > maxMs) return false;
      await sleep(400);
    }
  };
  await sleep(3000);
  await waitQuiet(15000); ev('quiet-before-ok');
  idx = await logCount();
  await say(PH.ok, 'ending-ok');
  await waitReply(idx, 12000, 'ending-ok');
  await waitQuiet(12000); ev('quiet-before-bye');
  idx = await logCount();
  await say(PH.bye, 'ending-bye');
  await waitReply(idx, 12000, 'ending-bye');
  await sleep(6000);

  await collect();
  finish(0);

  async function collect() {
    ev('collecting');
    const logs = await evalJs('__test.logs()').catch(() => []);
    const energy = await evalJs('__test.energy()').catch(() => []);
    const fin = await state().catch(() => null);
    fs.writeFileSync(path.join(OUT, 'session.json'), JSON.stringify({
      meta: { lang: LANG, pod: POD, url: URL0, startedAt: T0, tookMs: Date.now() - T0 },
      events, netReqs, logs, energy, finalState: fin, freezes: FR || null,
    }, null, 1));
    ev('saved', { out: OUT, logs: (logs || []).length, energy: (energy || []).length, net: netReqs.length });
  }
  function finish(code) {
    try { ws && ws.close(); } catch (_) {}
    try { proc.kill(); } catch (_) {}
    setTimeout(() => process.exit(code), 800);
  }
})().catch(e => { console.error('RUNNER-FATAL', e && e.message); process.exit(2); });
