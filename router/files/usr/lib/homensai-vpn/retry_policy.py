"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
Pause before the next pass after a failed supervisor pass (study wave 3 no. 6, WAVE3-PRODUCT-2026-11-04.ru.md).

Base after the n-th failure in a row: min(15, 2*F(n)) = 2, 2, 4, 6, 10, 15, 15 ...; the pause is uniform below it (full
jitter), so a failure that clears at once costs a second instead of 5 s and routers restarted together do not retry
together. option retry_backoff 'fixed' keeps the former 5 s. The bounds of what is retried stay as they were: this is the
only pause it changes (revive budget, vendor waits, retry_wait, boot resume and the server pick round keep theirs).
Lua twin: lua/retry_policy.lua (tests/retry_policy_cases.json)."""
import random

CAP=15
BASE=2
FLOOR=0.5     # a pass that fails at once still rests
FIXED=5
RESET=60      # seconds without a failed pass start a new series
FIBONACCI=(1,1,2,3,5,8)


def mode(settings):
    return 'fixed' if isinstance(settings,dict) and settings.get('retry_backoff')=='fixed' else 'fibonacci'


def base(failures):
    return min(CAP,BASE*FIBONACCI[min(max(failures,1),len(FIBONACCI))-1])


def count(failures,last,now):
    """The failures in a row including this one: (count, now). last: the time of the previous failed pass or None."""
    return (failures+1 if last is not None and 0<=now-last<RESET else 1),now


def pause(failures,settings,uniform=None):
    """Seconds before the next pass after the failures-th failed pass in a row. uniform() is in [0, 1)."""
    if mode(settings)=='fixed':return FIXED
    return max(FLOOR,(uniform or random.SystemRandom().random)()*base(failures))
