NOVA — LAUNCH PACK
==================

WHAT'S INSIDE
  nova-join.html        Main dance game (head / shoulders / hips / knee + freestyle)
  nova-wave.html        Wave game (shoulders -> elbows -> hand wave)
  nova-joined-small.mp4 Nova's dance video + music (for nova-join)
  handywave.mp4         Wave video + music (for nova-wave)
  intro-small.mp4       Cinematic intro splash
  NOVA-SPEC.md          Full system spec (brain, intro, game, detection, end, pending)
  NOVA-3-PHASES.md      Experience-arc design doc
  logserver.js          Local server that runs the game AND records sessions

HOW TO PLAY (no install beyond Node)
  1. Unzip this folder.
  2. Open a terminal in the folder and run:   node logserver.js
  3. In your browser open:   http://localhost:8787/nova-join.html
  4. Allow the camera. Stand back so your whole body is in frame. Copy the cues.
  (Needs internet: pose model + LiveKit load from CDN. Live Nova needs the worker awake.)

PLAY ONLINE (no Node)
  https://dsbeauty01-web.github.io/dance-project/nova-join.html
  https://dsbeauty01-web.github.io/dance-project/nova-wave.html
  (Online copies do NOT record sessions — only the localhost one does.)

SESSION RECORDING (for debugging detection)
  When run via logserver.js, every session is written to sessions.jsonl in this folder:
  session start, a detection snapshot every ~1.5s, every cue hit/miss, and the end summary.
  The end screen also has a "Copy debug log" button.

THE BRAIN (live Nova)
  Worker: https://novapython.onrender.com  (Render free tier; ~50s cold start).
  If it's asleep/down, the game still runs and Nova reacts locally; her live face
  appears automatically when the worker is up.

TIP: best light is FACING you (not a window behind you), and frame head-to-hips.
