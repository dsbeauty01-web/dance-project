// Runner cd's into tools/laws/; the checks below use repo-root-relative paths.
process.chdir(require('path').resolve(__dirname, '..', '..'));
// LAW-SPEAK-GATE: every game page carries the global speak-gate (>=7s between lines,
// drop-not-queue) — the Error-1 fix can never silently vanish again.
const fs = require('fs');
let fail = false;
for (const page of ['pod/pages/up-groove.html','pod/pages/wave.html']) {
  if (!fs.existsSync(page)) continue;
  const s = fs.readFileSync(page,'utf8');
  if (!/SPEAK_GATE_MS\s*=\s*7000/.test(s)) {
    console.error(`LAW-SPEAK-GATE FAIL: ${page} missing SPEAK_GATE_MS = 7000`); fail = true;
  }
  if (!/speakGate|SPEAK-GATE/.test(s)) {
    console.error(`LAW-SPEAK-GATE FAIL: ${page} missing the gate implementation marker`); fail = true;
  }
}
if (fail) process.exit(1);
console.log('LAW-SPEAK-GATE OK');
