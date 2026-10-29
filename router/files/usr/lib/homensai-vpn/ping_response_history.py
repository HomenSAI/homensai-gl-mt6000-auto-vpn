"""Observed ICMP ping history of the two Auto channels.

Same minute rows as the website history so one chart and one statistics table serve both
metrics. One echo is one cycle: a reply counts as a complete sample, no reply as a gap.
"""
import math
from website_response_history import WebsiteResponseHistory,number

METRIC='icmp-rtt-ms'
TARGET_SET='icmp-echo'
MAX_MS=60000
VALID_FOR=465


def measurement(profile,now):
    """Validate one completed echo of the selected ping target, independently of VPN health."""
    if (not isinstance(profile,dict)or not number(now)or profile.get('vendor_state')!='SETTLED'
            or profile.get('administrative_state')=='disabled'):return None
    sample=profile.get('ping')
    if not isinstance(sample,dict)or sample.get('metric')!=METRIC or sample.get('state')not in('ok','failed'):return None
    stamp=sample.get('time');ttl=sample.get('valid_for')
    if not number(stamp)or not number(ttl)or not 0<ttl<=VALID_FOR or not 0<=now-stamp<=ttl:return None
    if sample.get('interface')!=profile.get('interface')or sample.get('vendor_tunnel_id')!=profile.get('vendor_tunnel_id'):return None
    if sample['state']=='failed':return {'time':stamp,'avg_ms':None,'successes':0}
    rtt=sample.get('rtt_ms')
    if not number(rtt)or not 0<=rtt<=MAX_MS:return None
    return {'time':stamp,'avg_ms':math.floor(rtt*10+.5)/10,'successes':3}


class PingResponseHistory(WebsiteResponseHistory):
    METRIC=METRIC;TARGET_SET=TARGET_SET;MAX_MS=MAX_MS;PREFIX='PING-HISTORY'
    DEFINITION='one ICMP echo per channel per check through its own tunnel; minute means of replies'
    SCOPE='observed ICMP replies only; a lost echo is a gap; website history is separate'
    @staticmethod
    def measure(profile,now):return measurement(profile,now)
