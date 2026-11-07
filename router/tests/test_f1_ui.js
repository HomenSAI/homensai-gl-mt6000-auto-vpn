// Style F1 «Золотая сетка» (owner choice 04.11.2026) on the real built page: layout proportions in the stylesheet, the markup of the simple
// view, the console tabs and the wizard, the owner attributes on a phone, 44 px tap areas, blinking lamps with reduced motion, scoping.
'use strict';
const fs=require('fs'),assert=require('assert');
const {load,pageSource,CSS}=require('./approved_page');
const css=fs.readFileSync(CSS,'utf8').replace(/\/\*[\s\S]*?\*\//g,''),src=pageSource();
const has=(re,msg)=>assert(re.test(css),msg||String(re));

// ---------- Stylesheet: golden proportions, Fibonacci scale, phone behaviour ----------
has(/\.hvx \.gold\{display:grid;grid-template-columns:38\.2fr 61\.8fr/,'page columns 38.2 / 61.8');
has(/\.hvx \.hero\{aspect-ratio:1\.618034\/1/,'the status card is a golden rectangle');
has(/\.hvx \.chpair:has\(\.ch\[data-ch="primary"\]\.active\)\{grid-template-columns:1\.618fr 1fr\}/,'the channel carrying traffic gets 61.8 % (primary)');
has(/\.hvx \.chpair:has\(\.ch\[data-ch="reserve"\]\.active\)\{grid-template-columns:1fr 1\.618fr\}/,'... and the reserve');
has(/\.hvx\{--f2:2px;--f3:3px;--f5:5px;--f8:8px;--f13:13px;--f21:21px;--f34:34px;--f55:55px;--f89:89px/,'Fibonacci scale tokens');
has(/\.hvx\.v-console \.strip \.wrap\{display:grid;grid-template-columns:38\.2fr 61\.8fr/,'console status strip splits like the page');
has(/\.hvx\.v-console \.srvpair:has\(\.srv\[data-ch="primary"\]\.active\)\{grid-template-columns:1\.618fr 1fr\}/,'servers 61.8 / 38.2');
has(/\.hvx \.btn::after[^{]*\{content:"";position:absolute;inset:-5px\}/,'34 px buttons keep a 44 px tap area (5 + 34 + 5)');
has(/\.hvx \.aswitch \.trk\{width:55px;height:34px\}/,'Auto switch 55 x 34');
has(/@container \(max-width:520px\)\{\.hvx \.chpair\{grid-template-columns:1fr!important\}\}/,'@container rules are scoped, not mangled');
assert(!/\.hvx @container|\.hvx @media/.test(css),'no at-rule was prefixed by the scoper');
has(/\.hvx\.v-console\{padding-bottom:calc\(55px/,'console: 55 px bottom tab bar on phones keeps the content clear');
has(/\.hvx\.v-console \.tabbar\{position:fixed;left:0;right:0;bottom:0/,'console tab bar is the fixed bottom bar on a phone');
// the mockup-only parts are not in the product
assert(!/#fibui|#fibov|fib-sp|\.mock\b/.test(css),'no mockup banner or overlay rules');
// owner attributes: the router model line under the name is visible on a phone (the F1 header has two rows there), the footer too
has(/@media \(max-width:760px\)\{[^@]*\.hvx \.hdr \.devline\{display:block\}/,'the model line "GL.iNet GL-MT6000 · Flint 2" is shown on a phone');
assert(!/\.hdr \.devline\{display:none\}/.test(css),'nothing hides the model line any more');
// lamps blink, reduced motion stops them
has(/\.hvx \.lamp\.g\{[^}]*animation:hv-blink 2\.4s/);has(/@media \(prefers-reduced-motion:reduce\)\{\.hvx \.lamp,\.hvx \.lamp\.g,\.hvx \.lamp\.y,\.hvx \.lamp\.r\{animation:none!important\}/);
// the stylesheet does not ship the old per-view variant styles
assert(!/\.hvx\.v-simple/.test(css)&&!/\.hvx\.v-wizard [^{]*\{[^}]*(card|hero|gold)/.test(css),'A/C variant stylesheets are gone (only the wizard header placement stays)');
// form fields, lists and links reach 44 px in every view (settings of the simple view, wizard, console)
has(/\.hvx \.f label\{min-height:44px\}/);has(/\.hvx \.inp\{[^}]*min-height:44px/);has(/\.hvx main a\[href\]:not\(\.btn\):not\(\.code\)\{display:inline-flex[^}]*min-height:34px/);
has(/\.hvx \[data-codes\]\{overflow-x:auto\}/,'the code table scrolls inside its box, the page never scrolls sideways');
assert(src.includes('class="wrap hdr-in"'),'F1 header grid');
console.log('PASS: F1 stylesheet - 38.2/61.8 columns, golden status rectangle, 61.8 % traffic channel, Fibonacci tokens, 44 px areas, phone bar, scoped at-rules, no mockup leftovers');

// ---------- Markup ----------
for(const lang of ['ru','en']){
  const {T}=load({lang});
  const home=T.homeA();
  for(const part of ['class="gold"','class="gcol gl"','class="gcol gr"','class="card hero" data-g="status"','class="hero-top"','class="hero-act"','class="chpair" data-g="channels"','class="card stcard"','class="card evcard"','class="tests"'])assert(home.includes(part),lang+' home: '+part);
  for(const bind of ['ov.title','ov.sub','check.l','tiles','manual','events','speed','fault','p.ms','r.ms','p.active','r.active'])assert(home.includes('data-b="'+bind+'"')||home.includes('data-b-class="'+bind+'"'),lang+' home keeps the data binding '+bind);
  assert(home.includes('data-lamp="ov"')&&home.includes('data-auto-switch')&&home.includes('data-act="speed"')&&home.includes('data-act="fault"')&&home.includes('data-act="all"'),'actions are the real ones');
  assert(!/class="grid2"/.test(home),'no 50/50 grid left on the home page');
  const ch=T.tabs.ch();for(const part of ['class="gold"','class="card hero" data-o="2" data-g="last"','data-b="last.time"','data-b="last.what"','data-b="last.why"','class="chpair"'])assert(ch.includes(part),lang+' channels: '+part);
  const au=T.tabs.auto();for(const part of ['class="card hero" data-o="1" data-g="auto"','data-b="autochip"','data-b="autoplain"','class="card stcard"','data-act="fault"'])assert(au.includes(part),lang+' auto: '+part);
  const sv=T.tabs.srv();assert(sv.includes('class="srvpair"')&&sv.includes('data-b-class="p.srv"')&&sv.includes('data-b-class="r.srv"')&&sv.includes('class="card spd"')&&sv.includes('data-set="pick"'),lang+' servers');
  const lg=T.tabs.log();assert(lg.includes('data-b="events20"')&&lg.includes('class="card evcard"')&&lg.includes('data-act="incident"'),lang+' log');
  const sy=T.tabs.sys(),codePanel=/<div data-code-panel>([\s\S]*?)<\/div>/.exec(sy);
  assert(sy.includes('id="ready"')&&sy.includes('data-b="ready"')&&sy.includes('class="body hlp"')&&codePanel,lang+' system');
  assert(codePanel[1].includes('data-act="codeq"')||(/role="status"/.test(codePanel[1])&&codePanel[1].includes(lang==='ru'?'Загрузка справочника':'Loading the code reference')),lang+' reference has search or an explicit initial loading state');
  const wz=T.wizard();assert(wz.includes('class="wiz" data-g="wizard"')&&wz.includes('class="wz-side"')&&wz.includes('class="card wz-main"')&&wz.includes('class="steps"'),lang+' wizard');
  const st=T.settingsA();assert(st.includes('class="pg-h"')&&st.includes('data-secid')||st.includes('class="sec"')||st.includes('<details'),lang+' settings');
  // the A <-> D switch, language and theme buttons are still the header tools
  assert(T.toolsHTML().includes('data-act="view" data-v="console"')&&T.toolsHTML().includes('data-act="view" data-v="simple"')&&T.toolsHTML().includes('data-act="lang"'),'view switch');
  const brand=T.brandHTML();assert(brand.startsWith('<div class="hb"><a class="brand"')&&brand.includes('<div class="bv"><span class="badge-ver hv-version"')&&brand.includes('GL.iNet GL-MT6000 · Flint 2'),'header cells: brand with model, version badge');
}
// the alpha8 expert fields still exist in the settings of the console (system tab) and the simple view
{
  const {T}=load({lang:'ru'});
  const all=T.settingsA()+T.tabs.auto();
  for(const key of ['failure_model','server_pick_model','recovery_rescue_stable','data-set="rescue"'])assert(all.includes(key)||src.includes(key),'alpha8 field '+key);
}
console.log('PASS: F1 markup - golden grid on the home page and every console tab, real bindings and actions kept, wizard side column, header cells, RU and EN');

// ---------- Live paint keeps the active-channel classes for pair and servers ----------
{
  const {T}=load({lang:'ru'});
  assert(/B\[k\+'\.srv'\]=function\(\)\{return selectedRole\(\)===r&&!V\.d\.dataUnavailable\?'card srv active':'card srv';\}/.test(src),'server cards follow the traffic channel');
  assert(src.includes("B[k+'.active']"),'channel cards follow the traffic channel');
  assert(T.HV&&true);
}
console.log('PASS: the channel carrying traffic is marked on the channel and server cards by the live bindings');
