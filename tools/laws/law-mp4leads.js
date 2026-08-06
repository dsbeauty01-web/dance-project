// LAW: MP4 LEADS. In the Wave game the pre-baked MP4 leads the beat; the
// `__mp4Leads` gate decides whether the live pitch-plan or the MP4 owns the
// game clock, and suppresses live clips when the MP4 is leading.
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
runLaw({
  id: 'law-mp4leads', title: 'Wave MP4-led gate (__mp4Leads)', status: 'active',
  why: 'Without the gate the live pitch and the baked MP4 both drive the game and collide.',
  checks: [
    { desc: '__mp4Leads gate present',   rel: NC, present: /__mp4Leads/ },
    { desc: 'MP4_LEADS config present',   rel: NC, present: /MP4_LEADS/ },
  ],
});
