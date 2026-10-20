"""Run only a generic, pinned upstream SDK experiment inside an isolated Linux container.

Inputs are private read-only archives. The work/output directories must be new;
no removal, dependency downloads, router access or vendor certification occurs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

SDK_SHA='21c75e4c5a429da487f8a885555cb49eee80cfc355d5dbe35d2b3ae05324a09d'


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--source-commit',required=True);parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--reuse-work',action='store_true');parser.add_argument('--feeds-lock',type=Path)
    parser.add_argument('--makefile-overlay',type=Path);parser.add_argument('--configure-only',action='store_true')
    parser.add_argument('--payload-only',action='store_true',help='Build the SDK child package target only; excludes recursive runtime-dependency builds')
    parser.add_argument('--replace-package-source',action='store_true',help='Preserve the previous isolated SDK package tree outside package/ and stage a new immutable snapshot')
    parser.add_argument('--source-strip-components',type=int,choices=(0,1),default=0,help='Use 0 for export-sdk-source.py rewritten exports; 1 only for raw root-context router/ archives')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if os.name!='posix' or os.getuid()==0:raise ValueError('SDK-REQUIRES-NONROOT-LINUX')
    if digest(args.sdk)!=SDK_SHA or digest(args.source)!=args.source_sha256:raise ValueError('SDK-INPUT-HASH')
    if (args.work.exists() and not args.reuse_work) or args.output.exists() or ' ' in str(args.work):raise ValueError('SDK-NEW-DIRECTORIES-REQUIRED')
    identity={'sdk':SDK_SHA,'source':args.source_sha256,'commit':args.source_commit}
    if args.source_strip_components:identity['strip_components']=args.source_strip_components
    extract_source=['tar','-xf',str(args.source),'--strip-components='+str(args.source_strip_components)]
    if args.reuse_work:
        previous=json.loads((args.work/'homensai-inputs.json').read_text())
        if args.replace_package_source:
            if previous.get('sdk')!=SDK_SHA:raise ValueError('SDK-WORK-IDENTITY')
            old=args.work/('preserved-package-'+previous['source'][:12])
            if old.exists():raise ValueError('SDK-PRESERVED-SOURCE-EXISTS')
            (args.work/'package/homensai-auto-vpn').rename(old)
            package=args.work/'package/homensai-auto-vpn';package.mkdir()
            subprocess.run(extract_source+['-C',str(package)],check=True,timeout=60)
            (args.work/'homensai-inputs.json').write_text(json.dumps(identity))
        elif previous!=identity:raise ValueError('SDK-WORK-IDENTITY')
    else:
        args.work.mkdir(parents=True)
        subprocess.run(['tar','-xJf',str(args.sdk),'--strip-components=1','-C',str(args.work)],check=True,timeout=300)
        package=args.work/'package/homensai-auto-vpn';package.mkdir()
        subprocess.run(extract_source+['-C',str(package)],check=True,timeout=60)
        (args.work/'homensai-inputs.json').write_text(json.dumps(identity))
    args.output.mkdir(parents=True)
    package=args.work/'package/homensai-auto-vpn'
    if args.makefile_overlay:shutil.copyfile(args.makefile_overlay,package/'Makefile')
    steps=[]
    if args.feeds_lock:
        lock=json.loads(args.feeds_lock.read_text(encoding='utf-8-sig'));feed_lines=[]
        for feed in lock:
            archive=args.feeds_lock.parent/('feed-'+feed['name']+'.tar.gz')
            if digest(archive)!=feed['sha256']:raise ValueError('SDK-FEED-HASH')
            target=args.work/('locked-feed-'+feed['name']);target.mkdir()
            subprocess.run(['tar','-xzf',str(archive),'--strip-components=1','-C',str(target)],check=True,timeout=120)
            feed_lines.append('src-link '+feed['name']+' '+str(target/('package' if feed['name']=='base' else '')))
        (args.work/'feeds.conf').write_text('\n'.join(feed_lines)+'\n')
        steps.extend([('feed-index',['./scripts/feeds','update','-a']),
                      ('feed-install',['./scripts/feeds','install','python3','lua','lua-cjson','libuci-lua','ip-full','ubus','rpcd','luci-base','ca-bundle'])])
    config=args.work/'.config'
    # SDK defaults select every registered package; explicitly constrain this experiment.
    config.write_text('CONFIG_TARGET_x86=y\nCONFIG_TARGET_x86_64=y\n# CONFIG_ALL is not set\n'
                      '# CONFIG_ALL_NONSHARED is not set\n# CONFIG_ALL_KMODS is not set\n'
                      'CONFIG_PACKAGE_homensai-auto-vpn=m\n')
    record={'scope':'upstream OpenWrt21.02.7 x86/64 SDK experiment; not GL.iNet vendor build',
            'baseline_source_commit':args.source_commit,'source_archive_sha256':args.source_sha256,
            'actual_package_makefile_sha256':digest(package/'Makefile'),
            'sdk_archive_sha256':SDK_SHA,'uid':os.getuid(),'steps':[],
            'vendor_firmware_match':False,'installation_authorized':False,'hardware_acceptance':False}
    steps.append(('defconfig',['make','defconfig']))
    if not args.configure_only:
        if args.payload_only:
            command=['make','-j1','-C','package/homensai-auto-vpn','TOPDIR='+str(args.work),'V=s']
            steps.extend([('clean',command+['clean']),('compile',command+['compile'])])
            record['scope']+='; direct SDK child package target only, recursive runtime dependency rebuild excluded'
        else:
            steps.extend([('clean',['make','-j1','package/homensai-auto-vpn/clean','V=s']),
                          ('compile',['make','-j1','package/homensai-auto-vpn/compile','V=s'])])
    for label,command in steps:
        started=time.monotonic();log=args.output/(label+'.log')
        with log.open('wb') as stream:
            try:
                result=subprocess.run(command,cwd=args.work,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=900)
                exit_code=result.returncode
            except subprocess.TimeoutExpired:exit_code=124
        record['steps'].append({'step':label,'command':command,'exit_code':exit_code,
                                'elapsed_s':round(time.monotonic()-started,3),'log_sha256':digest(log)})
        if exit_code:break
    record['result']=('CONFIGURATION-COMMANDS-COMPLETED' if args.configure_only else 'BUILD-COMMANDS-COMPLETED') if len(record['steps'])==len(steps) and all(x['exit_code']==0 for x in record['steps']) else 'BLOCKED'
    if args.payload_only and record['result']=='BUILD-COMMANDS-COMPLETED':record['result']='PAYLOAD-TARGET-COMMANDS-COMPLETED'
    makefile=(package/'Makefile').read_text()
    version=re.search(r'^PKG_VERSION:=(.+)$',makefile,re.M).group(1)
    revision=re.search(r'^PKG_RELEASE:=(.+)$',makefile,re.M).group(1)
    expected_name='homensai-auto-vpn_'+version+'-'+revision+'_all.ipk'
    artifacts=list(args.work.glob('bin/**/'+expected_name)) if not args.configure_only and record['result']!='BLOCKED' else []
    if not args.configure_only and record['result']!='BLOCKED' and len(artifacts)!=1:
        record.update(result='BLOCKED',packaging_error='SDK-EXPECTED-ALL-ARTIFACT-MISSING-OR-AMBIGUOUS')
    for artifact in artifacts:
        shutil.copyfile(artifact,args.output/artifact.name)
        record.setdefault('artifacts',[]).append({'name':artifact.name,'sha256':digest(artifact),'bytes':artifact.stat().st_size})
    for name in ('.config','feeds.conf.default','feeds.conf'):
        if (args.work/name).is_file():shutil.copyfile(args.work/name,args.output/(name.lstrip('.')+'.txt'))
    (args.output/'attempt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,sort_keys=True))
    if record['result']=='BLOCKED':raise SystemExit(1)


if __name__=='__main__':main()
