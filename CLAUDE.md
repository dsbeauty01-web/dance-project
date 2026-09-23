Read MAYA-CONTEXT.md first.

# dance-project / maya-p1-finish

This branch holds Maya — the self-owned AI live-selling host. `MAYA-CONTEXT.md` at the repo
root is the single source of truth for what Maya is, what runs where, and the rules that must
never be broken. Read it before touching anything, in every session (laptop, cloud, or phone).

## Working here
- Code lives in `maya-ops/` (host stack in `maya-ops/lt/`, bench/bake tools in `maya-ops/host/`).
- `MAYA-NEXT.md` is the running task list.
- Patches merge on top of the latest green code — never overwrite whole files from an older package.
- One agent touches the RunPod account/pod at a time. Stop pods by explicit id only; never sweep —
  other projects share the account.
- Nothing restarts during a live. Tune on a recording; apply to the next live.

## Secrets
Never commit keys. They live in `host.env` on the `maya-persist` volume, or in cloud/session
environment variables. `*.env`, `host.env`, and `keys.env` are gitignored — keep it that way.
This repository is PUBLIC; treat every file you add as world-readable.
