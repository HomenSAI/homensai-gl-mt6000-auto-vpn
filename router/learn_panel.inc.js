/* Interactive training: lesson cards, then a quiz with checkboxes, a score and "take again". Data are [English, Russian] pairs. */
var LEARN_LESSONS=[
  {icon:'①',title:['What this system is','Что это за система'],
   body:[['HomenS.AI Auto VPN is a page on your GL.iNet router. It watches the VPN connections you already created in GL.iNet and shows which of them give internet right now.','HomenS.AI Auto VPN — страница на вашем роутере GL.iNet. Она следит за VPN-подключениями, которые вы уже создали в GL.iNet, и показывает, какие из них сейчас дают интернет.'],['If you switch Auto on, it can also move your traffic from the main VPN to a reserve VPN when the main one fails, and back when it recovers.','Если включить Auto, она ещё может переводить трафик с основного VPN на резервный, когда основной отказывает, и возвращать обратно, когда он восстановился.']],
   example:['Example: your main VPN is Germany · WireGuard, the reserve is Netherlands · OpenVPN. Germany stops working at night; Auto moves you to the Netherlands, and back in the morning.','Пример: основной VPN — Германия · WireGuard, резерв — Нидерланды · OpenVPN. Ночью Германия перестала работать; Auto переводит вас на Нидерланды, а утром возвращает.'],
   tip:['It does not create VPN profiles and does not connect VPNs you did not connect.','Она не создаёт VPN-профили и не подключает VPN, которые вы не подключали.']},
  {icon:'②',title:['Before you start: two ways to connect','Перед началом: два способа подключения'],
   body:[['Prepare two ways to reach the router: a laptop connected by a LAN cable, and a device on Wi-Fi (a phone or the same laptop). Keep both during the first tests.','Подготовьте два способа попасть на роутер: ноутбук, подключённый кабелем LAN, и устройство по Wi-Fi (телефон или тот же ноутбук). Держите оба на время первых тестов.'],['The cable is the reliable path for tests: it does not depend on Wi-Fi. Wi-Fi shows what your family devices will really experience. If the internet disappears, you can still open the router from the other path.','Кабель — надёжный путь для тестов: он не зависит от Wi-Fi. Wi-Fi показывает, что реально увидят устройства домашних. Если интернет пропадёт, вы всё равно сможете открыть роутер другим путём.'],['Also keep mobile data on your phone: it works even when the router VPN is broken.','Также держите мобильный интернет на телефоне: он работает, даже если VPN роутера сломан.']],
   example:['Example: laptop on the cable runs the check; the phone on Wi-Fi opens a site to confirm that Wi-Fi users have internet too.','Пример: ноутбук на кабеле запускает проверку; телефон по Wi-Fi открывает сайт, чтобы подтвердить, что интернет есть и у пользователей Wi-Fi.'],
   tip:['Never test only from one device that you cannot afford to lose.','Не тестируйте только с одного устройства, которое нельзя потерять.']},
  {icon:'③',title:['First start','Первый запуск'],
   body:[['Open Services → HomenS.AI Auto VPN. On the first screen read the terms and tick both boxes: this is experimental software that you use at your own risk.','Откройте «Службы» → HomenS.AI Auto VPN. На первом экране прочитайте условия и отметьте оба флажка: это экспериментальное ПО, вы используете его на свой риск.'],['Then open Settings → Monitor service and press Start. The traffic light turns green when fresh data arrives (up to a minute). Auto stays off.','Затем откройте «Настройки» → «Служба мониторинга» и нажмите «Старт». Светофор станет зелёным, когда придут свежие данные (до минуты). Auto остаётся выключенным.']],
   example:['Example: after pressing Start the light is yellow “Starting”, then green “Monitor is running”.','Пример: после «Старт» светофор жёлтый «Запускается», затем зелёный «Мониторинг работает».'],
   tip:['Grey means switched off, red means switched on but not working: open Help.','Серый — выключен, красный — включён, но не работает: откройте «Помощь».']},
  {icon:'④',title:['Setup','Настройка'],
   body:[['Settings → Setup → 1 · System: choose the primary and the reserve profile. Choose a different country or provider for the reserve.','«Настройки» → «Настройка» → 1 · Система: выберите основной и резервный профили. Для резерва берите другую страну или другого провайдера.'],['2 · Telegram is optional: create a bot with @BotFather, press Start in it, enter the token and your Chat ID, then press “Test Telegram delivery”. Under each step open “What is this and how to fill it in” for examples.','2 · Telegram — по желанию: создайте бота через @BotFather, нажмите в нём Start, введите токен и свой ID чата и нажмите «Проверить доставку Telegram». Под каждым шагом откройте «Что это и как заполнить» — там примеры.'],['Rules for switching and check intervals are in “Advanced settings”. The defaults are safe.','Правила переключения и интервалы проверок — в «Расширенных настройках». Значения по умолчанию безопасны.']],
   example:['Example: primary 1 = Germany · WireGuard, reserve 2 = Netherlands · OpenVPN.','Пример: основной 1 = Германия · WireGuard, резерв 2 = Нидерланды · OpenVPN.'],
   tip:['The bot token is a secret. Never post it or send it to anyone.','Токен бота — секрет. Никому не публикуйте и не отправляйте его.']},
  {icon:'⑤',title:['Step 1: check the VPNs, Step 2: turn on Auto','Шаг 1: проверить VPN, шаг 2: включить Auto'],
   body:[['On Overview press “Step 1 · Check the VPNs now”. It tests right away which connected VPNs give internet. Fix problems first.','На «Обзоре» нажмите «Шаг 1 · Проверить VPN сейчас». Сразу проверит, какие подключённые VPN дают интернет. Сначала устраните проблемы.'],['Step 2: Auto can be started only after a passed LAN trial. Download the LAN helper and run it on a Windows computer in your network, preferably on the cable. The page lists exactly which step is missing. Then press the Auto button.','Шаг 2: Auto можно запустить только после успешного LAN-теста. Скачайте LAN-помощник и запустите его на компьютере с Windows в вашей сети, лучше по кабелю. Страница показывает, какого шага не хватает. Затем нажмите кнопку Auto.'],['The Auto light: green — watching the primary; yellow — switching; orange — working on the reserve; red — needs your attention; grey — off.','Светофор Auto: зелёный — следит за основным; жёлтый — переключается; оранжевый — работает на резерве; красный — нужно ваше внимание; серый — выключен.']],
   example:['Example: green Auto light and “2 of 2 VPNs work” means everything is fine.','Пример: зелёный светофор Auto и «работают 2 из 2 VPN» — всё в порядке.'],
   tip:['Do not turn Auto on when you cannot afford a short interruption (a call, a download).','Не включайте Auto, когда нельзя терпеть короткий перерыв (звонок, загрузка).']},
  {icon:'⑥',title:['Reading the pages','Как читать страницы'],
   body:[['Overview: the Auto control and the state of your VPNs. Channels and servers: every VPN profile with its country and protocol (OpenVPN or WireGuard); the list comes from your router and changes when you add or remove profiles there.','«Обзор»: управление Auto и состояние ваших VPN. «Каналы и серверы»: каждый VPN-профиль со страной и протоколом (OpenVPN или WireGuard); список берётся с роутера и меняется, когда вы добавляете или удаляете профили.'],['Statistics shows how the VPNs behaved over time. “Advanced” (for administrators) holds the tests, rankings, traffic, service log, events and readiness.','«Статистика» показывает, как вели себя VPN со временем. «Расширенное» (для администраторов) содержит тесты, рейтинги, трафик, журнал службы, события и готовность.']],
   example:['Example: a server with only 3 checks is not a leader yet: the ranking needs at least 20 checks.','Пример: сервер всего с 3 проверками ещё не лидер: рейтингу нужно не меньше 20 проверок.'],
   tip:['Speed tests are optional and use traffic; they live under Advanced → Tests.','Тесты скорости необязательны и расходуют трафик; они в «Расширенное» → «Тесты».']},
  {icon:'⑦',title:['If the internet is gone','Если пропал интернет'],
   body:[['First stay calm: use mobile data on your phone to read Help. Open the router page by the cable or Wi-Fi and look at Overview.','Сначала спокойно: откройте «Помощь» на телефоне через мобильный интернет. Откройте страницу роутера по кабелю или Wi-Fi и посмотрите «Обзор».'],['If the router is on the reserve, press “Return to primary”. Still no internet? Connect by SSH and run the helper commands: `homensai-vpn-emergency show` (only reads), `homensai-vpn-emergency stop-auto` (stops the program’s services), `homensai-vpn-emergency remove-guard` (removes only the program’s own traffic block).','Если роутер на резерве, нажмите «Вернуться на основной». Интернета всё нет? Подключитесь по SSH и выполните команды помощника: `homensai-vpn-emergency show` (только чтение), `homensai-vpn-emergency stop-auto` (останавливает службы программы), `homensai-vpn-emergency remove-guard` (снимает только собственную блокировку трафика программы).'],['Then check GL.iNet → VPN → VPN Dashboard: the primary first, tunnels connected. Help → “I have no internet” has every step.','Затем проверьте GL.iNet → VPN → VPN Dashboard: основной первым, туннели подключены. В «Помощи» → «У меня пропал интернет» — все шаги.']],
   example:['Example: the page says “on reserve” and the internet is slow: press “Return to primary”; the router checks the primary first.','Пример: страница пишет «на резерве», интернет медленный: нажмите «Вернуться на основной»; роутер сначала проверит основной.'],
   tip:['Reading with `show` is always safe; run the other commands only when you need to.','Чтение командой `show` всегда безопасно; остальные команды запускайте, только когда нужно.']},
  {icon:'⑧',title:['Safety rules','Правила безопасности'],
   body:[['This is experimental software: it can interrupt your internet. You use it at your own risk and keep another way to reach the router.','Это экспериментальное ПО: оно может прервать интернет. Вы используете его на свой риск и сохраняете другой способ попасть на роутер.'],['Never share the router password, the Telegram token, VPN files or backups with anyone, including chats and support. After tests, change the router password if you typed it anywhere.','Никому не передавайте пароль роутера, токен Telegram, VPN-файлы и резервные копии, в том числе в чатах и поддержке. После тестов смените пароль роутера, если вводили его где-либо.'],['When unsure: leave Auto off. The monitor alone is read-only and safe.','Когда не уверены — оставьте Auto выключенным. Один только мониторинг только читает и безопасен.']],
   example:['Example: a person asks in a chat for your token “to help”. Do not send it.','Пример: в чате просят ваш токен «чтобы помочь». Не отправляйте.'],
   tip:['You can come back to this training at any time from the menu.','К этому обучению можно вернуться в любой момент из меню.']}
];
var LEARN_QUIZ=[
  {q:['What does the system do when Auto is OFF?','Что делает система при выключенном Auto?'],o:[['Only watches and shows the state of your VPNs','Только наблюдает и показывает состояние ваших VPN',true],['Switches to the reserve VPN by itself','Сама переключается на резервный VPN',false],['Creates new VPN profiles','Создаёт новые VPN-профили',false]]},
  {q:['Which ways to connect should you prepare for the first tests? (several answers)','Какие способы подключения нужно подготовить для первых тестов? (несколько ответов)'],o:[['A laptop on a LAN cable','Ноутбук на кабеле LAN',true],['A device on Wi-Fi','Устройство по Wi-Fi',true],['Only one device that you cannot lose','Только одно устройство, которое нельзя потерять',false],['Mobile data on the phone','Мобильный интернет на телефоне',true]]},
  {q:['What is the right order to start working?','Каков правильный порядок начала работы?'],o:[['Accept the terms, start the monitor, check the VPNs, then turn on Auto','Принять условия, запустить мониторинг, проверить VPN, затем включить Auto',true],['Turn on Auto first, check later','Сначала включить Auto, проверить потом',false],['Skip the terms and start Auto','Пропустить условия и сразу запустить Auto',false]]},
  {q:['What must pass before Auto can be started?','Что должно пройти перед запуском Auto?'],o:[['The LAN trial with the helper on a computer in your network','LAN-тест с помощником на компьютере в вашей сети',true],['A speed test','Тест скорости',false],['A Telegram message','Сообщение в Telegram',false]]},
  {q:['The Auto light is orange. What does it mean?','Светофор Auto оранжевый. Что это значит?'],o:[['Traffic works on the reserve','Трафик идёт через резерв',true],['Everything is on the primary','Всё идёт через основной',false],['Auto is off','Auto выключен',false]]},
  {q:['Which of these is a secret that you never send to anyone? (several answers)','Что из этого — секрет, который никому нельзя отправлять? (несколько ответов)'],o:[['The Telegram bot token','Токен Telegram-бота',true],['The router password','Пароль роутера',true],['The country of a VPN server','Страна VPN-сервера',false]]},
  {q:['The internet is gone. What do you do first?','Интернета нет. Что делаете сначала?'],o:[['Open the router page by cable or Wi-Fi and press “Return to primary” if it is on the reserve','Открываете страницу роутера по кабелю или Wi-Fi и нажимаете «Вернуться на основной», если он на резерве',true],['Flash the router firmware','Прошиваете роутер',false],['Delete all VPN profiles','Удаляете все VPN-профили',false]]},
  {q:['Which command only reads the state and is always safe?','Какая команда только читает состояние и всегда безопасна?'],o:[['homensai-vpn-emergency show','homensai-vpn-emergency show',true],['homensai-vpn-emergency stop-auto','homensai-vpn-emergency stop-auto',false],['homensai-vpn-emergency remove-guard','homensai-vpn-emergency remove-guard',false]]}
];
// A question is correct only when the chosen set equals the set of right options.
function learnGrade(question,chosen){
  var ok=true;
  var marks=question.o.map(function(option,index){
    var picked=chosen.indexOf(index)>=0,right=option[2]===true;
    if(picked!==right)ok=false;
    return picked&&right?'right':picked&&!right?'wrong':!picked&&right?'missed':'none';
  });
  return {ok:ok&&chosen.length>0,marks:marks};
}
function learnScore(quiz,answers){
  var correct=0;
  quiz.forEach(function(question,index){if(learnGrade(question,answers[index]||[]).ok)correct++;});
  return {correct:correct,total:quiz.length,percent:quiz.length?Math.round(correct*100/quiz.length):0};
}
function learnVerdict(percent){
  if(percent>=80)return bi('Well done. You know enough to use the system.','Отлично. Вы знаете достаточно, чтобы пользоваться системой.');
  if(percent>=50)return bi('Almost there. Read the cards again before you turn on Auto.','Почти. Перечитайте карточки, прежде чем включать Auto.');
  return bi('Please go through the cards again before you use the system.','Пожалуйста, пройдите карточки ещё раз, прежде чем пользоваться системой.');
}
function renderLearn(){
  var host=E('section',{'class':'hv-chart-card hv-learn'});
  var step=0,answers=[],checked=false,total=LEARN_LESSONS.length+LEARN_QUIZ.length+1;
  function clear(){while(host.firstChild)host.removeChild(host.firstChild);}
  function inline(text){var parts=String(text).split('`');return parts.map(function(part,i){return i%2?E('code',{},part):part;});}
  function progress(){return E('div',{'class':'hv-learn-progress','role':'progressbar','aria-valuemin':'0','aria-valuemax':String(total),'aria-valuenow':String(step+1)},[E('span',{'style':'width:'+Math.round((step+1)*100/total)+'%'}),E('small',{},bi('Step ','Шаг ')+(step+1)+' / '+total)]);}
  function nav(back,next,nextLabel,nextDisabled){
    return E('div',{'class':'hv-learn-nav'},[back?E('button',{'type':'button','class':'cbi-button','click':back},bi('Back','Назад')):E('span'),next?E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':nextDisabled?'disabled':null,'click':next},nextLabel):E('span')]);
  }
  function lesson(){
    var l=LEARN_LESSONS[step];
    host.appendChild(progress());
    if(step===0)host.appendChild(E('p',{'class':'hv-learn-intro'},bi('A short training, about 5 minutes: what the system is, how to set it up and use it, and what to do when something goes wrong. At the end there are questions.','Короткое обучение, около 5 минут: что это за система, как её настроить и использовать и что делать, если что-то пошло не так. В конце — вопросы.')));
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('div',{'class':'hv-learn-icon','aria-hidden':'true'},l.icon),E('h2',{},bi(l.title[0],l.title[1])),
      E('div',{'class':'hv-learn-body'},l.body.map(function(p){return E('p',{},inline(bi(p[0],p[1])));})),
      E('p',{'class':'hv-learn-example'},inline(bi(l.example[0],l.example[1]))),
      E('p',{'class':'hv-learn-tip'},[E('strong',{},bi('Remember: ','Запомните: ')),inline(bi(l.tip[0],l.tip[1]))])]));
    host.appendChild(nav(step>0?function(){step--;draw();}:null,function(){step++;draw();},step===LEARN_LESSONS.length-1?bi('To the questions','К вопросам'):bi('Next','Дальше')));
  }
  function question(){
    var index=step-LEARN_LESSONS.length,q=LEARN_QUIZ[index],chosen=answers[index]||(answers[index]=[]);
    var grade=checked?learnGrade(q,chosen):null;
    host.appendChild(progress());
    var options=q.o.map(function(option,i){
      var mark=grade?grade.marks[i]:'none';
      var box=E('input',{'type':'checkbox','disabled':checked?'disabled':null,'change':function(){var at=chosen.indexOf(i);if(box.checked&&at<0)chosen.push(i);if(!box.checked&&at>=0)chosen.splice(at,1);draw();}});
      box.checked=chosen.indexOf(i)>=0;
      var note=mark==='right'?bi('Correct','Верно'):mark==='wrong'?bi('Wrong choice','Неверный выбор'):mark==='missed'?bi('This was a correct answer','Это был правильный ответ'):'';
      return E('label',{'class':'hv-quiz-option hv-quiz-'+mark},[box,E('span',{},bi(option[0],option[1])),note?E('small',{},note):null].filter(Boolean));
    });
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('div',{'class':'hv-learn-icon','aria-hidden':'true'},'?'),E('h2',{},bi('Question ','Вопрос ')+(index+1)+' / '+LEARN_QUIZ.length),E('p',{'class':'hv-quiz-question'},bi(q.q[0],q.q[1])),E('div',{'class':'hv-quiz-options'},options),
      grade?E('p',{'class':'hv-quiz-result hv-quiz-result-'+(grade.ok?'ok':'bad'),'role':'status'},grade.ok?bi('Correct!','Верно!'):bi('Not quite. Red is your wrong choice, green is the right answer.','Не совсем. Красным отмечен ваш неверный выбор, зелёным — правильный ответ.')):null].filter(Boolean)));
    var last=index===LEARN_QUIZ.length-1;
    host.appendChild(nav(null,function(){if(!checked){checked=true;draw();}else{checked=false;step++;draw();}},checked?(last?bi('See my result','Узнать результат'):bi('Next question','Следующий вопрос')):bi('Check the answer','Проверить ответ'),!checked&&chosen.length===0));
  }
  function result(){
    var s=learnScore(LEARN_QUIZ,answers);
    if(s.percent>=80){try{window.localStorage.setItem('homensai-vpn-learn-done','1');}catch(e){}}
    host.appendChild(progress());
    host.appendChild(E('div',{'class':'hv-learn-card hv-learn-final'},[E('div',{'class':'hv-learn-score hv-learn-score-'+(s.percent>=80?'good':s.percent>=50?'mid':'low'),'aria-hidden':'true'},s.percent+'%'),
      E('h2',{},bi('Your knowledge: ','Ваши знания: ')+s.percent+bi(' out of 100',' из 100')),
      E('p',{},bi(s.correct+' of '+s.total+' answers were fully correct.',s.correct+' из '+s.total+' ответов полностью верны.')),
      E('p',{'class':'hv-learn-verdict'},learnVerdict(s.percent))]));
    host.appendChild(E('div',{'class':'hv-learn-nav'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){step=0;answers=[];checked=false;draw();}},bi('Take the training again','Пройти обучение заново')),E('a',{'class':'cbi-button','href':'#help'},bi('Open Help','Открыть помощь'))]));
  }
  function draw(){clear();if(step<LEARN_LESSONS.length)lesson();else if(step<LEARN_LESSONS.length+LEARN_QUIZ.length)question();else result();}
  draw();
  return host;
}
