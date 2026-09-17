# maya-ops/host — Maya commercial host on OpenTalking (+ director on-screen layer)
Chain: brain_server → OpenTalking (QuickTalk) → mediamtx (local) → director.py (PiP/cutaway/banner/chat/timer) → Facebook/Amazon/YouTube
Boot: bash ot_boot.sh [boot | live N | planted N | down]   ·   Persist once: ot_persist.sh   ·   mediamtx: mediamtx_setup.sh
Host runtime: maya_ot.py (ack <1s, answers voice+face+text ⏱, beats, busy batching, reactions, gestures, metrics, report)
Offline QA: python3 qa_run.py (10/10 expected; run director.py --source test in parallel to test overlays)
Selling layer control: POST :8796 /scene /banner /chat /timer · Clips: clip_cutter.py · Voice A/B: voice_bench.py · Policy: set_policy.py
Products: onboard_product.py brief.json --out clients/x → switch_product.sh clients/x · Amazon: amazon_go.sh · Audience: invite_kit.md
