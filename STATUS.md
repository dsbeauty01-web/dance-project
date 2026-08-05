# MAYA — STATUS

**Written:** 2026-08-05, 12:10 UTC · **Branch:** `maya-p0` · **Pod:** `tn2wyavs39v9s9`

---

## THE SHORT VERSION

She is alive, she speaks Hebrew, she gestures on her own words, and the operator
console now actually drives her. Phase 2 (the switchboard + the chat layer) is built
and tested. Three bugs that would have ruined a client demo are fixed.

**One thing is still unverified and only you can do it: talking to her by voice.**

---

## 1. WHAT IS RUNNING RIGHT NOW

| piece | where | state |
|---|---|---|
| Avatar engine (her face/body) | pod, port 8010 | running, loaded on `maya_idle` |
| Bridge (video to LiveKit) | pod | publishing 1080×1920 into room `maya-live` |
| Brain (her voice + mind) | pod, port 8765 | running, Hebrew, zero errors |
| Switchboard (`maya-server`) | pod, port 8000 | running, catalog loaded |
| Web pages | your laptop, port 8088 | serving |
| Tunnel laptop → pod backend | your laptop | running, reconnects itself |

**The pod stops itself at 15:23 UTC** to protect your money ($0.74/hour). That is
deliberate. Section 7 says how to bring it back.

### Your two links

Director (the console you drive her from):
```
http://localhost:8088/maya-director.html?saray=https://tn2wyavs39v9s9-8765.proxy.runpod.net/&api=http://localhost:8000
```

Stage (the page OBS captures — this one IS the stream):
```
http://localhost:8088/maya-stage.html?saray=https://tn2wyavs39v9s9-8765.proxy.runpod.net/&api=http://localhost:8000&scene=open
```

Remove `&api=...` from both and you get the simpler Phase-1 setup, which still works.

---

## 2. WHY YOU COULDN'T DRIVE HER THIS MORNING

Three faults, all in the same file, all invisible — nothing errored, nothing logged.

**1. She never heard the console.** The page in the middle only understood Nova's old
message names. Everything the director sent — SAY, scenes, chat, and **her entire
personality** — was thrown in the bin on the way through. She talked using her own
built-in prompt because that was the only instruction that ever reached her. The
contract document predicted this exact failure in bold, and it happened anyway.

**2. Her gestures never arrived.** The brain sent "wave now" at the right moment and
the page dropped it. The whole gesture system existed on both ends with nothing
joining them.

**3. Clicking start loaded Nova's avatar onto Maya's stream.** Wrong face, wrong
resolution, on what is supposed to be a client's broadcast.

All three fixed.

---

## 3. THE THREE BUGS THE TESTS CAUGHT AFTERWARDS

These were found by machine, before you ever saw them.

**She was reading her stage directions out loud.** She had been *asked* to end lines
with `[WAVE]` and merely *told* not to say it. Telling is not a mechanism — she said
it. She is no longer asked to write tags at all: her gestures are now matched from her
own words as she speaks ("שלום" → wave, "149 שקל" → reveal, "מהרו" → nudge), still
landing exactly when the voice starts.

**"She is on auto talk" — that was Nova's babysitter.** Nova gently nudges a child who
has gone quiet for 13 seconds. On a live broadcast with nobody speaking to her, that
made Maya talk to herself every 13 seconds. Worse, the nudge carried no identity, so
the test caught her saying, out loud, in **Spanish**, a line from the kids' game:
*"Hola, ¿cómo estás? ¿Te gustaría contarme algo o moverte un poquito?"* Off now.

**SAY wasn't wrong — it was silent.** A line you typed while she was talking was
discarded with no speech and no error. You press SAY, nothing happens, forever. Now
your line outranks whatever she is improvising: she is cut off and says yours
immediately. Tested with a real Hebrew sentence — it came back word for word.

---

## 4. WHAT WAS BUILT (PHASE 2)

**`maya-server`** — the switchboard between you, the chat, and her. It owns:

- the **product catalog** (`maya-server/catalog.json`) — the only place her facts come
  from, so the price on screen can never differ from the price she is allowed to say;
- the **chat queue** with three modes: *approve* (you release each message — the
  default for a pilot), *auto* (she answers everything the filter passed), *manual*
  (you write the answer, she voices it);
- **moderation** — abuse never reaches her or the on-screen chat; regulated words
  ("clinically proven", "מרפא") raise an alert if she ever says one;
- **leads** and an **end-of-stream report** with honest blanks where a number isn't
  really measured, rather than invented figures a client would trust.

It deliberately never opens its own line to her brain — that would put two voices on
one stream. Everything routes through the stage page, which holds the single session.

**n8n workflows** (`n8n/`, ready to import): YouTube chat in → filter, classify,
prioritise, de-duplicate → her; buy-intent → Google Sheet + a 🔥 LEAD alert on your
console. Instructions in `n8n/README.md`.

---

## 4b. ALSO BUILT (Phase 3 pieces that needed nothing from you)

- **`STREAM-RUNBOOK.md`** — cold pod to live stream: seven pre-flight checks, the OBS
  setup for both orientations, the going-live order, the M2 self-test procedure, and a
  what-to-do-when-it-breaks table for mid-stream. Read this before the first client.
- **Vertical layout for Instagram/TikTok** — add `&layout=vertical` to the stage URL and
  set the OBS canvas to 1080×1920. She goes full-frame, the product becomes a
  lower-third card, chat overlays above it. Same page, same everything else.
- **Catalog sync from a Google Sheet** (`n8n/W5-catalog-sync.json`) — the client edits
  their own sheet, her products update live, no restart. It **refuses** an empty or
  broken sheet rather than accepting it: an emptied catalog would leave her with no
  facts at all, answering "I'll check that" to every question for the rest of a stream.
- **RTMP delay bridge lines** — the stream is 3–10 seconds behind the viewer on every
  platform, so she now says "רגע, רואה את השאלה של דנה..." while picking up a question.
  Eight seconds of silence reads as broken; a host acknowledging you reads as live.

## 5. THE TESTS

Three harnesses, all passing, all runnable before a stream:

```
node tools/qa-maya-backend.mjs http://localhost:8000     27 passed   (switchboard, no pod needed)
node tools/qa-maya-brain.mjs   wss://<pod>-8765.../rt    11 passed   (real session, costs a few cents)
python3 tools/qa-maya-gestures.py                        21 passed   (gestures + tag leak)
bash tools/laws/run-all.sh                               GREEN       (all project laws)
```

The brain test judges what she **actually says**. It found two of the three bugs in
section 3 on its first run.

---

## 6. STILL OPEN

**Needs you:**

1. **Talking to her by voice.** My tests send text, not audio. The microphone path is
   the one thing I cannot verify from here — and it is exactly what you noticed. Ten
   minutes with the director open.
2. **A decision on the pod.** Cloud n8n cannot reach the switchboard: it lives on the
   pod behind a tunnel to your laptop. RunPod fixes ports when a pod is created, so
   the YouTube chat test needs a fresh pod with port 8000 opened. Say when.
3. **The three leaked keys** — still un-rotated, still in plain text in
   `/workspace/boot.sh` on a volume any pod can read. This is what formally blocks
   GATE 0. Rotate them, then they go in `/workspace/.env`.
4. **Nothing is on GitHub.** 29 commits sit only on this laptop. The push needs you to
   type your credentials:
   ```
   ! git -C C:\Users\dsbea\repos\dance-project push -u origin maya-p0
   ```

**Known and deliberate:**

- Another CLI session is working in this same repo on Nova (`pod-registry.js`,
  `animal-freeze.html`, `pod/rt_lk.py`). I have not touched those files.
- She is in Romania, you are in Israel. The stack is fast (63–66 fps against a
  requirement of 25); the lag you feel is the distance. Moving her means copying the
  volume, and it should be decided before the first paying client.

---

## 7. HOW TO BRING HER BACK AFTER THE POD STOPS

Ask me — it is four steps and I have them scripted. For the record, they are:

1. Start pod `tn2wyavs39v9s9` (or create a new one on volume `1ditrne6cb`, Secure
   4090, EU-RO-1, ports 8765 + 8010 + 22).
2. On the pod: `bash /workspace/maya-boot.sh` — engine, bridge, brain, in that order.
3. Start the switchboard: `cd /workspace/maya-server && python3 app.py`.
4. On the laptop: the page server on 8088 and the tunnel on 8000.

A fresh pod ships with **nothing** — ffmpeg, tmux, flask all have to be installed
first. That is normal and it is in the boot script.

---

## 8. MONEY

- Pod: **$0.74/hour**, with a 3-hour self-stop armed every time it starts.
- Today: roughly 3 pod-hours across the whole session.
- Her voice (OpenAI): a few cents of testing. The real per-hour figure gets measured
  in the YouTube test — that is the number you need before quoting a retainer.
