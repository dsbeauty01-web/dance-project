// LAW: PODS. Live/test pods are launched ONE way, safely (POD LAW in LAWS.md).
// The launch script must be Secure-Cloud and must arm the suicide-timer; the
// canonical boot.sh must git-pull first and must carry the no-pkill-window
// warning. If any of these markers vanishes, a safety rail was removed → RED.
const { runLaw } = require('./_lib');
const LAUNCH = 'tools/pod/launch_pod.sh';
const BOOT = 'tools/pod/boot.sh';
runLaw({
  id: 'law-pods', title: 'Pod launch — Secure Cloud + suicide-timer + safe boot', status: 'active',
  why: 'Community/no-timer/pkill-during-load pods burned money and hung the engine; the launch path must stay safe.',
  checks: [
    { desc: 'launch is Secure Cloud',        rel: LAUNCH, present: /"cloudType": "SECURE"/ },
    { desc: 'launch arms the suicide-timer',  rel: LAUNCH, present: /runpodctl stop pod/ },
    { desc: 'suicide-timer is 6h backstop',   rel: LAUNCH, present: /nohup sleep 6h/ },
    { desc: 'boot git-pulls first',           rel: BOOT,   present: /git -C \/workspace\/repo pull/ },
    { desc: 'boot carries no-pkill-window',   rel: BOOT,   present: /NO-PKILL-WINDOW/ },
  ],
});
