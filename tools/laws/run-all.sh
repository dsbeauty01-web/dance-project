#!/usr/bin/env bash
# tools/laws/run-all.sh — run every Nova law-test, print PASS/FAIL/LOST per law,
# exit non-zero if any ACTIVE law is violated (that is the RED build / the wall).
# Known-LOST laws are reported loudly but do not fail the build until the founder
# restores them and flips their status to 'active'.
#
# Usage:  bash tools/laws/run-all.sh
set -u
cd "$(dirname "$0")"

fails=0
lost=0
passed=0

echo "──────────────────────────────────────────────────────────────"
echo " NOVA LAW-TESTS  —  fixes are walls, not requests"
echo "──────────────────────────────────────────────────────────────"

for f in law-*.js; do
  out="$(node "$f" 2>&1)"
  code=$?
  echo "$out"
  if [ $code -ne 0 ]; then
    fails=$((fails+1))
  elif echo "$out" | grep -q '^LOST'; then
    lost=$((lost+1))
  else
    passed=$((passed+1))
  fi
done

echo "──────────────────────────────────────────────────────────────"
# Syntax guard — inline <script> blocks + shared JS must compile.
if node check-syntax.js; then :; else fails=$((fails+1)); fi
echo "──────────────────────────────────────────────────────────────"
# LAWS.md ↔ codebase consistency gate (every ACTIVE marker must still exist).
echo " Marker registry check (LAWS.md ↔ code):"
if node check-markers.js; then :; else fails=$((fails+1)); fi
echo "──────────────────────────────────────────────────────────────"

echo " SUMMARY: ${passed} passing · ${lost} known-lost (awaiting restore) · ${fails} FAILING"
if [ $fails -gt 0 ]; then
  echo " RESULT:  ❌ RED — an ACTIVE law was violated. The push is rejected."
  echo "          Restore the law (never delete its test). See LAWS.md."
  exit 1
fi
echo " RESULT:  ✅ GREEN — all active laws hold."
[ $lost -gt 0 ] && echo "          (${lost} law(s) known-lost — see GUARDIAN-REPORT.md red-list.)"
exit 0
