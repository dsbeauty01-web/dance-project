/* test/stage_test.mjs — node test/stage_test.mjs  (fake clock, no browser) */
import { Stage, TIER } from '../shared/stage.js';

let T = 0; const now = () => T; const adv = ms => { T += ms; };
function mk(extra = {}){
  const log = { spoke: [], remembered: [], clips: [], bodies: [], lights: [] };
  const s = new Stage({ now, speakNow: t => log.spoke.push(t), remember: n => log.remembered.push(n), playClip: c => { log.clips.push(c); return Promise.resolve(); },
    setBody: b => log.bodies.push(b), light: l => log.lights.push(l), ...extra });
  return { s, log };
}
let pass = 0, fail = 0; const out = [];
function ok(name, cond){ cond ? pass++ : fail++; out.push(`${cond ? 'PASS' : 'FAIL'}  ${name}`); }
function run(s, ms, step = 50){ for (let i = 0; i < ms; i += step){ adv(step); s.tick(); } }

// 1 · never speaks while the kid is talking; speaks once the gap has passed
{ T = 0; const { s, log } = mk(); s.phase('between', { live:true }); s.setKidSpeaking(true);
  s.requestSpeak('Great round!'); run(s, 1000);
  ok('does not speak while the kid is talking', log.spoke.length === 0);
  s.setKidSpeaking(false); run(s, 300);
  ok('still waits during the idle gap (300ms < 600ms)', log.spoke.length === 0);
  run(s, 400);
  ok('speaks once the kid has been quiet ≥ 600ms', log.spoke.length === 1); }

// 2 · never speaks while SHE is talking (no talk-over of herself)
{ T = 0; const { s, log } = mk(); s.phase('between', { live:true }); s.setNovaSpeaking(true);
  s.requestSpeak('line 2', { maxWaitMs: 10000 }); run(s, 2000);
  ok('does not stack a line on top of her own speech', log.spoke.length === 0);
  s.setNovaSpeaking(false); run(s, 700);
  ok('speaks after her previous line ends + gap', log.spoke.length === 1); }

// 3 · show phases never get live speech; the request falls back to a recorded clip
{ T = 0; const { s, log } = mk(); s.phase('round', { live:false });
  const p = s.requestSpeak('mid-round chatter', { fallbackClip: 'held.statue', maxWaitMs: 1500 }); run(s, 2000);
  ok('no live speech during a show phase', log.spoke.length === 0);
  ok('falls back to the recorded clip after maxWait', log.clips.includes('held.statue')); }

// 4 · a request with no fallback is dropped (never spoken late)
{ T = 0; const { s, log } = mk(); s.phase('between', { live:true }); s.setKidSpeaking(true);
  let result; s.requestSpeak('late line', { maxWaitMs: 1000 }).then(r => result = r); run(s, 1500);
  await Promise.resolve();
  ok('stale speech request dropped, not spoken late', log.spoke.length === 0 && result === 'dropped'); }

// 5 · facts: coalesced by key (burst collapses to the latest)
{ T = 0; const { s } = mk(); s.event('arm_up', { n:1 }, { key:'pose' }); adv(100); s.event('arm_up', { n:2 }, { key:'pose' }); adv(100); s.event('arm_down', {}, { key:'pose' });
  const f = s.fresh(); ok('a burst on one key collapses to one fact (latest wins)', f.length === 1 && f[0].type === 'arm_down'); }

// 6 · facts expire — she never mentions something from 10 seconds ago
{ T = 0; const { s } = mk(); s.event('froze', { round:1 }, { ttlMs: 2500 }); adv(3000);
  ok('an expired fact is gone', s.fresh().length === 0 && s.factsNote() === null); }

// 7 · the note is time-stamped and confidence-tiered
{ T = 0; const { s } = mk(); s.event('froze', { round:2 }, { key:'f', conf:0.9 }); s.event('moved', {}, { key:'m', conf:0.4 }); adv(1200);
  const n = s.factsNote(); ok('note carries age + tier per fact', /1\.2s ago · high\] froze/.test(n) && /· low\] moved/.test(n)); }

// 8 · facts are written silently at most once per second
{ T = 0; const { s, log } = mk(); s.event('x'); for (let i = 0; i < 20; i++){ adv(100); s.tick(); }
  ok('silent fact notes throttled to ~1/s', log.remembered.length === 2); }

// 9 · when she speaks, fresh facts go in first (so her line is true)
{ T = 0; const { s, log } = mk(); s.phase('between', { live:true }); s.lastSpeechEnd = -1e9;
  s.event('froze', { best:'flamingo' }, { conf:0.95 }); s.requestSpeak('React to the round'); run(s, 100);
  ok('facts written right before the speak', log.remembered.length >= 1 && /flamingo/.test(log.remembered.at(-1)) && log.spoke.length === 1); }

// 10 · gestures are commands: body changes, speech untouched, auto-return to rest
{ T = 0; const { s, log } = mk(); s.loadGestures({ wave: { bake:'gest_wave', durMs:900, peakMs:400 } });
  s.phase('between', { live:true }); s.setNovaSpeaking(true); s.gesture('wave'); run(s, 1000);
  ok('gesture switches the body', log.bodies[0] === 'gest_wave');
  ok('gesture returns to rest when the bake ends', log.bodies.at(-1) === 'nova_idle2');
  ok('gesture never cancels or triggers speech', log.spoke.length === 0 && s.novaSpeaking === true); }

// 11 · cue sheet: ordered, and peak-aligned gestures start early so the PEAK lands on the beat
{ T = 0; const { s } = mk(); s.loadGestures({ star: { bake:'gest_star', durMs:1300, peakMs:700 } });
  const sched = []; const plan = s.runCue([{ atMs:2000, clip:'cmd.armsUp' }, { atMs:2000, gesture:'star', peakAlign:true }, { atMs:2000, light:'wrists' }], (fn, ms) => sched.push(ms));
  ok('peak-aligned gesture starts 700ms early (1300ms)', sched.includes(1300));
  ok('cue items sorted by time', JSON.stringify(sched) === JSON.stringify([...sched].sort((a,b)=>a-b))); }

// 12 · praise follows confidence
{ T = 0; const { s } = mk(); const tpl = { high:['held.flamingo'], mid:['held.statue'], low:[] };
  ok('high confidence → specific praise', s.praise(tpl, 0.92, a => a[0]) === 'held.flamingo');
  ok('mid confidence → generic praise', s.praise(tpl, 0.6, a => a[0]) === 'held.statue');
  ok('low confidence → stay quiet', s.praise(tpl, 0.3, a => a[0]) === null); }

// 13 · memory: dedupe, cap, note
{ T = 0; const { s } = mk({ cfg:{ maxFacts:3 } }); s.loadMemory(['name: Noam']); s.addFact('favorite animal: flamingo'); s.addFact('name: Noam'); s.addFact('best freeze: star'); s.addFact('likes fast songs');
  ok('memory dedupes and keeps the newest N', s.facts.length === 3 && s.facts[0] === 'name: Noam' && s.facts.at(-1) === 'likes fast songs' && !s.facts.includes('favorite animal: flamingo'));
  ok('memory note lists the facts', /likes fast songs/.test(s.memoryNote())); }

// 14 · switching to a show phase clears pending live-only requests
{ T = 0; const { s, log } = mk(); s.phase('between', { live:true }); s.setKidSpeaking(true);
  s.requestSpeak('only live'); s.requestSpeak('with backup', { fallbackClip:'fallback.card1', maxWaitMs:500 });
  s.phase('round', { live:false }); s.setKidSpeaking(false); run(s, 800);
  ok('entering a round drops live-only speech, keeps the recorded fallback', log.spoke.length === 0 && log.clips.includes('fallback.card1')); }

console.log(out.join('\n')); console.log(`\n${pass} pass · ${fail} fail`); process.exit(fail ? 1 : 0);
