// LAW: LIGHT CONFIG. The magic-light look is LOCKED in light-config.json — the single
// source of truth. nova-light.js loads it (no hard-coded aesthetics), and the flagship
// selects a preset PER GAME via presetFor + mode-aware render routing. Builder picks
// 2026-07-27: 1(single)=B-slow, 2(wave)=C, 3(upgroove)=A, 4(dance)=B; freeze=CUT (ice owns it).
const { runLaw } = require('./_lib');
const CFG = 'light-config.json', JS = 'nova-light.js', NC = 'nova-commercial.html';
runLaw({
  id: 'law-lightconfig', title: 'Locked light look lives in light-config.json; games read it', status: 'active',
  why: 'If aesthetics leak back into JS/HTML or the per-game wiring is removed, the locked look silently drifts and a "feel change = new variant round" becomes an un-reviewed hand-edit.',
  checks: [
    // the four locked modes + the calm preset all present in the JSON
    { desc: 'preset single present',      rel: CFG, present: /"single"\s*:/ },
    { desc: 'preset wave present',        rel: CFG, present: /"wave"\s*:/ },
    { desc: 'preset upgroove present',    rel: CFG, present: /"upgroove"\s*:/ },
    { desc: 'preset dance present',       rel: CFG, present: /"dance"\s*:/ },
    { desc: 'preset hellohello present',  rel: CFG, present: /"hellohello"\s*:/ },
    // per-game routing map present and pointing joined→upgroove (spec anchor)
    { desc: '_gameMap present',           rel: CFG, present: /"_gameMap"\s*:/ },
    { desc: 'joined→upgroove mapping',    rel: CFG, present: /"joined"\s*:\s*"upgroove"/ },
    // engine loads the JSON and holds NO hard-coded preset aesthetics
    { desc: 'engine loads light-config', rel: JS,  present: /light-config\.json/ },
    { desc: 'PRESETS starts empty (no inline aesthetics)', rel: JS, present: /PRESETS\s*=\s*\{\s*\}/ },
    { desc: 'old hard-coded preset block removed', rel: JS, absent: /handwave:\s*\{\s*mode:\s*'travel',\s*nodes:\s*22/ },
    // flagship wires per-game selection + mode-aware (travel vs isolation) render routing
    { desc: 'flagship uses presetFor (per-game light)', rel: NC, present: /presetFor/ },
    { desc: 'flagship routes travel vs isolation', rel: NC, present: /cfg\s*&&\s*eng\.cfg\.mode===['"]travel['"]|mode===['"]travel['"]/ },
  ],
});
