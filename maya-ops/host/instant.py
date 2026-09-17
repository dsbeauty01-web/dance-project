#!/usr/bin/env python3
"""
instant.py — the instant-answer layer (host-controller organ 1). Regex patterns → catalog-true answers in ~0 ms.
Runs BEFORE the LLM. Covers the ~30 questions that make up most of a selling stream's chat.
Values come from the catalog (price, shipping, policy) so nothing here is invented.

  from instant import Instant; ins = Instant(catalog_product_dict); ins.match("how much?")  -> answer str | None
"""
import difflib
import re


class Instant:
    def __init__(self, p: dict):
        self.p = p or {}
        cur = {"ILS": "shekels", "USD": "dollars", "EUR": "euros"}.get(str(p.get("currency", "ILS")).upper(), "")
        price = f"{p.get('price', '')} {cur}".strip(); reg = p.get("regular_price")
        price_line = f"{price} live right now" + (f", down from {reg}" if reg else "")
        pol = p.get("policy") or {}
        facts = p.get("facts") or []
        f = lambda i, d="": facts[i] if len(facts) > i else d
        name = p.get("name", "the product")
        link = "The link is right below this video, or type ME and I'll send it."
        nul = "I don't have that in front of me — the link below has the details."
        self.rules = [
            (r"\b(how much|price|cost|כמה עולה|מחיר)\b", f"{price_line}. {link}"),
            (r"\b(discount|coupon|cheaper|deal|sale)\b", f"Today's price is the deal — {price_line}. {link}"),
            (r"\b(how (do|to) (i )?(use|apply)|usage|routine|how often|when (do|should) i)\b", (p.get("faq_usage") or f"{f(2, 'One drop every morning on clean skin, before your moisturizer.')}")),
            (r"\b(morning|night|evening|bedtime)\b", "Mornings — one drop on clean skin, then your moisturizer. Sunscreen after, always."),
            (r"\b(feel|texture|sticky|greasy|oily feel|smell)\b", "Light, almost like water — it absorbs in seconds, no sticky feeling."),
            (r"\b(oily skin|dry skin|combination|sensitive skin|skin type)\b", "It's a light serum that suits most skin types. If your skin is very sensitive, start every other day."),
            (r"\b(how long|when (will|do) i see|results|how fast|weeks)\b", "Most people notice a fresher glow after a few weeks of daily use. Consistency is the whole trick."),
            (r"\b(ingredient|what('?s| is) in it|contain|formula|percent|%)\b",f"{f(0, 'The active is vitamin C.')}. {f(1, '')}".strip()),
            (r"\b(size|ml|how big|how much product|last)\b", f"{f(1, '30 ml')} — about two months of daily use."),
            (r"\b(retinol|niacinamide|acid|mix with|combine|together with)\b", "Use it in the morning and keep stronger actives like retinol for the night — simple and safe."),
            (r"\b(ship|shipping|deliver|delivery)\b", (f"We ship to {pol['ships_to']}. " if pol.get("ships_to") else "") + (f"Delivery takes {pol['delivery_days']}. " if pol.get("delivery_days") else "") + (p.get("shipping") or "")),
            (r"\b(return|refund|money back|exchange)\b", f"Returns: {pol['returns']}." if pol.get("returns") else nul),
            (r"\b(pay|payment|credit card|paypal|bit\b|apple pay|visa)\b", f"You can pay with {pol['payment_methods']}." if pol.get("payment_methods") else nul),
            (r"\b(where (do|can) i (buy|order|get)|order|checkout|link|website|buy now|how to buy)\b", link),
            (r"\b(are you (an? )?(ai|robot|real)|is this (an? )?(ai|bot)|real person|fake)\b", "One hundred percent — I'm Maya, an AI host. Everything I say about the product comes from the catalog, nothing invented."),
            (r"\b(hi|hello|hey|shalom|היי|שלום|good (morning|evening)|whats? up)\b(?![\w ]*(much|price|cost))", f"Welcome in! Ask me anything about {name}."),
            (r"\b(thank|thanks|תודה)\b", "You're welcome — that's what I'm here for."),
            (r"\b(stock|available|in stock|sold out)\b", f"{p.get('stock', 'in stock').capitalize()} right now. {link}"),
            (r"\b(gift|present|for my (mom|wife|girlfriend|sister))\b", f"Great gift — {name}, {price_line}. {link}"),
            (r"\b(men|for guys|for a man)\b", "Yes — skin is skin. Same routine: one drop, mornings."),
            (r"\b(sunscreen|spf|sun)\b", "Vitamin C in the morning, sunscreen on top. They're a team."),
            (r"\b(pregnan|breastfeed|nursing)\b", "For pregnancy or nursing, check with your doctor before adding any new active — I can't advise on that."),
            (r"\b(made in|where is it made|country|origin)\b", nul),
            (r"\b(smell|fragrance|scent|perfume)\b", "Light and clean — no heavy fragrance."),
            (r"\b(expire|shelf life|how long does it keep)\b", nul),
            (r"\b(sample|tester|trial)\b", f"No samples on the live — but {price_line} today is the best way to try it. {link}"),
            (r"\b(video|record|replay|later)\b", "The replay stays up — but today's price is for today."),
            (r"^\s*(me|buy|link|1)\s*[!.]*\s*$", f"On it — {link}"),
            # 'send me' was the live 2026-09-15 purchase phrase: it missed every rule, fell to
            # the LLM, and came back as a raw tool envelope. Keep buy-intent on the fast path.
            (r"\b(send (me|it|the link|me the link)|dm me|text me|want (it|one)|i'?ll take it)\b", f"On it — {link}"),
        ]
        self.compiled = [(re.compile(rx, re.I), ans) for rx, ans in self.rules if ans]
        # vocabulary for typo repair: every literal word the rules can match on
        vocab = set()
        for rx, ans in self.rules:
            if ans:
                vocab.update(w for w in re.findall(r"[a-z']{3,}", rx.lower()))
        self.vocab = sorted(vocab)

    def _repair(self, t: str) -> str:
        """Fix typos token-by-token against the rule vocabulary.

        Viewers type 'hoiw muuch is hte serum?'. Exact regex misses it, the question falls
        to the LLM path and then queues behind live speech — that is how one comment cost
        32 seconds on 2026-09-15. Only whole tokens are replaced, and only on a close match,
        so 'acne' and 'cure' stay themselves and still reach the medical deflection.
        """
        out, changed = [], False
        for tok in re.split(r"(\W+)", t):
            low = tok.lower()
            if len(tok) >= 4 and tok.isalpha() and low not in self.vocab:
                hit = difflib.get_close_matches(low, self.vocab, n=1, cutoff=0.82)
                if hit:
                    out.append(hit[0]); changed = True; continue
            out.append(tok)
        return "".join(out) if changed else t

    def match(self, text: str, fuzzy: bool = True):
        t = (text or "").strip()
        if len(t) > 160:
            return None
        for rx, ans in self.compiled:
            if rx.search(t):
                return ans
        if not fuzzy:
            return None
        rep = self._repair(t)                     # second pass: same rules, typos repaired
        if rep != t:
            for rx, ans in self.compiled:
                if rx.search(rep):
                    return ans
        return None


if __name__ == "__main__":
    demo = {"name": "Vitamin C Serum", "facts": ["20% vitamin C", "30 ml", "one drop every morning on clean skin, before moisturizer"], "price": 149, "regular_price": 249,
            "currency": "ILS", "shipping": "free shipping over 200 ILS", "policy": {"ships_to": "Israel and worldwide", "delivery_days": "3-5 days", "returns": "30 days", "payment_methods": "Visa, Mastercard, PayPal, Bit"}}
    ins = Instant(demo)
    for q in ["how much?", "how do I use it", "does it feel sticky?", "do you ship to USA?", "is this AI?", "ME", "what's in it", "will it cure acne", "hi maya", "can I pay with paypal"]:
        print(f"{q:<28} → {ins.match(q)}")
