// tools/laws/check-syntax.js — syntax-guard. Extracts inline <script> blocks
// from the live game files and syntax-checks each (vm.Script compiles without
// executing — so browser globals are irrelevant, only SYNTAX is judged), plus
// node --check on the standalone shared JS. A broken brace in a game file is
// caught here before it ever ships. Exit 1 on any syntax error.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const cp = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
// maya-stage.html IS the stream and maya-director.html is the only way to steer it —
// a broken brace in either is a dead broadcast, so they get the same guard as the games.
const HTML = ['nova-commercial.html', 'animal-freeze.html',
              'maya-stage.html', 'maya-director.html'];
const JS = ['nova-ending.js', 'nova-engine.js', 'nova-light.js', 'nova-session-rec.js'];

let errors = 0;

function checkInline(rel) {
  const p = path.join(ROOT, rel);
  if (!fs.existsSync(p)) { console.log(`  ✗ FILE MISSING: ${rel}`); errors++; return; }
  const src = fs.readFileSync(p, 'utf8');
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m, n = 0, bad = 0;
  while ((m = re.exec(src))) {
    const attrs = m[1] || '';
    // skip external scripts and non-JS payloads (JSON choreo blocks, etc.)
    if (/\bsrc=/i.test(attrs)) continue;
    if (/type=/i.test(attrs) && !/type=["']?(text\/javascript|module|application\/javascript)/i.test(attrs)) continue;
    const code = m[2];
    if (!code.trim()) continue;
    n++;
    const line = src.slice(0, m.index).split('\n').length;
    try { new vm.Script(code, { filename: `${rel}#script@L${line}` }); }
    catch (e) { console.log(`  ✗ ${rel} inline <script> @L${line}: ${e.message}`); bad++; errors++; }
  }
  if (!bad) console.log(`  ✓ ${rel} — ${n} inline script block(s) OK`);
}

function checkJs(rel) {
  const p = path.join(ROOT, rel);
  if (!fs.existsSync(p)) { console.log(`  – ${rel} (absent, skipped)`); return; }
  try { cp.execFileSync(process.execPath, ['--check', p], { stdio: 'pipe' }); console.log(`  ✓ ${rel} — syntax OK`); }
  catch (e) { console.log(`  ✗ ${rel}: ${String(e.stderr || e.message).split('\n')[0]}`); errors++; }
}

console.log(' Syntax guard (inline + shared JS):');
HTML.forEach(checkInline);
JS.forEach(checkJs);
process.exit(errors ? 1 : 0);
