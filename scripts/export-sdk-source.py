"""Export router sources with repository-root Git attributes intact.

Never use COMMIT:router as the archive tree: that discards root .gitattributes
and can apply core.autocrlf to byte-pinned style assets on Windows.
"""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile


def create_snapshot(repo,commit,target):
    repo=Path(repo).resolve();target=Path(target).resolve();metadata=target.with_suffix('.json')
    if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('SDK-FULL-COMMIT-REQUIRED')
    if target.exists() or metadata.exists():raise ValueError('SDK-SNAPSHOT-EXISTS')
    resolved=subprocess.check_output(['git','rev-parse',commit+'^{commit}'],cwd=repo,text=True,timeout=30).strip()
    if resolved!=commit:raise ValueError('SDK-COMMIT-MISMATCH')
    # Keep the commit/repository root as the tree context; restrict only the pathspec.
    raw=subprocess.check_output(['git','archive','--format=tar',commit,'--','router'],cwd=repo,timeout=120)
    files={}
    # Rewrite only the TAR member prefix in memory. Do not checkout/extract to a host directory.
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive, tarfile.open(target,mode='x') as output:
        for member in archive:
            if member.isdir():continue
            if not member.isfile() or not member.name.startswith('router/'):
                raise ValueError('SDK-SOURCE-UNSUPPORTED-ENTRY')
            name=member.name.removeprefix('router/')
            if '..' in Path(name).parts or name in files:raise ValueError('SDK-SOURCE-PATH')
            data=archive.extractfile(member).read();files[name]=hashlib.sha256(data).hexdigest()
            rewritten=copy.copy(member);rewritten.name=name;rewritten.pax_headers=dict(member.pax_headers)
            rewritten.pax_headers.pop('path',None)
            output.addfile(rewritten,io.BytesIO(data))
    if not files:raise ValueError('SDK-SOURCE-EMPTY')
    record={'scope':'exact committed router export with repository-root attributes',
            'source_kind':'committed-tree','baseline_commit':commit,'archive':target.name,
            'source_strip_components':0,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'files':files}
    with metadata.open('x',encoding='utf-8') as stream:stream.write(json.dumps(record,indent=2)+'\n')
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True)
    parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();record=create_snapshot(args.repo,args.commit,args.archive)
    print(json.dumps({key:value for key,value in record.items() if key!='files'},sort_keys=True))
