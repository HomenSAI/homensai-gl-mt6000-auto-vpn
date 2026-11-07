# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""k-of-n heartbeat targets with rotation (GL-SENSORS-2026-11-04.ru.md, item 4; cake-autorate's reflector pool).

Option heartbeat_quorum '1' (default off: the previous rule, one echo per beat alternating 1.1.1.1 / 8.8.8.8):
every beat sends one echo to each of the N active targets of a pool; the beat is lost when K or more of them got no
reply (2 of 3 by default, wave-3 study 2). A target that misses MISS_LIMIT times within WINDOW seconds while the beat
as a whole was answered (the others replied: the tunnel works, this reflector does not) is replaced by the next pool
target; a lost beat never rotates (the tunnel itself may be down). The suspicion rule is unchanged: LOSSES lost beats
in a row (fast_detect.lua). Lua twin: lua/quorum.lua (shared cases router/tests/gl_sensors_cases.json).
"""

POOL=('1.1.1.1','8.8.8.8','9.9.9.9','208.67.222.222','1.0.0.1','8.8.4.4','149.112.112.112','208.67.220.220')
ACTIVE=3
K=2
MISS_LIMIT=3
WINDOW=60
OPTION='heartbeat_quorum'


class Pool:
    def __init__(self,pool=POOL,active=ACTIVE,k=K,start=0):
        self.pool=tuple(pool);self.k=k
        start=start%len(self.pool)
        self.active=[self.pool[(start+i)%len(self.pool)] for i in range(active)]
        self.next=(start+active)%len(self.pool)
        self.misses={};self.rotations=0

    def targets(self):
        return list(self.active)

    def replace(self,target):
        for _ in range(len(self.pool)):
            candidate=self.pool[self.next];self.next=(self.next+1)%len(self.pool)
            if candidate not in self.active:
                self.active[self.active.index(target)]=candidate
                self.misses.pop(target,None);self.rotations+=1
                return candidate
        return None

    def judge(self,answered,now):
        """answered: {target: True|False} for the active targets of the beat. Returns 'ok' or 'lost'."""
        missing=[t for t in self.active if answered.get(t) is not True]
        if len(missing)>=self.k:return 'lost'
        for target in missing:
            stamps=[s for s in self.misses.get(target,[]) if 0<=now-s<WINDOW]+[now]
            self.misses[target]=stamps
            if len(stamps)>=MISS_LIMIT:self.replace(target)
        for target in list(self.misses):
            if target not in missing and target in self.active:
                self.misses[target]=[s for s in self.misses[target] if 0<=now-s<WINDOW]
                if not self.misses[target]:del self.misses[target]
        return 'ok'


def enabled(settings):
    return isinstance(settings,dict) and settings.get(OPTION) is True
