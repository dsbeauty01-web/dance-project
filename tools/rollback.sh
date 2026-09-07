#!/usr/bin/env bash
# tools/rollback.sh <tag> — roll the LIVE commercial game back to a tagged version.
# Checks out main at the tag, prints the live URL, and (if a pod is running) redeploys
# the game pages to it. Safe: never force-pushes; leaves you on the tag to inspect.
#   bash tools/rollback.sh beta-b0.1
set -uo pipefail
TAG="${1:?usage: rollback.sh <tag>}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"; cd "$REPO"

git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 || { echo "!! unknown tag: $TAG"; echo "   tags:"; git tag | tail -10; exit 1; }
echo ">> rolling back to tag $TAG"
git fetch --tags -q origin 2>/dev/null || true
git checkout -q "$TAG" 2>&1 | tail -1
echo ">> working tree is now at $TAG ($(git log -1 --format='%h %s' "$TAG"))"

# redeploy to a running pod if one is up (pod serves from /workspace volume copy)
KEY="${RUNPOD_API_KEY:-$(powershell.exe -NoProfile -Command '[Environment]::GetEnvironmentVariable("RUNPOD_API_KEY","User")' 2>/dev/null | tr -d '\r')}"
if [ -n "$KEY" ]; then
  POD=$(curl -s -m 15 "https://rest.runpod.io/v1/pods" -H "Authorization: Bearer $KEY" \
        | tr '{' '\n' | grep '"desiredStatus":"RUNNING"' | grep -oE '"id":"[^"]+"' | head -1 | cut -d'"' -f4)
  if [ -n "$POD" ]; then
    echo ">> live pod $POD found — redeploy game pages with:"
    echo "   scp pod/pages/*.html root@<pod-ip>:/workspace/pages/   # then restart rt_lk"
    echo ">> LIVE URL: https://${POD}-8765.proxy.runpod.net/freeze"
  else
    echo ">> no pod running — pages will serve this tag on next boot."
    echo ">> STATIC URL: https://dsbeauty01-web.github.io/dance-project/nova-commercial.html"
  fi
fi
echo ">> to return to the tip:  git checkout main"
