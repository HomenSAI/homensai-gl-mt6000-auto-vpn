const fs=require('fs'),vm=require('vm'),assert=require('assert');
// The Auto hint is a live region only when its text changed; a refresh with the same text is not read again.
const c={};vm.createContext(c);
const src=fs.readFileSync('router/auto_panel.inc.js','utf8');
vm.runInContext(src.slice(src.indexOf('var AUTO_HINT_LAST'),src.indexOf('var autoRequestBusy')),c);
assert.equal(c.autoHintLive('Auto works')['aria-live'],'polite');
assert.equal(c.autoHintLive('Auto works')['aria-live'],'off','same text on the next refresh is not announced again');
assert.equal(c.autoHintLive('Auto stopped')['role'],'status');
console.log('PASS: Auto hint is announced only when it changes');
// The shipped module: hidden tab skips status calls, refreshes on return, focus capture covers links and summaries.
const ui=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+/UI_MODULE='([^']+)'/.exec(fs.readFileSync('router/build_sidebar_ui.py','utf8'))[1]+'.js','utf8');
assert(/var hvStatusTick=function\(\)\{if\(typeof document!=='undefined'&&document\.hidden\)return Promise\.resolve\(\);/.test(ui));
assert(ui.includes("poll.add(hvStatusTick,10);")&&ui.includes("addEventListener('visibilitychange'"));
assert(ui.includes('document.activeElement.matches(PAGE_FOCUS_SELECTOR)'));
assert(/PAGE_FOCUS_SELECTOR='[^']*a\[href\],summary/.test(ui));
assert(ui.includes("!node.getClientRects().length||typeof document!=='undefined'&&document.hidden"),'live chart pauses in a hidden tab');
console.log('PASS: hidden tab is quiet, focus survives the refresh on links and summaries');
