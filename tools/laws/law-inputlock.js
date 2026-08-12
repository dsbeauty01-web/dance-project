// LAW-INPUT-LOCK — THE FINAL LOCK (founder 2026-08-11): the pod brain generates
// ONLY on a validated kid-turn. VAD auto-response is structurally OFF; drops are
// logged [INPUT-LOCK]. If these markers vanish, the talks-to-air disease returns.
const { runLaw } = require('./_lib');
const RT = 'pod/rt_lk.py';
runLaw({
  id: 'law-inputlock', title: 'INPUT LOCK — she cannot answer air', status: 'active',
  why: 'Founder logs 2026-08-11: answered breaths, invented "Rilu" from noise, chained 4 lines into silence. Output gates leak; the input lock kills the class.',
  checks: [
    { desc: 'VAD auto-response OFF',   rel: RT, present: /"create_response": False/ },
    { desc: 'drops logged',            rel: RT, present: /\[INPUT-LOCK\] dropped/ },
    { desc: 'one-shot generation',     rel: RT, present: /one-shot fired for turn/ },
    { desc: 'law marker',              rel: RT, present: /LAW-INPUT-LOCK/ },
  ],
});
