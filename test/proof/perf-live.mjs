/* test/proof/perf-live.mjs — night item F: the LIVE path (fake webcam → MoveNet in the page) under CPU throttle.
   node test/proof/perf-live.mjs <video.y4m> <throttle> <wasm|webgl>   (?skip=1 in the URL to measure without frame-skip) */
import { chromium } from 'playwright-core';
import { serve } from '../lib/browser.mjs';
const [y4m, throttle, backend] = process.argv.slice(2);
const { srv, url } = await serve();
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', proxy: { server: process.env.HTTPS_PROXY, bypass: '127.0.0.1' },
  args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-video-capture=' + y4m, '--autoplay-policy=no-user-gesture-required'] });
const ctx = await b.newContext({ viewport: { width: 432, height: 768 }, permissions: ['camera'] }); const p = await ctx.newPage();
const cdp = await ctx.newCDPSession(p); await cdp.send('Emulation.setCPUThrottlingRate', { rate: +throttle });
await p.goto(`${url}/beta/freeze3.html?backend=${backend}&checked=1&autostart=1`); await p.waitForTimeout(15000);
const m = await p.evaluate(() => new Promise(ok => { let raf = 0; const f0 = window.__fedFrames || 0, t0 = performance.now();
  const tick = () => { raf++; if (performance.now() - t0 < 10000) requestAnimationFrame(tick); else ok({ raf: raf / 10, fed: ((window.__fedFrames || 0) - f0) / 10 }); }; requestAnimationFrame(tick); }));
console.log(`live camera · MoveNet ${backend} · CPU ${throttle}× → lights ${m.raf.toFixed(1)} fps · judged ${m.fed.toFixed(1)} fps`);
await b.close(); srv.close();
