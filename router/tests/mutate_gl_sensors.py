"""Mutation check of the GL sensors (GL-SENSORS-2026-11-04.ru.md): every mutant of the decision code must make
tests/test_gl_sensors.py (Python twins) or tests/lua/test_gl_sensors.lua (Lua twins) fail. Each mutant is applied in
place, the matching suite runs, the file is restored (also on error). Run on a copy (docker), never on the router:
  python router/tests/mutate_gl_sensors.py   -> one line per mutant, exit 1 when a mutant survives
"""
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
PY=[sys.executable,'-m','unittest','test_gl_sensors','-q']
LUA=['lua5.1','lua/test_gl_sensors.lua']

# Not listed (equivalent): dropping the rx-decrease reset - a decreasing rx is a change too (rx_at and the tx base move
# the same way); only the veto history differs and a negative growth can never reach the veto threshold.
MUTANTS=[
    # Python twins
    ('wan_diag.py','HOLD_P=0.95','HOLD_P=0.5'),
    ('wan_diag.py',"get('primary')=='bad' and get('reserve')!='ok'","get('primary')=='bad'"),
    ('wan_diag.py',"wan_proof=get('underlay')=='fail' or","wan_proof=get('underlay')=='ok' or"),
    ('wan_diag.py',"get('primary')=='bad' and get('reserve')=='ok' and p[4]<=HASTEN_WAN_MAX","get('primary')=='bad' and p[4]<=HASTEN_WAN_MAX"),
    ('wan_diag.py','p=[value/total for value in p]','p=p'),
    ('wan_diag.py',"'fail':(0.02,  0.02,   0.02,   0.03,   0.98,   0.03)","'fail':(0.02,  0.02,   0.02,   0.03,   0.5,   0.03)"),
    ('wan_diag.py',"if code=='DNS-001':return 'dns'","if code=='DNS-001':return 'bad'"),
    ('wan_diag.py','len(self.fail_targets)>=2','len(self.fail_targets)>=1'),
    ('wan_diag.py',"if self.calibrated and self.fails>=self.FAIL_N","if self.fails>=self.FAIL_N"),
    ('wan_diag.py','and not healthy_after:recovering=True',':recovering=True'),
    ('wan_diag.py','0<=now-self.up_at<grace','0<=now-self.up_at<=grace'),
    ('stall.py','VETO_BYTES=3750','VETO_BYTES=375'),
    ('stall.py','if stalled>=STALL_SECONDS and','if stalled>STALL_SECONDS and'),
    ('stall.py','if oldest is not None and self.rx_at==now and','if oldest is not None and'),
    ('quorum.py',"if len(missing)>=self.k:return 'lost'","if len(missing)>self.k:return 'lost'"),
    ('quorum.py','MISS_LIMIT=3','MISS_LIMIT=4'),
    ('wg_events.py',"if kind not in ('timeout','giveup'):continue","if kind not in ('timeout',):continue"),
    ('wg_events.py','            self.seen=max([e[0] for e in events],default=0.0)\n            return []','            self.seen=max([e[0] for e in events],default=0.0)\n            return list(events)'),
    ('boot_cause.py',"if fp!='' and fp!=remembered:return 'crash',fp","if fp!=remembered:return 'crash',fp"),
    ('boot_cause.py','return 0<=delta<=MATCH_MINUTES','return abs(delta)<=MATCH_MINUTES'),
    ('boot_cause.py','days.add(7 if value==0 else value)','days.add(value)'),
    ('interruption.py',"if f.get('crash'):return 'RESTART-KERNEL-CRASH'","if False:return 'RESTART-KERNEL-CRASH'"),
    ('interruption.py',"return 'RESTART-PLANNED-REBOOT' if f.get('reason')=='planned-reboot' else 'RESTART-CLEAN'","return 'RESTART-CLEAN'"),
    ('failure_diagnosis.py',"wan.get('hold') is True and isinstance","isinstance"),
    ('failure_diagnosis.py',"and fresh(wan.get('time'),now,age)):","):"),
    ('diag_bundle.py',"'secret','token','psk'","'secret','psk'"),
    ('diag_bundle.py',"line=MAC.sub(lambda m:m.group(0)[:8]+':xx:xx:xx',line)","pass"),
    ('diag_bundle.py',"return '<key>' if len(match.group(0))==44 else","return '<key>' if len(match.group(0))==43 else"),
    # security audit 04.11.2026: masks of public addresses, free text, IPv6, names (Python twin)
    ('diag_bundle.py',"a==10 or","a==11 or"),
    ('diag_bundle.py',"or (a==192 and b==168)","or (a==192 and b==169)"),
    ('diag_bundle.py',"line=IPV4.sub(_ipv4,line)","pass"),
    ('diag_bundle.py',"line=IPV6.sub(_ipv6,line)","pass"),
    ('diag_bundle.py',"if '::' not in token and token.count(':')!=7:return token","pass"),
    ('diag_bundle.py',"line=FREE_PAIR.sub(_free,line)","pass"),
    ('diag_bundle.py',"if not secret_name(name.rsplit('.',1)[-1]) or value==MASK","if not secret_name(name) or value==MASK"),
    ('diag_bundle.py',"line=CHAT_ID.sub(lambda m:m.group(1)+m.group(2)+MASK,line)","pass"),
    ('diag_bundle.py',"line=SSID_TEXT.sub(lambda m:m.group(1)+m.group(2)+\"'\"+MASK+\"'\",line)","pass"),
    ('diag_bundle.py',"line=JSON_NUMBER.sub(_number,line)","pass"),
    ('diag_bundle.py',"EXACT_SECRET=('sig',","EXACT_SECRET=('sigx',"),
    ('diag_bundle.py',"'bssid','user','login'","'bssid','login'"),
    ('diag_bundle.py',"'description','comment','label',","'comment','label',"),
    ('diag_bundle.py',"h=(h*33+byte)&0xFFFFFFFF","h=(h*31+byte)&0xFFFFFFFF"),
    ('diag_bundle.py',"previous,SALT=SALT,os.urandom(8).hex()","previous=SALT"),
    ('gl_sensors.py',"or self.underlay.fails>0 or tracked['hold'] is True)","or tracked['hold'] is True)"),
    ('gl_sensors.py',"self.underlay.record(ok is True,target,now)","self.underlay.record(True,target,now)"),
    # Lua twins
    ('lua/wan_diag.lua','M.HOLD_P=0.95','M.HOLD_P=0.5'),
    ('lua/wan_diag.lua',"get('primary')=='bad' and get('reserve')~='ok'","get('primary')=='bad'"),
    ('lua/wan_diag.lua',"get('primary')=='bad' and get('reserve')=='ok' and p[5]<=M.HASTEN_WAN_MAX","get('primary')=='bad' and p[5]<=M.HASTEN_WAN_MAX"),
    ('lua/wan_diag.lua','for i=1,#p do p[i]=p[i]/total end',''),
    ('lua/wan_diag.lua','#self.fail_targets>=2','#self.fail_targets>=1'),
    ('lua/wan_diag.lua','and not healthy_after then recovering=true','then recovering=true'),
    ('lua/stall.lua','M.VETO_BYTES=3750','M.VETO_BYTES=375'),
    ('lua/stall.lua','if oldest~=nil and self.rx_at==now and','if oldest~=nil and'),
    ('lua/quorum.lua',"if #missing>=self.k then return 'lost' end","if #missing>self.k then return 'lost' end"),
    ('lua/wg_events.lua',"if e[2]=='timeout' or e[2]=='giveup' then","if e[2]=='timeout' then"),
    ('lua/boot_cause.lua',"if fp~='' and fp~=remembered then return 'crash',fp end","if fp~=remembered then return 'crash',fp end"),
    ('lua/boot_cause.lua','h=(h*31+chunk[k])%4294967296','h=(h*33+chunk[k])%4294967296'),
    ('lua/boot_cause.lua','byte(data,i,math.min(i+255,n))','byte(data,i,math.min(i+254,n))'),
    ('lua/interruption.lua',"if f.crash then return 'RESTART-KERNEL-CRASH' end",''),
    ('lua/diagnosis.lua','canon.is_object(wan) and wan.hold==true and','canon.is_object(wan) and'),
    ('lua/diag_bundle.lua',"'secret','token','psk'","'secret','psk'"),
    ('lua/diag_bundle.lua',"a==10 or","a==11 or"),
    ('lua/diag_bundle.lua',"or (a==192 and b==168)","or (a==192 and b==169)"),
    ('lua/diag_bundle.lua',"h=(h*33+string.byte(s,i))%4294967296","h=(h*31+string.byte(s,i))%4294967296"),
    ('lua/diag_bundle.lua',"if not string.find(token,'::',1,true) and colons~=7 then return nil end",""),
    ('lua/diag_bundle.lua',"local last=string.match(name,'([^%.]+)$') or name","local last=name"),
    ('lua/diag_bundle.lua',"'bssid','user','login'","'bssid','login'"),
    ('lua/diag_bundle.lua',"'description','comment','label',","'comment','label',"),
    ('lua/diag_bundle.lua',"sig=true,","sigx=true,"),
    ('lua/diag_bundle.lua',"M.SALT=(string.gsub(seed,'.',function(ch) return string.format('%02x',string.byte(ch)) end))","M.SALT=''"),
    ('lua/diag_bundle.lua',"if after=='.' and string.find(after2,'^%d$') then return nil end",""),
    ('lua/diag_bundle.lua',"line=string.gsub(line,'([Cc][Hh][Aa][Tt][_ ]?[Ii][Dd])(%s*[=:]?%s*)(%-?%d%d%d%d%d+)',function(a,b) return a..b..M.MASK end)",""),
    ('lua/diag_bundle.lua',"if M.secret_name(k) then return '\"'..k..'\"'..sep..'\"'..M.MASK..'\"' end\n    return nil\n  end)\n  line=string.gsub(line,'([%w_%.@","return nil\n  end)\n  line=string.gsub(line,'([%w_%.@"),
    ('lua/fast_detect.lua',"if previous=='lost' and self.opts.veto and ch.flowing then previous='vetoed' end",''),
    ('lua/fast_detect.lua','ch.own_bytes=ch.own_bytes+M.ECHO_BYTES',''),
    ('lua/fast_detect.lua',"elseif ch.stalled then ch.suspect_reason=M.STALL_REASON end",'end'),
    ('lua/fast_detect.lua',"if ch.pool then previous=ch.pool:judge(answered,now)","if false then previous=ch.pool:judge(answered,now)"),
    ('lua/gl_sensors.lua',"u:record(ok,p.target,p.at)","u:record(true,p.target,p.at)"),
    ('lua/gl_sensors.lua',"if self.wg_on and not runner.exists(flag) then runner.write_ram(flag,'file\\n')","if false then"),
]


def write(path,text):
    with open(str(path),'w',encoding='utf-8',newline=chr(10)) as handle:handle.write(text)


def run(mutant):
    name,old,new=mutant
    path=LIB/name
    text=path.read_text(encoding='utf-8')
    if text.count(old)!=1:return 'BROKEN (pattern found %d times)'%text.count(old)
    try:
        write(path,text.replace(old,new,1))
        argv=LUA if name.startswith('lua/') else PY
        # the case-file currency check would kill every Python mutant without a semantic test: off for mutants
        env=dict(__import__('os').environ,GL_SENSORS_MUTATION='1')
        result=subprocess.run(argv,cwd=str(HERE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600,env=env)
        return 'killed' if result.returncode!=0 else 'SURVIVED'
    finally:
        write(path,text)


def main():
    survived=0
    for index,mutant in enumerate(MUTANTS,1):
        verdict=run(mutant)
        if verdict!='killed':survived+=1
        print('%2d %-22s %-8s %s'%(index,mutant[0],verdict,mutant[1][:70].replace('\n',' ')))
    print('mutants %d, killed %d, survived %d'%(len(MUTANTS),len(MUTANTS)-survived,survived))
    return 1 if survived else 0


if __name__=='__main__':
    sys.exit(main())
