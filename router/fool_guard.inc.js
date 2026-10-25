/* Fool-proofing helpers shared by every page and wizard (owner decision 18 Oct 2026, "clueless grandfather" user).
   1. ONE table of allowed number ranges (FOOL_RANGES). The backend bounds are authoritative; qa tests compare this table with them.
   2. Number fields: the allowed range is printed under the field, a wrong value turns the field red with a plain message and
      the Save/Next button stays disabled until it is fixed. The typed value is never changed silently.
   3. guardedAction(button,fn,opts): a button that sends an RPC is disabled while it works ("Working…"), then stays disabled
      for 10 seconds with a visible countdown ("Wait 7 s"). Extra clicks are ignored (no second RPC).
   4. confirmAction(): "Are you sure?" dialog (ui.showModal, never window.confirm) that gates the RPC. */
var FOOL_PAUSE_SECONDS=10;
// key -> [min, max, unit EN, unit RU, label EN, label RU]; unit is '' for plain counts.
var FOOL_RANGES={
  'system.interval':[10,300,'seconds','секунд'],
  'system.duration':[1,240,'minutes','минут'],
  'system.priority':[1,1000,'','' ],
  'telegram.interval':[5,10080,'minutes','минут'],
  'telegram.hour':[0,23,'','' ],
  'monitor.interval':[10,300,'seconds','секунд'],
  'monitor.checkpoint':[300,3600,'seconds','секунд'],
  'monitor.live_log_limit':[1,2000,'observations','наблюдений'],
  'monitor.history_days':[1,7,'days','дней'],
  'monitor.probe_limit':[1,16,'','' ],
  'speed.budget_mib':[1,32,'MiB','МиБ'],
  'speed.duration':[2,15,'seconds','секунд'],
  'speed.streams':[1,4,'','' ],
  'speed.daily_mib':[1,1024,'MiB','МиБ'],
  'speed.busy_mbps':[1,1000,'Mbps','Мбит/с'],
  // mirrors recovery_settings.py RANGES
  'recovery.failures':[3,10,'','' ],
  'recovery.successes':[2,10,'','' ],
  'recovery.cooldown':[60,1800,'seconds','секунд'],
  'recovery.min_dwell':[60,3600,'seconds','секунд'],
  'recovery.primary_successes':[2,10,'','' ],
  'recovery.primary_stable':[30,600,'seconds','секунд']
};
// Text limits that match the backend (names and channel groups 1-64 characters; chat id; bot token).
var FOOL_TEXT={name:[1,64],channel:[1,64],chat:[1,33],token:[0,120]};
function foolRangeText(key){
  var r=FOOL_RANGES[key];
  return bi('from '+r[0]+' to '+r[1]+(r[2]?' '+r[2]:''),'от '+r[0]+' до '+r[1]+(r[3]?' '+r[3]:''));
}
// Check one raw value of a number field. Returns {ok, value, message}; message is plain words (bilingual), never a code.
function foolCheckNumber(key,raw){
  var r=FOOL_RANGES[key],text=String(raw==null?'':raw),range=foolRangeText(key);
  if(text==='')return {ok:false,message:bi('This field is empty. Type a whole number '+range+'.','Поле пустое. Введите целое число '+range+'.')};
  if(!/^-?[0-9]+$/.test(text))return {ok:false,message:bi('“'+text.slice(0,20)+'” is not a whole number. Use digits only, no letters, spaces, commas or decimals. Allowed: '+range+'.','«'+text.slice(0,20)+'» — не целое число. Только цифры, без букв, пробелов, запятых и дробей. Допустимо: '+range+'.')};
  var n=Number(text);
  if(n<r[0])return {ok:false,message:bi('This number is too small. Allowed: '+range+'.','Число слишком маленькое. Допустимо: '+range+'.')};
  if(n>r[1])return {ok:false,message:bi('This number is too big. Allowed: '+range+'.','Число слишком большое. Допустимо: '+range+'.')};
  return {ok:true,value:n,message:''};
}
// Text field check (names, channel). Returns {ok,message}.
function foolCheckText(kind,raw){
  var lim=FOOL_TEXT[kind],rawText=String(raw==null?'':raw),text=rawText.trim();
  if(/[\x00-\x1f\x7f]/.test(rawText))return {ok:false,message:bi('Line breaks and control characters are not allowed.','Переносы строк и управляющие символы не допускаются.')};
  if(text.length<lim[0])return {ok:false,message:bi('This field cannot be empty. Type '+lim[0]+' to '+lim[1]+' characters.','Поле не может быть пустым. Введите от '+lim[0]+' до '+lim[1]+' символов.')};
  if(text.length>lim[1])return {ok:false,message:bi('Too long. At most '+lim[1]+' characters.','Слишком длинно. Не больше '+lim[1]+' символов.')};
  if(kind==='chat'&&!/^(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})$/.test(rawText))return {ok:false,message:bi('Enter a numeric chat ID or a channel name such as @channel_name.','Введите числовой ID чата или имя канала, например @channel_name.')};
  if(kind==='token'&&text!==''&&!/^[0-9]{6,15}:[A-Za-z0-9_-]{30,100}$/.test(rawText))return {ok:false,message:bi('Use the complete bot token from BotFather, without spaces.','Введите полный токен бота из BotFather, без пробелов.')};
  return {ok:true,message:''};
}
function foolSetText(node,text){node.textContent=text;}
/* Wrap a number input: sets min/max/step, prints the range under it, validates on every input.
   Returns {row, check}: row = <label> to append; check() re-validates, updates the red message, returns true/false.
   onChange() is called after each input so the caller can enable/disable its Save/Next button. */
function foolNumberRow(title,node,key,onChange){
  var r=FOOL_RANGES[key];
  node.setAttribute('min',String(r[0]));node.setAttribute('max',String(r[1]));node.setAttribute('step','1');node.setAttribute('inputmode','numeric');
  node.setAttribute('aria-label',title);
  var hint=E('small',{'class':'hv-fool-hint'},bi('Allowed: ','Допустимо: ')+foolRangeText(key)+'.');
  var error=E('small',{'class':'hv-fool-error','role':'alert','aria-live':'polite'},'');
  function check(){
    var res=foolCheckNumber(key,node.value);
    foolSetText(error,res.message);
    node.setAttribute('aria-invalid',res.ok?'false':'true');
    if(node.classList){if(res.ok)node.classList.remove('hv-fool-invalid');else node.classList.add('hv-fool-invalid');}
    node.fool_ok=res.ok;
    return res.ok;
  }
  function handler(){check();if(onChange)onChange();}
  if(typeof node.addEventListener==='function'){node.addEventListener('input',handler);node.addEventListener('change',handler);}
  var row=E('label',{'class':'hv-wizard-field hv-fool-field'},[E('span',{},title),node,hint,error]);
  check();
  return {row:row,check:check,node:node,error:error};
}
// The same for a text input (name, channel).
function foolTextRow(title,node,kind,onChange,required){
  var lim=FOOL_TEXT[kind];
  node.setAttribute('maxlength',String(lim[1]));node.setAttribute('aria-label',title);
  var hint=E('small',{'class':'hv-fool-hint'},bi(lim[0]+' to '+lim[1]+' characters.','от '+lim[0]+' до '+lim[1]+' символов.'));
  var error=E('small',{'class':'hv-fool-error','role':'alert','aria-live':'polite'},'');
  function check(){
    var res=foolCheckText(kind,node.value);
    if(required&&String(node.value||'').trim()==='')res={ok:false,message:bi('Paste the bot token from BotFather. No stored token is available.','Вставьте токен бота из BotFather. Сохранённого токена нет.')};
    foolSetText(error,res.message);node.setAttribute('aria-invalid',res.ok?'false':'true');
    if(node.classList){if(res.ok)node.classList.remove('hv-fool-invalid');else node.classList.add('hv-fool-invalid');}
    return res.ok;
  }
  function handler(){check();if(onChange)onChange();}
  if(typeof node.addEventListener==='function'){node.addEventListener('input',handler);node.addEventListener('change',handler);}
  var row=E('label',{'class':'hv-wizard-field hv-fool-field'},[E('span',{},title),node,hint,error]);
  check();
  return {row:row,check:check,node:node,error:error};
}
// Disable or enable a Save/Next button from a list of checks (every check also paints its own red message).
function foolGate(button,checks){
  var ok=true;checks.forEach(function(check){if(!check())ok=false;});
  if(button){button.fool_checks=checks;button.disabled=!ok||!!button.fool_lock;if(button.setAttribute)button.setAttribute('aria-disabled',button.disabled?'true':'false');}
  return ok;
}

/* ---- guardedAction ---- */
var FOOL_LOCKS=Object.create(null);
function foolLabelTarget(button,opts){return opts&&opts.status?opts.status:button;}
function foolShow(button,opts,text){
  var target=foolLabelTarget(button,opts);
  if(!button.fool_saved){
    button.fool_saved={snapshot:target.childNodes?Array.prototype.slice.call(target.childNodes):null,text:target.textContent,title:button.getAttribute?button.getAttribute('title'):null,aria:button.getAttribute?button.getAttribute('aria-label'):null};
  }
  target.textContent=text;
  if(opts&&opts.status){button.setAttribute('title',text);}
}
function foolRestore(button,opts){
  var saved=button.fool_saved,target=foolLabelTarget(button,opts);
  if(!saved)return;
  if(saved.snapshot&&saved.snapshot.length&&typeof target.appendChild==='function'){target.textContent='';saved.snapshot.forEach(function(n){target.appendChild(n);});}
  else target.textContent=saved.text==null?'':saved.text;
  if(opts&&opts.status){if(saved.title==null){if(button.removeAttribute)button.removeAttribute('title');}else button.setAttribute('title',saved.title);}
  button.fool_saved=null;
}
function foolPause(button,lock,opts){
  lock.left=FOOL_PAUSE_SECONDS;
  button.disabled=true;
  function tick(){
    if(lock.left>0){
      lock.display=lock.left;
      lock.watchers.forEach(function(w){foolShow(w.button,w.opts,bi('Wait '+lock.left+' s','Подождите '+lock.left+' с'));});
      lock.left--;
      lock.timer=setTimeout(tick,1000);
      return;
    }
    lock.timer=null;lock.phase='idle';
    if(lock.key)delete FOOL_LOCKS[lock.key];
    lock.watchers.forEach(function(w){
      w.button.fool_lock=null;foolRestore(w.button,w.opts);
      if(w.button.fool_checks)foolGate(w.button,w.button.fool_checks);else w.button.disabled=w.disabled;
    });
    lock.watchers=[];
  }
  lock.phase='pause';tick();
}
/* guardedAction(button, fn, opts): fn() must return a promise (the RPC). opts: key (shared lock for re-created buttons),
   status (node that shows the text instead of the button, for icon-only buttons), failCode (shown as a link on rejection). */
function guardedAction(button,fn,opts){
  opts=opts||{};
  var key=opts.key||null,existing=key?FOOL_LOCKS[key]:button.fool_lock;
  if(existing){guardResume(button,key,opts);return Promise.resolve(undefined);}
  var lock={key:key,phase:'work',left:0,timer:null,watchers:[]};
  if(key)FOOL_LOCKS[key]=lock;
  foolWatch(button,lock,opts);
  var promise;
  try{promise=Promise.resolve(fn());}catch(error){promise=Promise.reject(error);}
  function finish(){foolPause(button,lock,opts);}
  return promise.then(function(value){finish();return value;},function(error){
    var code=error&&safeCode(error.code)?error.code:(opts.failCode||'UI-ACTION-FAILED');
    ui.addNotification(null,E('p',{},[errorCodeLink(code),' · ',bi('The request did not finish. Wait a moment and try again.','Запрос не завершился. Подождите немного и повторите.')]));
    finish();
  });
}
/* A button that was re-created while its lock is still running (the page redraws after each refresh) continues the pause. */
function guardResume(button,key,opts){
  var lock=key?FOOL_LOCKS[key]:button.fool_lock;
  if(!lock)return button;
  foolWatch(button,lock,opts||{});
  return button;
}
function foolWatch(button,lock,opts){
  if(!lock.watchers.some(function(w){return w.button===button;}))lock.watchers.push({button:button,opts:opts,disabled:!!button.disabled});
  button.disabled=true;button.fool_lock=lock;
  foolShow(button,opts,lock.phase==='pause'?bi('Wait '+lock.display+' s','Подождите '+lock.display+' с'):bi('Working…','Выполняется…'));
}
/* Confirm dialog. Cancel closes it and nothing is sent; Confirm closes it and then calls onConfirm(). */
function confirmAction(title,paragraphs,confirmLabel,onConfirm,danger,onCancel){
  var confirmed=false;
  var body=(paragraphs||[]).map(function(text){return E('p',{},text);});
  body.unshift(E('p',{'class':'hv-fool-ask'},bi('Are you sure?','Вы уверены?')));
  var buttons=E('div',{'class':'hv-wizard-actions'},[
    E('button',{'type':'button','class':'cbi-button hv-confirm-cancel','click':function(){if(confirmed)return;confirmed=true;ui.hideModal();if(onCancel)return onCancel();}},bi('Cancel','Отмена')),
    E('button',{'type':'button','class':'cbi-button '+(danger?'cbi-button-negative hv-danger-action':'cbi-button-action hv-primary-action')+' hv-confirm-ok','click':function(){if(confirmed)return;confirmed=true;ui.hideModal();return onConfirm();}},confirmLabel)]);
  ui.showModal(title,body.concat([buttons]));
}
