const fs=require('fs'),vm=require('vm'),assert=require('assert');
for(const language of ['en','ru']){
 const c={bi:(en,ru)=>language==='ru'?ru:en,E:(tag,attrs={},children=[])=>({tag,attrs,children}),Date,locale:language,window:{},safeCode:v=>typeof v==='string'&&/^[A-Z][A-Z0-9-]+$/.test(v),serverTitle:p=>p.name||p.id};vm.createContext(c);
 for(const name of ['ui_logic','auto_panel','summary_panel','readiness_panel','error_rows_extra','error_table','journal_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
 const id='openvpn:1_2',sample={id,time:1000,code:'VPN-003',https_success:1,dns_ok:true};
 const event={profile:id,time:1004,measurement_time:1000,code:'VPN-003',https_success:1,dns_ok:true,role:'target',probe_checks:[{target:'dns.quad9.net',result:'http-unsupported',http_status:505}]};
 const status={profiles:[{id,name:'Reserve'}],samples:[sample],events:[event],accounting:{reliability:{events:[{profile:id,time:1000,kind:'FAILURE',code:'VPN-003',role:'target',sequence:1}]}}};
 let rows=c.journalRows(status,null,1010);assert.equal(rows.length,1,'one measurement cannot become two failure rows');
 let text=c.journalMessage(rows[0],status);assert(text.includes(language==='ru'?'частично':'partially'));assert(text.includes('HTTPS 1/3'));assert(text.includes('HTTP 505'));
 assert(!text.includes(language==='ru'?'трафика нет':'carries nothing'));
 const zero=JSON.parse(JSON.stringify(status));zero.samples[0].https_success=0;zero.events[0].https_success=0;rows=c.journalRows(zero,null,1010);
 text=c.journalMessage(rows[0],zero);assert(text.includes(language==='ru'?'не подтвердила':'not confirmed'));assert(!text.includes(language==='ru'?'часть трафика проходит':'some traffic is passing'));
 const old={profiles:status.profiles,samples:[{...sample,time:2000,https_success:0}],accounting:status.accounting};rows=c.journalRows(old,null,2010);assert.equal(rows[0].probe,null,'today cannot explain an old incident');
 const separate=JSON.parse(JSON.stringify(status));separate.events.push({...event,time:1014,measurement_time:1010});separate.samples.push({...sample,time:1010});assert.equal(c.journalRows(separate,null,1020).length,2,'distinct measurements stay distinct');
 const start={native_history:{events:[{sequence:1,time:1001,state:'STOPPED',codes:['CLIENT-STOP','VENDOR-SETTLING'],control_action:'start',control_time:1000,control_source:'programmatic'}]}};
 const pending=c.journalRows(start,null,1010).find(r=>r.origin==='controller');assert.equal(pending.state,'STARTING');assert.equal(pending.action_source,'programmatic');assert.notEqual(pending.code,'CLIENT-STOP');assert.equal(c.journalDefinition(pending).code,'EVENT-START-CONFIRMATION-PENDING');
 const wait=c.journalRows({native_history:{events:[{sequence:1,time:1000,state:'BLOCKED',codes:['VENDOR-WORKER-BUSY']}]}},null,1010)[0];assert.equal(wait.level,'warning');assert.equal(c.journalDefinition(wait).code,'EVENT-VENDOR-WAIT');
 const catalog=c.ERROR_ROWS.find(r=>r[0]==='VPN-003');assert(!catalog[3].includes('трафика нет'));
 function flatText(node){return Array.isArray(node)?node.map(flatText).join(' '):node&&typeof node==='object'?flatText(node.children||[]):String(node||'');}
 const examples=flatText(c.errorExamples());assert(examples.includes(language==='ru'?'режиме проверки':'proof mode'));assert(examples.includes(language==='ru'?'Остановка не подтверждена':'Stop could not be confirmed'));assert(!examples.includes(language==='ru'?'тест сбоя всё равно убран':'running failure test was still cleaned up'));assert(!examples.includes(language==='ru'?'ваш компьютер его подтвердил':'your computer confirmed it'));

}
console.log('PASS: partial/zero/unknown evidence, distinct vs duplicate measurements, HTTP incompatibility, pending Start and vendor wait EN/RU');
