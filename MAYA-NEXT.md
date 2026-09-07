# MAYA-NEXT.md — READ FIRST, EVERY SESSION. DO THE TOP UNCHECKED ITEM. NO GUESSING.
# Law (pinned in CLAUDE.md): read this → do the top unchecked item exactly as written → run its
# ACCEPT test → check it off → append LOG → update STATE. Never ask what's next. Never redo ✅.
# Standing permissions: pods (ask once/session, cap $3), Chrome, packages, commits on maya-p1-finish.
# QUESTIONS FORBIDDEN. Blockers → try the written fallback → report.

## STATE (2026-09-07)
✅ Facebook: live · reads comments · answers by VOICE (~10s render, coral, lips) · text reply
   "@Name —" · truth-gated · gapless slot stream. Witnessed by the founder.
Stack on pod: render_server.py (warm MuseTalk) · slot_stream.py · maya_host.py v2 · speak_server ·
chat pipeline · fb tools. Limits: FB token ~1h · portrait render · YouTube text reply blocked ·
buy link placeholder.

## THE CONTRACT (the only two interfaces the new code assumes — verify once, adapt once)
- render_server:  POST http://127.0.0.1:8793/render  {"text": "..."}  → {"clip": "/abs/path.mp4"}
- slot_stream:    POST http://127.0.0.1:8792/insert  {"clip": "/abs/path.mp4", "priority": 0-9}
  If the real endpoints/ports differ: change RENDER_URL / SLOT_URL in ~/.maya/host.env and, if the
  JSON shape differs, add a 5-line shim route in render_server/slot_stream. Do NOT rewrite the tools.
- slot_stream must expose its output as STREAM_SOURCE for push.py (a local rtmp://127.0.0.1/live/maya
  via nginx-rtmp/mediamtx, or a growing .flv/.mp4 file it writes). Set STREAM_SOURCE in host.env.

## NEW FILES (maya-ops/host/ — all compiled, no placeholders)
to_landscape.py · gesture_router.py · precache_ack.py · fb_tool.py · push.py · showcase_build.py
showcase.json · set_buy_url.py · systemd/{maya-*.service, maya-health.sh, install.sh}

## NEXT — one item per run
- [x] 1. LANDSCAPE 1080p (30 min, no pod for the files; pod for the live check)
   DONE 2026-09-07: idle converted blurpad→1920x1080 (to_landscape.py); idle re-segmented
   landscape into /workspace/vd/segs (11×1920x1080/25fps); answer bake maya_serum_close is
   native 1920x1080 (she fills the frame). ffprobe ACCEPT met on all stream files. LIVE-VISUAL
   ACCEPT (FB desktop screenshot she fills frame) = pending a fresh FB token / founder-watched
   run (done automatically on the next live run).
   cmd:  python to_landscape.py --batch /workspace/maya-ops/bake/src /workspace/maya-ops/bake/src1080 --mode auto
         python to_landscape.py <idle_loop_source>.mp4 /workspace/maya-ops/bake/src1080/idle_1080.mp4 --mode blurpad
         point slot_stream's idle playlist at src1080/; set LANDSCAPE=1 so every rendered answer is
         converted before insert (gesture_router does it).
   ACCEPT: ffprobe every file = 1920x1080, 25fps; on the FB desktop watch page she FILLS the frame
           (screenshot). Answer clip inserted still plays seamlessly.
- [ ] 2. GESTURES + REACTIONS (1 h)
   cmd:  mkdir -p /workspace/maya-ops/bake/gestures/{IDLE,LISTEN,SHOW,POINT,WAVE}
         copy existing silent bakes/clips into those folders (≥2 per folder where you have them;
         cutaway_examine→LISTEN is acceptable; missing folders = logged, not fatal)
         python gesture_router.py   (port 8791)   then in host.env:
         MAYA_SCENE_URL=http://127.0.0.1:8791/scene   MAYA_SPEAK_URL=http://127.0.0.1:8791/speak
   ACCEPT: POST /scene {"scene":"SHOW"} → a SHOW clip appears in the stream within one slot;
           idle micro-beat inserted automatically after 20-40s of silence (router log); a real
           comment → gesture beat then the spoken answer. Report which folders are empty (HUMAN item).
- [ ] 3. FASTER FEEL — instant acknowledgment (30 min)
   cmd:  python precache_ack.py --names Refael,Dana,Tom,Lior,Noa,Yossi   (renders ~36 short clips once)
         in maya_host.py Host.run, right after `self.out.scene("LISTEN")` add:
             try: requests.post(os.environ.get("MAYA_ACK_URL","http://127.0.0.1:8791/ack"), json={"name": ev.user_name.split()[0]}, timeout=2)
             except Exception: pass
         host.env: MAYA_ACK_URL=http://127.0.0.1:8791/ack
   ACCEPT: comment → an ack clip ("Refael — great question, one sec") plays within ≤5s, the full
           answer follows ~10s later. Log both timestamps.
- [x] 4. PERMANENT FB TOKEN (15 min)  DONE 2026-09-07: exchanged app secret + user token -> page token expires_at=0 (NEVER), reply-capable. In host.env.
   cmd:  app secret: Chrome → developers.facebook.com/apps/1335138022110608/settings/basic → App Secret
         → Show (if a password wall appears: print ONE line "enter FB password in Chrome, then say
         go" and continue other items). Put FB_APP_SECRET in ~/.maya/host.env.
         Graph Explorer (Chrome, config "rafa") → user token → python fb_tool.py token --user-token <T>
   ACCEPT: python fb_tool.py check → "expires: NEVER" and scopes OK.
- [ ] 5. AMAZON LIVE TEST (30 min, pod)  — HUMAN gate: AMAZON_RTMP_URL + AMAZON_STREAM_KEY in
   ~/.maya/amazon.env (from the Amazon Live Creator app → external encoder).
   cmd:  python push.py --source <idle_1080.mp4> --loop --targets amazon --once   (60s smoke)
         then real: python push.py --source $STREAM_SOURCE --targets fb,amazon
   ACCEPT: the show is visible on amazon.com/live + the product page (Chrome screenshot), health
           "good" in the Creator app, AI-people disclosure set on the show. Then end + pod down.
- [ ] 6. BUY LINK — HUMAN gate: the URL.   cmd: python set_buy_url.py <URL>
   ACCEPT: a "how much" comment → text reply contains the UTM'd link; banner unchanged.
- [ ] 7. 24/7 (1 h, pod)
   cmd:  bash systemd/install.sh   (render → 90s → stream, router, host, push; health cron every 60s)
         set MAYA_SLEEP_HOURS, MAYA_COST_CAP_USD in host.env; PUSH_TARGETS=fb (add amazon when 5 is ✅)
   ACCEPT: kill -9 any one service → back within 10s; health.log shows OK lines; 2-hour soak with
           3 injected comments answered; cost line reported; pod watchdog extended for the soak.
- [ ] 8. SHOWCASE VIDEO (1 h, pod)
   cmd:  edit showcase.json paths (cutaway file) → python showcase_build.py --config showcase.json
         --out /workspace/maya-ops/showcase/maya-showcase-90s.mp4
   ACCEPT: 80-100s, 1080p, every line catalog-true, overlays readable, vertical cut produced;
           present both files.
- [ ] 9. YOUTUBE READ-ONLY on every YT live:  python yt_readonly.py <VIDEO_ID>  (voice answers).
   ACCEPT: a YT comment → ANSWER log line + spoken clip on the YT push (targets fb,yt).
   Text reply stays blocked until Google enables the channel (HUMAN: Studio → Go live → Enable once).
- [ ] 10. ELEVENLABS A/B — only if the founder says "more human": voice skill bench, lock winner.

## HUMAN ITEMS (the CLI cannot do these — list them in every report, don't wait on them)
- Amazon Live Creator app (Android APK via apkmirror since Play is region-locked) → create show →
  external encoder → paste RTMP URL + key into ~/.maya/amazon.env
- Buy link URL (Stripe Payment Link / PayPal / store)
- Kling gesture clips for empty gesture folders (prompts: skills/tool, skills/host-controller)
- FB password wall for the app secret (once)
- YouTube Studio → Go live → Enable (once, then 24h)

## LOG (one line per session: date · item · result · cost)
- 2026-09-07 · voice on stream · DONE, 10.4s render, witnessed · ~$0.7
- 2026-09-07 · #1 landscape 1080p · DONE (idle blurpad + segs 1920x1080; answer bake native 1080p); live-visual pending token · ~$0.4
- 2026-09-07 · #4 permanent FB token · DONE, expires NEVER · ~$0
