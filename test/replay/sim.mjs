/* test/replay/sim.mjs — drive a beta game (beta/lib/*-game.js) with a play-recording, exactly as the page does:
   one feed() per camera frame at the recording's own frame rate, one tick() per frame. The clip loops.
   detector:'fail' replays a detector that throws on every frame (the page then feeds null). */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { frameAt } from '../../beta/lib/kp.js';

export const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
export const json = p => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
export const clip = name => existsSync(join(ROOT, `test/clips/${name}.json`)) ? json(`test/clips/${name}.json`) : null;

/* a seeded RNG so every replay run is identical (the dance lengths are random in play) */
export function seeded(seed = 7){ let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

export function run(create, rec, { detector = 'ok', maxS = 600, fps } = {}){
  const events = []; let ended = null;
  const g = create((type, d) => { events.push({ type, ...d }); if (type === 'end') ended = d; });
  const rate = fps || rec?.fps || 30, dt = 1 / rate;
  g.start(0);
  for (let t = 0; t < maxS && !ended; t += dt){
    const frame = detector === 'fail' || !rec ? null : frameAt(rec, t);
    g.feed(frame, t); g.tick(t);
  }
  return { ended, events, game: g };
}

export function table(title, cols, rows){
  const w = cols.map(c => Math.max(c.length, ...rows.map(r => String(r[c] ?? '').length)));
  const line = r => '| ' + cols.map((c, i) => String(r[c] ?? '').padEnd(w[i])).join(' | ') + ' |';
  return [`\n${title}`, line(Object.fromEntries(cols.map(c => [c, c]))), '|' + w.map(n => '-'.repeat(n + 2)).join('|') + '|', ...rows.map(line)].join('\n');
}
