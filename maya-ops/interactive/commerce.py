"""
commerce.py — buy-link + on-air commerce copy (T4).
The catalog contract (maya-server/catalog.json _meta.commerce):
  payment_link null  -> the post_link tool ALERTS the operator, never posts a
                        broken/fake link. Human sets it when a processor is picked.
  coupon             -> per-stream attribution code; also the sale-proof.
UTM is appended so a sale can be traced to the live (report T4 attribution).

Pure-python, no deps. Unit-tested off the pod. Wiring (pod phase): the director's
BUY/ME/LINK keyword path calls post_link_decision(); go-live calls
youtube_description()/pinned_comment(); the state machine PITCH beat shows
price_banner() and overlays a QR of buy_url().
"""
from __future__ import annotations
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

DEFAULT_UTM = "utm_source=youtube&utm_medium=live&utm_campaign=serum_demo"
AI_DISCLOSURE = ("AI disclosure: Maya is an AI-generated host (voice and face are "
                 "synthetic). The product is real and all product details stated are accurate.")


def buy_url(payment_link, coupon=None, utm: str = DEFAULT_UTM):
    """Compose the final buy URL with UTM + coupon params. None if no link set."""
    if not payment_link:
        return None
    parts = urlparse(payment_link)
    q = dict(parse_qsl(parts.query))
    if utm:
        q.update(dict(parse_qsl(utm)))
    if coupon:
        q["coupon"] = coupon
    return urlunparse(parts._replace(query=urlencode(q)))


def post_link_decision(product: dict, name: str | None = None) -> dict:
    """Decide what the BUY/ME/LINK path does. Honors the null->alert contract."""
    link = buy_url(product.get("payment_link"), product.get("coupon"))
    if not link:
        return {
            "action": "alert_operator",
            "url": None,
            "operator_msg": f"[BUY intent from {name or 'a viewer'}] but payment_link is "
                            f"null for {product.get('name_en')} — set it in catalog.json.",
            "spoken": None,
        }
    disp = product.get("name_en", "the product")
    return {
        "action": "post",
        "url": link,
        "operator_msg": None,
        # spoken reply is name-first; the actual URL is posted as a TEXT reply,
        # never read aloud digit-by-digit.
        "spoken": f"the link is pinned right below — tap it and it takes you straight to {disp}.",
        "chat_reply": f"🛒 {disp}: {link}",
    }


def price_line(product: dict) -> str:
    p = product.get("price_he") or product.get("price", "")
    old = product.get("old_price_he") or product.get("old_price", "")
    if old:
        return f"{old} → {p} (live)"
    return str(p)


def price_banner(product: dict) -> str:
    return f"{product.get('name_en','')} · {price_line(product)}"


def youtube_description(product: dict, link: str | None = None) -> str:
    link = link or buy_url(product.get("payment_link"), product.get("coupon")) or "[PRODUCT LINK — set when processor picked]"
    bullets = product.get("bullets") or []
    lines = [
        f"{product.get('name_en','')} — LIVE with Maya.",
        " · ".join(bullets) if bullets else "",
        f"Live price {price_line(product)}. {product.get('delivery_note','')}".strip(),
        "",
        f"🛒 Shop: {link}",
        "",
        f"⚠️ {AI_DISCLOSURE}",
    ]
    return "\n".join(l for l in lines if l is not None)


def pinned_comment(product: dict, link: str | None = None) -> str:
    link = link or buy_url(product.get("payment_link"), product.get("coupon")) or "[link coming up]"
    return f"🛒 {product.get('name_en','')} — {price_line(product)} · {link}"


if __name__ == "__main__":
    serum = {
        "name_en": "Concentrated Vitamin C Serum",
        "price": "149 ILS", "old_price": "249 ILS",
        "price_he": "₪149", "old_price_he": "₪249",
        "delivery_note": "3-5 business days, free shipping over 200 ILS",
        "bullets": ["20% pure vitamin C", "30 ml bottle", "Suitable for daily morning use"],
        "payment_link": None, "coupon": None,
    }

    # null link -> alert operator, never a fake url
    d = post_link_decision(serum, name="Dana")
    assert d["action"] == "alert_operator" and d["url"] is None
    assert "payment_link is null" in d["operator_msg"]

    # once a processor is set -> compose with UTM + coupon
    serum_live = dict(serum, payment_link="https://buy.stripe.com/abc123", coupon="LIVE28")
    url = buy_url(serum_live["payment_link"], serum_live["coupon"])
    assert url.startswith("https://buy.stripe.com/abc123?")
    assert "utm_source=youtube" in url and "coupon=LIVE28" in url
    d2 = post_link_decision(serum_live, name="Tom")
    assert d2["action"] == "post" and d2["url"] == url
    assert d2["chat_reply"].startswith("🛒") and url in d2["chat_reply"]
    # spoken reply never contains the raw url (not read aloud)
    assert "http" not in d2["spoken"]

    # description carries product line + price + link + AI disclosure
    desc = youtube_description(serum_live)
    assert "Concentrated Vitamin C Serum" in desc
    assert "₪249 → ₪149" in desc and url in desc
    assert "AI disclosure" in desc

    # null-link description uses the safe placeholder, not a fake url
    desc0 = youtube_description(serum)
    assert "set when processor picked" in desc0 and "AI disclosure" in desc0

    assert price_banner(serum_live) == "Concentrated Vitamin C Serum · ₪249 → ₪149 (live)"
    print("commerce self-test: PASS")
    print(price_banner(serum_live))
    print("--- pinned ---"); print(pinned_comment(serum_live))
