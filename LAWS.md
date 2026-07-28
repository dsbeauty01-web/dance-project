# LAWS.md — Nova's append-only law registry

> **This file is APPEND-ONLY.** You may add a law, or change a law's `status`
> when the founder decides. You may **never delete a law or its test.** If your
> change makes a law-test go red, you *restore the law* — you do not remove the
> test. Removing a marker without a written founder decision is a **treaty
> violation** (see `law-treaty`).
>
> Every law below has a **marker** — a literal string that must exist in the
> code. CI (`.github/workflows/laws.yml`) runs `tools/laws/run-all.sh`, which
> runs one `law-*.js` per law **and** greps every ACTIVE marker in the machine
> block at the bottom of this file against the codebase. **Any missing ACTIVE
> marker fails the build with the law's name.** That is the wall: a registered
> fix cannot silently disappear.

## Status meaning

| status | meaning | build effect if marker missing |
|---|---|---|
| `active` | law is live and guarded | ❌ **RED** — regression, push rejected |
| `lost`   | law was already lost before the Guardian (red-list) | reported loudly, **not** blocking — until founder restores + flips to `active` |
| `policy` | human discipline, no code marker | never gated (documented here so it is not forgotten) |

New laws start `active` the moment their marker exists in the code. A `lost`
law becomes `active` the instant the founder restores it and edits this file.

---

## The laws

### law-clock — one clock
Game cues are driven by the media's own `currentTime` (the video/song **is** the
clock), streamed to the worker — not by free-running `setTimeout` chains that
drift. **Marker:** `ZONE 1`, `startPosStream`, `__posLog` · **Files:**
nova-commercial.html · **Added:** 2026-07-27 · **Why:** timers drift against the
music; the media clock does not.

### law-duck — one refcounted duck engine
Music ducking under Nova's voice goes through a single refcounted engine
(`acquire`/`release`), never a naked boolean that races. **Marker:**
`window.__duck`, `.acquire(`, `.release(` · **Files:** nova-commercial.html ·
**Added:** 2026-07-27 · **Why:** a boolean duck un-ducks while another source
still needs the music quiet.

### law-autoplay — no autoplay on game media
The dance/song media is started **and resumed** by the countdown gate, never the
raw `autoplay` attribute (live camera/avatar streams may autoplay; game media
may not). **Marker:** `countdown` · **Files:** nova-commercial.html,
animal-freeze.html · **Added:** 2026-07-27 · **Why:** autoplay fires before the
kid, permission and the clock are ready.

### law-truth — no fake "you did it"
A truth gate only lets a success line through when the move fact is real; the
brain honours the same gate. **Marker:** `TRUTH GATE` (frontend) · **Files:**
nova-commercial.html (+ novapython/agent.py, brain-side, guarded locally) ·
**Added:** 2026-07-27 · **Why:** cheering a move that did not happen breaks the
kid's trust. **Note:** the spec's original marker `truthSnapshot` has drifted;
the live gate is `TRUTH GATE`.

### law-transcript — both sides recorded
Every session records what the kid said (`HEARD`) and what Nova said
(`nova-said`) for review + auto-analysis. **Marker:** `nova-said`, `HEARD`,
`tapLogBuffer` · **Files:** nova-commercial.html · **Added:** 2026-07-27 ·
**Why:** without both sides, sessions cannot be reviewed. **Note:** the pod-side
emitter (`rt_lk.py`) is not yet in git — Part 1 brings it in.

### law-frames — frame-mode bridge
The app tells the SARAY avatar page how to frame Nova: `closeup` (waist-up, no
black margins) for intro/end, `full` (full body) for the play corner.
**Marker:** `__sarayFrameMode`, `__sarayFrameMode('full`, `__sarayFrameMode('closeup`
· **Files:** nova-commercial.html · **Added:** 2026-07-27 · **Why:** wrong
framing = black margins or a cropped kid. See also `law-ambient` (pod-side).

### law-shoulder — intro chit-chat gate
On intro, Nova chit-chats first and does not fire the shoulder challenge for 25s;
a 35s fallback fires it if the natural moment never comes. **Marker:**
`__introChatT0`, `35s fallback` · **Files:** nova-commercial.html · **Added:**
2026-07-27 · **Why:** firing too early skips the warm-up; never firing strands
the intro.

### law-mp4leads — Wave MP4 leads
The `__mp4Leads` gate decides whether the live pitch-plan or the baked MP4 owns
the Wave clock, and suppresses live clips when the MP4 leads. **Marker:**
`__mp4Leads`, `MP4_LEADS` · **Files:** nova-commercial.html · **Added:**
2026-07-27 · **Why:** otherwise pitch and MP4 both drive the game and collide.

### law-endings — no bare zero
Every game ends through `nova-ending.js`, which never renders a bare zero /
"0 pts" / empty star row. **Marker:** `nova-ending`, `NEVER a zero` · **Files:**
nova-commercial.html, animal-freeze.html, nova-ending.js · **Added:** 2026-07-27
· **Why:** a child must always leave on celebration.

### law-consent — parental consent / legal lock-line  ⚠ LOST
Both live game files must carry the parental-consent / legal lock-line (EN+HE)
before camera + mic run on a child. **Marker:** `consent` · **Files:**
nova-commercial.html, animal-freeze.html · **Status:** `lost` · **Added:**
2026-07-27 · **Why:** camera + mic on a child with no visible consent line is a
compliance + trust failure. **Red-list:** absent from BOTH live game files as of
the audit; once lived in nova-app.html, never propagated. See GUARDIAN-REPORT.md.

### law-ambient — never-black avatar fallback  ⚠ LOST (pod-side)
The SARAY page shows an ambient/idle frame so Nova's panel is never black, even
if the pod-side patch lags. **Marker:** `nova-ambient` · **Files:** _(pod repo
nova-avatar — not yet in git)_ · **Status:** `lost` · **Added:** 2026-07-27 ·
**Why:** a black avatar panel reads as "broken". Guarded once Part 1 lands the
pod files in nova-avatar `pod-live`.

---

## Standing project laws (pre-Guardian, now registered)

### law-mirror — mirror map
On-screen arrows are mirrored to the kid's own left/right (`MIRROR_MAP`).
**Marker:** `MIRROR_MAP` · **Files:** nova-commercial.html · **Why:** un-mirrored
arrows send the kid the wrong way.

### law-onevoice — one mouth / one-mic
A single speech arbiter owns Nova's mouth; one microphone at a time. **Marker:**
`Arbiter`, `one-mic` · **Files:** nova-commercial.html · **Why:** two speech
sources = double-voice / self-talk.

### law-soft — never say wrong
Nova never says wrong/no/miss/fail — every attempt is met with warmth.
**Marker:** `Never say wrong` · **Files:** nova-commercial.html · **Why:** the
product's whole promise is a child never feeling they failed.

### law-storage — sessions persist
Sessions are captured via `NovaRec` for recording + analysis. **Marker:**
`NovaRec` · **Files:** nova-commercial.html, nova-session-rec.js · **Why:**
un-recorded sessions cannot be reviewed or improved.

### law-v2v — the sacred pipe  (policy)
NEVER interfere with the voice-to-voice pipe — no interruption guards, ear
shields, or VAD ctor changes. **Status:** `policy` · **Why:** every attempt has
broken her (deaf/silent/dead). Change only behind a spoken-WAV probe.

### law-treaty — one CLI, named commits  (policy)
One session edits a given flagship file at a time. `git add` named files only —
never `-A`/`.`. `git status` before every commit. An unauthored change = STOP +
ask. **Status:** `policy` · **Why:** broad `git add` from parallel sessions has
swept siblings' uncommitted work into the wrong commit.

---

## Machine block — CI reads this. Do not reformat.
Format:  `law-id | status | file1,file2 | marker one ;; marker two`
Only `active` rows are gated. Markers are literal substrings (case-sensitive).

```laws
law-clock      | active | nova-commercial.html                                    | ZONE 1 ;; startPosStream ;; __posLog
law-duck       | active | nova-commercial.html                                    | window.__duck ;; .acquire( ;; .release(
law-autoplay   | active | nova-commercial.html,animal-freeze.html                 | countdown
law-truth      | active | nova-commercial.html                                    | TRUTH GATE
law-transcript | active | nova-commercial.html                                    | nova-said ;; HEARD ;; tapLogBuffer
law-frames     | active | nova-commercial.html                                    | __sarayFrameMode ;; __sarayFrameMode('full ;; __sarayFrameMode('closeup
law-shoulder   | active | nova-commercial.html                                    | __introChatT0 ;; 35s fallback
law-mp4leads   | active | nova-commercial.html                                    | __mp4Leads ;; MP4_LEADS
law-endings    | active | nova-commercial.html,animal-freeze.html,nova-ending.js  | nova-ending ;; NEVER a zero
law-mirror     | active | nova-commercial.html                                    | MIRROR_MAP
law-onevoice   | active | nova-commercial.html                                    | Arbiter ;; one-mic
law-soft       | active | nova-commercial.html                                    | Never say wrong
law-storage    | active | nova-commercial.html,nova-session-rec.js                | NovaRec
law-consent    | lost   | nova-commercial.html,animal-freeze.html                 | consent
law-ambient    | lost   | -                                                       | nova-ambient
law-v2v        | policy | -                                                       | -
law-treaty     | policy | -                                                       | -
```
