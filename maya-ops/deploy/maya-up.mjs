// MAYA UP — one command: fresh pod -> booted -> verified -> n8n re-pointed -> links.
//
//   node maya-up.mjs            (needs RUNPOD_API_KEY in env; n8n key from ~/.maya/n8n.env)
//
// Encodes every bring-up lesson so none has to be re-learned:
//   PUBLIC_KEY at create (else no SSH) · watchdog rewritten with THIS pod id (money-guard)
//   · maya-boot.sh does deps/order/tmux/LK_ROOM itself · port 8000 open for cloud n8n
//   · stopped pods rarely restart, so we always CREATE · n8n CONFIGs re-pointed at the
//   new pod URL (they go stale on every swap).
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const RP = 'https://rest.runpod.io/v1';
const KEY = process.env.RUNPOD_API_KEY;
if (!KEY) throw new Error('set RUNPOD_API_KEY');
const H = { Authorization: `Bearer ${KEY}`, 'Content-Type': 'application/json' };
const MAYA_DIR = join(homedir(), '.maya');
const sleep = (s) => new Promise(r => setTimeout(r, s * 1000));
const log = (m) => console.log(`>> ${m}`);

function n8nEnv() {
  try {
    const txt = readFileSync(join(MAYA_DIR, 'n8n.env'), 'utf8');
    const get = (k) => (txt.match(new RegExp(`^${k}=(.+)$`, 'm')) || [])[1]?.trim();
    return { base: get('N8N_BASE'), key: get('N8N_KEY') };
  } catch { return null; }
}

// 1. CREATE
const pubkey = readFileSync(join(homedir(), '.ssh', 'id_ed25519.pub'), 'utf8').trim();
log('creating SECURE 4090, EU-RO-1, volume 1ditrne6cb, ports 8765/8010/8000/22 ...');
const pod = await (await fetch(`${RP}/pods`, { method: 'POST', headers: H, body: JSON.stringify({
  cloudType: 'SECURE', gpuTypeIds: ['NVIDIA GeForce RTX 4090'], gpuCount: 1,
  networkVolumeId: '1ditrne6cb', dataCenterIds: ['EU-RO-1'],
  imageName: 'runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04',
  containerDiskInGb: 40, volumeMountPath: '/workspace',
  ports: ['8765/http', '8010/http', '8000/http', '22/tcp'],
  name: `maya-live-${new Date().toISOString().slice(0, 10)}`, interruptible: false,
  env: { PUBLIC_KEY: pubkey },
}) })).json();
if (!pod.id) throw new Error(`create failed: ${JSON.stringify(pod)}`);
log(`pod ${pod.id}`);
mkdirSync(MAYA_DIR, { recursive: true });
writeFileSync(join(MAYA_DIR, 'current-pod.txt'), pod.id);

// 2. WAIT FOR SSH
let ip, port;
for (let i = 0; i < 30; i++) {
  await sleep(9);
  const d = await (await fetch(`${RP}/pods/${pod.id}`, { headers: H })).json();
  ip = d.publicIp; port = d.portMappings?.['22'];
  if (ip && port) break;
}
if (!ip || !port) throw new Error('no SSH endpoint after 4.5 min');
log(`ssh root@${ip} -p ${port}`);

const SSH = ['-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20',
             '-i', join(homedir(), '.ssh', 'id_ed25519'), '-p', String(port), `root@${ip}`];
const ssh = (cmd, input) => execFileSync('ssh', [...SSH, cmd],
  { input: input ?? '', encoding: 'utf8', timeout: 120000 });
for (let i = 0; i < 15; i++) { try { if (ssh('echo up').includes('up')) break; } catch {} await sleep(8); }

// 3. DEPLOY the repo's brain page BEFORE boot — the volume copy is whatever the last
//    deploy left; without this step, code changes (gate text, AI label, /test board)
//    silently never reach the pod. Repo root = two levels above this script.
const repoRoot = join(new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'), '..', '..');
execFileSync('scp', ['-o', 'StrictHostKeyChecking=no', '-i', join(homedir(), '.ssh', 'id_ed25519'),
  '-P', String(port), join(repoRoot, 'pod', 'maya_rt.py'), `root@${ip}:/workspace/maya_rt.py`],
  { timeout: 120000 });
log('deployed pod/maya_rt.py -> /workspace (repo is the source of truth)');

// 3b. MONEY-GUARD with THIS pod id, then boot (maya-boot.sh does everything else)
ssh('cat > /root/.rpkey && chmod 600 /root/.rpkey', KEY);
ssh(`cat > /root/maya-watchdog.sh << 'EOF'
#!/bin/bash
# MONEY GUARD: stop pod ${pod.id} after 3h. Pod id literal on purpose.
sleep 10800
curl -s -X POST "https://rest.runpod.io/v1/pods/${pod.id}/stop" -H "Authorization: Bearer \\$(cat /root/.rpkey)" > /root/watchdog_stop.log 2>&1
EOF
chmod +x /root/maya-watchdog.sh
nohup bash /root/maya-watchdog.sh >/dev/null 2>&1 &
command -v tmux >/dev/null 2>&1 || { apt-get update -qq >/dev/null; apt-get install -y -qq tmux >/dev/null; }
tmux new-session -d -s mayaboot "bash /workspace/maya-boot.sh"
echo ARMED_AND_BOOTING`);
log('watchdog armed, boot launched — cold load can take up to 25 min');

// 4. WAIT FOR HEALTH (brain + switchboard via public proxy)
const brainUrl = `https://${pod.id}-8765.proxy.runpod.net`;
const swUrl = `https://${pod.id}-8000.proxy.runpod.net`;
let healthy = false;
for (let i = 0; i < 60; i++) {
  await sleep(30);
  try {
    const h = await (await fetch(`${brainUrl}/health`)).json();
    const s = await (await fetch(`${swUrl}/health`)).json();
    if (h.ok && s.ok) {
      if (h.room !== 'maya-live') throw new Error(`ROOM LAW VIOLATION: brain in '${h.room}'`);
      healthy = true; log(`healthy: brain room=${h.room}, switchboard ok`); break;
    }
  } catch (e) { if (String(e).includes('ROOM LAW')) throw e; }
  if (i % 6 === 5) log(`still booting... ${(i + 1) / 2} min`);
}
if (!healthy) throw new Error('not healthy after 30 min — check /test on the pod or tmux logs');

// 5. RE-POINT n8n CONFIGS at the new pod
const n8n = n8nEnv();
if (n8n?.key) {
  const NH = { 'X-N8N-API-KEY': n8n.key, 'Content-Type': 'application/json' };
  const list = (await (await fetch(`${n8n.base}/workflows?limit=100`, { headers: NH })).json()).data || [];
  for (const w of list.filter(x => x.name.startsWith('MAYA W'))) {
    const full = await (await fetch(`${n8n.base}/workflows/${w.id}`, { headers: NH })).json();
    const cfg = full.nodes.find(n => n.name === 'CONFIG');
    const a = cfg?.parameters.assignments.assignments.find(x => x.name === 'maya_api');
    if (!a || a.value === swUrl) continue;
    a.value = swUrl;
    const r = await fetch(`${n8n.base}/workflows/${w.id}`, { method: 'PUT', headers: NH,
      body: JSON.stringify({ name: full.name, nodes: full.nodes, connections: full.connections, settings: full.settings }) });
    log(`n8n ${w.name}: maya_api -> new pod ${r.ok ? 'OK' : 'FAIL ' + r.status}`);
  }
} else log('n8n key not found at ~/.maya/n8n.env — re-point CONFIGs manually');

// 6. LINKS + BEEP
const links = `
  HER PAGE (talk):      ${brainUrl}/
  TEST BOARD:           ${brainUrl}/test
  DIRECTOR (phase 1):   http://localhost:8088/maya-director.html?saray=${brainUrl}/
  DIRECTOR (backend):   http://localhost:8088/maya-director.html?saray=${brainUrl}/&api=${swUrl}
  STAGE (OBS):          http://localhost:8088/maya-stage.html?saray=${brainUrl}/&api=${swUrl}&scene=open
  (page server: npx http-server -p 8088 in the dance-project folder)`;
console.log(links);
try { execFileSync('powershell', ['-c', '1..4 | % { [console]::beep(880,220); Start-Sleep -m 120 }']); } catch {}
log(`DONE. Pod ${pod.id} — money-guard stops it in 3h. maya-down.mjs stops it sooner.`);
