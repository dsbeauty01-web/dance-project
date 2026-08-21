#!/bin/bash
# usage: tools/lock.sh <name> "<what is locked>"   — run ONLY on founder's word "LOCKED"
set -e
NAME="$1"; DESC="$2"; DATE=$(date +%Y-%m-%d)
[ -z "$NAME" ] && { echo "usage: lock.sh <name> \"<desc>\""; exit 1; }
TAG="locked/${NAME}-${DATE}"
git tag -a "$TAG" -m "LOCKED: ${DESC}"
git push origin "$TAG"
echo "| ${DATE} | ${TAG} | ${DESC} |" >> LOCKS.md
git add LOCKS.md && git commit -m "lock: ${TAG}" && git push
echo "LOCKED as ${TAG} — rollback forever available: git checkout ${TAG}"
