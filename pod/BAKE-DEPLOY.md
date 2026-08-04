# BAKE-DEPLOY — unattended gesture bake (2026-08-02)

**Situation:** Founder leaves in ~20 min, laptop will CLOSE. The bake must survive that.
**Prime rule:** everything long-running goes in **tmux ON THE POD**. Nothing may depend on the laptop or this SSH session staying alive.

---

## POD LAWS in force (do not violate)

- **Bakes → Community pod. NEVER bake on the live Secure pod `ubu8krpcf0k62v`.**
- Attach the shared network volume **`1ditrne6cb`** (EU-RO-1) — bakes must land there so the live pod sees them.
- tmux for anything long. Bracket-pkill only (`pkill -f "[b]ake"`), never bare pkill.

---

## STEP 0 — Dedup check (10 seconds, saves money)

Already baked & COMPLETE on the volume (from today's BAKE REPORT — skip any of these found in the zip):

```
gest_bear gest_flamingo gest_frog gest_star gest_bothhand gest_clap
gest_freeze2 gest_lefthand gest_righthand gest_thankyou
nova_idle nova_idle2 nova_walk nova_sub nova_active nova_groove
```

`unzip -l <founder's zip>` → list contents → **bake only NEW videos + optionally re-bake `nova_hype`** (its old bake is dead; source `/workspace/sources/dance-hype.mp4` is already on the volume).

If the zip contains ONLY the 10 known gestures → tell the founder "already baked, nothing to do" and stop. Do NOT re-bake for free.

## STEP 1 — Spin up the bake pod (Community)

- GPU: RTX 4090, Community Cloud, region **EU-RO-1** (must match the volume)
- Network volume: **`1ditrne6cb`** mounted at `/workspace`
- Template/image: same as previous bake pods (MuseTalk/LiveTalking env already on the volume at `/workspace/LiveTalking`)

Record the new pod id in `pod-registry.js` (append, don't overwrite).

## STEP 2 — Get the zip onto the volume

From the laptop (do this FIRST — it needs the laptop alive):

```bash
# whichever transport works; runpodctl preferred
runpodctl send <path-to-zip>            # then receive on pod
# or: scp -P <ssh-port> <zip> root@<pod-ip>:/workspace/incoming.zip
```

On the pod:

```bash
mkdir -p /workspace/sources/new-2026-08-02
unzip -o /workspace/incoming.zip -d /workspace/sources/new-2026-08-02/
ls -la /workspace/sources/new-2026-08-02/    # confirm mp4s present, note names
```

**Zip transfer must COMPLETE before the founder leaves.** Verify size matches (`ls -l` both sides). If transfer can't finish in time → abort, tell founder to redo from home. Never bake from a half-copied file.

## STEP 3 — Write the bake script ON THE POD

`/workspace/bake-batch.sh`:

```bash
#!/bin/bash
# BAKE BATCH 2026-08-02 — runs unattended in tmux
set -o pipefail
cd /workspace/LiveTalking
LOG=/workspace/bake-2026-08-02.log
echo "=== BAKE BATCH start $(date -u) ===" >> $LOG

bake_one () {  # $1 = avatar_id   $2 = source video
  echo "--- baking $1 from $2 $(date -u) ---" >> $LOG
  # EXACT bake command: reuse the same invocation used for the existing 17 bakes.
  # Find it first:  grep -r "genavatar\|--avatar_id" /workspace/LiveTalking/*.sh /workspace/*.sh 2>/dev/null
  # It is the MuseTalk avatar-prep entrypoint (creates full_imgs/ mask/ latents.pt coords.pkl mask_coords.pkl).
  python -m musetalk.genavatar --avatar_id "$1" --file "$2" >> $LOG 2>&1
  # INTEGRITY CHECK — a real bake has latents.pt (121-frame std = 2,017,677 bytes)
  D=/workspace/LiveTalking/data/avatars/$1
  if [ -f "$D/latents.pt" ] && [ -f "$D/coords.pkl" ] && [ -f "$D/mask_coords.pkl" ]; then
    echo "OK  $1  latents=$(stat -c%s $D/latents.pt)" >> $LOG
  else
    echo "FAIL $1 — incomplete bake (missing latents/coords)" >> $LOG
  fi
}

# ⇩ CLI fills this list from STEP 0/2 (new videos only; id = gest_<shortname>)
# bake_one gest_xxx /workspace/sources/new-2026-08-02/xxx.mp4
# Optional repair of the one dead bake:
# rm -rf /workspace/LiveTalking/data/avatars/nova_hype
# bake_one nova_hype /workspace/sources/dance-hype.mp4

echo "=== BAKE BATCH done $(date -u) ===" >> $LOG
```

⚠️ **Before running:** verify the real bake command by inspecting how the existing bakes were made (grep above, or the LiveTalking README on the volume). Do not guess flags. The integrity check is the truth: `latents.pt` + both pkl files present = complete.

## STEP 4 — Launch DETACHED (the laptop-close-proof part)

```bash
chmod +x /workspace/bake-batch.sh
tmux new -d -s bake '/workspace/bake-batch.sh'
tmux ls                                   # must show: bake: 1 windows
sleep 20 && tail -5 /workspace/bake-2026-08-02.log   # confirm it's actually writing
```

**Only after `tmux ls` shows the session AND the log is growing → tell the founder: "detached, safe to close the laptop and go."** Not before.

## STEP 5 — Cost guard

Community 4090 ≈ $0.3-0.5/hr; a 121-frame bake ≈ minutes each. Whole batch well under an hour.
Add a self-stop so it can't burn money overnight — append to the END of bake-batch.sh (before writing it):

```bash
# self-stop the BAKE pod when done (NEVER the live pod ubu8krpcf0k62v)
runpodctl stop pod $RUNPOD_POD_ID 2>>$LOG || echo "self-stop failed — founder must stop pod manually" >> $LOG
```

## STEP 6 — Report for the founder's return

Write `/workspace/BAKE-RESULT-2026-08-02.md` (the founder reads it when back):
- zip contents, which were skipped as duplicates
- which baked OK / FAIL (from the log's OK/FAIL lines)
- new avatars now on volume → visible to live pod via `/set_avatar?id=…`
- pod stopped yes/no + cost
- reminder if `nova_hype` was repaired or still dead

---

## Founder's one-glance checklist before walking out

1. Zip fully transferred to pod ✅
2. `tmux ls` shows `bake` ✅
3. Log growing ✅
→ close laptop, go. Everything else is the pod's problem.
