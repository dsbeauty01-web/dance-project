#!/usr/bin/env python3
"""python set_buy_url.py https://buy.stripe.com/xxxx   → writes buy_url into the catalog product (serum-c.en.json)"""
import json, os, sys
p = os.environ.get("MAYA_CATALOG", "serum-c.en.json")
url = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: set_buy_url.py <URL>")
d = json.load(open(p, encoding="utf-8"))
def patch(obj):
    if isinstance(obj, dict):
        if "name" in obj and ("price" in obj or "facts" in obj): obj["buy_url"] = url; return 1
        return sum(patch(v) for v in obj.values())
    if isinstance(obj, list): return sum(patch(v) for v in obj)
    return 0
n = patch(d); json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"buy_url set on {n} product(s) in {p}")
