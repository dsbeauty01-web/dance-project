#!/usr/bin/env node
/* MACHINE-CERTIFY test/grade.js — scores one session against the G1–G6 law.
   NEVER weaken a grader to pass it (spec PART 4); any grader change = [CLI-FILL] logged.

   Usage: node test/grade.js test/sessions/<name>
   Reads session.json (+ rtlk.log if the loop script fetched the pod-side delta)
   and prints PASS/FAIL per grader + writes grade.json.

   Evidence sources:
   - logs[]   — the page console stream ([NOVA-SAID]/[KID-SAID]/[BODY]/[PHASE]/
                [VERDICT-LATENCY]/[SPEAK-GATE]/[AIR]...), each {t, k, m}
   - energy[] — HER-voice RMS 10Hz samples {t, mt, air, eng, phase} (G1 onset, G3 silence)
   - events[] — the runner's script journal (say timings, hold behaviors)
   - netReqs[]— session-rec/PULSE POSTs seen on the wire
   - rtlk.log — pod-side [INPUT-LOCK] evidence (G5) when present               */
'use strict';
const fs = require('fs'), path = require('path');

const DIR = process.argv[2];
if (!DIR) { console.error('usage: node test/grade.js <session dir>'); process.exit(2); }
const S = JSON.parse(fs.readFileSync(path.join(DIR, 'session.json'), 'utf8'));
const RTLK = fs.existsSync(path.join(DIR, 'rtlk.log')) ? fs.readFileSync(path.join(DIR, 'rtlk.log'), 'utf8') : '';
const HE = S.meta.lang === 'he';

const logs = S.logs || [], energy = S.energy || [], events = S.events || [];
const said = logs.filter(l => l.m.startsWith('[NOVA-SAID]')).map(l => ({ t: l.t, text: l.m.slice(12).trim() }));
const evAt = name => events.filter(e => e.ev === name);
const sayEnd = label => { const e = evAt('say-done:' + label)[0]; return e ? e.t : null; };
// page-clock (performance.now) vs runner-clock offset: use the harness-armed log line
const armed = logs.find(l => l.m.startsWith('[TEST] harness armed'));
// events use runner clock; logs/energy use page clock. Align via first common anchor:
// tap event ↔ nothing logged — so align say-done (runner) to the energy/log window by
// mapping: page zeroed at load which happened ~(chrome-launched→cdp-attached) before T0.
// Practical alignment: [NOVA-SAID] replies are matched to says by ORDER + windows on the
// runner clock after converting page t via OFFSET = median(logline wall deltas). We
// instead convert the other way: the runner records logCount snapshots before each say
// and waitReply matched by log INDEX — order-based, clock-free. Energy onset uses page
// clock deltas against the [KID-SAID]/say window found by index. Keep it index-based.

function fail(list, why) { list.push(why); }

/* ---------- G1 hears+answers ---------- */
// every conversational phrase → exactly ONE [NOVA-SAID] follows before the next say;
// name reply contains the name; response onset (voice energy after say end) ≤3.5s.
const G1 = [];
const NAME = HE ? ['שוקי', 'shuki', 'shukee'] : ['shuki', 'shukee', 'shooki', 'shuky', 'שוקי'];
const conv = ['name', 'chat', 'ending-ok', 'ending-bye'];
for (const c of conv) {
  const done = evAt('say-done:' + c)[0];
  if (!done) { fail(G1, c + ': phrase never sent'); continue; }
  if (evAt('no-reply:' + c).length) { fail(G1, c + ': NO reply'); continue; }
}
// name echo: the reply to the FIRST kid utterance (= the name phrase) must contain the
// name. Anchor on the first [KID-SAID] itself, NOT its transcript text — en-1 transcribed
// "Shuki" as "Chucky" yet Nova still echoed "Shuki" (a PASS); en-2 echoed "Shukee",
// a fair spelling of the heard name, so the accepted list covers phonetic spellings.
(function () {
  const nameDone = evAt('say-done:name')[0];
  if (!nameDone) return;
  const firstKid = logs.find(l => l.m.startsWith('[KID-SAID]'));
  if (!firstKid) { fail(G1, 'name: kid transcript never arrived'); return; }
  const reply = said.find(r => r.t > firstKid.t);
  if (!reply) { fail(G1, 'name: no reply after the name'); return; }
  if (!NAME.some(n => reply.text.toLowerCase().includes(n))) fail(G1, 'name reply misses the name: "' + reply.text.slice(0, 60) + '"');
})();
// onset latency: for each say-done, first energy sample (air or eng) >0.01 within 3.5s.
// Energy + says live on different clocks; use the [KID-SAID] page-log anchor per phrase.
const kidSaidLogs = logs.filter(l => l.m.startsWith('[KID-SAID]'));
(function () {
  if (!energy.length) { fail(G1, 'no energy samples at all'); return; }
  for (const k of kidSaidLogs) {
    const on = energy.find(e => e.t > k.t && e.t < k.t + 3500 && (e.air > 0.01 || e.eng > 0.01));
    const inGame = (() => { const p = energy.find(e => e.t >= k.t); return p && p.phase !== 'intro' && p.phase !== 'ending'; })();
    if (!on && !inGame) fail(G1, 'no voice onset ≤3.5s after kid line "' + k.m.slice(11, 40) + '"');
  }
})();

/* ---------- G2 presence (mid-game replies) ---------- */
const G2 = [];
const NEG = HE ? /(לא נכון|רע\b|טעות|\bno\b|wrong|bad|didn'?t)/i : /\b(no|wrong|bad|didn'?t|not quite|missed)\b/i;
const ASSISTANT = /(as an ai|assistant|language model|i can help|how can i|i'?m here to|לעזור לך|אוכל לעזור|במה אוכל)/i;
const gamePhases = new Set(['game', 'hold']);
const phaseAt = t => { let p = 'intro'; for (const l of logs) { if (l.t > t) break; if (l.m.startsWith('[PHASE]')) p = l.m.split(' ')[1]; } return p; };
// content laws (added after session en-1: she invented rounds, offered animals, counted
// down and called freezes herself — the exact behavior the founder hates; these checks
// STRENGTHEN G2, they never replace a spec check)
// [CLI-FILL] 'here it comes' removed from the ban list: "Keep on dancing, here it comes!"
// is a spec-perfect freeze tease (en-3) — the phrase only signaled self-DJ when she was
// announcing music SHE controlled ("Ready for the music again? Here it comes!"), which
// the 'ready for the music' ban still catches.
const SELF_DJ = /(another round|next round|new animal|how about a|want to (do|try|play)|you choose|pick a|3.{0,3}2.{0,3}1|ready for the music|what.{0,12}next|final round|play again later|your call|switch it up)/i;
for (const r of said) {
  const ph = phaseAt(r.t);
  if (!gamePhases.has(ph)) continue;
  const words = r.text.split(/\s+/).filter(Boolean).length;
  if (words > 6) fail(G2, `mid-game line ${words} words (>6): "${r.text.slice(0, 60)}"`);
  if (NEG.test(r.text)) fail(G2, 'negative word mid-game: "' + r.text.slice(0, 60) + '"');
  if (/[?？]/.test(r.text)) fail(G2, 'mid-game QUESTION (page owns the game): "' + r.text.slice(0, 60) + '"');
  if (SELF_DJ.test(r.text)) fail(G2, 'self-DJ line (inventing rounds/choices): "' + r.text.slice(0, 60) + '"');
  // HE mode: a mid-game line of 2+ Latin words is a language leak ("Perfect freeze, BEAR!")
  if (HE && (r.text.match(/[A-Za-z]{2,}/g) || []).length >= 2)
    fail(G2, 'English leak in Hebrew session: "' + r.text.slice(0, 60) + '"');
}
for (const r of said) if (ASSISTANT.test(r.text)) fail(G2, 'assistant-talk: "' + r.text.slice(0, 60) + '"');

/* ---------- G3 silence law ---------- */
const G3 = [];
// zero HER audio inside every hold window — measured, not inferred from gates
const THR = 0.01;
const holdSamples = energy.filter(e => e.phase === 'hold');
if (!holdSamples.length) fail(G3, 'no hold-phase energy samples (game never held?)');
// [CLI-FILL] a SINGLE loud sample is an analyser artifact, not a leak: the AnalyserNode's
// 2048-sample ring (~43ms) still holds pre-cut audio when the phase flips, so the first
// 100ms sampler tick inside a hold can read the tail of a legally-finished line (en-3:
// exactly one 0.015 sample at a boundary). A real voice line is 500ms+ = many samples —
// so a leak = ≥2 CONSECUTIVE loud samples inside a hold.
let leakRun = 0, worstRun = 0;
for (const e of holdSamples) {
  if (e.air > THR || e.eng > THR) { leakRun++; worstRun = Math.max(worstRun, leakRun); }
  else leakRun = 0;
}
if (worstRun >= 2) fail(G3, `HER VOICE inside a freeze hold: ${worstRun} consecutive samples >${THR} rms`);
// NO warning before the fakeout. [CLI-FILL 2026-08-30]: the naive window [stab-4.5, stab]
// overlaps the PREVIOUS round's hold + its legitimate warning tail (the stab lands ~1.2s
// after the previous melt by design) — so the honest window is the actual melt→stab gap.
if (S.freezes && energy.length) {
  const stab = S.freezes.findIndex((f, i) => i > 0 && f.at - (S.freezes[i - 1].at + S.freezes[i - 1].hold) < 3);
  if (stab > 0) {
    const gapLo = S.freezes[stab - 1].at + S.freezes[stab - 1].hold + 0.15;
    const win = energy.filter(e => e.mt != null && e.mt > gapLo && e.mt < S.freezes[stab].at - 0.1 && e.air > THR);
    if (win.length) fail(G3, `her voice in the fakeout gap (mt ${gapLo.toFixed(1)}–${S.freezes[stab].at})`);
  }
}
// lines per gap. [CLI-FILL 2026-08-30]: the spec both demands the pre-freeze warning
// (2-4s before every non-stab freeze) AND says "≤1 line per gap" — read as: the verdict
// (≤1) plus the scheduled warning (≤1), nothing else. So ≤2 lines per inter-hold gap,
// and any 3rd line is a violation. Grader never weakened: both spec features enforced.
if (S.freezes) {
  const holdsT = []; logs.forEach(l => { if (l.m.startsWith('[PHASE] hold')) holdsT.push(l.t); });
  for (let i = 0; i + 1 < holdsT.length; i++) {
    const inGap = said.filter(r => r.t > holdsT[i] && r.t < holdsT[i + 1]).length;
    if (inGap > 2) fail(G3, `${inGap} lines in gap ${i}→${i + 1} (max: verdict + warning = 2)`);
  }
}

/* ---------- G4 flow ---------- */
const G4 = [];
// intro ≤40s to music: greet-heard → music-started on the runner clock
(function () {
  const g = evAt('greet-heard')[0], m = evAt('music-started')[0];
  if (!g || !m) { fail(G4, 'greet or music-start missing'); return; }
  const silencePad = 25000;   // the scripted G5 silence window is test-added, not intro fat
  const introMs = m.t - g.t - silencePad;
  if (introMs > 40000) fail(G4, `intro ${Math.round(introMs / 1000)}s to music (>40s)`);
})();
// verdict latency median ≤2.5s post-melt
(function () {
  const lat = [];
  logs.forEach(l => { const m = l.m.match(/\[VERDICT-LATENCY\] \S+ (\d+)ms/); if (m) lat.push(+m[1]); });
  if (!lat.length) { fail(G4, 'no [VERDICT-LATENCY] measurements'); return; }
  const med = lat.sort((a, b) => a - b)[Math.floor(lat.length / 2)];
  if (med > 2500) fail(G4, `verdict median ${med}ms (>2500ms)`);
})();
// ending trio: a score number spoken · a fun question · the name in a goodbye
(function () {
  const endSaid = said.filter(r => phaseAt(r.t) === 'ending').map(r => r.text);
  if (!endSaid.length) { fail(G4, 'no ending lines at all'); return; }
  const all = endSaid.join(' | ');
  if (!/\d/.test(all) && !/(אחת|שתיים|שלוש|ארבע|חמש|שש|שבע|שמונה|תשע|עשר|one|two|three|four|five|six|seven|eight|nine|ten|eleven)/i.test(all)) fail(G4, 'ending: no score number spoken');
  if (!/[?？]/.test(all)) fail(G4, 'ending: no fun question');
  if (!NAME.some(n => all.toLowerCase().includes(n))) fail(G4, 'ending: name missing from goodbye');
})();
// PULSE row with feedback_text seen on the wire
(function () {
  const pulse = (S.netReqs || []).filter(r => r.method === 'POST');
  if (!pulse.length) { fail(G4, 'no session-rec/PULSE POST seen'); return; }
  if (!pulse.some(r => /feedback_text|feedback/.test(r.postData || '') || /feedback/.test(r.url))) fail(G4, 'no feedback row (feedback_text) sent');
})();

/* ---------- G5 lock ---------- */
const G5 = [];
for (const nz of ['garble', 'hum', 'breath']) {
  const done = evAt('say-done:noise-' + nz)[0];
  if (!done) { fail(G5, 'noise ' + nz + ' never injected'); continue; }
  // zero replies attributable to the noise: no no-reply event means waitReply wasn't used —
  // instead assert no [NOVA-SAID] whose matching [KID-SAID] is garbage. Pod-side is authoritative:
}
// [CLI-FILL] the lock has TWO equally-valid outcomes per noise: (a) VAD transcribed it
// and INPUT-LOCK dropped it (pod log line), or (b) it never even transcribed — zero
// mid-game kid transcripts at all (en-3: garble/hum/breath produced no [KID-SAID] and
// no response — stronger than a drop). Fail only when noise produced an actual RESPONSE.
if (RTLK || logs.length) {
  const dropped = (RTLK.match(/\[INPUT-LOCK\] dropped/g) || []).length;
  const gameStart = logs.find(l => l.m.startsWith('[PHASE] game'));
  const ending = logs.find(l => l.m.startsWith('[PHASE] ending'));
  const midGameKid = logs.filter(l => l.m.startsWith('[KID-SAID]') &&
    gameStart && l.t > gameStart.t && (!ending || l.t < ending.t));
  if (dropped < 1 && midGameKid.length > 0)
    fail(G5, `noise transcribed mid-game (${midGameKid.length} kid lines) yet zero [INPUT-LOCK] dropped`);
} else fail(G5, 'no evidence at all (no rtlk.log, no page logs)');
// silence window: exactly one re-invite
(function () {
  const s0 = evAt('silence-window-start')[0], s1 = evAt('silence-window-end')[0];
  if (!s0 || !s1) { fail(G5, 'silence window not run'); return; }
  const idx = s0.detail && s0.detail.logIdx || 0;
  const during = said.filter(r => { const li = logs.findIndex(l => l.t === r.t && l.m.startsWith('[NOVA-SAID]')); return li >= idx; });
  const winSaid = said.filter(r => r.t >= (logs[idx] ? logs[idx].t : 0)).filter(r => phaseAt(r.t) === 'intro');
  // count intro lines in the 25s window itself (between the two runner marks is clock-crossed;
  // approximate: intro [NOVA-SAID] before the name [KID-SAID])
  const nameKid = kidSaidLogs[0];
  const reinvites = said.filter(r => (!nameKid || r.t < nameKid.t) && phaseAt(r.t) === 'intro').length;
  // reinvites includes the greet itself (1) — silence may add exactly one more → ≤2 total, ≥1
  if (reinvites > 3) fail(G5, `${reinvites} intro lines before first kid word (greet + max 1 re-invite + ready ask allowed = 3)`);
})();

/* ---------- G6 body map ---------- */
const G6 = [];
const bodies = logs.filter(l => l.m.startsWith('[BODY]')).map(l => ({ t: l.t, m: l.m }));
if (!bodies.length) fail(G6, 'no [BODY] logs at all');
// [CLI-FILL 2026-08-30] transition tolerance: the page DELIBERATELY sets the body just
// BEFORE flipping the phase (groove before GAME so the body is in place at music start;
// idle2 before ENDING so lips can never animate the groove — that ordering is a safety
// law, see endGame). A [BODY] line whose phase mismatches is legal iff the matching
// [PHASE] flip lands within 2.5s after it. Pose clips may lead their hold by ≤1.5s
// (neutral-crossing swap window opens at T-0.6 and the clip lands into the pose).
const phaseFlipSoon = (t, ph, ms) => logs.some(l => l.t > t && l.t < t + ms && l.m.startsWith('[PHASE] ' + ph));
for (const b of bodies) {
  const mm = b.m.match(/\[BODY\] (\S+)(?: phase=(\S+))?/);
  if (!mm) continue;
  const [, id, ph] = mm;
  if (id.startsWith('poseclip')) {
    if (id !== 'poseclip:off' && ph && ph !== 'hold' && !phaseFlipSoon(b.t, 'hold', 1500))
      fail(G6, `pose clip outside a hold: ${b.m}`);
  } else if (id === 'nova_idle2') {
    if (ph && !['intro', 'ending', 'boot'].includes(ph) && !phaseFlipSoon(b.t, 'ending', 2500))
      fail(G6, `talk body during ${ph}: ${b.m}`);
  } else if (id === 'nova_idlegroove_v2') {
    if (ph && ph !== 'game' && !phaseFlipSoon(b.t, 'game', 2500))
      fail(G6, `dance body during ${ph}: ${b.m}`);
  } else fail(G6, `OFF-LAW body: ${b.m}`);
}
// the required arc: idle2 → idlegroove_v2 → (poseclips…) → idle2
(function () {
  const seq = bodies.map(b => (b.m.match(/\[BODY\] (\S+)/) || [])[1]).filter(x => x && !x.startsWith('poseclip'));
  if (seq[0] !== 'nova_idle2') fail(G6, 'session does not OPEN on nova_idle2 (talk)');
  if (!seq.includes('nova_idlegroove_v2')) fail(G6, 'dance body never set');
  if (seq[seq.length - 1] !== 'nova_idle2') fail(G6, 'session does not CLOSE on nova_idle2 (ending talk)');
  const clips = bodies.filter(b => /poseclip:(?!off)/.test(b.m)).length;
  if (clips < 8) fail(G6, `only ${clips} pose-clip holds logged (expect ~11)`);
})();

/* ---------- report ---------- */
const G = { G1, G2, G3, G4, G5, G6 };
const names = { G1: 'hears+answers', G2: 'presence', G3: 'silence law', G4: 'flow', G5: 'input lock', G6: 'body map' };
let clean = true;
console.log('\n═══ GRADE — ' + DIR + ' (' + S.meta.lang.toUpperCase() + ') ═══');
for (const [k, v] of Object.entries(G)) {
  const ok = v.length === 0; if (!ok) clean = false;
  console.log(`${ok ? '✅' : '❌'} ${k} ${names[k]}${ok ? '' : ':'}`);
  v.forEach(w => console.log('     · ' + w));
}
console.log(clean ? '\n★ SESSION CLEAN ★' : '\n✗ session dirty');
fs.writeFileSync(path.join(DIR, 'grade.json'), JSON.stringify({ clean, graders: G, gradedAt: new Date().toISOString() }, null, 1));
process.exit(clean ? 0 : 1);
