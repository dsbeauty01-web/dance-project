// LAW: TRANSCRIPT. Every session records what the kid said (HEARD) and what
// Nova said (NOVA-SAID / nova-said) so sessions can be reviewed and analysed.
// The event wiring must be present in the app.
// NOTE: the pod-side half (rt_lk.py emitting these tags) is not yet in git —
// Part 1 of the Guardian brings it in; until then this guards the app half.
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
runLaw({
  id: 'law-transcript', title: 'Transcript wiring — kid-HEARD + nova-said captured', status: 'active',
  why: 'Without both sides of the transcript, sessions cannot be reviewed or auto-analysed.',
  checks: [
    { desc: 'nova-said event handled', rel: NC, present: /nova-said/ },
    { desc: 'kid speech (HEARD) tapped', rel: NC, present: /HEARD/ },
    { desc: 'log buffer tapped to recorder', rel: NC, present: /tapLogBuffer/ },
  ],
});
