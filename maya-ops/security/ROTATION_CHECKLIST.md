# SECRET ROTATION CHECKLIST (2026-08-12)

Scan result: **the git repo and its full history are CLEAN** — no secret values in any
tracked file or past commit (verified `git log -p --all` + tracked-file grep). The secrets
below live OUTSIDE git (on the pod volume, in chat history, or in provider dashboards).
Rule: **any secret that was ever exposed in plaintext must be REVOKED, not just replaced.**

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
| 10 | RunPod API key | Windows user env | not in chat/git | no action | — |

## boot.sh refactor (pod volume, done at next deploy)
The pod's `/workspace/boot.sh` currently exports keys inline. Target pattern (template
committed as `maya-ops/security/boot.env.example`): boot.sh sources `/workspace/.env`
which holds the keys; `.env` is never in git and never copied off the volume.
`maya-boot.sh` already sources `/root/nova.env` — same idea; consolidate to one `.env`.
CLI applies this at the next `maya-up` (adds a "deploy .env, strip inline exports" step).

## Priority order
1. Revoke #5 (GitHub PAT) and #6/#7 (n8n + Meta) NOW — they went through chat, lowest effort.
2. Revoke + re-mint #1–#4 (OpenAI + LiveKit) — these are the GATE-0 blocker; needs a
   redeploy, so pair it with the next pod bring-up.
3. #9 optional; #10 no action.
