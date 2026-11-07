# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""The monitor side of the GL sensors for agent.py (docs/architecture/GL-SENSORS-2026-11-04.ru.md). Lua twin:
lua/gl_sensors.lua (the decisions are the shared pure modules wan_diag / wg_events / boot_cause).

  tick(now)    the monitor's 1 s wait loop: the underlay echo through the WAN device (raw ICMP socket bound to it with
               SO_BINDTODEVICE, no tunnel mark, 1 s deadline; one echo per 10 s, every 2 s while a channel fails or the
               WAN is suspected), new WireGuard events (one stat per second, read only when changed) and, once per
               boot after 120 s of uptime, the crash-log fingerprint (boot_cause.refresh). Returns the suspicion items
               of REKEY events of pair devices (Booster.suspect, dense checks only).
  configure(settings, wan_devices, rows, pair)   after every pass
  pass_(rows, pair, wall, age, settings, uplink) the status field wan_diagnosis; sets hasten / restored
"""
import errno
import json
import os
import socket
import struct
import time

import wan_diag
import wg_events

KMWAN='/proc/gl-kmwan/config'
BOOT_REFRESH_UPTIME=120
SCOPE=('WAN versus tunnel diagnosis: own ICMP echo through the WAN device, GL multi-WAN and repeater verdicts, the pair '
       'probes and WireGuard events; holds a switch only while the WAN is proven down')
SEND_FAILURE=frozenset((errno.EPERM,errno.EACCES,errno.ENETDOWN,errno.ENETUNREACH,errno.EHOSTUNREACH,errno.ENODEV,errno.ENXIO))


def underlay_echo(device,target,timeout=1.0):
    """True: a valid reply within timeout; False: none or a send the kernel refused. Raises only when no socket exists."""
    from icmp_ping import checksum,valid_reply
    identifier,sequence=struct.unpack('!HH',os.urandom(4));payload=b'HV-WAN\0\0'+os.urandom(16)
    packet=struct.pack('!BBHHH',8,0,0,identifier,sequence)+payload
    packet=struct.pack('!BBHHH',8,0,checksum(packet),identifier,sequence)+payload
    with socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP) as sock:
        try:sock.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_BINDTODEVICE',25),device.encode('ascii')+b'\0')
        except OSError as error:
            if error.errno in (errno.ENODEV,errno.ENXIO):return False
            raise
        deadline=time.monotonic()+timeout
        try:sock.sendto(packet,(target,0))
        except OSError as error:
            if error.errno in SEND_FAILURE:return False
            raise
        while True:
            left=deadline-time.monotonic()
            if left<=0:return False
            sock.settimeout(left)
            try:data,peer=sock.recvfrom(512)
            except socket.timeout:return False
            if peer[0]==target and valid_reply(data,identifier,sequence,payload,target):return True


def _read(path):
    try:
        with open(path,'r',encoding='utf-8',errors='replace') as handle:return handle.read(65536)
    except OSError:return None


def _key(path):
    try:
        st=os.stat(path);return (st.st_ino,st.st_size,st.st_mtime)
    except OSError:return None


class Sensors:
    def __init__(self,runtime,persist,echo=underlay_echo,read=_read,key=_key,repeater=None,write_json=None,uptime=None):
        self.runtime=str(runtime);self.persist=str(persist)
        self.echo=echo;self.read=read;self.key=key;self.repeater=repeater;self.write_json=write_json
        self.uptime=uptime or time.monotonic
        self.underlay=wan_diag.Underlay();self.tracker=wan_diag.Tracker();self.reader=wg_events.Reader()
        self.events=[];self.events_key=False;self.enabled=False;self.wg_on=False;self.alert=False
        self.channels=[];self.boot_done=False;self.hasten=False;self.restored=False;self.flag_done=False

    def configure(self,settings,wan_devices,rows,pair):
        self.enabled=wan_diag.enabled(settings)
        device=None
        if self.enabled:
            for row in wan_devices if isinstance(wan_devices,list) else []:
                if isinstance(row,dict) and isinstance(row.get('device'),str):device=row['device'];break
        self.underlay.bind(device)
        pair=pair if isinstance(pair,dict) else {}
        self.channels=[{'id':row['id'],'device':row['device']} for row in (rows if isinstance(rows,list) else [])
                       if isinstance(row,dict) and isinstance(row.get('id'),str) and isinstance(row.get('device'),str)
                       and row['id'] in (pair.get('source'),pair.get('target'))]
        on=wg_events.enabled(settings)
        if on!=self.wg_on:self.reader=wg_events.Reader();self.events=[];self.events_key=False;self.flag_done=False
        self.wg_on=on

    def flag_tick(self):
        '''The hotplug listener writes only while RUNTIME/wg-events.on exists (kept in step by the 1 s loop).'''
        if self.flag_done:return
        flag=os.path.join(self.runtime,wg_events.FLAG)
        try:
            if self.wg_on and not os.path.exists(flag):
                with open(flag,'w') as handle:handle.write('file\n')
            elif not self.wg_on and os.path.exists(flag):os.remove(flag)
            self.flag_done=True
        except OSError:pass

    def underlay_tick(self,now):
        if not self.enabled or self.underlay.device is None or not self.underlay.due(now,self.alert):return
        target=self.underlay.target()
        try:ok=self.echo(self.underlay.device,target)
        except OSError:return
        self.underlay.record(ok is True,target,now)

    def events_tick(self):
        if not self.wg_on:return []
        path=os.path.join(self.runtime,wg_events.FILE)
        key=self.key(path)
        if key==self.events_key:return []
        self.events_key=key
        self.events=wg_events.parse(self.read(path))
        return wg_events.suspicions(self.reader.new(self.events),self.channels)

    def tick(self,now):
        self.flag_tick()
        try:self.underlay_tick(now)
        except Exception:pass
        try:items=self.events_tick()
        except Exception:items=[]
        if not self.boot_done and now>=BOOT_REFRESH_UPTIME:
            self.boot_done=True
            try:
                import boot_cause
                boot_cause.refresh(self.persist,write=self.write_json)
            except Exception:pass
        return items

    def pass_(self,rows,pair,wall,age,settings,uplink):
        mono=self.uptime()
        try:kmwan=wan_diag.kmwan_verdict(self.read(KMWAN))
        except Exception:kmwan=None
        wg_state=None
        if self.wg_on and isinstance(pair,dict):
            for channel in self.channels:
                if channel['id']==pair.get('source'):wg_state=wg_events.latest(self.events,channel['device'],mono)
        sensors=dict(uplink=uplink,underlay=self.underlay.state(mono),kmwan=kmwan,wg=wg_state)
        evidence=wan_diag.evidence(rows,pair,wall,age,**sensors)
        if self.enabled and evidence['primary']=='bad' and self.repeater is not None:
            try:sensors['portal']=wan_diag.portal_verdict(json.loads(self.repeater()))
            except Exception:pass
            evidence=wan_diag.evidence(rows,pair,wall,age,**sensors)
        diagnosis=wan_diag.diagnose(evidence,self.enabled)
        primary_ok_at=None
        if isinstance(pair,dict):
            for row in rows if isinstance(rows,list) else []:
                if isinstance(row,dict) and row.get('id')==pair.get('source') and wan_diag.channel_state(row,wall,age)=='ok':
                    primary_ok_at=row.get('time')
        if self.enabled:tracked=self.tracker.update(diagnosis,wall,primary_ok_at,wan_diag.grace_seconds(settings))
        else:
            self.tracker=wan_diag.Tracker()
            tracked={'hold':False,'recovering':False,'restored':False,'code':diagnosis['code'],'down_since':None,'up_at':None}
        self.alert=(evidence['primary'] in ('bad','dns') or evidence['reserve'] in ('bad','dns')
                    or self.underlay.fails>0 or tracked['hold'] is True)
        self.restored=tracked['restored'] is True
        self.hasten=diagnosis['hasten'] is True
        return {'time':wall,'enabled':self.enabled,'verdict':diagnosis['verdict'],'confidence':diagnosis['confidence'],
                'code':tracked['code'],'hold':tracked['hold'] is True,'recovering':tracked['recovering'] is True,
                'hasten':diagnosis['hasten'] is True,'posterior':diagnosis['posterior'],'evidence':evidence,
                'underlay':self.underlay.public(mono),'down_since':tracked.get('down_since'),'up_at':tracked.get('up_at'),
                'scope':SCOPE}
