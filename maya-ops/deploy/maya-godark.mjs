// MAYA GO-DARK — flip the show OFF cleanly: deactivate every n8n workflow, then stop the pod.
// Usage:  node maya-godark.mjs [podId]
// STEP STATUS: n8n deactivate = TESTED (API) · pod stop = TESTED (maya-down path).
import { readFileSync } from 'node:fs'; import { homedir } from 'node:os'; import { join } from 'node:path';
const POD = process.argv[2] || readFileSync(join(homedir(), '.maya', 'current-pod.txt'), 'utf8').trim();
const RP = process.env.RUNPOD_API_KEY;
const n8nEnv = readFileSync(join(homedir(), '.maya', 'n8n.env'), 'utf8');
const g = (k) => (n8nEnv.match(new RegExp(`^${k}=(.+)$`, 'm')) || [])[1]?.trim();
const NB = g('N8N_BASE'), NH = { 'X-N8N-API-KEY': g('N8N_KEY'), 'Content-Type': 'application/json' };

const list = (await (await fetch(`${NB}/workflows?limit=100`, { headers: NH })).json()).data || [];
for (const wf of list.filter(w => w.name.startsWith('MAYA') && w.active)) {
  const r = await fetch(`${NB}/workflows/${wf.id}/deactivate`, { method: 'POST', headers: NH });
  console.log(`  ${r.ok ? '✓' : '✗'} deactivate ${wf.name}`);
}
await fetch(`https://rest.runpod.io/v1/pods/${POD}/stop`, { method: 'POST', headers: { Authorization: `Bearer ${RP}` } });
await new Promise(r => setTimeout(r, 6000));
const pod = await (await fetch(`https://rest.runpod.io/v1/pods/${POD}`, { headers: { Authorization: `Bearer ${RP}` } })).json();
console.log(`pod ${POD}: ${pod.desiredStatus}${pod.desiredStatus === 'EXITED' ? ' — $0/hr' : ' — CHECK CONSOLE'}`);
