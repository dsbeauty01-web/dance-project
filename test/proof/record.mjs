/* test/proof/record.mjs — the gate videos: a game page running on replay clips in headless Chromium, recorded.
   node test/proof/record.mjs <out-name> <seconds> <page?query> [<seconds> <page?query> …]
   Several segments are recorded one after another and joined (ffmpeg) into docs/evidence/6h/<out-name>.mp4. */
import { mkdirSync, readdirSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { serve, launch, ROOT } from '../lib/browser.mjs';

const [out, ...rest] = process.argv.slice(2);
const segs = []; for (let i = 0; i < rest.length; i += 2) segs.push({ secs: +rest[i], path: rest[i + 1] });
const OUT = join(ROOT, 'docs/evidence/6h'), TMP = join(OUT, '.tmp-' + out);
mkdirSync(TMP, { recursive: true });
const { srv, url } = await serve(); const browser = await launch();
const files = [];
try {
  for (const [i, s] of segs.entries()){
    const ctx = await browser.newContext({ viewport: { width: 432, height: 768 }, deviceScaleFactor: 1, recordVideo: { dir: TMP, size: { width: 432, height: 768 } } });
    const page = await ctx.newPage();
    const logs = []; page.on('console', m => logs.push(`[${m.type()}] ${m.text()}`)); page.on('pageerror', e => logs.push('[pageerror] ' + e.message));
    await page.goto(`${url}/${s.path}`);
    await page.waitForTimeout(s.secs * 1000);
    const shot = join(OUT, `${out}-${i + 1}.png`); await page.screenshot({ path: shot });
    const v = page.video(); await ctx.close(); const p = await v.path(); files.push(p);
    writeFileSync(join(OUT, `${out}-${i + 1}.log`), logs.join('\n'));
    console.log(`segment ${i + 1}: ${s.path} (${s.secs}s) → ${p}  console lines: ${logs.length}${logs.some(l => /error/i.test(l)) ? '  ⚠ errors — see .log' : ''}`);
  }
} finally { await browser.close(); srv.close(); }
const list = join(TMP, 'list.txt'); writeFileSync(list, files.map(f => `file '${f}'`).join('\n'));
const mp4 = join(OUT, `${out}.mp4`);
execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4]);
rmSync(TMP, { recursive: true, force: true });
const dur = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4], { encoding: 'utf8' }).trim();
console.log(`video: ${mp4}  ${(+dur).toFixed(1)}s`);
