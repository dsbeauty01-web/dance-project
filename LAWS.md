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

### law-consent — parental consent / legal lock-line  ✅ ACTIVE
The product must carry the parental-consent / legal lock-line (EN+HE) before
camera + mic run on a child. **Marker:** `A grown-up should read`, `תנאי שימוש`
· **Files:** nova-commercial.html · **Status:** `active` · **Added:** 2026-07-27
· **Why:** camera + mic on a child with no visible consent line is a compliance
+ trust failure. **Correction (2026-07-28):** the audit first reported this LOST
— that was a **truncated grep**. nova-commercial carries the full EN+HE legal
block (ported from nova-app 2026-07-17): the "a grown-up should read the
policies" line + Privacy/Terms/Parents modals in both languages. Now locked.

### law-ambient — never-black avatar fallback  ⚠ pod-side (deploys next boot)
The SARAY page shows an ambient/idle frame so Nova's panel is never black.
**Marker:** `nova-ambient` (pod-side) · **Files:** _(pod repo nova-avatar —
rt_lk.py)_ · **Status:** `lost` (pod-side) · **Added:** 2026-07-27 · **Why:** a
black avatar panel reads as "broken". **Update (2026-07-28):** the `#v`
letterbox → ambient fix is authored in `rt_lk.py` by the intro-brain session
and deploys at the next pod restart. The nova-commercial frontend is already
zero-black in all states (room-fill insurance + static Nova — verified headless).

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

## POD LAW (2026-07-28) — how live/test pods are launched

A morning was lost to pods: the working pod was reclaimed, replacements were
Community pods stuck on "not enough free GPUs", a launch had no suicide-timer,
and `pkill` during the silent-import window hung the engine at 394 MB. These are
now rules, walled by `law-pods.js` over `tools/pod/launch_pod.sh` + `tools/pod/boot.sh`.

1. **Live/test pods = Secure Cloud only.** Community = bakes only.
2. **Every launch arms the suicide-timer:** `nohup sleep 6h; runpodctl stop pod $RUNPOD_POD_ID &`.
3. **Boot = once, detached, logged.** NO process kills for ≥3 minutes after any
   launch (the silent-import window — a kill here is the engine-hang bug).
4. **A stopped Community pod is presumed unrestartable** — launch fresh, never
   wait on "not enough free GPUs".
5. **Cold-boot truth: full stack = 10-15 min.** Bring pods up 15 min before a human sits down.
6. **Verify before handing out any link:** video attaches **and** one voice-probe line answered.

### POD LAW additions (2026-07-28 — each cost real hours)

7. **tmux boots.** Every pod boot launches **inside tmux** (or another
   sshd-surviving session). Bare `setsid`/`disown`/`&` boots die when RunPod
   tears down sshd on disconnect. **Marker:** `# LAW-PODS-7-TMUX` in the launch
   script (`tmux new-session -d`).
8. **No self-matching pkill.** Any `pkill`/`pgrep` pattern must use the bracket
   trick so it cannot match its own command line — `pkill -f "[b]oot.sh"`, never
   plain `pkill -f boot.sh`. A self-match killed 3 boots today. **Marker:**
   `# LAW-PODS-8-BRACKET`; `law-pods.js` also asserts **no** plain
   `pkill -f boot` / `pkill -f app.py` string exists in the scripts.
9. **Cold-load patience.** The FIRST boot on a fresh container = **up to 25 min**
   (torch/CUDA multi-GB stream off the network volume — silent, no logs, no GPU
   activity). **No process intervention before minute 15.** Repeat boots on the
   same pod are fast (local cache). **Marker (boot.sh):**
   `# LAW-PODS-9-COLDLOAD: silence < 15min = loading, not dead`.
10. **Verify progress, not vibes.** A boot is "progressing" only if `boot.log`
    grows **or** `nvidia-smi` memory climbs — checked **read-only**. Absence of
    output alone is never a death verdict inside the cold-load window.

**Queued (doc-only, no test — next session, NOT today):** `POD-IMAGE.md` — bake a
Docker image with torch + CUDA + MuseTalk deps preinstalled; pods launch from the
image, only weights come from the volume. Cuts cold boot ~20 min → ~5 min.

**Status:** `active` · **Why:** see the morning above — money burned + engine hung.

---

## Out-of-scope files (exempt from the file-law checks)

**`nova-commercial.html` is THE product. All file-law checks target it only.**
These files are deliberately NOT law-checked:

| file | why exempt |
|---|---|
| `nova-joined.html` | **LEGACY** — superseded by nova-commercial.html. Kept fully playable for the founder's voice-only A/B test. Marked `DO NOT EDIT` at top of file. |
| `nova-app.html` | **LEGACY** — same as above; the earlier commercial page, kept playable for A/B. Marked `DO NOT EDIT`. |
| `animal-freeze.html` | Separate standalone game (not the commercial product). Not part of the commercial law-set; give it its own laws later if it needs guarding. |

Editing a legacy file is allowed only to keep it *running* — never to add
features. New work goes in nova-commercial.html.

---

## Machine block — CI reads this. Do not reformat.
Format:  `law-id | status | file1,file2 | marker one ;; marker two`
Only `active` rows are gated. Markers are literal substrings (case-sensitive).

```laws
law-clock      | active | nova-commercial.html                                    | ZONE 1 ;; startPosStream ;; __posLog
law-duck       | active | nova-commercial.html                                    | window.__duck ;; .acquire( ;; .release(
law-autoplay   | active | nova-commercial.html                                    | countdown
law-truth      | active | nova-commercial.html                                    | TRUTH GATE
law-transcript | active | nova-commercial.html                                    | nova-said ;; HEARD ;; tapLogBuffer
law-frames     | active | nova-commercial.html                                    | __sarayFrameMode ;; __sarayFrameMode('full ;; __sarayFrameMode('closeup
law-shoulder   | active | nova-commercial.html                                    | __introChatT0 ;; 35s fallback
law-mp4leads   | active | nova-commercial.html                                    | __mp4Leads ;; MP4_LEADS
law-endings    | active | nova-commercial.html,nova-ending.js                     | nova-ending ;; NEVER a zero
law-mirror     | active | nova-commercial.html                                    | MIRROR_MAP
law-onevoice   | active | nova-commercial.html                                    | Arbiter ;; one-mic
law-soft       | active | nova-commercial.html                                    | Never say wrong
law-storage    | active | nova-commercial.html,nova-session-rec.js                | NovaRec
law-consent    | active | nova-commercial.html                                    | A grown-up should read ;; תנאי שימוש
law-pods       | active | tools/pod/launch_pod.sh,tools/pod/boot.sh               | "cloudType": "SECURE" ;; runpodctl stop pod ;; nohup sleep 6h ;; git -C /workspace/repo pull ;; NO-PKILL-WINDOW ;; LAW-PODS-7-TMUX ;; LAW-PODS-8-BRACKET ;; LAW-PODS-9-COLDLOAD
law-ambient    | lost   | -                                                       | nova-ambient
law-v2v        | policy | -                                                       | -
law-treaty     | policy | -                                                       | -
```
