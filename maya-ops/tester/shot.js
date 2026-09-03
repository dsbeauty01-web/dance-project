#!/usr/bin/env node
/* single-screenshot via CDP (headless Edge already launched by the caller).
   usage: node shot.js <cdpPort> <fileUrl> <outPng> [w] [h] */
'use strict';
const fs = require('fs');
const PORT = +process.argv[2], URL = process.argv[3], OUT = process.argv[4];
const W = +(process.argv[5] || 900), H = +(process.argv[6] || 1200);
let ws, id = 0; const pend = new Map();
const cdp = (m, p) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej });
  ws.send(JSON.stringify({ id: i, method: m, params: p || {} }));
  setTimeout(() => { if (pend.has(i)) { pend.delete(i); rej(new Error('timeout ' + m)); } }, 30000); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  let t = list.find(x => x.type === 'page');
  if (!t) { await fetch(`http://127.0.0.1:${PORT}/json/new`, { method: 'PUT' }); await sleep(500);
    t = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find(x => x.type === 'page'); }
  ws = new WebSocket(t.webSocketDebuggerUrl);   // Node 22+ global
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  ws.onmessage = m => { const d = JSON.parse(m.data);
    if (d.id && pend.has(d.id)) { const p = pend.get(d.id); pend.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); } };
  await cdp('Page.enable');
  await cdp('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 2, mobile: true });
  await cdp('Page.navigate', { url: URL });
  await sleep(1600);
  const { data } = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  fs.writeFileSync(OUT, Buffer.from(data, 'base64'));
  console.log('WROTE ' + OUT);
  process.exit(0);
})().catch(e => { console.error('SHOT-FAIL', e.message); process.exit(1); });
