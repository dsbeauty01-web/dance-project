// LAW: MOVE-CLAIM NEEDS A FACT (founder ruling 2026-09-20) — the truth-gate's FOURTH path.
//
// Live session 2026-09-20: zero [FACT] lines in the entire log, and she still said
// "איזה יופי של הרמה עם הכתף הזאת!" — "what a beautiful lift with that shoulder". Three
// paths were already closed (success() + the 20s release in v1.0.4, the 13s re-invite in
// v1.0.7). This was the fourth: praise riding on a GENUINE kid turn, which the gate
// deliberately exempts — praise within 6s of a real turn is a legitimate reaction, and
// torture-1 proved that killing it also kills her honest name-echo.
//
// THE LAW: that exemption stands for warmth, but a line that CLAIMS A MOVE requires a real
// detection fact within 30s — inside the exemption window too. And the gate is bilingual:
// PRAISE_RE is English-only, so a Hebrew claim could never match it in ANY window.
//
// The verdict lives in ONE pure function (truthgate_blocks) so it is provable offline —
// test/truthgate_bench.py runs three no-lift sessions and asserts zero move-praise.
const { runLaw } = require('./_lib');
const RT = 'pod/rt_lk.py';
runLaw({
  id: 'law-moveclaim',
  title: 'A move-claim needs a real fact — even right after a kid turn',
  status: 'active',
  why: 'Founder session 2026-09-20: zero facts all session, and she praised a shoulder lift that never happened. A child who is told they did something they did not do stops trusting the praise.',
  checks: [
    { desc: 'the verdict is ONE pure function',        rel: RT, present: /def truthgate_blocks\(/ },
    { desc: '30s move-claim window exists',            rel: RT, present: /MOVE_FACT_WINDOW = 30\.0/ },
    { desc: 'move words are matched in Hebrew too',    rel: RT, present: /MOVE_WORD_RE/ },
    { desc: 'Hebrew claim shapes are matched',         rel: RT, present: /CLAIM_SHAPE_RE/ },
    { desc: 'Hebrew invitations stay sayable',         rel: RT, present: /INVITE_HE_RE/ },
    { desc: 'the gate asks, it does not read bare verbs', rel: RT, present: /INVITE_ASK_RE/ },
    { desc: 'the gate is wired into the pre-synth path', rel: RT, present: /truthgate_blocks\(\s*\n?\s*resp\["buf"\]/ },
    { desc: 'the kill is logged with its reason',      rel: RT, present: /pre-synth blocked \(/ },
    // The exemption this law is careful NOT to destroy (torture-1).
    { desc: 'praise within 6s of a real turn is still exempt', rel: RT, present: /since_kid > 6\.0/ },
  ],
});
