# SECRET ROTATION CHECKLIST (updated 2026-08-25)

Re-scan 2026-08-25: **the git repo and its history are still CLEAN** — no secret values in any
tracked file or scanned commit (working-tree grep + `git grep` over history; only hit was the
Google **Sheet ID**, an OAuth-protected identifier, not a credential). The secrets below live
OUTSIDE git (pod volume, chat history, provider dashboards).
Rule: **any secret that was ever exposed in plaintext must be REVOKED, not just replaced.**

> **NEW 2026-08-25 — two escalations from the `maya_rapa` bake session:**
> - **RunPod API key is now EXPOSED.** It sits in plaintext as `K="rpa_…"` inside
>   `/workspace/bake_master.sh` on the shared volume, and surfaced in session logs. Item #10
>   below is upgraded from "no action" to **revoke + mint new**.
> - **OpenAI key** is also read/hardcoded by the bake scripts (`bake.sh` reads `/workspace/.oai_key`;
>   confirmed exposed) — same revoke as #1.
> The pod-side refactor now covers **`bake.sh` + `bake_master.sh`** too, not just `boot.sh`.

| # | Secret | Where it lives | Ever exposed? | Action | Who |
|---|--------|----------------|---------------|--------|-----|
| 1 | OpenAI key (live avatar) | pod `/workspace/boot.sh` | yes (plaintext on shared volume) | **revoke + mint new** at platform.openai.com → API keys; paste into new `/workspace/.env` | HUMAN mints, CLI redeploys |
| 2 | LiveKit API key | pod `/workspace/boot.sh` | yes (same) | **revoke + mint new** in LiveKit dashboard; into `.env` | HUMAN mints, CLI redeploys |
| 3 | LiveKit API secret | pod `/workspace/boot.sh` | yes (same) | **revoke + mint new** (pair with #2); into `.env` | HUMAN mints, CLI redeploys |
| 4 | OpenAI key (n8n) | n8n credential store "OpenAI (Maya)" | passed through chat 2026-08-11 | **revoke + mint new**; update the n8n credential (CLI can via API) | HUMAN mints, CLI updates |
| 5 | GitHub PAT (`ghp_…`) | chat history + Windows cred manager | passed through chat 2026-08-09 | **revoke** at github.com/settings/tokens; mint fresh only if needed | HUMAN |
| 6 | n8n API key (JWT) | `~/.maya/n8n.env` + chat | passed through chat 2026-08-08 | **rotate** at rafa5555.app.n8n.cloud → Settings → n8n API; update `~/.maya/n8n.env` | HUMAN mints, CLI updates file |
| 7 | Meta app secret | `~/.maya/meta.env` + chat | passed through chat 2026-08-11 | rotate at developers.facebook.com → App settings → Basic → Reset; update `~/.maya/meta.env` | HUMAN |
| 8 | Meta tokens (user/system/page) | `~/.maya/meta.env` | derived from #7 | auto-invalidated when #7 resets; re-mint via `scratchpad/sysuser.mjs` after | CLI (post-approval) |
| 9 | YouTube stream key | `~/.maya/youtube-stream.env` | passed through chat 2026-08-08 | reset in YouTube Studio → Go live → Reset stream key if worried; update env | HUMAN |
| 10 | RunPod API key | Windows user env **+ `bake_master.sh` (plaintext, volume) + session logs** | **YES — exposed 2026-08-25** | **revoke + mint new** at runpod.io → Settings → API Keys; put in `/workspace/.env` as `RUNPOD_API_KEY` and Windows user env | HUMAN mints, CLI updates |
| 11 | Hume API key + config id | pod `/workspace/boot.sh` (if VOICE_BACKEND=hume) | yes (plaintext on volume) | **revoke + mint new** at platform.hume.ai; into `.env` | HUMAN mints, CLI redeploys |

## Pod-side script refactor (done at next pod session)
Every key-bearing script on `/workspace` currently hardcodes secrets:
- `boot.sh` — exports OpenAI/LiveKit/Hume inline.
- `bake.sh` — reads `/workspace/.oai_key`.
- `bake_master.sh` — hardcodes `K="rpa_…"` (RunPod).
Target: all of them `set -a; . /workspace/.env; set +a` (template = `maya-ops/security/boot.env.example`,
now expanded to cover RunPod + Hume). `.env` never leaves the volume, never enters git.
`maya-boot.sh` already sources `/root/nova.env` — consolidate to the one `/workspace/.env`.
CLI applies this at the next `maya-up`/bake session (step: "deploy .env, strip inline keys from *.sh").

## Priority order
1. **Revoke + mint new #10 (RunPod) and #1/#4 (OpenAI) NOW** — freshly exposed in plaintext on
   the shared volume (bake scripts). Highest urgency this session.
2. Revoke #5 (GitHub PAT) and #6/#7 (n8n + Meta) — went through chat, lowest effort.
3. Revoke + re-mint #2/#3 (LiveKit) and #11 (Hume) — needs a redeploy; pair with the next pod
   bring-up (the same session that strips inline keys from boot.sh/bake*.sh).
4. #9 optional.

## Scan method (for repeatability)
Working tree: `grep -rInE '(sk-[A-Za-z0-9]{20}|rpa_[A-Za-z0-9]{20}|ghp_…|github_pat_…|AKIA…)'`.
History: `git grep -InE '<same>' $(git rev-list --all)`. gitleaks not installed on this box;
if installed later, run `gitleaks detect --no-banner` and append findings here.
