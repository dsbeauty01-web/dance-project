// LAW: FRAME MODE. The app tells the SARAY avatar page how to frame Nova's
// video — WAIST-UP `closeup` for intro/end (no black margins) and FULL BODY for
// the corner during play. Both senders + the handler must be present.
// NOTE: the `nova-ambient` never-black fallback is POD-SIDE (SARAY page /
// rt_lk.py) and not yet in git — tracked in LAWS.md as law-ambient (pod repo),
// RED until Part 1 lands the pod files. This law guards the app-side bridge.
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
runLaw({
  id: 'law-frames', title: 'Frame-mode bridge — closeup + full senders to SARAY', status: 'active',
  why: 'Wrong framing = black side-margins or a cropped kid; the bridge keeps her framed per phase.',
  checks: [
    { desc: 'frame handler present',        rel: NC, present: /__sarayFrameMode\s*=/ },
    { desc: 'FULL-BODY frame sent',          rel: NC, present: /__sarayFrameMode\(\s*['"]full/ },
    { desc: 'CLOSEUP frame sent',            rel: NC, present: /__sarayFrameMode\(\s*['"]closeup/ },
  ],
});
