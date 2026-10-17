/* test/proof/screens.mjs — night item C: every kid screen in both languages, one contact sheet per language.
   node test/proof/screens.mjs → docs/evidence/night/c-screens-<lang>.png (+ the single shots in a temp dir) */
import { mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { serve, launch, ROOT } from '../lib/browser.mjs';

const OUT = join(ROOT, 'docs/evidence/night'), TMP = join(OUT, '.tmp-screens');
mkdirSync(TMP, { recursive: true });
const { srv, url } = await serve(); const browser = await launch();
const shot = async (page, name) => { const p = join(TMP, name + '.png'); await page.screenshot({ path: p }); return p; };
const GAMES = [
  { page: 'freeze3', q: 'replay=frozen-body&fast=1', playAt: 6500, end: 'end' },
  { page: 'copy', q: 'replay=pose-armsup&poses=armsUp,star&fast=1', playAt: 2200, end: 'end' },
  { page: 'groove', q: 'replay=dance-hype&fast=1', playAt: 5000, end: 'end' },
];
try {
  for (const lang of ['en', 'he']){
    const files = [];
    const ctx = await browser.newContext({ viewport: { width: 390, height: 780 } });
    // launcher: Doctor, then menu
    let p = await ctx.newPage(); await p.goto(`${url}/beta/index.html?replay=doc-too-close&lang=${lang}`); await p.waitForTimeout(2500);
    files.push(await shot(p, `${lang}-0-doctor`)); await p.click('#doctor .go'); await p.waitForTimeout(600); files.push(await shot(p, `${lang}-1-menu`)); await p.close();
    // each game: start screen, mid-play, medal
    const runs = await Promise.all(GAMES.map(async (g, i) => {
      const pg = await ctx.newPage(); const out = [];
      await pg.goto(`${url}/beta/${g.page}.html?${g.q}&lang=${lang}&checked=1`); await pg.waitForTimeout(800);
      out.push(await shot(pg, `${lang}-${i + 2}a-${g.page}-start`));
      await pg.click('#go'); await pg.waitForTimeout(g.playAt); out.push(await shot(pg, `${lang}-${i + 2}b-${g.page}-play`));
      await pg.waitForSelector('#end.on', { timeout: 120000 }); await pg.waitForTimeout(600); out.push(await shot(pg, `${lang}-${i + 2}c-${g.page}-medal`));
      await pg.close(); return out;
    }));
    files.push(...runs.flat());
    await ctx.close();
    const sheet = join(OUT, `c-screens-${lang}.png`), n = files.length;
    execFileSync('ffmpeg', ['-nostdin', '-v', 'error', '-y', ...files.flatMap(f => ['-i', f]), '-filter_complex',
      files.map((_, i) => `[${i}]scale=195:390[s${i}];`).join('') + files.map((_, i) => `[s${i}]`).join('') + `xstack=inputs=${n}:layout=` +
      files.map((_, i) => `${(i % 6) * 195}_${Math.floor(i / 6) * 390}`).join('|') + ':fill=black', sheet]);
    console.log(`${lang}: ${n} screens → ${sheet}`);
  }
} finally { await browser.close(); srv.close(); rmSync(TMP, { recursive: true, force: true }); }
