# ditto_take8 — the Ditto engine at the level of Maya's best take, for Nova

Copied **unchanged** on 2026-11-10 from `dsbeauty01-web/maya-lt` @ `lane/motion-transfer` `7d07a9f`
(read-only; nothing in the Maya repo was touched):

| file here | from maya-lt | why Nova needs it |
|---|---|---|
| `ditto_server.py` | `maya-ops/lt/` | the take-8 server. Nova's older copy (`docs/nova-ditto/from_maya/code/`) has **no** paste gate, fast close, debt fix or fast prime |
| `ditto_wide.py` | `bench/replace_musetalk_alt/` | paste-back, `DITTO_GRAIN`, `DITTO_MASK`, lip colour. Must sit beside the server |
| `ditto_up.sh`, `ditto_pack_get.py` | `maya-ops/lt/` | installer + the prebuilt pack (boot in ~3 min instead of 5–15). The pack needs `MAYA_ASSETS_TOKEN`; without it the script says so and installs the slow way |
| `motion_bank.py` | `maya-ops/lt/` | gestures (optional) |
| `drive_gate.py` | `maya-ops/lt/` | the drive-audio gate Maya's shim uses. **Not wired into Nova** (see `nova_take8.env`) |
| `prebake_gate.py` | `tools/` | free CPU check of any body video |
| `build_bank_v3.py` | `bench/lead_seyzar/` | closed-mouth patch for a body whose mouth moves. **Nova's dance body does not need it** (resting mouth p95 0.0057, already PASS) |

Written here: `nova_take8.env` (the settings, each one cited), `take8_body.sh` (native size + light sharpen).

**State: copied and read, not run.** No pod was started in the session that added this folder.
The numbers behind this are in `docs/nova-ditto/take8/` (numbers/, strips/, nova_ditto_selftest.log).
