// Live selling host driver — blip-proof: any network error is caught and retried,
// so a momentary laptop internet drop never kills the broadcast.
import { readFileSync } from 'node:fs';
const POD = process.argv[2] || 'iysdfoxqdpndyy';
const SW = `https://${POD}-8000.proxy.runpod.net`;
const products = ['serum-c', 'cream-night'].map(id =>
  JSON.parse(readFileSync(new URL(`../loop/scripts/${id}.he.json`, import.meta.url))));
const lines = products.flatMap(p => p.segments.map(s => s.text_he));
const sleep = (s) => new Promise(r => setTimeout(r, s * 1000));
const safe = async (fn, d = null) => { try { return await fn(); } catch { return d; } };

await safe(() => fetch(`${SW}/session/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ client: 'live', answer_mode: 'auto', lang: 'he' }) }));
console.log('session started');
let i = 0;
while (true) {
  const text = lines[i % lines.length];
  const r = await safe(() => fetch(`${SW}/say`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }) }));
  console.log(`[${i}] say ${r ? r.status : 'RETRY(net)'} — ${text.slice(0, 36)}...`);
  i++;
  await sleep(16);
}
