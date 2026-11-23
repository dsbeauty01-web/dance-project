# NOVA expert map (2026-11-23) — what runs where, for the next session

## Branches
| branch / tag | what |
|---|---|
| `main` (v1.0.x … v1.3, bd63370) | the commercial game, FROZEN. `nova-commercial.html` = INTRO-V2V (75396a4, v1.0.4): greet + name → real chat → page arms the shoulder light → Freeze. MuseTalk lips. |
| `beta` | game work; `nova-final` merged (Ditto wide talk + SoulX PiP, all kit games) |
| `nova-play-fix` → `nova-audit` → `nova-go` (+`nova-fastboot`) → `nova-go2` → `nova-go3` (2dfcfb8) | the hybrid commercial Ditto build of Freeze v4, each step flagged |
| **`nova-go4`** | nova-go3 + split screen + hearing (docs/NOVA-FIX-2026-11-23b.md). Live build candidate once a pod proof passes |

## What runs where (one pod, Secure 4090)
| piece | file | port |
|---|---|---|
| page | `beta/freeze4.html` + `beta/freeze4-flags.js` (flags; the pod overwrites it) + `beta/lib/*` + `shared/*` | served by the brain, :8765 `/beta/freeze4?lang=en` |
| brain | `pod/rt_lk.py` — OpenAI Realtime V2V, INPUT-LOCK, speak-gate, PRODUCER-SILENT verbs | :8765 (`/rt` websocket, `/token`) |
| face server | `tools/pod/nova_face.py` `FACE_RENDERER=dual`: Ditto wide body (`nova-wide-video`) / SoulX face (`nova-face-video`) + her voice, LiveKit identity `nova-face` | :8010 (`/humanaudio`, `/face_mode`) |
| Ditto | maya-lt `ditto_server.py`, body `tools/pod/assets/nova_talk_calm.mp4` | :8031 |
| boot | `tools/pod/nova_play.py create <sha>` → `nova_final_ctl.py` → `nova_final_pod.sh` (+`nova_fastboot.sh`, volume `pqbavl4mct`) | results :8099 |
| proof | `tools/pod/nova_final_proof.py` (+`freeze4_proof.py`): Chrome on the pod, recorded child, spoken lines | |
| no-pod proof of hearing | `test/hear_rig/` | |

## The voice loop, end to end
1. Play tap → (flag hear) `primeAudio()` → camera+microphone permission → that microphone track goes to the bridge.
2. `shared/nova-bridge.js startMic`: ScriptProcessor 4096 → 24 kHz PCM16 → `{type:'audio'}` on `/rt`. Held back while the
   brain says she speaks (`status.speaking`) and while her voice is audible in the browser (`echoGuard`).
3. Brain: discards mic while `speaking["v"]`; live mic gain; `input_audio_buffer.append` → OpenAI server VAD (0.35, 600 ms,
   `create_response:false`) → `speech_started` → page `nova:hearing`; transcript race (realtime vs REST) →
   `kid_transcript` = INPUT-LOCK validation (≥ 2 words / listed single words) → `you_text` to the page →
   ONE response (`speak_now`). Game phase (speak-gate on): stored, no reply — unless `NOVA_HEAR` and he spoke to her.
4. Her audio is buffered until its transcript clears the truth gates, then goes whole to the face server
   (`/humanaudio`); Ditto delays voice+lips ~1.8 s; LiveKit → browser. Mic gate reopens 0.6 s after the brain's last chunk.
5. Page lines: `note('say exactly: …')` → `nova-say` → exact line out-of-band. Intro/ending need a boundary
   (`routeVoice('engine')` = speak_gate off); game = one air credit per gap; holds = hard mute.

## Phase machine (page `setVoice` → `routeVoice` → brain speak_gate → face `/face_mode`)
intro/ending = `engine` = wide Ditto body · game = `air` = her clips + SoulX PiP · hold = `mute`.

## Camera / layout
`#stage` flex: `#novaSide` 50 % (her pane: `#novaAmb` blurred room, `#nova` clips, `#novaWide` live body, PiP) + `#camPane`
50 % (his camera `#cam`, lights `#fx`, "You:" line, mic chip). Portrait = stacked. The ready gate (`body[data-gate]`) used to
put `#camPane` full screen; flag `split` keeps the halves and curtains hers.

## Where each known fix lives
| fix | flag | file |
|---|---|---|
| shoulder-light intro | `shoulder` | beta/lib/shoulder-beat.js, freeze4.html |
| calm body | `NF_CALM` | nova_final_pod.sh (DITTO_SRC) |
| voice holes | `FACE_VOICE_PREBUF_MS=400` | nova_face.py |
| smooth wide picture | `FACE_WIDE_SMOOTH/PREP/SOURCE/TS`, `warmgate`, `ambstill` | nova_face.py, freeze4.html |
| no size jump / no blink | `matchcut`, `noblink` | freeze4.html |
| face tile fresh | `pipfresh` | freeze4.html |
| she answers in the intro | `NOVA_INTRO_ANSWER`, `NOVA_KID_EVENTS` | rt_lk.py |
| split screen, hearing | `split`, `hear`, `NOVA_HEAR` | freeze4.html, nova-bridge.js, rt_lk.py |
| fast boot | `NF_VOLUME` | nova_fastboot.sh |

## Traps
- A cloud sandbox cannot hold LiveKit media; the brain (OpenAI) IS reachable from it → use `test/hear_rig` for hearing.
- Pull `rtlk.log` from :8099 before terminating a play pod.
- `max_output_tokens` 60 on a reply returns an EMPTY response on gpt-realtime-2.
- A bare one-shot in page-owned mode can replay the commercial greeting.
- Balance floor $5; other sessions' pods drain the same account.
