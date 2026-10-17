/* test/proof/saveplay.mjs — night items D + G in the real page: play each game on a replay clip, press ⬇ Save my play
   on the medal screen, keep the file, and check window.novaEvents == the file's novaEvents == the game's own result.
   node test/proof/saveplay.mjs → docs/evidence/night/g-<game>-<timestamp>-play.json */
import { mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { serve, launch, ROOT } from '../lib/browser.mjs';

const OUT = join(ROOT, 'docs/evidence/night'); mkdirSync(OUT, { recursive: true });
const RUNS = [
  { game: 'freeze', page: 'freeze3', q: 'replay=frozen-body,dance-hype&fast=1' },
  { game: 'copy',   page: 'copy',    q: 'replay=pose-armsup,own-left-up,empty-room&poses=armsUp,leftUp,star&fast=1' },
  { game: 'groove', page: 'groove',  q: 'replay=dance-hype,frozen-body&fast=1' },
];
const { srv, url } = await serve(); const browser = await launch(); let fail = 0;
try {
  await Promise.all(RUNS.map(async r => {
    const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 390, height: 780 } }); const p = await ctx.newPage();
    await p.goto(`${url}/beta/${r.page}.html?${r.q}&checked=1&autostart=1`);
    await p.waitForSelector('#end.on', { timeout: 180000 });
    const live = await p.evaluate(() => window.novaEvents);
    const [dl] = await Promise.all([p.waitForEvent('download'), p.click('#save')]);
    const name = dl.suggestedFilename(), path = join(OUT, 'g-' + name); await dl.saveAs(path);
    const file = JSON.parse(readFileSync(path, 'utf8')), s = file.summary;
    const count = ev => file.novaEvents.filter(e => e.event === ev).length;
    const ok = /^(freeze|copy|groove)-.*-play\.json$/.test(name) && JSON.stringify(live) === JSON.stringify(file.novaEvents)
      && count('hit') === s.stars && count('skip_unseen') === s.skips && count('round_start') === s.rounds && count('medal') === 1
      && file.frames.length > 0;
    if (!ok) fail++;
    console.log(`${r.game.padEnd(7)} ${name}  frames ${file.frames.length}  events: ${['round_start', 'hit', 'skip_unseen', 'miss', 'medal'].map(e => `${e} ${count(e)}`).join(' · ')}  | game: ${s.rounds} rounds ${s.stars}⭐ ${s.skips} skips medal ${s.medal}  → ${ok ? 'PASS' : 'FAIL'}`);
    await ctx.close();
  }));
} finally { await browser.close(); srv.close(); }
process.exit(fail ? 1 : 0);
