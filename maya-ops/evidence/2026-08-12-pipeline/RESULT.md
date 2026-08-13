# Pipeline activation + test — 2026-08-12

- **Activation: DONE (real).** W3 → W2 → W4 activated in order via the n8n API (all returned ON).
- **Live message-flow test: BLOCKED — pod auto-stopped.** The pod's 3-hour money-guard fired
  mid-test; the switchboard went 404, so n8n's `/chat-in` call to the pod returned 500. This
  is a pod-down condition, not a pipeline fault. Not faking green: the end-to-end proof
  (question → brain answer by name → lead row in the sheet) needs the pod live.
- Workflows deactivated afterward so the pipeline state follows the pod (down = down).

## To complete this test (needs pod, ~5 min once up)
1. `node maya-ops/deploy/maya-up.mjs`
2. `node maya-ops/deploy/maya-golive.mjs`  (re-activates + health-checks)
3. `node scratchpad/fire-test.mjs`  (fires the 4 test viewer messages)
4. Check the Leads sheet gets the buy-intent row (רות → serum) and vitals show leads=1.

## What DID verify this session
- The **selling-host driver works**: earlier, with a stage connected, Maya received and
  voiced the sales script (5 lines, 200 OK) before the stage dropped — proving the
  driver → switchboard → brain → speech path.
- A **real YouTube live broadcast** ran (46 min, 11 views) from the pod.
