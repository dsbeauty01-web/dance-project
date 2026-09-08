#!/usr/bin/env node
/* record-demo.js — CDP screencast a page to frames + recmeta.json (video-only).
   usage: node record-demo.js <cdpPort> <url> <outDir> <seconds> */
'use strict';
const fs = require('fs'), path = require('path');
const PORT = +process.argv[2], URL = process.argv[3], OUT = process.argv[4], SECS = +(process.argv[5] || 30);
const FRAMES = path.join(OUT, 'frames');
fs.rmSync(OUT, { recursive: true, force: true }); fs.mkdirSync(FRAMES, { recursive: true });
let ws, id = 0; const pend = new Map(); const frames = [];
const cdp = (m, p) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method: m, params: p || {} })); setTimeout(() => { if (pend.has(i)) { pend.delete(i); rej(new Error('timeout ' + m)); } }, 20000); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const t = list.find(x => x.type === 'page' && x.url.includes('lights-demo')) || list.find(x => x.type === 'page');
  ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  ws.onmessage = m => { const d = JSON.parse(m.data);
    if (d.id && pend.has(d.id)) { const p = pend.get(d.id); pend.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); return; }
    if (d.method === 'Page.screencastFrame') { const n = frames.length; fs.writeFileSync(path.join(FRAMES, `f${String(n).padStart(6, '0')}.jpg`), Buffer.from(d.params.data, 'base64')); frames.push({ n, ts: d.params.metadata.timestamp }); cdp('Page.screencastFrameAck', { sessionId: d.params.sessionId }).catch(() => {}); } };
  await cdp('Page.enable');
  await cdp('Page.startScreencast', { format: 'jpeg', quality: 80, everyNthFrame: 1 });
  await sleep(SECS * 1000);
  await cdp('Page.stopScreencast').catch(() => {});
  fs.writeFileSync(path.join(OUT, 'recmeta.json'), JSON.stringify({ frames }));
  console.log('CAPTURED ' + frames.length + ' frames over ' + SECS + 's');
  process.exit(0);
})().catch(e => { console.error('REC-FAIL', e.message); process.exit(1); });
