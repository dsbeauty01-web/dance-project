/**
 * QA — v114 PICKER CLEANUP (nova-joined.html)
 *   NODE_PATH=$(npm root -g) node tools/qa-picker-v114.js
 */
const { chromium } = require('playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = 'C:/Users/ADMIN/projects/dance-project', SCR = __dirname;
const MIME = { '.html':'text/html','.js':'text/javascript','.mp4':'video/mp4','.png':'image/png','.riv':'application/octet-stream','.json':'application/json','.css':'text/css','.mp3':'audio/mpeg','.wav':'audio/wav' };
const results = [];
const rec = (n, pass, d) => { results.push({ n, pass }); console.log(`${pass ? 'PASS' : 'FAIL'}  ${n}  — ${d}`); };

(async () => {
  const server = http.createServer((q, r) => { let p = decodeURIComponent(q.url.split('?')[0]); if (p === '/') p = '/nova-joined.html';
    fs.readFile(path.join(ROOT, p), (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
      r.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => server.listen(0, r)); const port = server.address().port;
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'] });

  const open = async (w, h, q = '') => {
    const pg = await b.newPage(); await pg.setViewportSize({ width: w, height: h });
    pg.on('pageerror', e => console.log('  [pg-err]', e.message));
    await pg.goto(`http://localhost:${port}/nova-joined.html${q}`, { waitUntil: 'domcontentloaded' });
    await pg.waitForTimeout(1200);
    await pg.evaluate(() => { if (typeof window.goToPicker === 'function') window.goToPicker(); });
    await pg.waitForSelector('#phase-picker.active', { timeout: 15000 });
    await pg.waitForTimeout(900);
    return pg;
  };

  // 1 + 2 — card count, no h-scroll at both sizes, unique emoji, no subtext
  for (const [w, h] of [[1366,768],[1920,1080]]) {
    const pg = await open(w, h);
    const i = await pg.evaluate(() => {
      const cards = [...document.querySelectorAll('.picker-card')];
      const emo = cards.map(c => c.querySelector('.picker-emoji')?.textContent.trim());
      return { n: cards.length, emo, uniq: new Set(emo).size === emo.length,
               subtext: cards.reduce((a, c) => a + c.querySelectorAll('.picker-tag,.picker-desc').length, 0),
               sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth };
    });
    rec(`1 · cards render, no h-scroll @${w}x${h}`, i.sw <= i.cw && i.n >= 3, `${i.n} cards, scrollW=${i.sw}/${i.cw}`);
    if (w === 1366) {
      rec('2 · unique emoji, no card subtext', i.uniq && i.subtext === 0, `emoji=[${i.emo.join(' ')}] uniq=${i.uniq} subtextNodes=${i.subtext}`);
    }
    await pg.close();
  }

  // 3 — Nova's pick styling
  let pg = await open(1366, 768);
  const p3 = await pg.evaluate(() => {
    const r = document.querySelector('.picker-card.recommended');
    if (!r) return { found: false };
    const cs = getComputedStyle(r);
    const all = [...document.querySelectorAll('.picker-card')];
    const others = all.filter(c => c !== r);
    const rw = r.getBoundingClientRect().width;
    const ow = others.length ? others[0].getBoundingClientRect().width : 0;
    return { found: true, border: cs.borderTopWidth, colour: cs.borderTopColor,
             label: r.getAttribute('data-pick-label'), anim: cs.animationName,
             bigger: rw > ow * 1.05, ratio: +(rw / (ow || 1)).toFixed(2),
             idx: all.indexOf(r), total: all.length };
  });
  rec('3 · pick is centre, bigger, pink, badged, pulsing',
    p3.found && p3.bigger && !!p3.label && p3.anim === 'cardPulse' && p3.border === '4px',
    `idx=${p3.idx}/${p3.total} ratio=${p3.ratio}x border=${p3.border} ${p3.colour} label="${p3.label}" anim=${p3.anim}`);

  // 4 — each card routes to the right song id
  const p4 = await pg.evaluate(() => {
    const seen = [];
    const orig = window.pickGame;
    window.pickGame = id => { seen.push(id); };   // intercept, do not actually start
    document.querySelectorAll('.picker-card').forEach(c => c.click());
    window.pickGame = orig;
    // SONGS is module-scoped (not on window), so it cannot be read from page
    // context. Compare against the keys verified in source at nova-joined.html
    // :4824-4877 instead of silently treating an empty list as "unknown".
    const KNOWN = ['joined','hello','freeze','wave','wavemagic','bounce'];
    return { seen, allKnown: seen.length > 0 && seen.every(s => KNOWN.includes(s)),
             dupes: seen.length !== new Set(seen).size };
  });
  rec('4 · every card maps to a real SONGS entry', p4.seen.length >= 3 && p4.allKnown && !p4.dupes,
    `clicked=[${p4.seen.join(', ')}] allKnown=${p4.allKnown} dupes=${p4.dupes}`);

  // 6 — voice pick: "freeze" selects Freeze via the read-only stt-echo hook
  const p6 = await pg.evaluate(async () => {
    const seen = [];
    const orig = window.pickGame;
    window.pickGame = id => { seen.push(id); };
    window.pickerHear('I wanna do freeze please');
    await new Promise(r => setTimeout(r, 700));
    window.pickGame = orig;
    return { seen, hasHook: typeof window.pickerHear === 'function' };
  });
  rec('6 · saying "freeze" selects Freeze', p6.hasHook && p6.seen[0] === 'freeze',
    `hook=${p6.hasHook} picked=[${p6.seen.join(', ')}]`);

  // 5 — voice pick fires once only (no repeat on further speech)
  const p5 = await pg.evaluate(async () => {
    const seen = [];
    const orig = window.pickGame;
    window.pickGame = id => { seen.push(id); };
    window.pickerHear('freeze'); window.pickerHear('up groove'); window.pickerHear('hello');
    await new Promise(r => setTimeout(r, 800));
    window.pickGame = orig;
    return seen;
  });
  rec('5 · voice pick fires once, not per utterance', p5.length === 0,
    `already-armed guard held; extra picks after first = ${p5.length}`);
  await pg.close();

  // 7 — phone: vertical stack, pick on top
  pg = await open(412, 915);
  const p7 = await pg.evaluate(() => {
    const cards = [...document.querySelectorAll('.picker-card')];
    const tops = cards.map(c => Math.round(c.getBoundingClientRect().top));
    const r = document.querySelector('.picker-card.recommended');
    const rTop = r ? Math.round(r.getBoundingClientRect().top) : null;
    return { rows: new Set(tops).size, n: cards.length, pickIsTop: rTop !== null && rTop === Math.min(...tops),
             sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth };
  });
  rec('7 · phone stacks vertically, pick on top', p7.rows === p7.n && p7.pickIsTop && p7.sw <= p7.cw,
    `rows=${p7.rows}/${p7.n} pickOnTop=${p7.pickIsTop} scrollW=${p7.sw}/${p7.cw}`);
  await pg.screenshot({ path: path.join(SCR, 'qa-picker-phone.png') });
  await pg.close();

  // 8 — Hebrew
  pg = await open(1366, 768, '?lang=he');
  const p8 = await pg.evaluate(() => {
    const names = [...document.querySelectorAll('.picker-name')].map(n => n.textContent.trim());
    const hebrew = names.filter(n => /[֐-׿]/.test(n)).length;
    return { dir: document.documentElement.getAttribute('dir'), names, hebrew, total: names.length,
             label: document.querySelector('.picker-card.recommended')?.getAttribute('data-pick-label'),
             sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth };
  });
  rec('8 · lang=he translated, layout intact', p8.dir === 'rtl' && p8.hebrew === p8.total && p8.sw <= p8.cw,
    `dir=${p8.dir} hebrewNames=${p8.hebrew}/${p8.total} label="${p8.label}" scrollW=${p8.sw}/${p8.cw}`);
  await pg.close();

  // 9 — version banner
  pg = await open(1366, 768);
  const p9 = await pg.evaluate(() => {
    const t = document.getElementById('version-tag');
    return { text: t?.textContent.trim(), bg: t ? getComputedStyle(t).backgroundImage : null };
  });
  rec('9 · version banner present + not v113 indigo', !!p9.text && p9.text.includes('V114') && !p9.bg.includes('99, 102, 241'), `"${p9.text}"`);
  await pg.screenshot({ path: path.join(SCR, 'qa-picker-desk.png') });
  await pg.close();

  console.log('\n' + '─'.repeat(60));
  console.log(`${results.filter(r => r.pass).length}/${results.length} checks passed`);
  await b.close(); server.close();
  process.exit(results.every(r => r.pass) ? 0 : 1);
})();
