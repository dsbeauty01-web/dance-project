/* test/clips/track.mjs — pose-track replay clips: node test/clips/track.mjs [name …]
   Runs test/clips/track.html (MoveNet, the games' detector) in headless Chromium on test/clips/src/<name>.webm
   and writes test/clips/<name>.json in the play-recording format. With no names: every video in src/. */
import { readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { execSync } from 'node:child_process';
import { serve, launch, ROOT } from '../lib/browser.mjs';

const SRC = join(ROOT, 'test/clips/src');
const names = process.argv.slice(2).length ? process.argv.slice(2) : readdirSync(SRC).filter(f => f.endsWith('.webm')).map(f => f.slice(0, -5));
const { srv, url } = await serve();
const browser = await launch();
try {
  for (const name of names){
    const page = await browser.newPage();
    page.on('console', m => m.type() === 'error' && console.error('  [page]', m.text()));
    await page.goto(`${url}/test/clips/track.html`);
    await page.waitForFunction(() => window.trackReady, null, { timeout: 120000 });
    const rate = +(process.env.FPS || 0) || probeFps(name);
    const rec = await page.evaluate(([src, f]) => window.track(src, f), [`src/${name}.webm`, rate]);
    rec.src = `test/clips/src/${name}.webm`;
    writeFileSync(join(ROOT, `test/clips/${name}.json`), JSON.stringify(rec));
    const seen = rec.frames.filter(f => (f.lShoulder?.[2] ?? 0) >= 0.3 && (f.rShoulder?.[2] ?? 0) >= 0.3).length;
    console.log(`${name.padEnd(14)} ${rec.frames.length} frames @${rate}fps  ${rec.w}x${rec.h}  shoulders seen ${seen}/${rec.frames.length}`);
    await page.close();
  }
} finally { await browser.close(); srv.close(); }

function probeFps(name){   // the clip's own frame rate (ffprobe), so no frame is skipped or duplicated
  try { const out = (execSync(`ffprobe -v error -select_streams v -show_entries stream=r_frame_rate -of csv=p=0 "${join(SRC, name + '.webm')}"`, { encoding: 'utf8' })).trim();
    const [a, b] = out.split('/').map(Number); return Math.round(a / (b || 1)); } catch { return 30; }
}
