/* tools/laws/kid-screen-guard.mjs — the kid-screen wall (6-hour mission, Phase 5).
   Fails the build if a kid-facing beta file shows a number-score or a fail colour:
     visible strings (JS string literals + HTML text) must not contain  +<digits> · "score" · "points" · "%"
     anywhere (CSS too) no  #ff0000 / #f00 / the colour word red
   Comments are ignored — a comment may say what was removed. */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const FILES = ['beta/index.html', 'beta/freeze3.html', 'beta/copy.html', 'beta/groove.html', 'beta/play.css',
               'beta/demo.html', 'beta/lib/play.js', 'beta/lib/doctor.js', 'shared/nova-lights.js', ...process.argv.slice(2)];   // extra files: the guard's own self-test

const TOKEN = /\/\*[\s\S]*?\*\/|<!--[\s\S]*?-->|\/\/[^\n]*|'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`/g;
function jsStrings(src){ const out = []; for (const m of src.matchAll(TOKEN)){ const s = m[0]; if (s[0] === '/' || s.startsWith('<!--')) continue; out.push({ s: s.slice(1, -1), at: m.index }); } return out; }
function stripComments(src){ return src.replace(TOKEN, m => (m[0] === '/' || m.startsWith('<!--')) ? '' : m); }
const lineOf = (src, i) => src.slice(0, i).split('\n').length;

const VISIBLE = [[/\+\d+/, 'a "+number"'], [/\bscore\b/i, '"score"'], [/\bpoints?\b/i, '"points"'], [/%/, 'a "%"']];
const COLOUR = [[/#ff0000\b|#f00\b/i, '#ff0000'], [/(^|[^-\w])red\b/i, 'the colour red']];
let fails = 0;
const bad = (f, line, what, text) => { fails++; console.log(`  ✗ ${f}:${line} — ${what}: ${text.trim().slice(0, 90)}`); };

for (const f of FILES){
  const src = readFileSync(resolve(ROOT, f), 'utf8');
  const isHtml = f.endsWith('.html'), isCss = f.endsWith('.css');
  // colours: everywhere except comments
  const code = stripComments(src);
  code.split('\n').forEach((l, i) => { for (const [re, what] of COLOUR) if (re.test(l)) bad(f, i + 1, what, l); });
  if (isCss) continue;
  // visible strings: JS string literals (in .js and in <script>) + HTML text nodes
  let js = src, text = '';
  if (isHtml){
    js = [...src.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
    text = src.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<!--[\s\S]*?-->/g, '').replace(/<[^>]+>/g, '\n');
  }
  for (const { s, at } of jsStrings(js)){
    if (/^[\w-]+\s*:[^;]+;/.test(s)) continue;                                            // a CSS declaration (cssText), not text
    if (/^(\.\.?\/|https?:)/.test(s) || /^[\w./-]+\.(js|json|css|mp3|webm|mp4|html)$/.test(s)) continue;     // file paths / URLs are not shown
    for (const [re, what] of VISIBLE) if (re.test(s)) bad(f, lineOf(js, at), what + ' in a string', s);
  }
  text.split('\n').forEach(l => { for (const [re, what] of VISIBLE) if (re.test(l)) bad(f, '-', what + ' in page text', l); });
}
console.log(fails ? `KID-SCREEN GUARD: ❌ ${fails} problem(s)` : `KID-SCREEN GUARD: ✅ ${FILES.length} kid-screen files clean (no +N, score, points, %, red)`);
process.exit(fails ? 1 : 0);
