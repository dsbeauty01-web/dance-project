// LAW: THE NAME SURVIVES A CHOPPED TRANSCRIPT (founder ruling 2026-09-20).
//
// Live session 2026-09-20: "[INPUT-LOCK] dropped: sub-2-word | קוראים." — and קוראים is
// the FIRST WORD of "קוראים לי <name>" ("my name is ..."). The transcriber cut the child's
// answer in half, each half died the sub-2-word death, and the name was lost. The old
// single-token name branch could not rescue it either: it only fires on the session's
// FIRST valid turn, and by then the session was already on turn 2.
//
// THE LAW: while the name beat is open, in Hebrew, fragments arriving within 1.5s are
// JOINED and re-judged, and a 1-2 token Hebrew turn counts as a name candidate. Both rules
// are pure functions so the split-name case is provable offline (test/truthgate_bench.py
// joins "קוראים לי" + "נועם").
//
// The INPUT LOCK is NOT weakened: a joined fragment still runs the same validation, and a
// held fragment never generates anything on its own.
const { runLaw } = require('./_lib');
const RT = 'pod/rt_lk.py';
runLaw({
  id: 'law-namebeat',
  title: 'A chopped Hebrew name is rejoined, not lost',
  status: 'active',
  why: 'Founder session 2026-09-20: the name was said and the transcriber split it; both halves were dropped as sub-2-word and she spent the session with no name.',
  checks: [
    { desc: 'the join is a pure function',           rel: RT, present: /def join_fragment\(/ },
    { desc: 'the name test is a pure function',      rel: RT, present: /def name_candidate\(/ },
    { desc: '1.5s join window',                      rel: RT, present: /NAME_JOIN_S = 1\.5/ },
    { desc: 'the beat can close',                    rel: RT, present: /namebeat = \{"open": True\}/ },
    { desc: 'the Hebrew lead-in is known',           rel: RT, present: /קוראים לי/ },
    { desc: 'joins are logged',                      rel: RT, present: /\[NAME-JOIN\]/ },
    { desc: 'accepted candidates are logged',        rel: RT, present: /\[NAME-BEAT\] name candidate accepted/ },
    // The lock must not be weakened by any of it.
    { desc: 'a held fragment is still a DROPPED turn', rel: RT, present: /\[INPUT-LOCK\] dropped/ },
    { desc: 'game words can never be taken as a name', rel: RT, present: /"דוב", "כוכב", "פלמינגו"/ },
  ],
});
