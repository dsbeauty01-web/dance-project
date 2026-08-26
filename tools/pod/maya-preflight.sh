#!/usr/bin/env bash
# maya-preflight.sh  —  IDENTITY PREFLIGHT + ENV FIREWALL for the Maya project.
# Spec: maya-not-nova-fix.md STEP 2.  Made after the 2026-08-26 nova-leak
# (the Nova dance-kid was baked/streamed as `maya_rapa` — see maya-ops/NOVA-LEAK-REPORT.md).
#
# RULE: every Maya bring-up / bake / go-live MUST run this FIRST and abort on any 'nova' value.
# There is deliberately NO override flag.
#
#   Usage:   source tools/pod/maya-preflight.sh        # asserts, then exposes maya_safe_source()
#     or:    AVATAR=maya_idle bash tools/pod/maya-preflight.sh
#
# Correct Maya identity (from the audit):
#   PROJECT = maya   ·   LK_ROOM = maya-live   ·   AVATAR = maya_*   ·
#   BRAIN   = pod/maya_rt.py  (NOT rt_lk.py — that is Nova's brain)   ·
#   VOICE   via MAYA_VOICE     (never NOVA_VOICE)
set -euo pipefail

_maya_fail(){ printf '\n\033[41;97m  MAYA PREFLIGHT FAILED  \033[0m  %s\n\n' "$1" >&2; exit 87; }
_low(){ printf '%s' "$1" | tr 'A-Z' 'a-z'; }

# --- resolve identity (env overrides, then Maya defaults) ---
PROJECT="${PROJECT:-maya}"
LK_ROOM="${LK_ROOM:-maya-live}"
AVATAR="${AVATAR:-${1:-}}"                 # avatar id via env or first arg; may be empty for non-bake steps
BRAIN="${BRAIN:-pod/maya_rt.py}"
PERSONA="${PERSONA:-pod/maya_rt.py}"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

# --- 1) identity asserts ---
[ "$PROJECT" = "maya" ]      || _maya_fail "PROJECT is '$PROJECT' — must be 'maya'."
[ "$LK_ROOM" = "maya-live" ] || _maya_fail "LK_ROOM is '$LK_ROOM' — must be 'maya-live' (ROOM LAW)."
case "$AVATAR" in
  maya_*) : ;;
  "")     : ;;                              # empty allowed for steps that don't touch an avatar
  *)      _maya_fail "AVATAR '$AVATAR' must start with 'maya_' (bake/boot guard)." ;;
esac
case "$BRAIN" in
  *maya_rt.py) : ;;
  *)           _maya_fail "BRAIN '$BRAIN' must be maya_rt.py — rt_lk.py is Nova's brain." ;;
esac

# --- 2) no-nova assert on every identity value (case-insensitive) ---
for _v in "$PROJECT" "$LK_ROOM" "$AVATAR" "$BRAIN" "$PERSONA" "$BRANCH"; do
  case "$(_low "$_v")" in
    *nova*) _maya_fail "identity value '$_v' contains 'nova'." ;;
  esac
done

# --- 3) ENV FIREWALL: refuse to run if any NOVA_* variable is present ---
if env | grep -qiE '^NOVA_'; then
  _maya_fail "a NOVA_* env var is set: $(env | grep -iE '^NOVA_' | cut -d= -f1 | tr '\n' ' ')"
fi

# --- 4) safe-source helper: Maya scripts must use this instead of bare `source` ---
#     Refuses to source any path containing 'nova'.
maya_safe_source(){
  case "$(_low "$1")" in
    *nova*) _maya_fail "refusing to source '$1' — path contains 'nova' (env firewall)." ;;
  esac
  # shellcheck disable=SC1090
  . "$1"
}

printf '\033[42;30m  MAYA PREFLIGHT OK  \033[0m  PROJECT=%s  ROOM=%s  AVATAR=%s  BRAIN=%s  BRANCH=%s\n' \
  "$PROJECT" "$LK_ROOM" "${AVATAR:-<none>}" "$BRAIN" "$BRANCH"
