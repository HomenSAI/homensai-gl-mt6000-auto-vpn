"""Fetch hash-checked official x86 lab dependencies, never router feeds.

The marked guest must independently verify Packages.sig using its ROM keys.
Cached package binaries remain private under .git/handoff, outside releases.
"""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import urllib.parse
import urllib.request

FEEDS={
 'core':'https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/packages/',
 'base':'https://downloads.openwrt.org/releases/21.02.7/packages/x86_64/base/',
 'packages':'https://downloads.openwrt.org/releases/21.02.7/packages/x86_64/packages/'
}
REQUESTED=['openvpn-openssl','wireguard-tools','kmod-wireguard','kmod-tun','kmod-veth','openssl-util','conntrack']


def download(url,path,limit):
    with urllib.request.urlopen(url,timeout=30) as response:
        if urllib.parse.urlsplit(response.geturl()).hostname not in ('downloads.openwrt.org','archive.openwrt.org'):
            raise RuntimeError('UNTRUSTED-FEED-REDIRECT')
        data=response.read(limit+1)
    if len(data)>limit:raise RuntimeError('FEED-DOWNLOAD-LIMIT')
    if path.exists() and path.read_bytes()!=data:raise RuntimeError('CACHE-CONTENT-CHANGED')
    path.write_bytes(data)
    return data


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--installed',type=Path,required=True)
    args=parser.parse_args();cache=args.cache.resolve()
    installed=json.loads(args.installed.read_text(encoding='utf8'))
    if '.git' not in cache.parts or 'handoff' not in cache.parts:parser.error('private .git/handoff cache required')
    cache.mkdir(parents=True,exist_ok=True)
    packages={};indices=[]
    for feed,url in FEEDS.items():
        directory=cache/feed;directory.mkdir(exist_ok=True)
        packed=download(url+'Packages.gz',directory/'Packages.gz',8*1024*1024)
        signature=download(url+'Packages.sig',directory/'Packages.sig',65536)
        text=gzip.decompress(packed)
        if len(text)>32*1024*1024:raise RuntimeError('FEED-INDEX-LIMIT')
        (directory/'Packages').write_bytes(text)
        indices.append(dict(feed=feed,url=url,index_sha256=hashlib.sha256(text).hexdigest(),signature_sha256=hashlib.sha256(signature).hexdigest()))
        for stanza in text.decode('utf8').split('\n\n'):
            fields={}
            for line in stanza.splitlines():
                if line and not line[0].isspace() and ': ' in line:
                    key,value=line.split(': ',1);fields[key]=value
            name=fields.get('Package')
            if name and name not in packages:packages[name]=dict(fields,feed=feed)
    providers={}
    for name,row in packages.items():
        for alias in row.get('Provides','').split(','):
            alias=alias.strip().split(' ',1)[0]
            if alias:providers.setdefault(alias,name)
    selected={};pending=list(REQUESTED);satisfied={}
    while pending:
        name=pending.pop()
        if name not in packages and name in providers:name=providers[name]
        if name in selected:continue
        if name not in packages:
            if name in installed:satisfied[name]=installed[name];continue
            raise RuntimeError('LAB-DEPENDENCY-UNAVAILABLE:'+name)
        row=packages[name];selected[name]=row
        for dependency in row.get('Depends','').split(','):
            if not dependency.strip():continue
            options=[part.strip().split(' ',1)[0] for part in dependency.split('|')]
            found=next((candidate for candidate in options if candidate in packages or candidate in providers or candidate in installed),None)
            if not found:raise RuntimeError('LAB-DEPENDENCY-UNAVAILABLE:'+options[0])
            pending.append(found)
    if len(selected)>128:raise RuntimeError('LAB-PACKAGE-COUNT')
    artifacts=[];total=0
    for name,row in sorted(selected.items()):
        filename=row.get('Filename','');path=PurePosixPath(filename)
        if path.name!=filename or not re.fullmatch(r'[A-Za-z0-9+_.-]+\.ipk',filename):raise RuntimeError('LAB-PACKAGE-PATH')
        expected=row.get('SHA256sum','')
        if not re.fullmatch(r'[a-f0-9]{64}',expected):raise RuntimeError('LAB-PACKAGE-HASH-MISSING')
        data=download(FEEDS[row['feed']]+filename,cache/row['feed']/filename,32*1024*1024)
        if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('LAB-PACKAGE-HASH-MISMATCH')
        total+=len(data)
        if total>128*1024*1024:raise RuntimeError('LAB-PACKAGE-TOTAL-LIMIT')
        artifacts.append(dict(name=name,version=row['Version'],feed=row['feed'],filename=filename,sha256=expected,bytes=len(data)))
        print('HASH-CHECKED '+name+' '+row['Version'],flush=True)
    report=dict(scope='official OpenWrt 21.02.7 x86 lab only; not vendor 4.11.0 SDK',
                downloaded_at_utc=datetime.now(timezone.utc).isoformat(),requested=REQUESTED,
                indices=indices,packages=artifacts,satisfied_by_installed_image=satisfied,bytes=total,guest_usign_verification_required=True)
    (cache/'manifest.json').write_text(json.dumps(report,indent=2))
    print('LAB-FEEDS-READY '+str(len(artifacts))+' packages; '+str(total)+' bytes',flush=True)


if __name__=='__main__':main()
