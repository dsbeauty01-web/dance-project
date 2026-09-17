#!/usr/bin/env python3
"""python set_policy.py --ships-to "Israel, USA, EU" --delivery-days "3-5 Israel, 7-14 abroad" --returns "14 days unopened" --payment "credit card, PayPal, Bit"
Writes the catalog policy fields (serum-c.en.json or $MAYA_CATALOG) and adds instant FAQ answers for them."""
import argparse, json, os
ap = argparse.ArgumentParser()
for k in ("ships-to", "delivery-days", "returns", "payment"): ap.add_argument("--" + k, default=None)
a = ap.parse_args(); p = os.environ.get("MAYA_CATALOG", "serum-c.en.json"); d = json.load(open(p, encoding="utf-8"))
prod = d["products"][0] if isinstance(d, dict) and "products" in d else d
pol = prod.setdefault("policy", {}); faq = prod.setdefault("faq", [])
def add(q, ans):
    faq[:] = [f for f in faq if (f.get("q") or "") != q]; faq.append({"q": q, "a": ans})
if a.ships_to: pol["ships_to"] = a.ships_to; add("do you ship to", f"We ship to {a.ships_to}. Details in the link below.")
if a.delivery_days: pol["delivery_days"] = a.delivery_days; add("how long delivery", f"Delivery takes {a.delivery_days}.")
if a.returns: pol["returns"] = a.returns; add("returns", f"Returns: {a.returns}.")
if a.payment: pol["payment_methods"] = a.payment; add("how can I pay", f"You can pay with {a.payment}.")
pol.pop("_note", None); json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2); print("policy set:", {k: v for k, v in pol.items()})
