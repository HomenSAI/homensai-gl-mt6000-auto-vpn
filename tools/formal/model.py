#!/usr/bin/env python3
# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Explicit-state model checker of the HomenS.AI Auto VPN supervisor (pair mode, router-probed-ipv4).

Offline formal model (03.11.2026). Java/TLC is not installed on this PC, so this is a self-contained Python
breadth-first model checker: exhaustive state enumeration, invariants on states, assertions on transitions,
backward reachability (EF) for "no permanent HELD", and bottom-SCC analysis (Tarjan) for liveness under
strong fairness. Source of truth for the abstraction: private/integ-a7 (integ/alpha7-20261103, 6d7a4805).
Every action label names the code it abstracts (file:line in integ-a7).

Variant fix2 (fix/formal-k2-k5-20261103): the fixed transition rules of K1 tail, K2, K3, K4, K5 and the owner's
K9 decision (keep the VPN-only guard of a session HELD by an outside change until Start or Stop). Each changed rule
is marked "fix2" with the code it abstracts in the fix branch (lua/pair.lua, lua/auto.lua, lua/transaction.lua,
lua/control_request.lua; Python twins pair_auto.py, native_switch.py, auto_control.py).
K11 (04.11.2026): pair.cleanup re-reads the record under the control lock before its STOPPING write; a record the
owner's Start hand-over finished meanwhile ends the pass without a write (switch 'K11', transition 'CL0 superseded').
K12 (04.11.2026, finding 7): the vendor rebuilds the carrying reserve (switch 'K12', option --rebuild, liveness 'return').
Trace conformance (tools/formal/trace_check.py, 04.11.2026; marked G1-G7): the rules the conformance run showed the
abstraction did not have: no tunnel -> full block (G1), variant C kept clients (G2), the boot window of the hand-over (G3),
abandon writes the stop latch (G4), a session without owned clients (G5), the order of the checks in a pass (G6), the
details of a failed rollback (G7). The conditions the model cannot see (which clients are up, HANDOVER_WAIT, one attempt per
boot, KEEP_SECONDS) are free choices: the model allows both outcomes, which is a stronger claim for its properties and a
weaker one for conformance.

Fast end (feat/fast-switch-20261104, docs/architecture/FAST-SWITCH-2026-11-04.ru.md), option --fast-switch: what the base model
cannot say. The decision may now come from evidence that does not prove the primary dead (2 failed samples in a row, the
expert heartbeat verdict: a live primary can be left), and the live recheck runs beside the preparation, so its answer can be
older than the commit (a primary that recovers after it is not seen): TICK may start the forward switch with pUp, and FWD0 may
pass with pUp. L1 (the wake) only moves ticks in time, which the interleaving already covers; every guard stays in the code.
Off by default; the TLA+ re-statement has it as the constant FastSwitch.

Server keys (review 04.11.2026, findings 1 and 2), option --key-pin (option server_key_pin 'enforce'; off by default; the TLA+
re-statement has it as the constant KeyPin): a key of the primary or the reserve changes and waits
for the owner. 'directional' is the code: a Start with an unaccepted key on the channel that carries the traffic after it (the
live order: the reserve of a boot handover, else the primary) is refused before the session, the guard and the clients (pair.begin,
owner 05.11.2026), a key seen there while begin runs waits at the first proof, a key on the other channel changes nothing, a
working pair refuses only a move onto the channel with the unaccepted key, a rollback and a Stop do not depend on keys. 'blocker' is the code before the fix, for
the record: SERVER-KEY-UNACCEPTED was a diagnostic blocker, which ended every pass of the pair and failed the proof of a rollback
(the liveness checks failover, return and stop-wins fail with it). New properties: MOVE-ONTO-UNACCEPTED-KEY,
BEGIN-WITH-UNACCEPTED-KEY.

Run:  py -3 model.py                     # both variants (alpha6 Start, fixed Start), base model
      py -3 model.py --variant fix --faults --server
      py -3 model.py --json results.json # machine-readable results + traces
Python 3.10+ only, standard library only.
"""
import argparse
import collections
import json
import sys
import time
from array import array
from typing import NamedTuple

# ---------------------------------------------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------------------------------------------
NONTERM = frozenset({'STARTING', 'RUNNING', 'STOPPING', 'HELD'})       # pair.lua:25 TERMINAL = STOPPED/FAILED
TERM = frozenset({'NONE', 'STOPPED', 'FAILED'})
SETTLED = frozenset({'NONE', 'RB'})                                    # release_session: absent or ROLLED-BACK
BUSY = frozenset({'ARMED', 'APPLYING', 'WAIT', 'COMMITTED', 'HOR', 'RESTORING', 'RP'})   # auto_control.py:224
RECOVERY = frozenset({'ARMED', 'APPLYING', 'WAIT', 'RESTORING'})        # auto.lua:170, T.RECOVERY_PHASES
IDLE = ('IDLE', 0, '')
DOWN = ('DOWN', 0, '')
BLOCKED = ('GIVEUP', 0, '')


class S(NamedTuple):
    intent: str = 'off'      # RAM pair-auto-control.json mode ('on' always carries the current revision)
    fresh: bool = False      # intent id != session id: begin() pending (pair.lua:1177)
    marker: bool = False     # PERSIST auto-resume.json: the owner's own Start, newer than any Stop (boot_resume)
    stopped: bool = False    # ghost: a stop latch (owner Stop, abandon) is newer than the last Start
    sess: str = 'NONE'       # PERSIST pair-auto-state.json phase
    code: str = '-'          # HELD recovery_error: '-' | 'READOPT' (pair.lua:27) | 'OTHER'
    ran: bool = False        # state.ran
    ho: bool = False         # STOPPED with handover (variant D, pair.lua:796)
    jr: str = 'NONE'         # PERSIST native-transaction.json phase; RB=ROLLED-BACK, HOR=HELD-ON-RESERVE, WAIT=WAIT-CLIENT
    rtp: bool = False        # journal rtp_dispatched (a kernel write was dispatched)
    fails: int = 0           # rollback_failures (0..2, ROLLBACK_FAILURE_LIMIT=2)
    fres: bool = False       # forward_resumed recorded
    txrev: bool = False      # the transaction's control revision is still the current one
    failed: bool = False     # journal failure_code recorded (transaction.lua:676)
    uci: str = 'P'           # first rule of route_policy: P primary, R reserve, F foreign (GL panel change)
    kern: str = 'P'          # kernel route: P, R, X (being rebuilt / unknown), F (foreign)
    guard: str = 'none'      # nft guard: none, full (LAN block, 90 s self-release), vpn (VPN-only)
    pUp: bool = True         # primary tunnel healthy (live)
    rUp: bool = True         # reserve tunnel healthy (live)
    pStable: bool = True     # primary stable >= primary_stable (recovery_ready, undamped)
    pHold: bool = True       # primary stable >= damped return_hold (pair.return_hold)
    dwell: bool = True       # >= max(cooldown, min_dwell) since the last ledger charge
    ext: str = 'none'        # outside change by the owner in the GL panel: none | net | pol
    prep: bool = False       # a PREP check fails (autostart / stock boot link)
    readopt: int = 0         # RAM pair-readopt.json entries inside 15 min (limit 3)
    sup: tuple = IDLE        # supervisor program counter (proc, step, ctx)
    boot: bool = False       # a power cut happened since the journal's transaction started
    resume: bool = False     # monitor's boot/restart resume window open (boot_resume.py)
    sc: tuple = ('-', '', False)   # server change record (phase, tunnel P/R, verified)
    rgen: bool = False       # the vendor rebuilt the carrying reserve: the journal's vendor proof is stale (K12, finding 7)
    kept: bool = False       # STOPPED with the clients kept for the boot resume's Start (variant C, pair.boot_keep; G2)
    young: bool = False      # --window: uptime below BOOT_KEEP_UPTIME (900 s; pair.resume_pending; G3)
    kp: bool = False         # --key-pin: the primary's server key changed and waits for the owner (server_pin 'changed')
    kr: bool = False         # --key-pin: the same for the reserve
    kv: bool = False         # --key-pin: the session has proved its route (state.selected_policy): a Start is over


INIT = S()


def boot_window(s, cfg):
    """pair.resume_pending: inside the uptime window (--window: it doubles the state space; else a power cut during the
    journal stands for it) or a forward-resumed transaction, with the owner's marker and no newer stop latch."""
    return s.marker and not s.stopped and (s.fres or (s.young if cfg.window else s.boot))

# Individually switchable fixes of the formal-fixes branch; variant fix2 = all of them. K1T = K1 tail (early hand-over
# for the owner's marker after a reboot). See tools/formal/README.md for how CI uses them.
# F32 (b851db74, owner decision 07.11.2026): a RUNNING session adopts an outside change by itself only when readopt_class
# proves it touches nothing but wireless/dhcp/gl-dns-v2 or the network outside the pair; the pair's route_policy (and its
# order), the VPN profiles, the firewall, any other package or an unreadable class are HELD (PAIR-OUTSIDE-CHANGE-HELD) until
# the owner's Start or Stop. T4A (c31d7332): the owner's Stop ends such a hold STOPPED (end_hold_on_stop: release_session
# adopted_by='owner-stop', owned=[], the guard released, no readopt budget spent); a Start while Auto is on keeps it HELD.
ALL_FIXES = frozenset({'K1T', 'K2', 'K3', 'K4', 'K5', 'K9', 'K11', 'K12', 'F32', 'T4A'})


def fence(s):
    # pair.fence_recovery (pair.lua:540): the intent file is rewritten 'off' under the lock
    return s._replace(intent='off', fresh=False)


def carrying(kern):
    return kern if kern in ('P', 'R') else None


def key_on_carrying(s):
    """--key-pin: the channel the live order names has an unaccepted key (native_switch.carrying_unaccepted, owner 05.11.2026)."""
    return s.kr if s.uci == 'R' else s.kp


def key_pin(cfg):
    # getattr: trace_check.py builds its own cfg without this option
    return getattr(cfg, 'key_pin', None)


# ---------------------------------------------------------------------------------------------------------------
# Owner Start (auto_control.start + pair_auto.request + preparation_control.guard/auto_prepare)
# ---------------------------------------------------------------------------------------------------------------
def start(s, cfg, manual):
    """-> (accepted, new state, refusal code)"""
    if s.sup == BLOCKED:
        return False, s, 'TRANSACTION-IN-PROGRESS'
    handover = s.sess == 'STOPPED' and s.ho and s.jr in ('COMMITTED', 'HOR')
    if s.jr in BUSY and not handover:                                   # auto_control.py:224-232
        return False, s, 'TRANSACTION-IN-PROGRESS'
    early = manual or ('K1T' in cfg.fixed and s.marker and not s.stopped)     # fix2 K1 tail: auto_control.start / control_request.start
    if cfg.fix and early and s.sess == 'HELD' and s.code == 'READOPT' and s.intent != 'on':
        # pair_auto.release_for_start (fix/held-start-handover-20261103, pair_auto.py:210-248)
        if s.jr in SETTLED and s.readopt < 3:
            s = s._replace(sess='STOPPED', code='-', ran=False, ho=False, readopt=s.readopt + 1)
        else:
            return False, s, 'PAIR-RECOVERY-REQUIRED'
    if s.prep:
        # auto_prepare -> preparation_control.guard (preparation_control.py:108-125)
        if s.intent == 'on':
            return False, s, 'PREPARATION-STOP-AUTO-FIRST'
        if s.sess not in TERM:
            return False, s, 'PREPARATION-RECOVERY-REQUIRED'
        s = s._replace(prep=False)                                      # reviewed repair, readback
    # pair_auto.request (pair_auto.py:252-279)
    if s.sess in NONTERM and not (s.intent == 'on' and not s.fresh):
        if s.sess == 'HELD' and s.code == 'READOPT' and s.jr in SETTLED and s.readopt < 3:
            s = s._replace(sess='STOPPED', code='-', ran=False, ho=False, readopt=s.readopt + 1)
        else:
            return False, s, 'PAIR-RECOVERY-REQUIRED'
    if s.intent == 'on':
        return True, s, 'already'
    s = s._replace(intent='on', fresh=True)
    if manual:
        s = s._replace(marker=True, stopped=False)
    return True, s, None


def stop(s):
    # auto_control.stop: revision rotated under the control lock, pair intent off, stop latch on flash. The monitor's window
    # stays: its token is read on the next look (5 s), a later Start of the owner meets it with the owner's own marker.
    return s._replace(intent='off', fresh=False, marker=False, stopped=True, txrev=False)


# ---------------------------------------------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------------------------------------------
def can_readopt(s):
    """readopt_running -> release_session(automatic) succeeds: a running session, the 3/900 s budget, a settled journal."""
    return s.sess == 'RUNNING' and s.intent == 'on' and s.readopt < 3 and s.jr in SETTLED


def readopt(s):
    """readopt_running ADOPT: the record archived, the session retired (STOPPED), a new request id: begin() follows."""
    return s._replace(sess='STOPPED', code='-', ran=False, ho=False, readopt=s.readopt + 1, fresh=True, sup=IDLE)


def tick_error(s, cls, adopt=True):
    """pair.tick catch (pair.lua:1326-1356) followed by iteration (auto.lua:262-268). adopt=False (F32): readopt_class
    decided HOLD - readopt_running writes HELD with the code under the control lock, the catch goes on as for any error
    (Auto stays on for a session that ran; outside_hold is not called while the request is current)."""
    if adopt and cls == 'READOPT' and can_readopt(s):
        return readopt(s)
    if s.sess == 'STARTING':                                         # cleanup(pending) (pair.lua:1344-1347)
        return s._replace(sup=('CL', 0, 'st'))
    if (s.sess in TERM or (s.sess == 'HELD' and not s.ran)) and s.intent == 'on':
        s = s._replace(intent='off', fresh=False)                    # fail_request
    if s.sess in NONTERM:
        s = s._replace(sess='HELD', code=cls)                        # publish_failure
    if s.jr in RECOVERY:
        return fence(s)._replace(sup=DOWN)                           # fence_recovery + 'exit' -> procd restart
    return s._replace(sup=IDLE)


def rb_done(s, ctx):
    """Continuation after a successful rollback."""
    if ctx == 'fwd':
        return tick_error(s._replace(sup=IDLE), 'OTHER')            # attempt re-raises its failure code
    if ctx == 'ret':
        if s.sess == 'HELD' and s.ran:
            s = s._replace(sess='RUNNING', code='-')                 # resume_running (pair.lua:547)
        return s._replace(sup=IDLE)
    if ctx == 'native':
        return s._replace(sup=IDLE)
    if ctx in ('cl-tick', 'cl-rec', 'cl-st'):
        return s._replace(sup=('CL', 3, ctx[3:]))
    if ctx == 'rec':
        return s._replace(sup=('REC', 3, ''))
    raise AssertionError(ctx)


def rb_failed(s, ctx):
    """rollback raised; only rollback_counted counts it (rollback.lua:233): the attempt's and the recovery's (G7)."""
    if ctx in ('rec', 'fwd'):
        s = s._replace(fails=min(2, s.fails + 1))
    if ctx == 'rec':
        if s.fails >= 2:                                             # auto.lua:198 -> give_up (rollback.lua:223)
            return s._replace(sup=BLOCKED, guard='vpn', marker=False)
        return s._replace(sup=DOWN)                                  # error -> daemon dies -> procd
    if ctx == 'cl-rec':
        if s.sess in NONTERM:
            s = s._replace(sess='HELD', code='OTHER')
        # pair.recover catches it and the recovery ends (G7): the journal stays RESTORING until the next pass exits
        return s._replace(sup=IDLE, resume=True)
    return tick_error(s, 'OTHER')


def abandon(s, ctx):
    """rollback.abandon (rollback.lua:24-41): unguard, ROLLED-BACK abandoned, stop latch (G4: stop_latch rotates the
    revision, so the intent is off, and it is newer than the owner's marker); raise RELEASED."""
    s = s._replace(guard='none', jr='RB', marker=False, stopped=True, intent='off', fresh=False, txrev=False, sup=IDLE)
    if ctx in ('rec',):
        return s._replace(sup=('REC', 3, ''))
    if ctx == 'cl-rec':
        if s.sess in NONTERM:
            s = s._replace(sess='HELD', code='OTHER')
        return s._replace(sup=IDLE, resume=True)
    return tick_error(s, 'OTHER')


def sup_steps(s, cfg):
    """Successors of the supervisor process: list of (label, state, tags)."""
    out = []
    proc, k, ctx = s.sup

    def add(label, n, *tags):
        out.append((label, n, frozenset(tags)))

    if proc == 'GIVEUP':
        return out                                                   # alarm until the operator closes the journal
    if proc == 'DOWN':
        # procd restart -> auto.recover (auto.lua:132): rotate revision, read journal, fence intent
        add('REC0 supervisor start: revision rotated, intent fenced (auto.lua:133,158)',
            fence(s)._replace(txrev=False, resume=False, sup=('REC', 1, '')), 'sup')
        return out
    if proc == 'IDLE':
        return tick(s, cfg)

    # --------------------------------------------------------------------------------- forward switch (T.attempt)
    if proc == 'FWD':
        if k == 0:   # configure_lease -> require_running; diagnostic; late recheck (pair.lua:1306-1313)
            if s.intent != 'on':
                add('FWD0 configure_lease: CLIENT-STOP (pair.lua:513)', tick_error(s, 'OTHER'), 'sup')
            elif not s.rUp:
                add('FWD0 diagnostic: PAIR-READINESS-CHANGED (pair.lua:1309)', tick_error(s, 'OTHER'), 'sup')
            elif key_pin(cfg) and s.kr:
                add('FWD0 attempt refused: SERVER-KEY-UNACCEPTED (transaction.lua attempt, the key changed after the decision)', tick_error(s, 'OTHER'), 'sup')
            else:
                if s.pUp:
                    add('FWD0 late recheck: PRIMARY-RECOVERED-BEFORE-SWITCH (pair.lua:1311)', s._replace(sup=IDLE), 'sup')
                if not s.pUp or cfg.fast_switch:
                    # fast_switch: a recheck that started with the decision did not see a primary that came back after it
                    add('FWD1 journal ARMED (transaction.lua:556)',
                        s._replace(jr='ARMED', rtp=False, fails=0, fres=False, txrev=True, failed=False, boot=False,
                                   sup=('FWD', 2, '')), 'sup', 'armed')
        elif k == 2:  # dispatch under the lock: revision + charge_attempt (transaction.lua:558-576)
            if not s.txrev or not s.dwell:
                add('FWD2 dispatch refused -> ROLLED-BACK FAILED-BEFORE-APPLY (transaction.lua:567-569)',
                    tick_error(s._replace(jr='RB'), 'OTHER'), 'sup')
            else:
                add('FWD2 charge_attempt: ledger charged (pair.lua:564)', s._replace(dwell=False, sup=('FWD', 3, '')),
                    'sup', 'charge')
        elif k == 3:
            add('FWD3 journal APPLYING (transaction.lua:577-583)', s._replace(jr='APPLYING', sup=('FWD', 4, '')), 'sup')
        elif k == 4:
            if not s.txrev:
                add('FWD4 apply_steps: CONTROL-REVISION-STALE -> rollback', fwd_fail(s), 'sup')
            else:
                add('FWD4 guard(nil): full LAN block (transaction.lua:401)', s._replace(guard='full', sup=('FWD', 5, '')), 'sup')
        elif k == 5:
            if not s.txrev:
                add('FWD5 before_write: stale -> rollback (transaction.lua:403)', fwd_fail(s), 'sup')
            else:
                add('FWD5 uci reorder: reserve first (transaction.lua:432)', s._replace(uci='R', sup=('FWD', 6, '')),
                    'sup', 'move-to-R')
        elif k == 6:
            if not s.txrev:
                add('FWD6 before_write: stale -> rollback', fwd_fail(s), 'sup')
            else:
                add('FWD6 journal rtp_dispatched=true (transaction.lua:419-420)', s._replace(rtp=True, sup=('FWD', 7, '')), 'sup')
                if cfg.faults:
                    add('FWD6 FAULT apply refused before its dispatch (G7: rtp_boot, the synchronization script)', fwd_fail(s), 'sup', 'fault')
        elif k == 7:   # run.fenced(revision, fn): the revision is checked under the control lock (transaction.lua:423)
            if not s.txrev:
                add('FWD7 fenced dispatch refused: CONTROL-REVISION-STALE -> rollback', fwd_fail(s), 'sup')
            else:
                add('FWD7 rtp2 dispatched under the fence: kernel rebuilding (transaction.lua:423)',
                    s._replace(kern='X', sup=('FWD', 8, '')), 'sup', 'move-to-R')
        elif k == 8:
            add('FWD8 kernel rebuilt from UCI (reserve first)', s._replace(kern=s.uci, sup=('FWD', 9, '')), 'sup')
            if cfg.faults:
                add('FWD8 FAULT rtp2 failed: KERNEL-POLICY-UNVERIFIED', fwd_fail(s), 'sup', 'fault')
        elif k == 9:  # verify + guard(devices) fenced (transaction.lua:586-607)
            if not s.txrev:
                add('FWD9 verify/guard: stale -> rollback (transaction.lua:606)', fwd_fail(s), 'sup')
            elif s.kern != 'R' or s.uci != 'R':
                add('FWD9 verify: KERNEL-POLICY-UNVERIFIED -> rollback', fwd_fail(s), 'sup')
            else:
                add('FWD9 guard(devices): VPN-only (transaction.lua:607)', s._replace(guard='vpn', sup=('FWD', 10, '')), 'sup')
        elif k == 10:
            add('FWD10 journal WAIT-CLIENT (transaction.lua:608)', s._replace(jr='WAIT', sup=('FWD', 11, '')), 'sup')
        elif k == 11:  # confirmation loop (transaction.lua:613-668)
            if not s.txrev or s.stopped:
                add('FWD11 CLIENT-STOP / revision stale -> rollback (transaction.lua:614-616)', fwd_fail(s), 'sup')
            elif s.rUp and 'K5' in cfg.fixed:
                add('FWD11 fix2 K5: revision check and COMMITTED under the control lock (transaction.lua attempt)',
                    s._replace(jr='COMMITTED', sup=IDLE), 'sup', 'committed')
            elif s.rUp:
                add('FWD11 router probes confirm the reserve; require_control_revision passed (transaction.lua:637)',
                    s._replace(sup=('FWD', 12, '')), 'sup')
            else:
                add('FWD11 CLIENT-CONFIRMATION-TIMEOUT -> rollback (transaction.lua:668)', fwd_fail(s), 'sup')
        elif k == 12:
            add('FWD12 journal COMMITTED (transaction.lua:640, not under the lock)',
                s._replace(jr='COMMITTED', sup=IDLE), 'sup', 'committed')
        return out

    # --------------------------------------------------------------------------------- forward_resume (after a restart)
    if proc == 'FRES':
        if k == 0:
            # forward_resume.resume: kernel untouched (pre-switch graph) or already the reserve's; else refuse
            forward = s.uci == 'R' and s.kern == 'R'
            untouched = s.kern == 'P' and s.uci in ('P', 'R')
            if (s.stopped or not (forward or untouched) or s.sess not in ('RUNNING', 'HELD', 'STOPPING')
                    or (key_pin(cfg) and untouched and not forward and s.kr)):   # a kernel still on the primary: a new move
                add('FRES0 refused before any write -> rollback (forward_resume.lua:165-186)',
                    s._replace(sup=('RB', 0, 'rec')), 'sup')
            else:
                add('FRES0 journal forward_resumed (forward_resume.lua:189-191)',
                    s._replace(fres=True, txrev=True, sup=('FRES', 1 if untouched else 4, '')), 'sup')
        elif k == 1:
            if s.stopped or not s.txrev:
                add('FRES1 CLIENT-STOP -> rollback (forward_resume.lua:200)', s._replace(failed=True, sup=('RB', 0, 'rec')), 'sup')
            else:
                add('FRES1 guard(nil) + uci reserve first', s._replace(guard='full', uci='R', sup=('FRES', 2, '')), 'sup', 'move-to-R')
        elif k == 2:   # write_command: require_control_revision + run.fenced (forward_resume.lua:198-213)
            if s.stopped or not s.txrev:
                add('FRES2 fenced dispatch refused: CLIENT-STOP -> rollback', s._replace(failed=True, sup=('RB', 0, 'rec')), 'sup')
            else:
                add('FRES2 rtp dispatched under the fence', s._replace(rtp=True, kern='X', sup=('FRES', 3, '')), 'sup', 'move-to-R')
        elif k == 3:
            add('FRES3 kernel rebuilt from UCI', s._replace(kern=s.uci, sup=('FRES', 4, '')), 'sup')
            if cfg.faults:
                add('FRES3 FAULT kernel unverified -> rollback', s._replace(failed=True, sup=('RB', 0, 'rec')), 'sup', 'fault')
        elif k == 4:
            if s.kern != 'R' or s.uci != 'R':
                add('FRES4 kernel not target -> rollback', s._replace(failed=True, sup=('RB', 0, 'rec')), 'sup')
            else:
                add('FRES4 guard VPN-only + WAIT-CLIENT (forward_resume.lua:236)',
                    s._replace(guard='vpn', jr='WAIT', sup=('FRES', 5, '')), 'sup')
        elif k == 5:
            if s.stopped or not s.txrev:
                add('FRES5 CLIENT-STOP -> rollback (forward_resume.lua:249)', s._replace(failed=True, sup=('RB', 0, 'rec')), 'sup')
            elif s.rUp:
                add('FRES5 COMMITTED SUPERVISOR-FORWARD-RESUMED (forward_resume.lua:258)',
                    s._replace(jr='COMMITTED', sup=('REC', 3, '')), 'sup', 'committed')
            else:
                add('FRES5 CLIENT-CONFIRMATION-TIMEOUT -> rollback', s._replace(failed=True, sup=('RB', 0, 'rec')), 'sup')
        return out

    # --------------------------------------------------------------------------------- rollback (rollback.lua:43-201)
    if proc == 'RB':
        branch_a = (not s.rtp) and s.jr in RECOVERY
        if k == 0:
            if s.jr == 'ARMED' and not s.rtp and s.uci == 'P':
                add('RB0 ARMED, nothing written: ROLLED-BACK (rollback.lua:136-139)', rb_done(s._replace(jr='RB'), ctx), 'sup')
            elif branch_a:
                if s.uci == 'F':
                    add('RB-A order foreign: abandon (rollback.lua:63-66)', abandon(s, ctx), 'sup', 'abandon')
                else:
                    add('RB-A undo UCI order (rollback.lua:67)', s._replace(uci='P', sup=('RB', 1, ctx)), 'sup')
            else:
                add('RB-B journal RESTORING (rollback.lua:132-133)', s._replace(jr='RESTORING', sup=('RB', 2, ctx)), 'sup')
                if cfg.faults and s.jr == 'RESTORING':
                    # G7: a former failed apply left the kernel behind the restored order: the proof before the writes refuses
                    add('RB-B FAULT KERNEL-POLICY-UNVERIFIED before any write (rollback.lua:120)', rb_failed(s, ctx), 'sup', 'fault')
        elif k == 1:  # branch A: kernel follows if it changed (best effort), guard(devices), ROLLED-BACK
            if s.kern != 'P':
                add('RB-A vendor reload: kernel follows the restored UCI (rollback.lua:73-78)',
                    rb_done(s._replace(kern='P', guard='vpn', jr='RB'), ctx), 'sup', 'move-to-P')
                if cfg.faults:
                    add('RB-A FAULT reload failed (best effort, journal ROLLED-BACK anyway; rollback.lua:76)',
                        rb_done(s._replace(guard='vpn', jr='RB'), ctx), 'sup', 'fault')
            else:
                add('RB-A guard(devices) + ROLLED-BACK (rollback.lua:79-82)', rb_done(s._replace(guard='vpn', jr='RB'), ctx), 'sup')
        elif k == 2:
            add('RB-B guard(): full LAN block (rollback.lua:144)', s._replace(guard='full', sup=('RB', 3, ctx)), 'sup')
        elif k == 3:
            if s.uci == 'F':
                add('RB-B order foreign: abandon (rollback.lua:162-165)', abandon(s, ctx), 'sup', 'abandon')
            else:
                add('RB-B uci reorder: primary first (rollback.lua:169)', s._replace(uci='P', sup=('RB', 4, ctx)), 'sup')
        elif k == 4:
            add('RB-B kernel apply dispatched', s._replace(kern='X', sup=('RB', 5, ctx)), 'sup', 'move-to-P')
            if cfg.faults:
                # G7: the vendor write failed: the kernel stands, the full block releases itself, RESTORING stays
                add('RB-B FAULT apply failed: the full block stays', rb_failed(s, ctx), 'sup', 'fault')
        elif k == 5:
            add('RB-B kernel rebuilt from UCI (primary first)', s._replace(kern=s.uci, sup=('RB', 6, ctx)), 'sup')
            if cfg.faults:
                add('RB-B FAULT ROLLBACK-UNVERIFIED (rollback.lua:182-184)',
                    rb_failed(s._replace(guard='vpn'), ctx), 'sup', 'fault')
        elif k == 6:
            if s.kern != 'P' or s.uci != 'P':
                add('RB-B verify: ROLLBACK-UNVERIFIED', rb_failed(s._replace(guard='vpn'), ctx), 'sup')
            elif key_pin(cfg) == 'blocker' and (s.kp or s.kr):
                # finding 1: the key was a blocker of the proof: the route is back, the journal stays RESTORING
                add('RB-B verify: SERVER-KEY-UNACCEPTED fails the proof (before the fix)', rb_failed(s._replace(guard='vpn'), ctx), 'sup')
            else:
                add('RB-B journal ROLLED-BACK + guard(devices) (rollback.lua:197-201)',
                    rb_done(s._replace(jr='RB', guard='vpn'), ctx), 'sup')
        return out

    # --------------------------------------------------------------------------------- finish_committed (transaction.lua:757)
    if proc == 'FIN':
        if s.uci == 'F':
            add('FIN order foreign: abandon -> EXTERNAL-POLICY-CHANGE-RELEASED (transaction.lua:761-765)',
                abandon(s, ctx), 'sup', 'abandon')
        elif s.uci != 'P' and not (s.pHold if ('K2' in cfg.fixed and ctx in ('cl-tick', 'cl-rec', 'cl-st') and not s.stopped and s.rUp)
                                   else s.pStable):           # fix2 K2: pair.cleanup_hold -> finish_committed(hold)
            n = s._replace(guard='vpn', jr='HOR')
            if ctx in ('cl-tick', 'cl-rec', 'cl-st'):
                n = n._replace(sess='HELD')                           # pair.lua:922
                if ctx == 'cl-st':
                    n = st_post(n)
                elif ctx == 'cl-rec':
                    n = n._replace(code='OTHER', sup=IDLE, resume=True)  # pair.recover -> publish_failure
                else:
                    n = n._replace(sup=IDLE)
            else:
                n = n._replace(sup=IDLE)
            add('FIN primary not ready: HELD-ON-RESERVE (transaction.lua:774-779)', n, 'sup')
        else:
            add('FIN return to the primary (transaction.lua:790)', s._replace(sup=('RB', 0, ctx)), 'sup',
                *(() if ctx == 'ret' else ('return:' + ctx,)))
        return out

    # --------------------------------------------------------------------------------- pair.cleanup (pair.lua:901-965)
    if proc == 'CL':
        if k == 0:
            if 'K11' in cfg.fixed and s.sess in TERM:
                # fix K11 (04.11.2026): pair.cleanup re-reads the record under the control lock before its STOPPING write;
                # a record finished meanwhile (the owner's Start handed the HELD session over: STOPPED) ends the pass
                # without a write (cleanup -> false: recover publishes without a state write, the tick returns)
                n = s._replace(sup=IDLE, resume=True) if ctx == 'rec' else st_post(s) if ctx == 'st' else s._replace(sup=IDLE)
                add('CL0 superseded by the Start hand-over: no write (pair.lua cleanup, K11)', n, 'sup')
                return out
            n, extra = server_resume(s)                              # pair.lua:905
            add('CL0 session STOPPING (pair.lua:909)', n._replace(sess='STOPPING', sup=('CL', 1, ctx)), 'sup', *extra)
        elif k == 1:
            if s.jr in RECOVERY:
                add('CL1 journal mid-switch: PAIR-RECOVERY-REQUIRED (pair.lua:915)', cl_fail(s, ctx, 'OTHER'), 'sup')
            elif s.jr in ('COMMITTED', 'HOR'):
                # boot_handover: resume_pending = owner's marker, no newer Stop, young boot or a forward-resumed tx (G3: the
                # uptime window, any journal inside it). HANDOVER_WAIT and one attempt per boot are free: it may always refuse.
                if (boot_window(s, cfg) and not (s.pHold if 'K2' in cfg.fixed else s.pStable) and s.kern == 'R'
                        and s.uci == 'R' and s.rUp):
                    n = s._replace(guard='vpn', sess='STOPPED', ho=True, sup=IDLE)
                    if ctx == 'rec':
                        n = n._replace(resume=True)
                    elif ctx == 'st':
                        n = st_post(n)
                    add('CL1 boot handover on the reserve (pair.lua:837-869)', n, 'sup')
                add('CL1 finish_committed(PAIR-STOPPED) (pair.lua:920-921)', s._replace(sup=('FIN', 0, 'cl-' + ctx)), 'sup')
            else:
                add('CL1 journal settled', s._replace(sup=('CL', 3, ctx)), 'sup')
        elif k == 3:
            if s.uci != 'P':
                add('CL3 order_is(state.order) failed: PAIR-EXTERNAL-POLICY-CHANGE (pair.lua:931)',
                    cl_fail(s, ctx, 'READOPT', cfg), 'sup')
            else:
                if s.ext == 'net':
                    add('CL5 identity changed: PAIR-EXTERNAL-NETWORK-CHANGE (pair.lua:944)', cl_fail(s, ctx, 'READOPT', cfg), 'sup')
                    if s.code == 'READOPT' and not s.stopped:
                        return out                           # pair.outside_recheck (finding 5): the hold checks also with nothing owned
                    # G5: the check sits in the loop over the owned clients: a session owning none ends STOPPED (free choice)

                def finished(n):
                    if ctx == 'st':
                        return st_post(n)
                    return n._replace(sup=IDLE, resume=True) if ctx == 'rec' else n._replace(sup=IDLE)
                add('CL6 clients down, unguard, STOPPED (pair.lua:954)',
                    finished(s._replace(guard='none', sess='STOPPED', code='-', ran=False, ho=False)), 'sup')
                if s.ext != 'net' and boot_window(s, cfg):
                    # G2 variant C: the boot resume will press Start and every owned client is up (free): the clients and the guard stay
                    add('CL6 boot_keep: clients kept for the Start, the guard stays (pair.lua boot_keep)',
                        finished(s._replace(sess='STOPPED', code='-', ran=False, ho=False, kept=True)), 'sup')
        return out

    # --------------------------------------------------------------------------------- pair.begin (pair.lua:638-701)
    if proc == 'BEGIN':
        if k == 0:
            handover = s.sess == 'STOPPED' and s.ho and s.jr in ('COMMITTED', 'HOR')
            live = 'P' if s.uci == 'F' else s.uci
            if s.prep:
                add('BEGIN0 preflight: PAIR-PROFILES-UNVERIFIED (pair.lua:651)', tick_error(s, 'OTHER'), 'sup')
            elif ('P' if s.kern == 'F' else s.kern) != live:
                add('BEGIN0 preflight: kernel does not match the live order (pair_preflight attest)', tick_error(s, 'OTHER'), 'sup')
            elif key_pin(cfg) == 'directional' and key_on_carrying(s):
                add('BEGIN0 SERVER-KEY-UNACCEPTED: the Start is refused, nothing taken (pair.begin)', tick_error(s, 'OTHER'), 'sup')
            elif handover and not (s.kern == 'R' and s.uci == 'R' and s.rUp):
                n = s._replace(sess='HELD', ho=False)
                add('BEGIN0 handover not adoptable: BOOT-RESERVE-UNVERIFIED (pair.lua:657, 1339-1342)',
                    n._replace(intent='off', fresh=False, code='OTHER', sup=IDLE), 'sup')
            else:
                n = s._replace(ext='none', uci='P' if s.uci == 'F' else s.uci, kern='P' if s.kern == 'F' else s.kern)
                add('BEGIN1 session STARTING (pair.lua:675)',
                    n._replace(sess='STARTING', code='-', ran=False, ho=False, kept=False, fresh=False,
                               sup=('BEGIN', 2, 'ho' if handover else 'oh' if ('K4' in cfg.fixed and s.guard == 'vpn' and s.jr in SETTLED) else '')),
                    'sup', 'begin')
        elif k == 2:
            if 'K4' in cfg.fixed and ctx in ('ho', 'oh'):
                # fix2 K4: a standing VPN-only guard - the handover's, or the outside-change hold's (K9; approximated
                # here by any VPN-only guard with a settled journal, the code keeps it only after outside_hold) - stays
                add('BEGIN2 fix2 K4: a standing VPN-only guard is kept while the clients start (pair.begin keep_vpn)',
                    s._replace(guard='vpn', sup=('BEGIN', 3, ctx)), 'sup')
            else:
                add('BEGIN2 guard(): full LAN block while clients start (pair.lua:676)', s._replace(guard='full', sup=('BEGIN', 3, ctx)), 'sup')
        elif k == 3:
            if s.intent != 'on':
                add('BEGIN3 require_running: CLIENT-STOP (pair.lua:680)', tick_error(s, 'OTHER'), 'sup')
            else:
                n = s._replace(guard='vpn', sess='RUNNING', ran=True, sup=('BEGIN', 4, ctx) if ctx == 'ho' else IDLE)
                add('BEGIN4 guard(devices) + RUNNING (pair.lua:694-697)', n, 'sup')
        elif k == 4:
            add('BEGIN5 adopt the handed-over journal: COMMITTED BOOT-RESERVE-ADOPTED (pair.lua:889-897)',
                s._replace(jr='COMMITTED', ho=False, txrev=True, sup=IDLE, kv=bool(key_pin(cfg))), 'sup')    # adopt_journal: remember_selected
        return out

    # --------------------------------------------------------------------------------- auto.recover (auto.lua:132-235)
    if proc == 'REC':
        if k == 1:
            n, extra = server_resume(s)                              # server_resume_boot (auto.lua:162)
            if n.jr in RECOVERY:
                if n.fails >= 2:
                    add('REC2 rollback_failures limit: give_up ROLLBACK-GIVEN-UP (auto.lua:178)',
                        n._replace(sup=BLOCKED, guard='vpn', marker=False), 'sup', *extra)
                elif n.jr in ('APPLYING', 'WAIT') and fres_decide(n):
                    add('REC2 forward_resume.decide accepted (forward_resume.lua:54-79)', n._replace(sup=('FRES', 0, '')),
                        'sup', *extra)
                else:
                    add('REC2 boot_rollback SUPERVISOR-RECOVERY (auto.lua:196)', n._replace(sup=('RB', 0, 'rec')), 'sup',
                        'undo-forward', *extra)
            elif n.jr == 'HOR' and n.uci == 'R' and 'K3' in cfg.fixed:
                add('REC2 fix2 K3: HELD-ON-RESERVE on its route: guard(devices) (auto.recover / native_switch.serve)',
                    n._replace(guard='vpn', sup=('REC', 3, '')), 'sup', *extra)
            elif n.jr == 'COMMITTED':
                if n.uci != 'R':
                    add('REC2 COMMITTED but order changed: abandon (auto.lua:203)', abandon(n, 'rec'), 'sup', 'abandon', *extra)
                else:
                    add('REC2 COMMITTED: guard(devices) (auto.lua:205-206)', n._replace(guard='vpn', sup=('REC', 3, '')),
                        'sup', *extra)
            else:
                add('REC2 journal settled', n._replace(sup=('REC', 3, '')), 'sup', *extra)
        elif k == 3:
            if s.sess in NONTERM:
                add('REC3 pair.recover -> cleanup (auto.lua:219, pair.lua:967)', s._replace(sup=('CL', 0, 'rec')), 'sup')
            else:
                add('REC4 recovery finished, supervisor-start token (auto.lua:229)', s._replace(sup=IDLE, resume=True), 'sup')
        return out

    # --------------------------------------------------------------------------------- server change (pair.lua:1474-1539)
    if proc == 'SRV':
        tun = s.sc[1]
        if k == 1:
            add('SRV1 server_change APPLYING saved (pair.lua:1517)', s._replace(sc=('APPLYING', tun, False), sup=('SRV', 2, '')), 'sup')
        elif k == 2:
            add('SRV2 server_apply: uci/network of tunnel %s (pair.lua:1520)' % tun,
                s._replace(sc=('CONNECTING', tun, False), sup=IDLE), 'sup', 'server-write:' + tun)
        return out
    raise AssertionError(s.sup)


def fwd_fail(s):
    """attempt failure after APPLYING was written: failure_code, then rollback_counted (transaction.lua:670-681)."""
    return s._replace(failed=True, sup=('RB', 0, 'fwd'))


def st_post(s):
    # the rest of the tick catch after cleanup(pending) of a STARTING session (pair.lua:1348-1355)
    if (s.sess in TERM or (s.sess == 'HELD' and not s.ran)) and s.intent == 'on':
        s = s._replace(intent='off', fresh=False)                    # fail_request
    if s.sess in NONTERM:
        s = s._replace(sess='HELD', code='OTHER' if s.code == '-' else s.code)
    if s.jr in RECOVERY:
        return fence(s)._replace(sup=DOWN)
    return s._replace(sup=IDLE)


def cl_fail(s, ctx, cls, cfg=None):
    if cfg is not None and 'K9' in cfg.fixed and cls == 'READOPT' and ctx in ('rec', 'tick') and s.jr in SETTLED:
        # fix2 K9 (owner decision 03.11.2026): pair.outside_hold after a failed recovery/cleanup of a session that is not
        # running: VPN-only (or the re-armed full block) until Start or Stop; the owner's Stop releases it
        s = s._replace(guard='none' if s.stopped else 'vpn')
        if 'T4A' in cfg.fixed and s.stopped and s.intent != 'on':
            # T4A (c31d7332): outside_hold -> end_hold_on_stop. publish_failure wrote HELD, then the owner's Stop retires the
            # record under the control lock (release_session adopted_by='owner-stop': archived, STOPPED, owned=[], no profile
            # stopped, the readopt budget neither checked nor spent). One model step: a kill between the two writes leaves the
            # HELD record with the Stop latch, which the next pass ends the same way. The 'st' context is not covered (as for
            # K9): its HELD record ends on the next pass.
            n = s._replace(sess='STOPPED', code='-', ran=False, ho=False)
            return n._replace(sup=IDLE, resume=True) if ctx == 'rec' else n._replace(sup=IDLE)
    if ctx == 'st':
        return st_post(s._replace(sess='HELD', code=cls))
    if ctx == 'rec':
        n = s
        if n.sess in NONTERM:
            n = n._replace(sess='HELD', code=cls)                     # pair.recover -> publish_failure
        return n._replace(sup=IDLE, resume=True)
    return tick_error(s, cls)


def fres_decide(s):
    """forward_resume.decide (forward_resume.lua:54-79) on the model."""
    return (not s.failed and s.fails == 0 and not s.fres and not s.boot and s.marker and not s.stopped
            and not s.pUp and s.rUp)


def server_resume(s):
    """pair.server_resume (pair.lua:1573-1609): adopt, or restore 'from' unless its tunnel carries.
    -> (state without the record, extra transition tags)"""
    phase, tun, verified = s.sc
    if phase == '-':
        return s, ()
    n = s._replace(sc=('-', '', False))
    if phase in ('APPLYING', 'CONNECTING') and not verified:
        # server_carrying(): true unless the kernel proves the traffic on the other tunnel
        if carrying(s.kern) is not None and carrying(s.kern) != tun:
            return n, ('server-write:' + tun,)
    return n, ()


def tick(s, cfg):
    out = []

    def add(label, n, *tags):
        out.append((label, n, frozenset(tags)))

    running = s.intent == 'on'
    # boot/restart resume of the monitor: Start(programmatic) every 5 s while its window is open
    if s.resume and s.marker and not s.stopped and s.intent == 'off':
        ok, n, why = start(s, cfg, manual=False)
        if ok:
            add('RESUME Start(programmatic) accepted (boot_resume.py:134)', n._replace(resume=False), 'sup', 'resume')
        elif n != s:
            add('RESUME Start(programmatic) refused %s' % why, n, 'sup')
    if s.sess == 'STOPPED' and s.ho and not running:
        return out                                                   # the handover waits for the Start (pair.lua:1157)
    if s.kept and not running:
        # G2: no Start within KEEP_SECONDS, a Stop, a failed resume (free): the kept clients stop, the guard goes
        add('TICK release_kept (pair.lua release_kept)', s._replace(guard='none', kept=False), 'sup')
    if ('K9' in cfg.fixed and s.sess == 'HELD' and s.code == 'READOPT' and s.jr in SETTLED and not running and not s.stopped
            and s.guard in ('vpn', 'full')):
        # G1: pair.outside_hold follows the tunnels (free): VPN-only on those up, with none up the re-armed full block
        add('TICK outside_hold: the tunnels changed (pair.lua outside_hold)', s._replace(guard='full' if s.guard == 'vpn' else 'vpn'), 'sup')
    relevant = running or s.sess in NONTERM
    if not relevant:
        # native path of iteration (auto.lua:270-330)
        if s.jr == 'COMMITTED':
            add('NATIVE finish_committed(TRIAL-ENDED) (auto.lua:310)', s._replace(sup=('FIN', 0, 'native')), 'sup')
        elif s.jr == 'HOR' and s.pStable and s.uci != 'F':
            add('NATIVE HELD-ON-RESERVE: operator_return PRIMARY-RECOVERED (auto.lua:292-297)',
                s._replace(sup=('RB', 0, 'native')), 'sup', 'return:native')
        elif s.jr == 'RB' and s.uci == 'P' and s.guard != 'none':
            add('NATIVE unguard_if_restored (auto.lua:316)', s._replace(guard='none'), 'sup')
        elif s.sess == 'STOPPED' and s.stopped and s.jr in SETTLED and s.guard != 'none' and not s.kept:
            add('TICK release_orphan_guard after the owner Stop (finding 4, pair.lua)', s._replace(guard='none'), 'sup')
        return out
    if not running:
        add('TICK not running: cleanup (pair.lua:1170-1176)', s._replace(sup=('CL', 0, 'tick')), 'sup')
        return out
    if s.sess == 'NONE' or s.fresh or s.sess in TERM:
        if s.sess in NONTERM:
            add('TICK new request on a held session: PAIR-RECOVERY-REQUIRED (pair.lua:1179)', tick_error(s, 'OTHER'), 'sup')
        else:
            add('TICK begin (pair.lua:1180)', s._replace(sup=('BEGIN', 0, ''), kv=False), 'sup')
        return out
    if s.ext == 'net':
        if 'F32' in cfg.fixed:
            # F32: readopt_class of PAIR-EXTERNAL-NETWORK-CHANGE / -CONFIG-CHANGE reads which packages changed. The model's
            # 'net' does not say which (the network outside the pair, Wi-Fi, DHCP, DNS: ADOPT; the VPN profiles, the firewall,
            # any other package, an unreadable or empty class: HOLD), so both outcomes are free choices.
            if can_readopt(s):
                add('TICK identity changed: readopt_class ADOPT (network/wireless/dhcp/gl-dns-v2 only; pair_auto.readopt_running)',
                    readopt(s), 'sup')
            add('TICK identity changed: PAIR-EXTERNAL-NETWORK-CHANGE, readopt_class HOLD (pair_auto.readopt_running)',
                tick_error(s, 'READOPT', adopt=False), 'sup')
        else:
            add('TICK identity changed: PAIR-EXTERNAL-NETWORK-CHANGE (pair.lua:1192)', tick_error(s, 'READOPT'), 'sup')
        return out
    if s.sc[0] != '-':
        out.extend(server_pending(s, cfg))
        if out:
            return out
        s = s._replace(sc=('-', '', False))
    if cfg.server and s.sess == 'RUNNING' and s.sc[0] == '-' and s.kern in ('P', 'R'):
        # server_start gate (server_pick.lua:518-534): stage 2 idle reserve, stage 3 failed primary
        if s.kern == 'P' and s.uci == 'P' and s.jr in SETTLED:
            add('SRV0 owner/pick asks: change the idle reserve server (server_pick.lua:530)',
                s._replace(sc=('-', 'R', False), sup=('SRV', 1, '')), 'sup')
        if s.kern == 'R' and s.uci == 'R' and s.jr == 'COMMITTED':
            add('SRV0 change the failed primary server (stage 3, server_pick.lua:531)',
                s._replace(sc=('-', 'P', False), sup=('SRV', 1, '')), 'sup')
    if s.uci == 'F' or s.kern == 'F':
        # G6: before the committed decision and before the reserve health (reapply_missing_policy; T3 keeps it for a lost reserve)
        # F32: the pair's own route_policy or its order (readopt_class POLICY-OR-ORDER) is never adopted by itself: HELD
        add('TICK order check: PAIR-EXTERNAL-POLICY-CHANGE (pair.lua reapply_missing_policy)',
            tick_error(s, 'READOPT', adopt='F32' not in cfg.fixed), 'sup')
        return out
    pin = key_pin(cfg)
    if pin and ((pin == 'blocker' and (s.kp or s.kr)) or (not s.kv and key_on_carrying(s))):
        # reapply_missing_policy. 'blocker' (before the fix, finding 2): every pass ends BLOCKED. The code: only a Start waits, on
        # the key of the carrying channel (a key on the other channel is left to the directional gate)
        return out
    if pin and not s.kv and s.jr not in RECOVERY:
        add('TICK the route proved: selected_policy (pair.lua remember_selected)', s._replace(kv=True), 'sup')
        return out
    if s.jr in ('COMMITTED', 'HOR'):
        # committed_recovery_decision with the damped hold (pair.lua:1206-1245, transaction.lua:803-839).
        # The model has no return-policy dimension: it describes healthy_primary. Since 07.11.2026 (owner decision, F-80)
        # the first term (a dead reserve, the primary stable: the rescue) also holds under hold_reserve, which now only
        # keeps a WORKING reserve (rUp); the planned second term is healthy_primary only. The code probes the reserve
        # once more before the rescue; here 'ENV reserve tunnel fails' is that proof (no stale/unknown health in the model).
        restore = (not s.rUp and s.pStable) or (s.pHold and s.dwell)
        n = s._replace(sess='RUNNING', code='-') if (s.sess == 'HELD' and s.ran) else s
        if s.rgen:
            # K12 (finding 7, MT3000 04.11.2026 14:06-15:33): the vendor rebuilt the carrying reserve, only its generation
            # changed. Before the fix every pass held RESERVE-IDENTITY-UNKNOWN: no return to a healthy primary, ever.
            # Fixed: a healthy streak of the new generation is the same reserve (pair.reserve_rebound rebinds the journal
            # proof, the decision goes on); anything else stays unknown, and only the planned rule may leave it.
            if 'K12' not in cfg.fixed:
                return out
            if s.rUp:
                n = n._replace(rgen=False)
                add('TICK reserve rebuilt, healthy streak of the new generation: journal proof rebound (transaction.lua, pair.reserve_rebound)',
                    n, 'sup')
                return out
            restore = s.pHold and s.dwell
        if restore and not (pin and s.kp):      # T.committed_recovery_decision: no return onto an unaccepted key
            add('TICK committed decision RESTORE-PRIMARY (pair.lua:1211-1214)', n._replace(sup=('FIN', 0, 'ret')), 'sup',
                'return:ret')
        elif n != s:
            add('TICK committed decision OBSERVE (resume_running)', n, 'sup')
        return out
    if not s.rUp:
        # the blocker RESERVE-NOT-CONNECTED ends the pass; G6: a reserve unhealthy but connected resumes the session first
        if s.sess == 'HELD' and s.ran and s.uci == 'P' and s.kern == 'P':
            add('TICK resume_running (reserve unhealthy, still connected)', s._replace(sess='RUNNING', code='-'), 'sup')
        return out
    if s.uci != 'P' or s.kern != 'P':
        return out                                                   # attestation blocks / reapply (not modelled)
    n = s._replace(sess='RUNNING', code='-') if (s.sess == 'HELD' and s.ran) else s
    if (not s.pUp or cfg.fast_switch) and s.rUp and s.dwell and not (pin and s.kr):
        # fast_switch: leave_rule may also speak for a live primary (N failed samples in a row, the heartbeat verdict)
        add('TICK failed and healthy and dwell: forward switch (pair.lua:1291)', n._replace(sup=('FWD', 0, '')), 'sup')
    elif n != s:
        add('TICK resume_running', n, 'sup')
    return out


def server_pending(s, cfg):
    """pair.server_pending (pair.lua:1619-1660)."""
    out = []
    phase, tun, verified = s.sc
    if phase == 'APPLYING':
        n, extra = server_resume(s)
        out.append(('SRVP APPLYING found: server_resume (pair.lua:1624)', n, frozenset({'sup', *extra})))
        return out
    healthy = s.rUp if tun == 'R' else s.pUp
    if phase == 'CONNECTING':
        if healthy:
            out.append(('SRVP CONNECTING: new server healthy -> SETTLING verified (pair.lua:1643)',
                        s._replace(sc=('SETTLING', tun, True)), frozenset({'sup'})))
        out.append(('SRVP CONNECTING timeout: restore the previous server of %s (pair.lua:1645)' % tun,
                    s._replace(sc=('SETTLING', tun, False)), frozenset({'sup', 'server-write:' + tun})))
        return out
    if phase == 'SETTLING':
        out.append(('SRVP SETTLING done: record cleared (pair.lua:1652-1655)', s._replace(sc=('-', '', False)), frozenset({'sup'})))
        return out
    return out


# ---------------------------------------------------------------------------------------------------------------
# Environment and owner
# ---------------------------------------------------------------------------------------------------------------
def env_steps(s, cfg):
    out = []

    def add(label, n, kind):
        out.append((label, n, frozenset({kind})))

    # tunnel health (live)
    if s.pUp:
        add('ENV primary tunnel fails', s._replace(pUp=False, pStable=False, pHold=False), 'health-bad')
    else:
        add('ENV primary tunnel recovers', s._replace(pUp=True), 'health-good')
    if s.rUp:
        add('ENV reserve tunnel fails', s._replace(rUp=False), 'health-bad')
    else:
        add('ENV reserve tunnel recovers', s._replace(rUp=True), 'health-good')
    # time
    if s.pUp and not s.pStable:
        add('TIME primary stable for primary_stable', s._replace(pStable=True), 'time')
    if s.pStable and not s.pHold:
        add('TIME primary stable for the damped return_hold', s._replace(pHold=True), 'time')
    if not s.dwell:
        add('TIME max(cooldown,min_dwell) since the last switch', s._replace(dwell=True), 'time')
    if s.readopt > 0:
        add('TIME a readopt ledger entry ages out (900 s)', s._replace(readopt=s.readopt - 1), 'time')
    if s.resume:
        add('TIME boot-resume window over (boot_resume.WINDOW)', s._replace(resume=False), 'time')
    if s.young:
        add('TIME uptime over BOOT_KEEP_UPTIME (pair.lua resume_pending)', s._replace(young=False), 'time')
    if s.sess == 'STOPPED' and s.ho and s.intent == 'off':
        add('TIME handover not taken in KEEP_SECONDS: release_handover -> HELD (pair.lua:872)',
            s._replace(sess='HELD', ho=False), 'time')
    if s.kern == 'X':
        add('VENDOR rebuild finished: kernel follows UCI', s._replace(kern=s.uci), 'vendor')
    if cfg.rebuild and s.jr in ('COMMITTED', 'HOR') and s.kern == 'R' and not s.rgen:
        # not a 'vendor' step: the fair runs of the liveness checks would count on it never happening again
        add('VENDOR rebuilt the carrying reserve: its generation changed (K12, finding 7)', s._replace(rgen=True), 'rebuild')
    # fix2 K4: begin() re-arms the block before every bounded step (< 90 s): it can lapse only after a lost process
    if cfg.expire and s.guard == 'full' and (s.sup[0] in ('DOWN',) or (s.sup[:2] == ('BEGIN', 3) and 'K4' not in cfg.fixed)):
        add('TIME full LAN block self-released after 90 s (backend.lua:54,825)', s._replace(guard='none'), 'expire')
    if key_pin(cfg):
        # the monitor compares a key only on a channel it has just measured healthy (server_pin.py, agent.py)
        if s.pUp and not s.kp:
            add('ENV the primary server key changes', s._replace(kp=True), 'key')
        if s.rUp and not s.kr:
            add('ENV the reserve server key changes', s._replace(kr=True), 'key')
    # outside changes in the GL panel
    if s.ext == 'none' and cfg.gl:
        if cfg.ext in ('both', 'net'):
            add('OWNER changes VPN clients in the GL panel (network/config)', s._replace(ext='net', prep=True), 'gl')
        if cfg.ext in ('both', 'pol'):
            add('OWNER changes route policy in the GL panel', s._replace(ext='pol', uci='F', kern='F', prep=True), 'gl')
    # crash / power cut
    if s.sup[0] not in ('DOWN', 'GIVEUP') and cfg.crash:
        add('CRASH supervisor killed (procd restarts it)', s._replace(sup=DOWN), 'crash')
    if cfg.power and s.sup != BLOCKED:
        add('POWER cut: RAM lost (guard, intent, revision, readopt ledger), kernel rebuilt from UCI',
            s._replace(sup=DOWN, guard='none', intent='off', fresh=False, txrev=False, readopt=0, kern='X',
                       boot=True if s.jr in RECOVERY or s.jr in ('COMMITTED', 'HOR') else s.boot, resume=s.marker,
                       young=cfg.window, pStable=False, pHold=False), 'power')
    return out


def owner_steps(s, cfg):
    out = []
    ok, n, why = start(s, cfg, manual=True)
    if ok and why is None:
        out.append(('OWNER Start', n, frozenset({'owner'})))
    elif not ok:
        if n != s:
            out.append(('OWNER Start refused %s (after a hand-over)' % why, n, frozenset({'owner'})))
    if not s.stopped or s.intent == 'on' or s.marker:
        out.append(('OWNER Stop', stop(s), frozenset({'owner', 'stop'})))
    if s.kp or s.kr:
        out.append(('OWNER accepts the server keys (homensai-vpn-server-key accept)', s._replace(kp=False, kr=False), frozenset({'owner'})))
    return out


def successors(s, cfg):
    res = []
    for label, n, tags in sup_steps(s, cfg):
        res.append((label, n, tags))
    for item in env_steps(s, cfg):
        res.append(item)
    for item in owner_steps(s, cfg):
        res.append(item)
    if s.rgen:
        # the stale proof lives in the journal of this switch: it ends with the switch
        res = [(label, n._replace(rgen=False) if n.jr not in ('COMMITTED', 'HOR', 'RESTORING') else n, tags) for label, n, tags in res]
    return res


# ---------------------------------------------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------------------------------------------
def owned(s):
    return s.sess in NONTERM or s.jr in RECOVERY or s.jr in ('COMMITTED', 'HOR')


def leak(s):
    """LAN traffic could leave outside a VPN tunnel: no guard while the route is ours and unsafe."""
    if not owned(s) or s.guard != 'none':
        return None
    if s.kern == 'F' or s.uci == 'F':
        return None                                   # the owner's own GL configuration (abandoned to the owner)
    if s.stopped and s.jr in SETTLED and s.kern == 'P' and s.uci == 'P':
        return None                                   # after the owner's Stop on the primary: the cleanup unguards anyway
    unsafe = s.kern == 'X' or (s.kern == 'P' and not s.pUp) or (s.kern == 'R' and not s.rUp)
    if not unsafe:
        return None
    if in_recovery(s):
        return 'recovery-window'      # supervisor (re)start after a crash/power cut, before its guard step
    if s.sess == 'STARTING':
        return 'begin-window'         # begin(): before guard(), or the 90 s full block expired during the client start
    return 'running'


def family(s, kind):
    """The mechanism behind a leak state (report only)."""
    if kind == 'begin-window' and s.sup[:2] == ('BEGIN', 2):
        return 'begin-instant (between the STARTING write and guard(), no I/O wait)'
    if s.stopped and s.jr in SETTLED and s.uci == 'P':
        return 'after the owner Stop (guard released by the owner decision; kernel rebuilt from UCI primary)'
    if kind == 'recovery-window':
        return 'recovery-window (power cut/crash until the recovery guard step)'
    if s.jr == 'HOR' and s.uci == 'R':
        return 'K3 HELD-ON-RESERVE without guard'
    if s.sess == 'STARTING' or s.sup[0] == 'BEGIN' or s.sup[2] == 'st':
        return 'K4 begin block lapsed (and its cleanup)'
    if (s.readopt > 0 or (s.intent == 'on' and s.fresh)) and s.sess in ('STOPPING', 'HELD') and s.code != 'READOPT' and s.jr in SETTLED:
        return 'K11 Start hand-over (release_for_start) raced by an in-flight cleanup pass'
    if s.sess == 'HELD' and s.code == 'READOPT':
        return 'K9 HELD by an outside change without guard'
    return 'other ' + kind


def in_recovery(s):
    proc, _, ctx = s.sup
    return proc in ('DOWN', 'REC', 'FRES') or ctx in ('rec', 'cl-rec')


def consistent(s):
    """At rest (IDLE, no alarm) the journal and the kernel tell the same route."""
    if s.sup != IDLE or s.uci == 'F' or s.kern == 'F':
        return True
    if s.jr in SETTLED:
        return s.uci == 'P' and s.kern in ('P', 'X')
    if s.jr in ('COMMITTED', 'HOR'):
        return s.uci == 'R' and s.kern in ('R', 'X')
    return False


def transition_checks(s, n, label, tags):
    v = []
    if 'armed' in tags and s.jr not in SETTLED:
        v.append('TWO-TRANSACTIONS')
    if 'armed' in tags and s.kr:
        v.append('MOVE-ONTO-UNACCEPTED-KEY')     # --key-pin: a key that changes during a transaction ends with it, as in the code
    if 'begin' in tags and s.jr in RECOVERY:
        v.append('BEGIN-DURING-TRANSACTION')
    if 'begin' in tags and key_on_carrying(s):
        v.append('BEGIN-WITH-UNACCEPTED-KEY')    # --key-pin: no session, guard or client for a Start with an unaccepted key on the carrying channel
    if 'move-to-R' in tags and s.stopped:
        v.append('SWITCH-AFTER-STOP')
    if 'committed' in tags and s.stopped:
        v.append('COMMITTED-AFTER-STOP')
    for t in tags:
        if t.startswith('server-write:'):
            tun = t.split(':')[1]
            c = carrying(s.kern)
            if c is None or c == tun:
                v.append('SERVER-WRITE-ON-CARRYING')
            if s.jr in RECOVERY:
                v.append('SERVER-WRITE-DURING-TRANSACTION')
        if t.startswith('return:'):
            ctx = t.split(':')[1]
            if s.rUp and s.marker and not s.stopped and not s.pHold:
                v.append('RETURN-BEFORE-HOLD:' + ctx)
            if ctx == 'ret' and s.kp:
                v.append('MOVE-ONTO-UNACCEPTED-KEY')
    if 'undo-forward' in tags and s.jr in ('APPLYING', 'WAIT') and not s.pUp and s.rUp and s.marker and not s.stopped:
        v.append('ROLLBACK-ONTO-DEAD-PRIMARY:' + ('power-cut' if s.boot else 'crash'))
    return v


# ---------------------------------------------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------------------------------------------
TAGID = {}
INTERN = {}
TAGLIST = []


def E(succ):
    return ((x >> 10, TAGLIST[x & 1023]) for x in succ)


class Graph:
    def __init__(self, cfg):
        self.cfg = cfg
        self.index = {}
        self.states = []
        self.parent = []
        self.begin_other_key = 0
        self.plabel = []
        self.edges = []          # list of lists (target, kinds)

    def explore(self, init, limit=6_000_000):
        self.index[init] = 0
        self.states.append(init)
        self.parent.append(-1)
        self.plabel.append('init')
        self.edges.append(None)
        tviol = collections.defaultdict(list)
        q = collections.deque([0])
        while q:
            i = q.popleft()
            s = self.states[i]
            succ = []
            for label, n, tags in successors(s, self.cfg):
                n = n._replace(sup=INTERN.setdefault(n.sup, n.sup), sc=INTERN.setdefault(n.sc, n.sc))
                for v in transition_checks(s, n, label, tags):
                    if len(tviol[v]) < 3:
                        tviol[v].append((i, label))
                if 'begin' in tags and (s.kp or s.kr) and not key_on_carrying(s):
                    self.begin_other_key += 1    # the witness of the rule of 05.11.2026: a Start with a key only on the other channel goes on
                j = self.index.get(n)
                if j is None:
                    j = len(self.states)
                    if j >= limit:
                        raise RuntimeError('state limit')
                    self.index[n] = j
                    self.states.append(n)
                    self.parent.append(i)
                    self.plabel.append(label)
                    self.edges.append(None)
                    q.append(j)
                tid = TAGID.get(tags)
                if tid is None:
                    tid = TAGID[tags] = len(TAGLIST)
                    TAGLIST.append(tags)
                succ.append(j << 10 | tid)
            self.edges[i] = array('q', succ)
            if i and i % 500000 == 0:
                print('  ... %d states expanded, %d known, queue %d' % (i, len(self.states), len(q)), file=sys.stderr, flush=True)
        return tviol

    def trace(self, i):
        path = []
        while i != -1:
            path.append((self.plabel[i], self.states[i]))
            i = self.parent[i]
        return list(reversed(path))

    def ef(self, goal, allowed):
        """Backward reachability: states from which a goal state is reachable using allowed edges only."""
        rev = [[] for _ in self.states]
        for i, succ in enumerate(self.edges):
            for j, tags in E(succ):
                if allowed(tags):
                    rev[j].append(i)
        good = bytearray(len(self.states))
        q = collections.deque()
        for i, s in enumerate(self.states):
            if goal(s):
                good[i] = 1
                q.append(i)
        while q:
            j = q.popleft()
            for i in rev[j]:
                if not good[i]:
                    good[i] = 1
                    q.append(i)
        return good

    def bottom_sccs(self, starts, allowed):
        """Tarjan (iterative) on the sub-graph reachable from starts via allowed edges; returns bottom SCCs."""
        sub = set()
        stack = list(starts)
        while stack:
            i = stack.pop()
            if i in sub:
                continue
            sub.add(i)
            for j, tags in E(self.edges[i]):
                if allowed(tags) and j not in sub:
                    stack.append(j)
        index = {}
        low = {}
        onstack = set()
        st = []
        comps = []
        counter = 0
        for root in sub:
            if root in index:
                continue
            work = [(root, 0)]
            while work:
                v, pi = work.pop()
                if pi == 0:
                    index[v] = low[v] = counter
                    counter += 1
                    st.append(v)
                    onstack.add(v)
                succ = [j for j, tags in E(self.edges[v]) if allowed(tags)]
                recurse = False
                for idx in range(pi, len(succ)):
                    w = succ[idx]
                    if w not in index:
                        work.append((v, idx + 1))
                        work.append((w, 0))
                        recurse = True
                        break
                    elif w in onstack:
                        low[v] = min(low[v], index[w])
                if recurse:
                    continue
                if low[v] == index[v]:
                    comp = []
                    while True:
                        w = st.pop()
                        onstack.discard(w)
                        comp.append(w)
                        if w == v:
                            break
                    comps.append(comp)
                if work:
                    u = work[-1][0]
                    low[u] = min(low[u], low[v])
        compof = {}
        for c, comp in enumerate(comps):
            for v in comp:
                compof[v] = c
        bottoms = []
        for c, comp in enumerate(comps):
            bottom = True
            for v in comp:
                for j, tags in E(self.edges[v]):
                    if allowed(tags) and compof.get(j) != c:
                        bottom = False
                        break
                if not bottom:
                    break
            if bottom:
                bottoms.append(comp)
        return bottoms, sub


def fmt_state(s):
    sc = '' if s.sc[0] == '-' else ' sc=%s:%s%s' % (s.sc[0], s.sc[1], '+' if s.sc[2] else '')
    return ('intent=%s%s marker=%d stopped=%d | sess=%s%s%s%s%s | jr=%s%s%s%s | uci=%s kern=%s guard=%s | '
            'P=%s R=%s stable=%d hold=%d dwell=%d | ext=%s prep=%d readopt=%d | sup=%s%s%s%s' % (
                s.intent, '*' if s.fresh else '', s.marker, s.stopped, s.sess,
                '(' + s.code + ')' if s.code != '-' else '', '+ran' if s.ran else '', '+handover' if s.ho else '', '+kept' if s.kept else '',
                s.jr, ' rtp' if s.rtp else '', ' fails=%d' % s.fails if s.fails else '', ' fres' if s.fres else '',
                s.uci, s.kern, s.guard, 'up' if s.pUp else 'DOWN', 'up' if s.rUp else 'DOWN', s.pStable, s.pHold,
                s.dwell, s.ext, s.prep, s.readopt, ':'.join(str(x) for x in s.sup if x != ''),
                ' boot' if s.boot else '', ' resume' if s.resume else '', sc))


def print_trace(g, i, out, extra=None):
    for step, (label, s) in enumerate(g.trace(i)):
        out.append('  %2d. %s' % (step, label))
        out.append('      %s' % fmt_state(s))
    if extra:
        out.append('  -> %s' % extra)


def run(cfg):
    t0 = time.time()
    g = Graph(cfg)
    tviol = g.explore(INIT)
    n = len(g.states)
    edges = sum(len(e) for e in g.edges)
    res = {'variant': 'fix2' if cfg.fixed == ALL_FIXES else 'fix' if cfg.fix else 'alpha6', 'fixed': sorted(cfg.fixed), 'options': {k: getattr(cfg, k) for k in ('faults', 'server', 'fast_switch', 'gl', 'ext', 'crash', 'power', 'expire', 'rebuild', 'window', 'key_pin')},
           'states': n, 'transitions': edges}
    lines = ['=== variant %s, options %s: %d states, %d transitions (%.1f s)' % (
        res['variant'], res['options'], n, edges, time.time() - t0)]

    # --- state invariants
    inv = collections.OrderedDict()
    fam = collections.OrderedDict()
    for i, s in enumerate(g.states):
        lk = leak(s)
        if lk:
            inv.setdefault('LEAK:' + lk, []).append(i)
            fam.setdefault(family(s, lk), []).append(i)
        if not consistent(s):
            inv.setdefault('INCONSISTENT', []).append(i)
    res['invariants'] = {k: len(v) for k, v in inv.items()}
    res['leak_families'] = {k: len(v) for k, v in fam.items()}
    for k, v in fam.items():
        lines.append('LEAK FAMILY %s: %d states; shortest trace:' % (k, len(v)))
        print_trace(g, min(v), lines)
    for k, v in inv.items():
        best = min(v)  # BFS order: the lowest index has the shortest trace
        lines.append('INVARIANT %s violated in %d states; shortest trace:' % (k, len(v)))
        print_trace(g, best, lines)
    if not inv:
        lines.append('INVARIANTS LeakFree, Consistency: hold')
    # --- transition assertions
    res['transition'] = {k: len(v) for k, v in tviol.items()}
    res['begin_other_key'] = g.begin_other_key
    for k, v in tviol.items():
        i, label = min(v)
        lines.append('TRANSITION %s: e.g. from state below by "%s"' % (k, label))
        print_trace(g, i, lines, 'next: ' + label)
    for k in ('TWO-TRANSACTIONS', 'BEGIN-DURING-TRANSACTION', 'SWITCH-AFTER-STOP', 'SERVER-WRITE-ON-CARRYING',
              'SERVER-WRITE-DURING-TRANSACTION', 'MOVE-ONTO-UNACCEPTED-KEY', 'BEGIN-WITH-UNACCEPTED-KEY'):
        if k not in tviol:
            lines.append('TRANSITION %s: never' % k)

    # --- EF: no permanent HELD reachable by owner actions (owner Start/Stop, time, tunnels heal, vendor)
    goal = lambda s: s.intent == 'on' and s.sess == 'RUNNING' and not s.fresh and s.sup == IDLE
    allowed = lambda tags: bool(tags & {'sup', 'owner', 'time', 'vendor', 'health-good'}) and 'fault' not in tags
    good = g.ef(goal, allowed)
    stuck = [i for i in range(n) if not good[i]]
    groups = collections.Counter()
    for i in stuck:
        s = g.states[i]
        groups[(s.sess, s.code, s.jr, s.prep, s.intent, s.sup[0])] += 1
    res['ef_stuck'] = len(stuck)
    res['ef_groups'] = {str(k): v for k, v in groups.most_common(12)}
    if stuck:
        best = min(stuck)
        lines.append('EF-START (no permanent HELD) VIOLATED: %d states cannot reach "Auto running" by owner actions; groups %s'
                     % (len(stuck), dict(groups.most_common(8))))
        examples = [best]
        typical = [i for i in stuck if g.states[i].sess == 'HELD' and g.states[i].code == 'READOPT' and g.states[i].ran
                   and g.states[i].sup == IDLE and g.states[i].jr in SETTLED]
        if typical and min(typical) != best:
            examples.append(min(typical))
        for ex in examples:
            lines.append(' example (%s):' % ('shortest' if ex == best else 'running session, HELD by an outside change'))
            print_trace(g, ex, lines, 'from here no Start/Stop sequence, time or healthy tunnels reach RUNNING')
            s = g.states[ex]
            ok, _, why = start(s, cfg, manual=True)
            lines.append('  owner Start here: %s' % ('accepted' if ok else 'refused ' + why))
    else:
        lines.append('EF-START (no permanent HELD): holds')

    # --- liveness: primary dead, reserve healthy, Auto on -> eventually on the reserve (strong fairness)
    fair = lambda tags: bool(tags & {'sup', 'time', 'vendor'}) and 'fault' not in tags
    # --key-pin: towards a reserve with an accepted key, whatever the key of the primary, on a session past its Start (finding 2)
    starts = [i for i, s in enumerate(g.states) if not s.pUp and s.rUp and s.intent == 'on' and s.sess == 'RUNNING'
              and not s.fresh and s.ext == 'none' and s.sup == IDLE and s.uci != 'F' and not s.kr and (s.kv or not s.kp)]
    bottoms, sub = g.bottom_sccs(starts, fair)
    bad = [c for c in bottoms if not any(g.states[i].kern == 'R' for i in c)]
    res['liveness_failover'] = {'start_states': len(starts), 'bottom_sccs': len(bottoms), 'bad': len(bad)}
    if bad:
        c = min(bad, key=min)
        i = min(c)
        lines.append('LIVENESS failover VIOLATED: %d bottom SCCs never reach the reserve; example end state:' % len(bad))
        print_trace(g, i, lines, 'stays here forever under fairness (no owner action)')
    else:
        lines.append('LIVENESS failover (P dead, R healthy, Auto on => eventually kernel on R): holds (%d start states, %d bottom SCCs)'
                     % (len(starts), len(bottoms)))

    # --- liveness: Auto on, on the reserve, primary stably healthy, reserve healthy => eventually back on the primary (K12)
    # --key-pin: towards a primary with an accepted key, whatever the key of the reserve, the reserve healthy or not (finding 2)
    starts = [i for i, s in enumerate(g.states) if s.jr in ('COMMITTED', 'HOR') and s.kern == 'R' and s.uci == 'R' and s.pUp and s.pHold
              and (s.rUp or key_pin(cfg)) and s.intent == 'on' and s.sess == 'RUNNING' and not s.fresh and s.ext == 'none' and s.sup == IDLE
              and not s.kp and (s.kv or not s.kr)]
    bottoms, sub = g.bottom_sccs(starts, fair)
    bad = [c for c in bottoms if not any(g.states[i].kern == 'P' for i in c)]
    res['liveness_return'] = {'start_states': len(starts), 'bottom_sccs': len(bottoms), 'bad': len(bad)}
    if bad:
        c = min(bad, key=min)
        lines.append('LIVENESS return VIOLATED: %d bottom SCCs stay on the reserve with a healthy primary; example end state:' % len(bad))
        print_trace(g, min(c), lines, 'stays here forever under fairness (no owner action)')
    else:
        lines.append('LIVENESS return (on the reserve, primary stably healthy => eventually kernel on P): holds (%d start states, %d bottom SCCs)'
                     % (len(starts), len(bottoms)))

    # --- liveness: owner Stop wins (no owner action afterwards, faults excluded)
    for p_up in (True, False):
        starts = [i for i, s in enumerate(g.states) if s.stopped and s.intent == 'off' and s.pUp == p_up and s.rUp
                  and s.ext == 'none']
        bottoms, sub = g.bottom_sccs(starts, fair)
        clean = lambda s: s.sess in TERM and s.jr in SETTLED and s.sup == IDLE and not s.ho
        bad = [c for c in bottoms if not any(clean(g.states[i]) for i in c)]
        key = 'liveness_stop_primary_%s' % ('up' if p_up else 'down')
        res[key] = {'start_states': len(starts), 'bottom_sccs': len(bottoms), 'not_clean': len(bad)}
        if bad:
            ends = collections.Counter()
            for c in bad:
                s = g.states[c[0]]
                ends[(s.sess, s.code, s.jr, s.kern, s.guard, s.sup[0])] += 1
            c = min(bad, key=min)
            i = min(c)
            lines.append('LIVENESS stop-wins (primary %s): %d bottom SCCs end without a clean stop: %s; example:'
                         % ('up' if p_up else 'down', len(bad), dict(ends.most_common(6))))
            print_trace(g, i, lines, 'final (no owner action, no faults)')
        else:
            lines.append('LIVENESS stop-wins (primary %s): every fair run ends STOPPED, journal settled, guard released'
                         % ('up' if p_up else 'down'))

    # --- liveness (T4A, 07.11.2026): the owner's Stop ends a hold of an outside change (no owner action afterwards, faults
    # excluded): a HELD readopt record with a settled journal, the Stop latch standing, Auto off => eventually a terminal record
    starts = [i for i, s in enumerate(g.states) if s.stopped and s.intent == 'off' and s.sess == 'HELD' and s.code == 'READOPT'
              and s.jr in SETTLED]
    bottoms, sub = g.bottom_sccs(starts, fair)
    bad = [c for c in bottoms if not any(g.states[i].sess in TERM for i in c)]
    res['liveness_stop_hold'] = {'start_states': len(starts), 'bottom_sccs': len(bottoms), 'bad': len(bad)}
    if bad:
        c = min(bad, key=min)
        lines.append('LIVENESS stop-ends-hold VIOLATED: %d bottom SCCs keep the outside-change hold after the owner Stop; example:'
                     % len(bad))
        print_trace(g, min(c), lines, 'stays HELD forever under fairness (no owner action)')
    else:
        lines.append('LIVENESS stop-ends-hold (owner Stop on an outside-change hold => eventually STOPPED): holds (%d start states, '
                     '%d bottom SCCs)' % (len(starts), len(bottoms)))
    return res, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', choices=['alpha6', 'fix', 'fix2', 'both', 'all'], default='both')
    ap.add_argument('--faults', action='store_true', help='kernel apply/verify failures (rtp2, ROLLBACK-UNVERIFIED)')
    ap.add_argument('--server', action='store_true', help='server pick stages 2/3')
    ap.add_argument('--fast-switch', action='store_true', help='the fast end: a decision and a recheck that do not prove the primary dead')
    ap.add_argument('--no-gl', action='store_true')
    ap.add_argument('--ext', choices=['both', 'net', 'pol'], default='both',
                    help='which outside GL-panel changes the owner may make (CI bound: one kind only)')
    ap.add_argument('--no-crash', action='store_true')
    ap.add_argument('--no-power', action='store_true')
    ap.add_argument('--no-expire', action='store_true', help='no 90 s self-release of the full LAN block')
    ap.add_argument('--rebuild', action='store_true', help='the vendor rebuilds the carrying reserve (K12, finding 7)')
    ap.add_argument('--window', action='store_true', help='the uptime window of the boot hand-over and variant C as a state field (G2, G3)')
    ap.add_argument('--key-pin', choices=['directional', 'blocker'], help='server_key_pin enforce: the code, or the code before the fix (findings 1, 2)')
    ap.add_argument('--fixed', default='', help='with --variant fix: comma-separated list of K fixes assumed to be in the code (%s)' % ','.join(sorted(ALL_FIXES)))
    ap.add_argument('--json')
    ap.add_argument('--out')
    a = ap.parse_args()
    variants = {'both': ['alpha6', 'fix'], 'all': ['alpha6', 'fix', 'fix2']}.get(a.variant, [a.variant])
    results = []
    text = []
    for v in variants:
        fixed = ALL_FIXES if v == 'fix2' else frozenset(x for x in a.fixed.split(',') if x) if v == 'fix' else frozenset()
        if not fixed <= ALL_FIXES:
            ap.error('unknown fix in --fixed: %s' % ','.join(sorted(fixed - ALL_FIXES)))
        cfg = argparse.Namespace(fix=v in ('fix', 'fix2'), fixed=fixed, faults=a.faults, server=a.server, fast_switch=a.fast_switch, gl=not a.no_gl, ext=a.ext,
                                 crash=not a.no_crash, power=not a.no_power, expire=not a.no_expire, rebuild=a.rebuild, window=a.window, key_pin=a.key_pin)
        res, lines = run(cfg)
        results.append(res)
        text.extend(lines)
        text.append('')
    body = '\n'.join(text)
    print(body)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(body + '\n')
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=1, ensure_ascii=False)


if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    main()
