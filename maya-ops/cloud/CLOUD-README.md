# Running Maya from the phone (Claude Code cloud sessions)

Goal: Refael opens the Claude app → Code tab, types one line, and it runs in Anthropic's cloud —
laptop closed. No SSH to the pod; everything goes through RunPod's REST API and the pod's HTTPS proxy.

## 1. Environment variables (Refael pastes the values in claude.ai/code → environment settings)

Never put values in the repo or in chat. Local copies live in `~/.maya/*.env` on the laptop.

Required for a check run:

| Name | Source on the laptop |
|---|---|
| `RUNPOD_API_KEY` | Windows user env var |
| `OPENAI_API_KEY` | `~/.maya/openai.env` |

Required additionally for a real live run:

| Name | Source |
|---|---|
| `FB_PAGE_ID`, `FB_PAGE_TOKEN` | `~/.maya/host.env` |
| `BUY_URL` | `~/.maya/host.env` |
| `YT_REFRESH_TOKEN`, `YT_STREAM_KEY` | `~/.maya/host.env`, `~/.maya/youtube-stream.env` |

Needed only for a **volume-less** pod (running outside US-TX-3):

| Name | What it is |
|---|---|
| `MAYA_ASSETS_TOKEN` | GitHub token that can read `dsbeauty01-web/maya-lt` (private). `/start.sh` uses it to pull the face bake, gestures and weights from release `assets-v1` when the volume isn't there. |

`ELEVENLABS_API_KEY` is **not** needed. `/start.sh` exports `LT_TTS=openaitts` / `LT_REF_FILE=coral`
and deliberately overrides whatever `host.env` says, so the voice is OpenAI coral on every path.

Note: `YT_CLIENT_ID` / `YT_CLIENT_SECRET` are named in MAYA-CONTEXT.md but are **not** present in any
local `.env` file — only the tokens are. Refresh-token renewal will need them; find or re-mint them
before relying on YouTube from the cloud.

Defaults baked into `maya_cloud.py` (override only if they change):
`RUNPOD_IMAGE=ghcr.io/dsbeauty01-web/maya-lt:latest` ·
`RUNPOD_REGISTRY_AUTH_ID=cmuba1ii5003nrtix7j8yyr43` (ghcr-maya-lt) ·
`RUNPOD_VOLUME_ID=8gu2r2r0hr` (maya-persist) · `RUNPOD_DC=US-TX-3`

## 2. Network allowlist

The cloud sandbox must be able to reach:

```
rest.runpod.io          pod deploy / status / stop
api.runpod.io           legacy GraphQL (some tools still use it)
*.proxy.runpod.net      the pod's /health over HTTPS — this is what replaces SSH
api.openai.com          brain + TTS
graph.facebook.com      live video + comments
www.googleapis.com      YouTube Data API
oauth2.googleapis.com   YouTube token refresh
ghcr.io                 image pulls are done by RunPod, not the sandbox, but keep it allowed
github.com              clone / push
```

`*.proxy.runpod.net` is the one people forget. Without it there is no way to read the run report
without SSH, and the whole phone flow falls back to a VPS.

## 3. Setup script

```
pip install requests
```

## 4. The phone command

```
Read MAYA-CONTEXT.md. Run: python maya-ops/cloud/maya_cloud.py check
Report fps and audio level, confirm the pod was stopped by id.
```

`check` deploys, waits for RUNNING, polls `https://<podId>-8787.proxy.runpod.net/health`, prints the
report, and stops the pod in a `finally` block so a failed check can never leave a pod billing.

**Which script actually runs:** nothing here calls a boot script directly. The pod's `/start.sh`
sees `MAYA_AUTOSTART=1` and runs `lt_run.sh "$MAYA_MODE" "$MAYA_MINUTES"` itself. `lt_boot.sh` is the
older hand-run path — it expects LiveTalking and SRS to live on the volume (`$WS/LiveTalking`,
`$WS/srs`), which stopped being true once the image baked them at `/opt`. Don't call it from the cloud.

## 5. Rules this tool obeys

- Stops pods **by explicit id only**. There is no `--all` / sweep — other projects share the account.
- Defaults to `maya-persist` (`8gu2r2r0hr`, US-TX-3), not Nova's volume.
  `spawn_stream.py` still defaults to `1ditrne6cb` / EU-RO-1, which is **Nova's** volume — do not use
  it for Maya without overriding `RUNPOD_VOLUME_ID` and `RUNPOD_DC`.
- Check mode never receives Facebook or YouTube credentials, so it cannot go on air by accident.
