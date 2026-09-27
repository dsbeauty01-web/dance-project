// LAW: PODS. Live/test pods are launched ONE way, safely (POD LAW in LAWS.md).
// The launch script must be Secure-Cloud, arm the suicide-timer, and boot INSIDE
// tmux; the canonical boot.sh must git-pull first, carry the no-pkill-window +
// cold-load warnings, and neither script may hold an un-bracketed pkill that can
// self-match. If any rail vanishes, a safety rail was removed → RED.
// New rails (2026-07-28, each cost real hours): 7 tmux, 8 bracket-pkill, 9 cold-load.
// Rail 10 (2026-09-18) — BRAIN DEPLOY: the pull+copy step moved out of boot.sh into
// tools/pod/deploy_from_git.sh so it can ship by merge. The rail did not weaken, it moved:
// boot must CALL that step, and that step must pull AND copy pod/rt_lk.py, because for a
// year "merge = deploy" was true for the pages and silently false for the brain.
const { runLaw } = require('./_lib');
const LAUNCH = 'tools/pod/launch_pod.sh';
const BOOT = 'tools/pod/boot.sh';
const DEPLOY = 'tools/pod/deploy_from_git.sh';
runLaw({
  id: 'law-pods', title: 'Pod launch — Secure Cloud + suicide-timer + tmux + safe boot', status: 'active',
  why: 'Community/no-timer/pkill-during-load/sshd-teardown pods burned money and hung the engine; the launch path must stay safe.',
  checks: [
    { desc: 'launch is Secure Cloud',        rel: LAUNCH, present: /"cloudType": "SECURE"/ },
    { desc: 'launch arms the suicide-timer',  rel: LAUNCH, present: /runpodctl stop pod/ },
    { desc: 'suicide-timer is 6h backstop',   rel: LAUNCH, present: /nohup sleep 6h/ },
    { desc: 'boot runs the git deploy step first', rel: BOOT, present: /deploy_from_git\.sh/ },
    { desc: 'boot carries no-pkill-window',   rel: BOOT,   present: /NO-PKILL-WINDOW/ },
    // LAW-PODS-10 — brain deploy: a merge to main must reach the BRAIN, not just the pages.
    { desc: 'LAW-PODS-10 marker (deploy)',       rel: DEPLOY, present: /LAW-PODS-10-BRAINDEPLOY/ },
    { desc: 'LAW-PODS-10 deploy git-pulls first', rel: DEPLOY, present: /git -C "\$REPO" fetch/ },
    { desc: 'LAW-PODS-10 deploy copies the brain', rel: DEPLOY, present: /cp -f "\$SRC" "\$DST"/ },
    { desc: 'LAW-PODS-10 deploy keeps a rollback', rel: DEPLOY, present: /bak-predeploy/ },
    { desc: 'LAW-PODS-8 bracket marker (deploy)',  rel: DEPLOY, present: /LAW-PODS-8-BRACKET/ },
    { desc: 'LAW-PODS-8 no plain pkill brain',     rel: DEPLOY, absent: /pkill -f ['"]?rt_lk/ },
    // LAW-PODS-7 — tmux: boot survives RunPod sshd teardown.
    { desc: 'LAW-PODS-7 tmux marker (launch)',    rel: LAUNCH, present: /LAW-PODS-7-TMUX/ },
    { desc: 'LAW-PODS-7 boots inside tmux',        rel: LAUNCH, present: /tmux new-session -d/ },
    // LAW-PODS-8 — bracket pkill: no pattern may self-match. Marker present + the
    // plain (un-bracketed) forms must NOT appear anywhere in either script.
    { desc: 'LAW-PODS-8 bracket marker (launch)',  rel: LAUNCH, present: /LAW-PODS-8-BRACKET/ },
    { desc: 'LAW-PODS-8 bracket marker (boot)',     rel: BOOT,   present: /LAW-PODS-8-BRACKET/ },
    { desc: 'LAW-PODS-8 no plain pkill boot (launch)', rel: LAUNCH, absent: /pkill -f boot/ },
    { desc: 'LAW-PODS-8 no plain pkill boot (boot)',    rel: BOOT,   absent: /pkill -f boot/ },
    { desc: 'LAW-PODS-8 no plain pkill app (launch)',  rel: LAUNCH, absent: /pkill -f app\.py/ },
    { desc: 'LAW-PODS-8 no plain pkill app (boot)',     rel: BOOT,   absent: /pkill -f app\.py/ },
    // LAW-PODS-9 — cold-load patience: silence < 15min = loading, not dead.
    { desc: 'LAW-PODS-9 cold-load marker (boot)',   rel: BOOT,   present: /LAW-PODS-9-COLDLOAD/ },
  ],
});
