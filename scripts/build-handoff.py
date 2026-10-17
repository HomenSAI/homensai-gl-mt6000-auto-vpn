"""Build a context-only handoff archive from exact committed public allowlisted files."""
import argparse,hashlib,io,json,re,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def build(source,out):
    if not re.fullmatch('[a-f0-9]{40}',source):raise ValueError('HANDOFF-SOURCE')
    out=out.resolve()
    if not out.is_relative_to((ROOT/'private').resolve()):raise ValueError('HANDOFF-PRIVATE-OUTPUT')
    manifest=git('show',source+':VERSION.json');data=json.loads(manifest);version=data['handoff']['version']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version) or data['handoff']['release_tag']!='handoff-v'+version:raise ValueError('HANDOFF-VERSION')
    names=['CLAUDE.md','VERSION.json','docs/VERSIONING.md','releases/handoff-v'+version+'.md','qa/alpha0802-endurance-stopped.json']
    entries=git('ls-tree','-r',source,'--','.claude/handoff').decode().splitlines()
    for line in entries:
        mode,kind,object_and_name=line.split(' ',2);_,name=object_and_name.split('\t',1)
        if mode!='100644' or kind!='blob' or not name.startswith('.claude/handoff/') or Path(name).suffix not in ('.md','.json'):raise ValueError('HANDOFF-ENTRY')
        names.append(name)
    prefix='homensai-gl-mt6000-auto-vpn-claude-handoff-'+version+'/'
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(set(names)):
            if '..' in Path(name).parts or Path(name).is_absolute():raise ValueError('HANDOFF-PATH')
            payload=git('show',source+':'+name)
            info=zipfile.ZipInfo(prefix+name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=3;info.external_attr=0o100644<<16
            archive.writestr(info,payload)
        info=zipfile.ZipInfo(prefix+'BUNDLE-README.md',date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=3;info.external_attr=0o100644<<16
        archive.writestr(info,('Context-only Claude review bundle '+version+'. This is not a router package and does not include complete application source. Clone HomenSAI/homensai-gl-mt6000-auto-vpn at tag handoff-v'+version+' to audit code and referenced receipts. No test/deployment authorization is granted.\n').encode())
    out.mkdir(parents=True,exist_ok=True);name=prefix[:-1]+'.zip';artifact=out/name;artifact.write_bytes(raw.getvalue());(out/'VERSION.json').write_bytes(manifest)
    hashes={name:hashlib.sha256(artifact.read_bytes()).hexdigest(),'VERSION.json':hashlib.sha256(manifest).hexdigest()}
    (out/'SHA256SUMS.txt').write_bytes(''.join(sha+'  '+name+'\n' for name,sha in hashes.items()).encode())
    print(json.dumps({'source':source,'handoff':version,'zip':str(artifact),'sha256':hashes[name],'bytes':artifact.stat().st_size,'members':len(set(names))+1,'application_package_included':False},sort_keys=True))
    return artifact

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.source,a.out)
