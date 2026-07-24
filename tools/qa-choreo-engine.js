// QA — CHOREO ENGINE v1 (permanent harness)
// Proves, without a browser:
//  1. Every inline <script> in nova-commercial.html parses (syntax).
//  2. CHOREO_EMBED.wavemagic ≡ wavemagic.choreo.json  (runtime source == canonical file).
//  3. The REAL choreoToTimeline() (extracted from the page) reproduces the corrected legacy
//     TIMELINE_WAVEMAGIC_RAW byte-for-byte (ignoring the additive cueStyle field) — i.e. the
//     data-driven engine is behavior-preserving vs the hand-authored timeline.
//  4. validateChoreo() accepts the real choreo and REJECTS a malformed one (unknown move).
// Usage: node tools/qa-choreo-engine.js
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'nova-commercial.html'), 'utf8');
const JSONFILE = JSON.parse(fs.readFileSync(path.join(ROOT, 'wavemagic.choreo.json'), 'utf8'));

let pass = 0, fail = 0;
const ok  = (n, d = '') => { pass++; console.log('PASS  ' + n + (d ? '  — ' + d : '')); };
const bad = (n, d = '') => { fail++; console.log('FAIL  ' + n + (d ? '  — ' + d : '')); };

// ── 1. syntax of every inline script ───────────────────────────────
{
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m, i = 0, badCount = 0;
  while ((m = re.exec(HTML))) {
    if (/\bsrc\s*=/.test(m[1] || '')) continue;
    if (/type\s*=\s*["'](?!text\/javascript|module|application\/javascript)/i.test(m[1] || '')) continue;
    i++;
    try { new vm.Script(m[2], { filename: 'inline-' + i }); }
    catch (e) { badCount++; console.log('   syntax error in inline script #' + i + ': ' + e.message); }
  }
  badCount === 0 ? ok('all ' + i + ' inline scripts parse') : bad(badCount + ' inline scripts failed to parse');
}

// ── extract the REAL engine block + the legacy RAW array from the page ──
function extractEngine() {
  const start = HTML.indexOf('const CHOREO_REGISTRY');
  const end = HTML.indexOf('window.__CHOREO_EMBED = CHOREO_EMBED;');
  if (start < 0 || end < 0) throw new Error('engine block not found in page');
  const block = HTML.slice(start, end);
  const sandbox = { console, window: {} };
  return vm.runInNewContext(block + '\n;({ validateChoreo, choreoToTimeline, CHOREO_EMBED, CHOREO_REGISTRY });', sandbox);
}
function extractRaw() {
  const m = HTML.match(/const TIMELINE_WAVEMAGIC_RAW = (\[[\s\S]*?\]);/);
  if (!m) throw new Error('TIMELINE_WAVEMAGIC_RAW not found');
  return vm.runInNewContext(m[1]);
}

let ENG, RAW;
try { ENG = extractEngine(); ok('engine block extracted + evaluated'); }
catch (e) { bad('engine block extract', e.message); }
try { RAW = extractRaw(); ok('legacy TIMELINE_WAVEMAGIC_RAW extracted'); }
catch (e) { bad('raw extract', e.message); }

if (ENG && RAW) {
  const embed = ENG.CHOREO_EMBED.wavemagic;
  // Objects from vm.runInNewContext live in a separate realm (different Object.prototype),
  // which trips deepStrictEqual's prototype check even when values are identical. Compare
  // by a CANONICAL serialization instead: recursively key-sorted JSON — realm-agnostic and
  // key-order-insensitive (our data has no undefined/functions, so this is lossless).
  const canon = v => JSON.stringify(v, function sorter(k, val) {
    if (val && typeof val === 'object' && !Array.isArray(val)) {
      return Object.keys(val).sort().reduce((o, kk) => (o[kk] = val[kk], o), {});
    }
    return val;
  });
  const eq = (a, b) => canon(a) === canon(b);

  // ── 2. embed ≡ external json ─────────────────────────────────────
  eq(embed, JSONFILE) ? ok('CHOREO_EMBED.wavemagic ≡ wavemagic.choreo.json')
                      : bad('embed ≡ file', 'embed and JSON file differ — regenerate one from the other');

  // ── 4a. validate accepts the real choreo ─────────────────────────
  const v = ENG.validateChoreo(embed);
  v.ok ? ok('validateChoreo accepts wavemagic') : bad('validateChoreo rejects wavemagic', JSON.stringify(v.errors));

  // ── 4b. validate REJECTS a malformed choreo (unknown move) ───────
  const broken = JSON.parse(JSON.stringify(embed));
  broken.windows[0].move = 'moonwalk';           // not in the registry
  broken.bogusField = true;                        // unknown top-level field
  const vb = ENG.validateChoreo(broken);
  (!vb.ok && vb.errors.some(e => /moonwalk/.test(e)) && vb.errors.some(e => /bogusField/.test(e)))
    ? ok('validateChoreo rejects malformed choreo (unknown move + field)')
    : bad('malformed choreo not rejected', JSON.stringify(vb.errors));

  // ── 3. adapter reproduces the legacy corrected timeline ──────────
  const strip = ev => { const { cueStyle, ...rest } = ev; return rest; };   // cueStyle is additive
  const built = ENG.choreoToTimeline(embed).map(strip);
  if (built.length === RAW.length && built.every((e, i) => eq(e, RAW[i]))) {
    ok('choreoToTimeline(wavemagic) ≡ legacy corrected TIMELINE_WAVEMAGIC_RAW', built.length + ' events');
  } else {
    bad('adapter != legacy timeline', 'engine would change Wave Magic behavior');
    for (let i = 0; i < Math.max(built.length, RAW.length); i++) {
      if (!eq(built[i], RAW[i])) {
        console.log('   first diff @' + i + ':\n     built: ' + canon(built[i]) + '\n     raw  : ' + canon(RAW[i]));
        break;
      }
    }
  }

  // ── spec sanity on the built timeline ────────────────────────────
  const opens = built.filter(e => e.type === 'open');
  const closes = built.filter(e => e.type === 'close');
  const lastClose = Math.max(...closes.map(c => c.t));
  ok('windows: ' + opens.length + ' opens / ' + closes.length + ' closes; last close ' + lastClose + ' < ' + embed.media.durationMs,
     lastClose < embed.media.durationMs ? '' : 'OVERRUN!');
  const allInReg = opens.every(o => ENG.CHOREO_REGISTRY.includes(o.action));
  allInReg ? ok('every window move ∈ registry') : bad('a window move is not in the registry');

  // ── 5. inline data-choreo blocks: present, parse, validate, ≡ canonical .json ──
  const blockRe = /<script[^>]*\bdata-choreo\b[^>]*id="choreo-([a-z0-9_]+)"[^>]*>([\s\S]*?)<\/script>/gi;
  let bm, blocks = 0;
  const seen = new Set();
  while ((bm = blockRe.exec(HTML))) {
    blocks++;
    const id = bm[1];
    seen.add(id);
    let parsed;
    try { parsed = JSON.parse(bm[2]); } catch (e) { bad('inline block choreo-' + id + ' parses', e.message); continue; }
    // block ≡ canonical file
    const file = path.join(ROOT, id + '.choreo.json');
    if (!fs.existsSync(file)) { bad('inline block choreo-' + id + ' has a .json file'); continue; }
    const fileJson = JSON.parse(fs.readFileSync(file, 'utf8'));
    eq(parsed, fileJson) ? ok('inline choreo-' + id + ' ≡ ' + id + '.choreo.json')
                         : bad('inline choreo-' + id + ' ≠ its .json file', 're-run tools/build-choreo.js');
    // validates + resolves as data-driven
    ENG.validateChoreo(parsed).ok ? ok('choreo-' + id + ' validates')
                                  : bad('choreo-' + id + ' fails validation');
  }
  blocks >= 5 ? ok('inline choreo blocks present', blocks + ' games wired as data')
              : bad('too few inline choreo blocks', 'found ' + blocks + ', expected ≥5 — run tools/build-choreo.js');
}

console.log('\nCHOREO ENGINE QA: ' + pass + ' pass / ' + fail + ' fail');
process.exit(fail ? 1 : 0);
