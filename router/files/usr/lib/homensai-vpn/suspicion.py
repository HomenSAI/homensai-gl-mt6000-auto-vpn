"""Passive failure suspicion for the two Auto channels; never a failure proof.

The monitor reads the kernel's own interface counters (sysfs, no process) every
few seconds between full checks. A channel that keeps sending but receives
nothing, a WireGuard session whose handshake is older than the protocol allows
while it is sending, or a tunnel interface that disappeared makes the channel
"suspect". A suspicion only asks the scheduler for an immediate full check and
dense confirmation (probe_policy.Booster.suspect). Switching still needs the
unchanged proof: three failed full checks of the primary and two good checks of
the reserve. At most one `wg show` process runs per WG_READ_SPACING seconds.
"""
import re
import subprocess
from pathlib import Path

POLL_SECONDS=2          # sysfs reads are free; the monitor waits in 1 s steps
STALL_SECONDS=6         # tx grows while rx is flat for this long -> suspect
MIN_TX_PACKETS=3        # at least this many packets sent into the silence
MIN_TX_BYTES=120        # and this many bytes: a few empty WireGuard keepalives are not traffic
HANDSHAKE_STALE=180     # WireGuard REJECT_AFTER_TIME: the session is dead after it
HANDSHAKE_SETTLE=6      # a live peer answers a handshake within REKEY_TIMEOUT (5 s)
ACTIVITY_WINDOW=30      # recent send attempts that make an old handshake meaningful
WG_READ_SPACING=3       # at most one `wg show` process per 3 s for all channels
WG_DEVICE_SPACING=9     # and one per channel per 9 s
DEVICE=re.compile(r'^[A-Za-z0-9_.:-]{1,15}$')
COUNTERS=('rx_bytes','tx_bytes','rx_packets','tx_packets','tx_dropped')
ROLES=('source','target')
SYSFS=Path('/sys/class/net')


def read_counters(device,root=SYSFS):
    base=root/device
    values={'ifindex':int((base/'ifindex').read_text())}
    for name in COUNTERS:values[name]=int((base/'statistics'/name).read_text())
    return values


def read_wg_handshake(device):
    """Newest peer handshake (unix time, 0 = never). Public keys are parsed, never kept or logged."""
    if not DEVICE.fullmatch(device):raise ValueError('invalid device')
    out=subprocess.run(['wg','show',device,'latest-handshakes'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                       universal_newlines=True,timeout=2,check=True).stdout
    latest=None
    for line in out.splitlines():
        parts=line.split()
        if len(parts)==2 and parts[1].isdigit():latest=max(latest or 0,int(parts[1]))
    if latest is None:raise ValueError('no WireGuard peer')
    return latest


def channels(rows):
    """The two Auto channels of the last full pass, with their kernel device."""
    found=[]
    for row in rows if isinstance(rows,list) else []:
        if not isinstance(row,dict) or row.get('role') not in ROLES:continue
        device=row.get('device')
        if not isinstance(device,str) or not DEVICE.fullmatch(device) or not isinstance(row.get('id'),str):continue
        found.append({'id':row['id'],'role':row['role'],'device':device,
                      'protocol':'wireguard' if row.get('protocol')=='wireguard' else 'openvpn'})
    return found


class SuspicionWatcher:
    def __init__(self,counters=read_counters,handshake=read_wg_handshake):
        self.counters=counters;self.handshake=handshake
        self.channels={};self.track={};self.next_poll=0.0
        self.wg_at=None;self.wg_device_at={}

    def configure(self,items):
        current={}
        for item in items:
            if isinstance(item,dict) and isinstance(item.get('device'),str) and DEVICE.fullmatch(item['device']):
                current[item['device']]=dict(item)
        for device in list(self.track):
            if device not in current or self.channels.get(device,{}).get('id')!=current[device].get('id'):
                self.track.pop(device,None);self.wg_device_at.pop(device,None)
        self.channels=current

    def due(self,now):
        return now>=self.next_poll

    def _wg_allowed(self,device,now):
        if self.wg_at is not None and 0<=now-self.wg_at<WG_READ_SPACING:return False
        last=self.wg_device_at.get(device)
        return last is None or not 0<=now-last<WG_DEVICE_SPACING

    def poll(self,now,wall):
        """now: monotonic seconds, wall: unix time. Returns suspicions; never raises for one bad channel."""
        self.next_poll=now+POLL_SECONDS
        found=[]
        for device,channel in self.channels.items():
            base={'profile':channel['id'],'role':channel['role'],'device':device,'protocol':channel['protocol']}
            try:sample=self.counters(device)
            except FileNotFoundError:
                # The tunnel interface we were watching is gone (ifdown or a reconnect).
                if device in self.track:
                    self.track.pop(device,None)
                    found.append(dict(base,reason='link-missing',evidence={}))
                continue
            except (OSError,ValueError):continue
            seen=self.track.get(device)
            if (seen is None or sample['ifindex']!=seen['ifindex']
                    or any(sample[k]<seen['last'][k] for k in COUNTERS)):
                # First look, a new interface or a counter reset: no evidence before this moment.
                self.track[device]={'ifindex':sample['ifindex'],'last':sample,'rx_at':now,'rx_base':sample,'tx_times':[]}
                continue
            last=seen['last']
            if sample['rx_packets']!=last['rx_packets'] or sample['rx_bytes']!=last['rx_bytes']:
                seen['rx_at']=now;seen['rx_base']=sample
            if sample['tx_packets']>last['tx_packets'] or sample['tx_dropped']>last['tx_dropped']:
                seen['tx_times'].append(now)
            seen['tx_times']=[t for t in seen['tx_times'] if 0<=now-t<=ACTIVITY_WINDOW]
            seen['last']=sample
            stalled=now-seen['rx_at'];sent=sample['tx_packets']-seen['rx_base']['tx_packets']
            sent_bytes=sample['tx_bytes']-seen['rx_base']['tx_bytes']
            if stalled>=STALL_SECONDS and sent>=MIN_TX_PACKETS and sent_bytes>=MIN_TX_BYTES:
                found.append(dict(base,reason='rx-stall',evidence={'stalled_s':round(stalled,1),'tx_packets':sent}))
                continue
            if (channel['protocol']=='wireguard' and any(now-t>=HANDSHAKE_SETTLE for t in seen['tx_times'])
                    and self._wg_allowed(device,now)):
                self.wg_at=now;self.wg_device_at[device]=now
                try:latest=self.handshake(device)
                except (OSError,ValueError,subprocess.SubprocessError):continue
                age=None if latest==0 else wall-latest
                if age is None or age>HANDSHAKE_STALE:
                    found.append(dict(base,reason='wg-handshake-stale',
                                      evidence={'handshake_age_s':None if age is None else round(age)}))
        found.sort(key=lambda item:ROLES.index(item['role']))
        return found
