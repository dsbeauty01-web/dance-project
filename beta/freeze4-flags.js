/* beta/freeze4-flags.js — NOVA-AUDIT (2026-11-22) build flags for beta/freeze4.html. ALL OFF here (the repo default).
   tools/pod/nova_final_pod.sh overwrites the deployed copy on the pod with the flags this build turns on.
   A flag can also be set for one visit with ?<name>=1 (or forced off with ?<name>=0).
     shoulder  — her approved intro's SHOULDER LIGHT beat (beta/lib/shoulder-beat.js; origin/main nova-commercial.html INTRO-V2V)
     pipfresh  — her small face tile stays covered until a real (non-black) picture of her face arrives
     fpsprobe  — the page logs, once a second, how many NEW pictures of Nova really reached the browser (freeze4Log 'fps')
     warmgate  — NOVA-GO2: her greeting is asked (so she is revealed) only once her live wide picture flows smoothly
     matchcut  — NOVA-GO2: no size jump wide <-> game: matched-frame cut + a camera pull-back / push-in
     ambstill  — NOVA-GO2: while her live body is shown, the blurred room behind her is a still picture (smoother live video)
     noblink   — NOVA-GO3: no dark frame when her clip changes (last picture held until the next is drawn)
     heneutral — NOVA-GO2: the Hebrew shoulder lines and greeting in the plural (not boy-only)
     split     — NOVA-GO4: split screen from the first second (Nova's half behind a curtain of her room until she is ready)
     hear      — NOVA-GO4: the player is HEARD: one microphone stream, audio unlocked in the Play tap, microphone chip + watch,
                 tight echo guard, "Ready?" waits for his yes, his words outrank her game line, page log sent to the brain
                 (pair it with NOVA_HEAR=1 on the pod: she answers in the intro, in the game's gaps and at the ending) */
window.__F4_FLAGS = {};
