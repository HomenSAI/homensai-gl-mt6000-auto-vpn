"""Synchronize generated help, prompt and diagnostic references with runtime sources."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def outputs():
 p=ROOT/'router/terms_panel.inc.js';source=p.read_text(encoding='utf-8')
 block='// BEGIN GENERATED LEGAL REFERENCE\n'+'\n'.join('var TERMS_FULL_'+lang.upper()+'='+json.dumps((ROOT/filename).read_text(encoding='utf-8'),ensure_ascii=False)+';' for lang,filename in [('en','DISCLAIMER.md'),('ru','DISCLAIMER.ru.md')])+'\n// END GENERATED LEGAL REFERENCE\n'
 updated=re.sub(r'// BEGIN GENERATED LEGAL REFERENCE\n.*?// END GENERATED LEGAL REFERENCE\n',lambda _:block,source,flags=re.S) if '// BEGIN GENERATED LEGAL REFERENCE' in source else source.replace('var TERMS_POINTS=',block+'var TERMS_POINTS=')
 return p,updated

def generate(check=False):
 p,updated=outputs()
 if check:
  if p.read_text(encoding='utf-8')!=updated:raise ValueError('LEGAL-REFERENCE-STALE')
 else:p.write_text(updated,encoding='utf-8')
 proc=subprocess.run(['node',str(ROOT/'qa/export_documentation.js')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=45)
 if proc.returncode:raise ValueError('RUNTIME-DOC-EXPORT:'+proc.stderr[-900:])
 data=json.loads(proc.stdout);pending={}
 for lang,values in data['languages'].items():
  for kind,key,title,links in [('INSTALL','install','AI installation prompt','[Installation](INSTALL.'+lang+'.md) · [Current scope](CURRENT-STATUS.md)'),('LAN','lan','AI LAN helper prompt','[Modes / Режимы](LAN-HELPER.'+lang+'.md) · [Scope / Область](CLIENT-TRIAL.md)')]:
   pending[ROOT/('docs/AI-'+kind+'.'+lang+'.md')]='<!-- doc-role: current-generated-prompt -->\n# '+title+'\n\n'+links+'\n\n```text\n'+values[key].rstrip()+'\n```\n\nSynchronized with the application. / Синхронизировано с приложением.\n'
  body=['<!-- doc-role: current-generated-help -->','# '+('Built-in Help: complete reference' if lang=='en' else 'Встроенная помощь: полный справочник'),'','Generated from runtime topics, including readiness recipes, setup guide and diagnostic prompts. / Сформировано из тем приложения, рецептов готовности, помощи мастера и промптов.','','[Current state](CURRENT-STATUS.md) · [Installation prompt](AI-INSTALL.'+lang+'.md)','']
  for topic in values['topics']:
   body+=['<a id="'+topic['id']+'"></a>','## '+topic['title'],'',topic['when'],'']
   for step in topic['steps']:
    body+=[step['text'],'']
    if step['command']:body+=['```text',step['command'],'```','']
   if topic['custom']:
    custom=topic['custom']
    if topic['id']=='terms':custom=re.sub(r'\]\((DISCLAIMER(?:\.ru)?\.md)\)',r'](../\1)',custom)
    body+=[custom,'']
   if topic['id']=='ai-prompt':body+=['[Full installation prompt](AI-INSTALL.'+lang+'.md)','']
   body+=['### '+('Diagnostic prompt' if lang=='en' else 'Промпт диагностики'),'','```text',topic['diagnostic'],'```','']
  pending[ROOT/('docs/BUILTIN-HELP.'+lang+'.md')]='\n'.join(body).rstrip()+'\n'
 body=['<!-- doc-role: current-generated-codes -->','# Коды диагностики / Diagnostic reference','','Generated from the merged active error catalogue, including prefix families. / Сформировано из объединённого справочника приложения, включая семейства кодов.','','A listed code may describe a legacy mode or a guarded refusal; it does not prove that a route changed. Global service errors are not falsely assigned to a VPN role. / Наличие кода не доказывает выполненный переход. Общие ошибки службы не приписываются каналу.','','[Current scope](CURRENT-STATUS.md) · [History/provenance](CHANNEL-ATTRIBUTION.md)','']
 for row in data['errorRows']:
  body+=['## '+row[0],'',row[3]+' / '+row[2],'','**RU:** '+row[5],'','**EN:** '+row[4],'','**Что делать:** '+row[7],'','**Action:** '+row[6],'']
  if len(row)>9:body+=['**Пример / Example:** '+row[9]+' / '+row[8],'']
 pending[ROOT/'docs/ERROR_CODES.md']='\n'.join(body)
 inputs=sorted(list((ROOT/'router').glob('*.inc.js'))+[ROOT/'router/files/usr/lib/homensai-vpn/agent.py',ROOT/'qa/export_documentation.js',ROOT/'scripts/sync-documentation.py',ROOT/'DISCLAIMER.md',ROOT/'DISCLAIMER.ru.md'])
 manifest={'schema':1,'scope':'Generated reference equality, not device or external AI acceptance','inputs':{f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_text(encoding='utf-8').encode()).hexdigest() for f in inputs},'outputs':{f.relative_to(ROOT).as_posix():hashlib.sha256(t.encode()).hexdigest() for f,t in pending.items()}}
 pending[ROOT/'qa/documentation-generated.json']=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
 for target,text in pending.items():
  if check:
   if not target.exists() or target.read_text(encoding='utf-8')!=text:raise ValueError('GENERATED-DOC-STALE:'+target.name)
  else:target.write_text(text,encoding='utf-8')
 return {'generated':len(pending),'help_topics':{lang:len(v['topics']) for lang,v in data['languages'].items()},'error_codes':len(data['errorRows']),'terms_version':data['termsVersion']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();print(json.dumps(generate(a.check)))
