#!/usr/bin/env bash
# novafix_job.sh -- session novafix-intro, 2026-11-01. ONE pod, five stages, in this order:
#
#   A. FREE QUOTA on the production volume 1ditrne6cb  (the blocker; nothing works before it)
#   B. RESTORE the pages boot.sh truncated to 0 bytes  (the live commercial game is DOWN)
#   C. FACE ENGINE: probe + apply the Ditto bridge patch, Ditto on the full-body motion bank
#   D. THE RECORDING: the real page, in headless Chromium, with the kid played live
#   E. leave the volume as found (revert the patch, drop our backups)
#
# Everything this job writes lives on the CONTAINER disk (/root). The only writes to the
# volume are (1) the deletions of stage A, strictly allow-listed by free_quota.py, (2) the
# deploy of stage B, which is the normal boot.sh deploy and is the whole point, and (3)
# lk_bridge.py in stage C, backed up and reverted in stage E.
#
# ORDER MATTERS in stage C: lk_bridge.py with NOVA_FACE=ditto RAISES if the Ditto server is
# not already serving (no silent fallbacks, repo law 4), so Ditto comes up BEFORE boot.sh.
set -uo pipefail
# cd off the production volume. Its top level holds ~34 loose .py files, any of which can
# shadow a stdlib module for a plain `python3` run whose CWD is /workspace (this is the same
# class of failure that killed podsrv on 2026-10-31). From /root there is nothing to shadow.
cd /root || exit 9
IN=/root/in; OUT=/root/novafix_out; MT=/root/mt; LOG=/root/logs
mkdir -p "$OUT" "$MT/maya-ops/lt" "$MT/bench/replace_musetalk_alt" "$LOG"
say(){ local m="[job $(date -u +%H:%M:%S)] $*"; echo "$m"; echo "$m" >> "$OUT/STAGES"; }
: > "$OUT/STAGES"

# uploaded as novalive_job.sh because that is the name podup_nl.py's patched START waits for
need="novalive_job.sh free_quota.py live_intro_harness.py ditto_bridge_patch.py nova_ditto.py \
ditto_server.py ditto_up.sh ditto_wide.py motion_bank.py ditto_fullbody.py sitecustomize.py \
nova_fb_bank.mp4 nova_fb_bank.json PAYLOAD_DONE"
say "stage 0: waiting for the payload"
for i in $(seq 1 240); do
  ok=1; for f in $need; do [ -s "$IN/$f" ] || ok=0; done
  [ $ok = 1 ] && break; sleep 5
done
for f in $need; do [ -s "$IN/$f" ] || { say "MISSING $f -- abort"; echo 11 > "$OUT/RC"; exit 11; }; done
say "stage 0 OK: payload complete"
md5sum "$IN"/*.py "$IN"/*.json "$IN"/*.sh > "$OUT/payload_md5.txt" 2>/dev/null

# ---------- background: the two slow installs, started now so stages A/B hide them ----------
say "bg: python3.10-dev + build-essential (Ditto's pyximport needs Python.h)"
( apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3.10-dev build-essential && echo READY > "$OUT/DEV_READY" ) > "$OUT/aptdev.log" 2>&1 &
say "bg: playwright + chromium (the recording needs it)"
( pip install -q playwright >/dev/null 2>&1 \
    && python3 -m playwright install --with-deps chromium \
    && echo READY > "$OUT/PW_READY" ) > "$OUT/playwright.log" 2>&1 &

# =========================================================== STAGE A: FREE THE QUOTA =======
# A0. The deploy-failure evidence is in the volume's own boot log, and stage A2 deletes *.log.
#     Copy it FIRST. It also carries the GitHub deploy token in clear text (boot.sh prints the
#     full remote URL on a failed deploy), so the copy is redacted before it is ever pulled.
say "stage A0: preserving the deploy-failure evidence from the volume's boot log"
for bl in /workspace/logs/boot.log /root/boot.log /workspace/boot.log; do
  [ -s "$bl" ] || continue
  tail -500 "$bl" | sed -E 's#(https?://)[^/@[:space:]]+@#\1<REDACTED-TOKEN>@#g; s#x-access-token:[A-Za-z0-9_-]+#x-access-token:<REDACTED-TOKEN>#g; s#gh[psuor]_[A-Za-z0-9]{16,}#<REDACTED-TOKEN>#g' \
    > "$OUT/boot.log.tail500.$(basename "$(dirname "$bl")").txt"
  say "  kept $(wc -l < "$OUT/boot.log.tail500.$(basename "$(dirname "$bl")").txt") lines from $bl (token redacted)"
done
grep -lE 'x-access-token:[A-Za-z0-9_-]{8,}|gh[psuor]_[A-Za-z0-9]{16,}' /workspace/logs/boot.log /root/boot.log 2>/dev/null \
  > "$OUT/TOKEN_IN_LOG.txt" || true
[ -s "$OUT/TOKEN_IN_LOG.txt" ] && say "  SECURITY: a deploy token appears in clear text in: $(tr '\n' ' ' < "$OUT/TOKEN_IN_LOG.txt")"

# A1. survey -- READ ONLY apart from its own write probe
say "stage A1: survey (read only). df is reported but NOT trusted; du and a write probe decide."
df -h /workspace > "$OUT/df_workspace.txt" 2>&1
cat "$OUT/df_workspace.txt"
python3 -I "$IN/free_quota.py" --volume /workspace --survey --report "$OUT/survey.json" \
  > "$OUT/survey.txt" 2>&1; SRC=$?
say "stage A1: survey rc=$SRC"
cat "$OUT/survey.txt"
python3 -I - "$OUT/survey.json" > "$OUT/survey_human.txt" 2>&1 <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print("df (NOT the quota -- the cluster):",d.get("df_h","?").splitlines()[-1:])
print("du total on the volume:",d["du_total"],f"({d['du_total_bytes']} bytes)")
print()
print("== 30 LARGEST DIRECTORIES ==")
for r in d.get("largest_dirs",[])[:30]: print(f"  {r['h']:>9s}  {r['path']}")
print()
print("== 30 LARGEST FILES ==")
for r in d.get("largest_files",[])[:30]: print(f"  {r['h']:>9s}  {'DENY ' if r['denied'] else '     '}{r['path']}")
print()
print(f"== 0-BYTE FILES UNDER /workspace/pages ({d['zero_byte_count']}) ==")
for r in d.get("zero_byte_under_pages",[]): print(f"  {r['mtime']}  {r['path']}")
print()
print("== WRITE PROBE (the only honest headroom measure) ==")
for k,v in d.get("write_probe",{}).items(): print(f"  {k}: ok={v.get('ok')} {v.get('err','')}")
print()
print("== DELETABLE CANDIDATES (sized, not yet deleted) ==")
for k,v in d.get("candidates",{}).items(): print(f"  {k:9s} {v['h']:>9s}  n={v['n']}")
PY
cat "$OUT/survey_human.txt"
cp "$OUT/survey_human.txt" "$OUT/A1_SURVEY_DONE" 2>/dev/null

# A2. delete, allow-list only. 'scratch' is NOT in --cats: dated dumps are only listed.
say "stage A2: freeing space (allow-list: caches, pycache, logs, stale repo clones, tmp)"
python3 -I "$IN/free_quota.py" --volume /workspace --clean \
  --cats caches,pycache,logs,stale,tmp --report "$OUT/freed.json" > "$OUT/freed.txt" 2>&1; CRC=$?
say "stage A2: clean rc=$CRC"
cat "$OUT/freed.txt"
TWOGB=$(python3 -I -c "import json;print(json.load(open('$OUT/freed.json'))['two_gb_free'])" 2>/dev/null)
say "stage A2: 2GB writable = $TWOGB"

# A3. gate. If 2 GB is still not writable, STOP and ask -- do not guess at the bakes.
if [ "$TWOGB" != "True" ]; then
  say "stage A3: UNDER 2 GB FREE -- holding for a decision. Writing NEED_DECISION."
  { echo "2 GB is still not writable after the allow-list."; echo
    echo "Scratch dirs found but NOT deleted (a decision is needed):"
    python3 -I -c "
import json;d=json.load(open('$OUT/freed.json'))
[print(' ',s['h'].rjust(9),s['path']) for s in d.get('skipped_scratch',[])] or print('  (none)')"
    echo; echo "Largest things still on the volume:"; sed -n '/30 LARGEST DIRECTORIES/,/30 LARGEST FILES/p' "$OUT/survey_human.txt"
  } > "$OUT/NEED_DECISION"
  cat "$OUT/NEED_DECISION"
  say "stage A3: waiting up to 15 min for /root/in/SCRATCH_GO (delete the listed dumps) or /root/in/CONTINUE"
  for i in $(seq 1 180); do [ -e "$IN/SCRATCH_GO" ] && break; [ -e "$IN/CONTINUE" ] && break; sleep 5; done
  if [ -e "$IN/SCRATCH_GO" ]; then
    say "stage A3: SCRATCH_GO -- deleting the dated render dumps too"
    python3 -I "$IN/free_quota.py" --volume /workspace --clean --cats scratch --allow-scratch \
      --report "$OUT/freed2.json" > "$OUT/freed2.txt" 2>&1
    cat "$OUT/freed2.txt"
    TWOGB=$(python3 -I -c "import json;print(json.load(open('$OUT/freed2.json'))['two_gb_free'])" 2>/dev/null)
    say "stage A3: 2GB writable now = $TWOGB"
  else
    say "stage A3: CONTINUE (or timeout) -- proceeding with whatever headroom exists"
  fi
fi
echo "$TWOGB" > "$OUT/TWOGB"

# =========================================================== STAGE B: RESTORE THE PAGES ====
# The truncated files are all in git on nova-ditto. deploy_from_git.sh is the normal deploy
# step boot.sh runs at step 0; with room on the volume it rewrites every one of them.
say "stage B1: the normal deploy, NOVA_DEPLOY_BRANCH=nova-ditto"
export NOVA_DEPLOY_BRANCH=nova-ditto
export NOVA_DEPLOY_RESTART=0        # nothing is running yet; do not let it bounce a brain
DEPLOY=/workspace/_repo/tools/pod/deploy_from_git.sh
if [ -s "$DEPLOY" ]; then
  bash "$DEPLOY" > "$OUT/deploy.log" 2>&1; DRC=$?
else
  say "stage B1: $DEPLOY missing -- running boot.sh's own deploy via boot.sh step 0 instead"
  DRC=90
fi
# redact before this log is ever pulled: the deploy prints the tokenised remote URL on failure
sed -i -E 's#(https?://)[^/@[:space:]]+@#\1<REDACTED-TOKEN>@#g; s#x-access-token:[A-Za-z0-9_-]+#x-access-token:<REDACTED-TOKEN>#g; s#gh[psuor]_[A-Za-z0-9]{16,}#<REDACTED-TOKEN>#g' "$OUT/deploy.log" 2>/dev/null
say "stage B1: deploy rc=$DRC"
tail -25 "$OUT/deploy.log" 2>/dev/null

# B2. VERIFY: is every file that was 0 bytes now non-zero?
say "stage B2: verifying the restore, file by file"
python3 -I - > "$OUT/restore_verify.txt" 2>&1 <<'PY'
import json, os
# the 0-byte list measured BEFORE the deploy, from this run's own survey
try:
    pre = [r["path"] for r in json.load(open("/root/novafix_out/survey.json"))["zero_byte_under_pages"]]
except Exception as e:
    pre = []
    print("could not read the pre-deploy survey:", e)
# the files the 2026-11-01 diagnosis named explicitly, checked whether or not they were in pre
named = ["/workspace/pages/beta/freeze.html", "/workspace/pages/upperbody.html",
         "/workspace/pages/models/pose_landmarker_lite.task"]
named += ["/workspace/pages/shared/%s.js" % n for n in
          ("cue-window", "freeze-fx", "game-kit", "light-engine", "mover-engine", "mover-rules",
           "nova-bridge", "nova-lang", "nova-lights", "pose-adapter", "pose-engine", "pulse")]
named += ["/workspace/pages/beta/%s" % n for n in
          ("copy.html", "demo.html", "freeze-nova.html", "freeze3.html", "groove.html",
           "hello.html", "index.html", "novasays.html", "novasays.js", "play.css")]
check = sorted(set(pre) | set(named))
good, bad, missing = [], [], []
for p in check:
    if not os.path.exists(p):
        missing.append(p); continue
    n = os.path.getsize(p)
    (good if n > 0 else bad).append((p, n))
print(f"checked {len(check)} files  ({len(pre)} were 0 bytes in this run's survey)")
print(f"  NON-ZERO now : {len(good)}")
print(f"  STILL 0 BYTES: {len(bad)}")
print(f"  MISSING      : {len(missing)}")
for p, n in good: print(f"    ok   {n:>9d}  {p}")
for p, n in bad:  print(f"    ZERO {n:>9d}  {p}")
for p in missing: print(f"    GONE            {p}")
# and a fresh full scan, in case the deploy truncated something new
still = []
for root, d, fs in os.walk("/workspace/pages"):
    for f in fs:
        q = os.path.join(root, f)
        try:
            if os.path.getsize(q) == 0: still.append(q)
        except OSError: pass
print(f"\nfresh scan: {len(still)} file(s) under /workspace/pages are 0 bytes")
for q in sorted(still): print("   ZERO", q)
json.dump({"non_zero": len(good), "still_zero": [p for p,_ in bad],
           "missing": missing, "fresh_zero_scan": sorted(still)},
          open("/root/novafix_out/restore_verify.json", "w"), indent=1)
PY
cat "$OUT/restore_verify.txt"

# =========================================================== STAGE C: THE FACE ENGINE =====
say "stage C1: Ditto on the full-body motion bank (must be serving BEFORE the bridge wants it)"
for i in $(seq 1 60); do [ -s "$OUT/DEV_READY" ] && break; sleep 5; done
[ -e /usr/include/python3.10/Python.h ] && say "  Python.h present" || say "  WARN Python.h MISSING -- Ditto may fail to build"
cp "$IN/ditto_server.py" "$IN/ditto_up.sh" "$IN/motion_bank.py" "$MT/maya-ops/lt/"
cp "$IN/ditto_wide.py" "$MT/bench/replace_musetalk_alt/"
chmod +x "$MT/maya-ops/lt/ditto_up.sh"
export PYTHONPATH="$IN:${PYTHONPATH:-}"
export DITTO_FB_ON=1 DITTO_FB_SHIM="$IN" DITTO_FB_BENCH="$MT/bench/replace_musetalk_alt"
export DITTO_FB_UP="${FB_UP:-3.0}" DITTO_FB_BOX="${FB_BOX:-263,215,763,715}"
export DITTO_ROOT=/root/ditto MAYA_LOGS="$LOG" DITTO_PORT=8031
export DITTO_AMP=0.6 DITTO_CHUNK=25 DITTO_PRIME=35 DITTO_VAD=1 DITTO_THREADS=6 DITTO_EYE_HOLD=1
export DITTO_WAIT_SEC=1500
# DITTO-FULLBODY section 4: out_wh is reported from the SOURCE file, but Ditto resizes to
# max_size 1920 on the long side, so a 1924-high body is delivered at 1074x1920. Stating the
# truth here is one of the two documented fixes and needs no code change.
export DITTO_OUT_W=1074 DITTO_OUT_H=1920
export DITTO_SRC="$IN/nova_fb_bank.mp4" DITTO_BANK="$IN/nova_fb_bank.json"
bash "$MT/maya-ops/lt/ditto_up.sh" > "$OUT/ditto_up.log" 2>&1; DIRC=$?
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto.json" 2>&1
cp "$LOG/ditto_server.log" "$OUT/ditto_server.log" 2>/dev/null
say "stage C1: ditto_up rc=$DIRC health=$(head -c 300 "$OUT/health_ditto.json")"
DITTO_OK=0; grep -q '"ready": *true' "$OUT/health_ditto.json" 2>/dev/null && DITTO_OK=1
[ "$DITTO_OK" = 1 ] || { say "stage C1: Ditto NOT ready -- the recording will use MuseTalk"; tail -25 "$OUT/ditto_up.log"; }

FACE=musetalk
if [ "$DITTO_OK" = 1 ]; then
  say "stage C2: probing the REAL /workspace/lk_bridge.py (all four anchors must be exactly 1)"
  python3 -I "$IN/ditto_bridge_patch.py" --probe --wd "$OUT" > "$OUT/probe.txt" 2>&1; PRC=$?
  say "stage C2: probe rc=$PRC"; sed -n '1,16p' "$OUT/probe.txt"
  if [ "$PRC" = 0 ]; then
    python3 -I "$IN/ditto_bridge_patch.py" --apply --sidecar "$IN/nova_ditto.py" --wd "$OUT" \
      > "$OUT/apply.txt" 2>&1; ARC=$?
    say "stage C2: apply rc=$ARC"; tail -14 "$OUT/apply.txt"
    if [ "$ARC" = 0 ]; then
      FACE=ditto
    else
      say "stage C2: apply refused -- REVERTING to the untouched original and staying on MuseTalk"
      python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert_early.txt" 2>&1
      tail -4 "$OUT/revert_early.txt"
    fi
  else
    say "stage C2: the probe does not match this file -- NOT applying. MuseTalk."
  fi
fi
echo "$FACE" > "$OUT/FACE"
say "stage C DONE: face engine = $FACE"

# =========================================================== STAGE D: THE STACK + RECORD ==
say "stage D1: boot.sh -- the whole Nova stack, one boot (LAW-PODS-9-COLDLOAD: silence is loading)"
export NOVA_DEPLOY_BRANCH=nova-ditto
export NOVA_DITTO_DELAY_SITE=bridge
unset NOVA_DEPLOY_RESTART
[ "$FACE" = ditto ] && export NOVA_FACE=ditto || unset NOVA_FACE
setsid nohup bash /workspace/boot.sh > "$OUT/bootwrap.log" 2>&1 < /dev/null &
BRAIN=0
for i in $(seq 1 300); do
  c=$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)
  if [ "$c" = "200" ]; then BRAIN=1; say "stage D1: BRAIN_UP after $((i*5))s"; break; fi
  [ $((i % 12)) = 0 ] && say "stage D1: waiting ${i}0s... boot=$(wc -c < /root/boot.log 2>/dev/null) bridge=$(wc -c < /root/bridge.log 2>/dev/null)"
  sleep 5
done
for f in /root/boot.log /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E 's#(https?://)[^/@[:space:]]+@#\1<REDACTED-TOKEN>@#g; s#x-access-token:[A-Za-z0-9_-]+#x-access-token:<REDACTED-TOKEN>#g; s#gh[psuor]_[A-Za-z0-9]{16,}#<REDACTED-TOKEN>#g' "$f" > "$OUT/$(basename "$f")"
done
[ "$BRAIN" = 1 ] && echo UP > "$OUT/STACK" || { say "stage D1 FAILED: :8765 never answered 200"; echo FAILED > "$OUT/STACK"; }
grep -h "NOVA_FACE" "$OUT/bridge.log" "$OUT/rtlk.log" 2>/dev/null | head -5 | while read -r l; do say "    $l"; done

# D2. THE PROOF the live page is back: non-empty, and it carries JUDGE-TRUTH.
say "stage D2: what the brain serves now (this is the live-page evidence)"
{ for p in "/beta/freeze?intro=freeze" "/freeze?intro=freeze" "/" "/health"; do
    code=$(curl -s -m 10 -o /tmp/_pg -w '%{http_code}' "http://127.0.0.1:8765$p")
    sz=$(stat -c %s /tmp/_pg 2>/dev/null || echo 0)
    jt=$(grep -c "JUDGE-TRUTH" /tmp/_pg 2>/dev/null || echo 0)
    printf '%-28s http=%s  %s bytes  JUDGE-TRUTH=%s  first100=%s\n' "$p" "$code" "$sz" "$jt" "$(head -c 100 /tmp/_pg | tr '\n' ' ')"
  done; } > "$OUT/page_probe.txt" 2>&1
cat "$OUT/page_probe.txt"
curl -s -m 15 "http://127.0.0.1:8765/beta/freeze?intro=freeze" -o "$OUT/freeze.served.html"
say "stage D2: /beta/freeze = $(stat -c %s "$OUT/freeze.served.html" 2>/dev/null) bytes, JUDGE-TRUTH x$(grep -c JUDGE-TRUTH "$OUT/freeze.served.html" 2>/dev/null)"

# D3. the recording
say "stage D3: waiting up to 20 min for /root/in/GO"
for i in $(seq 1 240); do [ -e "$IN/GO" ] && break; sleep 5; done
if [ ! -e "$IN/GO" ]; then say "stage D3: no GO -- skipping the recording"; else
  [ -s "$OUT/PW_READY" ] || { say "stage D3: waiting on playwright"; for i in $(seq 1 90); do [ -s "$OUT/PW_READY" ] && break; sleep 5; done; }
  say "stage D3: RECORDING -- live_intro_harness.py (engine=$FACE)"
  # NOT -I here: the harness imports playwright from site-packages and -I implies -s.
  # CWD is /root (set at the top), so there is nothing on the volume to shadow a stdlib name.
  python3 "$IN/live_intro_harness.py" --out "$OUT" --inbox "$IN" \
      --rec-dir /root/rec --max-s "${REC_MAX_S:-240}" \
      --url "http://127.0.0.1:8765/beta/freeze?intro=freeze|http://127.0.0.1:8765/freeze?intro=freeze" \
      > "$OUT/harness.log" 2>&1
  say "stage D3: harness rc=$? -- $(tail -1 "$OUT/harness.log")"
fi
for f in /root/bridge.log /root/rtlk.log /root/app.log; do
  [ -s "$f" ] && sed -E 's#(https?://)[^/@[:space:]]+@#\1<REDACTED-TOKEN>@#g' "$f" > "$OUT/$(basename "$f")"
done
cp "$LOG/ditto_server.log" "$OUT/ditto_server_end.log" 2>/dev/null
curl -s -m 10 127.0.0.1:8031/health > "$OUT/health_ditto_end.json" 2>&1
ls -la "$OUT" > "$OUT/LISTING" 2>&1
say "ALL DONE -- waiting up to 20 min for /root/in/PULLED, then reverting"

# =========================================================== STAGE E: LEAVE AS FOUND ======
for i in $(seq 1 240); do [ -s "$IN/PULLED" ] && break; sleep 5; done
if [ "$FACE" = ditto ]; then
  python3 -I "$IN/ditto_bridge_patch.py" --revert --wd "$OUT" > "$OUT/revert.txt" 2>&1
  say "stage E: revert lk_bridge.py rc=$? -- $(tail -2 "$OUT/revert.txt" | head -1)"
fi
rm -f /workspace/lk_bridge.py.bak-ditto-* /workspace/nova_ditto.py
md5sum /workspace/lk_bridge.py /workspace/rt_lk.py > "$OUT/volume_md5_end.txt" 2>&1
say "stage E DONE: $(cat "$OUT/volume_md5_end.txt" | tr '\n' ' ')"
echo 0 > "$OUT/RC"
