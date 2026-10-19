# BETA-TRACK — versioned, guardian-safe deploy (skills → audit → fix on BETA → founder approves → promote to commercial)

## THE RULE
**Nothing touches the commercial game until the founder approves the BETA.** Two tracks, always:
- `main` = the commercial game (certified Freeze, live for testers). FROZEN by CI.
- `beta` = where all new work lands, served at its own URL (`/beta/...`). Versioned. Founder plays beta; on "PROMOTE vX" → beta merges to main under a tag.
Rollback = one command, always available. Every version has a tag and a changelog line.

═══════════════════════════════════════════
## STEP 1 — INSTALL THE SKILLS (repo, so every CLI loads them)
═══════════════════════════════════════════
1. Unzip `nova-skills.zip` → `.claude/skills/movement-tracking/`, `.claude/skills/game-cues-lights/`, `.claude/skills/performance-feedback-ai/` in `dance-project` (same location pattern as the existing lexi/companion skills — match it).
2. Add to CLAUDE.md (create if absent, lean): the laws list (INPUT-LOCK, phase machine, body map, truth-gate, FREEZE-APPROVED, no invented values → cite ORIGINS), "read the three skills before touching any game," and "all game work lands on `beta`, never `main`."
3. Commit: `chore(skills): install movement-tracking, game-cues-lights, performance-feedback-ai + CLAUDE.md` (named files only).

═══════════════════════════════════════════
## STEP 2 — THE BETA TRACK + GUARDIAN
═══════════════════════════════════════════
1. Branch `beta` from `main`. Beta pages are copies under `/beta/` (e.g. `beta/freeze.html`, `beta/upperbody.html`) that read the same pod-registry/auto-detect. The pod serves them at `/beta/freeze`, `/beta/upperbody` — same stack, separate pages.
2. Version stamp: `BETA_VERSION = 'b0.1'` shown as a tiny corner chip on beta pages only (never on main).
3. **Guardian rules (extend tools/laws/ + CI):**
   - `law-tracks`: any PR to `main` that changes a game file MUST carry `PROMOTE vX.Y` in its title and reference a beta tag → otherwise RED.
   - Existing FREEZE lock stays (FREEZE-APPROVED) on main.
   - `law-skills`: a game PR to beta must include a `SKILL-CHECK.md` diff (Step 3's audit table) → otherwise RED.
   - Rollback script `tools/rollback.sh <tag>` → checks out main to the tag, redeploys, prints the live URL. Test it once on a dummy tag; paste the output.
4. CHANGELOG.md at root: one line per beta version + promotions.

═══════════════════════════════════════════
## STEP 3 — THE AUDIT (skills vs the two games) → the founder's fix list
═══════════════════════════════════════════
For Freeze and Upper Body, produce `SKILL-CHECK.md`: a table, one row per skill law (all 3 skills), columns: LAW · FREEZE status ✓/✗/partial (evidence: file+line) · UPPER BODY status · proposed fix (one line). No code yet. Known expected findings to verify, not assume: Upper Body scores front/back (violates movement-tracking L1) · Freeze has no light language mid-game (game-cues L-juice) · both prompts lack the feedback-law block (performance-feedback) · praise ratio unmeasured.
**HOLD** → paste the table → the founder approves the fix list.

═══════════════════════════════════════════
## STEP 4 — FIX ON BETA (after approval) → b0.2, b0.3…
═══════════════════════════════════════════
Each approved fix = one bounded session on `beta`, one version bump, CHANGELOG line, tag `beta-b0.x`. Per version: self-test via the machine harness (MACHINE-CERTIFY graders G1-G6 + the new skill graders: praise-ratio ≥3:1, zero internal-focus cue words, zero negatives, cue density ≤1/beat) → recording to Downloads `beta-b0.x-video` + 3 beeps 🔔🔔🔔 → founder plays `/beta/...` → "approved" or notes.

═══════════════════════════════════════════
## STEP 5 — PROMOTE (the only way to main)
═══════════════════════════════════════════
Founder says **"PROMOTE vX.Y"** → PR `PROMOTE vX.Y` beta→main (FREEZE-APPROVED if freeze files change) → CI green → merge → tag `vX.Y` → CHANGELOG → verify the commercial URL live → paste link. Rollback path re-tested after every promote (`tools/rollback.sh v(X.Y-1)` dry-run).

## LAWS
Skills read before any game code · beta only, never main · cite ORIGINS/skills for every value · one version per session · founder's word gates every promote · pods self-stop · evidence per step. Ambiguity = QUESTION.
