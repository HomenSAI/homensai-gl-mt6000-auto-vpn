// "Top" button (07.11.2026, owner request): on the shipped page every view has one fixed bottom-right button
// (aria-label "Наверх" / "Back to top"), hidden at the top, shown after more than one screen of scrolling, hidden while a modal
// is open, scrolling to 0 (smooth unless prefers-reduced-motion), one scroll listener, no inline styles, no eval.
'use strict';
const fs=require('fs'),assert=require('assert');
const {load,pageSource,CSS}=require('./approved_page');
const src=pageSource(),css=fs.readFileSync(CSS,'utf8').replace(/\/\*[\s\S]*?\*\//g,'');

// ---------- Legacy page (reference pipeline, not shipped as the UI): its own Top button stays as it was ----------
{
  const build=fs.readFileSync('router/build_sidebar_ui.py','utf8'),panel=fs.readFileSync('router/design_panel.inc.js','utf8'),legacyCss=fs.readFileSync('router/design_layer.css','utf8');
  assert(panel.includes("'class':'hv-top-button'")&&panel.includes('window.scrollTo'),'legacy button scrolls to the top');
  assert(/\.hv-top-button\{position:fixed;right:18px;bottom:18px/.test(legacyCss),'legacy: fixed bottom-right');
  assert(panel.includes('prefers-reduced-motion'),'legacy: reduced motion respected');
  assert(build.length>0);
}

// ---------- Stylesheet: owner tokens, safe margins, layering, focus ring, phone tab bar ----------
assert(/\.hvx \.totop\{position:fixed;right:max\(16px,env\(safe-area-inset-right\)\);bottom:max\(16px,env\(safe-area-inset-bottom\)\);z-index:40;width:44px;height:44px/.test(css),'fixed bottom-right, 16 px / safe-area margins, 44 px target');
assert(/\.hvx \.totop\{[^}]*border-radius:var\(--r\)[^}]*background:var\(--card\)[^}]*color:var\(--acc\)/.test(css),'owner tokens (radius, card, accent): light and dark come with them');
assert(/\.hvx:has\(\.modal-bg\) \.totop\{display:none\}/.test(css),'hidden while a modal is open');
assert(/\.hvx\.v-console \.totop\{bottom:calc\(64px \+ env\(safe-area-inset-bottom\)\)\}/.test(css),'above the phone tab bar of the console');
const z=+/\.hvx \.totop\{[^}]*z-index:(\d+)/.exec(css)[1],modalZ=+/\.hvx \.modal-bg\{[^}]*z-index:(\d+)/.exec(css)[1];
assert(z>30&&z<modalZ,'above content, header and tab bar (<= 30), below modals ('+modalZ+')');
assert(!/\.hvx \.totop:focus\b[^{]*\{outline:(none|0)/.test(css),'the focus ring (global :focus-visible) is not removed');
assert(/:focus-visible\{outline:3px solid/.test(css),'visible focus ring exists');

// ---------- Source: one listener, shared helpers, CSP-ready ----------
assert(src.includes("window.addEventListener('scroll',topUpdate,{passive:true})")&&(src.match(/addEventListener\('scroll'/g)||[]).length===1,'a single passive scroll listener');
assert(/function topHTML\(\)\{[^}]*<button type="button" class="totop"[^}]*hidden>/.test(src)&&!/class="totop"[^>]*style=/.test(src),'a button element, hidden by default, no inline style');
assert(src.includes('prefers-reduced-motion: reduce')&&src.includes("behavior:m&&m.matches?'auto':'smooth'"),'smooth scroll unless reduced motion');
assert(!/new Function|\beval\(/.test(src.replace(/\/\*[\s\S]*?\*\//g,'')),'no new Function / eval in the page');

// ---------- Behaviour in every view ----------
function boot(opts){
  const L=load(opts),{c,inventory,status}=L;let html='',hidden=true;const listeners=[];
  const btn={get hidden(){return hidden;},set hidden(v){hidden=!!v;}};
  const root={className:'',modal:null,set innerHTML(v){html=v;hidden=true;},get innerHTML(){return html;},setAttribute(){},removeAttribute(){},addEventListener(){},
    querySelector(sel){return sel==='.totop'&&html.includes('class="totop"')?btn:sel==='.modal-bg'?root.modal:null;},querySelectorAll(){return [];},contains(){return true;},appendChild(){}};
  c.addEventListener=(n,f)=>{listeners.push([n,f]);};c.innerHeight=800;c.pageYOffset=0;c.scrolls=[];
  c.scrollTo=function(a,b){c.scrolls.push([a,b]);c.pageYOffset=a&&typeof a==='object'?a.top:(b===undefined?0:b);};
  c.matchMedia=q=>({matches:!!opts.reduced&&/reduce/.test(q)});
  c.HVX.boot(root,[inventory,status]);
  return Object.assign(L,{root,btn,listeners,html:()=>html});
}
const click=P=>P.T.onClick({target:{closest:()=>({dataset:{act:'top'},getAttribute:()=>null})},preventDefault(){}});
const views=[['simple home','ok','#home'],['simple settings','ok','#settings'],['console channels','ok','#ch'],['console auto','ok','#auto'],['console servers','ok','#srv'],['console log','ok','#log'],['console system','ok','#sys'],['wizard','first','']];
for(const [name,scn,hash] of views){
  const P=boot({scn,hash});
  const html=P.html();
  assert((html.match(/class="totop"/g)||[]).length===1,name+': exactly one Top button');
  assert(/<button type="button" class="totop" data-act="top" aria-label="Наверх" title="Наверх" hidden>/.test(html),name+': RU aria-label, button element, hidden at the top');
  assert.strictEqual(P.listeners.filter(l=>l[0]==='scroll').length,1,name+': one scroll listener after boot');
  const onScroll=P.listeners.find(l=>l[0]==='scroll')[1];
  assert.strictEqual(P.btn.hidden,true,name+': hidden at the top');
  P.c.pageYOffset=500;onScroll();assert.strictEqual(P.btn.hidden,true,name+': still hidden within one screen (800 px)');
  P.c.pageYOffset=1200;onScroll();assert.strictEqual(P.btn.hidden,false,name+': shown after more than one screen');
  P.root.modal={};onScroll();assert.strictEqual(P.btn.hidden,true,name+': hidden while a modal is open');
  P.root.modal=null;onScroll();assert.strictEqual(P.btn.hidden,false,name+': back after the modal closes');
  P.T.render();assert.strictEqual(P.btn.hidden,false,name+': shown after a redraw at 1200 px (reading position kept)');
  P.c.scrolls.length=0;click(P);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(P.c.scrolls)),[[{top:0,behavior:'smooth'},null]],name+': click scrolls to 0 smoothly');
  assert.strictEqual(P.c.pageYOffset,0,name+': at the top');
  onScroll();assert.strictEqual(P.btn.hidden,true,name+': hidden again at the top');
  P.T.setLocale('en');P.T.render();
  assert(/class="totop" data-act="top" aria-label="Back to top" title="Back to top" hidden>/.test(P.html()),name+': EN aria-label');
}
{  // reduced motion: instant
  const P=boot({scn:'ok',hash:'#home',reduced:true});P.c.pageYOffset=1500;P.c.scrolls.length=0;click(P);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(P.c.scrolls)),[[{top:0,behavior:'auto'},null]],'prefers-reduced-motion: instant');
}
console.log('PASS: Top button in all 8 views (home, settings, 5 console tabs, wizard): hidden at top, shown after one screen, hidden under a modal, scrolls to 0, RU/EN aria-label, reduced motion, one listener');
