"""
cost_meter.py — Realtime audio cost accounting + hard per-session cap.
Maya interactive build (T1 ground rule #2): "Realtime audio costs real money
(~$0.06/min in, $0.24/min out): build a cost meter + hard cap per session
(default $3, config). Log minutes."

Pure-python, no deps, deterministic — so it is unit-testable off the pod.
Wiring (pod phase): maya_rt.py accumulates input/output audio seconds from the
Realtime stream and periodically POSTs to maya-server /vitals; the director
holds ONE CostMeter per session, and when .tripped() flips True it fires the
kill switch (mute brain + drop to the scripted loop) — the stream never freezes,
it just stops spending.
"""
from __future__ import annotations
from dataclasses import dataclass, field

# Default OpenAI Realtime audio rates (USD per minute). Override per session
# from config if the model/pricing changes — never hard-code money in two places.
DEFAULT_IN_RATE_PER_MIN = 0.06
DEFAULT_OUT_RATE_PER_MIN = 0.24
DEFAULT_HARD_CAP_USD = 3.00


@dataclass
class CostMeter:
    hard_cap_usd: float = DEFAULT_HARD_CAP_USD
    in_rate_per_min: float = DEFAULT_IN_RATE_PER_MIN
    out_rate_per_min: float = DEFAULT_OUT_RATE_PER_MIN
    # accumulated audio, in SECONDS (what the Realtime stream reports)
    in_secs: float = 0.0
    out_secs: float = 0.0
    _tripped_at: float | None = field(default=None)

    def add_audio(self, in_secs: float = 0.0, out_secs: float = 0.0) -> None:
        """Accumulate input (mic/viewer) and output (Maya speaking) audio seconds."""
        if in_secs < 0 or out_secs < 0:
            raise ValueError("audio seconds must be >= 0")
        self.in_secs += in_secs
        self.out_secs += out_secs
        if self._tripped_at is None and self.cost_usd >= self.hard_cap_usd:
            self._tripped_at = self.cost_usd

    @property
    def in_min(self) -> float:
        return self.in_secs / 60.0

    @property
    def out_min(self) -> float:
        return self.out_secs / 60.0

    @property
    def cost_usd(self) -> float:
        return round(self.in_min * self.in_rate_per_min
                     + self.out_min * self.out_rate_per_min, 4)

    def tripped(self) -> bool:
        """True once the session has reached/exceeded the hard cap. Latches."""
        return self._tripped_at is not None

    def remaining_usd(self) -> float:
        return round(max(0.0, self.hard_cap_usd - self.cost_usd), 4)

    def pct_of_cap(self) -> float:
        if self.hard_cap_usd <= 0:
            return 100.0
        return round(min(100.0, self.cost_usd / self.hard_cap_usd * 100.0), 1)

    def vitals(self) -> dict:
        """Shape the director already expects on /vitals (voice_cost_est_usd)."""
        return {
            "voice_cost_est_usd": self.cost_usd,
            "in_min": round(self.in_min, 3),
            "out_min": round(self.out_min, 3),
            "cap_usd": self.hard_cap_usd,
            "pct_of_cap": self.pct_of_cap(),
            "remaining_usd": self.remaining_usd(),
            "tripped": self.tripped(),
        }

    def log_line(self) -> str:
        return ("[cost] ${:.3f}/{:.2f} ({}%) | in {:.2f}m @${}/m, out {:.2f}m @${}/m{}"
                .format(self.cost_usd, self.hard_cap_usd, self.pct_of_cap(),
                        self.in_min, self.in_rate_per_min,
                        self.out_min, self.out_rate_per_min,
                        "  << HARD CAP -- DROP TO LOOP" if self.tripped() else ""))


if __name__ == "__main__":
    # --- self-test (real green: computed, not estimated) ---
    m = CostMeter(hard_cap_usd=3.00)
    assert m.cost_usd == 0.0 and not m.tripped()
    # 1 min in + 1 min out = 0.06 + 0.24 = 0.30
    m.add_audio(in_secs=60, out_secs=60)
    assert m.cost_usd == 0.30, m.cost_usd
    assert not m.tripped() and m.remaining_usd() == 2.70
    # push to the cap: need $2.70 more. Output-only: 2.70/0.24 = 11.25 min = 675s
    m.add_audio(out_secs=675)
    assert m.cost_usd >= 3.00, m.cost_usd
    assert m.tripped(), "should latch tripped at cap"
    # stays tripped even if no more audio
    before = m.tripped()
    m.add_audio(in_secs=0)
    assert m.tripped() == before
    # negative guarded
    try:
        m.add_audio(in_secs=-1); assert False
    except ValueError:
        pass
    # pct + vitals shape
    v = m.vitals()
    assert set(v) >= {"voice_cost_est_usd", "cap_usd", "tripped", "remaining_usd"}
    assert v["tripped"] is True and v["remaining_usd"] == 0.0
    print("cost_meter self-test: PASS")
    print(m.log_line())
    print(v)
