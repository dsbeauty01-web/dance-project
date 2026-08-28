"""
answer_discipline.py — the "answer discipline" gate (T2).
Rules (from the live-sales playbook, spec T2):
  - name-first ALWAYS
  - max ~2 answers / minute (sliding 60s window)
  - >=8s between cues (improvised beats/fillers)
  - never answer the same user twice in a row if others are waiting
  - purchase-intent and greeting-by-name get priority; noise sinks

Clock is injected (`now` = monotonic seconds) so this is deterministic and
unit-testable off the pod. Wiring (pod phase): the director (maya-server) holds
one AnswerGate per session and calls admit_answer() before forwarding a comment
to the pod /rt `chat` handler; record_answer() when maya-said fires.
"""
from __future__ import annotations
from dataclasses import dataclass, field

# priority ranks (higher = answered first). Mirrors W2 classify labels.
PRIORITY = {
    "buy_intent": 40,
    "greeting": 30,          # greeting-with-name
    "question_shipping_price": 25,
    "question_product": 20,
    "noise": 0,
}


def priority_of(label: str) -> int:
    return PRIORITY.get(label, 10)


def name_first(name: str, body: str) -> str:
    """Prefix the reply with the viewer's name, unless it already leads with it."""
    name = (name or "").strip()
    body = (body or "").strip()
    if not name:
        return body
    if body.lower().startswith(name.lower()):
        return body
    return f"{name}, {body}"


@dataclass
class AnswerGate:
    max_answers_per_min: int = 2
    min_cue_interval_s: float = 8.0
    _answer_times: list[float] = field(default_factory=list)
    _cue_times: list[float] = field(default_factory=list)
    last_answered_user: str | None = None

    def _recent_answers(self, now: float) -> int:
        self._answer_times = [t for t in self._answer_times if now - t < 60.0]
        return len(self._answer_times)

    def admit_answer(self, user_id: str, now: float, others_waiting: bool = False) -> tuple[bool, str]:
        """Decide whether to answer this comment right now."""
        if self._recent_answers(now) >= self.max_answers_per_min:
            return False, "rate_limited_2_per_min"
        if others_waiting and user_id is not None and user_id == self.last_answered_user:
            return False, "same_user_back_to_back"
        return True, "ok"

    def record_answer(self, user_id: str, now: float) -> None:
        self._answer_times.append(now)
        self.last_answered_user = user_id

    def admit_cue(self, now: float) -> tuple[bool, str]:
        self._cue_times = [t for t in self._cue_times if now - t < 60.0]
        if self._cue_times and (now - self._cue_times[-1]) < self.min_cue_interval_s:
            return False, "cue_8s_interval"
        return True, "ok"

    def record_cue(self, now: float) -> None:
        self._cue_times.append(now)

    @staticmethod
    def pick_next(queue: list[dict]) -> dict | None:
        """Highest priority first; ties break by arrival order (stable)."""
        pending = [m for m in queue if priority_of(m.get("priority", "")) > 0]
        if not pending:
            return None
        return max(pending, key=lambda m: (priority_of(m.get("priority", "")), -m.get("_i", 0)))


if __name__ == "__main__":
    g = AnswerGate(max_answers_per_min=2, min_cue_interval_s=8.0)

    # name-first
    assert name_first("Dana", "one drop every morning.") == "Dana, one drop every morning."
    assert name_first("Dana", "Dana, hi!") == "Dana, hi!"           # no double
    assert name_first("", "hello") == "hello"

    # rate limit: 2/min then blocked, frees after 60s
    ok, _ = g.admit_answer("u1", now=0.0); assert ok; g.record_answer("u1", 0.0)
    ok, _ = g.admit_answer("u2", now=5.0); assert ok; g.record_answer("u2", 5.0)
    ok, why = g.admit_answer("u3", now=10.0); assert not ok and why == "rate_limited_2_per_min"
    ok, _ = g.admit_answer("u3", now=66.0); assert ok, "window should slide open after 60s"

    # same user back-to-back only blocked when others wait
    g2 = AnswerGate()
    g2.record_answer("dana", 0.0)
    ok, why = g2.admit_answer("dana", now=1.0, others_waiting=True); assert not ok and why == "same_user_back_to_back"
    ok, _ = g2.admit_answer("dana", now=1.0, others_waiting=False); assert ok, "solo repeat is fine"

    # cue 8s interval
    g3 = AnswerGate()
    ok, _ = g3.admit_cue(0.0); assert ok; g3.record_cue(0.0)
    ok, why = g3.admit_cue(3.0); assert not ok and why == "cue_8s_interval"
    ok, _ = g3.admit_cue(9.0); assert ok

    # priority ordering
    q = [
        {"_i": 0, "priority": "question_product", "name": "A"},
        {"_i": 1, "priority": "buy_intent", "name": "B"},
        {"_i": 2, "priority": "greeting", "name": "C"},
        {"_i": 3, "priority": "noise", "name": "D"},
    ]
    nxt = AnswerGate.pick_next(q)
    assert nxt["name"] == "B", nxt
    assert AnswerGate.pick_next([{"_i": 0, "priority": "noise"}]) is None

    print("answer_discipline self-test: PASS")
