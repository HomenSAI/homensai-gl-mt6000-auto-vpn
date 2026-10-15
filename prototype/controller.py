"""Offline reference controller. No network, credentials, or router write operations."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Policy:
    failures: int = 3
    ready_rounds: int = 2
    recovery_seconds: float = 120
    hold_backup_seconds: float = 300
    cooldown_seconds: float = 30
    max_gap_seconds: float = 15
    min_interval_seconds: float = 5
    auto_return: bool = True

    def __post_init__(self):
        for name in ("failures", "ready_rounds"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(name)
        for name in ("recovery_seconds", "hold_backup_seconds", "cooldown_seconds", "max_gap_seconds", "min_interval_seconds"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(name)
        if type(self.auto_return) is not bool:
            raise ValueError("auto_return")
        if self.min_interval_seconds > self.max_gap_seconds:
            raise ValueError("sampling intervals")


def validate_snapshot(s):
    """Reject missing, stale, or unproven evidence rather than treating it as success."""
    required = {"time", "active", "operator_revision", "wan", "manual_override", "primary", "backup"}
    if type(s) is not dict or set(s) != required:
        raise ValueError("snapshot fields")
    if type(s["time"]) not in (int, float) or not math.isfinite(s["time"]) or s["time"] < 0:
        raise ValueError("time")
    if s["active"] not in ("primary", "backup", "none"):
        raise ValueError("active")
    if type(s["operator_revision"]) is not int or s["operator_revision"] < 0:
        raise ValueError("operator_revision")
    if s["wan"] not in ("up", "down", "unknown") or type(s["manual_override"]) is not bool:
        raise ValueError("wan/manual_override")
    for name in ("primary", "backup"):
        health = s[name]
        if type(health) is not dict or set(health) != {"interface_up", "route_verified", "dns_ok", "https"}:
            raise ValueError("health fields")
        if any(type(health[key]) is not bool for key in ("interface_up", "route_verified", "dns_ok")):
            raise ValueError("health booleans")
        targets = health["https"]
        if type(targets) is not dict or len(targets) != 3:
            raise ValueError("three independent HTTPS targets required")
        if any(type(k) is not str or not k or len(k) > 64 or type(v) is not bool for k, v in targets.items()):
            raise ValueError("target result")


def health_status(health):
    if not health["route_verified"]:
        return "UNVERIFIED_ROUTE"
    if not health["interface_up"]:
        return "TUNNEL_DOWN"
    if sum(health["https"].values()) < 2:
        return "INTERNET_DOWN"
    if not health["dns_ok"]:
        return "DNS_DEGRADED"
    return "OK"


class Controller:
    """Propose only. Actual route state is reconciled from each input snapshot.

    operator_revision is an operator-config revision, not an automatic UCI commit
    counter. A future adapter must produce it reliably before live mode is possible.
    """
    def __init__(self, policy=None):
        self.policy = policy or Policy()
        self.last_time = None
        self.revision = None
        self.active = None
        self.active_since = None
        self.last_proposal = None
        self.paused = False
        self.good = {"primary": 0, "backup": 0}
        self.bad = {"primary": 0, "backup": 0}
        self.good_since = {"primary": None, "backup": None}

    def _reset_evidence(self):
        for name in self.good:
            self.good[name] = self.bad[name] = 0
            self.good_since[name] = None

    def step(self, snapshot):
        validate_snapshot(snapshot)
        now = snapshot["time"]
        if self.last_time is not None and now <= self.last_time:
            raise ValueError("time must strictly increase")
        if self.last_time is not None and now - self.last_time < self.policy.min_interval_seconds:
            raise ValueError("observations too frequent")
        statuses = {name: health_status(snapshot[name]) for name in self.good}
        result = {"time": now, "mode": "observe_only", "active": snapshot["active"],
                  "health": statuses, "state": "STARTING", "proposal": None}
        gap = self.last_time is not None and now - self.last_time > self.policy.max_gap_seconds
        changed = self.revision is not None and snapshot["operator_revision"] != self.revision
        active_changed = self.last_time is not None and snapshot["active"] != self.active
        # This observer never applies a proposal. Any actual route change is external.
        if changed or active_changed or snapshot["manual_override"]:
            self.paused = True
        self.revision = snapshot["operator_revision"]
        self.last_time = now
        if gap:
            self._reset_evidence()
        if snapshot["active"] != self.active:
            self.active = snapshot["active"]
            self.active_since = now
            self._reset_evidence()
        if self.paused:
            self._reset_evidence()
            result["state"] = "MANUAL_OVERRIDE"
            return result
        if snapshot["wan"] != "up":
            self._reset_evidence()
            result["state"] = "WAN_DOWN" if snapshot["wan"] == "down" else "WAN_UNKNOWN"
            return result
        for name, status in statuses.items():
            if status == "OK":
                self.good[name] += 1
                self.bad[name] = 0
                if self.good_since[name] is None:
                    self.good_since[name] = now
            else:
                self.good[name] = 0
                self.good_since[name] = None
                # Unknown routing evidence must not count as a confirmed outage.
                self.bad[name] = 0 if status == "UNVERIFIED_ROUTE" else self.bad[name] + 1
        ready = {name: self.good[name] >= self.policy.ready_rounds for name in self.good}
        cooldown = self.last_proposal is not None and now - self.last_proposal < self.policy.cooldown_seconds
        target, reason = None, None
        active = self.active
        if active == "none":
            target = "primary" if ready["primary"] else "backup" if ready["backup"] else None
            reason = "NO_ACTIVE_VPN"
            result["state"] = "STARTING"
        else:
            other = "backup" if active == "primary" else "primary"
            status = statuses[active]
            result["state"] = ("PRIMARY_OK" if active == "primary" else "BACKUP_OK") if status == "OK" else status
            if self.bad[active] >= self.policy.failures:
                if ready[other]:
                    target, reason = other, status
                else:
                    result["state"] = "ALL_VPN_DOWN" if all(self.bad[n] >= self.policy.failures for n in self.bad) else "BACKUP_PREPARING"
            elif (active == "backup" and status == "OK" and self.policy.auto_return
                  and ready["primary"] and self.good_since["primary"] is not None
                  and now - self.good_since["primary"] >= self.policy.recovery_seconds
                  and now - self.active_since >= self.policy.hold_backup_seconds):
                target, reason = "primary", "PRIMARY_RECOVERED"
                result["state"] = "RECOVERING"
        if target is not None:
            if cooldown:
                result["state"] = "COOLDOWN"
            else:
                result["proposal"] = {"target": target, "reason": reason, "applied": False}
                result["state"] = "SWITCH_RECOMMENDED"
                self.last_proposal = now
        return result
