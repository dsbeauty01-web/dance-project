/* test/replay_all.mjs — every beta game's replay table + the freeze2 judge tests. Guardian runs this
   (.github/workflows/laws.yml); any regression = RED.   node test/replay_all.mjs */
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { ROOT } from './replay/sim.mjs';

let fail = 0;
const lines = [];

for (const t of ['test/freeze2_hold_test.mjs', 'test/freeze2_realdata_test.mjs']){
  try { const out = execFileSync('node', [join(ROOT, t)], { encoding: 'utf8' }); lines.push(`${t}: ${out.trim().split('\n').pop()}`); }
  catch (e) { fail++; lines.push(`${t}: FAIL\n${e.stdout || ''}${e.stderr || ''}`); }
}

for (const [file, fn] of [['test/replay/freeze.mjs', 'freezeReplay'], ['test/replay/copy.mjs', 'copyReplay'], ['test/replay/groove.mjs', 'grooveReplay']]){
  if (!existsSync(join(ROOT, file))) continue;
  const mod = await import(join(ROOT, file)); const r = mod[fn]();
  lines.push(r.text); if (r.fail){ fail++; lines.push(`${r.name}: ${r.fail} FAIL`); }
}

console.log(lines.join('\n'));
console.log(fail ? `\nREPLAY: ❌ ${fail} failing` : '\nREPLAY: ✅ all green');
process.exit(fail ? 1 : 0);
