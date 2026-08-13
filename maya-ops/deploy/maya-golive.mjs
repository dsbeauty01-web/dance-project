// MAYA GO-LIVE — flip the whole show ON: verify pod, activate the n8n chat pipeline in the
// correct order, health-check every hop via the pod /test board, print the OBS command, and
// confirm the YouTube broadcast. Companion: maya-godark.mjs.
//
// Usage:  node maya-golive.mjs [podId]     (RUNPOD_API_KEY in env; n8n key from ~/.maya/n8n.env)
//
// STEP STATUS (verified during authoring 2026-08-12):
//   pod verify ............ TESTED (RunPod REST)
//   n8n activate .......... TESTED (n8n API /activate used successfully this session)
//   hop health checks ..... TESTED (/selftest board returns all-ok)
//   OBS command print ..... TESTED (string only)
//   YouTube live confirm .. UNTESTED (needs YouTube Data API creds not yet wired — prints a
//                            manual-check URL instead; do not fake green)
import { readFileSync } from 'node:fs'; import { homedir } from 'node:os'; import { join } from 'node:path';
const POD = process.argv[2] || readFileSync(join(homedir(), '.maya', 'current-pod.txt'), 'utf8').trim();
const RP = process.env.RUNPOD_API_KEY;
const n8nEnv = readFileSync(join(homedir(), '.maya', 'n8n.env'), 'utf8');
const g = (k) => (n8nEnv.match(new RegExp(`^${k}=(.+)$`, 'm')) || [])[1]?.trim();
const NB = g('N8N_BASE'), NH = { 'X-N8N-API-KEY': g('N8N_KEY'), 'Content-Type': 'application/json' };
const log = (m) => console.log(m);

// 1. pod up?
const pod = await (await fetch(`https://rest.runpod.io/v1/pods/${POD}`, { headers: { Authorization: `Bearer ${RP}` } })).json();
if (pod.desiredStatus !== 'RUNNING') { console.error(`POD NOT RUNNING (${pod.desiredStatus}) — run maya-up first, then confirm spend.`); process.exit(1); }
log(`✓ pod ${POD} RUNNING`);

// 2. activate pipeline in order: W3 (lead sink) → W2 (filter) → W4 (brain) → W1 (YouTube ear)
const ORDER = ['W3', 'W2', 'W4', 'W1 —']; // W1-FB stays inactive (Meta review pending)
const list = (await (await fetch(`${NB}/workflows?limit=100`, { headers: NH })).json()).data || [];
for (const tag of ORDER) {
  const wf = list.find(w => w.name.includes(`MAYA ${tag}`) || w.name.includes(tag));
  if (!wf) { log(`  ! ${tag}: workflow not found`); continue; }
  const r = await fetch(`${NB}/workflows/${wf.id}/activate`, { method: 'POST', headers: NH });
  log(`  ${r.ok ? '✓' : '✗'} activate ${wf.name}`);
}

// 3. hop health via the pod's own self-test board
const st = await (await fetch(`https://${POD}-8765.proxy.runpod.net/selftest`)).json();
const hops = ['engine_8010', 'bridge_9999', 'switchboard_8000', 'room_law_ok'];
for (const h of hops) { const v = st[h]; const ok = typeof v === 'object' ? v.ok : v; log(`  ${ok ? '✓' : '✗'} ${h}`); }
if (!st.ok) { console.error('SELF-TEST NOT ALL GREEN — stop and inspect /test board.'); process.exit(1); }

// 4. desktop-side talking broadcast
log('\nTALKING BROADCAST (desktop — one human action):');
log('  obs64.exe --startstreaming --minimize-to-tray   (OBS scene "Maya" is preconfigured)');
log('  then: node maya-ops/deploy/sales-driver.mjs ' + POD + '   (feeds her the sales script)');

// 5. YouTube live confirm — honest UNTESTED
log('\nYOUTUBE: confirm live at https://studio.youtube.com/channel/UCP6vE9sQs9B1aEiWzja1Uxw/livestreaming');
log('  (auto-confirm needs YouTube Data API creds — not wired; verify by eye for now.)');
log('\n✓ GO-LIVE checks complete.');
