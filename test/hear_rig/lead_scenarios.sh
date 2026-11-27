#!/bin/bash
# NOVA-LEAD v2 scenario rig (2026-11-26): the real page + the real voice brain + the engine stand-in, no pod.
# usage: lead_scenarios.sh <outdir> [scenario ...]     (keys from the environment: OPENAI_API_KEY)
# Each scenario prints its transcript (who said what, t), the time from the greeting to the game, and the backups used.
R=$(cd $(dirname $(readlink -f $0))/../.. && pwd); OUT=${1:-/tmp/lead-sc}; shift
export HEAR_RIG_DIR=${HEAR_RIG_DIR:-/tmp/nova-hear-rig}
F4_FLAGS='{"shoulder":true,"pipfresh":true,"warmgate":true,"matchcut":true,"heneutral":true,"ambstill":true,"noblink":true,"split":true,"hear":true,"v2vintro":true,"react":true,"live2":true,"barge":true,"lead":true}' bash $R/test/hear_rig/deploy.sh >/dev/null
declare -A EV X
EV[normal]="NAME:open:0.6:hi_im_shuki;CHAT:open:0.7:yes_i_love_dancing;LIGHT:hit:3"
EV[silent]="";                                                                                   X[silent]="&shrug=off"
EV[chatty]="NAME:open:0.6:chatty1;CHAT:open:0.7:chatty2;LIGHT:open:1.5:chatty3;LIGHT:hit:6"
EV[questions]="NAME:open:0.6:can_you_hear_me;NAME:open:0.7:hi_im_shuki;CHAT:open:0.7:what_now;LIGHT:open:1.2:what_do_i_do;LIGHT:hit:5"
EV[refusal]="NAME:open:0.6:hi_im_shuki;CHAT:open:0.7:i_dont_want_to"
EV[noise]="NAME:open:0.6:garble1;NAME:open:1.0:hum;CHAT:open:0.7:garble1;LIGHT:hit:4"
EV[talkover]="NAME:open:0.6:hi_im_shuki;CHAT:over:0.9:wait_wait;CHAT:open:0.8:yes_i_love_dancing;LIGHT:over:0.8:what_do_i_do;LIGHT:hit:6"
for s in ${@:-normal silent chatty questions refusal noise talkover}; do
  python3 $R/test/hear_rig/run.py $OUT/$s name=$s lang=en NOVA_HEAR=1 NOVA_KID_EVENTS=1 NOVA_INTRO_ANSWER=1 NOVA_V2V_INTRO=1 NOVA_FAST_KID=1 NOVA_UTT_MAP=1 \
    NOVA_TX_CONF=1 NOVA_TX_CONF_MIN=-9 NOVA_RT_EFFORT=${NOVA_RT_EFFORT:-minimal} NOVA_TRACE=1 NOVA_LIVE2=1 NOVA_BARGE=1 NOVA_LEAD=1 echo=0.3 \
    "ev=${EV[$s]}" until=game cap=${CAP:-75} "extra=&debug=1${X[$s]}" > $OUT/$s.txt 2>&1
  sed -n '/=== TRANSCRIPT/,/TIME TO GAME/p' $OUT/$s.txt
done
