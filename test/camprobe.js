#!/usr/bin/env node
'use strict';
/* probes fake-camera state on the camtest page: node test/camprobe.js <cdpPort> */
const PORT = +process.argv[2] || 9581;
(async () => {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
  const page = list.find(t => t.type === 'page' && /camtest/.test(t.url || ''));
  if (!page) { console.log('no target: ' + list.map(t => t.url).join(' | ')); process.exit(2); }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pend = new Map();
  ws.onmessage = e => { const m = JSON.parse(e.data); const p = pend.get(m.id); if (p) { pend.delete(m.id); p.res(m.result); } };
  const cdp = (m, p) => new Promise(res => { const i = ++id; pend.set(i, { res }); ws.send(JSON.stringify({ id: i, method: m, params: p || {} })); });
  const ev = async (e, a) => { const r = await cdp('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: !!a });
    if (r.exceptionDetails) return 'THREW:' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description || '').slice(0, 200);
    return r.result && r.result.value; };
  console.log('enumerate:', JSON.stringify(await ev('navigator.mediaDevices.enumerateDevices().then(d=>d.map(x=>x.kind+":"+x.label))', true)));
  console.log('gum:', await ev('window.__gum'), 'ready:', await ev('v.readyState'), 'w:', await ev('v.videoWidth'), 't:', await ev('v.currentTime'));
  console.log('settings:', JSON.stringify(await ev('window.__track')));
  process.exit(0);
})().catch(e => { console.error(e.message); process.exit(2); });
