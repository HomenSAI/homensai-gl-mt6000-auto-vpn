/* Optional catalogue UI. Pure rendering/search; no RPC, settings or control. */
function catalogueText(ru,en,lang){return lang==='en'?en:ru;}
function catalogueEscape(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function catalogueFold(value){return String(value||'').toLowerCase().replace(/ё/g,'е').replace(/[‐‑‒–—−]/g,'-');}
function codeCatalogueState(rows,query,page){
  var words=catalogueFold(query).trim().split(/\s+/).filter(Boolean);
  var all=rows.filter(function(r){return r&&typeof r[0]==='string';}).slice().sort(function(a,b){return a[0]<b[0]?-1:a[0]>b[0]?1:0;});
  var matched=all.filter(function(r){var text=catalogueFold(r.slice(0,10).join(' ')),prefix=r[0].endsWith('*')?catalogueFold(r[0]).slice(0,-1):'';return words.every(function(word){return text.indexOf(word)>=0||(prefix&&word.indexOf(prefix)===0);});});
  var pages=Math.max(1,Math.ceil(matched.length/40)),index=Math.max(0,Math.min(pages-1,Math.floor(Number(page)||0))),showAll=page==='all';
  return {total:all.length,matched:matched.length,pages:pages,page:index,showAll:showAll,start:matched.length?(showAll?1:index*40+1):0,
    end:showAll?matched.length:Math.min(matched.length,(index+1)*40),rows:showAll?matched:matched.slice(index*40,index*40+40)};
}
function codeCatalogueResultsHTML(rows,query,page,lang){
  var s=codeCatalogueState(rows,query,page),e=catalogueEscape,t=function(ru,en){return catalogueText(ru,en,lang);};
  var summary=t('Найдено: ','Found: ')+s.matched+t(' из ',' of ')+s.total+(s.matched?t(' · Показаны ',' · Showing ')+s.start+'–'+s.end:'');
  var out='<p class="small code-count" role="status" aria-live="polite" tabindex="-1" data-code-count data-total="'+s.total+'" data-matched="'+s.matched+'">'+e(summary)+'</p>';
  if(!s.matched)return out+'<p class="note">'+t('Совпадений нет. Проверьте код или попробуйте другое слово: например, VPN, DNS, сертификат.','No matches. Check the code or try another word, such as VPN, DNS or certificate.')+'</p><button type="button" class="btn sm" data-act="codeclear">'+t('Сбросить поиск','Clear search')+'</button>';
  out+=codeCatalogueNavHTML(s,lang,'top');
  out+='<ul class="codes-list">'+s.rows.map(function(r){return '<li><button type="button" class="code-entry" data-act="code" data-code="'+e(r[0])+'"><span class="mono code-id">'+e(r[0])+'</span><span>'+e(lang==='en'?r[2]:r[3])+(r[0].endsWith('*')?'<small class="mute code-family">'+t('Семейство кодов','Code family')+'</small>':'')+'</span></button></li>';}).join('')+'</ul>';
  return out+codeCatalogueNavHTML(s,lang,'bottom');
}
function codeCatalogueNavHTML(s,lang,position){
  var out='',t=function(ru,en){return catalogueText(ru,en,lang);};
  if(s.matched>40){
    out+='<nav class="row code-pages" data-code-nav="'+position+'" aria-label="'+t('Страницы справочника','Code reference pages')+'">';
    if(!s.showAll){out+='<button type="button" class="btn sm" data-act="codepage" data-page="'+(s.page-1)+'"'+(s.page===0?' disabled':'')+'>'+t('Назад','Previous')+'</button><label>'+t('Страница ','Page ')+'<select class="inp" data-act="codepage" aria-label="'+t('Номер страницы справочника','Code reference page number')+'">';
      for(var i=0;i<s.pages;i++)out+='<option value="'+i+'"'+(i===s.page?' selected':'')+'>'+(i+1)+'</option>';
      out+='</select>'+t(' из ',' of ')+s.pages+'</label><button type="button" class="btn sm" data-act="codepage" data-page="'+(s.page+1)+'"'+(s.page===s.pages-1?' disabled':'')+'>'+t('Далее','Next')+'</button>';}
    out+='<button type="button" class="btn sm ghost" data-act="codepage" data-page="'+(s.showAll?'0':'all')+'">'+(s.showAll?t('По 40 кодов','40 codes per page'):t('Показать все ','Show all ')+s.matched)+'</button></nav>';
  }
  return out;
}
function codeCataloguePanelHTML(rows,query,page,lang){
  var t=function(ru,en){return catalogueText(ru,en,lang);},e=catalogueEscape;
  return '<h3>'+t('Справочник кодов','Code reference')+'</h3><p class="small mute">'+t('Ошибки, предупреждения и обычные события программы. Найдите код или опишите проблему; нажмите запись, чтобы прочитать объяснение и действия. Звёздочка * обозначает семейство кодов: можно искать и полный код из журнала.','Errors, warnings and normal program events. Enter a code or describe the problem; open an entry for its explanation and next steps. An asterisk * marks a code family; you can also search for a full code from the log.')+'</p><label class="code-search">'+t('Поиск по всему справочнику','Search the whole reference')+'<input type="search" maxlength="256" class="inp" data-act="codeq" aria-label="'+t('Код, объяснение или действие','Code, explanation or action')+'" value="'+e(query)+'" placeholder="'+t('Например: DNS, сертификат, нет интернета','For example: DNS, certificate, no internet')+'"></label><div data-codes>'+codeCatalogueResultsHTML(rows,query,page,lang)+'</div>';
}
function catalogueSteps(text){
  var lines=String(text||'').trim().split(/\n+/).map(function(line){return line.trim().replace(/^(?:\d+[.)]|[-*•])\s+/,'');}).filter(Boolean);
  if(lines.length>1)return lines;
  return (lines[0]||'').split(/([.!?])\s+(?=[A-ZА-ЯЁ])/).reduce(function(out,part){
    if(!part)return out;if(/^[.!?]$/.test(part)&&out.length)out[out.length-1]+=part;else if(part.trim())out.push(part.trim());return out;
  },[]);
}
function codeCatalogueBodyHTML(row,code,lang){
  var t=function(ru,en){return catalogueText(ru,en,lang);},e=catalogueEscape,r=row||[],title=lang==='en'?r[2]:r[3],why=lang==='en'?r[4]:r[5],action=lang==='en'?r[6]:r[7],example=lang==='en'?r[8]:r[9];
  var out='<section class="code-guide" data-cb="'+e(code)+'"><p class="code-summary"><strong>'+e(title||code)+'</strong></p><h3>'+t('Что это значит','What it means')+'</h3><p>'+e(why||t('Подробное объяснение для этого кода пока не подготовлено.','A detailed explanation for this code is not available yet.'))+'</p><h3>'+t('Что делать','What to do')+'</h3>';
  var steps=catalogueSteps(action||t('Сохраните код и время появления сообщения. Откройте помощь по диагностике, если сообщение повторяется.','Save the code and the time it appeared. Open the diagnostics help if the message repeats.'));
  out+='<ol class="code-steps">'+steps.map(function(step){return '<li>'+e(step)+'</li>';}).join('')+'</ol>';
  if(example)out+='<details class="code-tech"><summary>'+t('Пример и технические подробности','Example and technical details')+'</summary><p>'+e(example)+'</p></details>';
  return out+'</section>';
}
