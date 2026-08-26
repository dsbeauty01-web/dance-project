# NOVA-LEAK-REPORT — Maya vs Nova contamination audit

**Date:** 2026-08-26 · **Repo:** `C:\Users\dsbea\repos\dance-project` · **Branch:** `freeze-structural-fix`
**Spec:** `C:\Users\dsbea\Downloads\maya-not-nova-fix.md`
**Method:** read-only. `grep -rin "nova"` across the whole repo (11,869 hits / 194 files), then
classified only the operationally-meaningful hits. The bulk of hits are the **Nova kids' dance
app itself** (`nova-*.html`, `v*.html`, `index.html`, `shuky.html`, `pod/rt_lk.py`,
`pod/pages/*`) — that is Nova's own product living in the shared fork repo and is **LEGIT**, not
contamination. This report focuses on the Maya-operational surface: `pod/`, `tools/pod/`, `n8n/`,
`maya-server/`, `maya-ops/`, runbooks.

---

## 1. What this (fork/deploy) session did wrong

Maya was forked from Nova, and the **deploy + bake pipeline was never forked with it.** The repo
ships Maya's own brain file, persona, contract, switchboard, catalog, n8n flows and stage runbook —
all genuinely Maya — but the scripts that actually *bring a pod up and bake avatars* are still
**Nova's**:

- `tools/pod/boot.sh` copies and launches **`rt_lk.py` (Nova's brain, Nova's kids-dance persona)**
  and starts the engine on **`--avatar_id nova_idle`**. It never touches `maya_rt.py` or `maya_idle`.
- `tools/pod/launch_pod.sh` creates a pod literally named **`nova-live-fresh`**.
- `tools/pod/bake_all.sh` bakes **only `nova_*` avatars** from Nova source clips.
- The Maya-correct scripts that `STATUS.md` / `STREAM-RUNBOOK.md` call for — **`maya-boot.sh`,
  `maya-watchdog.sh`** — are **NOT in this repo** (they live only on the pod volume, unversioned).

Net effect: any "Maya" bake or bring-up done through the repo's committed scripts produces **Nova
content wearing a Maya task label** — which is exactly how `data/avatars/maya_rapa` ended up being
the Nova cartoon dance kid. The `maya_rt.py` brain also still *defaults* its room to `nova-live`
and reads the `NOVA_VOICE` env var, so the leak is baked into the forked brain too.

**Nothing was committed, no pod was started, no file other than this report was modified.**

---

## 2. Contamination table

| # | file:line | offending value | should-be (Maya) | severity |
|---|-----------|-----------------|------------------|----------|
| 1 | `pod/maya_rt.py:17` | `LK_ROOM = os.environ.get("LK_ROOM", "nova-live")` | default `"maya-live"`, ideally **hardcoded** (ROOM LAW) | HIGH |
| 2 | `pod/maya_rt.py:20` | `VOICE = os.environ.get("NOVA_VOICE", "marin")` | read `MAYA_VOICE`; never source a `NOVA_*` var (env firewall). `marin` is Nova's kid-sister voice — founder must pick Maya's | MED |
| 3 | `tools/pod/boot.sh:28` | `cp .../pod/rt_lk.py /workspace/rt_lk.py` | copy `pod/maya_rt.py` | HIGH |
| 4 | `tools/pod/boot.sh:51` | `app.py ... --avatar_id nova_idle` | `--avatar_id maya_idle` | HIGH |
| 5 | `tools/pod/boot.sh:61` | `python -u rt_lk.py` (boots Nova's brain) | boot `maya_rt.py` | HIGH |
| 6 | `tools/pod/launch_pod.sh:33` | pod name `"nova-live-fresh"` | `"maya-live-*"` | MED |
| 7 | `tools/pod/launch_pod.sh:12-15` | env names `NOVA_VOLUME_ID / NOVA_DC / NOVA_GPU / NOVA_IMAGE` | `MAYA_*` (values/volume `1ditrne6cb` are shared → OK, prefixes are the leak) | LOW |
| 8 | `tools/pod/bake_all.sh:18-24` | JOBS bake `nova_wave_a, nova_hello_a/b, nova_prewave_a/b/c` from `nova-hello.mp4` / `handywave-full.mp4` | Maya bake must produce `maya_*` from `maya-ops/bake/src/*` (serum sources) | HIGH (for a Maya bake task) |
| 9 | `pod/maya_rt.py:959,1008,1011,1012` | visible page `<title>Nova</title>`, "Nova", "tap/type to Nova" on Maya's stage page | "Maya" labels | MED (cosmetic but on-air) |
| 10 | `pod/maya_rt.py:1036` | LiveKit identity gate `p.identity!=='nova-avatar'` | confirm whether Maya's engine publishes as `nova-avatar` (shared) or should be `maya-avatar` — functional, needs a human check | OPEN |

Borderline / **not** contamination (left as LEGIT, see §4): the wire-protocol message names
`nova-say / nova-cue / nova-fact / nova-pick` and ws types `nova_text / nova_done`, plus CSS ids
`nova-frame / nova-ambient`. `pod/MAYA-CONTRACT.md` defines the relay as "same shape as Nova's
relay", and the Maya stage page maps onto exactly these names, so renaming them would break the
contract. They are shared-engine protocol, harmless — but noted.

---

## 3. Answers to the required questions

### 4a. Does a genuine MAYA visual identity exist? — **NO.**
- Maya-specific visual assets in the repo are only: `maya/maya-bg.jpg` (a background), and
  `maya-ops/bake/src/{serum_close_src,serum_present_src,cutaway_apply,cutaway_examine}.mp4` plus
  `maya-ops/bake/rejected/REJECTED_male-hand-bottle.mp4` — these are **product B-roll of the serum
  bottle/hands, not a host face.**
- There is **no** Maya face image, no Maya portrait, no source video of a woman host, **no
  `verified-avatars.json`** (that registry lives on the pod volume, not in-repo), and no bake
  manifest that produces a `maya_*` **face**.
- A `nova-face.png` (the Nova kid) **is** present at repo root.
- Combined with the already-established finding that `data/avatars/maya_rapa` renders as the Nova
  cartoon dance kid: **every "maya_" avatar is either Nova-kid content under a Maya name
  (`maya_rapa`) or an unbuilt reference (`maya_idle`, cited in STATUS/RUNBOOK but with no in-repo
  source or bake).** No real Maya visual identity has been created.

### 4b. LK_ROOM / room name
- Maya-correct room is **`maya-live`** (`STATUS.md:22` — "publishing 1080×1920 into room
  `maya-live`").
- But `pod/maya_rt.py:17` **defaults to `nova-live`** when `LK_ROOM` is unset, and the repo's
  `boot.sh` **does not set `LK_ROOM`** (it only sources `/workspace/.env`). So the room is **not**
  hardcoded/asserted as the spec's ROOM LAW requires — if `.env` omits it, Maya subscribes to
  `nova-live`. This must become a hardcoded/asserted `maya-live`.

### 4c. Avatar registry
- `verified-avatars.json` is **not in the repo** (on the volume only).
- Intended Maya avatar: **`maya_idle`** (`pod/maya_rt.py:1128`, `STATUS.md:21`, `STREAM-RUNBOOK.md:14`).
- Nova-named avatars used by the active pipeline where Maya ones belong: `nova_idle` (boot.sh:51),
  and the bake set `nova_wave_a / nova_hello_a / nova_hello_b / nova_prewave_a/b/c` (bake_all.sh),
  plus `nova_idle nova_idle2 nova_walk nova_sub nova_active nova_groove nova_hype` (BAKE-DEPLOY.md).
- **Flagged:** `maya_rapa` = a `maya_`-named entry whose content is the Nova dance kid (established).
  The engine bring-up loads `nova_idle` rather than `maya_idle`; `STREAM-RUNBOOK.md:103` even lists
  "wrong face — a `nova_*` bake loaded" as a known mid-stream failure.

### 4d. Persona / brain
- **The persona FILE is correct.** Maya's brain `pod/maya_rt.py` loads its **own inline Maya
  persona** — `PROMPT` (lines 45-76) + `CORE_LAWS` (lines 81-101): a Hebrew/English live-shopping
  host, TRUTH/DISCLOSURE/NO-EYES laws, serum context. Not Nova's.
- **But the boot WIRING is wrong.** The repo's `tools/pod/boot.sh` boots **`rt_lk.py`**, whose
  persona is `"You are Nova — a magical AI dance teacher"` (`pod/rt_lk.py:27,46,97`). So a Maya
  bring-up via the committed boot script loads **Nova's persona**, not `maya_rt.py`'s. The Maya
  persona is only reached if the (missing-from-repo) `maya-boot.sh` is used.

### 4e. n8n workflows — **CLEAN, all Maya.**
- `W1-youtube-chat-ingest.json`, `W2-priority-queue.json`, `W3-lead-capture.json`,
  `W5-catalog-sync.json`: webhooks are `maya-chat` (W2) and `maya-lead` (W3); `CONFIG.maya_api`
  points at maya-server; W1 posts to `.../webhook/maya-chat`. **No `nova` webhook, sheet, or
  credential anywhere in `n8n/`.** (No W4 file is present; W1/W2/W3/W5 exist.)

### 4f. Pod template / volume
- The pod bring-up template is **Nova's**: `launch_pod.sh` names the pod `nova-live-fresh` and uses
  `NOVA_*` env-var names.
- **Volume `1ditrne6cb` is legitimately shared** — `STATUS.md:179` and `BAKE-DEPLOY.md:11` both
  place Maya on the same `1ditrne6cb` / EU-RO-1 volume, so the path itself is not contamination.
- The real gap: **no Maya pod template / boot script is committed**; the Nova template stands in.

---

## 4. Must re-run with Maya sources (redo list)

1. **Fork the deploy pipeline.** Add committed `maya-boot.sh` (boots `maya_rt.py`, engine on
   `--avatar_id maya_idle`, sets `LK_ROOM=maya-live`) and `maya-watchdog.sh`, referenced by
   STATUS/RUNBOOK but absent. Do **not** reuse `tools/pod/boot.sh` for Maya.
2. **Fix `maya_rt.py:17`** → hardcode/assert `maya-live` (ROOM LAW). **Fix line 20** → `MAYA_VOICE`.
3. **Re-bake Maya avatars from Maya sources.** Replace the `nova_*` JOBS in a Maya bake script with
   `maya_*` built from `maya-ops/bake/src/*` — and, critically, obtain a **real Maya host face
   source** first (none exists yet). Re-bake `maya_rapa` (currently Nova kid) and `maya_idle` from
   genuine Maya identity, then re-register in `verified-avatars.json`.
4. **Fix on-air labels** in `maya_rt.py` page (`<title>`, "Nova" text) → "Maya".
5. **Add the identity preflight + env firewall** (spec STEP 2) to whatever the Maya bring-up script
   becomes, so `nova` values hard-fail.

---

## 5. Open questions a human must decide

1. **There is no Maya face at all.** Who/what is Maya's visual identity? A real host source video
   or a licensed avatar must be provided before any honest `maya_*` bake — otherwise `maya_rapa` /
   `maya_idle` stay Nova-kid content. This is the blocker.
2. **`nova-avatar` LiveKit identity** (`maya_rt.py:1036`, `pod/rt_lk.py`): is the publisher identity
   a shared-engine constant (leave it) or should Maya publish as `maya-avatar`? Needs the engine's
   publish-side confirmed.
3. **Voice:** `marin` was a founder decision for *Nova*. Is it also Maya's voice, or does the adult
   sales host need a different one? (`MAYA_VOICE`.)
4. Should the **Nova bake/boot scripts** (`tools/pod/boot.sh`, `launch_pod.sh`, `bake_all.sh`,
   `pod/BAKE-DEPLOY.md`) be moved out of this Maya repo entirely, or kept for the co-resident Nova
   project? `STATUS.md:167` confirms another CLI session actively works on Nova in this same repo.
5. The **verified-avatars registry lives only on the volume** (`1ditrne6cb`), unversioned — a human
   must inspect it on the pod to see every avatar name actually registered and whether any Nova bake
   sits under a `maya_` key.

---

**Report location note:** `maya-ops/` exists, so this was written to
`maya-ops/NOVA-LEAK-REPORT.md` as specified.

**The one thing a human should still eyeball:** open the pod volume `1ditrne6cb` and look at
`data/avatars/maya_rapa` (and `maya_idle`) with your own eyes — confirm they are the Nova dance kid,
because the fix is worthless until a real Maya face replaces them, and that asset does not exist yet.
