/* Colour theme: follow the system (default), light or dark. Stored only in this browser. */
function applyTheme(mode){
  var root=document.documentElement;
  if(mode==='light'||mode==='dark')root.setAttribute('data-theme',mode);else root.removeAttribute('data-theme');
}
function storedTheme(){try{var v=window.localStorage.getItem('homensai-vpn-theme');return v==='light'||v==='dark'?v:'system';}catch(e){return 'system';}}
function renderThemeSelect(){
  var mode=storedTheme();applyTheme(mode);
  var select=E('select',{'aria-label':bi('Colour theme','Цветовая тема'),'change':function(){var v=select.value;try{window.localStorage.setItem('homensai-vpn-theme',v);}catch(e){}applyTheme(v);}},[
    E('option',{'value':'system'},bi('Theme: system','Тема: как в системе')),E('option',{'value':'light'},bi('Theme: light','Тема: светлая')),E('option',{'value':'dark'},bi('Theme: dark','Тема: тёмная'))]);
  select.value=mode;
  return select;
}
