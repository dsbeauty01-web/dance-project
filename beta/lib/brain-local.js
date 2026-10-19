/* beta/lib/brain-local.js — Nova's LOCAL BRAIN for a game round: pre-game, between rounds, after the medal.
   Pure (no DOM, no audio) → testable in Node. The page feeds it the game's events and gets back short lines
   to say (recorded voice where one exists, speech synthesis for the rest). Zero cost, no pod, no key.

   Rules it lives by (performance-feedback research, kids 4–10):
   · Truth Law — she only talks about what the judge actually detected; silence beats a lie.
   · Praise is SPECIFIC and about the move ("you held the flamingo the whole time"), not the child ("good girl").
   · Correction is one small, external-focus tip ("when the music stops, stop your hands first"), never negative.
   · Memory — every line can refer to what just happened or to the streak; the recap tells the story of the round.
   · No numbers on screen or in speech: stars, animals, "two in a row" — never "80%".
   · Short: one breath per line. She never talks over the freeze sting.
   API: const B = createLocalBrain({ lang:'en'|'he', g:'f'|'m', rng }); B.react(type, d) → { text, key, delayMs } | null
        B.recap(summary) → string[] (the after-game story, 2–3 lines)                     Written by the architect. */

const pick = (rng, arr) => arr[Math.floor(rng() * arr.length)];

const ANIMAL = {
  en: { flamingo: 'flamingo', bear: 'bear', frog: 'frog', star: 'star', statue: 'statue' },
  he: { flamingo: 'פלמינגו', bear: 'דוב', frog: 'צפרדע', star: 'כוכב', statue: 'פסל' },
};

/* lines. {a} = animal. Hebrew verbs that change by gender use {stop} / {hold} / {come} slots filled per g. */
const L = {
  en: {
    intro:      ['Dance when the music plays. When it stops — freeze like the animal I show you! Ready?',
                 'Here is the game: music on, you dance. Music off, you freeze! Let us go!'],
    calibrated: ['I can see you! Here comes the music.', 'Got you! Music… starting!'],
    hype1:      ['Dance, dance, dance!', 'Show me your moves!', 'Wiggle everything!'],
    afterStar:  ['Yes! Another one coming — keep dancing!', 'You are a freeze champion. Again!', 'That was perfect. Dance!'],
    streak2:    ['Two in a row! Freeze master!', 'Two frozen! Can you make it three?'],
    streak3:    ['Three in a row — you are ICE!', 'Unstoppable! Three!'],
    streakMore: ['Still frozen! You are made of ice!', 'Another one! Nobody can move you!', 'The statue champion strikes again!'],
    afterAlmost:['So close! You froze — then moved at the very end. This time hold one more breath.',
                 'Almost! Next time, when it stops, stay frozen a little longer.'],
    afterMiss:  ['The music tricked you! When it stops — stop your hands first, then everything.',
                 'Next time: music stops, you turn into a statue. Even your fingers!'],
    afterSkip:  ['I lost you for a moment. Step back so I can see all of you.',
                 'Come to the middle of the picture, I want to see your whole body!'],
    starLow:    ['Not even a wobble — you held the {a} the whole time!', 'Perfect {a}! Totally still!'],
    starWobble: ['A tiny wobble, but you held the {a}!', 'You held it! The {a} is yours!'],
    almost:     ['You froze like a {a}… and then moved right at the end!', 'Almost a {a}! Hold it a moment longer!'],
    missed:     ['The {a} got away — the music stopped and you kept dancing!', 'Oops, you kept moving. Freeze when it stops!'],
    skip:       ['I could not see you — where did you go?', 'Come back into the picture!'],
    endGold:    ['What a round! You froze like a real {best}, and you never stopped trying.'],
    endSilver:  ['Great round! Your best freeze was the {best}.'],
    endBronze:  ['You got stars, and you learned the trick: music stops — statue!'],
    endNone:    ['The music was tricky today. Next time: when it stops, stop your hands first.'],
    trendUp:    ['You started moving, then froze two in a row — that is learning!'],
    again:      ['Again? Or try Copy Nova?', 'One more round? I am ready when you are.'],
  },
  he: {
    intro:      ['{dance} כשהמוזיקה מתנגנת. כשהיא נעצרת — {freeze} כמו החיה שאני מראה! {ready}?',
                 'ככה משחקים: יש מוזיקה — {dance}. אין מוזיקה — {freeze}! יאללה!'],
    calibrated: ['אני רואה אותך! הנה המוזיקה.', 'מעולה! המוזיקה… מתחילה!'],
    hype1:      ['{dance}, {dance}, {dance}!', '{show} לי את התנועות!', 'לנענע הכול!'],
    afterStar:  ['כן! עוד אחד מגיע — {keepDancing}!', '{champion} של הקפאה. שוב!', 'זה היה מושלם. {dance}!'],
    streak2:    ['שניים ברצף! {master} הקפאה!', 'שניים קפואים! {can} שלושה?'],
    streak3:    ['שלושה ברצף — קרח!', 'אי אפשר לעצור אותך! שלושה!'],
    streakMore: ['עדיין קפוא! {you} מקרח!', 'עוד אחד! אף אחד לא מזיז אותך!', '{champion} הפסלים שוב!'],
    afterAlmost:['כמעט! {froze} — ואז {moved} ממש בסוף. הפעם {hold} עוד נשימה אחת.',
                 'כמעט! בפעם הבאה, כשזה נעצר, {stay} קפוא עוד קצת.'],
    afterMiss:  ['המוזיקה עבדה עליך! כשהיא נעצרת — {stop} קודם את הידיים, ואז הכול.',
                 'בפעם הבאה: המוזיקה נעצרת — {become}פסל. אפילו האצבעות!'],
    afterSkip:  ['איבדתי אותך לרגע. {stepBack} כדי שאראה את כולך.',
                 '{come} לאמצע התמונה, אני רוצה לראות את כל הגוף!'],
    starLow:    ['אפילו לא ניד — {held} את ה{a} כל הזמן!', '{a} מושלם! לגמרי בלי לזוז!'],
    starWobble: ['ניד קטן, אבל {held} את ה{a}!', '{held}! ה{a} שלך!'],
    almost:     ['{froze} כמו {a}… ואז {moved} ממש בסוף!', 'כמעט {a}! {hold} עוד רגע!'],
    missed:     ['לא הפעם, {a}! המוזיקה נעצרה ו{kept}!', 'אופס, המשכת לזוז. {freeze} כשזה נעצר!'],
    skip:       ['לא ראיתי אותך — לאן נעלמת?', '{comeBack} לתמונה!'],
    endGold:    ['איזה סיבוב! {froze} כמו {best} אמיתי, ולא הפסקת לנסות.'],
    endSilver:  ['סיבוב מעולה! ההקפאה הכי טובה שלך הייתה ה{best}.'],
    endBronze:  ['קיבלת כוכבים, ולמדת את הטריק: המוזיקה נעצרת — פסל!'],
    endNone:    ['המוזיקה הייתה טריקית היום. בפעם הבאה: כשהיא נעצרת, {stop} קודם את הידיים.'],
    trendUp:    ['{started} בתזוזה, ואז {froze} פעמיים ברצף — זה נקרא ללמוד!'],
    again:      ['עוד פעם? או {try} את "חקה את נובה"?', 'עוד סיבוב? אני מוכנה כש{you} {ready2}.'],
  },
};
/* Hebrew gender slots */
const HE_G = {
  f: { dance: 'תרקדי', freeze: 'תקפאי', ready: 'מוכנה', show: 'תראי', keepDancing: 'תמשיכי לרקוד', champion: 'אלופה', master: 'מלכת', can: 'תצליחי', froze: 'קפאת', moved: 'זזת', hold: 'תחזיקי', stay: 'תישארי', stop: 'תעצרי', become: 'תהפכי ל', stepBack: 'תתרחקי קצת', come: 'תבואי', held: 'החזקת', kept: 'המשכת לרקוד', comeBack: 'תחזרי', started: 'התחלת', try: 'תנסי', you: 'את', ready2: 'מוכנה' },
  m: { dance: 'תרקוד', freeze: 'תקפא', ready: 'מוכן', show: 'תראה', keepDancing: 'תמשיך לרקוד', champion: 'אלוף', master: 'מלך', can: 'תצליח', froze: 'קפאת', moved: 'זזת', hold: 'תחזיק', stay: 'תישאר', stop: 'תעצור', become: 'תהפוך ל', stepBack: 'תתרחק קצת', come: 'תבוא', held: 'החזקת', kept: 'המשכת לרקוד', comeBack: 'תחזור', started: 'התחלת', try: 'תנסה', you: 'אתה', ready2: 'מוכן' },
};

export function createLocalBrain({ lang = 'en', g = 'f', rng = Math.random } = {}){
  const T = L[lang] || L.en, A = ANIMAL[lang] || ANIMAL.en, G = HE_G[g] || HE_G.f;
  const M = { results: [], streak: 0, lastSaid: {}, animal: null };
  const fill = (s, vars = {}) => s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? G[k] ?? '');
  const say = (key, vars, delayMs = 0) => {   // never the same sentence twice in a row for one key
    let arr = T[key]; if (!arr) return null;
    let text = fill(pick(rng, arr), vars); if (arr.length > 1 && text === M.lastSaid[key]) text = fill(pick(rng, arr.filter(x => fill(x, vars) !== text)) || arr[0], vars);
    M.lastSaid[key] = text; return { key, text, delayMs };
  };

  /* react(type, d) — the same events freeze-game.js emits (and the page's 'intro' before START) */
  function react(type, d = {}){
    if (type === 'intro') return say('intro');
    if (type === 'calibrated') return say('calibrated', {}, 1700);                    // after the recorded countdown line
    if (type === 'phase' && d.phase === 'dance'){
      if (d.round === 1) return say('hype1', {}, 3800);                              // after "I can see you" — not on top of it
      const prev = M.results[M.results.length - 1];                                 // coaching = about what JUST happened
      if (!prev) return say('hype1');
      if (prev.outcome === 'star') return M.streak >= 4 ? say('streakMore') : M.streak === 3 ? say('streak3') : M.streak === 2 ? say('streak2') : say('afterStar');
      if (prev.outcome === 'skip') return say('afterSkip');
      return prev.hold === 'almost' ? say('afterAlmost') : say('afterMiss');
    }
    if (type === 'freeze'){ M.animal = d.animal; return null; }                       // the sting + the card speak here, not her
    if (type === 'star'){ M.results.push(d); M.streak++;
      const wobble = d.maxE != null && d.thrMove != null && d.maxE > 0.6 * d.thrMove;    // held, but it was close
      return say(wobble ? 'starWobble' : 'starLow', { a: A[d.animal || M.animal] || '' }, 1300); }
    if (type === 'notyet'){ M.results.push(d); M.streak = 0;
      return say(d.hold === 'almost' ? 'almost' : 'missed', { a: A[d.animal || M.animal] || '' }, 1300); }
    if (type === 'skip'){ M.results.push(d); M.streak = 0; return say('skip', {}, 600); }
    if (type === 'end') return null;                                                  // the page asks recap() instead
    return null;
  }

  /* recap(summary) — 2–3 lines that tell the story of THIS round (Truth Law: only from the results) */
  function recap(S = {}){
    const R = S.results || M.results, stars = R.filter(r => r.outcome === 'star');
    const out = [];
    // best freeze = the stillest star (lowest maxE), named by its animal
    const best = stars.length ? stars.reduce((a, b) => (a.maxE ?? 1) <= (b.maxE ?? 1) ? a : b) : null;
    const bestName = best ? (A[best.animal || 'statue'] || '') : '';
    if (S.medal === 'gold') out.push(say('endGold', { best: bestName }).text);
    else if (S.medal === 'silver') out.push(say('endSilver', { best: bestName }).text);
    else if (stars.length) out.push(say('endBronze').text);
    else out.push(say('endNone').text);
    // trend: first judged rounds not held, later two stars in a row → say it
    const judged = R.filter(r => r.outcome !== 'skip');
    const firstMissed = judged.length >= 3 && judged[0].outcome !== 'star';
    let laterStreak = false; for (let i = 1; i < judged.length; i++) if (judged[i].outcome === 'star' && judged[i - 1].outcome === 'star') laterStreak = true;
    if (firstMissed && laterStreak) out.push(say('trendUp').text);
    out.push(say('again').text);
    return out;
  }

  return { react, recap, memory: M };
}
