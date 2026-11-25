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
