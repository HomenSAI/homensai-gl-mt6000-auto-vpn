"""Read-only ref-by-ref reconciliation proposal. Never fetches or pushes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def collision_plan(refs):
    rows=[]
    prefix='refs/homensai-canonical/tags/'
    for ref,sha in sorted(refs.items()):
        if not ref.startswith(prefix):continue
        name=ref[len(prefix):];other=refs.get('refs/tags/'+name)
        rows.append(dict(tag=name,canonical_object=sha,existing_tag_object=other,
                         collision=other is not None and sha!=other,
                         preserve_canonical_as='refs/archive/gitea-native/tags/'+name,
                         preserve_existing_as='refs/archive/github-legacy/tags/'+name if other else None,
                         proposed_distinct_public_tag='native/'+name if other and sha!=other else name))
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--git',default=shutil.which('git') or 'git')
    args=parser.parse_args()
    def git(*items,check=True):
        return subprocess.run([args.git,'-C',str(args.repo),*items],capture_output=True,text=True,check=check)
    rows=git('for-each-ref','--format=%(refname) %(objectname)').stdout.splitlines()
    refs=dict(row.split(' ',1) for row in rows)
    pairs=[('refs/remotes/origin/main','refs/heads/feature/local-completion-alpha6'),
           ('refs/remotes/gitea/main','refs/heads/feature/local-completion-alpha6'),
           ('refs/heads/main','refs/remotes/origin/main')]
    relations=[]
    for left,right in pairs:
        if left not in refs or right not in refs:continue
        result=git('merge-base','--all',left,right,check=False)
        if result.returncode not in (0,1):raise RuntimeError('REF-RELATION-UNAVAILABLE')
        relations.append(dict(left=left,right=right,left_object=refs[left],right_object=refs[right],
                              common_ancestors=result.stdout.splitlines(),unrelated=result.returncode==1))
    assets=[]
    for path in sorted((args.repo/'releases').glob('*.ipk')):
        assets.append(dict(name=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    plan=collision_plan(refs)
    print(json.dumps(dict(generated_at=datetime.now(timezone.utc).isoformat(),
        scope='local stored refs only; remote freshness and release metadata not asserted',
        changes_executed=False,source_commit=git('rev-parse','HEAD').stdout.strip(),
        shallow=git('rev-parse','--is-shallow-repository').stdout.strip()=='true',
        refs=refs,relations=relations,tags=plan,collision_count=sum(r['collision'] for r in plan),assets=assets,
        gates=['Verify fresh remote refs and release metadata before approved migration',
               'Audit all reachable history objects for secrets before public push',
               'Create and verify recoverable bundles/dumps; retain original refs and immutable tags',
               'Review tree merge and both histories; never force/mirror/delete/tag-overwrite',
               'Public GitHub write and protected-main integration need explicit approval'],
        metadata_steps=['Retain existing public release/tag objects unchanged',
                        'Map native releases to distinct proposed tags where collisions exist',
                        'Copy only reviewed English notes and version-matched audited assets',
                        'Verify asset SHA256 against source and downloaded destination',
                        'Keep prerelease/experimental and physical/virtual acceptance limits explicit'],
        rollback='No writes in this plan. For any later approved migration restore only newly created refs/assets under a separately reviewed rollback; never delete originals.'),indent=2))


if __name__=='__main__':main()
