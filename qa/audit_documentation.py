"""Offline Markdown inventory, local-target and current-version agreement checks."""
import json,os,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def audit():
 files=[]
 for base,dirs,names in os.walk(ROOT):
  dirs[:]=[d for d in dirs if d not in {'.git','private','node_modules','.venv','__pycache__','dist','build'}]
  files.extend(Path(base)/n for n in names if n.endswith('.md'))
 missing=[];rows=[]
 for p in sorted(files):
  name=p.relative_to(ROOT).as_posix();text=p.read_text(encoding='utf-8')
  rows.append({'path':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  for _,target in re.findall(r'\[([^\]]*)\]\(([^)]+)\)',text):
   target=target.strip().split(' "')[0].strip('<>').split('#')[0]
   if not target or re.match(r'^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|/)',target):continue
   if not (p.parent/target).exists():missing.append({'document':name,'target':target})
 app=json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']
 for lang in ('ru','en'):
  text=(ROOT/('docs/CURRENT-STATE.'+lang+'.md')).read_text(encoding='utf-8')
  assert app['version'] in text,'CURRENT-GUIDE-VERSION'
  assert '0.9.0' in text and 'alpha9' in text.lower() and 'alpha10' in text.lower(),'EVIDENCE-SCOPES'
 assert not missing,'BROKEN-LOCAL-LINKS:'+str(missing)
 return {'result':'PASS','version':app['version'],'markdown_files':len(rows),'missing_local_targets':missing,'files':rows,'scope':'offline target existence and version/scope agreement; not external URL or native visual acceptance'}
if __name__=='__main__':print(json.dumps(audit(),ensure_ascii=False))
