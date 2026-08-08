// LAW: CONSENT. Both live game files must carry the parental-consent / legal
// lock-line, in English AND Hebrew, before camera + mic are used on a child.
//
// STATUS: LOST. As of the Guardian audit (2026-07-27) NEITHER live game file
// (nova-commercial.html, animal-freeze.html) contains a consent/legal lock-line.
// Memory records it once lived in nova-app.html; it was never propagated to the
// live commercial/freeze surfaces. Reported in GUARDIAN-REPORT.md. This test is
// registered as 'lost' so it does not block the Guardian's own landing — the
// moment the founder restores the lock-line and flips this to 'active', any
// future removal turns the build RED.
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
const AF = 'pod/pages/animal-freeze.html';  // ONE-ORIGIN 2026-08-08: the real game file
const CONSENT = /consent|parental|הסכמ|תנאי שימוש|מדיניות פרטיות/i;
runLaw({
  id: 'law-consent', title: 'Parental-consent / legal lock-line in both game files (EN+HE)', status: 'lost',
  why: 'Camera + mic on a child without a visible consent/legal line is a compliance and trust failure.',
  checks: [
    { desc: 'consent lock-line present (commercial)', rel: NC, present: CONSENT },
    { desc: 'consent lock-line present (freeze)',      rel: AF, present: CONSENT },
  ],
});
