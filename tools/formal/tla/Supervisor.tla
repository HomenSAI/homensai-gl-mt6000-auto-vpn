----------------------------- MODULE Supervisor -----------------------------
(***************************************************************************)
(* HomenS.AI Auto VPN - pair-mode failover supervisor, TLA+ cross-check.   *)
(* HomenS.AI / Serhii Khomenko / https://homensai.com                      *)
(*                                                                         *)
(* Same abstraction as the hand-written explicit-state checker             *)
(* tools/formal/model.py (rules G1-G7, K12 and its options --fast-switch   *)
(* and --key-pin included).  Every operator below names the model.py       *)
(* function it mirrors; model.py in turn names the Lua/Python code         *)
(* (file:line of integ-a7) it abstracts.                                   *)
(*                                                                         *)
(* One state variable s (a record with the 35 fields of model.py's class  *)
(* S).  Successors are built as sets of records [l |-> label, n |-> next   *)
(* state, t |-> tags], exactly like model.py's (label, state, tags)        *)
(* lists, so that                                                          *)
(*   - transition assertions (COMMITTED-AFTER-STOP, RETURN-BEFORE-HOLD...) *)
(*     are STATE invariants over all outgoing edges of a state (what       *)
(*     model.py's transition_checks does on every expanded edge), and      *)
(*   - the actions of Next are split by tag kind (ActSup, ActFault,        *)
(*     ActOwner, ActTime, ...) so the dumped state graph carries the kind  *)
(*     needed for "Start never stuck" (AG EF) and the fair-liveness checks *)
(*     (graph_check.py; TLC has no CTL operator EF).                       *)
(*                                                                         *)
(* Fix switches: Fix (FALSE = variant alpha6 Start without 58921e2f) and   *)
(* Fixed \subseteq {K1T,K2,K3,K4,K5,K9,K11,K12,F32,T4A}, as model.py      *)
(* --fixed.  F32: an outside change of a running session is adopted by    *)
(* itself only for the network outside the pair / Wi-Fi / DHCP / DNS (a   *)
(* free choice for "net"), the pair's route policy is held; T4A: the      *)
(* owner's Stop ends an outside-change hold STOPPED (07.11.2026).         *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS Fix,      \* BOOLEAN: variant fix (TRUE) or alpha6 (FALSE)
          Fixed,    \* subset of AllFixes switched on (model.py --fixed)
          Faults,   \* kernel apply/verify failures (model.py --faults)
          Server,   \* server pick stages 2/3 (--server)
          GL,       \* outside GL-panel changes (NOT --no-gl)
          Ext,      \* "both" | "net" | "pol" (--ext)
          Crash,    \* supervisor crash (NOT --no-crash)
          Power,    \* power cut (NOT --no-power)
          Expire,   \* 90 s self-release of the full LAN block (NOT --no-expire)
          Rebuild,  \* the vendor rebuilds the carrying reserve (--rebuild)
          Window,   \* the uptime window of the boot hand-over (--window)
          FastSwitch, \* a decision and a recheck that do not prove the primary dead (--fast-switch)
          KeyPin    \* "off" | "directional" (the code) | "blocker" (the code before the fix) (--key-pin)

AllFixes == {"K1T", "K2", "K3", "K4", "K5", "K9", "K11", "K12", "F32", "T4A"}
ASSUME Fixed \subseteq AllFixes
ASSUME Fixed # {} => Fix
ASSUME Ext \in {"both", "net", "pol"}
ASSUME KeyPin \in {"off", "directional", "blocker"}
ASSUME {Fix, Faults, Server, GL, Crash, Power, Expire, Rebuild, Window, FastSwitch} \subseteq BOOLEAN

VARIABLE s

\* ------------------------------------------------------------------ sets (model.py top)
NONTERM  == {"STARTING", "RUNNING", "STOPPING", "HELD"}
TERM     == {"NONE", "STOPPED", "FAILED"}
SETTLED  == {"NONE", "RB"}
BUSY     == {"ARMED", "APPLYING", "WAIT", "COMMITTED", "HOR", "RESTORING", "RP"}
RECOVERY == {"ARMED", "APPLYING", "WAIT", "RESTORING"}
CTD      == {"COMMITTED", "HOR"}
IDLE     == <<"IDLE", 0, "">>
DOWN     == <<"DOWN", 0, "">>
BLOCKED  == <<"GIVEUP", 0, "">>
NOSC     == <<"-", "", FALSE>>
CLCTX    == {"cl-tick", "cl-rec", "cl-st"}
ToCl(c)  == CASE c = "tick" -> "cl-tick" [] c = "rec" -> "cl-rec" [] c = "st" -> "cl-st"
FromCl(c) == CASE c = "cl-tick" -> "tick" [] c = "cl-rec" -> "rec" [] c = "cl-st" -> "st"
RetTag(c) == CASE c = "ret" -> "return:ret" [] c = "native" -> "return:native"
               [] c = "cl-tick" -> "return:cl-tick" [] c = "cl-rec" -> "return:cl-rec" [] c = "cl-st" -> "return:cl-st"
RetTags  == {"return:ret", "return:native", "return:cl-tick", "return:cl-rec", "return:cl-st"}
RetCtx(t) == CASE t = "return:ret" -> "ret" [] t = "return:native" -> "native" [] t = "return:cl-tick" -> "cl-tick"
               [] t = "return:cl-rec" -> "cl-rec" [] t = "return:cl-st" -> "cl-st"
SrvTag(t) == IF t = "R" THEN "server-write:R" ELSE "server-write:P"
SrvTags  == {"server-write:R", "server-write:P"}
SrvTun(t) == IF t = "server-write:R" THEN "R" ELSE "P"
Min(a, b) == IF a < b THEN a ELSE b
K(x) == x \in Fixed
KeyOnCarrying(x) == IF x.uci = "R" THEN x.kr ELSE x.kp                            \* the channel that carries the traffic
Pin == KeyPin # "off"                                                              \* key_pin

\* ------------------------------------------------------------------ class S / INIT
Init0 == [intent |-> "off", fresh |-> FALSE, marker |-> FALSE, stopped |-> FALSE,
          sess |-> "NONE", code |-> "-", ran |-> FALSE, ho |-> FALSE,
          jr |-> "NONE", rtp |-> FALSE, fails |-> 0, fres |-> FALSE, txrev |-> FALSE, failed |-> FALSE,
          uci |-> "P", kern |-> "P", guard |-> "none",
          pUp |-> TRUE, rUp |-> TRUE, pStable |-> TRUE, pHold |-> TRUE, dwell |-> TRUE,
          ext |-> "none", prep |-> FALSE, readopt |-> 0, sup |-> IDLE,
          boot |-> FALSE, resume |-> FALSE, sc |-> NOSC, rgen |-> FALSE, kept |-> FALSE, young |-> FALSE,
          kp |-> FALSE, kr |-> FALSE, kv |-> FALSE]

Edge(l, n, t) == [l |-> l, n |-> n, t |-> t]
Sup(l, n) == {Edge(l, n, {"sup"})}

Fence(x) == [x EXCEPT !.intent = "off", !.fresh = FALSE]                          \* fence
Carrying(k) == IF k \in {"P", "R"} THEN k ELSE "none"                              \* carrying
Handover(x) == x.sess = "STOPPED" /\ x.ho /\ x.jr \in CTD
Release(x) == [x EXCEPT !.sess = "STOPPED", !.code = "-", !.ran = FALSE, !.ho = FALSE, !.readopt = @ + 1]
BootWindow(x) == x.marker /\ ~x.stopped /\ (x.fres \/ (IF Window THEN x.young ELSE x.boot))   \* boot_window

\* ------------------------------------------------------------------ owner Start / Stop (start, stop)
Res(ok, n, why) == [ok |-> ok, n |-> n, why |-> why]
StartFin(x, manual) ==
  IF x.intent = "on" THEN Res(TRUE, x, "already")
  ELSE LET y == [x EXCEPT !.intent = "on", !.fresh = TRUE]
       IN Res(TRUE, IF manual THEN [y EXCEPT !.marker = TRUE, !.stopped = FALSE] ELSE y, "none")
StartReq(x, manual) ==                                                            \* pair_auto.request
  IF x.sess \in NONTERM /\ ~(x.intent = "on" /\ ~x.fresh)
  THEN IF x.sess = "HELD" /\ x.code = "READOPT" /\ x.jr \in SETTLED /\ x.readopt < 3
       THEN StartFin(Release(x), manual)
       ELSE Res(FALSE, x, "PAIR-RECOVERY-REQUIRED")
  ELSE StartFin(x, manual)
StartPrep(x, manual) ==                                                           \* preparation_control.guard
  IF x.prep
  THEN IF x.intent = "on" THEN Res(FALSE, x, "PREPARATION-STOP-AUTO-FIRST")
       ELSE IF x.sess \notin TERM THEN Res(FALSE, x, "PREPARATION-RECOVERY-REQUIRED")
       ELSE StartReq([x EXCEPT !.prep = FALSE], manual)
  ELSE StartReq(x, manual)
Start(x, manual) ==
  IF x.sup = BLOCKED THEN Res(FALSE, x, "TRANSACTION-IN-PROGRESS")
  ELSE IF x.jr \in BUSY /\ ~Handover(x) THEN Res(FALSE, x, "TRANSACTION-IN-PROGRESS")
  ELSE LET early == manual \/ (K("K1T") /\ x.marker /\ ~x.stopped)
           rel   == Fix /\ early /\ x.sess = "HELD" /\ x.code = "READOPT" /\ x.intent # "on"
       IN IF rel
          THEN IF x.jr \in SETTLED /\ x.readopt < 3 THEN StartPrep(Release(x), manual)   \* release_for_start
               ELSE Res(FALSE, x, "PAIR-RECOVERY-REQUIRED")
          ELSE StartPrep(x, manual)

Stop(x) == [x EXCEPT !.intent = "off", !.fresh = FALSE, !.marker = FALSE, !.stopped = TRUE, !.txrev = FALSE]

\* ------------------------------------------------------------------ supervisor helpers
CanReadopt(x) == x.sess = "RUNNING" /\ x.intent = "on" /\ x.readopt < 3 /\ x.jr \in SETTLED   \* can_readopt
Readopt(x) == [Release(x) EXCEPT !.fresh = TRUE, !.sup = IDLE]                              \* readopt
TickErrorHold(x, cls) ==                                                          \* tick_error(adopt=False)
  IF x.sess = "STARTING" THEN [x EXCEPT !.sup = <<"CL", 0, "st">>]
  ELSE LET a == IF (x.sess \in TERM \/ (x.sess = "HELD" /\ ~x.ran)) /\ x.intent = "on"
                THEN [x EXCEPT !.intent = "off", !.fresh = FALSE] ELSE x
           b == IF a.sess \in NONTERM THEN [a EXCEPT !.sess = "HELD", !.code = cls] ELSE a
       IN IF b.jr \in RECOVERY THEN [Fence(b) EXCEPT !.sup = DOWN] ELSE [b EXCEPT !.sup = IDLE]
TickError(x, cls) ==                                                              \* tick_error
  IF cls = "READOPT" /\ CanReadopt(x) THEN Readopt(x) ELSE TickErrorHold(x, cls)

StPost(x) ==                                                                      \* st_post
  LET a == IF (x.sess \in TERM \/ (x.sess = "HELD" /\ ~x.ran)) /\ x.intent = "on"
           THEN [x EXCEPT !.intent = "off", !.fresh = FALSE] ELSE x
      b == IF a.sess \in NONTERM THEN [a EXCEPT !.sess = "HELD", !.code = IF a.code = "-" THEN "OTHER" ELSE a.code]
           ELSE a
  IN IF b.jr \in RECOVERY THEN [Fence(b) EXCEPT !.sup = DOWN] ELSE [b EXCEPT !.sup = IDLE]

RbDone(x, ctx) ==                                                                 \* rb_done
  CASE ctx = "fwd"    -> TickError([x EXCEPT !.sup = IDLE], "OTHER")
    [] ctx = "ret"    -> LET a == IF x.sess = "HELD" /\ x.ran THEN [x EXCEPT !.sess = "RUNNING", !.code = "-"] ELSE x
                         IN [a EXCEPT !.sup = IDLE]
    [] ctx = "native" -> [x EXCEPT !.sup = IDLE]
    [] ctx \in CLCTX  -> [x EXCEPT !.sup = <<"CL", 3, FromCl(ctx)>>]
    [] ctx = "rec"    -> [x EXCEPT !.sup = <<"REC", 3, "">>]

RbFailed(x, ctx) ==                                                               \* rb_failed
  LET a == IF ctx \in {"rec", "fwd"} THEN [x EXCEPT !.fails = Min(2, @ + 1)] ELSE x
  IN IF ctx = "rec"
     THEN IF a.fails >= 2 THEN [a EXCEPT !.sup = BLOCKED, !.guard = "vpn", !.marker = FALSE]
          ELSE [a EXCEPT !.sup = DOWN]
     ELSE IF ctx = "cl-rec"
     THEN LET b == IF a.sess \in NONTERM THEN [a EXCEPT !.sess = "HELD", !.code = "OTHER"] ELSE a
          IN [b EXCEPT !.sup = IDLE, !.resume = TRUE]
     ELSE TickError(a, "OTHER")

Abandon(x, ctx) ==                                                                \* abandon
  LET a == [x EXCEPT !.guard = "none", !.jr = "RB", !.marker = FALSE, !.stopped = TRUE, !.intent = "off",
                     !.fresh = FALSE, !.txrev = FALSE, !.sup = IDLE]
  IN IF ctx = "rec" THEN [a EXCEPT !.sup = <<"REC", 3, "">>]
     ELSE IF ctx = "cl-rec"
     THEN LET b == IF a.sess \in NONTERM THEN [a EXCEPT !.sess = "HELD", !.code = "OTHER"] ELSE a
          IN [b EXCEPT !.sup = IDLE, !.resume = TRUE]
     ELSE TickError(a, "OTHER")

FwdFail(x) == [x EXCEPT !.failed = TRUE, !.sup = <<"RB", 0, "fwd">>]              \* fwd_fail

ClFail(x, ctx, cls, useCfg) ==                                                    \* cl_fail
  LET k9 == useCfg /\ K("K9") /\ cls = "READOPT" /\ ctx \in {"rec", "tick"} /\ x.jr \in SETTLED
      a == IF k9 THEN [x EXCEPT !.guard = IF x.stopped THEN "none" ELSE "vpn"] ELSE x
      e == [a EXCEPT !.sess = "STOPPED", !.code = "-", !.ran = FALSE, !.ho = FALSE]  \* T4A end_hold_on_stop
  IN IF k9 /\ K("T4A") /\ a.stopped /\ a.intent # "on"
     THEN IF ctx = "rec" THEN [e EXCEPT !.sup = IDLE, !.resume = TRUE] ELSE [e EXCEPT !.sup = IDLE]
     ELSE IF ctx = "st" THEN StPost([a EXCEPT !.sess = "HELD", !.code = cls])
     ELSE IF ctx = "rec"
     THEN LET n == IF a.sess \in NONTERM THEN [a EXCEPT !.sess = "HELD", !.code = cls] ELSE a
          IN [n EXCEPT !.sup = IDLE, !.resume = TRUE]
     ELSE TickError(a, cls)

FresDecide(x) == ~x.failed /\ x.fails = 0 /\ ~x.fres /\ ~x.boot /\ x.marker /\ ~x.stopped /\ ~x.pUp /\ x.rUp

ServerResume(x) ==                                                                \* server_resume -> [n, extra]
  LET phase == x.sc[1]  tun == x.sc[2]  verified == x.sc[3]
  IN IF phase = "-" THEN [n |-> x, extra |-> {}]
     ELSE [n |-> [x EXCEPT !.sc = NOSC],
           extra |-> IF phase \in {"APPLYING", "CONNECTING"} /\ ~verified
                        /\ Carrying(x.kern) # "none" /\ Carrying(x.kern) # tun
                     THEN {SrvTag(tun)} ELSE {}]

ServerPending(x) ==                                                               \* server_pending
  LET phase == x.sc[1]  tun == x.sc[2]
      healthy == IF tun = "R" THEN x.rUp ELSE x.pUp
  IN CASE phase = "APPLYING" -> LET r == ServerResume(x) IN {Edge("SRVP APPLYING found", r.n, {"sup"} \cup r.extra)}
       [] phase = "CONNECTING" ->
            (IF healthy THEN Sup("SRVP CONNECTING healthy", [x EXCEPT !.sc = <<"SETTLING", tun, TRUE>>]) ELSE {})
            \cup {Edge("SRVP CONNECTING timeout", [x EXCEPT !.sc = <<"SETTLING", tun, FALSE>>], {"sup", SrvTag(tun)})}
       [] phase = "SETTLING" -> Sup("SRVP SETTLING done", [x EXCEPT !.sc = NOSC])
       [] OTHER -> {}

\* ------------------------------------------------------------------ tick (pair.tick / auto iteration)
TickMain(y) ==
  LET srv == IF Server /\ y.sess = "RUNNING" /\ y.sc[1] = "-" /\ y.kern \in {"P", "R"}
             THEN (IF y.kern = "P" /\ y.uci = "P" /\ y.jr \in SETTLED
                   THEN Sup("SRV0 change the idle reserve server", [y EXCEPT !.sc = <<"-", "R", FALSE>>, !.sup = <<"SRV", 1, "">>])
                   ELSE {})
                  \cup (IF y.kern = "R" /\ y.uci = "R" /\ y.jr = "COMMITTED"
                        THEN Sup("SRV0 change the failed primary server", [y EXCEPT !.sc = <<"-", "P", FALSE>>, !.sup = <<"SRV", 1, "">>])
                        ELSE {})
             ELSE {}
      n == IF y.sess = "HELD" /\ y.ran THEN [y EXCEPT !.sess = "RUNNING", !.code = "-"] ELSE y
  IN srv \cup
     (IF y.uci = "F" \/ y.kern = "F"                                                 \* F32: the pair's policy is held
      THEN Sup("TICK order check: PAIR-EXTERNAL-POLICY-CHANGE", IF K("F32") THEN TickErrorHold(y, "READOPT") ELSE TickError(y, "READOPT"))
      ELSE IF Pin /\ ((KeyPin = "blocker" /\ (y.kp \/ y.kr)) \/ (~y.kv /\ KeyOnCarrying(y))) THEN {}      \* blocker: every pass ends. The code: only a Start waits
      ELSE IF Pin /\ ~y.kv /\ y.jr \notin RECOVERY THEN Sup("TICK the route proved: selected_policy", [y EXCEPT !.kv = TRUE])
      ELSE IF y.jr \in CTD
      THEN IF y.rgen /\ ~K("K12") THEN {}
           ELSE IF y.rgen /\ y.rUp THEN Sup("TICK reserve rebuilt: journal proof rebound", [n EXCEPT !.rgen = FALSE])
           ELSE IF (IF y.rgen THEN y.pHold /\ y.dwell ELSE (~y.rUp /\ y.pStable) \/ (y.pHold /\ y.dwell)) /\ ~(Pin /\ y.kp)
           THEN {Edge("TICK committed decision RESTORE-PRIMARY", [n EXCEPT !.sup = <<"FIN", 0, "ret">>], {"sup", "return:ret"})}
           ELSE IF n # y THEN Sup("TICK committed decision OBSERVE", n) ELSE {}
      ELSE IF ~y.rUp
      THEN IF y.sess = "HELD" /\ y.ran /\ y.uci = "P" /\ y.kern = "P"
           THEN Sup("TICK resume_running (reserve unhealthy, still connected)", [y EXCEPT !.sess = "RUNNING", !.code = "-"])
           ELSE {}
      ELSE IF y.uci # "P" \/ y.kern # "P" THEN {}
      ELSE IF (~y.pUp \/ FastSwitch) /\ y.rUp /\ y.dwell /\ ~(Pin /\ y.kr) THEN Sup("TICK forward switch", [n EXCEPT !.sup = <<"FWD", 0, "">>])
      ELSE IF n # y THEN Sup("TICK resume_running", n) ELSE {})

Tick(x) ==                                                                        \* tick
  LET running == x.intent = "on"
      rs == IF x.resume /\ x.marker /\ ~x.stopped /\ x.intent = "off"
            THEN LET r == Start(x, FALSE)
                 IN IF r.ok THEN {Edge("RESUME Start(programmatic) accepted", [r.n EXCEPT !.resume = FALSE], {"sup", "resume"})}
                    ELSE IF r.n # x THEN Sup("RESUME Start(programmatic) refused", r.n) ELSE {}
            ELSE {}
      rest ==
        IF x.sess = "STOPPED" /\ x.ho /\ ~running THEN {}
        ELSE (IF x.kept /\ ~running THEN Sup("TICK release_kept", [x EXCEPT !.guard = "none", !.kept = FALSE]) ELSE {})
        \cup (IF K("K9") /\ x.sess = "HELD" /\ x.code = "READOPT" /\ x.jr \in SETTLED /\ ~running /\ ~x.stopped /\ x.guard \in {"vpn", "full"}
              THEN Sup("TICK outside_hold: the tunnels changed", [x EXCEPT !.guard = IF x.guard = "vpn" THEN "full" ELSE "vpn"]) ELSE {})
        \cup
        IF ~(running \/ x.sess \in NONTERM)
        THEN IF x.jr = "COMMITTED" THEN Sup("NATIVE finish_committed(TRIAL-ENDED)", [x EXCEPT !.sup = <<"FIN", 0, "native">>])
             ELSE IF x.jr = "HOR" /\ x.pStable /\ x.uci # "F"
             THEN {Edge("NATIVE HELD-ON-RESERVE operator_return", [x EXCEPT !.sup = <<"RB", 0, "native">>], {"sup", "return:native"})}
             ELSE IF x.jr = "RB" /\ x.uci = "P" /\ x.guard # "none" THEN Sup("NATIVE unguard_if_restored", [x EXCEPT !.guard = "none"])
             ELSE IF x.sess = "STOPPED" /\ x.stopped /\ x.jr \in SETTLED /\ x.guard # "none" /\ ~x.kept
             THEN Sup("TICK release_orphan_guard after the owner Stop", [x EXCEPT !.guard = "none"])
             ELSE {}
        ELSE IF ~running THEN Sup("TICK not running: cleanup", [x EXCEPT !.sup = <<"CL", 0, "tick">>])
        ELSE IF x.sess = "NONE" \/ x.fresh \/ x.sess \in TERM
        THEN IF x.sess \in NONTERM THEN Sup("TICK new request on a held session", TickError(x, "OTHER"))
             ELSE Sup("TICK begin", [x EXCEPT !.sup = <<"BEGIN", 0, "">>, !.kv = FALSE])
        ELSE IF x.ext = "net"
        THEN (IF K("F32")                                                         \* F32: readopt_class, a free choice
              THEN (IF CanReadopt(x) THEN Sup("TICK identity changed: readopt_class ADOPT", Readopt(x)) ELSE {})
                   \cup Sup("TICK identity changed: readopt_class HOLD", TickErrorHold(x, "READOPT"))
              ELSE Sup("TICK identity changed", TickError(x, "READOPT")))
        ELSE IF x.sc[1] # "-"
        THEN LET sp == ServerPending(x)
             IN IF sp \cup rs # {} THEN sp ELSE TickMain([x EXCEPT !.sc = NOSC])
        ELSE TickMain(x)
  IN rs \cup rest

\* ------------------------------------------------------------------ supervisor program (sup_steps)
FwdSteps(x, k) ==
  CASE k = 0 -> IF x.intent # "on" THEN Sup("FWD0 configure_lease: CLIENT-STOP", TickError(x, "OTHER"))
                ELSE IF ~x.rUp THEN Sup("FWD0 diagnostic: PAIR-READINESS-CHANGED", TickError(x, "OTHER"))
                ELSE IF Pin /\ x.kr THEN Sup("FWD0 attempt refused: SERVER-KEY-UNACCEPTED", TickError(x, "OTHER"))
                ELSE (IF x.pUp THEN Sup("FWD0 late recheck: PRIMARY-RECOVERED", [x EXCEPT !.sup = IDLE]) ELSE {})
                     \cup (IF ~x.pUp \/ FastSwitch      \* a recheck beside the decision does not see a primary that came back after it
                           THEN {Edge("FWD1 journal ARMED", [x EXCEPT !.jr = "ARMED", !.rtp = FALSE, !.fails = 0, !.fres = FALSE,
                                      !.txrev = TRUE, !.failed = FALSE, !.boot = FALSE, !.sup = <<"FWD", 2, "">>], {"sup", "armed"})}
                           ELSE {})
    [] k = 2 -> IF ~x.txrev \/ ~x.dwell THEN Sup("FWD2 dispatch refused", TickError([x EXCEPT !.jr = "RB"], "OTHER"))
                ELSE {Edge("FWD2 charge_attempt", [x EXCEPT !.dwell = FALSE, !.sup = <<"FWD", 3, "">>], {"sup", "charge"})}
    [] k = 3 -> Sup("FWD3 journal APPLYING", [x EXCEPT !.jr = "APPLYING", !.sup = <<"FWD", 4, "">>])
    [] k = 4 -> IF ~x.txrev THEN Sup("FWD4 stale -> rollback", FwdFail(x))
                ELSE Sup("FWD4 guard(nil): full LAN block", [x EXCEPT !.guard = "full", !.sup = <<"FWD", 5, "">>])
    [] k = 5 -> IF ~x.txrev THEN Sup("FWD5 stale -> rollback", FwdFail(x))
                ELSE {Edge("FWD5 uci reorder: reserve first", [x EXCEPT !.uci = "R", !.sup = <<"FWD", 6, "">>], {"sup", "move-to-R"})}
    [] k = 6 -> IF ~x.txrev THEN Sup("FWD6 stale -> rollback", FwdFail(x))
                ELSE Sup("FWD6 rtp_dispatched", [x EXCEPT !.rtp = TRUE, !.sup = <<"FWD", 7, "">>])
                     \cup (IF Faults THEN {Edge("FWD6 FAULT apply refused before its dispatch", FwdFail(x), {"sup", "fault"})} ELSE {})
    [] k = 7 -> IF ~x.txrev THEN Sup("FWD7 fenced dispatch refused", FwdFail(x))
                ELSE {Edge("FWD7 rtp2 dispatched", [x EXCEPT !.kern = "X", !.sup = <<"FWD", 8, "">>], {"sup", "move-to-R"})}
    [] k = 8 -> Sup("FWD8 kernel rebuilt from UCI", [x EXCEPT !.kern = x.uci, !.sup = <<"FWD", 9, "">>])
                \cup (IF Faults THEN {Edge("FWD8 FAULT rtp2 failed", FwdFail(x), {"sup", "fault"})} ELSE {})
    [] k = 9 -> IF ~x.txrev THEN Sup("FWD9 verify/guard: stale", FwdFail(x))
                ELSE IF x.kern # "R" \/ x.uci # "R" THEN Sup("FWD9 verify: KERNEL-POLICY-UNVERIFIED", FwdFail(x))
                ELSE Sup("FWD9 guard(devices): VPN-only", [x EXCEPT !.guard = "vpn", !.sup = <<"FWD", 10, "">>])
    [] k = 10 -> Sup("FWD10 journal WAIT-CLIENT", [x EXCEPT !.jr = "WAIT", !.sup = <<"FWD", 11, "">>])
    [] k = 11 -> IF ~x.txrev \/ x.stopped THEN Sup("FWD11 CLIENT-STOP / stale -> rollback", FwdFail(x))
                 ELSE IF x.rUp /\ K("K5")
                 THEN {Edge("FWD11 K5: COMMITTED under the control lock", [x EXCEPT !.jr = "COMMITTED", !.sup = IDLE], {"sup", "committed"})}
                 ELSE IF x.rUp THEN Sup("FWD11 probes confirm; revision passed", [x EXCEPT !.sup = <<"FWD", 12, "">>])
                 ELSE Sup("FWD11 CLIENT-CONFIRMATION-TIMEOUT", FwdFail(x))
    [] k = 12 -> {Edge("FWD12 journal COMMITTED (not under the lock)", [x EXCEPT !.jr = "COMMITTED", !.sup = IDLE], {"sup", "committed"})}

FresFail(x) == [x EXCEPT !.failed = TRUE, !.sup = <<"RB", 0, "rec">>]
FresSteps(x, k) ==
  CASE k = 0 -> LET forward == x.uci = "R" /\ x.kern = "R"
                    untouched == x.kern = "P" /\ x.uci \in {"P", "R"}
                IN IF x.stopped \/ ~(forward \/ untouched) \/ x.sess \notin {"RUNNING", "HELD", "STOPPING"}
                      \/ (Pin /\ untouched /\ ~forward /\ x.kr)                   \* a kernel still on the primary: a new move
                   THEN Sup("FRES0 refused -> rollback", [x EXCEPT !.sup = <<"RB", 0, "rec">>])
                   ELSE Sup("FRES0 forward_resumed", [x EXCEPT !.fres = TRUE, !.txrev = TRUE,
                                                               !.sup = <<"FRES", IF untouched THEN 1 ELSE 4, "">>])
    [] k = 1 -> IF x.stopped \/ ~x.txrev THEN Sup("FRES1 CLIENT-STOP -> rollback", FresFail(x))
                ELSE {Edge("FRES1 guard(nil) + uci reserve", [x EXCEPT !.guard = "full", !.uci = "R", !.sup = <<"FRES", 2, "">>], {"sup", "move-to-R"})}
    [] k = 2 -> IF x.stopped \/ ~x.txrev THEN Sup("FRES2 fenced dispatch refused", FresFail(x))
                ELSE {Edge("FRES2 rtp dispatched", [x EXCEPT !.rtp = TRUE, !.kern = "X", !.sup = <<"FRES", 3, "">>], {"sup", "move-to-R"})}
    [] k = 3 -> Sup("FRES3 kernel rebuilt from UCI", [x EXCEPT !.kern = x.uci, !.sup = <<"FRES", 4, "">>])
                \cup (IF Faults THEN {Edge("FRES3 FAULT kernel unverified", FresFail(x), {"sup", "fault"})} ELSE {})
    [] k = 4 -> IF x.kern # "R" \/ x.uci # "R" THEN Sup("FRES4 kernel not target", FresFail(x))
                ELSE Sup("FRES4 guard VPN-only + WAIT-CLIENT", [x EXCEPT !.guard = "vpn", !.jr = "WAIT", !.sup = <<"FRES", 5, "">>])
    [] k = 5 -> IF x.stopped \/ ~x.txrev THEN Sup("FRES5 CLIENT-STOP -> rollback", FresFail(x))
                ELSE IF x.rUp THEN {Edge("FRES5 COMMITTED SUPERVISOR-FORWARD-RESUMED", [x EXCEPT !.jr = "COMMITTED", !.sup = <<"REC", 3, "">>], {"sup", "committed"})}
                ELSE Sup("FRES5 CLIENT-CONFIRMATION-TIMEOUT", FresFail(x))

RbSteps(x, k, ctx) ==
  CASE k = 0 -> IF x.jr = "ARMED" /\ ~x.rtp /\ x.uci = "P" THEN Sup("RB0 ARMED, nothing written", RbDone([x EXCEPT !.jr = "RB"], ctx))
                ELSE IF ~x.rtp /\ x.jr \in RECOVERY
                THEN IF x.uci = "F" THEN {Edge("RB-A order foreign: abandon", Abandon(x, ctx), {"sup", "abandon"})}
                     ELSE Sup("RB-A undo UCI order", [x EXCEPT !.uci = "P", !.sup = <<"RB", 1, ctx>>])
                ELSE Sup("RB-B journal RESTORING", [x EXCEPT !.jr = "RESTORING", !.sup = <<"RB", 2, ctx>>])
                     \cup (IF Faults /\ x.jr = "RESTORING" THEN {Edge("RB-B FAULT KERNEL-POLICY-UNVERIFIED before any write", RbFailed(x, ctx), {"sup", "fault"})} ELSE {})
    [] k = 1 -> IF x.kern # "P"
                THEN {Edge("RB-A vendor reload: kernel follows", RbDone([x EXCEPT !.kern = "P", !.guard = "vpn", !.jr = "RB"], ctx), {"sup", "move-to-P"})}
                     \cup (IF Faults THEN {Edge("RB-A FAULT reload failed", RbDone([x EXCEPT !.guard = "vpn", !.jr = "RB"], ctx), {"sup", "fault"})} ELSE {})
                ELSE Sup("RB-A guard(devices) + ROLLED-BACK", RbDone([x EXCEPT !.guard = "vpn", !.jr = "RB"], ctx))
    [] k = 2 -> Sup("RB-B guard(): full LAN block", [x EXCEPT !.guard = "full", !.sup = <<"RB", 3, ctx>>])
    [] k = 3 -> IF x.uci = "F" THEN {Edge("RB-B order foreign: abandon", Abandon(x, ctx), {"sup", "abandon"})}
                ELSE Sup("RB-B uci reorder: primary first", [x EXCEPT !.uci = "P", !.sup = <<"RB", 4, ctx>>])
    [] k = 4 -> {Edge("RB-B kernel apply dispatched", [x EXCEPT !.kern = "X", !.sup = <<"RB", 5, ctx>>], {"sup", "move-to-P"})}
                \cup (IF Faults THEN {Edge("RB-B FAULT apply failed: the full block stays", RbFailed(x, ctx), {"sup", "fault"})} ELSE {})
    [] k = 5 -> Sup("RB-B kernel rebuilt from UCI", [x EXCEPT !.kern = x.uci, !.sup = <<"RB", 6, ctx>>])
                \cup (IF Faults THEN {Edge("RB-B FAULT ROLLBACK-UNVERIFIED", RbFailed([x EXCEPT !.guard = "vpn"], ctx), {"sup", "fault"})} ELSE {})
    [] k = 6 -> IF x.kern # "P" \/ x.uci # "P" THEN Sup("RB-B verify: ROLLBACK-UNVERIFIED", RbFailed([x EXCEPT !.guard = "vpn"], ctx))
                ELSE IF KeyPin = "blocker" /\ (x.kp \/ x.kr)                     \* finding 1: before the fix the key failed the proof
                THEN Sup("RB-B verify: SERVER-KEY-UNACCEPTED fails the proof", RbFailed([x EXCEPT !.guard = "vpn"], ctx))
                ELSE Sup("RB-B journal ROLLED-BACK + guard(devices)", RbDone([x EXCEPT !.jr = "RB", !.guard = "vpn"], ctx))

FinSteps(x, ctx) ==                                                               \* finish_committed
  LET holdOk == IF K("K2") /\ ctx \in CLCTX /\ ~x.stopped /\ x.rUp THEN x.pHold ELSE x.pStable
      n0 == [x EXCEPT !.guard = "vpn", !.jr = "HOR"]
      n1 == [n0 EXCEPT !.sess = "HELD"]
      held == IF ctx \in CLCTX
              THEN IF ctx = "cl-st" THEN StPost(n1)
                   ELSE IF ctx = "cl-rec" THEN [n1 EXCEPT !.code = "OTHER", !.sup = IDLE, !.resume = TRUE]
                   ELSE [n1 EXCEPT !.sup = IDLE]
              ELSE [n0 EXCEPT !.sup = IDLE]
  IN IF x.uci = "F" THEN {Edge("FIN order foreign: abandon", Abandon(x, ctx), {"sup", "abandon"})}
     ELSE IF x.uci # "P" /\ ~holdOk THEN Sup("FIN primary not ready: HELD-ON-RESERVE", held)
     ELSE {Edge("FIN return to the primary", [x EXCEPT !.sup = <<"RB", 0, ctx>>],
                IF ctx = "ret" THEN {"sup"} ELSE {"sup", RetTag(ctx)})}

ClSteps(x, k, ctx) ==                                                             \* pair.cleanup
  CASE k = 0 -> IF K("K11") /\ x.sess \in TERM
                THEN Sup("CL0 superseded by the Start hand-over (K11)",
                         IF ctx = "rec" THEN [x EXCEPT !.sup = IDLE, !.resume = TRUE]
                         ELSE IF ctx = "st" THEN StPost(x) ELSE [x EXCEPT !.sup = IDLE])
                ELSE LET r == ServerResume(x)
                     IN {Edge("CL0 session STOPPING", [r.n EXCEPT !.sess = "STOPPING", !.sup = <<"CL", 1, ctx>>], {"sup"} \cup r.extra)}
    [] k = 1 -> IF x.jr \in RECOVERY THEN Sup("CL1 journal mid-switch", ClFail(x, ctx, "OTHER", FALSE))
                ELSE IF x.jr \in CTD
                THEN (IF BootWindow(x) /\ ~(IF K("K2") THEN x.pHold ELSE x.pStable)
                        /\ x.kern = "R" /\ x.uci = "R" /\ x.rUp
                      THEN LET n == [x EXCEPT !.guard = "vpn", !.sess = "STOPPED", !.ho = TRUE, !.sup = IDLE]
                           IN Sup("CL1 boot handover on the reserve",
                                  IF ctx = "rec" THEN [n EXCEPT !.resume = TRUE] ELSE IF ctx = "st" THEN StPost(n) ELSE n)
                      ELSE {})
                     \cup Sup("CL1 finish_committed(PAIR-STOPPED)", [x EXCEPT !.sup = <<"FIN", 0, ToCl(ctx)>>])
                ELSE Sup("CL1 journal settled", [x EXCEPT !.sup = <<"CL", 3, ctx>>])
    [] k = 3 -> IF x.uci # "P" THEN Sup("CL3 order changed: PAIR-EXTERNAL-POLICY-CHANGE", ClFail(x, ctx, "READOPT", TRUE))
                ELSE LET fin(n) == IF ctx = "st" THEN StPost(n) ELSE IF ctx = "rec" THEN [n EXCEPT !.sup = IDLE, !.resume = TRUE]
                                   ELSE [n EXCEPT !.sup = IDLE]
                         cl5 == IF x.ext = "net" THEN Sup("CL5 identity changed: PAIR-EXTERNAL-NETWORK-CHANGE", ClFail(x, ctx, "READOPT", TRUE)) ELSE {}
                     IN IF x.ext = "net" /\ x.code = "READOPT" /\ ~x.stopped THEN cl5   \* pair.outside_recheck (finding 5)
                        ELSE cl5                                                        \* G5: a session owning no client ends STOPPED
                             \cup Sup("CL6 clients down, unguard, STOPPED",
                                      fin([x EXCEPT !.guard = "none", !.sess = "STOPPED", !.code = "-", !.ran = FALSE, !.ho = FALSE]))
                             \cup (IF x.ext # "net" /\ BootWindow(x)
                                   THEN Sup("CL6 boot_keep: clients kept for the Start",
                                            fin([x EXCEPT !.sess = "STOPPED", !.code = "-", !.ran = FALSE, !.ho = FALSE, !.kept = TRUE]))
                                   ELSE {})

BeginSteps(x, k, ctx) ==                                                          \* pair.begin
  CASE k = 0 -> LET ho == Handover(x)
                    live == IF x.uci = "F" THEN "P" ELSE x.uci
                    kl == IF x.kern = "F" THEN "P" ELSE x.kern
                    n == [x EXCEPT !.ext = "none", !.uci = live, !.kern = kl]
                    c == IF ho THEN "ho" ELSE IF K("K4") /\ x.guard = "vpn" /\ x.jr \in SETTLED THEN "oh" ELSE ""
                IN IF x.prep THEN Sup("BEGIN0 preflight: PAIR-PROFILES-UNVERIFIED", TickError(x, "OTHER"))
                   ELSE IF kl # live THEN Sup("BEGIN0 preflight: kernel does not match", TickError(x, "OTHER"))
                   ELSE IF KeyPin = "directional" /\ KeyOnCarrying(x)              \* the Start is refused, nothing taken (pair.begin)
                   THEN Sup("BEGIN0 SERVER-KEY-UNACCEPTED", TickError(x, "OTHER"))
                   ELSE IF ho /\ ~(x.kern = "R" /\ x.uci = "R" /\ x.rUp)
                   THEN Sup("BEGIN0 handover not adoptable: BOOT-RESERVE-UNVERIFIED",
                            [x EXCEPT !.sess = "HELD", !.ho = FALSE, !.intent = "off", !.fresh = FALSE,
                                      !.code = "OTHER", !.sup = IDLE])
                   ELSE {Edge("BEGIN1 session STARTING", [n EXCEPT !.sess = "STARTING", !.code = "-", !.ran = FALSE, !.ho = FALSE, !.kept = FALSE,
                                                                   !.fresh = FALSE, !.sup = <<"BEGIN", 2, c>>], {"sup", "begin"})}
    [] k = 2 -> IF K("K4") /\ ctx \in {"ho", "oh"}
                THEN Sup("BEGIN2 K4: standing VPN-only guard kept", [x EXCEPT !.guard = "vpn", !.sup = <<"BEGIN", 3, ctx>>])
                ELSE Sup("BEGIN2 guard(): full LAN block while clients start", [x EXCEPT !.guard = "full", !.sup = <<"BEGIN", 3, ctx>>])
    [] k = 3 -> IF x.intent # "on" THEN Sup("BEGIN3 require_running: CLIENT-STOP", TickError(x, "OTHER"))
                ELSE Sup("BEGIN4 guard(devices) + RUNNING", [x EXCEPT !.guard = "vpn", !.sess = "RUNNING", !.ran = TRUE,
                                                                      !.sup = IF ctx = "ho" THEN <<"BEGIN", 4, ctx>> ELSE IDLE])
    [] k = 4 -> Sup("BEGIN5 adopt handed-over journal: COMMITTED", [x EXCEPT !.jr = "COMMITTED", !.ho = FALSE, !.txrev = TRUE, !.kv = Pin, !.sup = IDLE])

RecSteps(x, k) ==                                                                 \* auto.recover
  CASE k = 1 -> LET r == ServerResume(x)  n == r.n  ex == r.extra
                IN IF n.jr \in RECOVERY
                   THEN IF n.fails >= 2 THEN {Edge("REC2 give_up ROLLBACK-GIVEN-UP", [n EXCEPT !.sup = BLOCKED, !.guard = "vpn", !.marker = FALSE], {"sup"} \cup ex)}
                        ELSE IF n.jr \in {"APPLYING", "WAIT"} /\ FresDecide(n)
                        THEN {Edge("REC2 forward_resume accepted", [n EXCEPT !.sup = <<"FRES", 0, "">>], {"sup"} \cup ex)}
                        ELSE {Edge("REC2 boot_rollback SUPERVISOR-RECOVERY", [n EXCEPT !.sup = <<"RB", 0, "rec">>], {"sup", "undo-forward"} \cup ex)}
                   ELSE IF n.jr = "HOR" /\ n.uci = "R" /\ K("K3")
                   THEN {Edge("REC2 K3: HELD-ON-RESERVE guard(devices)", [n EXCEPT !.guard = "vpn", !.sup = <<"REC", 3, "">>], {"sup"} \cup ex)}
                   ELSE IF n.jr = "COMMITTED"
                   THEN IF n.uci # "R" THEN {Edge("REC2 COMMITTED but order changed: abandon", Abandon(n, "rec"), {"sup", "abandon"} \cup ex)}
                        ELSE {Edge("REC2 COMMITTED: guard(devices)", [n EXCEPT !.guard = "vpn", !.sup = <<"REC", 3, "">>], {"sup"} \cup ex)}
                   ELSE {Edge("REC2 journal settled", [n EXCEPT !.sup = <<"REC", 3, "">>], {"sup"} \cup ex)}
    [] k = 3 -> IF x.sess \in NONTERM THEN Sup("REC3 pair.recover -> cleanup", [x EXCEPT !.sup = <<"CL", 0, "rec">>])
                ELSE Sup("REC4 recovery finished", [x EXCEPT !.sup = IDLE, !.resume = TRUE])

SrvSteps(x, k) ==
  LET tun == x.sc[2]
  IN CASE k = 1 -> Sup("SRV1 server_change APPLYING saved", [x EXCEPT !.sc = <<"APPLYING", tun, FALSE>>, !.sup = <<"SRV", 2, "">>])
       [] k = 2 -> {Edge("SRV2 server_apply", [x EXCEPT !.sc = <<"CONNECTING", tun, FALSE>>, !.sup = IDLE], {"sup", SrvTag(tun)})}

SupSteps(x) ==                                                                    \* sup_steps
  LET proc == x.sup[1]  k == x.sup[2]  ctx == x.sup[3]
  IN CASE proc = "GIVEUP" -> {}
       [] proc = "DOWN"   -> Sup("REC0 supervisor start: revision rotated, intent fenced",
                                 [Fence(x) EXCEPT !.txrev = FALSE, !.resume = FALSE, !.sup = <<"REC", 1, "">>])
       [] proc = "IDLE"   -> Tick(x)
       [] proc = "FWD"    -> FwdSteps(x, k)
       [] proc = "FRES"   -> FresSteps(x, k)
       [] proc = "RB"     -> RbSteps(x, k, ctx)
       [] proc = "FIN"    -> FinSteps(x, ctx)
       [] proc = "CL"     -> ClSteps(x, k, ctx)
       [] proc = "BEGIN"  -> BeginSteps(x, k, ctx)
       [] proc = "REC"    -> RecSteps(x, k)
       [] proc = "SRV"    -> SrvSteps(x, k)

\* ------------------------------------------------------------------ environment and owner (env_steps, owner_steps)
EnvSteps(x) ==
  LET E1(l, n, kind) == {Edge(l, n, {kind})} IN
  (IF x.pUp THEN E1("ENV primary tunnel fails", [x EXCEPT !.pUp = FALSE, !.pStable = FALSE, !.pHold = FALSE], "health-bad")
   ELSE E1("ENV primary tunnel recovers", [x EXCEPT !.pUp = TRUE], "health-good"))
  \cup (IF x.rUp THEN E1("ENV reserve tunnel fails", [x EXCEPT !.rUp = FALSE], "health-bad")
        ELSE E1("ENV reserve tunnel recovers", [x EXCEPT !.rUp = TRUE], "health-good"))
  \cup (IF x.pUp /\ ~x.pStable THEN E1("TIME primary stable", [x EXCEPT !.pStable = TRUE], "time") ELSE {})
  \cup (IF x.pStable /\ ~x.pHold THEN E1("TIME damped return_hold", [x EXCEPT !.pHold = TRUE], "time") ELSE {})
  \cup (IF ~x.dwell THEN E1("TIME dwell", [x EXCEPT !.dwell = TRUE], "time") ELSE {})
  \cup (IF x.readopt > 0 THEN E1("TIME readopt entry ages out", [x EXCEPT !.readopt = @ - 1], "time") ELSE {})
  \cup (IF x.resume THEN E1("TIME boot-resume window over", [x EXCEPT !.resume = FALSE], "time") ELSE {})
  \cup (IF x.young THEN E1("TIME uptime over BOOT_KEEP_UPTIME", [x EXCEPT !.young = FALSE], "time") ELSE {})
  \cup (IF x.sess = "STOPPED" /\ x.ho /\ x.intent = "off"
        THEN E1("TIME release_handover -> HELD", [x EXCEPT !.sess = "HELD", !.ho = FALSE], "time") ELSE {})
  \cup (IF x.kern = "X" THEN E1("VENDOR rebuild finished", [x EXCEPT !.kern = x.uci], "vendor") ELSE {})
  \cup (IF Rebuild /\ x.jr \in CTD /\ x.kern = "R" /\ ~x.rgen
        THEN E1("VENDOR rebuilt the carrying reserve (K12)", [x EXCEPT !.rgen = TRUE], "rebuild") ELSE {})
  \cup (IF Expire /\ x.guard = "full" /\ (x.sup[1] = "DOWN" \/ (x.sup[1] = "BEGIN" /\ x.sup[2] = 3 /\ ~K("K4")))
        THEN E1("TIME full LAN block self-released after 90 s", [x EXCEPT !.guard = "none"], "expire") ELSE {})
  \cup (IF Pin /\ x.pUp /\ ~x.kp THEN E1("ENV the primary server key changes", [x EXCEPT !.kp = TRUE], "key") ELSE {})
  \cup (IF Pin /\ x.rUp /\ ~x.kr THEN E1("ENV the reserve server key changes", [x EXCEPT !.kr = TRUE], "key") ELSE {})
  \cup (IF x.ext = "none" /\ GL
        THEN (IF Ext \in {"both", "net"} THEN E1("OWNER changes VPN clients in GL", [x EXCEPT !.ext = "net", !.prep = TRUE], "gl") ELSE {})
             \cup (IF Ext \in {"both", "pol"}
                   THEN E1("OWNER changes route policy in GL", [x EXCEPT !.ext = "pol", !.uci = "F", !.kern = "F", !.prep = TRUE], "gl")
                   ELSE {})
        ELSE {})
  \cup (IF x.sup[1] \notin {"DOWN", "GIVEUP"} /\ Crash THEN E1("CRASH supervisor killed", [x EXCEPT !.sup = DOWN], "crash") ELSE {})
  \cup (IF Power /\ x.sup # BLOCKED
        THEN E1("POWER cut", [x EXCEPT !.sup = DOWN, !.guard = "none", !.intent = "off", !.fresh = FALSE, !.txrev = FALSE,
                                       !.readopt = 0, !.kern = "X",
                                       !.boot = IF x.jr \in RECOVERY \/ x.jr \in CTD THEN TRUE ELSE x.boot,
                                       !.resume = x.marker, !.young = Window, !.pStable = FALSE, !.pHold = FALSE], "power")
        ELSE {})

OwnerSteps(x) ==
  LET r == Start(x, TRUE) IN
  (IF r.ok /\ r.why = "none" THEN {Edge("OWNER Start", r.n, {"owner"})}
   ELSE IF ~r.ok /\ r.n # x THEN {Edge("OWNER Start refused (after a hand-over)", r.n, {"owner"})}
   ELSE {})
  \cup (IF ~x.stopped \/ x.intent = "on" \/ x.marker THEN {Edge("OWNER Stop", Stop(x), {"owner", "stop"})} ELSE {})
  \cup (IF x.kp \/ x.kr THEN {Edge("OWNER accepts the server keys", [x EXCEPT !.kp = FALSE, !.kr = FALSE], {"owner"})} ELSE {})

\* successors: the stale proof lives in the journal of this switch, it ends with the switch
Rg(x, n) == IF x.rgen /\ n.jr \notin {"COMMITTED", "HOR", "RESTORING"} THEN [n EXCEPT !.rgen = FALSE] ELSE n

Succ(x) == SupSteps(x) \cup EnvSteps(x) \cup OwnerSteps(x)

\* ------------------------------------------------------------------ spec
Init == s = Init0

\* the actions are split by tag kind so the dumped graph carries it (graph_check.py); written out (no helper
\* operator) because TLC names a dumped edge after the innermost operator that defines the action
ActSup        == \E e \in SupSteps(s) : "fault" \notin e.t /\ s' = Rg(s, e.n)
ActFault      == \E e \in SupSteps(s) : "fault" \in e.t /\ s' = Rg(s, e.n)
ActOwner      == \E e \in OwnerSteps(s) : s' = Rg(s, e.n)
ActHealthBad  == \E e \in EnvSteps(s) : "health-bad" \in e.t /\ s' = Rg(s, e.n)
ActHealthGood == \E e \in EnvSteps(s) : "health-good" \in e.t /\ s' = Rg(s, e.n)
ActTime       == \E e \in EnvSteps(s) : "time" \in e.t /\ s' = Rg(s, e.n)
ActVendor     == \E e \in EnvSteps(s) : "vendor" \in e.t /\ s' = Rg(s, e.n)
ActExpire     == \E e \in EnvSteps(s) : "expire" \in e.t /\ s' = Rg(s, e.n)
ActGL         == \E e \in EnvSteps(s) : "gl" \in e.t /\ s' = Rg(s, e.n)
ActCrash      == \E e \in EnvSteps(s) : "crash" \in e.t /\ s' = Rg(s, e.n)
ActPower      == \E e \in EnvSteps(s) : "power" \in e.t /\ s' = Rg(s, e.n)
ActRebuild    == \E e \in EnvSteps(s) : "rebuild" \in e.t /\ s' = Rg(s, e.n)
ActKey        == \E e \in EnvSteps(s) : "key" \in e.t /\ s' = Rg(s, e.n)

Next == ActSup \/ ActFault \/ ActOwner \/ ActHealthBad \/ ActHealthGood \/ ActTime \/ ActVendor
        \/ ActExpire \/ ActGL \/ ActCrash \/ ActPower \/ ActRebuild \/ ActKey

Spec == Init /\ [][Next]_s

\* ------------------------------------------------------------------ properties (leak, family, consistent, transition_checks)
TypeOK ==
  /\ s.intent \in {"off", "on"} /\ s.sess \in NONTERM \cup TERM /\ s.code \in {"-", "READOPT", "OTHER"}
  /\ s.jr \in {"NONE", "RB", "HOR", "ARMED", "APPLYING", "WAIT", "COMMITTED", "RESTORING", "RP"}
  /\ s.fails \in 0..2 /\ s.uci \in {"P", "R", "F"} /\ s.kern \in {"P", "R", "X", "F"}
  /\ s.guard \in {"none", "full", "vpn"} /\ s.ext \in {"none", "net", "pol"} /\ s.readopt \in 0..3
  /\ {s.kp, s.kr, s.kv} \subseteq BOOLEAN

Owned(x) == x.sess \in NONTERM \/ x.jr \in RECOVERY \/ x.jr \in CTD
InRecovery(x) == x.sup[1] \in {"DOWN", "REC", "FRES"} \/ x.sup[3] \in {"rec", "cl-rec"}

LeakKind(x) ==                                                                    \* leak
  IF ~Owned(x) \/ x.guard # "none" THEN ""
  ELSE IF x.kern = "F" \/ x.uci = "F" THEN ""
  ELSE IF x.stopped /\ x.jr \in SETTLED /\ x.kern = "P" /\ x.uci = "P" THEN ""
  ELSE IF ~(x.kern = "X" \/ (x.kern = "P" /\ ~x.pUp) \/ (x.kern = "R" /\ ~x.rUp)) THEN ""
  ELSE IF InRecovery(x) THEN "recovery-window"
  ELSE IF x.sess = "STARTING" THEN "begin-window"
  ELSE "running"

Family(x) ==                                                                      \* family (canonical CI signature)
  LET kind == LeakKind(x) IN
  IF kind = "" THEN ""
  ELSE IF kind = "begin-window" /\ x.sup[1] = "BEGIN" /\ x.sup[2] = 2 THEN "begin-instant"
  ELSE IF x.stopped /\ x.jr \in SETTLED /\ x.uci = "P" THEN "after-the-owner-stop"
  ELSE IF kind = "recovery-window" THEN "recovery-window"
  ELSE IF x.jr = "HOR" /\ x.uci = "R" THEN "k3-held-on-reserve-without-guard"
  ELSE IF x.sess = "STARTING" \/ x.sup[1] = "BEGIN" \/ x.sup[3] = "st" THEN "k4-begin-block-lapsed"
  ELSE IF (x.readopt > 0 \/ (x.intent = "on" /\ x.fresh)) /\ x.sess \in {"STOPPING", "HELD"} /\ x.code # "READOPT" /\ x.jr \in SETTLED
       THEN "k11-start-hand-over"
  ELSE IF x.sess = "HELD" /\ x.code = "READOPT" THEN "k9-held-by-an-outside-change-without-guard"
  ELSE "other-" \o kind

Consistent(x) ==
  IF x.sup # IDLE \/ x.uci = "F" \/ x.kern = "F" THEN TRUE
  ELSE IF x.jr \in SETTLED THEN x.uci = "P" /\ x.kern \in {"P", "X"}
  ELSE IF x.jr \in CTD THEN x.uci = "R" /\ x.kern \in {"R", "X"}
  ELSE FALSE

TransChecks(x, tags) ==                                                           \* transition_checks
  (IF "armed" \in tags /\ x.jr \notin SETTLED THEN {"TWO-TRANSACTIONS"} ELSE {})
  \cup (IF ("armed" \in tags /\ x.kr) \/ ("return:ret" \in tags /\ x.kp) THEN {"MOVE-ONTO-UNACCEPTED-KEY"} ELSE {})
  \cup (IF "begin" \in tags /\ x.jr \in RECOVERY THEN {"BEGIN-DURING-TRANSACTION"} ELSE {})
  \cup (IF "begin" \in tags /\ KeyOnCarrying(x) THEN {"BEGIN-WITH-UNACCEPTED-KEY"} ELSE {})
  \cup (IF "move-to-R" \in tags /\ x.stopped THEN {"SWITCH-AFTER-STOP"} ELSE {})
  \cup (IF "committed" \in tags /\ x.stopped THEN {"COMMITTED-AFTER-STOP"} ELSE {})
  \cup UNION {(IF Carrying(x.kern) = "none" \/ Carrying(x.kern) = SrvTun(t) THEN {"SERVER-WRITE-ON-CARRYING"} ELSE {})
              \cup (IF x.jr \in RECOVERY THEN {"SERVER-WRITE-DURING-TRANSACTION"} ELSE {}) : t \in tags \cap SrvTags}
  \cup {"RETURN-BEFORE-HOLD:" \o RetCtx(t) : t \in {u \in tags \cap RetTags : x.rUp /\ x.marker /\ ~x.stopped /\ ~x.pHold}}
  \cup (IF "undo-forward" \in tags /\ x.jr \in {"APPLYING", "WAIT"} /\ ~x.pUp /\ x.rUp /\ x.marker /\ ~x.stopped
        THEN {"ROLLBACK-ONTO-DEAD-PRIMARY:" \o (IF x.boot THEN "power-cut" ELSE "crash")} ELSE {})

ViolationsOut(x) == UNION {TransChecks(x, e.t) : e \in Succ(x)}

\* ---- accepted by design (tools/formal/expected.json "accepted"; profile-scoped ones are listed per cfg)
AcceptedFamilies == {"begin-instant", "recovery-window", "after-the-owner-stop"}
AcceptedTransitions == {"ROLLBACK-ONTO-DEAD-PRIMARY:crash", "ROLLBACK-ONTO-DEAD-PRIMARY:power-cut"}

\* P1: no LAN traffic outside the VPN (guard present whenever the route is ours and unsafe), except accepted windows
NoUnacceptedLeak == Family(s) \in AcceptedFamilies \cup {""}
\* one invariant per counterexample class, for one shortest TLC trace each
NoLeakK3  == Family(s) # "k3-held-on-reserve-without-guard"
NoLeakK4  == Family(s) # "k4-begin-block-lapsed"
NoLeakOtherRunning == Family(s) # "other-running"
NoLeakK9  == Family(s) # "k9-held-by-an-outside-change-without-guard"
NoLeakK11 == Family(s) # "k11-start-hand-over"
\* P3/K5: no COMMITTED after the owner's Stop;  K2/P8: no return to the primary before the damped hold
NoCommittedAfterStop == "COMMITTED-AFTER-STOP" \notin ViolationsOut(s)
NoReturnBeforeHold   == \A t \in ViolationsOut(s) : t \notin {"RETURN-BEFORE-HOLD:" \o c : c \in {"ret", "native", "cl-tick", "cl-rec", "cl-st"}}
NoUnacceptedTransition == ViolationsOut(s) \subseteq AcceptedTransitions
JournalConsistent == Consistent(s)

\* ---- census: one line per leak state / violating edge / supervisor step, aggregated by tlc_check.py (always TRUE; TLC
\*      evaluates an invariant once per distinct new state, so the line counts equal model.py's per-state counts).
\*      CENSUS-STEP counts each supervisor edge by its program counter before and after: an edge that moves to another
\*      state which is reachable anyway changes no count of states or transitions, but it changes these pairs.
PcKey(p) == p[1] \o ":" \o ToString(p[2]) \o ":" \o p[3]
Census ==
  LET sup == SupSteps(s) IN                                                       \* evaluated once: this runs for every state
  /\ (Family(s) = "" \/ PrintT(<<"CENSUS-LEAK", Family(s)>>))
  /\ (Consistent(s) \/ PrintT(<<"CENSUS-INV", "INCONSISTENT">>))
  /\ \A e \in sup \cup EnvSteps(s) \cup OwnerSteps(s) : \A v \in TransChecks(s, e.t) : PrintT(<<"CENSUS-TRANS", v>>)
  /\ \A e \in sup : PrintT(<<"CENSUS-STEP", PcKey(s.sup) \o ">" \o PcKey(e.n.sup)>>)
=============================================================================
