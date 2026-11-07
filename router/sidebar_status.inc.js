/* Bottom-left of the sidebar: two small lamps in one row (Auto, Monitoring) and the program version. Always visible. */
function fillSideStatus(host,status,inventory){
  while(host.firstChild)host.removeChild(host.firstChild);
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),model=autoControlModel(status,now),id=identityModel(status);
  var monitorFresh=!status.rpc_error&&!status.error&&observationFresh(status,now);
  var light=typeof autoLightModel==='function'?autoLightModel(status,inventory,now):null;
  var signal=autoSignal(light),state={green:'on',yellow:'switching',red:'off',off:'dark'}[signal];
  var autoText=autoStateText(light),autoHint=[light.title,light.hint].filter(Boolean).join(' · ');
  var monText=bi('Monitoring','Мониторинг');
  var monHint=monitorFresh?bi('Monitoring works: fresh data from the router.','Мониторинг работает: свежие данные от роутера.'):status.rpc_error?bi('The router does not answer.','Роутер не отвечает.'):bi('Monitoring is not sending data.','Мониторинг не присылает данные.');
  function go(tab,anchor){return function(event){if(event&&event.type==='keydown'&&event.key!=='Enter'&&event.key!==' ')return;if(event&&event.preventDefault)event.preventDefault();
    var link=document.querySelector('[data-hv-tab="'+tab+'"]');if(link&&(typeof pageKeyNow!=='function'||pageKeyNow()!==tab))link.click();
    if(anchor)setTimeout(function(){var node=document.querySelector(anchor);if(node&&node.getBoundingClientRect){var top=node.getBoundingClientRect().top+(window.pageYOffset||0)-180;window.scrollTo({top:Math.max(0,top),behavior:'smooth'});}},120);};}
  function lampLink(kind,text,hint,tab,anchor,more){var open=go(tab,anchor),title=hint+' '+more;return E('span',{'class':'hv-side-lamp hv-side-lamp-link','role':'link','tabindex':'0','title':title,'click':open,'keydown':open},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},text),E('span',{'class':'hv-visually-hidden'},' — '+title)]);}
  function lamp(kind,text,hint){return E('span',{'class':'hv-side-lamp','role':'status','title':hint},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},text),E('span',{'class':'hv-visually-hidden'},' — '+hint)]);}
  function openAuto(event){if(event&&event.type==='keydown'&&event.key!=='Enter'&&event.key!==' ')return;if(event&&event.preventDefault)event.preventDefault();var link=document.querySelector('[data-hv-tab="overview"]');if(link&&typeof pageKeyNow==='function'&&pageKeyNow()!=='overview')link.click();else if(typeof overviewToAuto==='function')overviewToAuto();else if(typeof goToSection==='function')goToSection('overview','hv-auto-vpn');}
  var autoTitle=autoHint+' '+bi('Click to open Automatic VPN failover.','Нажмите, чтобы открыть «Автоматическое переключение VPN».');
  var autoLamp=E('span',{'class':'hv-side-lamp hv-side-lamp-link','role':'link','tabindex':'0','title':autoTitle,'click':openAuto,'keydown':openAuto},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+state,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},autoText),E('span',{'class':'hv-visually-hidden'},' — '+autoTitle)]);
  host.appendChild(E('div',{'class':'hv-side-lamps'},[autoLamp,lampLink(monitorFresh?'on':'off',monText,monHint,'services','[data-monitor-page]',bi('Click to open the monitoring statistics.','Нажмите, чтобы открыть статистику мониторинга.'))]));
  function channel(role,label){
    var tone=channelLampTone(status,inventory,role,now,light);
    return lampLink({green:'on',yellow:'switching',grey:'unknown',red:'off'}[tone.color]||'unknown',label,label+': '+tone.text,'channels','.hv-server-grid',bi('Click to open the channel cards.','Нажмите, чтобы открыть карточки каналов.'));
  }
  host.appendChild(E('div',{'class':'hv-side-channel-lamps'},[channel('source',bi('Primary','Основной')),channel('target',bi('Reserve','Резерв'))]));
  host.appendChild(E('p',{'class':'hv-side-version'},[bi('Version ','Версия '),E('strong',{},id.agent||id.uiAgent)]));
}
