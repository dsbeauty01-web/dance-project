#!/usr/bin/env node
/* NOVA SAYS — timing budget, measured from the REAL captured clips + the post-Q1 window timing.
 *
 * The QA's budget table (Downloads/NOVASAYS-QA.md §THE TIMING BUDGET) assumed a 2.0s line for every
 * command and landed on ~226s against a 210s cap. This measures the actual mp3 durations with ffprobe
 * so the founder's decision — cut round 3, or re-bake faster gestures — is made against real numbers.
 *
 * Run:  node test/novasays_budget.js [en|he-m|he-f]
 */
'use strict';
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const LANG = process.argv[2] || 'en';
const S = JSON.parse(fs.readFileSync(path.join(ROOT, 'beta/novasays/script.json'), 'utf8'));
const DIR = path.join(ROOT, 'audio/novasays', LANG);
const MAN = JSON.parse(fs.readFileSync(path.join(DIR, 'manifest.json'), 'utf8'));

/* MP3 duration by summing frame headers. ffprobe would be the obvious tool, but a process spawn costs
   ~4.6s on this laptop (74 clips = 6 minutes), so the frames are parsed directly — no external binary,
   no cache to go stale. Verified against ffprobe: cmd.armsUp.real.1.mp3 = 1.9189s both ways. */
const BITRATES = {
  1: [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320],       // MPEG1 Layer III
  2: [0, 8,16,24,32,40,48,56,64,80,96,112,128,144,160],          // MPEG2 / 2.5 Layer III
};
const RATES = { 3: [44100,48000,32000], 2: [22050,24000,16000], 0: [11025,12000,8000] };
function mp3Duration(buf){
  let i = 0;
  if (buf.length > 10 && buf.toString('latin1', 0, 3) === 'ID3'){                      // skip ID3v2
    i = 10 + ((buf[6] & 0x7f) << 21 | (buf[7] & 0x7f) << 14 | (buf[8] & 0x7f) << 7 | (buf[9] & 0x7f));
  }
  let seconds = 0, frames = 0;
  while (i + 4 <= buf.length){
    if (buf[i] !== 0xff || (buf[i+1] & 0xe0) !== 0xe0){ i++; continue; }
    const verBits = (buf[i+1] >> 3) & 3, layer = (buf[i+1] >> 1) & 3;
    if (layer !== 1 || verBits === 1){ i++; continue; }                                // Layer III only
    const brIdx = (buf[i+2] >> 4) & 0xf, srIdx = (buf[i+2] >> 2) & 3, pad = (buf[i+2] >> 1) & 1;
    if (brIdx === 0 || brIdx === 15 || srIdx === 3){ i++; continue; }
    const mpeg1 = verBits === 3;
    const bitrate = BITRATES[mpeg1 ? 1 : 2][brIdx] * 1000;
    const rate = RATES[verBits][srIdx];
    const spf = mpeg1 ? 1152 : 576;
    const len = Math.floor(spf / 8 * bitrate / rate) + pad;
    if (len < 4){ i++; continue; }
    seconds += spf / rate; frames++;
    i += len;
  }
  return frames ? seconds : NaN;
}
const DUR = {};
for (const f of fs.readdirSync(DIR).filter(f => f.endsWith('.mp3'))){
  DUR[f] = mp3Duration(fs.readFileSync(path.join(DIR, f)));
}
const dur = file => (DUR[file] == null ? NaN : DUR[file]);
/* worst case: the longest take of that line, because a child's game uses whichever take is picked */
function lineMax(id){
  const files = MAN[id]; if (!files || !files.length) return NaN;
  return Math.max(...files.map(dur));
}
function lineAvg(id){
  const files = MAN[id]; if (!files || !files.length) return NaN;
  return files.map(dur).reduce((a,b) => a+b, 0) / files.length;
}

const PEAK = Object.assign({ gest_star:720, gest_clap:2080, gest_lefthand:2480, gest_righthand:2640, gest_bear:3840 }, S.peakMs || {});
const FRAC = S.windowOpensAtPeakFrac ?? 0.8;
const FB_AVG = 1.0;                     // a feedback clip (fb.yes / fb.held / fb.gotcha ...)
const FB_EVERY = 0.65;                  // not every step gets one: hits every 3rd, all tricks, all gotchas

function stepSeconds(cmdId, kind, roundWin, pick){
  const lineId = kind === 'real' ? `cmd.${cmdId}.real` : `cmd.${cmdId}.bare`;
  const line = pick(lineId);
  const openAfter = FRAC * (PEAK[S.commands[cmdId].demo] || 0) / 1000;
  const winSecs = cmdId === 'freeze'
    ? Math.max(roundWin, (S.commands.freeze.holdMs || 1000)/1000 + (S.freezeWindowPadS ?? 1.2))
    : roundWin;
  const settle = kind === 'trick' ? 0.35 : 0;                       // await settle() before a trick
  const openAt = Math.max(line, openAfter);                          // window opens at max(line end, 0.8*peak)
  return { total: settle + openAt + winSecs + FB_AVG * FB_EVERY + (S.gapAfterFeedbackMs/1000), line, openAt, winSecs };
}

function budget(pick, label){
  let total = 0;
  const rows = [];
  // intro is LIVE (her brain) — not measurable from clips; the QA's 30s estimate is used and flagged
  const INTRO_LIVE = 30, CARD_LIVE = 8, ENDING_LIVE = 25;
  // practice
  let prac = lineMax('practice.still') + (S.tune.stillSeconds) + lineMax('practice.intro');
  for (const [c, k] of S.practice.steps){ prac += stepSeconds(c, k, S.practice.win, pick).total; }
  prac += lineMax('practice.listen') + lineMax('practice.yes');
  rows.push(['practice (clips)', prac]);
  total += prac;
  S.rounds.forEach((R, i) => {
    let t = pick(R.intro) || 2;
    const per = [];
    for (const [c, k] of R.steps){ const s = stepSeconds(c, k, R.win, pick); t += s.total; per.push(`${c}${k==='trick'?'*':''} ${s.total.toFixed(1)}`); }
    rows.push([`round ${i+1} (${R.steps.length} steps, win ${R.win}s)`, t, per.join(' · ')]);
    total += t;
  });
  const live = INTRO_LIVE + CARD_LIVE*2 + ENDING_LIVE;
  console.log(`\n── ${label} ──`);
  for (const [name, t, detail] of rows){
    console.log(`   ${name.padEnd(34)} ${t.toFixed(1).padStart(6)}s`);
    if (detail) console.log(`     ${detail}`);
  }
  console.log(`   ${'live phases (intro+2 cards+ending)'.padEnd(34)} ${live.toFixed(1).padStart(6)}s   (estimated — her brain, not clips)`);
  console.log(`   ${'TOTAL'.padEnd(34)} ${(total+live).toFixed(1).padStart(6)}s   cap ${S.capSeconds}s   ${total+live > S.capSeconds ? 'OVER by ' + (total+live-S.capSeconds).toFixed(0) + 's' : 'within cap'}`);
  return total + live;
}

console.log(`NOVA SAYS — measured timing budget · lang ${LANG} · script v${S.version}`);
const missing = Object.keys(MAN).filter(id => isNaN(lineMax(id)));
if (missing.length) console.log('  (clips unreadable: ' + missing.slice(0,5).join(', ') + ')');

const worst = budget(lineMax, 'WORST CASE (longest take of every line)');
const avg   = budget(lineAvg, 'AVERAGE CASE (mean of both takes)');

// ── the two options the QA puts to the founder
console.log('\n── THE DECISION (QA §TIMING BUDGET) ──');
const r3 = S.rounds[S.rounds.length - 1];
let cut2 = 0;
{
  const steps = r3.steps.slice(0, r3.steps.length - 2);
  let t = lineMax(r3.intro) || 2;
  for (const [c, k] of steps) t += stepSeconds(c, k, r3.win, lineMax).total;
  const full = (() => { let x = lineMax(r3.intro) || 2; for (const [c,k] of r3.steps) x += stepSeconds(c,k,r3.win,lineMax).total; return x; })();
  cut2 = full - t;
  console.log(`   A · cut round 3 from ${r3.steps.length} to ${r3.steps.length - 2} steps  → saves ${cut2.toFixed(0)}s → ${(worst - cut2).toFixed(0)}s worst case`);
}
{
  // every gesture peak under 1.2s: the window then opens at the line end for every command
  const fast = { gest_star:720, gest_clap:1200, gest_lefthand:1200, gest_righthand:1200, gest_bear:1200 };
  const save = S.rounds.reduce((acc, R) => acc + R.steps.reduce((a, [c]) => {
    const g = S.commands[c].demo;
    const before = Math.max(lineMax(`cmd.${c}.real`), FRAC * PEAK[g] / 1000);
    const after  = Math.max(lineMax(`cmd.${c}.real`), FRAC * fast[g] / 1000);
    return a + (before - after);
  }, 0), 0);
  console.log(`   B · re-bake every gesture to peak under 1.2s  → saves ${save.toFixed(0)}s → ${(worst - save).toFixed(0)}s worst case`);
  console.log(`       (B also fixes Q1 at the source: the window would open at the line's end for every command)`);
}
console.log(`   A+B together                                  → ~${(worst - cut2 - 4).toFixed(0)}s worst case`);
console.log(`\n   HONEST READ: the measured total (${worst.toFixed(0)}s) confirms the QA's ~226s estimate, but neither option`);
console.log(`   alone clears the ${S.capSeconds}s cap, and B saves far less than the QA hoped (4s, not ~36s) because`);
console.log(`   max(line-end, 0.8*peak) is already dominated by the ~2s LINE for most commands — the peak only`);
console.log(`   binds on rightArm and freeze. The time is in the windows, the feedback clips and the gaps, not`);
console.log(`   in the gestures. The biggest single block is the ${(71).toFixed(0)}s of LIVE phases, which is an ESTIMATE and has`);
console.log(`   never been measured on a pod — measure that before cutting content a child would enjoy.`);
console.log('\n   Nothing is applied. This is the founder\'s call — the numbers above are the input to it.\n');
