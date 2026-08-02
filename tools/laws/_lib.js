// tools/laws/_lib.js — shared harness for the Nova law-tests (Guardian, 2026-07-27).
//
// Each law-*.js is a tiny script that describes ONE law: the files it guards,
// the markers that must be PRESENT, and (optionally) the anti-markers that must
// be ABSENT. This lib does the grepping, prints a uniform PASS/FAIL/LOST line,
// and sets the process exit code with the right "wall" semantics:
//
//   status: 'active'  → a violation is a REGRESSION → exit 1 (RED build, wall).
//   status: 'lost'    → the law was ALREADY lost before the Guardian existed.
//                       A violation is EXPECTED. It is reported loudly but does
//                       NOT fail the build — so the founder can restore it on
//                       their own clock. The moment they restore + flip it to
//                       'active', any future removal turns the build RED.
//
// No dependencies. Node >= 16. Runs on Linux CI and local Git-Bash alike.

const fs = require('fs');
const path = require('path');

// Repo root = two levels up from tools/laws/.
const ROOT = path.resolve(__dirname, '..', '..');

function read(rel) {
  const p = path.join(ROOT, rel);
  try { return fs.readFileSync(p, 'utf8'); }
  catch (_) { return null; }
}

// Does `rel` contain a match for `pattern` (string=literal, RegExp=as-is)?
function has(rel, pattern) {
  const src = read(rel);
  if (src == null) return { ok: false, missing: 'file', file: rel };
  const re = pattern instanceof RegExp ? pattern : new RegExp(escape(pattern), 'i');
  return { ok: re.test(src), file: rel, pattern: String(pattern) };
}

function count(rel, pattern) {
  const src = read(rel);
  if (src == null) return 0;
  const re = pattern instanceof RegExp
    ? new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : pattern.flags + 'g')
    : new RegExp(escape(pattern), 'gi');
  const m = src.match(re);
  return m ? m.length : 0;
}

function escape(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

// Run a law. `checks` is an array of {desc, rel, present?, absent?} where
// present = pattern that MUST match, absent = pattern that must NOT match.
// Returns true if every check passed.
function runLaw({ id, title, status = 'active', why, checks }) {
  const fails = [];
  for (const c of checks) {
    if (c.present !== undefined) {
      const r = has(c.rel, c.present);
      if (!r.ok) fails.push(`  ✗ ${c.desc} — expected ${fmt(c.present)} in ${c.rel}${r.missing === 'file' ? ' (FILE MISSING)' : ''}`);
    }
    if (c.absent !== undefined) {
      const r = has(c.rel, c.absent);
      if (r.ok) fails.push(`  ✗ ${c.desc} — forbidden ${fmt(c.absent)} FOUND in ${c.rel}`);
    }
  }

  const passed = fails.length === 0;
  if (passed) {
    console.log(`PASS  ${id} — ${title}`);
    process.exitCode = process.exitCode || 0;
    return true;
  }

  if (status === 'lost') {
    console.log(`LOST  ${id} — ${title}   ⚠ known-lost, awaiting founder restore (non-blocking)`);
    fails.forEach(f => console.log(f));
    // do NOT fail the build for a pre-existing loss
    return false;
  }

  console.log(`FAIL  ${id} — ${title}   ✗ ACTIVE LAW VIOLATED — build must go RED`);
  fails.forEach(f => console.log(f));
  process.exitCode = 1;
  return false;
}

function fmt(p) { return p instanceof RegExp ? `/${p.source}/` : `"${p}"`; }

module.exports = { ROOT, read, has, count, runLaw };
