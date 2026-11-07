"""HomenS.AI Auto VPN page: the owner-approved mockups (03.11.2026) built as the real LuCI view.

Views: «Простой» (mockup A: Home + Settings), «Пульт» (mockup D: Channels/Auto/Servers/Log/System) and the first-run
wizard (mockup C, wizard only), all in the owner-chosen style F1 «Золотая сетка» (04.11.2026). Sources:
  router/ui/mockup/*.css  the approved styles, copied verbatim: core.css (shared base of A/C/D), fib-base.css + f1.css (the F1
                          layer for every view and the wizard), d-f1.css (console parts); scoped to .hvx here (the page lives inside LuCI)
  router/ui/app.css       additions the mockups did not need (LuCI host, view switch, help content)
  router/ui/*.js          markup, wording and wiring (core, actions, settings, views) and the module bridge
Logic (freshness, health, traffic channel, Auto/manual/monitor models, journal, error catalogue, help topics) is not
copied: it is extracted from the legacy pipeline (legacy_page_build.py, executed in memory) by ui_extract.py, so the
display truth stays the same tested code. Outputs: view/homensai-vpn/<UI_MODULE>.js and its stylesheet, the optional
help/codes/training module help<N>.js, the server module pick<N>.js; the menu and the LuCI controller name the page.
"""
from pathlib import Path
import re
import sys

UI_MODULE='dashboard211'
STYLESHEET='ui177.css'
LEGACY_STYLESHEET='ui177.css'  # the in-memory legacy pipeline names the same file (scripts/bump-version.py renames both)
HERE=Path(__file__).resolve().parent
VIEW=HERE/'files/www/luci-static/resources/view/homensai-vpn'
LAZY=HERE/'files/www/luci-static/resources/homensai-vpn'
UI=HERE/'ui'
REFERENCE=HERE.parent/'qa/legacy-page'
sys.path.insert(0,str(HERE))
from ui_extract import closure, statements, referenced, squeeze_indent  # noqa: E402

UI_FILES=('core.js','actions.js','settings.js','advisor.js','views.js')
# Names the page provides itself at module level (the legacy versions navigated the old menu).
BRIDGED=('showErrorCode','pageKeyNow','activeTab')
EXTRA_ROOTS=('TERMS_FULL_EN','TERMS_FULL_RU','TERMS_POINTS','TERMS_CHECKS','TERMS_VERSION','RECOVERY_PRESETS','TG_PRESETS','ERROR_ROWS',
             'lazyHelpContext','loadLazyHelp','statusCall','loadInventory','uiStatusFailure','uiNewestStatus',
             # error-code coverage of the shipped page is tested on these (router/tests/test_error_coverage_ui.js)
             'ERROR_GROUP_OF','errorFamilyOf','findErrorCodes')
SCOPE='.hvx'


def legacy():
    outputs={}
    text=(HERE/'legacy_page_build.py').read_text(encoding='utf8')
    namespace={'__file__':str(HERE/'legacy_page_build.py'),'__name__':'legacy_page_build','LEGACY_UI_MODULE':UI_MODULE,
               'LEGACY_CSS':LEGACY_STYLESHEET,'OUTPUTS':outputs}
    exec(compile(text,str(HERE/'legacy_page_build.py'),'exec'),namespace)
    return outputs


def _split_rules(css):
    """Top-level CSS blocks as (prelude, body) with nested blocks kept as text."""
    out=[];i=0;n=len(css)
    while i<n:
        j=css.find('{',i)
        if j<0:break
        prelude=css[i:j].strip();depth=0;k=j
        while k<n:
            if css[k]=='{':depth+=1
            elif css[k]=='}':
                depth-=1
                if depth==0:break
            k+=1
        out.append((prelude,css[j+1:k]));i=k+1
    return out


def _scope_selector(sel,prefix):
    sel=sel.strip()
    if sel.startswith(':root'):return prefix+sel[len(':root'):]
    if sel in ('html','body'):return prefix
    if sel=='*':return prefix+' *'
    if sel.startswith(':'):return prefix+' '+sel
    return prefix+' '+sel


def scope_css(css,prefix):
    css=re.sub(r'/\*.*?\*/','',css,flags=re.S)
    parts=[]
    for prelude,body in _split_rules(css):
        if prelude.startswith('@keyframes'):parts.append(prelude+'{'+body+'}');continue
        if prelude.startswith(('@media','@container','@supports')):
            inner=scope_css(body,prefix)
            if inner.strip():parts.append(prelude+'{'+inner+'}')
            continue
        selectors=[s for s in prelude.split(',') if s.strip()]
        if any(s.strip().startswith('.mock') for s in selectors):continue  # the mockup banner is not part of the product
        scoped=','.join(dict.fromkeys(_scope_selector(s,prefix) for s in selectors))
        parts.append(scoped+'{'+body.strip()+'}')
    return '\n'.join(parts)


def stylesheet():
    core=scope_css((UI/'mockup/core.css').read_text(encoding='utf8'),SCOPE)
    # body{...} of the mockup is the page root here; the root keeps the page background and type.
    # F1 «Золотая сетка» replaces the per-view variant styles of mockups A/C/D: one layer for the simple view, the console
    # view and the wizard (fib-base.css + f1.css), plus the console-only parts (d-f1.css).
    base=scope_css((UI/'mockup/fib-base.css').read_text(encoding='utf8')+'\n'+(UI/'mockup/f1.css').read_text(encoding='utf8'),SCOPE)
    # d-f1.css: the console parts (status strip, tabs, tab pages) apply to the console only; its tail (fields, lists, links,
    # table scrolling, remaining off-scale values: 44 px targets) is shared by every view, because settings and the wizard
    # carry the same fields in the simple view.
    dtext=(UI/'mockup/d-f1.css').read_text(encoding='utf8');cut=dtext.index('/* lists inside cards')
    d=scope_css(dtext[:cut],SCOPE+'.v-console')+'\n'+scope_css(dtext[cut:],SCOPE)
    head='/* HomenS.AI Auto VPN page stylesheet (generated by router/build_sidebar_ui.py from router/ui; HomenS.AI Style 1.14.3) */\n'
    return (head+'\n'.join([core,base,d,(UI/'app.css').read_text(encoding='utf8')])).rstrip('\r\n')+'\n'


def page(legacy_page):
    ui_src='\n'.join((UI/name).read_text(encoding='utf8') for name in UI_FILES)
    marker='return view.extend({'
    ui_stmts=statements(ui_src+'\n'+marker,len(ui_src)+1)
    own={name for _s,_e,names in ui_stmts for name in names}
    legacy_stmts=statements(legacy_page,legacy_page.rindex(marker))
    legacy_names={name for _s,_e,names in legacy_stmts for name in names}
    used=referenced(ui_src,0,len(ui_src))
    clash=sorted(own&legacy_names&used)
    roots=sorted(((used&legacy_names)-own-set(BRIDGED))|set(EXTRA_ROOTS))
    logic,names=closure(legacy_page,roots,exclude=BRIDGED)
    shadowed=sorted(own&names)
    if shadowed:
        # A page name hiding a legacy name the logic needs would silently change behaviour inside the page.
        needed=sorted(set(shadowed)&used)
        if needed:raise ValueError('UI-NAME-SHADOWS-LOGIC: '+', '.join(needed))
    agent=(HERE/'files/usr/lib/homensai-vpn/agent.py').read_text(encoding='utf8')
    version=re.search(r"^VERSION = '([^']+)'",agent,re.M).group(1)
    style=re.search(r"HV_STYLE_VERSION='([^']+)'",(HERE/'attribution_panel.inc.js').read_text(encoding='utf8')).group(1)
    bridge=(UI/'bridge.js').read_text(encoding='utf8')
    for key,value in (('__UI_AGENT__',version),('__HV_STYLE__',style),('__HV_STYLESHEET__',STYLESHEET)):
        assert bridge.count(key)==1,key;bridge=bridge.replace(key,value)
    assert bridge.count('/*@UI@*/')==1
    bridge=bridge.replace('/*@UI@*/',ui_src)
    head=("// HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/\n'use strict';\n'require view';\n'require rpc';\n'require poll';\n"
          "'require ui';\n'require baseclass';\n'require request';\n"
          "/* Display logic extracted from the legacy pipeline (router/legacy_page_build.py) by router/ui_extract.py. */\n")
    source=head+logic+'\n/* The approved page (router/ui). */\n'+bridge
    return squeeze_indent(re.sub(r'(?m)^[ \t]+$','',source)),{'roots':len(roots),'logic':len(logic.encode('utf8')),'clash':clash}


def main():
    out=legacy()
    source,info=page(out['legacy_page'])
    (VIEW/(UI_MODULE+'.js')).write_text(source,encoding='utf8',newline='\n')
    (VIEW/STYLESHEET).write_text(stylesheet(),encoding='utf8',newline='\n')
    LAZY.mkdir(parents=True,exist_ok=True)
    number=UI_MODULE.removeprefix('dashboard')
    (LAZY/('help'+number+'.js')).write_text(out['help'],encoding='utf8',newline='\n')
    (LAZY/('pick'+number+'.js')).write_text(out['pick'],encoding='utf8',newline='\n')
    (HERE/'files/usr/lib/lua/luci/controller/homensai_vpn.lua').write_text(out['controller'],encoding='utf8',newline='\n')
    (HERE/'files/usr/share/luci/menu.d/luci-app-homensai-vpn.json').write_text(out['menu'],encoding='utf8',newline='\n')
    # The legacy page the logic is extracted from: a test reference only (never packaged). Legacy-logic tests read it
    # through router/tests/legacy_reference.js; the original UI itself is preserved by tag ui-original-2.1.0-alpha6.
    REFERENCE.mkdir(parents=True,exist_ok=True)
    (REFERENCE/'dashboard.js').write_text(out['legacy_page'],encoding='utf8',newline='\n')
    (REFERENCE/'ui.css').write_text(out['legacy_css'],encoding='utf8',newline='\n')
    print('Generated %s.js (%d bytes, %d logic roots, %d logic bytes) and %s' % (UI_MODULE,len(source.encode('utf8')),info['roots'],info['logic'],STYLESHEET))


if __name__=='__main__':
    main()
