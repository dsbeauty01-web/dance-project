# DEPLOY — Maya in one command

```
node maya-ops/deploy/maya-up.mjs      # fresh pod -> deploy -> boot -> verify -> n8n re-point -> links + beep
node maya-ops/deploy/maya-down.mjs    # stop the current pod (money off)
```

Needs: `RUNPOD_API_KEY` in the environment · `~/.ssh/id_ed25519(.pub)` · `~/.maya/n8n.env`
(N8N_BASE + N8N_KEY; without it the n8n re-point step is skipped with a warning).

What `maya-up` does, in order — each item is a lesson that was once learned the hard way:

1. **Creates** a fresh pod (never restarts a stopped one — the GPU is usually taken):
   SECURE 4090 · EU-RO-1 · volume `1ditrne6cb` · ports 8765/8010/**8000**/22 ·
   `env.PUBLIC_KEY` (without it there is NO ssh, period).
2. **Deploys** `pod/maya_rt.py` from the repo to `/workspace` — the repo is the source of
   truth; the volume is just the runtime copy.
3. **Arms the money-guard** with THIS pod's id hardcoded (3h self-stop), then launches
   `/workspace/maya-boot.sh` in tmux — the boot script installs its own deps and starts
   engine → bridge → brain → switchboard, each in its own tmux session.
4. **Waits for real health** (brain + switchboard through the public proxy) and REFUSES to
   continue if the brain is not in room `maya-live` (ROOM LAW — the day Maya showed up
   inside Nova's app).
5. **Re-points every `MAYA W*` n8n workflow's** `maya_api` at the new pod — pod URLs die
   with every swap; stale ones are the silent killer of "why is nothing arriving".
6. Prints all links (her page, `/test` board, director, stage), writes the pod id to
   `~/.maya/current-pod.txt`, and beeps ×4.

First stop after bring-up: **`https://<pod>-8765.proxy.runpod.net/test`** — the founder's
green/red board, served by the pod itself, one glance = is she ready.
