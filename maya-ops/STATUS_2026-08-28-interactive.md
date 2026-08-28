# STATUS — Maya Interactive Host Build (2026-08-28)
Branch `maya-p1-finish`. Executes `maya-interactive-build-2026-08-28.md`.
**Honest state:** the interactive host already existed in v1 (`maya_rt.py` Realtime pipe +
`maya-server` director + n8n W1/W2/W3). This session closed the *logic* gaps with tested,
pod-free modules and a precise wiring plan. **Nothing pod-dependent is claimed working** —
live validation is the T6 dry run, which needs a pod (asked-for, not run).

## Per-task

| Task | State | Detail |
|---|---|---|
| **T1** Ears+mouth (Realtime) | PARTIAL | Realtime voice-to-voice pipe already exists (`maya_rt.py`, `gpt-realtime-2`). **Cost meter + hard cap ($3): LOGIC DONE + tested** (`interactive/cost_meter.py`). Barge-in + acknowledge-fast + `/vitals` reporting = **specified, PENDING POD** (must measure, not fake). |
| **T2** Comments in | PARTIAL | W1/W1-FB/W2/W3 exist. **Answer discipline (name-first, ≤2/min, 8s cue, no back-to-back): LOGIC DONE + tested** (`interactive/answer_discipline.py`). Dual **text reply** to chat = build ready, **NEEDS YouTube OAuth**. |
| **T3** Body / state machine | READY | **State machine IDLE→LISTEN→SPEAK→PITCH: LOGIC DONE + tested** (`interactive/state_machine.py`). Runs in `fallback_2state` today (`maya_serum` baked 08-27 + `maya_idle`). Auto-upgrades to `full` when 4 Kling clips are baked — no code change. Wiring PENDING POD. |
| **T4** Money | PARTIAL | Catalog extended (`serum-c.en.json`: buy/price/currency/facts/deflections). **Commerce logic DONE + tested** (`interactive/commerce.py`: buy_url+UTM+coupon, `post_link` alert-on-null, description, pinned, price banner). `catalog.json.payment_link` correctly stays **null** until processor pick. Posting = **NEEDS OAuth**. QR overlay = specified. |
| **T5** Orchestration (golive v3) | SPECIFIED | `maya-golive.mjs`/`godark.mjs` exist. v3 additions (monitors: latency/cost/health/queue; **fallback-to-loop** so stream never freezes; kill switch = existing `/kill`; cost report in godark; auto description+pinned) = **PENDING POD** (needs the running stack to validate the fallback). |
| **T6** Prove it (dry run) | BLOCKED (env) | Attempted on pod `m87z4jkc08ubbk` (08-28). **Blocker found: the interactive RUNTIME is not on a fresh pod** — the `_sys` overlay has torch/cv2/av but **not `flask`/`aiortc`/`aiohttp`** (engine won't import), and the **SRS binary is gone** (only `srs_nova.conf` remains). No latency measured (would be faked otherwise — ground rule #4). Fix committed: `maya-ops/deploy/maya-stack-setup.sh` (UNVERIFIED — run once on a pod to confirm the full dep set), then re-attempt the dry run. |
| **T7** Report | DONE | this file + `interactive/README.md` (wiring spec). |

## Measured (real green)
- `cost_meter` / `answer_discipline` / `commerce` / `state_machine` self-tests: **all PASS** (`python <mod>.py`). These are computed/deterministic, not estimated.
- **No live latency numbers yet** — those are measured in T6 on the pod, never estimated (ground rule #4).

## HUMAN-CLICK LIST (blocks the live upgrade)
1. **Payment processor pick** → then set `catalog.json.payment_link`. See decision below. *(one click to decide, ~10 min to create the link)*
2. **YouTube W1 OAuth re-auth** — unlocks comment ingest + posting text replies / pinned comment / description.
3. **4 Kling clips** — hands-free **idle**, **speak**, **listen**, **invite/gesture** on the serum background. Unlocks `full` state machine (idle→pitch, real gestures). *(prompts already drafted per spec)*
4. **Meta (Facebook Live) submit** — still pending review; W1-FB stays inactive until approved.
5. **URGENT — rotate keys**: RunPod + OpenAI keys are in plaintext in `bake_master.sh` on the volume (flagged 08-25, still open). Rotate + move to `.env`.
6. **Per-stream coupon code** — set `catalog.json.coupon` before each stream (this is the sale-attribution proof).

## PAYMENT PROCESSOR — your decision (T4)
Pick one; I wire `post_link` + description/pinned to it. All three are one-link setups:
- **Stripe Payment Link** — fastest, card + Apple/Google Pay, hosted checkout, no store needed. Best if you don't already sell online.
- **PayPal** — familiar to buyers, quick if you have a PayPal business account.
- **Existing store URL** — if you already have a product page (Shopify/WooCommerce/etc.), just give the URL. Best attribution continuity.
_Israel note: if you use Grow/Meshulam/iCount, give me that checkout URL and it drops straight in._

## Attribution (how we'll know a sale came from the stream)
`buy_url()` appends `utm_source=youtube&utm_medium=live&utm_campaign=serum_demo` + the per-stream
`coupon`. Sales are then countable two ways: UTM in the processor/store analytics, and the coupon
redemptions in the processor dashboard. No coupon = no proof.

## SUGGESTED NEXT BAKES (ranked — do NOT start; needs human clips + a pod)
1. **`maya_idle` hands-free** (biggest lift) — lets her rest naturally, only raising the serum to pitch. Kills the "holds bottle forever" look.
2. **`maya_speak`** — a neutral talking body so SPEAK ≠ PITCH.
3. **`maya_invite` / point-to-link gesture** on the serum set — for CTA beats.
4. **`maya_listen`** — attentive pose while a viewer's question comes in.
