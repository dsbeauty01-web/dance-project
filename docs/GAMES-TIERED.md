# GAMES-TIERED — the master (two coach tiers · every game's reaction map on its real clock · graders · beta track + guardian · MOST CODE WRITTEN · CLI deploys)

CLI MANDATE: read the 3 skills in `.claude/skills/` (movement-tracking, game-cues-lights, performance-feedback-ai) BEFORE any game code. Everything lands on `beta`. `main` is frozen until "PROMOTE vX.Y". Genuine gaps → `[CLI-FILL]` logged, never contradicting written values. Laws: INPUT-LOCK, phase machine, live-V2V-only voice, truth-gate, clock law, body maps, FREEZE-APPROVED on freeze files.

═══════════════════════════════════════════════
## 0 · THE TIER CONFIG (one object — every game reads it)
═══════════════════════════════════════════════
```js
// shared/tiers.js
export const TIERS = {
  kids: {   // Freeze · Hello Hello · Up Groove  (ages 4-8)
    voicePrompt: `You are Nova — the most exciting dance friend a kid ever had. 110% energy, sound words (Woohoo! Boom! Yesss!).
React ONLY to facts from your notes. Praise is specific and names the move and the moment ('you froze like a STATUE that time!'), never a trait ('you're amazing'). Max 6 words mid-game, one line per gap. Corrections: at most one per round, future-tense, about the target not the body ('next one — chase the gold further!'). NEVER negative words (no, wrong, bad, didn't, missed). A miss is 'almost — next one's yours!' at most. Reference earlier moments by name. Offer a choice at every phase edge. Between rounds: one strength + one next-cue + one choice question, max 3 lines. Reply only with what Nova says.`,
    praiseRatioMin: 3.0,          // encourage : correct (target 4:1)
    maxWordsMidGame: 6,
    windowScale: 1.0,             // slow 1.0s / fast 0.75s base windows
    graceMissPerRound: 1,
    juice: 'full',                // full gold: orb+ring+ribbon+flare+shimmer+fire
    choicesPerSession: 'every-edge',
    scoreDisplay: 'stars',
    cueLead: { slow: 1.2, fast: 0.8 },
  },
  adult: {  // Wave · Upper Body  (13+)
    voicePrompt: `You are Nova — a calm, confident dance coach. Warm, precise, no baby talk.
React only to facts. Praise is specific and technical ('the wave traveled cleanly wrist to elbow'). Max 10 words mid-game, one line per gap. Corrections welcome: one per round, external-focus and actionable ('lead with the wrist next pass'), never about body parts in the past tense. Numbers and tempo talk are fine. Between rounds: one strength + one correction + 'ready?'. No sound-effect words. Reply only with what Nova says.`,
    praiseRatioMin: 1.5,          // target 2:1
    maxWordsMidGame: 10,
    windowScale: 0.7,
    graceMissPerRound: 0,
    juice: 'cool',                // amber accents, no fire mode, no confetti
    choicesPerSession: 'ready-only',
    scoreDisplay: 'numbers',
    cueLead: { slow: 1.0, fast: 0.7 },
  },
};
export const GAME_TIER = { freeze:'kids', hello:'kids', upgroove:'kids', wave:'adult', upperbody:'adult' };
```
Juice map: `full` = the golden-light engine from UPPERBODY-PERFECT Part 3 as written · `cool` = same engine with `fire=false`, particles×0.4, colors `--gold`→`#e6a93a`, no hipShimmer burst (a thin amber ring instead), no confetti.

═══════════════════════════════════════════════
## 1 · FREEZE (kids · 132s · the certified array stays) — her reaction map
═══════════════════════════════════════════════
```js
// beta/freeze.js — reaction scheduler layered on the certified engine (no timing changes to FREEZES)
const T = TIERS.kids; let gapIdx = 0, memory = { name:null, held:0, streak:0, best:null, moments:[] };
for (const [i, f] of FREEZES.entries()) {
  const prev = FREEZES[i-1];
  // ONE voice event per gap: warning OR hype — never both.
  if (!f.fakeout) scheduleAt(gameT0 + f.at - 4.5, () => {
    if (phase !== 'game') return;
    const memoryLine = (gapIdx % 3 === 2) && memory.best;      // every 3rd gap: reference a real earlier moment
    producerNote(memoryLine
      ? `warn+memory: freeze in 3s. One short warning that references ${memory.best} ("even stiller than the ${memory.best} one?").`
      : `warn: freeze in 3s. Say a SHORT playful warning, 3-5 words, like "get ready to freeeeze!"`);
    gapIdx++;
  });
  scheduleAt(gameT0 + f.at, () => setPhase('hold'));
  scheduleAt(gameT0 + f.at + f.hold, () => {
    setPhase('game'); const v = verdict(f); playDing(v); scoreFreeze(f, v);
    if (v==='HELD'){ memory.held++; memory.streak++; memory.best = f.clip; memory.moments.push(`${f.clip} held`); }
    else memory.streak = 0;
    producerNote(`verdict:${v} clip:${f.clip} streak:${memory.streak}. React 4-6 words, specific, NOW.` +
      (f.fakeout ? ' It was the trick freeze — laugh WITH them: "tricked you — you froze anyway!"' : ''));
  });
}
// intro: setPhase('intro') before the session opens (lips, conversation, name, consent). music start line via note: "music starts — one hype line: 'dance until it STOPS!'"
// ending: setPhase('ending'); note(`ending: name=${memory.name} held=${memory.held} score=${score} best=${memory.best}`) → trio + PULSE.
```
Body map unchanged (idle2 / idlegroove_v2 / pose clips). Lights: add the kids-juice engine to the freeze page — orb on both shoulders pulsing during the -3s warning (the visual "get ready"), ice-flash at the cut, flare on HELD. Cue density law: the warning orb is the ONLY visual cue per gap.

═══════════════════════════════════════════════
## 2 · HELLO HELLO (kids · 111s · video leads · no bake)
═══════════════════════════════════════════════
```js
// SECTIONS: measured from the hello video's own structure — CLI runs motion-energy segmentation on nova-hello.mp4
// to mark the ~6 section boundaries (expect roughly every 15-20s). Paste the map; placeholders:
const SECTIONS = [ {t:0,name:'hello'}, {t:18,name:'groove'}, {t:36,name:'wave-hi'}, {t:55,name:'bounce'}, {t:74,name:'mirror'}, {t:92,name:'big-finish'}, {t:105,name:'end'} ];
sched(0,    () => note('start: "Hello hello! Copy me — let\'s dance together!"'));
for (const s of SECTIONS.slice(1,-1)) sched(s.t, () => note(`section ${s.name}: ONE invite line, 3-5 words, external focus ("follow my hands!").`));
// scoring: mirror-match = kid motion-energy correlates with the video's motion-energy per section (both normalized) → 10 pts/section ≥0.5 corr, 20 ≥0.75. Hype ≤4 per game, facts only.
sched(SECTIONS.at(-1).t, () => { setPhase('ending'); note(`ending: name=… sections=… score=…`); });
```
Layout: the original full-screen-camera Hello layout (ORIGINS) with the kids juice on the kid. Lips: intro + ending only (calm body); video leads mid-game, voice in the air.

═══════════════════════════════════════════════
## 3 · UP GROOVE (kids · 90s · the traced ladder)
═══════════════════════════════════════════════
```js
const LADDER = [ {t:30,part:'head',line:'"HEAD side to side!"'}, {t:35,part:'shoulder',line:'"shoulders now!"'},
  {t:40,part:'ribs',line:'"RIBS!"'}, {t:45,part:'hips',line:'"HIPS!"'}, {t:50,part:'double',line:'"again — FASTER!"'},
  {t:65,part:'chain',line:'"fingers... elbows... wrists!"'}, {t:78,part:'freestyle',line:'"YOUR moves — go wild!"'} ];
sched(8, () => note('groove-in: ONE line, "feel the beat first..."'));
for (const L of LADDER) sched(L.t, () => { note(`ladder ${L.part}: say exactly ${L.line}`); lightCue(L.part); });
// detection + scoring = ORIGINS: ISO.thr {headbob:.22, shrug:.15, ribslide:.18, hipbounce:.18}, points 100/120/140/130, streak×2 at ≥2 (cite nova-joined.html L4354/L4884+).
// hype ≤4 facts; lights: part-specific orb (head/shoulders/chest/hips), fire mode allowed in double-speed.
sched(85, () => { setPhase('ending'); note('ending: …'); });
```

═══════════════════════════════════════════════
## 4 · WAVE (adult · 28.5s sprint · nova_wave_a)
═══════════════════════════════════════════════
```js
sched(0,  () => note('"Wave time — arms like water."'));
sched(5,  () => { note('"Let it travel: fingers, wrist, elbow."'); lightComet('R'); });
sched(15, () => { note('"Other arm — pass it across."');          lightComet('L'); });
sched(24, () => { note('"Hold the wave — and freeze it."');       lightCue('both'); });
// scoring: ORIGINS DOM logic (dominant-mover, 120-160 pts), smoothness streak; NO mid-run hype at all (adult tier, sprint).
sched(27.5, () => { setPhase('ending'); note(`ending-adult: score=… flowLeft=… flowRight=…. ONE quality note (external focus, e.g. "smoother on the left — lead with the wrist"), then the real score, then goodbye.`); });
```

═══════════════════════════════════════════════
## 5 · UPPER BODY (adult · 38s × 4 rounds slow/slow/fast/fast) — corrected per the movement skill
═══════════════════════════════════════════════
```js
// FRONT/BACK DROPPED (untrackable in 2D). Sides only + isolation-quality bonus.
const TARGETS = [ {t:16.10,dir:'R'},{t:17.37,dir:'L'},{t:23.00,dir:'R'},{t:24.30,dir:'L'},{t:28.07,dir:'R'},{t:29.37,dir:'L'},
  {t:31.90,dir:'R'},{t:32.50,dir:'L'},{t:33.27,dir:'R'},{t:34.33,dir:'L'}, {t:35.20,dir:'FREEZE',hold:1.0} ];
// (the former B/F slots become 'flow' beats: no score, chest orb pulses softly to keep the rhythm — [CLI-FILL] if a better use emerges)
// calibration/EMA/velocity/wobble = UPPERBODY-PERFECT Part 4 as written; windows × TIERS.adult.windowScale; graceMissPerRound 0.
// scoring: slow 15 (+10 iso) / fast 10, streak×2 ≥3 kept but juice='cool' (no fire visuals, HUD shows ×2 text only), round NAILED ≥8 of 10 hits.
function betweenRounds(stats){ setPhase('between'); const weak = stats.R < stats.L ? 'right' : 'left';
  note(`between-adult: strength="${stats.best}" correction="${weak} side — reach the light further next round" then ask "ready?"`); }
```

═══════════════════════════════════════════════
## 6 · GRADERS (extend the machine harness — tier-aware)
═══════════════════════════════════════════════
```js
// test/grade-tier.js — run on every session transcript
export function gradeTier(session, tier){
  const lines = session.novaLines;                                  // [{t, text, phase}]
  const mid = lines.filter(l => l.phase==='game');
  const words = s => s.trim().split(/\s+/).length;
  const NEG = /\b(no|not|wrong|bad|didn'?t|missed|fail|don'?t)\b/i, NEG_HE = /(לא נכון|רע|טעות|פספסת)/;
  const INTERNAL = /\b(shoulder|hip|arm|knee|elbow|head)\b.*\b(lift|move|raise|bend|turn)\b/i;  // body-part instruction = internal focus
  const praise = lines.filter(l => /!/.test(l.text) && !/next|try/i.test(l.text)).length;
  const correct = lines.filter(l => /next|try|lead|reach|chase/i.test(l.text)).length;
  return {
    wordsOk:    mid.every(l => words(l.text) <= TIERS[tier].maxWordsMidGame),
    negZero:    lines.every(l => !NEG.test(l.text) && !NEG_HE.test(l.text)),
    internalZero: lines.every(l => !INTERNAL.test(l.text)),
    ratioOk:    correct===0 ? true : (praise/correct) >= TIERS[tier].praiseRatioMin,
    oneLinePerGap: session.gaps.every(g => g.novaLines <= 1),
    cueDensity: session.cues.every(c => c.perBeat <= 1),
    holdsSilent: session.holds.every(h => h.novaAudioEnergy < 0.01),
    choicesOk:  tier==='kids' ? session.choiceQuestions >= 3 : session.choiceQuestions >= 1,
  };
}
```
Bar: every field true, 3 consecutive sessions per game per language (EN+HE), machine harness from MACHINE-CERTIFY.

═══════════════════════════════════════════════
## 7 · BETA TRACK + GUARDIAN (the code)
═══════════════════════════════════════════════
```bash
# tools/beta-init.sh
git checkout main && git pull && git checkout -b beta || git checkout beta
mkdir -p beta && for g in freeze upperbody upgroove wave hello; do cp $g.html beta/$g.html 2>/dev/null; done
sed -i 's#</body>#<div id="betaChip" style="position:fixed;bottom:8px;left:8px;background:#7c5cbf;color:#fff;padding:2px 8px;border-radius:8px;font:600 11px Nunito;z-index:99">BETA b0.1</div></body>#' beta/*.html
echo "b0.1 — beta track opened; tiers + reaction maps + graders" >> CHANGELOG.md
git add beta/ CHANGELOG.md tools/beta-init.sh && git commit -m "beta: b0.1 track opened" && git tag beta-b0.1 && git push -u origin beta --tags
```
```bash
# tools/rollback.sh <tag>
set -e; TAG=$1; git fetch --tags; git checkout main; git reset --hard "$TAG"; git push --force-with-lease origin main
echo "main rolled back to $TAG — verify: https://dsbeauty01-web.github.io/dance-project/nova-commercial.html"
```
```yaml
# .github/workflows/tracks.yml — law-tracks + law-skills
name: Nova Tracks
on: [pull_request]
jobs:
  tracks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: law-tracks (main only accepts PROMOTE)
        if: github.base_ref == 'main'
        run: |
          echo "${{ github.event.pull_request.title }}" | grep -Eq '^PROMOTE v[0-9]+\.[0-9]+' || { echo "RED: PR to main must be titled 'PROMOTE vX.Y'"; exit 1; }
          git diff --name-only origin/main...HEAD | grep -Eq 'freeze' && { echo "${{ github.event.pull_request.body }}" | grep -q FREEZE-APPROVED || { echo "RED: freeze files need FREEZE-APPROVED"; exit 1; }; } || true
      - name: law-skills (beta game PRs carry SKILL-CHECK)
        if: github.base_ref == 'beta'
        run: git diff --name-only origin/beta...HEAD | grep -Eq '\.html$|\.js$' && { git diff --name-only origin/beta...HEAD | grep -q SKILL-CHECK.md || { echo "RED: game change without SKILL-CHECK.md"; exit 1; }; } || true
```
Branch protection on main: required check "Nova Tracks" + existing "Nova Laws". Verify: open a dummy PR to main titled wrongly → RED; titled `PROMOTE v0.0` → passes tracks (then close it). Paste both runs.

═══════════════════════════════════════════════
## 8 · EXECUTION ORDER (one bounded session each)
═══════════════════════════════════════════════
S1 install skills + CLAUDE.md + beta-init + tracks.yml + rollback test → S2 SKILL-CHECK audit table (both live games) → **HOLD for the founder's fix approval** → S3 Freeze reaction map (b0.2) → S4 Upper Body correction (b0.3) → S5 Up Groove (b0.4) → S6 Wave (b0.5) → S7 Hello (b0.6). Each: graders 3× clean EN+HE → recording to Downloads `beta-bX-video` + 3 beeps 🔔🔔🔔 → founder plays `/beta/<game>` → approved → next. Promotion only on "PROMOTE vX.Y".
