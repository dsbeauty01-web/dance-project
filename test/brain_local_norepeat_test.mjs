// node test/brain_local_norepeat_test.mjs — NOVA-GO5: in one game she never opens two lines the same way
import { createLocalBrain } from '../beta/lib/brain-local.js';
let bad = 0;
for (const lang of ['en', 'he']) for (let seed = 1; seed <= 50; seed++) {
  let x = seed; const rng = () => (x = (x * 16807) % 2147483647) / 2147483647;
  const B = createLocalBrain({ lang, rng }); const heads = [];
  for (let r = 1; r <= 4; r++) {                  // Refael's play: four rounds, every one a clean star
    const out = B.react('star', { round: r, animal: ['bear', 'frog', 'star', 'flamingo'][r - 1], stillness: 0.01 });
    if (out) heads.push(out.text.split(/(?<=[.!?…])\s|\s[—–-]\s/)[0].trim().toLowerCase());
  }
  if (new Set(heads).size !== heads.length) { bad++; console.log('FAIL', lang, seed, heads); }
}
console.log(bad ? bad + ' FAILED' : 'ALL PASS (4 stars in a row, 50 seeds x EN+HE: no repeated opening)'); process.exit(bad ? 1 : 0);
