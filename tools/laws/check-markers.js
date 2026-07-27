// tools/laws/check-markers.js — the LAWS.md ↔ codebase consistency gate.
//
// LAWS.md is the append-only registry. It carries a machine-readable block:
//
//   ```laws
//   law-id | status | file1,file2 | marker one ;; marker two
//   ```
//
// For every ACTIVE law, every marker must still be found in at least one of its
// files. A missing marker means a registered law silently vanished from the
// code → exit 1 with the law's name (the RED build). LOST laws are reported but
// not gated. This catches removals even for laws without a dedicated law-*.js.
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const md = fs.readFileSync(path.join(ROOT, 'LAWS.md'), 'utf8');

const m = md.match(/```laws\s*([\s\S]*?)```/);
if (!m) { console.log('  ✗ LAWS.md has no ```laws``` registry block'); process.exit(1); }

const rows = m[1].split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));
let failed = 0, checked = 0, lost = 0;

function fileHas(rel, marker) {
  try {
    const src = fs.readFileSync(path.join(ROOT, rel), 'utf8');
    return src.includes(marker);
  } catch (_) { return false; }
}

for (const row of rows) {
  const [id, status, files, markers] = row.split('|').map(s => s.trim());
  if (!id) continue;
  if (status !== 'active') { lost++; console.log(`  ⚠ ${id} — status ${status}, not marker-gated`); continue; }
  const fileList = files.split(',').map(s => s.trim()).filter(Boolean);
  const markerList = markers.split(';;').map(s => s.trim()).filter(Boolean);
  for (const marker of markerList) {
    checked++;
    const found = fileList.some(f => fileHas(f, marker));
    if (!found) {
      failed++;
      console.log(`  ✗ ${id} — MARKER LOST: "${marker}" not found in ${fileList.join(', ')}`);
    }
  }
}

if (failed) {
  console.log(`  ❌ ${failed} registered marker(s) missing — a law vanished from the code.`);
  process.exit(1);
}
console.log(`  ✓ ${checked} active markers present · ${lost} law(s) known-lost.`);
process.exit(0);
