# GUARDIAN-REPORT.md — fixes are walls now (2026-07-27)

The Nova Guardian turns hard-won fixes from *requests* (which ~40 CLI sessions
kept silently overwriting) into *walls* (a registered fix cannot disappear
without a RED build that names it). This report is the deliverable: the red-list
of already-lost laws, the proof the walls fire, and how a future CLI must work.

---

## 1. The red-list — laws already lost / drifted (found by the audit)

These are **reported, not re-implemented** (per the brief — the Guardian does not
touch product code). Each is registered in `LAWS.md`; the ones marked `lost` are
non-blocking until the founder restores + activates them.

| # | law | state | finding | what to restore |
|---|-----|-------|---------|-----------------|
| 1 | **law-consent** | ❌ LOST | No parental-consent / legal lock-line in **either** live game file (`nova-commercial.html`, `animal-freeze.html`). Memory records it once lived in `nova-app.html`; it was **never propagated** to the live commercial/freeze surfaces. Camera + mic run on a child with no visible consent line. | Add the EN+HE consent/legal lock-line to both live game files, then flip `law-consent` to `active` in LAWS.md. |
| 2 | **law-ambient** | ❌ LOST (pod-side) | The `nova-ambient` never-black avatar fallback is **not in git at all** — it lives on the SARAY page / `rt_lk.py` on the volume. A code comment in `nova-commercial.html` even says it depends on "the pod-side ambient patch". Unversioned = unprotected. | Land the pod files (Part 1 `pod-live` branch) with the ambient patch, register `law-ambient` against the pod repo, flip to `active`. |
| 3 | **law-truth** | ⚠ DRIFTED | The Truth-Law is **present and working** as `TRUTH GATE`, but the brief's original marker name `truthSnapshot` is **gone** — a later session renamed it. Not lost, but a future grep for the old name would wrongly think it lost. | None needed — registered against the real name `TRUTH GATE`. Noted so the drift is on record. |
| 4 | **law-transcript** (pod half) | ⚠ PARTIAL | The app half (`nova-said` / `HEARD` / `tapLogBuffer`) is present and guarded. The **pod emitter** half (`rt_lk.py` tagging these) is not yet in git. | Lands with Part 1; then guard the pod half in the pod repo. |

> The disease, seen directly: the 7-zone laws (`ZONE 1`, `__duck` refcount,
> `__mp4Leads`) are richly present in **`nova-commercial.html`** but read as
> **zero** in the older shipped `nova-app.html` / `nova-joined.html`. Fixes made
> in one lineage never propagated to the other. The walls now make that visible
> on every push.

**Everything else holds.** 9 active laws + 4 standing project laws pass:
`law-clock, law-duck, law-autoplay, law-truth, law-transcript, law-frames,
law-shoulder, law-mp4leads, law-endings` + `law-mirror, law-onevoice, law-soft,
law-storage`. Two policy laws recorded: `law-v2v` (sacred pipe), `law-treaty`.

---

## 2. Proof the walls fire (local — CI proof pending push)

The kill-test: remove one registered marker and watch the build reject it.

```
########## delete the shoulder-gate marker (__introChatT0) ##########
FAIL  law-shoulder — Intro chit-chat gate (25s) + 35s shoulder fallback   ✗ ACTIVE LAW VIOLATED — build must go RED
  ✗ law-shoulder — MARKER LOST: "__introChatT0" not found in nova-commercial.html
 SUMMARY: 8 passing · 1 known-lost · 2 FAILING
 RESULT:  ❌ RED — an ACTIVE law was violated. The push is rejected.
RUNNER-EXIT-WITH-MARKER-GONE=1

>>> restoring the marker...
 SUMMARY: 9 passing · 1 known-lost · 0 FAILING
 RESULT:  ✅ GREEN — all active laws hold.
RUNNER-EXIT-AFTER-RESTORE=0
```

Note **both** layers caught it — the dedicated `law-shoulder.js` *and* the
`LAWS.md` marker registry (`check-markers.js`). That is 2 independent walls on
one fix.

**To reproduce the RED build on GitHub (needs a push, which was intentionally
left to you):**
```
git checkout -b prove-red
perl -0pi -e 's/__introChatT0/GONE/g' nova-commercial.html
git commit -am "prove: drop a marker" && git push -u origin prove-red
# → the "Nova Laws" Action goes RED, naming law-shoulder. Then revert → green.
```

---

## 3. What shipped

### dance-project (Parts 2 + 3) — on branch `guardian`
- `tools/laws/` — `_lib.js`, ten `law-*.js`, `check-markers.js` (LAWS.md ↔ code),
  `check-syntax.js` (compiles inline `<script>` + shared JS), `run-all.sh`.
- `LAWS.md` — **append-only** registry: human section + machine block CI parses.
- `.github/workflows/laws.yml` — runs the walls on every push + PR.
- `README.md` — Nova Laws status badge.
- `START-HERE-CLI.md` — the append-only / restore-don't-delete rules.

### nova-avatar (Part 1) — on branch `pod-live`
- `boot.sh` — **pulls the checkout from git before launch** (clone/ff-only;
  refuses to clobber a diverged volume checkout, prints it for capture).
- `pod-run/` — clean launch scripts sourcing `/workspace/.env` (no key literals).
- `EDIT-LAW.txt` — direct volume edits forbidden; edit → push → pull.
- `tools/laws/pod-laws.sh` + `.github/workflows/laws.yml` — secret-scan + python
  syntax + boot-discipline walls (verified GREEN locally).
- **Security:** redacted 3 leaked live keys (LiveKit key/secret, RunPod key) from
  8 inherited scripts. **History still holds them → rotate** (LiveKit + RunPod
  dashboards), then put new values in `/workspace/.env` only.

---

## 4. Deferred (founder-coordinated — the running pods were NOT touched)

1. **Pod reconcile + live kill/revive proof (Part 1.4 / Part 4).** `pod-live` was
   seeded from the committed `lk-publisher` files (2026-07-23). The pod that ran
   most recently may hold **newer** volume-only edits (frame-mode, `nova-ambient`,
   transcript tags). At the next natural restart: `cd /workspace/app && git status`,
   commit any newer volume code **first**, then kill + revive via `boot.sh` and
   confirm the stack runs byte-identical from git. Do this only through the
   founder — no session touches the running pods out of band.
2. **Push + branch protection.** Push `guardian` (dance-project) and `pod-live`
   (nova-avatar); require the "Nova Laws" / "Nova Pod Laws" checks green to merge
   to `main`. The README badge shows red until a push exists.
3. **Rotate the leaked keys** (above).

---

## 5. How a future CLI must work now

> Before you touch anything, read `START-HERE-CLI.md`. A fix that matters becomes
> a **law**: land the code, then register its marker in the **append-only**
> `LAWS.md` (human row + machine block). CI greps every active marker on every
> push — if one vanishes, the build goes **RED with the law's name**. You fix a
> red build by **restoring the law, never by deleting its test**. Removing a
> marker without a written founder decision is a treaty violation. Pod app files
> are edited **in the repo → pushed → pulled by the pod** — never directly on the
> volume (emergency hotfix = commit from the pod within the hour). The
> 40-repeats era is over: a landed, registered fix cannot silently disappear.
