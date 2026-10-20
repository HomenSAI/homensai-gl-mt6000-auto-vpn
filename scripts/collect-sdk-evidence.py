"""Collect a same-snapshot SDK payload comparison inside the isolated Linux builder.

Run only after two bounded payload builds and a custom reference. No builds,
downloads or router operations occur here; compiler --version is the only command.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

spec=importlib.util.spec_from_file_location('sdk_evidence',Path(__file__).with_name('check-sdk-evidence.py'))
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True);parser.add_argument('--snapshot',required=True)
    parser.add_argument('--first',required=True);parser.add_argument('--second',required=True)
    parser.add_argument('--reference',required=True);args=parser.parse_args()
    base=args.base.resolve();snapshot=json.loads(check.checked_path(base,args.snapshot).read_text())
    source=check.checked_path(base,snapshot['archive'])
    if check.sha256(source)!=snapshot['sha256']:raise ValueError('SDK-SOURCE-ARCHIVE-CHANGED')
    package=args.work/'package/homensai-auto-vpn'
    for name,digest in snapshot['files'].items():
        if check.sha256(check.checked_path(package.resolve(),name))!=digest:raise ValueError('SDK-PACKAGE-SOURCE-CHANGED:'+name)
    first=json.loads(check.checked_path(base,args.first+'/attempt.json').read_text())
    second=json.loads(check.checked_path(base,args.second+'/attempt.json').read_text())
    for record in (first,second):
        if record.get('result')!='PAYLOAD-TARGET-COMMANDS-COMPLETED' or record.get('source_archive_sha256')!=snapshot['sha256'] or record.get('uid')!=10001:
            raise ValueError('SDK-ATTEMPT-SOURCE-OR-STATUS')
        if record.get('actual_package_makefile_sha256')!=snapshot['files']['Makefile']:raise ValueError('SDK-ATTEMPT-MAKEFILE')
        for step in record['steps']:
            log=check.checked_path(base,(args.first if record is first else args.second)+'/'+step['step']+'.log')
            if step['exit_code']!=0 or check.sha256(log)!=step['log_sha256']:raise ValueError('SDK-ATTEMPT-LOG')
    artifacts=first['artifacts']
    if len(artifacts)!=1 or len(second['artifacts'])!=1 or artifacts[0]!=second['artifacts'][0]:raise ValueError('SDK-ATTEMPT-REPRODUCIBILITY')
    name=artifacts[0]['name']
    if not name.endswith('_all.ipk'):raise ValueError('SDK-ATTEMPT-ARCHITECTURE')
    compiler=next(args.work.glob('staging_dir/toolchain-*/bin/*-gcc'))
    toolchain=subprocess.check_output([str(compiler),'--version'],text=True,timeout=15)
    (base/'sdk-toolchain.txt').write_text(toolchain)
    licences=sorted(p for p in (args.work/'LICENSES').rglob('*') if p.is_file())
    if not licences:raise ValueError('SDK-LICENCE-NOT-FOUND')
    (base/'sdk-licences.txt').write_text('\n'.join(p.name+'\n'+p.read_text(errors='strict') for p in licences))
    feed_lock=json.loads((base/'feed-downloads.json').read_text(encoding='utf-8-sig'))
    (base/'feeds.lock.txt').write_text('\n'.join('src-git-full '+x['name']+' '+x['url'].replace('https://codeload.github.com/','https://github.com/').split('/tar.gz/')[0]+'.git^'+x['revision'] for x in feed_lock)+'\n')
    role_paths={'sdk_archive':'openwrt-sdk-21.02.7-x86-64_gcc-8.4.0_musl.Linux-x86_64.tar.xz',
                'supplier_checksums':'sha256sums','config':args.first+'/config.txt','feeds':'feeds.lock.txt',
                'toolchain':'sdk-toolchain.txt','licence':'sdk-licences.txt',
                'build_log_first':args.first+'/compile.log','build_log_second':args.second+'/compile.log',
                'package_first':args.first+'/'+name,'package_second':args.second+'/'+name,'reference_package':args.reference+'/'+name}
    source_kind='exact committed router tree' if snapshot.get('source_kind')=='committed-tree' else 'frozen working snapshot; baseline commit is not exact tree identity'
    data={'schema':1,'sdk_scope':'upstream','source_commit':snapshot['baseline_commit'],
          'source_kind':source_kind,
          'source_archive_sha256':snapshot['sha256'],'source_files_verified':len(snapshot['files']),
          'supplier_url':'https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/'+role_paths['sdk_archive'],
          'files':{role:{'path':path,'sha256':check.sha256(check.checked_path(base,path))} for role,path in role_paths.items()}}
    result=check.verify(data,base)
    result.update(source_kind=data['source_kind'],source_archive_sha256=snapshot['sha256'],
                  source_files_verified=len(snapshot['files']),build_scope='direct SDK child payload target; excludes recursive runtime dependency compilation')
    (base/'sdk-evidence.json').write_text(json.dumps(data,indent=2)+'\n')
    (base/'sdk-evidence-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
