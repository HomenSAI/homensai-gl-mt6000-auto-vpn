"""Read the complete public documentation corpus and check current generated contracts.

This is a structural/source agreement audit. It deliberately does not certify
historical claims, remote URLs, native visuals or autonomous external models.
"""
import json,os,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','private','node_modules','.venv','__pycache__','dist','build'}

def public_files(root=ROOT):
 for base,dirs,names in os.walk(root):
  dirs[:]=[d for d in dirs if d not in EXCLUDED]
  for name in names:
   p=Path(base)/name
   if p.suffix.lower()=='.md' or name.upper().startswith(('LICENSE','COPYING','NOTICE')):
    yield p

def unfenced(text):
 return re.sub(r'(?m)^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$', '', text,flags=re.S)

def local_targets(text):
 for _,target in re.findall(r'\[([^\]]*)\]\(([^)]+)\)',unfenced(text)):
  target=target.strip().split(' "')[0].strip('<>').split('#')[0]
  if target and not re.match(r'^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|/)',target):yield target

def normalized_hash(p):
 return hashlib.sha256(p.read_text(encoding='utf-8-sig').encode()).hexdigest()

def classify(p,text):
 name=p.relative_to(ROOT).as_posix()
 if p.name.upper().startswith(('LICENSE','COPYING','NOTICE','DISCLAIMER','LICENSING')):return 'preserved-legal'
 role=re.search(r'<!-- doc-role: ([^>]+) -->',text)
 if role:return role[1]
 if '<!-- documentation-context: archive -->' in text or 'current-release-context' in text:return 'historical-reference'
 if name.startswith(('.claude/handoff/','docs/handoff/')):return 'recovery-record'
 if re.search(r'2026-\d\d-\d\d|ALPHA\d|alpha\d',p.name):return 'versioned-evidence'
 return 'technical-reference'

def audit():
 missing=[];rows=[]
 for p in sorted(public_files()):
  text=p.read_text(encoding='utf-8-sig');name=p.relative_to(ROOT).as_posix()
  rows.append({'path':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':classify(p,text),'bytes':p.stat().st_size})
  for target in local_targets(text):
   if not (p.parent/target).exists():missing.append({'document':name,'target':target})
 app=json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']
 for lang in ('ru','en'):
  text=(ROOT/('docs/CURRENT-STATE.'+lang+'.md')).read_text(encoding='utf-8')
  assert app['version'] in text,'CURRENT-GUIDE-VERSION'
  for target in ('CLIENT-TRIAL.md','CURRENT-STATUS.md','HISTORY-RETENTION.md'):
   assert target in text,'CURRENT-GUIDE-SCOPE:'+target
 manifest=json.loads((ROOT/'qa/documentation-generated.json').read_text(encoding='utf-8'))
 for group in ('inputs','outputs'):
  for name,digest in manifest[group].items():assert normalized_hash(ROOT/name)==digest,'GENERATED-DOC-STALE:'+name
 assert len(manifest['outputs'])==7,'GENERATED-REFERENCE-COVERAGE'
 for lang in ('en','ru'):
  lan=(ROOT/('docs/AI-LAN.'+lang+'.md')).read_text(encoding='utf-8')
  assert '.\\client-test.ps1' in lan and '.\\start-lan-helper.ps1' in lan,'WINDOWS-PROMPT-PATH'
  assert 'CLIENT-CONTROL-PATH-MISMATCH' in lan and all(mode in lan for mode in ('SelfTest','CheckOnly','ProbeOnly')),'HELPER-MODE-SCOPE'
 assert not missing,'BROKEN-LOCAL-LINKS:'+str(missing)
 return {'result':'PASS','version':app['version'],'markdown_files':sum(r['path'].endswith('.md') for r in rows),'files_read':len(rows),'missing_local_targets':missing,'files':rows,'scope':'complete public prose/notice read, local targets and generated source agreement; historical body facts retained, not re-certified; no remote URL/native visual/external model acceptance'}
if __name__=='__main__':print(json.dumps(audit(),ensure_ascii=False))
