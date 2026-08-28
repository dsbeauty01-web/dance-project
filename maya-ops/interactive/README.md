# maya-ops/interactive — the gap-closers for the live interactive host

The interactive host already mostly exists: `pod/maya_rt.py` (OpenAI **Realtime** voice pipe,
answer-by-name + truth-gate already work) + `maya-server/app.py` (director: moderation, queue,
approve-mode, latency, session timer, `/vitals`, `/lead`) + n8n W1/W1-FB/W2/W3 (comment ingest →
classify → priority → lead). See `maya-ops/NOVA-LEAK-REPORT.md` and the recon in the build order.

These four modules close the **measured gaps** the recon found. Each is pure-python, no deps, and
ships with a `__main__` self-test that runs green off the pod (`python <mod>.py`). They are the
**logic**; the live wiring + measured latency happen in the pod dry-run (T6), which is asked-for.

| Module | Closes gap | Wires into | Status |
|---|---|---|---|
| `cost_meter.py` | pod never reports cost → `voice_cost_est_usd` stays 0.0; **no hard cap** (ground rule #2) | pod `maya_rt.py` accumulates Realtime in/out audio secs → POST `maya-server /vitals`; director holds one `CostMeter`; `tripped()` → kill switch → loop | logic ✅ tested · wiring ⏳ pod |
| `answer_discipline.py` | **no rate-limiting** anywhere; name-first not enforced centrally | director gates each comment before forwarding to pod `/rt` `chat`; `record_answer()` on `maya-said` | logic ✅ tested · wiring ⏳ pod |
| `commerce.py` | `payment_link` null + `post_link` tool **doesn't exist**; no description/pinned automation | director BUY/ME/LINK path → `post_link_decision()`; `maya-golive` → `youtube_description()` + `pinned_comment()`; PITCH beat → `price_banner()` + QR of `buy_url()` | logic ✅ tested · wiring ⏳ pod/OAuth |
| `state_machine.py` | avatar hot-swap is ad-hoc; no IDLE/LISTEN/SPEAK/PITCH | director drives `request()`; on clip boundary `on_boundary()` → POST engine `/set_avatar?id=` | logic ✅ tested · wiring ⏳ pod |

## Exact wiring points (for the pod phase — do not fake before measuring)

**cost_meter** — `maya_rt.py`: the Realtime session already streams `response.audio` out and mic/comment
audio in. Sum `len(pcm)/ (24000*2)` seconds per chunk; every ~5 s POST `{in_secs,out_secs}` to
`ENGINE`-sibling `maya-server /vitals`. Director: `meter.add_audio(...)`, log `meter.log_line()`, and
when `meter.tripped()` → call existing `/kill` (mute brain) + switch OBS/stream source to the scripted
`session_stream_v2.mp4` loop. **Barge-in** is a separate pod change: `maya_rt.py:211`
`interrupt_response` is `False` — flip to `True` and add "finish the current clause, then switch"
(only cut on sentence boundary). Test live in T6.

**answer_discipline** — director `/chat-in` (`app.py:425`): build the queue, `AnswerGate.pick_next()`
to choose, `admit_answer(user_id, now, others_waiting)` before forwarding; on `maya-said`,
`record_answer()`. `name_first()` wraps the spoken line (the pod `chat` handler already says "answer BY
NAME"; this enforces it centrally too). Cues use `admit_cue()`/`record_cue()` (8 s).

**commerce** — set `catalog.json.products[].payment_link` when the human picks a processor (stays
`null` today → `post_link_decision()` returns `alert_operator`, which is the correct safe behavior — it
never posts a fake link). `coupon` = per-stream attribution code, set before each stream. The chat
text-reply + YouTube description/pinned-comment posting need **YouTube OAuth** (W1 re-auth) — build is
here, the post is gated on that human click.

**state_machine** — today's baked set is `maya_serum` (baked 2026-08-27) + `maya_idle`,`maya_nudge`,
`maya_point`,`maya_bothhand`,`maya_goodbye` + the two cutaway masters → runs in `fallback_2state`.
The moment `maya_listen`/`maya_speak`/`maya_invite` are baked from the human's Kling clips,
`mode()` flips to `full` and the machine uses them automatically — **no code change**.

## Run the tests
```
cd maya-ops/interactive && for m in cost_meter answer_discipline commerce state_machine; do python $m.py; done
```
