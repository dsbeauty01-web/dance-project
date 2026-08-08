// MAYA DOWN — stop the current pod, verify EXITED. Usage: node maya-down.mjs [podId]
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const KEY = process.env.RUNPOD_API_KEY;
if (!KEY) throw new Error('set RUNPOD_API_KEY');
const H = { Authorization: `Bearer ${KEY}` };
const id = process.argv[2] || readFileSync(join(homedir(), '.maya', 'current-pod.txt'), 'utf8').trim();

await fetch(`https://rest.runpod.io/v1/pods/${id}/stop`, { method: 'POST', headers: H });
await new Promise(r => setTimeout(r, 6000));
const d = await (await fetch(`https://rest.runpod.io/v1/pods/${id}`, { headers: H })).json();
console.log(`pod ${id}: ${d.desiredStatus}`);
if (d.desiredStatus !== 'EXITED') { console.error('NOT STOPPED — check the RunPod console'); process.exit(1); }
console.log('stopped. $0/hr.');
