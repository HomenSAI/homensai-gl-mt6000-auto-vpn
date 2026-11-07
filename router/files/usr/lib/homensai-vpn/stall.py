# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Passive stall sensor of one tunnel device (GL-SENSORS-2026-11-04.ru.md, item 3; cake-autorate's stall detection).

Fed once per second with two sysfs counters of the device (rx_bytes, tx_bytes: two reads, no fork), tx minus the
heartbeat's own echoes (the caller subtracts them):
  'stall'    tx grew by >= MIN_TX_BYTES since rx last moved while rx has not moved for STALL_SECONDS: the classic dead
             WireGuard peer, seen without a single probe. Only a suspicion: it starts the dense full checks
             (probe_policy.Booster.suspect reason 'rx-stall'), never a switch.
  'flowing'  rx moved since the previous sample AND grew by >= VETO_BYTES over the last VETO_SECONDS (10 kbit/s,
             cake-autorate's stall threshold): the peer is delivering authenticated data right now, so a lost heartbeat
             echo (ICMP filtered somewhere) is not counted (the veto, option stall_veto). Requiring the movement of the
             last second ends the veto the second rx stops: a real outage of a loaded tunnel is not delayed.
  'idle'     anything else (also the first sample, a counter reset or a gap longer than GAP).
The Python monitor has no heartbeat: there suspicion.py keeps its own counter rule and takes STALL_SECONDS from here
with option stall_sensor on. Lua twin: lua/stall.lua (shared cases router/tests/gl_sensors_cases.json).
"""

STALL_SECONDS=3
VETO_SECONDS=3
VETO_BYTES=3750          # 10 kbit/s for 3 s
MIN_TX_BYTES=300         # a few packets of real traffic into the silence; empty WireGuard keepalives count 0 bytes
GAP=5                    # seconds without a sample: start again (no evidence across a pause or a speed test)
HISTORY=6                # samples kept for the rx rate
OPTION='stall_sensor'
VETO_OPTION='stall_veto'


def _count(value):
    return type(value) is int and value>=0


class Stall:
    def __init__(self):
        self.reset()

    def reset(self):
        self.last=None;self.rx_at=None;self.base_tx=None;self.history=[]

    def feed(self,now,rx_bytes,tx_bytes):
        """One sample; returns {'state','stalled_s','tx_bytes'}."""
        if not (_count(rx_bytes) and _count(tx_bytes)):
            self.reset();return {'state':'idle','stalled_s':0,'tx_bytes':0}
        last=self.last
        if last is None or now-last[0]>GAP or now<last[0] or rx_bytes<last[1] or tx_bytes<last[2]:
            self.last=(now,rx_bytes,tx_bytes);self.rx_at=now;self.base_tx=tx_bytes;self.history=[(now,rx_bytes)]
            return {'state':'idle','stalled_s':0,'tx_bytes':0}
        if rx_bytes!=last[1]:
            self.rx_at=now;self.base_tx=tx_bytes
        self.last=(now,rx_bytes,tx_bytes)
        self.history.append((now,rx_bytes))
        if len(self.history)>HISTORY:self.history=self.history[-HISTORY:]
        oldest=None
        for stamp,rx in self.history:
            if now-stamp>=VETO_SECONDS:oldest=(stamp,rx)
        if oldest is not None and self.rx_at==now and rx_bytes-oldest[1]>=VETO_BYTES:
            return {'state':'flowing','stalled_s':0,'tx_bytes':0}
        stalled=now-self.rx_at;sent=tx_bytes-self.base_tx
        if stalled>=STALL_SECONDS and sent>=MIN_TX_BYTES:
            return {'state':'stall','stalled_s':int(stalled),'tx_bytes':sent}
        return {'state':'idle','stalled_s':0,'tx_bytes':0}


def enabled(settings,option=OPTION):
    return not (isinstance(settings,dict) and settings.get(option) is False)
