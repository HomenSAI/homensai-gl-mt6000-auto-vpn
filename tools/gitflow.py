#!/usr/bin/env python3
"""Local-first Git workflow. Stdlib only; no force, mirror, pruning or tag rewrites."""
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import subprocess
import sys
import tempfile
import time
import uuid

class FlowError(Exception):
    def __init__(self,code):self.code=code;super().__init__(code)


def execute(args,cwd=None,check=True,input=None,env=None):
    environment=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never',LC_ALL='C')
    if env:environment.update(env)
    result=subprocess.run(args,cwd=cwd,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment,timeout=120)
    if check and result.returncode:raise FlowError('COMMAND-FAILED')
    return result


def safe_url(value):
    if not value or any(c in value for c in ('\n','\r','\0')):raise FlowError('REMOTE-URL-INVALID')
    if re.match(r'https?://[^/]*@',value):raise FlowError('REMOTE-CREDENTIALS-FORBIDDEN')
    return value


def safe_path(value):
    path=PurePosixPath(value.replace('\\','/'))
    if path.is_absolute() or not path.parts or any(part in ('..','.git') for part in path.parts) or ':' in value or '\0' in value:raise FlowError('PATH-INVALID')
    return path.as_posix()


def overlaps(a,b):
    a=a.lower().rstrip('/');b=b.lower().rstrip('/')
    return a==b or a.startswith(b+'/') or b.startswith(a+'/')


@contextmanager
def temporary(root):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    holder=tempfile.TemporaryDirectory(prefix='gitflow-',dir=str(root));path=Path(holder.name).resolve()
    if os.path.commonpath([str(root),str(path)])!=str(root):raise FlowError('TEMP-PATH-INVALID')
    try:yield path
    finally:
        if os.path.commonpath([str(root),str(path)])==str(root):holder.cleanup()


class Repo:
    def __init__(self,path,config_path=None):
        self.path=Path(path).resolve()
        self.common=Path(self.git('rev-parse','--git-common-dir').strip())
        if not self.common.is_absolute():self.common=(self.path/self.common).resolve()
        self.state=self.common/'gitflow';self.state.mkdir(mode=0o700,parents=True,exist_ok=True)
        config=Path(config_path).resolve() if config_path else self.path/'.gitflow.json'
        if not config.is_file():raise FlowError('CONFIG-MISSING')
        self.config=json.loads(config.read_text(encoding='utf-8-sig'))
        ssh=self.git('config','--get','core.sshCommand',check=False)
        self.transport={'GIT_SSH_COMMAND':ssh.stdout.decode().strip()} if ssh.returncode==0 else {}
    def run(self,args,**kwargs):
        environment=dict(getattr(self,'transport',{}));environment.update(kwargs.pop('env',{}) or {})
        return execute(args,env=environment,**kwargs)
    def git(self,*args,check=True,input=None):
        result=self.run(['git','-C',str(self.path),*args],check=check,input=input)
        return result.stdout.decode().strip() if check else result
    def remote(self,kind):
        name=self.config[kind]['remote'];url=safe_url(self.git('remote','get-url',name))
        if url not in self.config[kind]['urls']:raise FlowError('REMOTE-IDENTITY-MISMATCH')
        return name,url
    def branch(self):
        value=self.git('symbolic-ref','--quiet','--short','HEAD',check=False)
        if value.returncode:raise FlowError('DETACHED-HEAD')
        return value.stdout.decode().strip()
    def clean_operation(self):
        for marker in ('MERGE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','rebase-apply','rebase-merge'):
            path=Path(self.git('rev-parse','--git-path',marker))
            if not path.is_absolute():path=self.path/path
            if path.exists():raise FlowError('GIT-OPERATION-IN-PROGRESS')
    def remote_refs(self,url):
        result=self.git('ls-remote','--heads','--tags',safe_url(url),check=False)
        if result.returncode:raise FlowError('REMOTE-UNAVAILABLE')
        return {line.split('\t')[1]:line.split('\t')[0] for line in result.stdout.decode().splitlines() if '\t' in line and not line.endswith('^{}')}
    def audit(self):
        result={'branch':self.branch(),'head':self.git('rev-parse','HEAD'),'commits':int(self.git('rev-list','--all','--count')),
                'worktrees':len(self.git('worktree','list','--porcelain').split('worktree '))-1,'status_entries':len(self.git('status','--porcelain=v1').splitlines()),'remotes':{}}
        for kind in ('primary','secondary'):
            name,url=self.remote(kind)
            try:refs=self.remote_refs(url);result['remotes'][kind]={'name':name,'reachable':True,'heads':sum(k.startswith('refs/heads/') for k in refs),'tags':sum(k.startswith('refs/tags/') for k in refs)}
            except FlowError:result['remotes'][kind]={'name':name,'reachable':False}
        return result
    def write_receipt(self,kind,data):
        path=self.state/(kind+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]+'.json')
        path.write_text(json.dumps(data,indent=2)+'\n');return data
    def checks(self):
        commands=list(self.config['checks'])
        for relative,command in self.config.get('optional_checks',{}).items():
            if (self.path/relative).exists():commands.append(command)
        results=[]
        for command in commands:
            if not isinstance(command,list) or not command or any(not isinstance(x,str) for x in command):raise FlowError('CHECK-CONFIG-INVALID')
            result=self.run(command,cwd=self.path,check=False)
            results.append({'command':command,'passed':result.returncode==0})
            if result.returncode:self.write_receipt('checks',{'result':'FAIL','checks':results});raise FlowError('CHECK-FAILED')
        return self.write_receipt('checks',{'result':'PASS','checks':results})
    def privacy(self):
        names=self.git('diff','--cached','--name-only','-z').split('\0')
        patterns=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'\bghp_[A-Za-z0-9]{30,}\b',rb'\bgithub_pat_[A-Za-z0-9_]{40,}\b',rb'\b[0-9]{8,15}:[A-Za-z0-9_-]{30,100}\b']
        for name in names:
            if not name:continue
            if any(part.lower() in ('output','private','backups','.ssh','.env') for part in PurePosixPath(name).parts) or name.lower().endswith(('.key','.p12','.pfx')):raise FlowError('PRIVATE-PATH-STAGED')
            blob=self.git('show',':'+name,check=False).stdout
            if b'\0' not in blob and any(re.search(pattern,blob) for pattern in patterns):raise FlowError('SECRET-PATTERN-STAGED')
    def save_primary(self,branch=None):
        branch=branch or self.branch();self.git('check-ref-format','refs/heads/'+branch)
        name,url=self.remote('primary');head=self.git('rev-parse','refs/heads/'+branch)
        try:
            self.remote_refs(url)
            result=self.git('push',name,head+':refs/heads/'+branch,check=False)
            if result.returncode:raise FlowError('PRIMARY-PUSH-REJECTED')
            if self.remote_refs(url).get('refs/heads/'+branch)!=head:raise FlowError('PRIMARY-VERIFY-FAILED')
        except FlowError as error:
            self.write_receipt('primary',{'result':'LOCAL_ONLY','branch':branch,'head':head,'code':error.code,'remote_confirmed':False})
            raise
        return self.write_receipt('primary',{'result':'SAVED','branch':branch,'head':head})
    def finish(self,message,paths,agent,checkpoint=False):
        self.clean_operation();branch=self.branch()
        if not re.fullmatch(r'(feature|fix|hotfix|backup)/[A-Za-z0-9._/-]+',branch):raise FlowError('MAIN-DIRECT-COMMIT-FORBIDDEN')
        paths=[safe_path(value) for value in paths]
        self.require_claim(agent,branch,paths)
        staged=self.git('diff','--cached','--name-only','-z').split('\0')
        if any(name and not any(name==path or name.startswith(path.rstrip('/')+'/') for path in paths) for name in staged):raise FlowError('FOREIGN-STAGED-CHANGES')
        if not checkpoint:self.checks()
        self.git('add','--',*paths);self.privacy()
        changed=bool(self.git('diff','--cached','--name-only'))
        if changed:self.git('commit','-m',('WIP: ' if checkpoint else '')+message)
        saved=self.save_primary(branch);saved.update(created_commit=changed,verified=not checkpoint)
        try:self.coordinate(agent,'PAUSED' if checkpoint else 'DONE',message,paths,branch)
        except FlowError as error:saved['coordination_warning']=error.code
        return self.write_receipt('checkpoint' if checkpoint else 'finish',saved)
    def _coord_read(self,path,url):
        repo=path/'coord.git';self.run(['git','init','--bare','-q',str(repo)])
        refs=self.remote_refs(url);ref=self.config.get('coord_ref','refs/heads/coord/agents');head=refs.get(ref)
        base=head or refs.get('refs/heads/main')
        if not base:raise FlowError('COORD-BASE-MISSING')
        self.run(['git','--git-dir',str(repo),'fetch','--quiet','--no-tags',url,base])
        records={}
        if head:
            names=self.run(['git','--git-dir',str(repo),'ls-tree','-r','--name-only',base]).stdout.decode().splitlines()
            for name in names:
                if re.fullmatch(r'agents/[A-Za-z0-9_-]+\.json',name):records[name]=json.loads(self.run(['git','--git-dir',str(repo),'show',base+':'+name]).stdout)
        return repo,base,head,records
    def coordinate(self,agent,status,task,paths,branch=None,ttl=1800):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',agent) or status not in ('ACTIVE','PAUSED','DONE'):raise FlowError('COORD-INVALID')
        paths=[safe_path(value) for value in paths];branch=branch or self.branch()
        if not 60<=ttl<=7200 or len(task)>256:raise FlowError('COORD-INVALID')
        _,url=self.remote('primary');ref=self.config.get('coord_ref','refs/heads/coord/agents')
        for attempt in range(5):
            with temporary(self.state/'tmp') as directory:
                repo,base,head,records=self._coord_read(directory,url);now=time.time()
                if status=='ACTIVE':
                    for name,record in records.items():
                        if name=='agents/'+agent+'.json':continue
                        if record.get('status')=='ACTIVE' and record.get('expires',0)>now and any(overlaps(a,b) for a in paths for b in record.get('paths',[])):raise FlowError('COORD-PATH-BUSY')
                        if record.get('status')=='ACTIVE' and record.get('expires',0)>now and record.get('branch')==branch:raise FlowError('COORD-BRANCH-BUSY')
                value={'agent':agent,'status':status,'task':task,'paths':paths,'branch':branch,'head':self.git('rev-parse','HEAD'),'updated':now,'expires':now+ttl if status=='ACTIVE' else now}
                records['agents/'+agent+'.json']=value
                index=directory/'index';env={'GIT_INDEX_FILE':str(index)}
                self.run(['git','--git-dir',str(repo),'read-tree','--empty'],env=env)
                for name,record in sorted(records.items()):
                    payload=(json.dumps(record,sort_keys=True)+'\n').encode();blob=self.run(['git','--git-dir',str(repo),'hash-object','-w','--stdin'],input=payload).stdout.decode().strip()
                    self.run(['git','--git-dir',str(repo),'update-index','--add','--cacheinfo','100644',blob,name],env=env)
                tree=self.run(['git','--git-dir',str(repo),'write-tree'],env=env).stdout.decode().strip()
                author={'GIT_AUTHOR_NAME':'Git workflow coordinator','GIT_AUTHOR_EMAIL':'gitflow@localhost','GIT_COMMITTER_NAME':'Git workflow coordinator','GIT_COMMITTER_EMAIL':'gitflow@localhost'}
                commit=self.run(['git','--git-dir',str(repo),'commit-tree',tree,'-p',base,'-m','coord: '+agent+' '+status],env=author).stdout.decode().strip()
                result=self.run(['git','--git-dir',str(repo),'push','--quiet',url,commit+':'+ref],check=False)
                if result.returncode==0:
                    if self.remote_refs(url).get(ref)!=commit:raise FlowError('COORD-VERIFY-FAILED')
                    return {'result':status,'agent':agent,'paths':paths,'branch':branch}
            time.sleep(.05*(attempt+1))
        raise FlowError('COORD-CONTENTION')
    def coord_status(self):
        _,url=self.remote('primary')
        with temporary(self.state/'tmp') as directory:
            _,_,_,records=self._coord_read(directory,url)
        now=time.time()
        return {'agents':[dict(value,lease_live=value.get('status')=='ACTIVE' and value.get('expires',0)>now) for value in records.values()]}
    def require_claim(self,agent,branch,paths):
        records=self.coord_status()['agents'];own=next((value for value in records if value['agent']==agent),None)
        if not own or not own['lease_live'] or own['branch']!=branch or not all(any(overlaps(path,claim) and (path==claim or path.startswith(claim.rstrip('/')+'/')) for claim in own['paths']) for path in paths):raise FlowError('COORD-CLAIM-REQUIRED')
    def sync_plan(self,publish=False,authorization=None):
        _,primary=self.remote('primary');_,secondary=self.remote('secondary')
        first=self.remote_refs(primary)
        try:second=self.remote_refs(secondary)
        except FlowError:return self.write_receipt('sync',{'result':'SECONDARY-OFFLINE','primary_saved':True,'push_performed':False})
        desired={ref:sha for ref,sha in first.items() if ref.startswith('refs/tags/') or re.fullmatch(r'refs/heads/(main|(?:feature|fix|hotfix|backup)/.+)',ref)}
        problems=[];updates=[]
        with temporary(self.state/'tmp') as directory:
            bare=directory/'audit.git';self.run(['git','init','--bare','-q',str(bare)])
            for label,url,refs in (('primary',primary,desired),('secondary',secondary,second)):
                mappings=[ref+':refs/gitflow/'+label+'/'+ref[len('refs/'):] for ref in refs]
                for index in range(0,len(mappings),64):self.run(['git','--git-dir',str(bare),'fetch','--quiet','--no-tags',url,*mappings[index:index+64]])
            for ref,sha in sorted(desired.items()):
                other=second.get(ref)
                if other==sha:continue
                if other and ref.startswith('refs/tags/'):problems.append({'ref':ref,'code':'TAG-COLLISION'});continue
                if other:
                    check=self.run(['git','--git-dir',str(bare),'merge-base','--is-ancestor',other,sha],check=False)
                    if check.returncode:problems.append({'ref':ref,'code':'NON-FAST-FORWARD-OR-UNRELATED'});continue
                updates.append({'ref':ref,'sha':sha,'operation':'create' if other is None else 'fast-forward'})
            plan={'result':'BLOCKED' if problems else 'READY','updates':updates,'problems':problems,'push_performed':False,'source':'verified primary refs','coord_excluded':True}
            if publish:
                if problems:raise FlowError('SYNC-HISTORY-CONFLICT')
                if authorization is None:raise FlowError('SECONDARY-APPROVAL-REQUIRED')
                grant=json.loads(Path(authorization).read_text())
                if grant.get('secondary_url')!=secondary or grant.get('primary_url')!=primary or grant.get('expires',0)<time.time() or grant.get('allow_publish') is not True:raise FlowError('SECONDARY-APPROVAL-INVALID')
                latest=self.remote_refs(primary)
                relevant={ref:sha for ref,sha in latest.items() if ref.startswith('refs/tags/') or re.fullmatch(r'refs/heads/(main|(?:feature|fix|hotfix|backup)/.+)',ref)}
                if relevant!=desired:raise FlowError('PRIMARY-CHANGED-DURING-PLAN')
                if updates:
                    result=self.run(['git','--git-dir',str(bare),'push','--atomic',secondary,*[item['sha']+':'+item['ref'] for item in updates]],check=False)
                    if result.returncode:raise FlowError('SECONDARY-PUSH-REJECTED')
                    actual=self.remote_refs(secondary)
                    if any(actual.get(item['ref'])!=item['sha'] for item in updates):raise FlowError('SECONDARY-VERIFY-FAILED')
                    plan.update(result='SYNCED',push_performed=True)
                else:plan['result']='NO-CHANGES'
            return self.write_receipt('sync',plan)
    def merge(self,branch,agent):
        self.clean_operation()
        if self.branch()!='main' or self.git('status','--porcelain=v1'):raise FlowError('MAIN-CLEAN-CHECKOUT-REQUIRED')
        name,url=self.remote('primary');refs=self.remote_refs(url);source='refs/heads/'+branch;target=refs.get(source)
        if not target:raise FlowError('FEATURE-NOT-SAVED-IN-PRIMARY')
        self.git('fetch','--no-tags',name,source)
        if self.git('rev-parse','HEAD')!=refs.get('refs/heads/main'):raise FlowError('MAIN-NOT-PRIMARY-HEAD')
        if self.git('merge-base','--is-ancestor','HEAD',target,check=False).returncode:raise FlowError('NON-FAST-FORWARD-REVIEW-REQUIRED')
        if self.git('diff','--name-only') or self.git('diff','--cached','--name-only'):raise FlowError('MAIN-NOT-CLEAN')
        # Verify the tested commit in an isolated temporary checkout; no worktree reset.
        with temporary(self.state/'tmp') as directory:
            self.run(['git','clone','--quiet','--no-hardlinks',str(self.path),str(directory/'check')])
            self.run(['git','-C',str(directory/'check'),'checkout','--detach',target])
            checked=Repo(directory/'check');checked.checks()
        changed=self.git('diff','--name-only','HEAD',target).splitlines()
        self.require_claim(agent,'main',changed)
        self.git('merge','--ff-only',target)
        result=self.save_primary('main')
        self.coordinate(agent,'DONE','verified main integration',[],'main')
        return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',default='.');parser.add_argument('--config',help='Reviewed config for first-time integration into an older main')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('audit');commands.add_parser('check');commands.add_parser('coord-status')
    claim=commands.add_parser('claim');claim.add_argument('--agent',required=True);claim.add_argument('--task',required=True);claim.add_argument('--ttl',type=int,default=1800);claim.add_argument('paths',nargs='+')
    release=commands.add_parser('release-claim');release.add_argument('--agent',required=True);release.add_argument('--status',choices=['PAUSED','DONE'],default='DONE');release.add_argument('--task',default='complete')
    finish=commands.add_parser('finish');finish.add_argument('--agent',required=True);finish.add_argument('--message',required=True);finish.add_argument('paths',nargs='+')
    wip=commands.add_parser('checkpoint');wip.add_argument('--agent',required=True);wip.add_argument('--message',required=True);wip.add_argument('paths',nargs='+')
    save=commands.add_parser('save');save.add_argument('--branch')
    sync=commands.add_parser('sync');sync.add_argument('--publish',action='store_true');sync.add_argument('--authorization')
    merge=commands.add_parser('merge');merge.add_argument('branch');merge.add_argument('--agent',required=True)
    args=parser.parse_args();repo=Repo(args.repo,args.config)
    if args.command=='audit':result=repo.audit()
    elif args.command=='check':result=repo.checks()
    elif args.command=='coord-status':result=repo.coord_status()
    elif args.command=='claim':result=repo.coordinate(args.agent,'ACTIVE',args.task,args.paths,ttl=args.ttl)
    elif args.command=='release-claim':result=repo.coordinate(args.agent,args.status,args.task,[])
    elif args.command=='finish':result=repo.finish(args.message,args.paths,args.agent)
    elif args.command=='checkpoint':result=repo.finish(args.message,args.paths,args.agent,checkpoint=True)
    elif args.command=='save':result=repo.save_primary(args.branch)
    elif args.command=='sync':result=repo.sync_plan(args.publish,args.authorization)
    elif args.command=='merge':result=repo.merge(args.branch,args.agent)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    try:main()
    except FlowError as error:print(json.dumps({'result':'ERROR','code':error.code}));raise SystemExit(2)
    except (OSError,ValueError,subprocess.SubprocessError):print(json.dumps({'result':'ERROR','code':'WORKFLOW-SYSTEM-ERROR'}));raise SystemExit(2)
