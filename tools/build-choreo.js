// BUILD — generate {id}.choreo.json for every game from the legacy TIMELINE_*_RAW arrays
// in nova-commercial.html, then PROVE each generated choreo round-trips: the page's real
// choreoToTimeline(choreo) must reproduce that game's legacy timeline exactly (canonical,
// key-sorted, realm-agnostic compare). This is how "a game = a JSON" is created without
// hand-transcription and without drift.
//
//   node tools/build-choreo.js          # generate + verify all games
//   node tools/build-choreo.js --check  # verify only (no write) — used by qa
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'nova-commercial.html'), 'utf8');
const CHECK_ONLY = process.argv.includes('--check');

// ── pull SONGS (+ all TIMELINE_*_RAW it references) out of the page ──
function extractSongs() {
  const s = HTML.indexOf('const TIMELINE_HELLO_RAW');
  const songsAt = HTML.indexOf('const SONGS = {');
  if (s < 0 || songsAt < 0) throw new Error('could not locate TIMELINE/SONGS block');
  const end = HTML.indexOf('\n};', songsAt) + 3;          // first "};" that closes SONGS
  const code = HTML.slice(s, end);
  return vm.runInNewContext(code + '\n;(SONGS);', { window: {}, console });
}
// ── pull the REAL adapter (choreoToTimeline) out of the page ──
function extractAdapter() {
  const s = HTML.indexOf('const CHOREO_REGISTRY');
  const e = HTML.indexOf('window.__CHOREO_EMBED = CHOREO_EMBED;');
  return vm.runInNewContext(HTML.slice(s, e) + '\n;({ choreoToTimeline });', { window: {}, console }).choreoToTimeline;
}

// ── invert a legacy timeline into a choreo object (schema v1) ──
function rawToChoreo(game) {
  const raw = game.timeline;
  const beats = raw.filter(e => e.type === 'beat').map(e => ({ t: e.t, name: e.name }));
  const demos = raw.filter(e => e.type === 'demo').map(e => ({ t: e.t, emoji: e.emoji, label: e.label, instr: e.instr }));
  const windows = [];
  raw.forEach((e, i) => {
    if (e.type !== 'open') return;
    let close = null;
    for (let j = i + 1; j < raw.length; j++) { if (raw[j].type === 'close' && raw[j].action === e.action) { close = raw[j]; break; } }
    const w = { start: e.t, end: close ? close.t : e.t, move: e.action };
    ['pts', 'emoji', 'label', 'instr', 'dir', 'holdMs', 'cueStyle'].forEach(k => { if (e[k] !== undefined) w[k] = e[k]; });
    if (e.soft === true) w.soft = true;
    windows.push(w);
  });
  const choreo = {
    schema: 1, id: game.id, title: game.name,
    media: { video: game.videoFile || null, audio: game.audioFile || null, durationMs: game.durationMs },
    beats, demos, windows,
  };
  if (Array.isArray(game.bakedSpeech) && game.bakedSpeech.length) {
    // SONGS stores bakedSpeech in SECONDS; the choreo schema uses MS (worker-export source).
    choreo.bakedSpeech = game.bakedSpeech.map(b => ({ start: Math.round(b.start * 1000), end: Math.round(b.end * 1000) }));
  }
  return choreo;
}

// canonical (key-sorted) serialization — realm & key-order agnostic
const canon = v => JSON.stringify(v, function s(k, val) {
  if (val && typeof val === 'object' && !Array.isArray(val)) return Object.keys(val).sort().reduce((o, kk) => (o[kk] = val[kk], o), {});
  return val;
});

const SONGS = extractSongs();
const choreoToTimeline = extractAdapter();
const packs = require('./choreo-packs');

// Merge a game's content pack (the "brain") + cueStyle presets onto the generated choreo.
// Pack fields never touch beats/demos/windows timing, so the round-trip proof is unaffected.
const PACK_FIELDS = ['knowledge', 'styleExamples', 'scripted', 'stopResume', 'summaryTemplate', 'dosage', 'noSpeak', 'blocked'];
function applyPack(choreo, pack) {
  if (!pack) return;
  if (pack.cueStyles) choreo.windows.forEach(w => { if (pack.cueStyles[w.move]) w.cueStyle = pack.cueStyles[w.move]; });
  PACK_FIELDS.forEach(f => { if (pack[f] !== undefined) choreo[f] = pack[f]; });
}

let pass = 0, fail = 0, wrote = 0;
const inlineBlocks = [];   // {id, json} for every DATA-driven game (all 6)
for (const id of Object.keys(SONGS)) {
  const game = SONGS[id];
  const choreo = rawToChoreo(game);
  applyPack(choreo, packs[id]);   // brain + cueStyle presets

  // verify: adapter(choreo) reproduces the legacy timeline (minus additive cueStyle)
  const built = choreoToTimeline(choreo).map(ev => { const { cueStyle, ...r } = ev; return r; });
  const raw = game.timeline;
  const equiv = built.length === raw.length && built.every((e, i) => canon(e) === canon(raw[i]));
  const hasBrain = !!(packs[id] && packs[id].knowledge);
  if (equiv) { pass++; console.log(`PASS  ${id.padEnd(9)} round-trips (${built.length} events)${hasBrain ? ' +brain' : ''}`); }
  else {
    fail++; console.log(`FAIL  ${id.padEnd(9)} adapter != legacy timeline`);
    for (let i = 0; i < Math.max(built.length, raw.length); i++) if (canon(built[i]) !== canon(raw[i])) { console.log(`        first diff @${i}:\n          built: ${canon(built[i])}\n          raw  : ${canon(raw[i])}`); break; }
  }

  inlineBlocks.push({ id, json: JSON.stringify(choreo) });   // compact — the runtime source
  if (!CHECK_ONLY) {
    fs.writeFileSync(path.join(ROOT, `${id}.choreo.json`), JSON.stringify(choreo, null, 2) + '\n');
    wrote++; console.log(`      wrote ${id}.choreo.json`);
  }
}

// ── splice the inline <script type=application/json data-choreo> blocks into the page ──
if (!CHECK_ONLY) {
  const START = '<!-- CHOREO-BLOCKS:START -->', END = '<!-- CHOREO-BLOCKS:END -->';
  const s = HTML.indexOf(START), e = HTML.indexOf(END);
  if (s < 0 || e < 0) { console.error('markers not found — add ' + START + ' / ' + END + ' to the page'); process.exit(1); }
  const blocksHtml = inlineBlocks
    .map(b => `<script type="application/json" data-choreo id="choreo-${b.id}">${b.json}</script>`)
    .join('\n');
  const next = HTML.slice(0, s + START.length) + '\n' + blocksHtml + '\n' + HTML.slice(e);
  fs.writeFileSync(path.join(ROOT, 'nova-commercial.html'), next);
  console.log(`      spliced ${inlineBlocks.length} inline choreo blocks into nova-commercial.html`);
}

console.log(`\nBUILD-CHOREO: ${pass} round-trip pass / ${fail} fail${CHECK_ONLY ? ' (check-only)' : `, ${wrote} files written`}`);
process.exit(fail ? 1 : 0);
