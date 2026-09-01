#!/usr/bin/env node
/* MACHINE-CERTIFY test/encode_cert.js — turn a --record session dir into the delivery mp4.
   Video: frames/*.jpg with epoch timestamps (recmeta.json) -> concat demuxer, real durations.
   Audio: audio.webm (opus, epoch-stamped start) aligned to the first frame.
   Usage: node test/encode_cert.js <sessionDir> <out.mp4> */
'use strict';
const fs = require('fs'), path = require('path'), { spawnSync } = require('child_process');

const DIR = process.argv[2], OUTMP4 = process.argv[3];
if (!DIR || !OUTMP4) { console.error('usage: node test/encode_cert.js <sessionDir> <out.mp4>'); process.exit(1); }
const meta = JSON.parse(fs.readFileSync(path.join(DIR, 'recmeta.json'), 'utf8'));
const frames = meta.frames;
if (!frames || frames.length < 10) { console.error('too few frames: ' + (frames ? frames.length : 0)); process.exit(1); }

/* concat list with per-frame durations (timestamps are epoch seconds) */
const lines = [];
for (let i = 0; i < frames.length; i++) {
  const f = frames[i];
  const dur = i + 1 < frames.length ? Math.max(0.01, frames[i + 1].ts - f.ts) : 0.2;
  lines.push(`file 'frames/f${String(f.n).padStart(6, '0')}.jpg'`);
  lines.push(`duration ${dur.toFixed(4)}`);
}
lines.push(`file 'frames/f${String(frames[frames.length - 1].n).padStart(6, '0')}.jpg'`);
fs.writeFileSync(path.join(DIR, 'concat.txt'), lines.join('\n'));

/* audio/video alignment: positive skew = audio started BEFORE the first frame -> trim it */
const skew = frames[0].ts - meta.audioStartEpoch / 1000;
const audioArgs = skew >= 0
  ? ['-ss', skew.toFixed(3), '-i', 'audio.webm']
  : ['-itsoffset', (-skew).toFixed(3), '-i', 'audio.webm'];
console.log(`frames=${frames.length} span=${(frames[frames.length - 1].ts - frames[0].ts).toFixed(1)}s audioSkew=${skew.toFixed(3)}s`);

const r = spawnSync('ffmpeg', [
  '-y', '-f', 'concat', '-safe', '0', '-i', 'concat.txt',
  ...audioArgs,
  '-fps_mode', 'vfr', '-pix_fmt', 'yuv420p',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '21',
  '-c:a', 'aac', '-b:a', '128k', '-shortest',
  path.resolve(OUTMP4),
], { cwd: DIR, stdio: ['ignore', 'pipe', 'pipe'] });
const err = r.stderr ? r.stderr.toString() : '';
if (r.status !== 0) { console.error('FFMPEG FAILED\n' + err.slice(-1500)); process.exit(1); }
console.log('WROTE ' + OUTMP4 + ' (' + Math.round(fs.statSync(OUTMP4).size / 1024 / 1024 * 10) / 10 + ' MB)');
