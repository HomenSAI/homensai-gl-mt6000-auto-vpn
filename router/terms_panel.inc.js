/* First-run terms. The same points are in DISCLAIMER.md / DISCLAIMER.ru.md. Acceptance is stored on the router
   (terms_version, terms_time); the controller refuses to switch and Auto refuses to start until it is stored. */
var TERMS_VERSION='__TERMS_VERSION__';
var TERMS_POINTS=[
  {h:["It is experimental","Это экспериментальная версия"],t:["This is an early alpha release. It has been tested only in a limited way, on a GL.iNet GL-MT6000 (firmware 4.11.0) and in a virtual OpenWrt. It is not production software.","Это ранняя версия alpha. Она проверялась лишь ограниченно, на GL.iNet GL-MT6000 (прошивка 4.11.0) и в виртуальном OpenWrt. Это не промышленное ПО."]},
  {h:["It can interrupt your internet","Оно может прервать ваш интернет"],t:["Switching a VPN route can drop calls, downloads and sessions. A fault or bug can leave devices on your network without internet until you repair the router by hand. Keep another way to reach the internet and the router, and make a backup first.","Переключение маршрута VPN может оборвать звонки, загрузки и сессии. Сбой или ошибка могут оставить устройства без интернета, пока вы не исправите роутер вручную. Держите другой способ выхода в интернет и доступа к роутеру и сначала сделайте резервную копию."]},
  {h:["It changes router settings","Оно меняет настройки роутера"],t:["It reorders your existing VPN rules and can add a temporary firewall rule. It does not edit your VPN keys. You can remove it at any time (see Help).","Оно переставляет ваши существующие правила VPN и может добавить временное правило firewall. Ключи VPN оно не редактирует. Удалить его можно в любой момент (см. «Помощь»)."]},
  {h:["No warranty","Гарантий нет"],t:["Provided “AS IS” under the MIT License, without warranty of any kind. The author and contributors are not liable for any damage, loss of data, loss of service, cost or other consequence of installing or using it.","Предоставляется «КАК ЕСТЬ» (AS IS) по лицензии MIT, без каких-либо гарантий. Автор и участники не отвечают за ущерб, потерю данных, потерю связи, расходы и иные последствия установки или использования."]},
  {h:["You are responsible","Ответственность на вас"],t:["You use it at your own risk. You are responsible for your router, your network, your VPN accounts, your VPN provider’s terms and the law that applies to you. Do not use it where an interruption could endanger people or property.","Вы используете его на свой риск. Вы отвечаете за свой роутер, сеть, аккаунты VPN, условия провайдера VPN и применимое к вам законодательство. Не используйте его там, где перерыв связи может угрожать людям или имуществу."]},
  {h:["Optional reports","Необязательные отчёты"],t:["If you set up Telegram reports, summaries are sent through Telegram’s servers with a bot token stored on your router. Nothing is sent unless you set it up.","Если вы настроите отчёты в Telegram, сводки отправляются через серверы Telegram с токеном бота, хранящимся на вашем роутере. Без вашей настройки ничего не отправляется."]},
  {h:["No promise of support","Поддержка не обещана"],t:["Features, behaviour and these terms may change in later versions; you may be asked to accept them again.","Возможности, поведение и эти условия могут измениться в следующих версиях; вас могут попросить принять их снова."]}
];
if(typeof HELP_TOPICS!=='undefined'){HELP_TOPICS.push({id:'terms',title:["Terms of use (experimental software)","Условия использования (экспериментальное ПО)"],when:["What you accepted on the first screen. The full text is DISCLAIMER.md in the project repository.","Что вы приняли на первом экране. Полный текст — DISCLAIMER.ru.md в репозитории проекта."],steps:TERMS_POINTS.map(function(point){return {t:[point.h[0]+'. '+point.t[0],point.h[1]+'. '+point.t[1]]};})});}
var TERMS_CHECKS=[
  ["I understand that this software is experimental and may interrupt my internet connection.","Я понимаю, что это ПО экспериментальное и может прервать моё подключение к интернету."],
  ["I have read the terms above and accept full responsibility for installing and using it.","Я прочитал условия выше и принимаю полную ответственность за установку и использование."]
];
function termsAccepted(inventory){
  return !!inventory&&!inventory.error&&!!inventory.settings&&inventory.settings.terms_version===TERMS_VERSION;
}
function renderTermsGate(inventory,status){
  var boxes=TERMS_CHECKS.map(function(){return E('input',{'type':'checkbox'});});
  var busy=false,button=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-terms-accept','click':function(){
    if(busy||!boxes.every(function(box){return box.checked===true;}))return;
    busy=true;button.disabled=true;
    return rpc.declare({object:'homensai-vpn',method:'terms_accept',params:['version'],expect:{}})(TERMS_VERSION).then(function(result){
      if(result&&result.saved===true){window.location.reload();return;}
      busy=false;sync();ui.addNotification(null,E('p',{},(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(result.code))?result.code:'TERMS-SAVE-FAILED'));
    }).catch(function(){busy=false;sync();ui.addNotification(null,E('p',{},'TERMS-SAVE-UNCONFIRMED'));});
  }},bi('Accept and continue','Принять и продолжить'));
  function sync(){button.disabled=busy||!boxes.every(function(box){return box.checked===true;});}
  boxes.forEach(function(box){box.addEventListener('change',sync);});
  button.disabled=true;
  var other=locale==='ru'?'en':'ru';
  var language=E('a',{'href':'#','click':function(ev){ev.preventDefault();var next=new URL(window.location.href);next.searchParams.set('lang',other);window.location.assign(next.toString());}},other==='ru'?'Русский':'English');
  var model=identityModel(status||{});
  var versionBadge=E('span',{'class':'hv-version','aria-label':bi('Program version','Версия программы')},'v'+(model.agent||model.uiAgent));
  var attribution=E('div',{'class':'hv-terms-attribution'},[renderAttribution(status||{})]);
  var footer=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(footer,locale,'platform');
  applyTheme(storedTheme());
  var gate=E('div',{'class':'hv-app hv-terms','data-terms-gate':TERMS_VERSION,'data-hv-design':currentDesign(),'style':'width:100%;box-sizing:border-box;overflow-wrap:anywhere'},[
    E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui15.css')}),
    E('section',{'class':'hv-chart-card hv-terms-card'},[
      E('header',{'class':'hv-page-header','style':'flex-wrap:wrap;gap:12px'},[E('p',{'class':'hv-eyebrow'},bi('HomenS.AI Auto VPN · first start','HomenS.AI Auto VPN · первый запуск')),versionBadge]),
      E('h1',{},bi('Experimental software: please read','Экспериментальное ПО: прочитайте, пожалуйста')),
      E('p',{'class':'hv-terms-license'},bi('MIT License · experimental alpha software · use at your own risk','Лицензия MIT · экспериментальная alpha-версия · использование на свой риск')),
      E('p',{},bi('Read the agreement, tick both confirmations and press Accept and continue. The eight-step setup opens next.','Прочитайте соглашение, отметьте оба подтверждения и нажмите «Принять и продолжить». Затем откроется настройка из восьми шагов.')),
      E('p',{},[bi('Language: ','Язык: '),language]),
      E('ol',{'class':'hv-terms-list'},TERMS_POINTS.map(function(point){return E('li',{},[E('strong',{},bi(point.h[0],point.h[1])),E('p',{},bi(point.t[0],point.t[1]))]);})),
      E('p',{'class':'hv-terms-note'},bi('This is not legal advice. The full text is in DISCLAIMER.md in the project repository and on the Help page.','Это не юридическая консультация. Полный текст — в DISCLAIMER.ru.md в репозитории проекта и на странице «Помощь».')),
      E('div',{'class':'hv-terms-checks'},TERMS_CHECKS.map(function(text,index){return E('label',{'class':'hv-terms-check'},[boxes[index],' ',bi(text[0],text[1])]);})),
      E('p',{},button),
      E('div',{'class':'hv-terms-note'},[E('p',{},bi('If you do not accept, remove the package and your router stays as it was:','Если вы не принимаете условия, удалите пакет, и роутер останется как был:')),helpCommand('opkg remove homensai-auto-vpn')])
    ]),attribution,footer
  ]);
  return gate;
}
