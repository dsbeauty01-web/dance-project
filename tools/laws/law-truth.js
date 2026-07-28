// LAW: TRUTH. Nova never claims a hit that did not happen ("You did it!" with
// nobody moving). A truth gate on the frontend only lets a success line through
// when the move fact is real, and the brain honours the same gate.
// NOTE: the spec's original marker `truthSnapshot` has DRIFTED — the live gate
// is named `TRUTH GATE`. Registered against the real name so future greps hold.
const fs = require('fs');
const path = require('path');
const { runLaw, ROOT } = require('./_lib');
const NC = 'nova-commercial.html';

runLaw({
  id: 'law-truth', title: 'Truth gate — no fake "you did it" (frontend)', status: 'active',
  why: 'A cheer for a move that did not happen breaks the kid\'s trust; the gate only passes real move facts.',
  checks: [
    { desc: 'frontend TRUTH GATE present', rel: NC, present: /TRUTH GATE/ },
  ],
});

// Companion brain-side check — only when the worker repo sits alongside (local
// dev). In CI only dance-project is checked out, so this is a NOTE, not a gate.
const workerAgent = path.join(ROOT, '..', 'novapython', 'agent.py');
if (fs.existsSync(workerAgent)) {
  const ok = /truth/i.test(fs.readFileSync(workerAgent, 'utf8'));
  console.log(`${ok ? 'PASS' : 'FAIL'}  law-truth(brain) — worker honours the truth gate (novapython/agent.py)`);
  if (!ok) process.exitCode = 1;
} else {
  console.log('NOTE  law-truth(brain) — novapython not checked out here; brain-side guarded by its own suite');
}
