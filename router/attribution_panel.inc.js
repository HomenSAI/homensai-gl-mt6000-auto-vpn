/* Owner attributes: product name, device, developer, version/package/page and style. Shown at the bottom of every page in every design; no design may hide it. */
var HV_STYLE_VERSION='HomenS.AI Style 1.14.3';
function renderAttribution(status){
  return E('div',{'class':'hv-attribution','data-hv-attribution':'1','aria-label':bi('About this program','О программе')},[
    E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI'),' Auto VPN']),
    E('span',{},routerModelLabel()),
    E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),
    E('span',{'class':'hv-attribution-version'},identityLine(status||{})),
    E('span',{},HV_STYLE_VERSION),
    attributionVersionWarning(status)
  ].filter(Boolean));
}
// Page and router program differ (old cached page or unfinished upgrade): a quiet link to the Help topic that explains it.
function attributionVersionWarning(status){
  var model=identityModel(status||{});
  if(!model.pageOld&&!model.packageMismatch)return null;
  return E('span',{'class':'hv-attribution-warn'},[helpLink('stale',bi('Page and router versions differ: press Ctrl+F5 (details)','Версии страницы и роутера различаются: нажмите Ctrl+F5 (подробнее)'))]);
}
