// Runner cd's into tools/laws/; the checks below use repo-root-relative paths.
process.chdir(require('path').resolve(__dirname, '..', '..'));
// LAW-PROMPTS: certified prompt files exist and no page carries inline persona text.
const fs = require('fs');
const files = ['core-laws','freeze-rules','upgroove-persona','wave-persona']
  .map(n => `pod/prompts/${n}.txt`);
let fail = false;
for (const f of files) {
  if (!fs.existsSync(f) || fs.readFileSync(f,'utf8').trim().length < 40) {
    console.error(`LAW-PROMPTS FAIL: missing/empty ${f}`); fail = true;
  }
}
for (const page of ['pod/pages/up-groove.html','pod/pages/wave.html']) {
  if (!fs.existsSync(page)) continue;
  const s = fs.readFileSync(page,'utf8');
  if (/\[GAME-MODE\]/.test(s)) {           // persona text belongs in pod/prompts/, not pages
    console.error(`LAW-PROMPTS FAIL: inline persona text in ${page}`); fail = true;
  }
  if (!/fetch\([^)]*\/prompts\//.test(s)) {   // fetch(location.origin + '/prompts/..') — base-href-safe
    console.error(`LAW-PROMPTS FAIL: ${page} does not load its persona from /prompts/`); fail = true;
  }
}
if (fail) process.exit(1);
console.log('LAW-PROMPTS OK');
