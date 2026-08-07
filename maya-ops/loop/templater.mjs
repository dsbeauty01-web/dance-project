// LOOP MODE step 1 — product truth -> the 5-part script (五段式), Hebrew.
//
// Usage:  node templater.mjs <catalog.json> <outdir> [extras.json]
//
// The playbook rules this file enforces (live-sales-playbook skill):
//   - exactly the 5 sections: hook / points / interact / urgency / close
//   - EXACTLY 3 selling points, each its own segment (segment stops between points)
//   - the live price appears at least 3 times across the block
//   - every segment's text targets <= 15 seconds spoken (~35 Hebrew words)
//   - forbidden_claims from the catalog must not appear anywhere — build FAILS if they do
//   - facts come from the catalog ONLY (TRUTH LAW); anything the founder hasn't supplied
//     renders as a [NEEDS-FOUNDER: ...] marker that also FAILS the build, so a script
//     with holes can never reach the bake.
//
// extras.json (optional, per product id) supplies what the catalog doesn't hold:
//   { "serum-c": { "gift_he": "...", "scenario_he": "...", "testimonial_he": "...",
//                  "competitor_he": "..." } }
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const [catalogPath, outDir, extrasPath] = process.argv.slice(2);
if (!catalogPath || !outDir) { console.error('usage: node templater.mjs <catalog.json> <outdir> [extras.json]'); process.exit(1); }
const catalog = JSON.parse(readFileSync(catalogPath, 'utf8'));
const extras = extrasPath ? JSON.parse(readFileSync(extrasPath, 'utf8')) : {};
mkdirSync(outDir, { recursive: true });

const need = (v, what) => v || `[NEEDS-FOUNDER: ${what}]`;
const seg = (id, role, gesture, text) => ({ id, role, gesture, text_he: text.trim(), target_secs: 15 });

let failed = false;

for (const p of catalog.products) {
  const x = extras[p.id] || {};
  const gift = need(x.gift_he, 'מתנה/קופון ללייב');
  const scenario = need(x.scenario_he, 'תרחיש שימוש');
  const testimonial = need(x.testimonial_he, 'משפט המלצה מאושר');
  const bullets = p.bullets_he ? p.bullets_he.split('·').map(s => s.trim()) : [];
  while (bullets.length < 3) bullets.push(need(null, `נקודת מכירה ${bullets.length + 1}`));

  const segs = [
    seg('hook', 'hook', 'REVEAL', `
      תראו מה יש לי בשבילכם! ${p.name_he}. במקום ${p.old_price_he} — עכשיו בלייב בלבד ${p.price_he}, ועוד מתנה: ${gift}. רק כאן, רק עכשיו.`),
    seg('point-1', 'points', 'POINT', `נקודה ראשונה: ${bullets[0]}. זה מה שעושה את ההבדל.`),
    seg('point-2', 'points', 'POINT', `ודבר שני: ${bullets[1]}. ${scenario}`),
    seg('point-3', 'points', 'POINT', `ושלישי: ${bullets[2]}. לקוחה כתבה לנו: "${testimonial}"`),
    seg('interact', 'interact', 'NUDGE', `
      עכשיו אתם: מי שכבר מכיר את ${p.name_he} — תכתבו 1. מי ששומע עליו פעם ראשונה — תכתבו 2. אני פה, עונה לכל שאלה על משלוח, מידות והנחות.`),
    seg('urgency', 'urgency', 'REVEAL', `
      בואו נסגור את זה: מחיר רגיל ${p.old_price_he}, מחיר לייב ${p.price_he}, ועוד ${gift}. המלאי ללייב הזה מוגבל — הקישור למטה, לוחצים עכשיו. שוב: ${p.price_he} בלבד.`),
    seg('close', 'close', 'WAVE', `
      עוד רגע עוברים למוצר הבא — תישארו איתי ותעשו עקוב כדי לא לפספס. ${p.name_he}, ${p.price_he}, הקישור למטה.`),
  ];

  // guards
  const all = segs.map(s => s.text_he).join(' ');
  const priceCount = all.split(p.price_he).length - 1;
  if (priceCount < 3) { console.error(`FAIL ${p.id}: live price appears ${priceCount}x, need >=3`); failed = true; }
  for (const s of segs) {
    const words = s.text_he.split(/\s+/).length;
    if (words > 40) { console.error(`FAIL ${p.id}/${s.id}: ${words} words > 40 (~15s limit)`); failed = true; }
  }
  for (const claim of (p.forbidden_claims || [])) {
    if (all.toLowerCase().includes(String(claim).toLowerCase())) { console.error(`FAIL ${p.id}: forbidden claim "${claim}" in script`); failed = true; }
  }
  const holes = all.match(/\[NEEDS-FOUNDER:[^\]]*\]/g) || [];
  for (const h of holes) console.error(`HOLE ${p.id}: ${h}`);
  if (holes.length) failed = true;

  const out = { product_id: p.id, name_he: p.name_he, price_he: p.price_he, lang: 'he',
    generated: catalog._meta?.updated || null, holes: holes.length, segments: segs };
  writeFileSync(join(outDir, `${p.id}.he.json`), JSON.stringify(out, null, 2));
  console.log(`${holes.length ? 'DRAFT (holes)' : 'OK'}: ${p.id} — ${segs.length} segments, price x${priceCount}`);
}
process.exit(failed ? 2 : 0);
