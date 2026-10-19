/* test/replay/brain.mjs — Nova's local brain (beta/lib/brain-local.js) replayed over a REAL round:
   Refael's Freeze-with-Nova play, 2026-10-19 (test/clips/refael-freeze-round-2026-10-19.json — 2⭐, 3 not-yet, 1 skip).
   Truth Law checks: she praises only on 'star', coaches only after a miss/skip, never speaks over the freeze sting,
   names the right animal, tells a recap that matches the medal, and never says a number. EN and HE. */
import { createLocalBrain } from '../../beta/lib/brain-local.js';
import { json, table } from './sim.mjs';

export function brainReplay(){
  const rec = json('test/clips/refael-freeze-round-2026-10-19.json');
  const rows = []; let fail = 0;
  const ok = (what, cond, got = '') => { rows.push({ check: what, result: cond ? 'PASS' : 'FAIL', got: String(got).slice(0, 70) }); if (!cond) fail++; };
  for (const lang of ['en', 'he']){
    let seed = 3; const rng = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
    const B = createLocalBrain({ lang, g: 'm', rng });
    const said = []; const intro = B.react('intro'); said.push(['intro', intro]);
    for (const e of rec.events){ const r = B.react(e.type, e); said.push([e.type, r, e]); }
    const recap = B.recap(rec.summary);
    const text = said.filter(x => x[1]).map(x => x[1].text).concat(recap).join(' | ');
    ok(`${lang}: speaks before START`, !!intro?.text, intro?.text);
    ok(`${lang}: silent on every 'freeze' (the sting speaks)`, said.filter(x => x[0] === 'freeze').every(x => !x[1]));
    const stars = said.filter(x => x[0] === 'star'); ok(`${lang}: a line for every star (2)`, stars.length === 2 && stars.every(x => x[1]?.text));
    const ANIMALS = lang === 'he' ? ['פלמינגו', 'דוב', 'צפרדע', 'כוכב', 'פסל'] : ['flamingo', 'bear', 'frog', 'star', 'statue'];
    ok(`${lang}: star line names an animal`, stars.every(x => ANIMALS.some(a => x[1].text.includes(a))), stars.map(x => x[1].text).join(' / '));
    const miss = said.filter(x => x[0] === 'notyet'); ok(`${lang}: a line for every not-yet (3)`, miss.length === 3 && miss.every(x => x[1]?.text));
    const almost = miss.find(x => x[2].hold === 'almost'); ok(`${lang}: 'almost' gets the almost line`, !!almost && almost[1].key === 'almost', almost?.[1].text);
    ok(`${lang}: a clean miss gets the missed line`, miss.filter(x => x[2].hold === 'missed').every(x => x[1].key === 'missed'));
    const skip = said.find(x => x[0] === 'skip'); ok(`${lang}: skip → come back into the picture`, !!skip?.[1] && /picture|see|תמונה|נעלמת/.test(skip[1].text), skip?.[1]?.text);
    const coach = said.filter(x => x[0] === 'phase' && x[2]?.phase === 'dance' && x[2].round > 1);
    ok(`${lang}: coaches before every round after the first (5)`, coach.length === 5 && coach.every(x => x[1]?.text));
    ok(`${lang}: after the skip she asks to step back`, /back|middle|תתרחק|אמצע/.test(coach.find(x => x[2].round === 3)?.[1]?.text || ''), coach.find(x => x[2].round === 3)?.[1]?.text);
    ok(`${lang}: recap 2–3 lines, matches bronze (stars but no gold words)`, recap.length >= 2 && recap.length <= 3 && !/gold|זהב/i.test(recap[0]), recap.join(' / '));
    ok(`${lang}: never says a digit`, !/\d/.test(text));
  }
  return { name: 'Brain', fail, text: table('BRAIN (beta/lib/brain-local.js) — Refael\'s real round, EN + HE', ['check', 'result', 'got'], rows) };
}
if (import.meta.url === `file://${process.argv[1]}`){ const r = brainReplay(); console.log(r.text); process.exit(r.fail ? 1 : 0); }
