#!/usr/bin/env node
'use strict';
/* one-off page diagnostic for recal video phase */
const PORT = +process.argv[2] || 9433;
let ws, msgId = 0; const pending = new Map();
function cdp(m, p) { return new Promise((res, rej) => { const id = ++msgId; pending.set(id, { res, rej });
  ws.send(JSON.stringify({ id, method: m, params: p || {} }));
  setTimeout(() => { if (pending.has(id)) { pending.delete(id); rej(new Error('timeout ' + m)); } }, 30000); }); }
async function evalJs(e, a) { const r = await cdp('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: !!a });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 300)); return r.result && r.result.value; }
(async () => {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
  const page = list.find(t => t.type === 'page' && /freeze/.test(t.url || ''));
  if (!page) { console.error('no freeze target: ' + list.map(t => t.url).join(' | ')); process.exit(2); }
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  ws.onmessage = ev => { const m = JSON.parse(ev.data); const p = pending.get(m.id);
    if (p) { pending.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); } };
  await cdp('Runtime.enable');
  const d = await evalJs(`(function(){
    const b=document.getElementById('start-btn');
    const errs=(window.__test?__test.logs(0):[]).filter(l=>l.k!=='log').slice(-15).map(l=>l.m);
    const pose=(window.__test?__test.logs(0):[]).filter(l=>/POSE|CAL|GATE|AUDIO|LIVE/i.test(l.m)).slice(-25).map(l=>l.m);
    return { url:location.href,
      startBtn: b?{disabled:b.disabled, visible:b.offsetParent!==null, text:b.textContent}:null,
      startScreen: (function(){const s=document.getElementById('start-screen');return s?getComputedStyle(s).display:null})(),
      phase: typeof PHASE!=='undefined'?PHASE:null,
      liveOn: typeof Live!=='undefined'?{on:Live.on,alive:Live.alive,dead:Live.dead}:null,
      poseStarted: typeof Pose!=='undefined'?{started:!!Pose._started, ok:Pose.ok, engine:Pose.engine}:null,
      camReady: typeof camEl!=='undefined'?camEl.readyState:null,
      visibleButtons: Array.from(document.querySelectorAll('button')).filter(x=>x.offsetParent!==null).map(x=>({id:x.id,text:(x.textContent||'').trim().slice(0,40),disabled:x.disabled})),
      gates: Array.from(document.querySelectorAll('input[type=checkbox]')).map(x=>({id:x.id,checked:x.checked,visible:x.offsetParent!==null})),
      warns: errs, interesting: pose };
  })()`);
  console.log(JSON.stringify(d, null, 2));
  process.exit(0);
})().catch(e => { console.error(e.message); process.exit(2); });
