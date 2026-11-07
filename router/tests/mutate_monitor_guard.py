"""Mutation check of the monitor loop guard and of the codes of a long VENDOR-WORKER-BUSY: every mutant must make its suite fail. Each mutant is
applied in place, the matching suite runs, the file is restored (also on error). Run on a copy (docker), never on the router:
  python router/tests/mutate_monitor_guard.py [lua|py|js] [substring]   -> one line per mutant, exit 1 when one survives
Not listed (equivalent): AttributeError in pair_auto.busy_fields: getattr with a default reaches no such error; the `finished` flag of monitor_io.datagram's finish(): after the first finish the descriptor and the
deadline timer are gone, so nothing calls it twice; it only keeps a double uloop delete impossible if that ever changes.
"""
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
REPO=HERE.parents[1]
GUARD=[['lua5.1','lua/test_monitor_guard.lua'],['lua5.1','lua/test_monitor_io.lua']]
LOCK=[['lua5.1','lua/test_vendor_retry.lua']]
PY=[[sys.executable,'-m','unittest','test_vendor_retry.LongVendorBusy','test_vendor_retry.VendorNotice','test_mt3000_manual_platform','-q']]
JS=[['python3','router/build_sidebar_ui.py'],['node','router/tests/test_auto_state_table_ui.js'],['node','router/tests/test_auto_signal_ui.js']]
LAZY=[['python3','router/build_sidebar_ui.py'],['node','router/tests/test_lazy_help_ui.js']]

LUA_MUTANTS=[
    # the guards in monitor.run
    ('lua/monitor.lua',"    package.loaded['uloop']=guard.uloop(real,recorder.report)\n","",GUARD),
    ('lua/monitor.lua',"object=function(object,conn) guard.guard_object(object,conn,recorder.report) end,","",GUARD),
    ('lua/monitor.lua',"  if not ok then recorder.fatal('monitor',err) end\n","",GUARD),
    ('lua/monitor.lua',"  if dead or not ok then os.exit(1) end\n","",GUARD),
    ('lua/monitor.lua',"dead=true;recorder.fatal('monitor loop',text);real.cancel()","recorder.fatal('monitor loop',text)",GUARD),
    ('lua/monitor.lua',"    handle.monitor.loop_summary=recorder.summary\n","",GUARD),
    # passing=true never outlives a failure
    ('lua/monitor.lua',"  self.pass_started=nil\n  local finished=false\n","  self.pass_started=runner.clock()\n  local finished=false\n",GUARD),
    ('lua/monitor.lua',"  self.pass_started=nil\n  local finished=false\n","  accounting.stats.diagnostic(runner,runner.wall())\n  local finished=false\n",GUARD),
    ('lua/monitor.lua',"if err then pcall(function() self:publish_failure(err) end) end","if err then self:publish_failure(err) end",GUARD),
    ('lua/monitor.lua',"if okw then finish(ctx) else finish(nil,werr) end","if okw then finish(ctx) end",GUARD),
    # the next pass
    ('lua/monitor.lua',"        if not okd then failed('monitor next pass',derr) end\n        arm(delay)\n","        if not okd then failed('monitor next pass',derr);return end\n        arm(delay)\n",GUARD),
    ('lua/monitor.lua',"        local delay=M.TICK_RETRY*1000\n","        local delay=1\n",GUARD),
    # a dead monitor is not hidden
    ('lua/monitor.lua',"  if self.overdue_beats<M.OVERDUE_BEATS then return nil end\n","",GUARD),
    ('lua/monitor.lua',"M.PASS_OVERDUE=M.PASS_WATCHDOG+15","M.PASS_OVERDUE=M.PASS_WATCHDOG+1500",GUARD),
    ('lua/monitor.lua',"    if late=='pass' or rearms>=M.TICK_REARMS then\n","    if rearms>=M.TICK_REARMS then\n",GUARD),
    ('lua/monitor.lua',"    if late=='pass' or rearms>=M.TICK_REARMS then\n","    if late=='pass' then\n",GUARD),
    ('lua/monitor.lua',"    monitor.tick_due=runner.clock()\n    timer:set(1)\n","    monitor.tick_due=runner.clock()\n",GUARD),
    ('lua/monitor.lua',"    watcher:set(1000)  -- first: nothing below can lose the beat\n","",GUARD),
    # the record
    ('lua/loop_guard.lua',"  return debug.traceback(tostring(e),2)\n","  return tostring(e)\n",GUARD),
    ('lua/loop_guard.lua',"    e=code~=nil and ('code '..tostring(code)) or 'error object'\n","    e=require('canon').encode(e)\n",GUARD),
    ('lua/loop_guard.lua',"M.LOG_EVERY=60 ","M.LOG_EVERY=0 ",GUARD),
    ('lua/loop_guard.lua',"M.KEEP=5 ","M.KEEP=50 ",GUARD),
    ('lua/loop_guard.lua',"  if not mask then return M.WITHHELD end\n","  if not mask then mask=function(x) return x end end\n",GUARD),
    ('lua/loop_guard.lua',"    lines[#lines+1]=(string.gsub(masked,'[%w%+/=_%-]+',token))\n","    lines[#lines+1]=masked\n",GUARD),
    ('lua/loop_guard.lua',"  local lines={}\n  for line in string.gmatch(text,'[^\\n]+') do\n","  local lines={}\n  text=string.sub(string.gsub(text,'%s+',' '),1,M.MESSAGE_LIMIT)\n  for line in string.gmatch(text,'[^\\n]+') do\n",GUARD),
    ('lua/loop_guard.lua',"  return string.sub(joined,1,M.MESSAGE_LIMIT)\n","  return joined\n",GUARD),
    ('lua/loop_guard.lua',"    if new or fatal or not logged[signature] or","    if new or not logged[signature] or",GUARD),
    ('lua/loop_guard.lua',"    if not native_pcall(note,where,err,fatal) then\n","    note(where,err,fatal)\n    if false then\n",GUARD),
    ('lua/loop_guard.lua',"    rows={}\n    local ok,value=native_pcall(function() return canon.decode(d.read(d.path)) end)\n","    rows={}\n    local ok,value=false,nil\n",GUARD),
    # the socket
    ('lua/monitor_io.lua',"local ok,what,data,received_at=pcall(receive)","local ok,what,data,received_at=true,receive()",GUARD),
    ('lua/diag_bundle.lua',"  {'lua-monitor-crashes.json',{'cat','/var/run/homensai-vpn/lua-monitor-crashes.json'}},\n","",GUARD),
    # a long VENDOR-WORKER-BUSY: both publishing paths
    ('lua/pair.lua',"    T.publish(env,M.busy_fields(env,blockers,published))\n","    T.publish(env,published)\n",LOCK),
    ('lua/pair.lua',"      T.publish(env,M.busy_fields(env,blockers,value))\n","      T.publish(env,value)\n",LOCK),
    ('lua/pair.lua',"      if busy and canon.is_object(selection) then value.source=selection.source.id;value.target=selection.target.id end\n","",LOCK),
    ('lua/pair.lua',"    if #blockers==0 then M.busy_fields(env,blockers,nil) end\n","",LOCK),
    ('lua/pair.lua',"M.BUSY_SEEN_SECONDS=120","M.BUSY_SEEN_SECONDS=60",LOCK),
    ('lua/pair.lua',"M.BUSY_SCAN_SECONDS=30 ","M.BUSY_SCAN_SECONDS=60 ",LOCK),
    ('lua/pair.lua',"    if track.logged~=code then\n","    if true then\n",LOCK),
    ('lua/pair.lua',"  if track and now-track.seen>M.BUSY_SCAN_SECONDS then track=nil end\n","",LOCK),
    ('lua/pair.lua',"  if not busy then return nil,nil end\n","  if not busy then return track,nil end\n",LOCK),
    ('lua/pair.lua',"  if row.mark~=track.mark then\n","  if track.mark==nil then\n",LOCK),
    ('lua/pair.lua',"  elseif track.kind=='unidentified' or row.kind~='unidentified' then track.kind=row.kind end\n","  else track.kind=row.kind end\n",LOCK),
    ('lua/pair.lua',"  if scan then track.workers=row.workers end\n","",LOCK),
    ('lua/pair.lua',"  if scan then track.scanned=now end\n","",LOCK),
    ('lua/pair.lua',"workers='VENDOR-BUSY-WORKERS',unidentified='VENDOR-BUSY-UNIDENTIFIED'}","workers='VENDOR-BUSY-UNIDENTIFIED',unidentified='VENDOR-BUSY-UNIDENTIFIED'}",LOCK),
    # what is seen
    ('lua/platform.lua',"      if not sys.exists(base) then row.kind='rtp-lock-dead'\n      else\n","      if true then row.kind='rtp-lock-dead'\n      else\n",LOCK),
    ('lua/platform.lua',"        if command~=nil then row.kind=string.find(command,'rtp2',1,true) and 'rtp-lock-live' or 'rtp-lock-dead' end\n","        row.kind=(command and string.find(command,'rtp2',1,true)) and 'rtp-lock-live' or 'rtp-lock-dead'\n",LOCK),
    ('lua/platform.lua',"row.mark='rtp-lock:'..tostring(st.ino)","row.mark='rtp-lock'",LOCK),
    ('lua/platform.lua',"  elseif M.tunnel_switch_locks(sys) then row.kind='tunnel-switch';row.mark='tunnel-switch' end\n","  end\n",LOCK),
    ('lua/platform.lua',"local raw=st.type=='reg' and sys.read(M.RTP_LOCK) or nil","local raw=sys.read(M.RTP_LOCK)",LOCK),
    ('lua/platform.lua',"    if ok and seen.verified==true then row.workers=seen.busy end\n","    if ok then row.workers=seen.busy end\n",LOCK),
    ('lua/platform.lua',"((row.workers or 0)>0 or M.queues_busy(sys))","(row.workers or 0)>0",LOCK),
    ('lua/platform.lua',"((row.workers or 0)>0 or M.queues_busy(sys))","M.queues_busy(sys)",LOCK),
    ('lua/platform.lua',"    if row.mark=='no-file' and ((row.workers","    if ((row.workers",LOCK),
    ('lua/platform.lua',"(lock and not ignore_lock and M.mt3000_rtp_lock_busy(sys))","(lock and M.mt3000_rtp_lock_busy(sys))",LOCK),
    # the Telegram notice
    ('lua/telegram.lua',"  state=M.vendor_notice(d,config,status,state,now)\n","",LOCK),
    ('lua/telegram.lua',"  if known==key then return state end\n","",LOCK),
    ('lua/telegram.lua',"    if known~=nil then pcall(d.remove,path) end\n","",LOCK),
    ('lua/telegram.lua',"      state=with(state,{last_code='TELEGRAM-DELIVERED'})\n","      state=with(state,{last_code='TELEGRAM-DELIVERED',sent=canon.float(now)})\n",LOCK),
    ('lua/telegram.lua',"      state=with(state,{last_code='TELEGRAM-DELIVERED'})\n","      state=with(state,{last_code='TELEGRAM-DELIVERED',attempt=canon.float(now)})\n",LOCK),
    ('lua/telegram.lua',"      state=with(state,{attempt=canon.float(now),last_code=err.code,retry_after=err.retry_after})\n","      state=with(state,{last_code=err.code})\n",LOCK),
    ('lua/telegram.lua',"  if not stamp or now-stamp>M.NOTICE_MAX_AGE then return nil end\n","",LOCK),
    ('lua/telegram.lua',"This does not prove GL.iNet has finished: a killed rtp2 can leave its child commands running. ","GL.iNet is idle. ",LOCK),
    # a bypass of the blocker must fail
    ('lua/platform.lua',"  local allowed=M.ALLOWED_STALE_LOCK\n  if allowed==nil then return true end\n","  local allowed=M.ALLOWED_STALE_LOCK\n  if allowed==nil then return M.vendor_busy_seen(sys).kind~='rtp-lock-dead' end\n",LOCK),
    ('lua/backend.lua',"    if platform.tunnel_switch_locks(sys) or platform.rtp_lock_busy(sys) then add('VENDOR-WORKER-BUSY') end\n","",[['lua5.1','lua/test_backend.lua']]),
    ('lua/backend.lua',"  function B.vendor_busy_seen(scan) return platform.vendor_busy_seen(sys,scan) end\n","",[['lua5.1','lua/test_backend.lua']]),
]
PY_MUTANTS=[
    ('pair_auto.py',"        n.publish(busy_fields(backend,blockers,value))\n        return True\n    if proof(selection)","        n.publish(value)\n        return True\n    if proof(selection)",PY),
    ('pair_auto.py',"            n.publish(busy_fields(backend,blockers,value))\n            return True\n        if not state_order","            n.publish(value)\n            return True\n        if not state_order",PY),
    ('pair_auto.py',"        if not blockers:busy_fields(backend,blockers,None)\n","",PY),
    ('pair_auto.py',"            if 'VENDOR-WORKER-BUSY' in blockers and selection:value.update(source=selection['source']['id'],target=selection['target']['id'])\n","",PY),
    ('pair_auto.py',"BUSY_SEEN_SECONDS = 120","BUSY_SEEN_SECONDS = 60",PY),
    ('pair_auto.py',"BUSY_SCAN_SECONDS = 30 ","BUSY_SCAN_SECONDS = 60 ",PY),
    ('pair_auto.py',"        if track.get('logged')!=code:\n","        if True:\n",PY),
    ('pair_auto.py',"    if track is not None and now-track['seen']>BUSY_SCAN_SECONDS:track=None\n","",PY),
    ('pair_auto.py',"    if not busy:return None,None\n","    if not busy:return track,None\n",PY),
    ('pair_auto.py',"    if row['mark']!=track.get('mark'):\n","    if track.get('mark') is None:\n",PY),
    ('pair_auto.py',"    elif track['kind']=='unidentified' or row['kind']!='unidentified':track['kind']=row['kind']\n","    else:track['kind']=row['kind']\n",PY),
    ('pair_auto.py',"    if scan:track['workers']=row.get('workers')\n","",PY),
    ('pair_auto.py',"    if scan:track['scanned']=now\n","",PY),
    ('rollback_recovery.py',"            if not base.exists():row['kind']='rtp-lock-dead'\n            else:\n","            if True:row['kind']='rtp-lock-dead'\n            else:\n",PY),
    ('rollback_recovery.py',"                except OSError:pass\n    elif list(Path('/var/run')","                except OSError:row['kind']='rtp-lock-dead'\n    elif list(Path('/var/run')",PY),
    ('rollback_recovery.py',"row['mark']='rtp-lock:%d'%st.st_ino","row['mark']='rtp-lock'",PY),
    ('rollback_recovery.py',"            if seen.get('verified') is True:row['workers']=seen.get('busy')\n","            row['workers']=None\n",PY),
    ('mt3000_manual_platform.py',"or not ignore_lock and RTP_LOCK.exists() and _rtp_lock_busy():","or RTP_LOCK.exists() and _rtp_lock_busy():",PY),
    ('telegram_report.py',"    state=vendor_notice(config,status,state,now)\n","",PY),
    ('telegram_report.py',"    if known==key:return state\n","",PY),
    ('telegram_report.py',"        if known is not None:\n            try:path.unlink()\n            except OSError:pass\n        return state\n","        return state\n",PY),
    ('telegram_report.py',"    return dict(state,last_code='TELEGRAM-DELIVERED')\n","    return dict(state,last_code='TELEGRAM-DELIVERED',attempt=now)\n",PY),
    ('telegram_report.py',"or now-stamp>NOTICE_MAX_AGE:return None","or False:return None",PY),
    ('telegram_report.py',"            return dict(state,attempt=now,last_code=error.code,retry_after=error.retry_after,**{counter:state.get(counter,0)+1})\n","            return state\n",PY),
    # a bypass of the blocker must fail
    ('rollback_recovery.py',"    allowed=ALLOWED_STALE_LOCK[0]\n    if allowed is None:return True\n","    allowed=ALLOWED_STALE_LOCK[0]\n    if allowed is None:return vendor_busy_seen()['kind']!='rtp-lock-dead'\n",PY),
]
JS_MUTANTS=[
    ('../../../../../qa/export_lazy_titles.js',".filter(row=>!row[0].startsWith('VENDOR-BUSY-'))","",LAZY),
    ('../../../../auto_panel.inc.js',"var waitingNow=sessionRuns&&blockers.length&&blockers.every(","var waitingNow=false&&blockers.length&&blockers.every(",JS),
    ('../../../../auto_panel.inc.js',"return AUTO_TRANSIENT.indexOf(code)<0;","return false;",JS),
    ('../../../../auto_panel.inc.js',"||ns.busy_seconds&&ns.reason||blockers[0]||(","||ns.reason||blockers[0]||(",JS),
]


def fails(suites,cwd):
    for argv in suites:
        try:
            if subprocess.run(argv,cwd=cwd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=900).returncode:return True
        except subprocess.TimeoutExpired:return True  # a spin or a hang is a detected mutant
    return False


def main(argv):
    kinds=[x for x in argv if x in ('lua','py','js')] or ['lua','py','js']
    needles=next((x for x in argv if x not in ('lua','py','js')),'').split('|')  # any of a|b|c
    groups={'lua':(LUA_MUTANTS,HERE),'py':(PY_MUTANTS,HERE),'js':(JS_MUTANTS,REPO)}
    survived=broken=total=0
    for kind in kinds:
        mutants,cwd=groups[kind]
        for name,old,new,suites in mutants:
            if not any(needle in name+old+new for needle in needles):continue
            total+=1
            path=(LIB/name).resolve()
            source=path.read_bytes()
            text=source.decode('utf-8').replace('\r\n','\n')
            if old not in text:
                broken+=1;print('NOT-APPLIED',name,repr(old[:70]),flush=True);continue
            try:
                path.write_bytes(text.replace(old,new,1).encode('utf-8'))
                caught=fails(suites,cwd)
            finally:
                path.write_bytes(source)
                if kind=='js':
                    subprocess.run([sys.executable,'router/build_sidebar_ui.py'],cwd=REPO,check=True,stdout=subprocess.DEVNULL)
            print('killed  ' if caught else 'SURVIVED',name,repr(old[:70]),'->',repr(new[:40]),flush=True)
            survived+=0 if caught else 1
    print('MUTANTS total',total,'survived',survived,'not applied',broken,flush=True)
    return 1 if survived or broken else 0


if __name__=='__main__':sys.exit(main(sys.argv[1:]))
