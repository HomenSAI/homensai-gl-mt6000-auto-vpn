"""Split the already-patched page; canonical sources still drive docs and source tests."""
import json
from pathlib import Path
import re
import subprocess

MODULES=('help_panel','learn_scenes','learn_panel','error_rows_extra','error_table','ai_prompt')


def marked(name,text):
    return '/* HV-LAZY-BEGIN '+name+' */\n'+text+'\n/* HV-LAZY-END '+name+' */'


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('LAZY-BUILD-ANCHOR: '+old[:100])
    return text.replace(old,new,1)


def split(source,ui_module):
    root=Path(__file__).resolve().parents[1]
    parts={}
    for name in MODULES:
        pattern=r'/\* HV-LAZY-BEGIN '+name+r' \*/\n(.*?)\n/\* HV-LAZY-END '+name+r' \*/'
        matches=list(re.finditer(pattern,source,re.S))
        if len(matches)!=1:raise ValueError('LAZY-BUILD-MODULE: '+name)
        parts[name]=matches[0].group(1)
        source=source[:matches[0].start()]+source[matches[0].end():]
    # Terms/setup still use these two small helpers before Help is opened.
    help_source=parts['help_panel']
    helpers=help_source[help_source.index('function richText('):help_source.index('function helpDiagnosticPrompt(')]
    ai=parts['ai_prompt'];navigation=ai[ai.index('// Opens a Help topic from anywhere'):]
    navigation=once(navigation,"  setTimeout(function(){var topic=document.getElementById('help-'+id);if(topic){topic.open=true;try{topic.scrollIntoView({block:'start'});}catch(e){}}},200);", "  LAZY_HELP.pendingTopic=id;return ensureLazyPage('help').then(function(){lazyHelpDeepLink('help');});")
    parts['ai_prompt']=ai[:ai.index('// Opens a Help topic from anywhere')]
    result=subprocess.run(['node',str(root/'qa/export_lazy_titles.js')],cwd=root,capture_output=True,text=True,encoding='utf8',timeout=45)
    if result.returncode:raise ValueError('LAZY-TITLE-EXPORT: '+result.stderr[-800:])
    eager=json.loads(result.stdout)
    manifest='var ERROR_ROWS='+json.dumps(eager['rows'],ensure_ascii=False,separators=(',',':'))+';\nvar HELP_TOPICS=['+json.dumps(eager['telegram'],ensure_ascii=False,separators=(',',':'))+'];\n'
    # Root code keeps its title registry and state; long details are adopted atomically on load.
    core=(root/'router/lazy_help.inc.js').read_text(encoding='utf8')
    core=once(core,'__LAZY_HELP_MODULE__','homensai-vpn.help'+ui_module.removeprefix('dashboard'))
    core=manifest+helpers+'\n'+navigation+'\n'+core
    source=once(source,"'require ui';","'require ui';\n'require baseclass';\n'require request';")
    # Before terms_panel executes, so its Help topic is retained as a small eager callback.
    source=once(source,'/* First-run terms.',core+'\n/* First-run terms.')
    source=once(source,"activeTab=key;if(appRoot)appRoot.setAttribute('data-hv-active',key);", "activeTab=key;if(appRoot)appRoot.setAttribute('data-hv-active',key);ensureLazyPage(key,inventory).then(function(){lazyHelpDeepLink(key);});")
    source=once(source,'function showErrorCode(code){',"function showErrorCode(code){\n  if(pageKeyNow()&&pageKeyNow()!=='events')errorReturn={tab:pageKeyNow(),y:window.pageYOffset||0};\n  if(typeof ensureLazyPage==='function'&&!LAZY_HELP.api){LAZY_HELP.pendingCode=code;var lazyLink=document.querySelector('[data-hv-tab=\"events\"]');if(lazyLink)lazyLink.click();return ensureLazyPage('events').then(function(){lazyHelpDeepLink('events');});}")
    # Replace the fixed timer in topic links with the parsed route after asynchronous load.
    source=once(source,"      key=hybridPage(key);placeHybridControls(key);", "      lazyHelpRoute(key);key=hybridPage(key);placeHybridControls(key);if(activeTab==='events'&&key!=='events')hideErrorBack();")
    source=once(source,'    var requestedTab=hybridPage(window.location.hash.slice(1));','    lazyHelpRoute(window.location.hash.slice(1));var requestedTab=hybridPage(window.location.hash.slice(1));')
    # Module factory dependencies are explicit; it cannot see view-local variables by accident.
    bindings=('E','bi','locale','richText','helpCommand','READINESS_GUIDES','READINESS_CHECKS','renderReadinessHelp',
              'renderAutoRemedy','AUTO_BLOCKERS','AUTO_REMEDIES','autoRemedyKey','PLAN_BLOCKERS','errorCodeLink','ensureJournalDictionary','spanText')
    imports='\n'.join('var '+name+'=ctx.'+name+';' for name in bindings)
    payload="'use strict';\n'require baseclass';\nreturn baseclass.extend({create:function(ctx){\n"+imports+'\n'
    payload+='\n'.join(parts[name] for name in MODULES)+'\n'
    payload+="ctx.extraHelpTopics.forEach(function(topic){if(topic.id!=='telegram'&&!HELP_TOPICS.some(function(t){return t.id===topic.id;}))HELP_TOPICS.push(topic);});\n"
    payload+="ctx.installCatalogue({rows:ERROR_ROWS,groups:ERROR_GROUPS,groupOf:ERROR_GROUP_OF,state:ERROR_TABLE_STATE,persist:persistErrorTableState});\nensureJournalDictionary();\nreturn {renderHelp:renderHelp,renderLearn:renderLearn,renderErrorTable:renderErrorTable,renderSwitchPage:renderSwitchPage};\n}});\n"
    lazy_dir=root/'router/files/www/luci-static/resources/homensai-vpn';lazy_dir.mkdir(parents=True,exist_ok=True)
    (lazy_dir/('help'+ui_module.removeprefix('dashboard')+'.js')).write_text(payload,encoding='utf8',newline='')
    if len(source.encode('utf8'))>int((len(source.encode('utf8'))+sum(len(text.encode('utf8')) for text in parts.values()))*.70):
        raise ValueError('LAZY-MAIN-SIZE: less than 30 percent reduction')
    return source
