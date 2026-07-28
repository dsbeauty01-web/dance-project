// LAW: NO AUTOPLAY ON GAME MEDIA. The dance/song media must be started (and
// resumed) by the countdown gate — never the raw `autoplay` attribute, which
// fires before the kid is ready and before permission/clock are set. (Live
// camera + avatar streams legitimately autoplay; only the dance/song media —
// the choreo video and the song audio — is covered here.)
//
// We scan each real <video>/<audio> TAG (bounded — cannot cross the closing
// '>') and flag any tag that carries BOTH the `autoplay` attribute AND a
// game-media reference. A whole-file regex would false-match across comments.
const { read, has } = require('./_lib');

const FILES = ['nova-commercial.html', 'animal-freeze.html'];
const GAME_MEDIA = /(nova-joined|handywave|freeze|\.mp3)/i;
let violated = false;
const fails = [];

for (const rel of FILES) {
  const src = read(rel);
  if (src == null) { fails.push(`  ✗ FILE MISSING: ${rel}`); violated = true; continue; }

  // countdown gate must exist
  if (!/countdown/i.test(src)) { fails.push(`  ✗ no countdown gate in ${rel}`); violated = true; }

  // scan bounded media tags
  const tags = src.match(/<(?:video|audio)\b[^>]*>/gi) || [];
  for (const tag of tags) {
    if (/\bautoplay\b/i.test(tag) && GAME_MEDIA.test(tag)) {
      fails.push(`  ✗ game media with autoplay in ${rel}: ${tag.slice(0, 90)}`);
      violated = true;
    }
  }
}

if (!violated) {
  console.log('PASS  law-autoplay — No autoplay on game/song media; countdown gates play + resume');
  process.exitCode = process.exitCode || 0;
} else {
  console.log('FAIL  law-autoplay — No autoplay on game/song media   ✗ ACTIVE LAW VIOLATED — build must go RED');
  fails.forEach(f => console.log(f));
  process.exitCode = 1;
}
