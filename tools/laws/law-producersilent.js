// LAW: PRODUCER-SILENT (founder spec 2026-09-18, Downloads/PRODUCER-SILENT.md).
//
// The producer writes to her MEMORY, never to her mouth. The audit that forced this law
// counted 14 response.create (speak NOW) against 3 conversation.item.create (remember) in
// pod/rt_lk.py: every producer path forced speech into the middle of her flow, and mid-game
// facts were dropped at the speak-gate entirely — she never learned the move happened, so
// she invented one. Three verbs now own the socket, and only one of them can make her talk:
//
//   remember()      conversation.item.create   silent, always allowed
//   speak_now()     response.create            ONLY at a boundary, else queued
//   cancel_speech() response.cancel            the child barging in, a pause, a birth-gate
//
// The wall is a COUNT, not just a marker: the moment a 15th response.create appears
// anywhere outside _speak_send, this law goes red and the old disease is back.
//
// _lib's checks are grep-shaped, so the counts are computed here and turned into a pattern
// that can only match when the count is legal: ALWAYS exists in the file, NEVER cannot.
const { runLaw, count } = require('./_lib');
const RT = 'pod/rt_lk.py';
const ALWAYS = /PRODUCER-SILENT/;
const NEVER = /__LAW_PRODUCER_SILENT_VIOLATED__/;
const ok = (cond) => (cond ? ALWAYS : NEVER);

const creates = count(RT, /"type": "response\.create"/);
const items = count(RT, /"type": "conversation\.item\.create"/);
const cancels = count(RT, /"type": "response\.cancel"/);

runLaw({
  id: 'law-producer-silent',
  title: 'Producer writes to memory; speech only at boundaries',
  status: 'active',
  why: 'Founder session 2026-09-17: on the 13s re-invite she said "hold it like that" to a child who had not moved. Producer notes that arrive as ORDERS TO SPEAK break her flow and force her to invent; notes that arrive as MEMORY do not.',
  checks: [
    { desc: 'the silent verb exists',                       rel: RT, present: /async def remember\(/ },
    { desc: 'the speech verb exists',                       rel: RT, present: /async def speak_now\(/ },
    { desc: 'boundaries exist',                             rel: RT, present: /async def boundary_open\(/ },
    { desc: 'the single cancel verb exists',                rel: RT, present: /async def cancel_speech\(/ },
    { desc: `response.create ONLY in _speak_send (found ${creates}, allowed 2)`,         rel: RT, present: ok(creates <= 2) },
    { desc: `conversation.item.create ONLY in remember (found ${items}, allowed 1)`,     rel: RT, present: ok(items === 1) },
    { desc: `response.cancel ONLY in cancel_speech (found ${cancels}, allowed 1)`,       rel: RT, present: ok(cancels === 1) },
    // The mid-game fact drop is the specific bug this law exists to keep buried.
    { desc: 'a detected move is remembered in EVERY phase', rel: RT, absent: /fact stored silently/ },
    { desc: 'the fact note says she was TOLD, not that she saw', rel: RT, present: /you were told, you did not guess/ },
    { desc: 'barge-in is the cancel that belongs to the child', rel: RT, present: /barge-in \(the child started speaking\)/ },
    { desc: 'boundaries are logged',                        rel: RT, present: /\[BOUNDARY\]/ },
    { desc: 'notes are logged',                             rel: RT, present: /\[REMEMBER\]/ },
    { desc: 'speech is logged with its boundary',           rel: RT, present: /\[SPEAK\]/ },
    // The WAIT LAW (INTRO-V2V) must keep outranking a page boundary.
    { desc: 'a page boundary cannot override the ask-lock', rel: RT, present: /BOUNDARY\] refused/ },
  ],
});
