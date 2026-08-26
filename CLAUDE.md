# ⚠️ SHARED REPO — TWO PRODUCTS. READ BEFORE ANY ACTION.

This repository is a **fork-shared codebase for TWO different products**. Confusing them shipped
Nova on air as Maya on 2026-08-26 (the Nova dance-kid was baked and streamed as `maya_rapa`).
See `maya-ops/NOVA-LEAK-REPORT.md`.

| | **Nova** | **Maya** |
|---|---|---|
| What | Kids' **dance** app | English **AI live-sell** host (vitamin-C serum) |
| Looks like | 3D cartoon kid, pink hair, cap, hoodie | adult woman sales host (**no asset exists yet**) |
| Room | `nova-live` | **`maya-live`** |
| Brain | `pod/rt_lk.py` (persona: "You are Nova, a magical AI dance teacher") | **`pod/maya_rt.py`** (Maya sales persona) |
| Avatars | `nova_*` | **`maya_*`** |
| Boot | `tools/pod/boot.sh`, `launch_pod.sh`, `bake_all.sh` | **`maya-boot.sh` / `maya-watchdog.sh` (NOT yet forked — do not reuse Nova's)** |
| Voice | `NOVA_VOICE` | `MAYA_VOICE` |

## THE LAW (both directions)

1. **Declare which product your task is** before you touch anything. If unsure, ASK — do not guess.
2. **Never cross resources.** A Maya task must not use a Nova room, env, persona, brain, avatar,
   pod template, sheet, or source clip — and vice-versa. `rapa` inside a **Maya** task means
   `maya_rapa` on `maya-live`; the Nova upperbody/dance game is a **separate** concern.
3. **Maya bring-up / bake / go-live MUST run `tools/pod/maya-preflight.sh` first** and abort on any
   `nova` value. No override flag. It asserts PROJECT=maya · ROOM=maya-live · AVATAR=maya_* ·
   BRAIN=maya_rt.py and refuses to run if any `NOVA_*` env var is set.
4. **The committed boot/bake scripts (`boot.sh`, `launch_pod.sh`, `bake_all.sh`) are NOVA's.**
   Running them for a Maya task produces Nova content under a Maya label. Do not.
5. **There is currently NO real Maya face.** Every `maya_*` avatar today is Nova-kid content
   (`maya_rapa`) or unbuilt (`maya_idle`). Do **not** bake or stream a "Maya" avatar until a genuine
   Maya identity source is provided by the founder. Never reuse the Nova kid as Maya.
6. **Branch hygiene:** Nova freeze work is on `freeze-structural-fix`; Maya work belongs on a
   `maya-*` branch. Do not commit Maya changes onto a Nova branch or vice-versa.

## Standing security rules (both products)
- Ask before starting any pod; batch pod tasks into ONE session; stop pods at the end and verify 0 running.
- Never commit secrets; never print full keys. `.maya/*.env` and stream keys stay out of git.
- Never fake green — a failed check is reported as failed.
- Don't overwrite Hebrew assets; add English versions alongside.
