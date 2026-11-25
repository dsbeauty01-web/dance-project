# HANDOFF — Nova live (Freeze v4 hybrid Ditto build), 2026-11-23

For the Nova project chat. Read with `docs/NOVA-EXPERT-MAP-2026-11-23.md` (what runs where) and
`docs/NOVA-FIX-2026-11-23b.md` (split + hearing, causes and sources). 0 pods are running.

## 1. State
| branch | sha | what |
|---|---|---|
| **`nova-go4`** | `b0e7d72` (+ this doc) | the build Refael played today. nova-go3 + split screen + hearing + whole-game recorder |
| `nova-go5-wip` | `1bbac00` | nova-go4 + `tools/voice/nova_voice_samples.py` only. The "human" redesign was stopped BEFORE any code |
| `nova-go3` | `2dfcfb8` | previous build (set `NF_GO4=0` on a nova-go4 pod to get it back) |

Flags on in the nova-go4 build (all default off in code; `tools/pod/nova_final_pod.sh` turns them on, `NF_GO4=0` / `NF_REC=false` turn them off):
page `split`, `hear`, `rec` (+ the older shoulder, warmgate, matchcut, ambstill, noblink, pipfresh, heneutral, fpsprobe) ·
brain `NOVA_HEAR=1`, `NOVA_REC=1`, `NOVA_INTRO_ANSWER=1`, `NOVA_KID_EVENTS=1` · voice `NOVA_VOICE` (default `marin`; `?voice=<name>` on the page URL overrides per visit — this already works).

## 2. What is proven, and where
| thing | proven on | not proven |
|---|---|---|
| split screen from the first second | proof pod `jzh6hgg13hqtg5` (coordinator's run) + Refael's own play | — |
| she hears and answers (intro, game gaps, ending) | same proof pod ("kid line reached the brain, intro-answer true, game answer after the hold"); Refael: "she can hear me" | a quiet room vs noise: see §5.3 |
| whole-game recorder (`play-<session>.mp4` on :8099) | pod `2r2p6rxwm1f71q`: on-pod Chrome capture → 46 pieces → h264+aac mp4 (frame: `docs/evidence/2026-11-23/recorder-pod-frame.jpg`); Refael's session `20261123102354-r6ih` was recorded (the coordinator has that mp4) | desktop Chrome/Edge only — a phone browser cannot share its tab (red "not recording") |
| no-pod conversation test | `test/hear_rig/` (real page + real brain + spoken lines) | lips, picture, a real microphone |

## 3. Launch
```
cd <nova-go4 worktree>/tools/pod && set -a; . /root/.maya/host.env; set +a
python3 nova_final_ctl.py balance
# proof pod (its own Chrome plays, results on :8099): leave NF_SKIP_A unset
NF_FLOOR=2 NF_SKIP_W=1 NF_MIN_VCPU=24 NF_VOLUME=pqbavl4mct NF_BRANCH=nova-go4 python3 nova_play.py create <40-char sha>
# play-only pod (faster, no evidence): add NF_SKIP_A=1
python3 nova_play.py mine | status <id> | terminate <id>
```
- `NF_FLOOR` = the balance floor (default $5; Refael allowed 2 today). Secure 4090, $0.89/h.
- Fast boot = volume `pqbavl4mct` (EU-RO-1 only, one pod at a time): page up ~9 min after create today.
- **Capacity:** "no longer any instances available" came back for ~4 minutes today. Retry `NF_MIN_VCPU=24`, then `16`, then `0`, every 20 s.
- **Slow host:** pod `alkbue4ll59ugx` had `apt done 124` → no Xvfb/ffmpeg → proof and recordings dead. The script now retries apt once; still read `STAGES` for `apt done 0`.
- Page `https://<pod>-8765.proxy.runpod.net/beta/freeze4?lang=en` · results `https://<pod>-8099.proxy.runpod.net/` (curl `-A 'nova-final/1.0'`): `STAGES`, `rtlk.log` (now with `[PAGE]` lines from the player's browser), `A-console.log`, `nova-final-run.mp4`, `play-<session>.mp4`.
- **Pull `rtlk.log` before terminating.** The pod's own self-stop may not fire: always terminate by id.
- **OpenAI credit:** at 10:05 UTC the brain got `insufficient_quota` and Nova was mute ("Nova did not start talking"). Topped up since. The no-pod rig spends the same credit.

## 4. Evidence kept in the repo (`/tmp` will be lost)
`docs/evidence/2026-11-23/`: `refael-live-nova-go4-rtlk.log` (his live session — the conversation starts at "browser connected", line 307) ·
`proof-pod-jzh6hgg13hqtg5-*` · `recorder-pod-frame.jpg` · `voice_A_coral.mp3`, `voice_B_sage.mp3`, `voice_now_marin.mp3` ·
`docs/nova-go4/split-*.jpg`.

## 5. Refael's verdict on the live play, and the analysis so far
"She can hear me but she starts a fixed monologue, not human-like. Slow to respond. Change her voice, upgrade her fully — she is not ready."

### 5.1 Where she is scripted (from his log)
- **Every line of the intro is a fixed sentence** the page stages and the brain repeats word for word out of band (`[SPEAK] (phase-end) …`, `conversation:"none"`): "Hi! I'm Nova, your magical AI dance teacher! Look — a magic light…" (9 s, no question, no pause for him), "Yes! The light caught it!", "Here is the game: music on, you dance…". The log marks each one `[DE-CAN] she repeated a line verbatim`.
- **The phase note tells her to be a line reader**: `[REMEMBER] [phase] … Speak only the lines you are given` (intro and ending), and the session prompt for this page is `FREEZE_RULES` ("you are ONLY the freeze-game VOICE", "never ask their name").
- **Game lines are a small canned set** from `beta/lib/brain-local.js`: "I can see you!", then **"Not even a wobble!" asked 4 times** (rounds at 93.7, 103.9, 116.0, 127.8 s) — the brain's own duplicate guard dropped the repeats (`[DE-CAN] dropped duplicate staged line`), so she said it once and was silent after.
- **Her answers to him are generic** because the reply instruction I wrote for NOVA_HEAR is itself a template ("Answer exactly what THEY said, warmly, in ONE short sentence…"): "Yes, I can hear you clearly." / "That's okay, I'm here and listening." / "No worries at all, you're doing just fine." — assistant register, never his words back, never his name (she never asks it).
- She never asks him anything, so there is no turn that is his.

### 5.2 Where the answer delay goes (his session, page clock)
| his words recognised | her voice starts | delay |
|---|---|---|
| 65.7 "What's up?" (intro) | 69.9 | **4.2 s** |
| 105.1 "What's up?" (game) | 109.4 | **4.3 s** |
| 84.1 (game, start of a round) | 86.1 | 2.1 s (a staged line, not an answer) |
From the moment he STARTS a short sentence it is 4.5-7 s. Pieces: turn end = 0.6 s of quiet (server VAD) → transcript 0.1-1.3 s (the fast REST copy often returns junk — "Gjerme" for "can you hear me" — so the slower realtime transcript decides) → the brain holds her audio until the first full sentence has passed the truth gate (~1 s) → each 0.2 s piece is converted by an ffmpeg process → face server cushion 0.4 s + Ditto 1.4 s + network. On the no-pod rig (face delay simulated at 1.8 s) the same answer takes 2.4-2.8 s, so about 1.5 s more is lost on the real pod between the brain and the browser — NOT measured piece by piece yet.
Ideas, none built: stream her answer to a child at once instead of holding the first sentence (kid replies are exempt from the truth gate for 6 s anyway); resample in-process instead of ffmpeg; start generating at end-of-speech and release only when the transcript validates; a smaller cushion for short answers. Ditto's 1.4 s is fixed.

### 5.3 A third finding: she answers things nobody said
In his session the two transcripts of the same sound disagree wildly — realtime "What's up?" vs REST "Sorry." / "对不起。"; "Noëlle." vs "Yo estoy."; "Thanks." vs "Fascinating." / "안녕하세요". That is what noise, music or her own voice from the speakers looks like. Several of her "answers" ("It's just a friendly hello before we begin.") were to those. NOVA_HEAR made her answer every validated turn, so this now shows. Not fixed. Idea: ask the transcriber for log-probabilities and drop low-confidence turns; never accept a turn whose two transcripts are in different scripts.

### 5.4 Voice
Now: `marin` (founder's choice 2026-08-08; "shimmer too adult, coral weird" on the older model). Same Nova line generated on the Realtime API (gpt-realtime-2), measured, NOT judged by ear:
| voice | median pitch | pitch movement | length of the line |
|---|---|---|---|
| marin (now) | 224 Hz | 13.1 st | 7.9 s |
| coral (sample A) | 253 Hz | 14.1 st | 9.4 s |
| sage (sample B) | 220 Hz | 11.6 st | 10.9 s |
| ballad 195 / verse 214 / shimmer 198 / alloy 190 | | | |
A/B without a new build: add `&voice=coral` or `&voice=sage` to the play link. Someone must listen.

## 6. Recommended plan (for the Nova chat, with its skills)
1. **Goals, not lines.** The page keeps owning the beats and the truth (light on, real lift seen, judge result) but sends each as a goal; the brain says it in her own words inside the conversation (not out of band), 1-2 short sentences; game reactions ≤ 6 words, reworded every time.
2. **Give him a turn at once:** "Hi! I'm Nova! What's your name?" → wait → she uses the name → then the light. (The commercial intro, 75396a4.)
3. **A short persona prompt with 4-6 example exchanges at the target length**, banned strings with replacements ("I'm here and listening", "you're doing just fine", "loud and clear", "magical AI dance teacher"), no trailing wrap-up question, his words back.
4. **Stop the phantom answers** (§5.3) before making her more talkative.
5. **Latency cuts** (§5.2), measured on a pod piece by piece first.
6. **Voice A/B** by ear with the two samples.
7. Interrupting her: the microphone is closed while she talks (anti-echo). Real barge-in needs trust in the browser's echo cancelling — test on his laptop before building.
Laws to keep: live V2V only · truth-gate · never negative · holds mute · INPUT-LOCK · everything flagged.

## 7. Money today (this agent's pods)
`alkbue4ll59ugx` ~15 min (no ffmpeg, terminated) + `2r2p6rxwm1f71q` (recorder proof, then Refael's play; closed by the coordinator). ≈ $0.45 up to the proof; the play time after it is the coordinator's count.
