// Layout probe: 5 cards must sit 3 + 2 with the second row CENTRED, and the
// phone breakpoint must collapse to one full-width column. Geometry only —
// no Nova, no worker, no pod.
const { chromium } = require('playwright-core');
const path = require('path');

const ROOT = 'C:/Users/ADMIN/projects/dance-project';

function rows(boxes){                       // group by y, tolerate 2px jitter
  const out = [];
  for (const b of boxes){
    const r = out.find(r => Math.abs(r.y - b.y) < 4);
    if (r) r.items.push(b); else out.push({ y: b.y, items: [b] });
  }
  return out.sort((a,b) => a.y - b.y);
}

(async () => {
  const browser = await chromium.launch();
  let fail = 0;
  const check = (name, ok, detail) => {
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
    if (!ok) fail++;
  };

  for (const [file, sel, phase] of [
    ['games.html',      '.card',        null],
    ['nova-joined.html','.picker-card', 'phase-picker'],
  ]){
    for (const [label, vp] of [['desktop',{width:1280,height:900}], ['phone',{width:390,height:844}]]){
      const page = await browser.newPage({ viewport: vp });
      await page.goto('file:///' + path.posix.join(ROOT, file));
      await page.waitForTimeout(400);
      if (phase) {                          // nova-joined boots on the intro phase
        await page.evaluate(id => {
          document.querySelectorAll('.phase').forEach(p => p.style.display = 'none');
          const el = document.getElementById(id);
          el.style.display = 'flex'; el.classList.add('active');
        }, phase);
        await page.waitForTimeout(300);
      }
      const boxes = await page.$$eval(sel, els => els
        .filter(e => e.offsetParent !== null)
        .map(e => { const r = e.getBoundingClientRect();
                    return { x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width),
                             name:(e.textContent||'').trim().replace(/\s+/g,' ').slice(0,20) }; }));

      const tag = `${file} @${label}`;
      check(`${tag}: 5 cards visible`, boxes.length === 5, `${boxes.length} found`);
      check(`${tag}: no Bounce card`, !boxes.some(b => /bounce/i.test(b.name)),
            boxes.map(b => b.name).join(' | '));

      const rs = rows(boxes);
      if (label === 'desktop'){
        check(`${tag}: rows are 3 + 2`,
              rs.length === 2 && rs[0].items.length === 3 && rs[1].items.length === 2,
              rs.map(r => r.items.length).join('+'));
        if (rs.length === 2 && rs[1].items.length === 2){
          const mid = r => { const s = r.items.map(i => i.x); const e = r.items.map(i => i.x + i.w);
                             return (Math.min(...s) + Math.max(...e)) / 2; };
          const d = Math.abs(mid(rs[0]) - mid(rs[1]));
          check(`${tag}: last row centred`, d < 6, `centres differ by ${d.toFixed(1)}px`);
        }
      } else {
        check(`${tag}: single column`, rs.length === 5, `${rs.length} rows`);
        const widths = new Set(boxes.map(b => b.w));
        check(`${tag}: cards full width`, widths.size === 1 && boxes[0].w > vp.width * 0.8,
              `w=${[...widths].join(',')} of ${vp.width}`);
      }
      const shot = process.argv[2] ? `${process.argv[2]}/${file}-${label}.png` : null;
      if (shot) await page.screenshot({ path: shot, fullPage: true });
      await page.close();
    }
  }
  await browser.close();
  console.log(fail ? `\n${fail} FAILED` : '\nALL PASS');
  process.exit(fail ? 1 : 0);
})();
