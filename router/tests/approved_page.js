// Loads the SHIPPED page (approved mockups A/C/D, 03.11.2026) into a vm with the synthetic pair fixture of the preview
// (qa/ui-preview/fixture-pair.js): no browser, no router. Every router call is recorded in order.
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path');
const ROOT=path.resolve(__dirname,'..','..');
const app=JSON.parse(fs.readFileSync(path.join(ROOT,'VERSION.json'),'utf8').replace(/^﻿/,'')).application;
const PAGE=path.join(ROOT,'router/files/www/luci-static/resources/view/homensai-vpn/'+app.ui_module+'.js');
const CSS=path.join(ROOT,'router/files/www/luci-static/resources/view/homensai-vpn/'+app.ui_stylesheet);
function pageSource(){return fs.readFileSync(PAGE,'utf8');}
function load(opts){
  opts=opts||{};const scn=opts.scn||'ok',calls=[],stored=Object.assign({},opts.storage||{}),modals=[],toasts=[];
  const settings={},profiles=[],status={profiles},inventory={profiles:[],servers:[],settings};
  const c={console,URL,URLSearchParams,Intl,Promise,Date,Math,JSON,Error,Object,Array,Number,String,Boolean,RegExp,Map,Set,WeakMap,
    setTimeout:(fn,ms)=>ms<=50?setTimeout(fn,0):0,clearTimeout(){},setInterval(){return 0;},clearInterval(){},
    location:{search:'?fixture=pair&scn='+scn+(opts.query||''),href:'http://router/cgi-bin/luci/admin/services/homensai-vpn',hash:opts.hash||'',pathname:'/cgi-bin/luci/admin/services/homensai-vpn'},
    localStorage:{getItem:k=>Object.prototype.hasOwnProperty.call(stored,k)?stored[k]:null,setItem:(k,v)=>{stored[k]=String(v);}},
    sessionStorage:{getItem:()=>null,setItem(){}},performance:{now:()=>Date.now()},navigator:{},
    document:{hidden:false,head:null,activeElement:null,createElement:()=>({}),addEventListener(){},querySelector(){return null;},querySelectorAll(){return [];},getElementById(){return null;}},
    E:(tag,attrs,children)=>({tag,attrs,children}),L:{resource:p=>'/luci-static/resources/'+p,require:()=>Promise.reject(new Error('no lazy module in this test'))},
    poll:{add(){}},ui:{addNotification(){},showModal(){},hideModal(){}},view:{extend:o=>o},baseclass:{extend:o=>o},request:{},
    addEventListener(){},scrollTo(){},pageYOffset:0,fixtureCalls:[]};
  c.window=c;c.globalThis=c;
  const answers=Object.assign({inventory:()=>inventory,status:()=>status,setup_check:()=>({passed:true}),history:()=>({}),
    pair_manual:()=>({accepted:true,queued:true,completed:false,request_id:'b'.repeat(32)}),manual_switch:()=>({accepted:true,queued:true,completed:false,request_id:'c'.repeat(32)}),
    speed_start:()=>({accepted:true,run_id:'d'.repeat(32)}),fault_start:()=>({code:'FAULT-ACTIVE'}),statistics:()=>({events:[]})},opts.answers||{});
  c.rpc={declare:spec=>(...args)=>{const a=answers[spec.method];return Promise.resolve(a?a(args):spec.method.indexOf('setup_')===0?{saved:true}:{queued:true,accepted:true});}};
  vm.createContext(c);
  vm.runInContext(fs.readFileSync(path.join(ROOT,'qa/ui-preview/fixture-pair.js'),'utf8'),c);
  c.HV_FIXTURE({status,inventory,settings,profiles});
  if(opts.mutate)opts.mutate({status,inventory,settings,profiles});
  const inner=c.rpc.declare;
  c.rpc.declare=spec=>{const f=inner(spec);return (...args)=>{calls.push({method:spec.method,params:spec.params,args});return f(...args);};};
  const src=pageSource(),marker='return view.extend({',at=src.lastIndexOf(marker);
  const view=vm.runInContext('(function(){'+src.slice(0,at)+'globalThis.HVX=HVX;'+src.slice(at)+'\n})()',c);
  const T=c.HVX._test;
  T.HV.inv=inventory;T.HV.st=status;T.HV.root=null;
  T.HV.testModal=o=>{modals.push(o);return {remove(){}};};T.HV.testToast=m=>{toasts.push(m);};
  T.setLocale(opts.lang||'ru');
  if(opts.tick!==false&&opts.mutate===undefined)c.HV_FIXTURE_CMD=undefined;
  T.snap();
  return {c,T,calls,modals,toasts,status,inventory,settings,profiles,stored,view,flush:()=>new Promise(r=>setTimeout(r,20)),
    methods:()=>calls.map(x=>x.method).filter(m=>m!=='status'&&m!=='history'&&m!=='inventory')};
}
function strip(html){return String(html).replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#39;|&quot;|&amp;|&lt;|&gt;/g,' ').replace(/\s+/g,' ');}
module.exports={load,strip,pageSource,PAGE,CSS,ROOT,app};
