#!/usr/bin/env bash
# tools/beta-init.sh — open (or re-sync) the beta track. Idempotent.
# Track first opened 2026-09-07, tag beta-b0.1 (see CHANGELOG.md).
# Real page names on this repo (spec used generic ones — GAMES-TIERED §7):
#   freeze → animal-freeze.html · upperbody → upperbody.html · upgroove → up-groove.html
#   wave → nova-wave.html · hello → nova-hello.html
# Note: the spec's sed used '#' as delimiter, which collides with the '#7c5cbf' color —
# fixed here with '|' delimiters.
set -euo pipefail
cd "$(dirname "$0")/.."

git checkout beta 2>/dev/null || { git checkout main && git pull && git checkout -b beta; }
mkdir -p beta

pairs="freeze:animal-freeze.html upperbody:upperbody.html upgroove:up-groove.html wave:nova-wave.html hello:nova-hello.html"
CHIP='<div id="betaChip" style="position:fixed;bottom:8px;left:8px;background:#7c5cbf;color:#fff;padding:2px 8px;border-radius:8px;font:600 11px Nunito;z-index:99">BETA b0.1</div></body>'
for p in $pairs; do
  g="${p%%:*}"; src="${p#*:}"
  if [ ! -f "beta/$g.html" ] && [ -f "$src" ]; then
    cp "$src" "beta/$g.html"
    sed -i "s|</body>|$CHIP|" "beta/$g.html"
    echo ">> created beta/$g.html from $src (+ BETA chip)"
  else
    echo ">> beta/$g.html already present (or no source $src) — skipped"
  fi
done
echo ">> beta track ready:"; ls beta
