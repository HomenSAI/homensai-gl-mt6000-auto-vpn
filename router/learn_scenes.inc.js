/* Pure teaching scenes: no RPC, credentials, route writes or readiness side effects. */
var LEARN_SCENES=[
 [['Observe the pair','Наблюдаем пару'],['Repeated primary failures','Повторные отказы основного'],['Reserve passes checks','Резерв прошёл проверки'],['Select reserve traffic policy','Выбираем маршрут резерва']],
 [['Cable access to the router','Кабельный доступ к роутеру'],['Wi-Fi client access','Доступ клиента по Wi-Fi'],['Separate mobile connection','Независимая мобильная связь'],['Keep router access during tests','Сохраняем доступ на время тестов']],
 [['Accept the current terms once','Принимаем текущие условия один раз'],['Read introduction and training','Читаем объяснение и обучение'],['Review the eight setup steps','Проверяем восемь шагов настройки'],['Save; Auto still stays off','Сохраняем; Auto остаётся выключенным']],
 [['Configure profiles in stock VPN app','Настраиваем профили в штатном VPN'],['Bind a profile to each client','Назначаем профиль каждому клиенту'],['Assign primary and reserve roles','Выбираем роли основного и резерва'],['Save two distinct clients','Сохраняем два разных клиента']],
 [['Check current DNS and HTTPS','Проверяем свежие DNS и HTTPS'],['Confirm identity and routing readiness','Проверяем идентичность и маршруты'],['Client trial needs its own helper','Для клиентского теста нужен помощник'],['Explicit Start for the ready mode','Явно запускаем готовый режим']],
 [['Selected route and health differ','Маршрут и исправность — разные данные'],['Compare HTTPS delays','Сравниваем HTTPS-задержки'],['Explore the saved 1–24h window','Просматриваем историю 1–24 ч'],['One outage, several failed checks','Один отказ, несколько плохих проверок']],
 [['Inspect fresh observations','Смотрим свежие наблюдения'],['Keep the working reserve','Сохраняем работающий резерв'],['Diagnose the failed primary','Проверяем неисправный основной'],['Return only under valid policy/readiness','Возвращаемся по политике и готовности']],
 [['Keep keys and backups private','Храним ключи и копии приватно'],['Use the permitted existing pair','Используем разрешённую пару'],['Missing data stays unconfirmed','Нет данных — нет подтверждения'],['Training is not router certification','Обучение не заменяет проверку роутера']]
];
function renderLearnScene(lesson){
 var frames=LEARN_SCENES[lesson]||LEARN_SCENES[0],index=0,timer=null,disposed=false;
 var root=E('figure',{'class':'hv-learn-scene','data-learn-scene':String(lesson)}),drawing=E('div',{'class':'hv-learn-drawing'}),caption=E('figcaption',{'role':'status','aria-live':'polite'});
 function svg(tag,attrs,text){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,String(attrs[k]));});if(text!=null)n.textContent=text;return n;}
 function pause(){if(timer!==null){clearTimeout(timer);timer=null;}play.textContent=bi('Play','Запустить');play.setAttribute('aria-pressed','false');}
 function visible(){return root.isConnected!==false&&(!root.getClientRects||root.getClientRects().length>0);}
 function schedule(){timer=setTimeout(function(){timer=null;if(disposed||!visible()){pause();return;}index=Math.min(frames.length-1,index+1);draw();if(index===frames.length-1)pause();else schedule();},1800);}
 function action(name,label,fn){return E('button',{'type':'button','class':'cbi-button','data-scene-action':name,'click':function(){if(!disposed)fn();}},label);}
 var back=action('back',bi('Previous step','Шаг назад'),function(){pause();index=Math.max(0,index-1);draw();});
 var play=action('play',bi('Play','Запустить'),function(){if(timer!==null){pause();return;}if(index===frames.length-1){index=0;draw();}play.textContent=bi('Pause','Пауза');play.setAttribute('aria-pressed','true');schedule();});play.setAttribute('aria-pressed','false');
 var next=action('next',bi('Next step','Шаг вперёд'),function(){pause();index=Math.min(frames.length-1,index+1);draw();});
 var reset=action('reset',bi('Reset scene','Сначала'),function(){pause();index=0;draw();});
 function renderFrame(){
  while(drawing.firstChild)drawing.removeChild(drawing.firstChild);
  var reserve=(lesson===0&&index===3)||(lesson===6&&index>0),failed=(lesson===0&&index>0)||(lesson===6&&index>0);
  var image=svg('svg',{viewBox:'0 0 640 270',role:'img','aria-label':bi(frames[index][0],frames[index][1])});
  if(lesson!==0&&lesson!==6){
   frames.forEach(function(frame,i){
    var x=12+i*158,color=i===index?'#2563eb':i<index?'#13986c':'#8a929d';
    if(i<3)image.appendChild(svg('path',{d:'M'+(x+140)+' 124 h18',stroke:i<index?'#13986c':'#8a929d','stroke-width':3}));
    image.appendChild(svg('rect',{x:x,y:44,width:140,height:164,rx:14,fill:'var(--surface,#fff)',stroke:color,'stroke-width':i===index?3:1}));
    image.appendChild(svg('circle',{cx:x+70,cy:76,r:17,fill:color}));image.appendChild(svg('text',{x:x+70,y:81,'text-anchor':'middle',fill:'#fff','font-size':14},String(i+1)));
    var lines=[],line='';bi(frame[0],frame[1]).split(' ').forEach(function(word){if(line&&(line+' '+word).length>18){lines.push(line);line=word;}else line+=(line?' ':'')+word;});if(line)lines.push(line);
    lines.forEach(function(text,j){image.appendChild(svg('text',{x:x+70,y:115+j*18,'text-anchor':'middle','font-size':12,fill:'currentColor'},text));});
   });
  }else{
  var nodes=[{x:8,y:90,w:125,label:bi('Your device','Ваше устройство')},{x:174,y:90,w:125,label:bi('Router','Роутер')},{x:342,y:20,w:136,label:bi('Primary VPN','Основной VPN')},{x:342,y:170,w:136,label:bi('Reserve VPN','Резервный VPN')},{x:518,y:90,w:114,label:bi('Internet','Интернет')}];
  function link(path,active){image.appendChild(svg('path',{d:path,fill:'none',stroke:active?'#13986c':'#8a929d','stroke-width':active?5:2,'stroke-dasharray':active?'none':'6 5'}));}
  link('M133 127 H174',true);link('M299 127 H320 V57 H342',!reserve);link('M299 127 H320 V207 H342',reserve);link('M478 57 H498 V127 H518',!reserve);link('M478 207 H498 V127 H518',reserve);
  nodes.forEach(function(n,i){var selected=i===2?!reserve:i===3?reserve:true,color=i===2&&failed?'#c33b4d':selected?'#13986c':'#a16207';
   image.appendChild(svg('rect',{x:n.x,y:n.y,width:n.w,height:74,rx:13,fill:'var(--surface, #fff)',stroke:color,'stroke-width':2}));
   image.appendChild(svg('rect',{x:n.x+n.w/2-12,y:n.y+10,width:24,height:17,rx:3,fill:'none',stroke:color,'stroke-width':2}));
   image.appendChild(svg('path',{d:'M'+(n.x+n.w/2-7)+' '+(n.y+32)+' h14',stroke:color,'stroke-width':2}));
   image.appendChild(svg('text',{x:n.x+n.w/2,y:n.y+52,'text-anchor':'middle','font-size':12,fill:'currentColor'},n.label));
   if(i===2||i===3)image.appendChild(svg('text',{x:n.x+n.w/2,y:n.y+66,'text-anchor':'middle','font-size':10,fill:'currentColor'},i===2&&failed?bi('Failure in this example','Отказ в этом примере'):selected?bi('Selected','Выбран'):bi('Standby','Ожидает')));
  });
  }
  drawing.appendChild(image);caption.textContent=(index+1)+' / '+frames.length+' · '+bi(frames[index][0],frames[index][1]);
  back.disabled=index===0;next.disabled=index===frames.length-1;
  root.setAttribute('data-scene-step',String(index));
 }
 function draw(){return typeof learnKeepViewport==='function'?learnKeepViewport(root,renderFrame):renderFrame();}
 root.hvDispose=function(){disposed=true;pause();};
 root.appendChild(E('p',{'class':'hv-muted'},bi('Interactive illustration — changes only this example, never the router.','Интерактивная схема — меняется только пример, настройки роутера не затрагиваются.')));
 root.appendChild(drawing);root.appendChild(caption);root.appendChild(E('div',{'class':'hv-scene-controls'},[back,play,next,reset]));
 root.appendChild(E('ol',{'class':'hv-scene-outline'},frames.map(function(f){return E('li',{},bi(f[0],f[1]));})));
 draw();return root;
}
