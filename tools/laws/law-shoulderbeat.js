// LAW: THE SHOULDER BEAT SPEAKS, REACTS AND RETRIES ON ITS OWN CLOCK
// (founder spec SHOULDER-BEAT §4b, 2026-09-20).
//
// PRODUCER-SILENT made every producer note silent — correct, and it left the light beat
// mute: the page armed the light and she said nothing until the child happened to speak.
// The three rules that close it:
//
//   1. THE LIGHT APPEARING IS A BOUNDARY. The page reports section-start and hands her the
//      EXACT line; she speaks within 2s. The WAIT LAW does not swallow it (the page only
//      arms after the child answered), but nothing ELSE gains that privilege.
//   2. THE INSTANT REACTION IS PAGE-SIDE. A detected lift pops the glow and fires a 300ms
//      "YES!!" in her own voice, in the same frame. The brain is not in that path — a round
//      trip is not instant, and she must not be the one claiming the lift. Her words come
//      afterwards, from the FACT she is told.
//   3. THE RETRY IS THIS WINDOW'S OWN, AT 8s, read exactly — it states what she has NOT
//      seen. The brain stands its generic 13s timer down for the whole section, so the
//      child never gets two producers counting to two different numbers. RELEASE stays 20s.
const { runLaw } = require('./_lib');
const RT = 'pod/rt_lk.py';
const NC = 'nova-commercial.html';
runLaw({
  id: 'law-shoulderbeat',
  title: 'The light is a boundary · the pop is page-side · the retry is 8s',
  status: 'active',
  why: 'Live session 2026-09-20: the light armed silently and she waited for the child to speak first; there was no instant reward for a lift; and the only retry was the brain\'s generic 13s line, which knows nothing about the light.',
  checks: [
    // 1 — the light is a boundary
    { desc: 'the page can report a section boundary',  rel: NC, present: /window\.novaSection = function/ },
    { desc: 'the page can hand her an exact line + its boundary', rel: NC, present: /window\.novaSayNow = function/ },
    { desc: 'ARM reports section-start',               rel: NC, present: /novaSection\('shoulder', 'start'\)/ },
    { desc: 'ARM speaks the exact light line',         rel: NC, present: /novaSayNow\(T\('sayLightArm'\), 'section-start'\)/ },
    { desc: 'the brain honours a carried boundary',    rel: RT, present: /_b = \(m\.get\("boundary"\) or ""\)/ },
    { desc: 'a section-start outranks the ask-lock',   rel: RT, present: /"section-start", "section-retry"/ },
    { desc: 'the 2s claim is MEASURED, not hoped',     rel: RT, present: /\[SECTION\] spoke %\.2fs after/ },
    // 2 — the instant reaction is page-side
    { desc: 'the glow pops',                           rel: NC, present: /classList\.add\('pop'\)/ },
    { desc: 'the pop is a real animation',             rel: NC, present: /@keyframes glowBloom/ },
    { desc: 'her own-voice sting fires',               rel: NC, present: /audio\/says\/sting_yes_/ },
    { desc: 'the sting follows the language',          rel: NC, present: /window\.NOVA_HE \? 'he' : 'en'/ },
    // 3 — the retry is this window's own
    { desc: 'retry at 8s',                             rel: NC, present: /age > 8000/ },
    { desc: 'retry is the exact line',                 rel: NC, present: /novaSayNow\(T\('sayLightRetry'\), 'section-retry'\)/ },
    { desc: 'RELEASE still at 20s',                    rel: NC, present: /no shrug seen in 20s/ },
    { desc: 'the brain stands down inside a section',  rel: RT, present: /if section\["on"\]:/ },
    { desc: 'the generic silence retry is untouched',  rel: RT, present: /SILENCE_RETRY_S = 13\.0/ },
    // the truth law this beat must never break
    { desc: 'release never claims a lift',             rel: NC, present: /she must never claim she saw one/ },
    { desc: 'the win line still rides on a FACT',      rel: NC, present: /factShrug/ },
  ],
});
