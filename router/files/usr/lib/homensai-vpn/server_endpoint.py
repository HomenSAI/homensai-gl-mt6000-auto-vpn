"""Read-only public peer address, bound to a live VPN interface/process epoch.

Never returns keys, credentials, raw configuration, DNS results or guessed
addresses from profile names. Missing/ambiguous evidence stays unavailable.
"""
import ipaddress
import os
from pathlib import Path
import re
import socket
import subprocess
import time

INTERFACE=re.compile(r'^(?:wgclient|ovpnclient)[0-9]{1,4}$')
PROFILE=re.compile(r'^(?:wireguard|openvpn):[A-Za-z0-9_.:-]{1,80}$')

def address(value):
    if not isinstance(value,str) or len(value)>100:raise ValueError('ENDPOINT-ADDRESS')
    if value.startswith('['):host,port=value[1:].split(']:')
    else:host,port=value.rsplit(':',1)
    parsed=ipaddress.ip_address(host);port=int(port)
    if parsed.is_unspecified or parsed.is_loopback or parsed.is_multicast or not 1<=port<=65535:raise ValueError('ENDPOINT-ADDRESS')
    return str(parsed.ipv4_mapped if isinstance(parsed,ipaddress.IPv6Address) and parsed.ipv4_mapped else parsed),port

def proc_address(value,ipv6=False):
    host,port=value.split(':');raw=bytes.fromhex(host)
    if len(raw)!=(16 if ipv6 else 4):raise ValueError('ENDPOINT-PROC')
    raw=b''.join(raw[i:i+4][::-1] for i in range(0,16,4)) if ipv6 else raw[::-1]
    ip=socket.inet_ntop(socket.AF_INET6 if ipv6 else socket.AF_INET,raw)
    return address(('['+ip+']' if ipv6 else ip)+':'+str(int(port,16)))

def socket_peers(text,inodes,transport,ipv6=False):
    if len(text)>65536:return set()
    peers=set()
    for line in text.splitlines()[1:]:
        fields=line.split()
        if len(fields)<10 or fields[9] not in inodes or transport=='tcp' and fields[3]!='01':continue
        try:peers.add((*proc_address(fields[2],ipv6),transport))
        except (ValueError,IndexError):continue
    return peers

def _read(path,limit):
    with path.open('rb') as stream:data=stream.read(limit+1)
    if len(data)>limit:raise ValueError('ENDPOINT-READ-LIMIT')
    return data.decode('ascii')

def process_epoch(text):
    if ')' not in text:raise ValueError('ENDPOINT-PROCESS-EPOCH')
    fields=text.rsplit(')',1)[1].split()
    if len(fields)<=19:raise ValueError('ENDPOINT-PROCESS-EPOCH')
    value=fields[19]
    if not value.isdigit():raise ValueError('ENDPOINT-PROCESS-EPOCH')
    return value

def observe(profile,now,root=Path('/'),runner=None):
    interface=profile.get('interface');identifier=profile.get('id')
    if (not isinstance(interface,str) or not INTERFACE.fullmatch(interface)
            or not isinstance(identifier,str) or not PROFILE.fullmatch(identifier)
            or profile.get('protocol') not in ('openvpn','wireguard') or not identifier.startswith(profile['protocol']+':')):
        return None
    until=time.monotonic()+.5
    try:
        index=_read(root/'sys/class/net'/interface/'ifindex',32).strip()
        peers=set()
        if profile.get('protocol')=='wireguard' and interface.startswith('wgclient'):
            if runner is None:raw=subprocess.check_output(['wg','show',interface,'endpoints'],stderr=subprocess.DEVNULL,timeout=.4)
            else:raw=runner(['wg','show',interface,'endpoints'])
            if len(raw)>4096:return None
            for line in raw.decode('ascii').splitlines():
                parts=line.split()
                if len(parts)!=2:return None
                host,port=address(parts[1]);peers.add((host,port,'udp'))
        elif profile.get('protocol')=='openvpn' and interface.startswith('ovpnclient'):
            pid=_read(root/'var/run'/('ovpnclient-'+interface+'.pid'),32).strip()
            if not pid.isdigit() or not 1<int(pid)<2**31:return None
            process=root/'proc'/pid
            if _read(process/'comm',64).strip()!='openvpn':return None
            epoch=process_epoch(_read(process/'stat',4096))
            args=_read(process/'cmdline',16384).strip('\0').split('\0')
            if args.count('--dev')!=1 or args.index('--dev')+1>=len(args) or args[args.index('--dev')+1]!=interface:return None
            inodes=set()
            with os.scandir(process/'fd') as entries:
                for count,entry in enumerate(entries):
                    if count>=256 or time.monotonic()>until:return None
                    try:target=os.readlink(entry.path)
                    except OSError:continue
                    match=re.fullmatch(r'socket:\[([0-9]{1,20})\]',target)
                    if match:inodes.add(match[1])
            for name,transport,ipv6 in [('tcp','tcp',False),('tcp6','tcp',True),('udp','udp',False),('udp6','udp',True)]:
                if time.monotonic()>until:return None
                try:text=_read(process/'net'/name,65536)
                except FileNotFoundError:continue
                peers.update(socket_peers(text,inodes,transport,ipv6))
            # The process may perform more than one connection. Never guess.
            if process_epoch(_read(process/'stat',4096))!=epoch:return None
        else:return None
        if time.monotonic()>until or len(peers)!=1 or _read(root/'sys/class/net'/interface/'ifindex',32).strip()!=index:return None
        host,port,transport=next(iter(peers))
        return {'profile':identifier,'interface':interface,'host':host,'port':port,'transport':transport,'time':now,'source':'live-kernel-peer'}
    except (OSError,ValueError,UnicodeError,subprocess.SubprocessError):return None
