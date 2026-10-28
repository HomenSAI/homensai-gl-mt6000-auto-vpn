const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={bi:(a,b)=>b,E:()=>({}),Date,Math,Number,Array,Object,locale:'ru',performance:{now:()=>0}};
vm.createContext(c);vm.runInContext(fs.readFileSync('router/ui_logic.inc.js','utf8'),c);
// A PC clock a few seconds behind the router must not turn fresh router data into "waiting".
const realNow=Date.now;
try{
  const serverTime=2000000000,status={server_time:serverTime,time:serverTime-3};
  Date.now=()=> (serverTime-4.5)*1000;                       // browser 4.5 s behind the router
  const now=c.statusNow(status);assert(Math.abs(now-serverTime)<0.01,'statusNow follows the router clock');
  assert(Math.abs(c.routerWall()-serverTime)<0.01,'routerWall follows the router clock');
  assert(c.routerWall()>=status.time,'fresh status is never in the future');
  Date.now=()=> (serverTime-4.5+30)*1000;                    // 30 s later, same skew
  assert(Math.abs(c.routerWall()-(serverTime+30))<0.01);
}finally{Date.now=realNow;}
// A channel always has a verdict in words: a result, what failed and when; never "no measurement".
const t0=Date.UTC(2026,9,27,13,31,29)/1000,base={id:'p',interface:'wgclient1',time:t0};
const text=p=>c.channelCheckText(Object.assign({},base,p),t0+5);
assert(/HTTPS 0\/3/.test(text({code:'VPN-003',dns_ok:false,https_success:0}))&&/DNS не прошёл/.test(text({code:'VPN-003',dns_ok:false,https_success:0})));
assert(/Проверка не прошла/.test(text({code:'VPN-003',dns_ok:true,https_success:1}))&&/HTTPS 1\/3/.test(text({code:'VPN-003',dns_ok:true,https_success:1})));
assert(/Проверка пройдена: HTTPS 2\/3/.test(text({code:null,dns_ok:true,https_success:2,rtt_ms:876.4})));assert(!text({code:null,dns_ok:true,https_success:2,rtt_ms:876.4}).includes('876.4'),'technical health RTT is not a headline website response');
assert(/Туннель не подключён/.test(text({code:'VPN-001'})));assert(/Туннель не подключён/.test(c.channelCheckText({id:'p',time:t0},t0)));
assert(/с назад/.test(c.channelCheckText(Object.assign({},base,{code:'VPN-003',https_success:0}),t0+200)),'stale checks say how old they are');
assert(/Первая проверка/.test(c.channelCheckText({id:'p'},t0)));
for(const p of [{code:'VPN-003',https_success:0},{code:null,dns_ok:true,https_success:2},{code:'VPN-001'}])assert(!/Нет свежего/.test(text(p)));
console.log('PASS: router clock skew cannot grey out fresh data; every channel shows its latest check result');
