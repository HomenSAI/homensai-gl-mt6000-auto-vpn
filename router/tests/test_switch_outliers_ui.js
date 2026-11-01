'use strict';
// Owner 01.11.2026, Switch statistics: (10) abnormally long episodes are left out of the chart and the averages, with a
// note and a toggle, and stay in the table marked; (12) switch durations under 10 s are shown in milliseconds, under a
// minute with one decimal; (11) the page carries the statistics reset of its data (native history = 'auto').
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[];[].concat(children==null?[]:children).flat(Infinity).filter(n=>n!=null&&n!==false).forEach(n=>this.children.push(n));}
  appendChild(n){this.children.push(n);return n;}setAttribute(k,v){this.attrs[k]=v;}}
const walk=n=>n instanceof N?[n,...n.children.flatMap(walk)]:[];
const text=n=>typeof n==='string'||typeof n==='number'?String(n):n instanceof N?n.children.map(text).join(''):'';
let charted=null;
function load(locale){
  const c={HELP_TOPICS:[],E:(t,a,ch)=>new N(t,a,ch),locale,bi:(en,ru)=>locale==='ru'?ru:en,console,Date,Math,Number,String};
  vm.createContext(c);
  vm.runInContext(fs.readFileSync('router/measurements_help.inc.js','utf8'),c);
  vm.runInContext(fs.readFileSync('router/switch_timing.inc.js','utf8'),c);
  vm.runInContext(fs.readFileSync('router/switch_stats_page.inc.js','utf8'),c);
  c.phaseChart=rows=>{charted=rows;return new N('svg');};
  return c;
}
let c=load('en');
// (12) precision: 0.712 s is never "0 s"
assert.equal(c.spanText(0.712),'712 ms');assert.equal(c.spanText(9.9994),'9999 ms');assert.equal(c.spanText(12.34),'12.3 s');
assert.equal(c.spanText(226),'3 min 46 s');assert.equal(c.spanText(-1),'—');
assert.equal(load('ru').spanText(0.5),'500 мс');assert.equal(load('ru').spanText(12.34),'12,3 с');
// (10) four fast manual switches and one bench/power-cut episode (3 min 46 s on the reserve, primary down 2 min 15 s)
const T=1793500000;
function ep(i,switching,onReserve){const start=T+i*600;return {key:'k'+i,kind:'manual',time:start,failure:null,start,reserve:start+switching,returnStart:start+switching+onReserve,back:start+switching+onReserve+0.8,
  rolledBack:null,detect:null,switching,total:null,onReserve,returning:0.8,down:null,returnKind:'manual',closed:1};}
const episodes=[ep(0,0.71,20),ep(1,0.81,25),ep(2,0.74,18),ep(3,0.79,22),Object.assign(ep(4,0.9,226),{down:135})];
assert.equal(c.switchOutliers(episodes.slice(0,4).concat([ep(5,0.75,40)])).length,0,'5 episodes: 41.5 s is within 3 x median (23.6 s)');
assert.deepEqual(c.switchOutliers(episodes).map(e=>e.key),['k4'],'fewer than 5 rule does not apply at 5; MAD rule finds the long one');
assert.deepEqual(c.switchOutliers(episodes.slice(2)).map(e=>e.key),['k4'],'fewer than 5 episodes: above 120 s');
let page=c.renderSwitchPage({episodes,now:T+9999,timing:{avg_seconds:0.76,count:4,last_seconds:0.7}});
assert.equal(page.attrs['data-stats-reset'],'auto','statistics reset of the switch history');
assert.equal(charted.length,4,'the outlier is not drawn');
const note=walk(page).find(n=>n.attrs['data-switch-outlier-note']);assert(note,'outlier note');
assert(/Not shown: abnormally long episodes: 1 \(the longest 3 min 48 s\)/.test(text(note)),text(note));
const cards=walk(page).find(n=>n.attrs['data-switch-cards']);assert(/Switching \(mean\)763 ms/.test(text(cards)),text(cards));
assert(/Router switch average760 ms/.test(text(cards)),'switch_timing.json average in ms');
const table=walk(page).find(n=>n.attrs['data-switch-table']);
assert(text(table).includes('abnormally long, not averaged'),'kept in the table, marked');assert(text(table).includes('Mean (without outliers)'));
assert(text(table).includes('710 ms')&&!/\b0 s\b/.test(text(table)),'no "0 s" for fast switches');
// the toggle draws them again
const toggle=walk(note).find(n=>n.tag==='button');assert.equal(toggle.attrs['data-switch-outliers'],'show');
toggle.attrs.click();assert.equal(c.SWITCH_SHOW_OUTLIERS,true);
page=c.renderSwitchPage({episodes,now:T+9999});assert.equal(charted.length,5,'shown after the toggle');
assert(/Switching \(mean\)763 ms/.test(text(walk(page).find(n=>n.attrs['data-switch-cards']))),'never in the averages');
// built page: the main module formats milliseconds and the lazy module has the outlier rule
const built=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+JSON.parse(fs.readFileSync('VERSION.json','utf8')).application.ui_module+'.js','utf8'),lazy=fs.readFileSync('router/files/www/luci-static/resources/homensai-vpn/'+JSON.parse(fs.readFileSync('VERSION.json','utf8')).application.ui_lazy_modules[0].split('/').pop(),'utf8');
assert(built.includes("Math.round(s*1000)+bi(' ms',' мс')")&&lazy.includes('function switchOutliers('));
console.log('PASS: switch outliers left out of the chart and averages (note, toggle, marked rows), ms durations, reset');
