#!/usr/bin/env node
/* record-demo2.js — like record-demo.js but WAITS for window.__ready before rolling,
   and stops early once window.__demoDone. usage: node record-demo2.js <cdpPort> <outDir> <maxSecs> */
'use strict';
const fs = require('fs'), path = require('path');
const PORT = +process.argv[2], OUT = process.argv[3], MAX = +(process.argv[4] || 34);
const FRAMES = path.join(OUT, 'frames');
fs.rmSync(OUT, { recursive: true, force: true }); fs.mkdirSync(FRAMES, { recursive: true });
let ws, id = 0; const pend = new Map(); const frames = [];
const cdp = (m, p) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method: m, params: p || {} })); setTimeout(() => { if (pend.has(i)) { pend.delete(i); rej(new Error('timeout ' + m)); } }, 20000); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const evalJs = async expr => { try { const r = await cdp('Runtime.evaluate', { expression: expr, returnByValue: true }); return r.result && r.result.value; } catch { return undefined; } };
(async () => {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const t = list.find(x => x.type === 'page' && x.url.includes('lights-demo')) || list.find(x => x.type === 'page');
  if (!t) throw new Error('no page target');
  ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  ws.onmessage = m => { const d = JSON.parse(m.data);
    if (d.id && pend.has(d.id)) { const p = pend.get(d.id); pend.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); return; }
    if (d.method === 'Page.screencastFrame') { const n = frames.length; fs.writeFileSync(path.join(FRAMES, `f${String(n).padStart(6, '0')}.jpg`), Buffer.from(d.params.data, 'base64')); frames.push({ n, ts: d.params.metadata.timestamp }); cdp('Page.screencastFrameAck', { sessionId: d.params.sessionId }).catch(() => {}); } };
  await cdp('Page.enable'); await cdp('Runtime.enable');
  // wait up to 45s for the demo to finish booting (getUserMedia + MediaPipe + calibration)
  let ready = false; for (let i = 0; i < 90; i++) { if (await evalJs('!!window.__ready')) { ready = true; break; } await sleep(500); }
  const eng = await evalJs('document.getElementById("eng") && document.getElementById("eng").textContent');
  console.log('READY=' + ready + ' ' + (eng || ''));
  await cdp('Page.startScreencast', { format: 'jpeg', quality: 82, everyNthFrame: 1 });
  const t0 = Date.now();
  while (Date.now() - t0 < MAX * 1000) { if (await evalJs('!!window.__demoDone')) { await sleep(400); break; } await sleep(400); }
  await cdp('Page.stopScreencast').catch(() => {});
  fs.writeFileSync(path.join(OUT, 'recmeta.json'), JSON.stringify({ frames }));
  console.log('CAPTURED ' + frames.length + ' frames');
  process.exit(0);
})().catch(e => { console.error('REC-FAIL', e.message); process.exit(1); });
