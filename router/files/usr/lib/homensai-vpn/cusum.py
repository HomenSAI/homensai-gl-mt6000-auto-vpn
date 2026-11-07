# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Two small sequential detectors over the 1 Hz ICMP heartbeat (docs/architecture/CUSUM-TRIGGER-2026-11-04.ru.md).

Lua twin: lua/cusum.lua (same rules and constants; shared cases router/tests/cusum_cases.json). The heartbeat lives in
the Lua monitor (lua/fast_detect.lua); the Python monitor has none, so here these classes are the reference of the
shared cases and of the offline study (private/math/wave4-confirm). Neither detector ever decides a switch.

LossCusum: Bernoulli CUSUM over lost heartbeat echoes. S <- max(0, S + x), x = ln(P1/P0) for a lost echo, 0 for a lost
  echo past the CAP-th of one run (a long run is an outage: the heartbeat's own rule and the failure model handle it,
  and a provider that filters every echo can never reach H), ln((1-P1)/(1-P0)) for an answered one. S >= H fires and
  S restarts at 0. A fire only asks for a dense confirmation episode (probe_policy.Booster.suspect, reason 'cusum-loss').
  Echoes alternate between targets, so a healthy tunnel with one filtered target loses every second echo: a fire needs
  lost echoes of two different targets within GATE beats (a beat with target None is not attributed to a target and
  passes the gate: a refused send, a missing link, the k-of-n quorum). A refused fire still restarts S.

RttWatch: soft 'congested' signal from a Kalman local-linear-trend filter on log RTT. The base of each target (the two
  targets differ by their anycast distance) and the noise come from the first WARM answers (median and MAD); then
  z = (level - drift) / sqrt(P00 + 0.05^2). z >= Z_ON raises the signal; z < Z_OFF for CLEAR answered beats clears it.
  The baseline follows slow change while calm; a level that stays up for MAX_HOLD answered beats is the new normal: the
  watch learns again. A signal only: no suspicion, no switch.
"""
import math

P0=0.01                 # healthy share of lost echoes
P1=0.5                  # target share: the drift is zero near 15 % loss, so 5-10 % loss is ridden out
H=8.0
CAP=2                   # lost echoes of one run that count
GATE=8                  # beats within which two targets must have lost an echo
LOST_STEP=math.log(P1/P0)
KEPT_STEP=math.log((1-P1)/(1-P0))
OPTION='cusum_trigger'
REASON='cusum-loss'     # probe_policy.SUSPICION_REASONS and REST_BYPASS


class LossCusum:
    def __init__(self):
        self.fired=0;self.gated=0
        self.reset()

    def reset(self):
        self.s=0.0;self.run=0;self.beat=0;self.seen={}

    def feed(self,lost,target=None):
        """One heartbeat outcome (lost True/False); returns True when the detector fires."""
        self.beat+=1
        if lost:
            self.run+=1
            if target is not None:self.seen[target]=self.beat
            step=LOST_STEP if self.run<=CAP else 0.0
        else:
            self.run=0;step=KEPT_STEP
        self.s=max(0.0,self.s+step)
        if self.s<H:return False
        self.s=0.0
        if target is not None and sum(1 for at in self.seen.values() if self.beat-at<GATE)<2:
            self.gated+=1
            return False
        self.fired+=1
        return True


RTT_OPTION='rtt_watch'
CODE='CHANNEL-CONGESTED'
WARM=120                # answered beats of the warm-up
TARGET_MIN=5            # answers a target needs in the warm-up to get a base of its own
SIG_MIN=0.05
Z_ON=4.0;Z_OFF=2.0
CLEAR=30                # answered beats below Z_OFF that clear the signal
TRACK=1800.0            # time constant (beats) of the baseline while calm
MAX_HOLD=1800           # answered beats of a raised signal after which the level is the new normal
Q_L=2e-5;Q_S=1e-9;P_START=0.05;INNOVATION_GATE=3.0;LEVEL_SOFT=0.05*0.05


class RttWatch:
    def __init__(self):
        self.raised=0;self.relearned=0
        self.learn()

    def learn(self):
        """Back to the warm-up (a new channel epoch, a pause, a level that became the new normal)."""
        self.samples=[];self.base=None;self.congested=False;self.calm=0;self.held=0;self.z=0.0;self.drift=0.0

    def _start(self):
        by_target={}
        for target,y in self.samples:by_target.setdefault(target,[]).append(y)
        base={};residuals=[]
        for target in by_target:
            values=sorted(by_target[target])
            if len(values)<TARGET_MIN:continue
            middle=values[len(values)//2]
            base[target]=middle
            residuals.extend(abs(y-middle) for y in values)
        self.samples=[]
        if not base:return
        residuals.sort()
        sigma=max(residuals[len(residuals)//2]*1.4826,SIG_MIN)
        self.base=base;self.R=sigma*sigma
        self.x0=0.0;self.x1=0.0;self.P00=P_START;self.P01=0.0;self.P11=1e-6

    def _predict(self):
        self.x0+=self.x1
        P00=self.P00+2*self.P01+self.P11+Q_L
        self.P01+=self.P11;self.P11+=Q_S;self.P00=P00

    def _update(self,y):
        innovation_var=self.P00+self.R
        error=y-self.x0
        limit=INNOVATION_GATE*math.sqrt(innovation_var)
        if error>limit:error=limit
        elif error<-limit:error=-limit
        K0=self.P00/innovation_var;K1=self.P01/innovation_var
        self.x0+=K0*error;self.x1+=K1*error
        P00=(1-K0)*self.P00;P01=(1-K0)*self.P01
        self.P11-=K1*self.P01
        self.P00=P00;self.P01=P01

    def feed(self,rtt_ms,target=None):
        """One beat: rtt_ms (None = no answer). Returns 'learning', 'ok' or 'congested'."""
        answered=type(rtt_ms) in (int,float) and rtt_ms>0 and math.isfinite(rtt_ms)
        if self.base is None:
            if answered:
                self.samples.append((target,math.log(rtt_ms)))
                if len(self.samples)>=WARM:self._start()
            return 'learning'
        self._predict()
        if answered and target in self.base:
            self._update(math.log(rtt_ms)-self.base[target])
            self.z=(self.x0-self.drift)/math.sqrt(self.P00+LEVEL_SOFT)
            if self.congested:
                self.held+=1
                self.calm=self.calm+1 if self.z<Z_OFF else 0
                if self.calm>=CLEAR:self.congested=False;self.calm=0;self.held=0
                elif self.held>=MAX_HOLD:
                    self.relearned+=1
                    self.learn()
                    return 'learning'
            elif self.z>=Z_ON:
                self.congested=True;self.calm=0;self.held=0;self.raised+=1
            elif abs(self.z)<Z_OFF:
                self.drift+=(self.x0-self.drift)/TRACK
        return 'congested' if self.congested else 'ok'
