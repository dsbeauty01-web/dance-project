#!/bin/bash
# rig deploy: mimic nova_final_pod.sh's page deploy into $RIG/ws (the brain's /workspace)
RIG=${HEAR_RIG_DIR:-/tmp/nova-hear-rig}; R=$(cd $(dirname $(readlink -f $0))/../.. && pwd); W=$RIG/ws; P=$W/pages; mkdir -p $RIG/src $RIG/kid
mkdir -p $P/beta $P/test $W/audio $W/media
if [ ! -d $P/freezegame ]; then
  (cd $R && git archive HEAD freezegame/idle_sway.mp4 freezegame/dance-active.mp4 freezegame/dance-sub.mp4 freezegame/flamingo_freeze.mp4 freezegame/freezebear.mp4 freezegame/freezefrog.mp4 freezegame/freeze-star.mp4 freezegame/animal-freeze-song.mp3 audio/freeze2 test/clips | tar -x -C $RIG/src 2>/dev/null || { mkdir -p $RIG/src; git archive HEAD freezegame/idle_sway.mp4 freezegame/dance-active.mp4 freezegame/dance-sub.mp4 freezegame/flamingo_freeze.mp4 freezegame/freezebear.mp4 freezegame/freezefrog.mp4 freezegame/freeze-star.mp4 freezegame/animal-freeze-song.mp3 audio/freeze2 test/clips | tar -x -C $RIG/src; })
  cp -r $RIG/src/freezegame $P/freezegame; cp -r $RIG/src/audio/freeze2 $W/audio/freeze2; cp -r $RIG/src/test/clips $P/test/clips
fi
rm -rf $P/beta/lib $P/beta/freeze2 $P/shared
cp $R/beta/freeze4.html $R/beta/play.css $P/beta/; cp -r $R/beta/lib $R/beta/freeze2 $P/beta/; cp -r $R/shared $P/shared
cp $R/tools/pod/assets/nova_talk_calm.mp4 $W/media/
rm -rf $W/audio/react; cp -r $R/audio/react $W/audio/react   # NOVA-GO5 react: her listening hums
echo "window.__F4_FLAGS = ${F4_FLAGS:-{ shoulder: true, fpsprobe: true, pipfresh: true, warmgate: true, matchcut: true, heneutral: true, ambstill: true, noblink: true, split: true, hear: true \}};" > $P/beta/freeze4-flags.js
sed "s#/workspace#$W#g" $R/pod/rt_lk.py > $RIG/rt_lk_rig.py
echo deployed: $(cat $P/beta/freeze4-flags.js | cut -c1-200)
