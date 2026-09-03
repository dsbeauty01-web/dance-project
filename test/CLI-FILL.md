# MACHINE-CERTIFY — [CLI-FILL] decision log

Every gap in the spec filled by the CLI, with reason. Grader changes are listed here per
PART 4 ("Never weaken a grader; a grader change = [CLI-FILL] logged with reason").

1. **Phrase-bank filenames (HE)** — spec names `shalom_ani_shuki.wav`/`ken.wav`/… ; the
   committed bank uses `he_hi_im_shuki_24k.wav`/`he_yes_24k.wav`/… with the same content
   (שוקי introduces himself, כן, אני מוכן, פיצה question, אוקיי, ביי). `sababa`/`yalla`
   are covered by the Hebrew yes-word whitelist; not needed as audio for the script.
2. **Phrase format** — spec says "16k mono wavs"; the harness feeds the realtime session
   at its native 24k pcm16 (same path the mic uses), so the bank is 24k pcm16 mono —
   *higher* fidelity than spec'd, zero resampling in the loop.
3. **G3 "≤1 line per gap" vs required warnings** — the spec ALSO requires a live warning
   2–4s before every non-stab freeze, so a gap legally holds verdict(≤1) + warning(≤1).
   Grader enforces ≤2 with both features present; a 3rd line fails. Not a weakening:
   both spec'd features are enforced, chatter is not.
4. **G3 fakeout window** — "NO warning before the fakeout" measured over the actual
   melt→stab gap (~1.2s). The naive [stab−4.5s] window overlaps the previous round's
   hold and its own legitimate warning tail, which would flag spec-correct behavior.
5. **G6 transition tolerance** — the page sets the body BEFORE flipping the phase on
   purpose (idle2 must be live before the engine voice path opens, so lips can never
   animate the groove body). [BODY] lines within 2.5s before their matching [PHASE]
   flip are the switch itself; pose clips may lead their hold by ≤1.5s (neutral-crossing
   swap). Violations outside those windows still fail.
6. **G1 name matching** — anchored on the reply to the first kid utterance, not on the
   transcript containing "shuki": en-1 transcribed the SAPI kid voice as "Chucky" while
   Nova still echoed "Shuki" — hearing quality is graded by the echo, not by Whisper's
   spelling of a synthetic voice.
7. **G2 strengthened (not spec'd)** — added mid-game bans: questions, self-DJ lines
   (offering rounds/animals/choices), countdowns. Session en-1 showed these are the
   founder's core complaint; strengthening is always allowed.
8. **G5 silence re-invite budget** — the greet, one silence re-invite and the ready-ask
   all land before the kid's first word; grader allows ≤3 intro lines pre-name, exactly
   one of which may be the silence re-invite.
9. **G4 intro ≤40s** — measured greet→music minus the scripted 25s G5 silence window
   (test-added, not intro fat).
10. **Browser** — sessions run in headless Edge (same Chromium/CDP): node-spawned Chrome
    dies with exit 21 on this machine and headed windows would land on the founder's
    screen. Delivery videos still record the real page pixels via CDP screencast.
11. **G2 'here it comes'** — removed from the self-DJ ban: "Keep on dancing, here it
    comes!" (en-3) is a spec-perfect freeze tease; self-DJ music announcements are still
    caught by 'ready for the music'.
12. **G3 single-sample leaks** — the analyser's ~43ms ring still holds pre-cut audio at
    the hold flip, so one loud sample at the boundary is an artifact; a leak = ≥2
    consecutive loud samples (a real line is 500ms+).
13. **G5 noise outcomes** — noise that never transcribes (zero mid-game [KID-SAID]) is a
    PASS equal to an [INPUT-LOCK] drop; only a noise-triggered RESPONSE fails.
14. **NAME variant "shaky"** — Whisper spelling of the SAPI kid voice saying Shuki (en-17 goodbye graded on echo, same class as shooki/shuky per #6).
