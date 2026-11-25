/* beta/lib/name-catch.js — the child's NAME out of what they said (NOVA-GO5 2026-11-24, flag `v2vintro` in beta/freeze4.html).
   Pure (no DOM). Node tests: test/name_catch_test.mjs.

   WHERE IT COMES FROM (ported, not reinvented): origin/main nova-commercial.html L4612-4665, the "v106 bulletproof name
   parser" (+ v112 / v113 fixes) of the approved intro (INTRO-V2V, law-shoulder: "the name is the ONLY thing that may arm
   the shoulder beat"). Same word lists, same sentence patterns, same next-word rule, same 4-letter floor for a bare word.
   NEW here, each marked [CLI-FILL] (no spec gives them — QUESTION for the founder):
   · the text is cleaned of punctuation first (a live transcript says "Refael." — the commercial bare-word test wanted
     letters only and would refuse it);
   · `asked: true` = this turn is the direct answer to her "What's your name?": a bare word of 2-3 letters ("Tom", "Noa")
     and a two-word answer ("Refael Sela" -> Refael) count as well. pod/rt_lk.py INPUT-LOCK already takes one name-shaped
     word of 2+ letters as the name on that turn;
   · Hebrew: the commercial parser was Latin-only, so a Hebrew name could only come from the name buttons. The patterns
     and stop words below are the Hebrew of the same rules, plus the game words the brain refuses as names (rt_lk.py,
     nephew test 2026-09-13). */

const GREETING_WORDS = new Set(['hi','hey','hello','yes','no','ok','okay','sure','what','huh','yeah','nope','um','uh','dance','play','go','wait','stop','sup','nova','well','fine','great','good','bad']);
const VERB_STATE_WORDS = new Set([
  'going','doing','trying','thinking','feeling','dancing','playing','singing','running','jumping','watching','listening','talking','calling','coming','leaving','working','waiting','sitting','standing','looking','moving','hoping','helping','asking','telling','starting','stopping','crying','laughing','smiling',
  'ready','tired','happy','sad','sorry','hungry','thirsty','cold','hot','sick','fine','okay','great','bored','excited','scared','angry','mad','done','here','there','back','home','away','outside','inside','upstairs','downstairs',
  'me','you','it','that','this','him','her','them','us','myself','yourself','itself','my','your','our','their','his','name','names','color','shirt','eyes','hair',
]);
const NEXT_WORD_DISQUALIFIES = /\b(back|here|there|to|from|with|in|out|up|down|on|off|at|for|now|today|already|just|kind|of|the|a|an)\b/i;
const BARE_NAME_BLOCKLIST = new Set(['why','who','how','wow','huh','aww','umm','hmm','yep','nah','sup','lol','ugh','oof','ouch','hii','yay']);
/* [CLI-FILL] only used for the `asked` cases (short bare word, two words): everyday words a child may answer with */
const ASKED_EXTRA = new Set(['not','dont','nothing','nobody','secret','can','cant','is','are','the','and','but','please','thanks','thank','bye','mom','mommy','dad','daddy','mama','papa','too','yes','yea','nah','idk','hear','see','am','im','its','who','guess','tell','know','maybe','test','testing','one','two','three','cool','nice','wow']);

const HE_NOT_NAMES = new Set(['כן','לא','היי','הי','שלום','מה','אוקיי','אוקי','סבבה','יאללה','תודה','ביי','מוכן','מוכנה','מוכנים','בסדר','טוב','רגע','למה','מי','איך','אני','את','אתה','זה','פה','כאן','נובה',
  'דוב','כוכב','פלמינגו','צפרדע','פסל','קפוא','גל','פריז','מוזיקה','ריקוד','משחק',                      // rt_lk.py: game words are never a name
  'רוצה','אוהב','אוהבת','יודע','יודעת','שומע','שומעת','רואה','עייף','עייפה','בן','בת','ילד','ילדה','רוקד','רוקדת','משחק','משחקת','מדבר','מדברת']);

function clean(text){ return String(text || '').replace(/[.,!?…:;"“”()\[\]]/g, ' ').replace(/\s+/g, ' ').trim(); }
function cap(w){ return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase(); }

function isValidName(word, fullText, matchIdx){
  const lower = word.toLowerCase();
  if (word.length < 2) return false;
  if (GREETING_WORDS.has(lower) || VERB_STATE_WORDS.has(lower)) return false;
  if (lower.endsWith('ing') && lower.length > 4) return false;
  const after = fullText.substring(matchIdx + word.length).trim();
  if (after){ const nextWord = after.split(/\s+/)[0]; if (nextWord && NEXT_WORD_DISQUALIFIES.test(nextWord)) return false; }
  return true;
}

function catchLatin(text, asked){
  const m = text.match(/(?:i(?:'m| am)|my name(?:'s| is)|im called|call me|the name(?:'s| is))\s+([A-Za-z]+)/i);
  if (m){ const c = m[1], idx = text.toLowerCase().indexOf(c.toLowerCase(), m.index);
    return isValidName(c, text, idx) ? cap(c) : null; }
  const words = text.split(' ');
  if (words.length === 1 && /^[A-Za-z]+$/.test(text)){
    const low = text.toLowerCase(), floor = asked ? 2 : 4;
    if (text.length >= floor && !BARE_NAME_BLOCKLIST.has(low) && !(asked && ASKED_EXTRA.has(low)) && isValidName(text, text, 0)) return cap(text);
    return null; }
  if (asked && words.length === 2 && words.every(w => /^[A-Za-z][A-Za-z'-]*$/.test(w) && w.length >= 2)){
    const ok = w => { const l = w.toLowerCase(); return !BARE_NAME_BLOCKLIST.has(l) && !ASKED_EXTRA.has(l) && !GREETING_WORDS.has(l) && !VERB_STATE_WORDS.has(l) && !(l.endsWith('ing') && l.length > 4) && !NEXT_WORD_DISQUALIFIES.test(l); };
    if (ok(words[0]) && ok(words[1])) return cap(words[0]); }
  return null;
}

function catchHebrew(text, asked){
  const HE = "[א-ת][א-ת'׳־-]*";
  const m = text.match(new RegExp('(?:קוראים לי|שמי|השם שלי(?: הוא)?|אני)\\s+(' + HE + ')'));
  if (m) return (m[1].length >= 2 && !HE_NOT_NAMES.has(m[1])) ? m[1] : null;
  const words = text.split(' ');
  if (words.length === 1 && new RegExp('^' + HE + '$').test(text)) return (text.length >= 2 && !HE_NOT_NAMES.has(text)) ? text : null;
  if (asked && words.length === 2 && words.every(w => new RegExp('^' + HE + '$').test(w) && w.length >= 2 && !HE_NOT_NAMES.has(w))) return words[0];
  return null;
}

/* catchName(text, { asked }) -> the name, or null. `asked` = this turn directly answers her name question. */
export function catchName(text, { asked = false } = {}){
  const t = clean(text);
  if (!t) return null;
  return /[א-ת]/.test(t) ? catchHebrew(t, asked) : catchLatin(t, asked);
}
