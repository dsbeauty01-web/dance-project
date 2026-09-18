#!/bin/bash
# tools/pod/deploy_from_git.sh — THE deploy step. Merge to main == deploy, brain included.
#
# WHY THIS FILE EXISTS
#   The volume's boot.sh grew its own deploy_from_git() by hand on 2026-09-08. It copied
#   pages/shared/models/beta but NOT pod/rt_lk.py, so "merge = deploy" was true for the
#   pages and false for the brain — every brain fix needed a manual scp and quietly
#   drifted (v1.0.6 shipped with the volume brain only accidentally in sync).
#   The deploy logic now lives HERE, in git, and boot.sh only calls it. After the one-time
#   volume edit (see INSTALL below) every future change to the deploy step ships by merge,
#   because the repo is pulled before this script runs.
#
# INSTALL (one time, per volume — /workspace/boot.sh):
#   Replace the body of deploy_from_git() with, or add right after its call:
#       bash /workspace/_repo/tools/pod/deploy_from_git.sh || echo "[DEPLOY] step failed"
#   GOTCHA (cost a boot on 2026-09-08): NEVER scp-overwrite /workspace/boot.sh while a
#   boot is running it — bash re-reads the file at its old byte offset and corrupts mid-boot.
#   Edit only when no boot is in flight, and write-then-mv atomically.
#
# ORDERING: boot.sh runs this at step 0, before the brain is launched at step 7, so at boot
# the copy IS the deploy and no restart is needed. Run standalone on a live pod and it will
# restart the brain itself (with health check + rollback).
#
# POD LAW (LAWS.md):
#   LAW-PODS-8-BRACKET — every pkill/pgrep pattern is bracketed so the pattern never
#     self-matches and kills the boot.
#   LAW-PODS-10-BRAINDEPLOY — a merge to main must reach the BRAIN, not just the pages:
#     this step pulls, copies pod/rt_lk.py to /workspace, keeps a rollback copy, and logs
#     the md5 transition + a real diff. Walled by tools/laws/law-pods.js.
set -u

REPO="${NOVA_REPO_DIR:-/workspace/_repo}"
BRANCH="${NOVA_DEPLOY_BRANCH:-main}"
WS="${NOVA_WORKSPACE:-/workspace}"
TOKEN_FILE="${NOVA_DEPLOY_TOKEN:-/workspace/.deploy-token}"
REPO_URL_DEFAULT="https://github.com/dsbeauty01-web/dance-project.git"
STAMP="${WS}/.deploy-rtlk.md5"      # md5 of the brain WE last deployed (drift detector)
DIFF_OUT="${NOVA_DEPLOY_DIFF:-/root/deploy-rtlk.diff}"  # the proof: what this deploy changed
RESTART="${NOVA_DEPLOY_RESTART:-1}" # 0 = copy only, never touch a running brain
BRAIN_LOG="${NOVA_BRAIN_LOG:-/root/rtlk.log}"
HEALTH_TRIES="${NOVA_DEPLOY_HEALTH_TRIES:-15}"   # x4s — how long the new brain may take

say(){ echo "[DEPLOY] $*"; }
md5of(){ [ -f "$1" ] && md5sum "$1" 2>/dev/null | cut -c1-32 || echo "-"; }

# ---------------------------------------------------------------- 1) refresh the repo
if [ ! -d "$REPO/.git" ]; then
  url="$REPO_URL_DEFAULT"
  [ -f "$TOKEN_FILE" ] && url="https://x-access-token:$(tr -d '\r\n' <"$TOKEN_FILE")@github.com/dsbeauty01-web/dance-project.git"
  git clone --depth 20 -b "$BRANCH" "$url" "$REPO" >/dev/null 2>&1 || { say "clone FAILED — nothing deployed"; exit 1; }
fi
git -C "$REPO" fetch --depth 20 origin "$BRANCH" >/dev/null 2>&1 || say "fetch failed — deploying the cached checkout"
git -C "$REPO" reset --hard "origin/${BRANCH}" >/dev/null 2>&1
SHA="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"

# ---------------------------------------------------------------- 2) pages + static
mkdir -p "$WS/pages" "$WS/shared" "$WS/models"
copied=""
for f in "$REPO"/pod/pages/*.html; do
  [ -f "$f" ] && { cp -f "$f" "$WS/pages/" && copied="$copied $(basename "$f")"; }
done
say "pages synced from ${BRANCH}@${SHA}:${copied:- none}"
# (explicit loops, not colon-packed pairs — a ":" splitter silently ate the drive letter
#  when this was sandbox-tested on Windows paths)
for f in "$REPO"/shared/*.js;    do [ -f "$f" ] && cp -f "$f" "$WS/shared/"; done
for f in "$REPO"/models/*.task;  do [ -f "$f" ] && cp -f "$f" "$WS/models/"; done
if [ -d "$REPO/beta" ]; then mkdir -p "$WS/beta"; cp -rf "$REPO"/beta/* "$WS/beta/" 2>/dev/null; fi

# ---------------------------------------------------------------- 3) the brain (the gap)
SRC="$REPO/pod/rt_lk.py"
DST="$WS/rt_lk.py"
if [ ! -f "$SRC" ]; then
  say "brain SKIPPED — $SRC missing on ${BRANCH}@${SHA}"
  exit 0
fi

live_md5="$(md5of "$DST")"; new_md5="$(md5of "$SRC")"
last_md5="$( [ -f "$STAMP" ] && tr -d '\r\n' <"$STAMP" || echo - )"

if [ "$live_md5" = "$new_md5" ]; then
  say "brain rt_lk.py already at ${BRANCH}@${SHA} (md5 ${new_md5:0:8}) — UNCHANGED"
  echo "$new_md5" >"$STAMP"
  exit 0
fi

# The proof: a real diff of what is about to change, kept on the pod.
if [ -f "$DST" ]; then
  diff -u "$DST" "$SRC" >"$DIFF_OUT" 2>/dev/null
  adds="$(grep -c '^+[^+]' "$DIFF_OUT" 2>/dev/null || echo 0)"
  dels="$(grep -c '^-[^-]' "$DIFF_OUT" 2>/dev/null || echo 0)"
else
  : >"$DIFF_OUT"; adds="$(wc -l <"$SRC")"; dels=0
fi

# Drift guard: if the live brain is NOT what we last deployed, someone hand-edited the
# volume (it has happened: "volume rt_lk.py evolved past repo"). main still wins — but the
# hand-edit is preserved and shouted about, never silently destroyed.
if [ -f "$DST" ] && [ "$live_md5" != "$last_md5" ]; then
  drift="${DST}.bak-drift-$(date -u +%Y%m%dT%H%M%SZ)"
  cp -f "$DST" "$drift"
  say "WARNING volume brain was hand-edited (md5 ${live_md5:0:8} != last deployed ${last_md5:0:8}) — saved $drift"
fi
[ -f "$DST" ] && cp -f "$DST" "${DST}.bak-predeploy"

cp -f "$SRC" "$DST" || { say "brain copy FAILED — live file untouched"; exit 1; }
echo "$new_md5" >"$STAMP"
say "brain rt_lk.py DEPLOYED from ${BRANCH}@${SHA}: md5 ${live_md5:0:8} -> ${new_md5:0:8} (+${adds} -${dels} lines, diff: ${DIFF_OUT})"

# ---------------------------------------------------------------- 4) restart the brain
# pgrep is in procps on the pod; ps-fallback keeps the script usable where it is not.
find_brain(){
  if command -v pgrep >/dev/null 2>&1; then pgrep -f '[r]t_lk\.py' | head -1
  else ps -ef 2>/dev/null | grep '[r]t_lk\.py' | awk '{print $2}' | head -1; fi
}
BRAIN_PID="$(find_brain)"
if [ -z "$BRAIN_PID" ]; then
  say "brain not running — boot starts the new file at step 7 (no restart needed)"
  exit 0
fi
if [ "$RESTART" != "1" ]; then
  say "brain running (pid $BRAIN_PID) but NOVA_DEPLOY_RESTART=0 — new code lands on next restart"
  exit 0
fi

brain_up(){ [ "$(curl -s -m4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/ 2>/dev/null)" = "200" ]; }
detach(){ if command -v setsid >/dev/null 2>&1; then setsid "$@"; else "$@"; fi; }
start_brain(){
  # env lives in boot.sh's exports (and /workspace/.env); a bare `python rt_lk.py` dies on
  # ModuleNotFoundError livekit without PYTHONPATH. tmux is NOT installed on a fresh
  # container and dies with the ssh session — always setsid.
  if [ -x /root/start_rtlk.sh ]; then
    detach nohup bash /root/start_rtlk.sh >>"$BRAIN_LOG" 2>&1 </dev/null & disown
  else
    ( set -a
      [ -f "$WS/.env" ] && . "$WS/.env"
      [ -f "$WS/boot.sh" ] && eval "$(grep '^export ' "$WS/boot.sh")"
      export PYTHONPATH="${PYTHONPATH:-/workspace/_sys/pylibs311_good/dist-packages}"
      set +a
      cd "$WS" && detach nohup python -u rt_lk.py >>"$BRAIN_LOG" 2>&1 </dev/null & disown )
  fi
}

say "brain restart: killing pid $BRAIN_PID"
kill "$BRAIN_PID" 2>/dev/null; sleep 3; kill -9 "$BRAIN_PID" 2>/dev/null
start_brain
for i in $(seq 1 "$HEALTH_TRIES"); do brain_up && break; sleep 4; done

if brain_up; then
  say "brain RESTARTED and healthy on :8765 at ${BRANCH}@${SHA} (md5 ${new_md5:0:8})"
  exit 0
fi

# Rollback: a pod that boots with a dead brain is worse than one running yesterday's brain.
say "brain did NOT come up after 60s — ROLLING BACK to ${DST}.bak-predeploy"
[ -f "${DST}.bak-predeploy" ] && cp -f "${DST}.bak-predeploy" "$DST"
echo "$live_md5" >"$STAMP"
pkill -f '[r]t_lk\.py' 2>/dev/null; sleep 2
start_brain
for i in $(seq 1 "$HEALTH_TRIES"); do brain_up && break; sleep 4; done
brain_up && say "ROLLBACK OK — brain back on md5 ${live_md5:0:8}; see /root/rtlk.log" \
         || say "ROLLBACK FAILED — brain DOWN, needs hands; see /root/rtlk.log"
exit 1
