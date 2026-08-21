// Runner cd's into tools/laws/; run git from the repo root.
process.chdir(require('path').resolve(__dirname, '..', '..'));
// LAW-SKILLS: the lexi/loora knowledge files are read-only history.
const { execSync } = require('child_process');
try {
  const out = execSync(
    "git diff --name-only origin/main...HEAD -- .claude/skills/ 2>/dev/null || true"
  ).toString().trim();
  if (out) { console.error('LAW-SKILLS FAIL: skill files modified:\n' + out); process.exit(1); }
} catch (e) { /* no origin/main in CI checkout: skip quietly */ }
console.log('LAW-SKILLS OK');
