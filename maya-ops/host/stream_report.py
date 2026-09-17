#!/usr/bin/env python3
"""
stream_report.py — the client deliverable after every live. Reads maya_host.db (answers, leads, latency)
+ Facebook Graph (viewers, comments, reactions) → reports/<date>/stream_report.md + .html

  python stream_report.py --video-id <FB_VIDEO_ID> [--since "2026-09-08 18:00"] [--cost 0.9]
ENV: MAYA_DB (default maya_host.db) · FB_PAGE_TOKEN · FB_API_VERSION
"""
import argparse, json, os, sqlite3, statistics, time
from datetime import datetime
import requests

E = os.environ.get
for p in (os.path.expanduser("~/.maya/host.env"),):
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip().strip('"'))
G = f"https://graph.facebook.com/{E('FB_API_VERSION', 'v21.0')}"


def fb_stats(video_id: str) -> dict:
    tok = E("FB_PAGE_TOKEN", "")
    if not (tok and video_id):
        return {}
    out = {}
    try:
        v = requests.get(f"{G}/{video_id}", params={"fields": "title,live_status,permalink_url,length", "access_token": tok}, timeout=15).json()
        out["title"] = v.get("title"); out["permalink"] = "https://www.facebook.com" + (v.get("permalink_url") or "")
        ins = requests.get(f"{G}/{video_id}/video_insights", params={"metric": "total_video_views,total_video_impressions,total_video_view_total_time,total_video_avg_time_watched",
                           "access_token": tok}, timeout=15).json()
        for m in ins.get("data", []):
            out[m["name"]] = (m.get("values") or [{}])[0].get("value")
        c = requests.get(f"{G}/{video_id}/comments", params={"summary": "true", "limit": 1, "filter": "stream", "access_token": tok}, timeout=15).json()
        out["comments_total"] = (c.get("summary") or {}).get("total_count")
        r = requests.get(f"{G}/{video_id}/reactions", params={"summary": "total_count", "limit": 1, "access_token": tok}, timeout=15).json()
        out["reactions_total"] = (r.get("summary") or {}).get("total_count")
    except Exception as e:
        out["fb_error"] = str(e)
    return out


def db_stats(db_path: str, since_ts: float) -> dict:
    if not os.path.exists(db_path):
        return {}
    db = sqlite3.connect(db_path)
    ans = db.execute("SELECT user_key, question, answer, latency, ts FROM answers WHERE ts>=? ORDER BY ts", (since_ts,)).fetchall()
    leads = db.execute("SELECT ts, name, platform, intent, message FROM leads WHERE ts>=?", (since_ts,)).fetchall()
    viewers = db.execute("SELECT COUNT(*) FROM viewers WHERE last_seen>=?", (since_ts,)).fetchone()[0]
    lat = [a[3] for a in ans if a[3] is not None]
    named = sum(1 for a in ans if a[2] and "—" in a[2][:40])
    return {"answers": len(ans), "answered_by_name_pct": round(100 * named / len(ans)) if ans else 0,
            "latency_median_s": round(statistics.median(lat), 1) if lat else None, "latency_worst_s": round(max(lat), 1) if lat else None,
            "leads": len(leads), "unique_viewers_in_chat": viewers,
            "lead_rows": [{"time": datetime.fromtimestamp(l[0]).strftime("%H:%M"), "name": l[1], "platform": l[2], "intent": l[3]} for l in leads],
            "samples": [{"q": a[1][:80], "a": a[2][:120], "s": round(a[3], 1) if a[3] else None} for a in ans[:8]]}


def render(fb: dict, d: dict, cost: float, since: str) -> str:
    L = [f"# Maya stream report — {since}", ""]
    if fb.get("title"):
        L += [f"**{fb['title']}**  ", f"{fb.get('permalink','')}", ""]
    L += ["## Numbers", "",
          f"- Views: {fb.get('total_video_views','n/a')} · Impressions: {fb.get('total_video_impressions','n/a')} · Avg watch: {fb.get('total_video_avg_time_watched','n/a')} ms",
          f"- Comments: {fb.get('comments_total','n/a')} · Reactions: {fb.get('reactions_total','n/a')} · Unique people in chat: {d.get('unique_viewers_in_chat','n/a')}",
          f"- Answered by Maya: {d.get('answers',0)} ({d.get('answered_by_name_pct',0)}% by name) · Median comment→voice: {d.get('latency_median_s','n/a')}s · Worst: {d.get('latency_worst_s','n/a')}s",
          f"- Leads captured (ME/BUY): {d.get('leads',0)}", f"- Cost of this stream: ${cost:.2f}", ""]
    if d.get("lead_rows"):
        L += ["## Leads", ""] + [f"- {r['time']} · {r['name']} · {r['platform']} · {r['intent']}" for r in d["lead_rows"]] + [""]
    if d.get("samples"):
        L += ["## What she answered (samples)", ""] + [f"- **{s['q']}** → {s['a']} ({s['s']}s)" for s in d["samples"]] + [""]
    L += ["## Next stream", "", "- Add the 3 most-asked questions to the instant-answer list", "- Refresh one product beat", "- Keep the price line exactly as approved", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--video-id", default=E("FB_VIDEO_ID", "")); ap.add_argument("--since", default="")
    ap.add_argument("--cost", type=float, default=0.0); ap.add_argument("--out", default="")
    a = ap.parse_args()
    since_ts = datetime.fromisoformat(a.since).timestamp() if a.since else time.time() - 6 * 3600
    since = a.since or datetime.fromtimestamp(since_ts).strftime("%Y-%m-%d %H:%M")
    fb, d = fb_stats(a.video_id), db_stats(E("MAYA_DB", "maya_host.db"), since_ts)
    md = render(fb, d, a.cost, since)
    out = a.out or os.path.join("reports", datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "stream_report.md"), "w", encoding="utf-8").write(md)
    html = "<!doctype html><meta charset=utf-8><style>body{font:16px/1.5 system-ui;max-width:760px;margin:40px auto;padding:0 20px;color:#14213d}h1{font-size:28px}h2{font-size:18px;margin-top:28px}li{margin:4px 0}</style>"
    html += "".join(f"<h1>{l[2:]}</h1>" if l.startswith("# ") else f"<h2>{l[3:]}</h2>" if l.startswith("## ") else f"<li>{l[2:]}</li>" if l.startswith("- ") else f"<p>{l}</p>" if l else "" for l in md.splitlines())
    open(os.path.join(out, "stream_report.html"), "w", encoding="utf-8").write(html.replace("**", ""))
    json.dump({"fb": fb, "db": d, "cost": a.cost}, open(os.path.join(out, "raw.json"), "w"), indent=2)
    print(md); print("→", out)


if __name__ == "__main__":
    main()
