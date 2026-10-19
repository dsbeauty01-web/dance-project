---
name: lexi-ux-patterns
description: Use this skill when designing screens, layouts, or UX flows for Nova Dance or any kids' AI-companion app with a talking avatar. Triggers when the user asks about layout, screen design, avatar sizing, lesson structure, parent flows, conversation UI, or references Lexi/Loora/similar competitor apps. Captures the proven patterns from Lexi (lexiteach.com) — adaptive avatar sizing, dual-mode layouts (lesson vs conversation), parent-facing course dashboard, state badges, and emotional closeups — so Nova can selectively borrow what works without copying the whole product.
---

# Lexi UX Patterns — What to Steal, What to Skip

## The core insight

**Lexi is a talking-head conversation app with slides. Nova is body + movement + music + voice.** Different products. But Lexi has solved several UX problems that Nova will hit, and copying the *solutions* (not the product) saves time.

The single most important pattern Lexi uses: **the avatar changes size based on what matters most in this moment.** Static layouts feel dead. Adaptive layouts feel alive.

---

## Pattern 1: Adaptive avatar sizing (the big one)

Lexi runs three layout modes and switches between them inside a single lesson:

| Mode | When | Layout |
|---|---|---|
| **Lesson mode** | Showing content, story, slides | Avatar SMALL in corner tile, content fills canvas |
| **Conversation mode** | Real back-and-forth talking | Avatar + kid both medium, side-by-side |
| **Closeup mode** | Emotional / praise / introduction moments | Only avatar + kid, both BIG, nothing else on screen |

**Apply to Nova:**

| Phase | Mode | Why |
|---|---|---|
| Arrival / "Hi I'm Nova!" | Closeup | First impression — Nova must feel present |
| Recognition / "I see you!" | Closeup | Magic moment — kid sees Nova react to them |
| Countdown / "Ready?" | Conversation | Building anticipation, both visible |
| Game / dancing to song | Lesson mode (Nova small) | Kid's body is the content — Nova shrinks to corner bubble |
| Reaction mid-game ("Ooh nearly!") | Pop closeup overlay | Brief takeover, then back to corner |
| End / "You did it!" | Closeup | Emotional payoff |

The pop-up "Ooh nearly!" bubble already in v29 is the right instinct. Take it further: during dancing, Nova is small in the corner (with state badge); when she has something specific to say, she briefly grows.

---

## Pattern 2: State badges on the avatar

Lexi shows a tiny label inside the avatar tile that updates in real time:
- **"Listening"** — black pill, bottom-left of avatar tile, shown while STT is active
- **"Talking"** — green pulse + "Talking" text, shown while TTS is playing

**Why it works:** kids (and parents) need to know whose turn it is. Without the badge, awkward silences feel like the app is broken. With it, silence feels intentional ("she's listening to me").

**Apply to Nova:** add four states:
- `Watching` — pose detection running, no specific event
- `Listening` — mic active
- `Talking` — TTS playing
- `Thinking` — LLM call in flight (rare, but covers latency >500ms)

Render as a small pill at the bottom of Nova's tile. Same visual language whether Nova is corner-sized or full-screen.

---

## Pattern 3: Dual-audience structure (parent vs kid)

Lexi separates two surfaces hard:

- **Parent surface** = course dashboard. Multi-unit curriculum, locked progression, lesson thumbnails, descriptions, CEFR badges, "Earn!" rewards. Boring-looking, list-heavy, info-dense. Parents pick the class, then hand the device to the kid.
- **Kid surface** = the lesson player itself. Cloud backgrounds, big colorful titles, avatars, no menus. Kid never sees the dashboard.

**Apply to Nova:** when Nova grows past v29, build:
- **Parent home** — list of songs/dances/activities, age range, what the kid will learn (movement skills, words, etc.), preview thumbnail. Parent-readable.
- **Kid player** — what v29 already is. Full-screen, no chrome, just the experience.

Don't mix them. The dashboard is not for kids and shouldn't try to be.

---

## Pattern 4: Skip / Pause / X always available

Lexi keeps three controls visible at top of every lesson screen:
- **Skip Slide** (with count remaining)
- **Pause Lesson**
- **X** (exit)

Plus settings gear and help (?). Kids get bored, parents need to interrupt for dinner, devices get grabbed by siblings. Always-on escape hatches matter.

**Apply to Nova:** at minimum, Pause and Exit always reachable during the song phase. Probably also a "Skip to next song" once Nova has multiple songs.

---

## Pattern 5: Star tracker visible during activity

Lexi shows a 2x7 grid of stars on the right side during conversation drills. Stars fill in as the kid completes prompts. Visible but not center-stage.

**Apply to Nova carefully.** Stars work for Lexi because the activity is *transactional* (answer prompts → get stars). Nova's activity is *expressive* (dance to a song). Counting individual moves with stars could make it feel like a test.

Better Nova version: a single "energy meter" or "Nova-ometer" that fills as the kid moves, not per-move. Or skip gamification entirely for v1 and see if kids care. **Don't add stars just because Lexi has them.**

---

## Pattern 6: Speech-to-text echoed back as a chat bubble

In Lexi's conversation mode, what the kid says is transcribed and shown as a chat bubble next to a "You" avatar. The kid sees their words validated visually.

**Apply to Nova:** when Nova asks a question ("What's your name?" "What song do you want?"), echo back what the STT heard. This catches misrecognitions early ("Nova heard 'Bob' — say it again?") and makes the kid feel heard.

Don't do this during dancing — would clutter the screen. Only during conversation phases.

---

## Pattern 7: Translation hints (ignore for Nova)

Lexi shows a yellow `EN-US` tag with the source phrase under each title — because Lexi is a *language tutor for non-English-speaking kids*. Nova is not a language app, so skip this entirely. Listed here only so we don't accidentally copy it.

---

## What NOT to copy from Lexi

- **The whole curriculum/unit/lesson/CEFR-badge structure.** That's a language-school metaphor. Nova is play, not school. Songs, not lessons. Activities, not units.
- **The chat-bubble conversation as the main UX.** Lexi is a conversation app. Nova's main UX is movement to music. Conversation is a *phase* in Nova, not the whole product.
- **The "Skip Slide (3)" framing.** Nova doesn't have slides. It has phases (arrival → game → end) and songs. Use song-native language.
- **Heavy gamification (stars per response).** See Pattern 5 — risk of making expressive movement feel like a quiz.
- **The polished marketing-y aesthetic of the dashboard.** That's a B2C signup funnel. Nova's first parent surface can be much simpler.

---

## The competitive reframe

After studying Lexi, Nova's pitch sharpens:

> "Lexi is the AI English tutor that talks to your kid. Nova is the AI play companion that *moves with* your kid."

Lexi proved the talking-avatar-for-kids market is real and parents will pay for it. Nova's moat — body tracking, music, real-time pose reactions — is something Lexi structurally can't add without becoming a different product. Good news.

---

## Checklist when designing a new Nova screen

1. Which mode is this — lesson, conversation, or closeup? Pick one.
2. What state badge should Nova show right now?
3. Is there a Pause / Exit reachable?
4. Is the parent or the kid looking at this screen? Don't mix.
5. Am I about to copy a Lexi pattern that's actually language-school metaphor in disguise (units, CEFR, stars-per-response)? Stop.
6. Does the avatar size match what matters most in this moment, or is it static?
