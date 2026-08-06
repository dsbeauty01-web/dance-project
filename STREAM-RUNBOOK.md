# STREAM RUNBOOK — from cold pod to live stream

Everything needed to go on air, in order. Nothing here is guesswork: every command is one
that has actually run on this stack.

---

## PRE-FLIGHT (do all seven, in order — none takes more than a minute)

| # | check | how | must see |
|---|---|---|---|
| 1 | Pod is running | RunPod console, or ask the CLI | status RUNNING |
| 2 | Self-stop armed | `pgrep -f maya-watchdog.sh` on the pod | a pid |
| 3 | Engine loaded on a **maya_** bake | `tail /root/app.log` | `avatar_id='maya_idle'` |
| 4 | Bridge publishing | `tail /root/bridge.log` | `video track published 1080x1920` |
| 5 | Brain answering | open `https://<pod>-8765.proxy.runpod.net/health` | `{"ok": true …}` |
| 6 | Switchboard answering | `http://localhost:8000/health` | `{"ok": true …}` |
| 7 | Contract test green | `node tools/qa-maya-backend.mjs http://localhost:8000` | `22 passed, 0 failed` |

**Cold-start facts learned the hard way (2026-08-06, first fresh-pod boot):**
- A fresh pod must be created with `env: {PUBLIC_KEY: "<ssh pubkey>"}` or SSH is impossible.
- `/workspace/maya-boot.sh` now installs its own deps and boots ENGINE → BRIDGE → BRAIN →
  SWITCHBOARD in tmux sessions (`mayaengine`/`mayabridge`/`mayabrain`/`mayaserver`).
  It was rewritten after the old order (bridge first) crashed the bridge: it sat idle
  through the engine's 25-minute cold load, its LiveKit connection died, and it fell over
  the moment the engine connected. Old version kept at `maya-boot.sh.bak-2026-08-06`.
- The money-guard watchdog has the pod id HARDCODED — rewrite `/root/maya-watchdog.sh`
  for every new pod or it silently stops nothing.
- Echo on the stream = Maya open in two tabs. Every open stage/pod page is a full session
  with its own voice. Exactly ONE live tab, always.
- After running the QA suite, `POST /session/start {"answer_mode":"approve"}` — the tests
  leave the switchboard in auto mode with a test product active.

**Kill-switch test before every stream.** Open the director, press KILL, confirm the BRB
card appears and she goes silent, press it again to resume. An untested kill switch is
not a kill switch — and it is the only thing standing between a bad moment and a client's
audience.

---

## THE CHAIN

```
maya-stage.html in Chrome  →  OBS Browser Source  →  RTMP  →  YouTube / Instagram
```

Browser Source, **not** screen capture: no cursor, no window borders, no notifications,
and the audio comes with it.

---

## OBS SETUP (once)

**Landscape (YouTube), the default:**

1. Settings → Video → Base and Output resolution **1920×1080**, FPS **30**.
2. Sources → **+ Browser**
   - URL: the stage URL from `STATUS.md` (with `?saray=…&api=…&scene=open`)
   - Width **1920**, Height **1080**
   - ✅ **Control audio via OBS** ← without this you stream a silent Maya
   - ✅ Shutdown source when not visible → **OFF** (it would drop her session on scene change)
3. Audio Mixer → the browser source should show level when she speaks. If it does not,
   nothing else matters — fix it before going further.
4. Settings → Stream → Service **YouTube - RTMPS**, paste the stream key.

**Vertical (Instagram / TikTok):**

1. Settings → Video → Base and Output **1080×1920**.
2. Same Browser Source, but Width **1080**, Height **1920**, and add
   **`&layout=vertical`** to the stage URL. She goes full-frame and the product becomes a
   lower-third card.
3. Instagram: instagram.com/live/producer → copy RTMP URL + key into OBS. No follower
   gate, this is the official path.

**One OBS profile per orientation.** Switching resolutions inside one profile is how you
end up streaming a 9:16 page into a 16:9 canvas with black bars on a client's feed.

---

## GOING LIVE (every time)

1. Start the pod, run `bash /workspace/maya-boot.sh`, wait for `MAYA_BRAIN_UP`.
2. Start the switchboard and the page server (see `STATUS.md` §7).
3. Run pre-flight above. **Do not skip step 7.**
4. Open the **stage** page. Click into it once — the pod page needs one click to start
   audio and the microphone. Wait until you see her, not the "מתחברת…" card.
5. Open the **director** in a second window. Confirm Stage says *connected*.
6. Set answer mode: **approve** for anything client-facing, **auto** only once you trust
   the filter on that stream.
7. Say one Hebrew line through SAY and watch the stream, not the page — that confirms the
   whole chain including RTMP.
8. Go live.

---

## THE M2 SELF-TEST (the gate that proves the chat loop)

1. YouTube → Go Live → **Unlisted**. OBS streams the stage.
2. n8n W1/W2/W3 active (see `n8n/README.md`).
3. From a **second account**, comment a product question.
4. Watch the stream and time it: comment → her spoken answer. **Target under 8 seconds**,
   RTMP delay included.
5. From the second account, comment "אני רוצה" → a row must appear in the Leads sheet and
   a 🔥 LEAD line in the director log.
6. Note the voice cost from the director vitals. **That number is what you quote a client
   against** — do not price a retainer before you have it.

Pass = M2 done, and the recording of that same session is the demo you show clients.

---

## WHEN SOMETHING BREAKS, MID-STREAM

| symptom | first move |
|---|---|
| She stops speaking | Director log — a 409 means the stage socket dropped. Reload the stage page; her session lives in it. |
| Wrong face / wrong size | The engine loaded a `nova_*` bake. Never mix families: restart the engine with `--avatar_id maya_idle`. |
| She says something wrong about a product | KILL, fix the row in `catalog.json`, `POST /catalog/reload`, resume. The catalog is the only thing she is allowed to state. |
| Chat flood | Answer mode → **approve**. You become the filter. |
| Audio on stream but not lip-synced | The bridge lost the engine — `tail /root/bridge.log` for `BRIDGE_DROP`, then re-run `maya-boot.sh`. |
| Everything is wrong | KILL. The BRB card is a complete, honest cover. Fix off-air. |

---

## AFTER THE STREAM

1. Director → session end (or `POST /session/end`) → writes
   `maya-server/reports/session-report-<id>.json`: messages in/answered, median answer
   latency, leads, questions per product, claim alerts.
2. **Stop the pod.** `curl -X POST https://rest.runpod.io/v1/pods/<id>/stop -H "Authorization: Bearer $(cat /root/.rpkey)"`
   — the REST endpoint, not `runpodctl` (it needs its own auth and has silently failed,
   costing ~4 idle hours once).
3. That report is what the monthly retainer is renewed on. Keep every one.
