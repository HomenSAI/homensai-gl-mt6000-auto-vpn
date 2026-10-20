"""Read-only upstream SDK evidence consistency check; never certifies vendor/device support.

The evidence manifest is an index of local files, not an attestation of their origin.
No commands, downloads, extraction or installation are performed by this checker.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import tarfile
from urllib.parse import urlparse

ROLES={'sdk_archive','supplier_checksums','config','feeds','toolchain','licence',
       'build_log_first','build_log_second','package_first','package_second','reference_package'}
LIMIT=256*1024*1024
SDK_WRAPPERS={
    'postinst':b'#!/bin/sh\n[ "${IPKG_NO_SCRIPT}" = "1" ] && exit 0\n[ -s ${IPKG_INSTROOT}/lib/functions.sh ] || exit 0\n. ${IPKG_INSTROOT}/lib/functions.sh\ndefault_postinst $0 $@\n',
    'prerm':b'#!/bin/sh\n[ -s ${IPKG_INSTROOT}/lib/functions.sh ] || exit 0\n. ${IPKG_INSTROOT}/lib/functions.sh\ndefault_prerm $0 $@\n'}


def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def checked_path(base,name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name:
        raise ValueError('SDK-EVIDENCE-PATH')
    part=PurePosixPath(name)
    if part.is_absolute() or PureWindowsPath(name).is_absolute() or '..' in part.parts:
        raise ValueError('SDK-EVIDENCE-PATH')
    path=(base/name).resolve()
    if base not in path.parents or not path.is_file() or path.stat().st_size>LIMIT:
        raise ValueError('SDK-EVIDENCE-PATH-OR-SIZE')
    return path


def tar_files(data):
    """Inspect bounded archives without ever extracting their paths to disk."""
    result={};seen=set();total=0
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as archive:
        for member in archive:
            name=member.name
            while name.startswith('./'):name=name[2:]
            if name in ('','.'):continue
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or name in seen:
                raise ValueError('SDK-PACKAGE-PATH-OR-DUPLICATE')
            seen.add(name)
            if len(seen)>20000:raise ValueError('SDK-PACKAGE-MEMBER-LIMIT')
            if member.isdir():continue
            if not member.isfile():raise ValueError('SDK-PACKAGE-LINK-OR-SPECIAL')
            total+=member.size
            if member.size<0 or total>LIMIT:raise ValueError('SDK-PACKAGE-SIZE')
            result[name]=(member.mode & 0o7777,archive.extractfile(member).read())
    return result


def package(path):
    if path.stat().st_size>16*1024*1024:raise ValueError('SDK-PACKAGE-FILE-SIZE')
    outer=tar_files(path.read_bytes())
    if set(outer)!={'debian-binary','control.tar.gz','data.tar.gz'} or outer['debian-binary'][1]!=b'2.0\n':
        raise ValueError('SDK-PACKAGE-ENVELOPE')
    controls=tar_files(outer['control.tar.gz'][1]);payload=tar_files(outer['data.tar.gz'][1])
    if 'control' not in controls:raise ValueError('SDK-PACKAGE-CONTROL')
    fields={}
    for line in controls.pop('control')[1].decode('utf-8').splitlines():
        if not line or line[0].isspace():continue
        key,separator,value=line.partition(':')
        if not separator or key in fields:raise ValueError('SDK-PACKAGE-CONTROL')
        fields[key]=value.strip()
    for key in ('Package','Version','Architecture','Depends'):
        if not fields.get(key):raise ValueError('SDK-PACKAGE-CONTROL-MISSING')
    return fields,controls,payload


def compare_packages(candidate,reference):
    actual,actual_control,actual_payload=package(candidate)
    expected,expected_control,expected_payload=package(reference)
    if actual.get('Package')!='homensai-auto-vpn':raise ValueError('SDK-PACKAGE-NAME')
    for key in ('Package','Version','Architecture'):
        if actual[key]!=expected[key]:raise ValueError('SDK-PACKAGE-METADATA:'+key)
    # Dependency order may differ; dependency expressions, including versions, may not.
    deps=lambda value:sorted(x.strip() for x in value.split(',') if x.strip())
    expected_dependencies=deps(expected['Depends']);allowed=[expected_dependencies]
    if 'libc' not in expected_dependencies:allowed.append(sorted(expected_dependencies+['libc']))
    if deps(actual['Depends']) not in allowed:
        raise ValueError('SDK-PACKAGE-DEPENDENCIES')
    if any(key.endswith('-pkg') for key in actual_control):
        # Exact wrappers observed in the pinned 21.02.7 SDK. Never strip arbitrary code.
        for name,wrapper in SDK_WRAPPERS.items():
            if actual_control.get(name)!=(0o755,wrapper) or name+'-pkg' not in actual_control:
                raise ValueError('SDK-PACKAGE-UNKNOWN-WRAPPER')
            actual_control[name]=actual_control.pop(name+'-pkg')
    if actual_control!=expected_control:raise ValueError('SDK-PACKAGE-CONTROL-SCRIPTS-OR-MODES')
    if actual_payload!=expected_payload:raise ValueError('SDK-PACKAGE-PAYLOAD-OR-MODES')
    return len(actual_payload)


def verify(data,base):
    base=Path(base).resolve()
    if not isinstance(data,dict) or data.get('schema')!=1:raise ValueError('SDK-EVIDENCE-SCHEMA')
    if data.get('sdk_scope')!='upstream':raise ValueError('SDK-VENDOR-CLAIM-REFUSED')
    if not re.fullmatch('[a-f0-9]{40}',data.get('source_commit','')):raise ValueError('SDK-SOURCE-COMMIT')
    supplier=urlparse(data.get('supplier_url',''))
    if supplier.scheme!='https' or supplier.netloc!='downloads.openwrt.org' or not re.fullmatch(
            r'/releases/[0-9.]+/targets/[a-z0-9_-]+/[a-z0-9_-]+/openwrt-sdk-[A-Za-z0-9_.-]+\.tar\.(?:xz|zst)',supplier.path):
        raise ValueError('SDK-UPSTREAM-SUPPLIER')
    if supplier.query or supplier.fragment:raise ValueError('SDK-UPSTREAM-SUPPLIER')
    files=data.get('files',{})
    if not isinstance(files,dict) or set(files)!=ROLES:raise ValueError('SDK-EVIDENCE-INCOMPLETE')
    paths={};hashes={}
    for role,entry in files.items():
        if not isinstance(entry,dict) or not re.fullmatch('[a-f0-9]{64}',entry.get('sha256','')):
            raise ValueError('SDK-EVIDENCE-HASH-FORMAT')
        path=checked_path(base,entry.get('path'));digest=sha256(path)
        if digest!=entry['sha256']:raise ValueError('SDK-EVIDENCE-HASH-MISMATCH:'+role)
        if not path.stat().st_size:raise ValueError('SDK-EVIDENCE-EMPTY:'+role)
        paths[role]=path;hashes[role]=digest
    if len(set(paths.values()))!=len(paths):raise ValueError('SDK-EVIDENCE-REUSED-FILE')
    sdk_name=PurePosixPath(supplier.path).name
    checksums=paths['supplier_checksums'].read_text(encoding='utf-8')
    matches=re.findall(r'^([a-f0-9]{64}) [ *]'+re.escape(sdk_name)+r'$',checksums,re.M)
    if matches!=[hashes['sdk_archive']]:raise ValueError('SDK-SUPPLIER-CHECKSUM-MISMATCH')
    if hashes['package_first']!=hashes['package_second']:raise ValueError('SDK-PACKAGE-NOT-REPRODUCIBLE')
    count=compare_packages(paths['package_first'],paths['reference_package'])
    # The checker verifies actual configuration/locked inputs exist, not just a PASS label.
    config=paths['config'].read_text(encoding='utf-8')
    if not re.search(r'^CONFIG_PACKAGE_homensai-auto-vpn=[ym]$',config,re.M):raise ValueError('SDK-PACKAGE-NOT-SELECTED')
    if not re.search(r'^CONFIG_TARGET_[A-Za-z0-9_]+=y$',config,re.M):raise ValueError('SDK-TARGET-NOT-RECORDED')
    feeds=paths['feeds'].read_text(encoding='utf-8')
    feed_rows=[line for line in feeds.splitlines() if line and not line.startswith('#')]
    if not feed_rows or any(not re.fullmatch(r'src-git(?:-full)? [a-z0-9_-]+ https://[^ ]+[;^][a-f0-9]{40}',line) for line in feed_rows):
        raise ValueError('SDK-FEEDS-NOT-IMMUTABLE')
    return {'result':'EVIDENCE-CONSISTENT','scope':'upstream SDK package evidence only; build execution and supplier authenticity require independent review',
            'baseline_source_commit':data['source_commit'],
            'source_linkage':'exact source-tree relation requires the separate snapshot/attempt collector',
            'files_verified':len(paths),'payload_files_compared':count,
            'sha256':hashes,'vendor_firmware_match':False,'device_acceptance':False,
            'permitted_sdk_differences':['implicit libc dependency','exact pinned default_postinst/default_prerm wrappers with identical package hooks'],
            'installation_authorized':False,'native_adapter_certified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('manifest',type=Path);args=parser.parse_args()
    try:
        if args.manifest.stat().st_size>65536:raise ValueError('SDK-MANIFEST-SIZE')
        result=verify(json.loads(args.manifest.read_text(encoding='utf-8')),args.manifest.parent)
        print(json.dumps(result,indent=2,sort_keys=True))
    except (OSError,ValueError,TypeError,KeyError,tarfile.TarError,UnicodeError) as error:
        print(json.dumps({'result':'BLOCKED','reason':str(error),'vendor_firmware_match':False,'installation_authorized':False}))
        raise SystemExit(1)
