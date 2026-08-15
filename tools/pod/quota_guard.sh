#!/usr/bin/env bash
# tools/pod/quota_guard.sh <payload_bytes> [volume_dir]
# DISK QUOTA GUARD (2026-08-15) — the truncated-copy killer.
# RunPod network volumes enforce a quota the MooseFS client reports as "Disk quota
# exceeded", but `df` shows the underlying cluster (petabytes) — useless. So we PROBE:
# real-write 2x the payload to the volume. If that fails, there is not enough room and
# we STOP LOUDLY with the biggest deletable items, BEFORE a bake/copy truncates to 0 bytes.
#
# Returns 0 = room to proceed, 1 = STOP (not enough space).
# Call this from the bake script itself, right before writing to the volume.
set -u
PAYLOAD="${1:?usage: quota_guard.sh <payload_bytes> [volume_dir]}"
VOL="${2:-/workspace}"
NEED=$(( PAYLOAD * 2 ))
# cap the probe at 300MB so we never write gigabytes just to test (2x of a big frame set
# is still a good-enough signal; the incremental bake write fails fast if truly full)
CAP=$(( 300 * 1024 * 1024 ))
PROBE_BYTES=$(( NEED < CAP ? NEED : CAP ))
MB=$(( PROBE_BYTES / 1048576 + 1 ))
probe="$VOL/.quota_probe.$$"

if dd if=/dev/zero of="$probe" bs=1M count="$MB" >/dev/null 2>&1 && sync 2>/dev/null; then
  actual=$(stat -c%s "$probe" 2>/dev/null || echo 0)
  rm -f "$probe"
  if [ "$actual" -ge "$(( MB * 1048576 - 4096 ))" ]; then
    echo "QUOTA-OK — room for $(( NEED/1048576 ))MB (need 2x $(( PAYLOAD/1048576 ))MB payload)"
    exit 0
  fi
fi
rm -f "$probe" 2>/dev/null
echo "════════════════════════════════════════════════════════════════"
echo "QUOTA-STOP — the volume cannot hold 2x the payload ($(( NEED/1048576 ))MB)."
echo "A bake/copy now would TRUNCATE to 0 bytes (the blank-Nova bug). Free space first."
echo "Biggest deletable items:"
{
  du -sh "$VOL"/LiveTalking/data/avatars/*.BROKEN* 2>/dev/null
  du -sh "$VOL"/*.bak-* 2>/dev/null
  du -sh "$VOL"/LiveTalking/data/avatars/nova_hype 2>/dev/null   # dead avatar per founder
  du -sh "$VOL"/* 2>/dev/null | grep -vE "/_sys|/LiveTalking"
} | sort -rh | head -5
echo "════════════════════════════════════════════════════════════════"
exit 1
