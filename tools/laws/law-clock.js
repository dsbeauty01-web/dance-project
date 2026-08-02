// LAW: THE ONE CLOCK. Game cues are driven by the media's own currentTime
// (the video/song IS the clock), streamed to the worker — NOT by free-running
// setTimeout chains that drift. Zone-1 markers must be present.
const { runLaw } = require('./_lib');
const NC = 'nova-commercial.html';
runLaw({
  id: 'law-clock', title: 'One clock — video/song currentTime drives cues (Zone 1)', status: 'active',
  why: 'setTimeout-driven cues drift out of sync with the music; the media clock does not.',
  checks: [
    { desc: 'Zone-1 clock block present',        rel: NC, present: /ZONE 1/ },
    { desc: 'position stream to worker present',  rel: NC, present: /startPosStream/ },
    { desc: 'position-stream QA hook present',    rel: NC, present: /__posLog/ },
  ],
});
