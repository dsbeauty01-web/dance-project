// Runner cd's into tools/laws/; the checks below use repo-root-relative paths.
process.chdir(require('path').resolve(__dirname, '..', '..'));
// LAW-VOICE: the founder's voice decision is code. marin default + OpenAI primary.
const fs = require('fs');
const s = fs.readFileSync('pod/rt_lk.py','utf8');
let fail = false;
if (!/NOVA_VOICE",\s*"marin"/.test(s)) {
  console.error('LAW-VOICE FAIL: marin is not the default voice'); fail = true;
}
if (/NOVA_VOICE_BACKEND",\s*"hume"/.test(s)) {
  console.error('LAW-VOICE FAIL: hume set as default backend'); fail = true;
}
if (fail) process.exit(1);
console.log('LAW-VOICE OK');
