// LAW: ENDINGS. Every game ends through nova-ending.js, which NEVER renders a
// bare zero / "0 pts" / empty star row — a child always leaves on celebration.
// nova-ending.js must be wired into both live game files and keep its zero-guard.
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
const AF = 'pod/pages/animal-freeze.html';  // ONE-ORIGIN 2026-08-08: the real game file
const END = 'nova-ending.js';
runLaw({
  id: 'law-endings', title: 'nova-ending.js wired in both games; no raw "0 pts" renderable', status: 'active',
  why: 'A child seeing "0 pts" at the end is the opposite of the product\'s promise; the ending guards against it.',
  checks: [
    { desc: 'ending engine wired (commercial)', rel: NC,  present: /nova-ending/ },
    { desc: 'ending engine wired (freeze)',      rel: AF,  present: /nova-ending/ },
    { desc: 'zero-guard present in engine',       rel: END, present: /NEVER a zero|no.?zero|0 pts/i },
  ],
});
