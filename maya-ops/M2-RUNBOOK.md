# M2 SELF-TEST — the run that proves the chat loop (one page)

The gate: a stranger's YouTube comment becomes her spoken, correct, Hebrew answer on the
stream in under 40 seconds, and a buyer comment becomes a row in the Leads sheet.
The recording of a passing M2 **is the client demo** — nothing to stage, nothing to fake.

## Before (once)

1. Pod up + boot (say "bring Maya up" — everything is scripted).
2. n8n W3→W2→W1 active with the LIVE pod URL in each CONFIG (say "activate" — scripted too).
3. OBS installed. Stream key already saved at `C:\Users\dsbea\.maya\youtube-stream.env`.

## OBS (once, ~5 minutes)

1. Settings → Video: Base **1920×1080**, Output **1920×1080**, FPS **30**.
2. Settings → Output: Encoder **NVENC** (fallback x264 if no NVIDIA), Bitrate **4500 Kbps**,
   Keyframe **2s**, Preset Quality.
3. Sources → **+ Browser**:
   - URL = the STAGE link I hand you at bring-up (with `&api=` and `&scene=open`)
   - Width **1920**, Height **1080**
   - ✅ **Control audio via OBS** (without it: silent stream)
   - "Shutdown source when not visible" = **OFF**
4. Audio Mixer must show level when she speaks. No level = stop, fix first.
5. Settings → Stream: **YouTube - RTMPS**, paste the stream key from the env file.

## YouTube (each test)

1. YouTube Studio → **Go live** → Streaming software (not webcam).
2. Visibility: **Unlisted**. Title: `בדיקת מערכת — מיה`. NOT made for kids.
3. Start OBS streaming → wait for YouTube preview → **Go live**.

## The 10-comment script (from a SECOND account, ~1 per 30–45s)

**Comment method (decided 2026-08-08): the founder phone-types them.** Automated posting
would need a second Google account's OAuth kept in n8n — more moving parts than typing 10
comments, and typing from a real phone is also the more honest test of the real path.

| # | type | comment |
|---|------|---------|
| 1 | product | כמה ויטמין C יש בסרום? |
| 2 | product | הקרם לילה מתאים לעור רגיש? |
| 3 | product | מה ההבדל בין הסרום לקרם? |
| 4 | price | כמה עולה הסרום? |
| 5 | price | יש הנחה אם קונים את שניהם? |
| 6 | shipping | תוך כמה זמן זה מגיע? |
| 7 | **lead** | אני רוצה את הסרום! |
| 8 | noise | חחחח |
| 9 | noise | ערב טוב לכולם 🙂 |
| 10 | noise | (any link, e.g. a URL) — must be stripped/dropped |

## PASS = all of these

- [ ] Questions 1–6: she answers **by name** ("דנה שאלה…"), in Hebrew, **≤40s** from comment
      to speech (time it — this is the number for clients; playbook target 10–40s).
- [ ] Every fact she states matches `catalog.json` — prices, sizes, shipping. One invented
      fact = FAIL (truth law).
- [ ] #7: a row appears in the Leads sheet + 🔥 LEAD toast in the director log.
- [ ] #8–10: never reach her, never spoken, no dead-air weirdness.
- [ ] The AI label is visible on the YouTube stream the whole time.
- [ ] KILL press mid-test → BRB card + silence → resume works. (Untested kill = no kill.)

Write down: median answer seconds + voice cost from director vitals. Those two numbers
price the retainer.

## FAIL = stop

Any hop broken: stop the test, keep the stream up if harmless, report which hop
(comment→W1, W1→W2, W2→server, server→her mouth, lead→sheet). No live improvising.
