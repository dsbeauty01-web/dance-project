# test/hear_rig - "does she hear the child?" with NO pod (2026-11-23, docs/NOVA-FIX-2026-11-23b.md)

The real page (beta/freeze4.html) in headless Chrome + the real brain (pod/rt_lk.py, real OpenAI voice) on this machine.
Only the GPU face server and LiveKit are stand-ins: `engine_stub.py` takes her voice from the brain and hands it to the
page after the face server's constant delay (wide 1.8 s, PiP 1.0 s); `lk_shim.js` gives the page her picture (the calm clip)
and that voice; `kidmic.js` is the child's microphone - a stream the test speaks recorded lines into, with a microphone's
noise floor and, with `echo=0.5`, her own voice leaking back in (a phone with no echo cancelling).

    export HEAR_RIG_DIR=/tmp/nova-hear-rig         # ~70 MB of page files are copied here
    bash test/hear_rig/deploy.sh                    # F4_FLAGS='{ ... }' to choose the page flags
    # kid lines: $HEAR_RIG_DIR/kid/{hi,yes,game,end}.wav (48 kHz mono; any spoken wav)
    python3 test/hear_rig/run.py /tmp/out NOVA_HEAR=1 say=listen:hi,game:game,end:end [echo=0.5] [w=390 h=844]

Read `/tmp/out/rtlk.log`: `[RACE] rest got utt N : <his words>` then `[ORIGIN] kid | <her answer>`.
It costs OpenAI voice minutes only. It does not prove lips, picture speed or a real phone's microphone.

## NOVA-LEAD (2026-11-26, docs/NOVA-LEAD-2026-11-26.md)

Page flag `lead` + brain `NOVA_LEAD=1` (with `NOVA_LIVE2=1`). The stand-in engine answers `GET /played_out` like the face server.

    F4_FLAGS='{"shoulder":true,...,"v2vintro":true,"react":true,"live2":true,"barge":true,"lead":true}' bash test/hear_rig/deploy.sh
    python3 test/hear_rig/run.py /tmp/out lang=en NOVA_HEAR=1 NOVA_KID_EVENTS=1 NOVA_INTRO_ANSWER=1 NOVA_V2V_INTRO=1 NOVA_FAST_KID=1 \
        NOVA_UTT_MAP=1 NOVA_TX_CONF=1 NOVA_TX_CONF_MIN=-9 NOVA_RT_EFFORT=minimal NOVA_TRACE=1 NOVA_LIVE2=1 NOVA_BARGE=1 NOVA_LEAD=1 \
        echo=0.3 say=name:hi_im_shuki hit=3 cap=45 extra='&debug=1'

- `say=name:<wav>` his answer in NAME (leave `say=` empty = a silent child) - `nameq:<wav>` his own question first, then `name:`
- `light:<wav>` his question in LIGHT, right after her light line played out (`light_at=<s>` = at a fixed time instead)
- `hit=<s>` a real shoulder lift <s> after the LIGHT step - `extra='&shrug=off'` = the replayed body never lifts it
- read the page log lines `lead step <NAME> <ms>`, `lead backup: ...`, `lead played out (...)`, `lead done: greeting -> game <ms>`

### NOVA-LEAD v2 scenarios (2026-11-26)

    bash test/hear_rig/lead_scenarios.sh /tmp/lead-sc            # all 7: normal silent chatty questions refusal noise talkover
    bash test/hear_rig/lead_scenarios.sh /tmp/lead-sc chatty     # one

Each prints the transcript (who said what, page seconds), the time from the greeting to the game, and the backups used.
`run.py` scenario arguments: `ev=STEP:mode:after[:wav];...` (events fire in order, each while the page is in STEP;
`open` = he speaks <after> s into open microphone · `over` = he talks over her, <after> s after her voice starts ·
`hit` = a real shoulder lift <after> s after the check is armed) and `until=game`. New child clips in `test/phrases/`
(copy 48 kHz versions to `$HEAR_RIG_DIR/kid/`): `yes_i_love_dancing i_dont_want_to chatty1 chatty2 chatty3 wait_wait`.
