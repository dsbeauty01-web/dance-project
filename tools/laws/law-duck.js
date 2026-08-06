// LAW: ONE DUCK ENGINE, REFCOUNTED. Music ducking under Nova's voice goes
// through a single refcounted engine (acquire/release), never a naked boolean
// that races when two sources duck at once (Zone 2).
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
runLaw({
  id: 'law-duck', title: 'One refcounted duck engine (acquire/release, no boolean)', status: 'active',
  why: 'A boolean duck flag races: source B un-ducks while source A still needs it. Refcount does not.',
  checks: [
    { desc: 'single duck engine present',   rel: NC, present: /window\.__duck/ },
    { desc: 'refcount acquire present',      rel: NC, present: /\.acquire\(/ },
    { desc: 'refcount release present',      rel: NC, present: /\.release\(/ },
    { desc: 'no naked boolean duck flag',    rel: NC, absent:  /isDucked\s*=\s*(true|false)/ },
  ],
});
