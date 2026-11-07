# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""WireGuard kernel events as a fast sensor (GL-SENSORS-2026-11-04.ru.md, item 2).

GL's patched WireGuard sends hotplug events of class 'wireguard' (ACTION=KEYPAIR-CREATED | REKEY-TIMEOUT |
REKEY-GIVEUP, ifname=<device>); GL's own ifup.sh/ifdown.sh keep working, our listener
/etc/hotplug.d/wireguard/60-homensai only appends one line '<uptime> <ACTION> <ifname>' to FILE in RAM (only while
the monitor has written FLAG, i.e. option wg_events is on). The monitor reads new lines once per second:
  REKEY-TIMEOUT / REKEY-GIVEUP of a pair channel's device: a suspicion (Booster.suspect reason 'wg-rekey') -> dense full
  checks; never a failure proof on its own (one lost handshake packet is an event too; events only come with traffic).
  KEYPAIR-CREATED: the tunnel answered a handshake (evidence 'created' for wan_diag; supersedes an older REKEY).
Lua twin: lua/wg_events.lua (shared cases router/tests/gl_sensors_cases.json).
"""
import re

FILE='wg-events.log'
FLAG='wg-events.on'
ACTIONS={'REKEY-TIMEOUT':'timeout','REKEY-GIVEUP':'giveup','KEYPAIR-CREATED':'created'}
LINE=re.compile(r'^([0-9]{1,9}(?:\.[0-9]{1,3})?) (REKEY-TIMEOUT|REKEY-GIVEUP|KEYPAIR-CREATED) ([A-Za-z0-9_.-]{1,15})$')
WINDOW=120
REASON='wg-rekey'
OPTION='wg_events'
MAX_LINES=200


def parse(text):
    """[(uptime, kind, device)] in file order; malformed lines are skipped."""
    found=[]
    if not isinstance(text,str):return found
    for line in text.split('\n')[-MAX_LINES-1:]:
        match=LINE.match(line.rstrip('\r'))
        if match:found.append((float(match.group(1)),ACTIONS[match.group(2)],match.group(3)))
    return found


def latest(events,device,now,window=WINDOW):
    """The newest event kind of one device within window seconds (uptime clock), or None."""
    best=None
    for stamp,kind,name in events:
        if name==device and 0<=now-stamp<=window and (best is None or stamp>=best[0]):best=(stamp,kind)
    return None if best is None else best[1]


class Reader:
    """New events since the last read (a restart of the monitor starts after the newest line it finds)."""

    def __init__(self):
        self.seen=None

    def new(self,events):
        if self.seen is None:
            self.seen=max([e[0] for e in events],default=0.0)
            return []
        fresh=[e for e in events if e[0]>self.seen]
        if fresh:self.seen=max(e[0] for e in fresh)
        elif events and max(e[0] for e in events)<self.seen:self.seen=max(e[0] for e in events)  # a new boot
        return fresh


def suspicions(fresh,channels):
    """REKEY events of the pair devices -> suspicion items. channels: [{'id','device'}]."""
    items=[]
    for stamp,kind,device in fresh:
        if kind not in ('timeout','giveup'):continue
        for channel in channels:
            if isinstance(channel,dict) and channel.get('device')==device and isinstance(channel.get('id'),str):
                items.append({'profile':channel['id'],'reason':REASON,'evidence':{'event':kind}})
    return items


def enabled(settings):
    return not (isinstance(settings,dict) and settings.get(OPTION) is False)
