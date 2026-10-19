// LAW: SHOULDER BEAT — NAME-GATED, NOT CLOCK-GATED.
//
// SUPERSEDED 2026-09-14 by the founder's INTRO-V2V design (Downloads/INTRO-V2V (1).md).
// The old law required a 25s chit-chat gate and a 35s hard fallback. The intro audit
// (Downloads/zevel.md) showed what those timers actually did: the beat fired on a clock,
// straight over a child who was still answering, and because the third trigger was an
// English-only regex on her own transcript, a Hebrew session could ONLY ever reach the
// shoulder through the blind 35s fallback.
//
// The law it becomes: nothing may reach the brain before the child's name is captured, the
// beat arms on that event, and the only clock left is a single no-name safety. The test is
// not deleted — it is inverted, so the old timers can never come back by accident.
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
runLaw({
  id: 'law-shoulder', title: 'Shoulder beat is name-gated (INTRO-V2V), never clock-gated', status: 'active',
  why: 'Firing on a timer talks over the child and, in Hebrew, could only ever fire blind. The name is the trigger.',
  checks: [
    { desc: 'chit-chat clock still measured (for logs)', rel: NC, present: /__introChatT0/ },
    { desc: 'ARM is gated on the captured name',          rel: NC, present: /if \(!window\.__nameCaptured\) return;/ },
    { desc: 'the name event drives the beat',             rel: NC, present: /nova-name-captured/ },
    { desc: 'no-name safety is the ONLY timer left',      rel: NC, present: /45s no-name safety/ },
    { desc: '25s chit-chat gate is GONE',                 rel: NC, absent:  /__introChatT0 < 25000/ },
    { desc: '35s hard fallback is GONE',                  rel: NC, absent:  /35s fallback/ },
    { desc: 'a timeout never fakes a win',                rel: NC, present: /no shrug seen in 20s . RELEASE/ },
  ],
});
