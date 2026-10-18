/* Page design: A Control room (default), B Calm, C Instrument panel. Chosen in Settings, stored only in this browser. */
var HV_DESIGNS=[
  {key:'a',name:['A · Control room','A · Пульт'],
   about:['Sections as tabs across the top, full width for the content. Status, failover path and servers stay where they are now.','Разделы вкладками сверху, вся ширина отдана содержимому. Статус, путь переключения и серверы на привычных местах.'],
   suits:['Everyone. The default.','Всем. Вариант по умолчанию.']},
  {key:'b',name:['B · Calm','B · Спокойный'],
   about:['Larger text and more space. Administrator sections are hidden behind “Advanced”; on a phone the sections sit at the bottom of the screen.','Крупнее текст и больше воздуха. Разделы для администратора спрятаны за «Расширенное»; на телефоне разделы внизу экрана.'],
   suits:['People who only want to know that the internet works, and phone users.','Тем, кому важно только знать, что интернет работает, и для телефона.']},
  {key:'c',name:['C · Instrument panel','C · Приборная панель'],
   about:['A narrow icon column, compact cards, numbers and tables in a monospaced font. All sections, including administrator ones, are always visible.','Узкая колонка иконок, компактные карточки, цифры и таблицы моноширинным шрифтом. Все разделы, включая администраторские, видны всегда.'],
   suits:['The owner and testers: diagnostics, error codes, router tests.','Владельцу и тестировщикам: диагностика, коды ошибок, тесты на роутере.']}
];
var HV_DESIGN_KEY='homensai-vpn-design';
function validDesign(key){return HV_DESIGNS.some(function(d){return d.key===key;});}
function storedDesign(){try{var v=window.localStorage.getItem(HV_DESIGN_KEY);return validDesign(v)?v:'a';}catch(e){return 'a';}}
/* The design chosen in this page session; it wins over storage, so a browser that refuses storage still keeps the choice until reload. */
var HV_DESIGN_NOW=null;
function currentDesign(){return validDesign(HV_DESIGN_NOW)?HV_DESIGN_NOW:storedDesign();}
function saveDesign(key){if(!validDesign(key))return false;HV_DESIGN_NOW=key;try{window.localStorage.setItem(HV_DESIGN_KEY,key);return true;}catch(e){return false;}}
function applyDesign(root,key){if(!root)return;root.setAttribute('data-hv-design',validDesign(key)?key:'a');}
function renderDesignPicker(getRoot,onApplied){
  var current=currentDesign(),note=E('p',{'class':'hv-design-note','role':'status','aria-live':'polite'},'');
  var options=HV_DESIGNS.map(function(d){
    var input=E('input',{'type':'radio','name':'hv-design','value':d.key,'id':'hv-design-'+d.key,'checked':d.key===current?'':null,'change':function(){
      var stored=saveDesign(d.key);applyDesign(getRoot(),d.key);if(onApplied)onApplied(d.key);
      note.textContent=stored?bi(d.name[0]+' is on. It opens again next time in this browser.',d.name[1]+' включён. Он откроется и в следующий раз в этом браузере.'):bi(d.name[0]+' is on for now. This browser does not allow saving it, so it resets after a reload.',d.name[1]+' включён сейчас. Этот браузер не разрешает его сохранить, после перезагрузки он сбросится.');
    }});
    input.checked=d.key===current;
    return E('label',{'class':'hv-design-option','for':'hv-design-'+d.key},[
      input,
      E('span',{'class':'hv-design-preview hv-design-preview-'+d.key,'aria-hidden':'true'},[E('i'),E('i'),E('i'),E('i')]),
      E('strong',{},bi(d.name[0],d.name[1])),
      E('span',{'class':'hv-design-about'},bi(d.about[0],d.about[1])),
      E('span',{'class':'hv-design-suits'},[E('b',{},bi('Suits: ','Подходит: ')),bi(d.suits[0],d.suits[1])])
    ]);
  });
  return E('section',{'class':'hv-chart-card hv-design-card'},[
    E('h3',{},bi('Page design','Оформление страницы')),
    E('p',{},bi('Choose how this page looks. The data and the buttons are the same in every design. The choice is kept in this browser and opens every time you come back.','Выберите, как выглядит эта страница. Данные и кнопки одинаковые во всех вариантах. Выбор хранится в этом браузере и открывается при каждом входе.')),
    E('div',{'class':'hv-design-options','role':'radiogroup','aria-label':bi('Page design','Оформление страницы')},options),
    note
  ]);
}

/* Wizards open in LuCI's modal outside the page root; give the modal the page's design, palette and fonts. */
function installModalStyle(){
  if(typeof ui==='undefined'||!ui||ui.__hvModalStyle||typeof ui.showModal!=='function')return;
  var original=ui.showModal;ui.__hvModalStyle=true;
  ui.showModal=function(){
    var node=original.apply(ui,arguments);
    try{var dialog=node&&node.classList?node:document.querySelector('#modal_overlay .modal')||document.getElementById('qa-modal');if(dialog){dialog.classList.add('hv-app','hv-modal');dialog.setAttribute('data-hv-design',currentDesign());}}catch(e){}
    return node;
  };
}
