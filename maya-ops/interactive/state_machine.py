"""
state_machine.py — Maya's body: IDLE -> LISTEN -> SPEAK -> PITCH -> IDLE (T3).
Avatar swap is HTTP /set_avatar on the engine; transitions apply ONLY at clip
boundaries (never mid-clip). The machine resolves each logical state to the BEST
available baked avatar, so it runs today on the fallback set and AUTO-UPGRADES
the moment the human's Kling idle/gesture clips are baked. No deps; unit-tested.

Wiring (pod phase): director calls request(state) as events happen
(comment arrives -> LISTEN; maya starts speaking -> SPEAK; product beat -> PITCH;
idle -> IDLE) and calls on_boundary() when the current clip loops; if it returns
an avatar id, POST engine /set_avatar?id=<that>.
"""
from __future__ import annotations
from dataclasses import dataclass, field

IDLE, LISTEN, SPEAK, PITCH = "IDLE", "LISTEN", "SPEAK", "PITCH"

# ordered preference per state — first AVAILABLE baked avatar wins.
PREF = {
    IDLE:   ["maya_idle", "maya_serum"],
    LISTEN: ["maya_listen", "maya_nudge", "maya_idle", "maya_serum"],
    SPEAK:  ["maya_speak", "maya_serum", "maya_idle"],
    PITCH:  ["maya_serum", "maya_point", "maya_bothhand", "maya_idle"],
}
# the dedicated interactive clips that unlock "full" mode when baked.
UPGRADE_CLIPS = {"maya_listen", "maya_speak", "maya_invite"}
# cutaways playable UNDER her voice on these answer topics (B-roll, not a swap).
CUTAWAY_TOPIC = {"texture": "cutaway_examine", "usage": "cutaway_apply"}


@dataclass
class HostStateMachine:
    available: frozenset = field(default_factory=frozenset)  # baked avatar ids present
    cutaways: frozenset = field(default_factory=frozenset)   # cutaway ids present
    state: str = IDLE
    _pending: str | None = None
    current_avatar: str | None = None

    def __post_init__(self):
        self.available = frozenset(self.available)
        self.cutaways = frozenset(self.cutaways)
        self.current_avatar = self.resolve_avatar(self.state)

    def resolve_avatar(self, state: str) -> str | None:
        for a in PREF.get(state, []):
            if a in self.available:
                return a
        # last resort: anything baked, so she is never a black frame
        return next(iter(sorted(self.available)), None)

    def mode(self) -> str:
        """'full' once dedicated interactive clips exist, else the 2-state fallback."""
        return "full" if (self.available & UPGRADE_CLIPS) else "fallback_2state"

    def request(self, state: str) -> None:
        if state not in PREF:
            raise ValueError(f"unknown state {state!r}")
        self._pending = state

    def on_boundary(self) -> str | None:
        """Apply a pending transition at a clip boundary. Returns the avatar id to
        swap to, or None if no swap is needed (same avatar or nothing pending)."""
        if self._pending is None:
            return None
        target_state = self._pending
        self._pending = None
        self.state = target_state
        target_avatar = self.resolve_avatar(target_state)
        if target_avatar and target_avatar != self.current_avatar:
            self.current_avatar = target_avatar
            return target_avatar
        return None

    def cutaway_for(self, topic: str) -> str | None:
        cid = CUTAWAY_TOPIC.get(topic)
        return cid if cid in self.cutaways else None


if __name__ == "__main__":
    # --- fallback set (today): maya_serum + maya_idle baked, two cutaways ---
    sm = HostStateMachine(available={"maya_serum", "maya_idle", "maya_point", "maya_nudge"},
                          cutaways={"cutaway_examine", "cutaway_apply"})
    assert sm.mode() == "fallback_2state"
    assert sm.state == IDLE and sm.current_avatar == "maya_idle"

    # no swap mid-clip: request PITCH, nothing happens until boundary
    sm.request(PITCH)
    assert sm.current_avatar == "maya_idle", "must not swap mid-clip"
    swap = sm.on_boundary()
    assert swap == "maya_serum" and sm.state == PITCH

    # boundary with no pending -> no swap
    assert sm.on_boundary() is None

    # LISTEN resolves to maya_nudge (no maya_listen yet)
    sm.request(LISTEN); assert sm.on_boundary() == "maya_nudge"
    # SPEAK falls back to maya_serum
    sm.request(SPEAK); assert sm.on_boundary() == "maya_serum"
    # requesting the state we already show -> no redundant swap
    sm.request(SPEAK); assert sm.on_boundary() is None

    # cutaways available on texture/usage
    assert sm.cutaway_for("texture") == "cutaway_examine"
    assert sm.cutaway_for("price") is None

    # --- upgraded set (after Kling clips baked): auto-uses the new clips ---
    sm2 = HostStateMachine(available={"maya_serum", "maya_idle", "maya_listen", "maya_speak"},
                           cutaways={"cutaway_examine"})
    assert sm2.mode() == "full"
    sm2.request(LISTEN); assert sm2.on_boundary() == "maya_listen", "auto-upgrade to dedicated clip"
    sm2.request(SPEAK); assert sm2.on_boundary() == "maya_speak"
    # cutaway that isn't baked returns None even for a valid topic
    assert sm2.cutaway_for("usage") is None

    # never a black frame: unknown-only set still resolves something
    sm3 = HostStateMachine(available={"maya_rapa"})
    assert sm3.current_avatar == "maya_rapa"

    print("state_machine self-test: PASS  (mode fallback->full verified)")
