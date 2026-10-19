/* test/lib/browser.mjs — a static server for the repo root + a headless Chromium (playwright-core, already a
   repo dependency). Used by the clip tracker and the proof-video recorder. Network (TF.js + MoveNet weights)
   goes through the environment's HTTPS proxy when one is set. */
import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, extname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

export const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const TYPES = { '.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript', '.json':'application/json', '.css':'text/css',
  '.mp4':'video/mp4', '.mp3':'audio/mpeg', '.png':'image/png', '.jpg':'image/jpeg', '.svg':'image/svg+xml' };

export function serve(port = 0){
  const srv = http.createServer(async (req, res) => {
    try {
      const p = join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
      if (!p.startsWith(ROOT)) { res.writeHead(403).end(); return; }
      const st = await stat(p); const body = await readFile(st.isDirectory() ? join(p, 'index.html') : p);
      const type = TYPES[extname(st.isDirectory() ? 'index.html' : p)] || 'application/octet-stream';
      const range = req.headers.range?.match(/bytes=(\d*)-(\d*)/);          // <video> seeks need ranges
      if (range){ const a = +range[1] || 0, b = range[2] ? +range[2] : body.length - 1;
        res.writeHead(206, { 'Content-Type': type, 'Content-Range': `bytes ${a}-${b}/${body.length}`, 'Accept-Ranges': 'bytes', 'Content-Length': b - a + 1 });
        res.end(body.subarray(a, b + 1)); return; }
      res.writeHead(200, { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Content-Length': body.length }); res.end(body);
    } catch { res.writeHead(404).end(); }
  });
  return new Promise(ok => srv.listen(port, '127.0.0.1', () => ok({ srv, url: `http://127.0.0.1:${srv.address().port}` })));
}

const CANDIDATES = [process.env.CHROMIUM_PATH, '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', '/opt/pw-browsers/chromium/chrome-linux/chrome'];
export async function launch(){
  const executablePath = CANDIDATES.find(p => p && existsSync(p));
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost' } : undefined;
  return chromium.launch({ executablePath, proxy, args: ['--autoplay-policy=no-user-gesture-required', '--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
}
