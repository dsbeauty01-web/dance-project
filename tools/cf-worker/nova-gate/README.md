# nova-gate — free Cloudflare Worker that wakes Nova

Replaces the paid Render worker (`novapython`, deleted 2026-11-23). Cost: $0 (Cloudflare Workers + KV free plans).

What it does:
- `/` — the link players open. Always on. "Wake Nova" button (access code, language).
- Starts ONE fast-boot `nova-go4` pod (Secure 4090, volume `pqbavl4mct`, EU-RO-1). Refuses under $3 balance, refuses a second player while one plays, retries 24 → 16 → any CPU cores when RunPod is sold out.
- Shows "waking up" and sends the player to `https://<pod>-8765.proxy.runpod.net/beta/freeze4?lang=…` once the face server and the page answer.
- Every 5 minutes (cron) it closes the pod when the game is idle 10 min, over 30 min of play, stuck booting 20 min, or failed. It always saves the game logs first (`STAGES`, `rtlk.log`, `A-console.log`, `boot.log`) to KV.
- `/api/logs?admin=<ADMIN_CODE>` lists saved games; `/api/logs/<key>?admin=…` opens one.
- It never touches a pod that is not named `nova-play`.

Proof: `node test.mjs` (16 offline tests) and one dry run against the real account (reads only) on 2026-11-24: body built for EU-RO-1, 4090, 24 cores.

Deploy (once, needs a Cloudflare account and an API token with "Edit Cloudflare Workers"):
```
cd tools/cf-worker/nova-gate
export CLOUDFLARE_API_TOKEN=...            # never commit it
npx wrangler kv namespace create LOGS     # put the id into wrangler.toml
for k in RUNPOD_API_KEY OPENAI_API_KEY LIVEKIT_URL LIVEKIT_API_KEY LIVEKIT_API_SECRET MAYA_ASSETS_TOKEN ACCESS_CODE ADMIN_CODE; do
  printenv $k | npx wrangler secret put $k; done
npx wrangler deploy                       # DRY_RUN=1 first; set DRY_RUN = "0" in wrangler.toml for real pods
```

Not proven yet: a real pod started by the worker end to end; the idle rule (brain log stops growing) on a real abandoned game.
