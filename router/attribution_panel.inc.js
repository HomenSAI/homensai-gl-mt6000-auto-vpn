/* Owner attributes: product name, device, developer, version/package/page and style. Shown at the bottom of every page in every design; no design may hide it. */
var HV_STYLE_VERSION='HomenS.AI Style 1.14.3';
function renderAttribution(status){
  return E('div',{'class':'hv-attribution','data-hv-attribution':'1','aria-label':bi('About this program','О программе')},[
    E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI'),' Auto VPN']),
    E('span',{},'GL.iNet GL-MT6000 · Flint 2'),
    E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),
    E('span',{'class':'hv-attribution-version'},identityLine(status||{})),
    E('span',{},HV_STYLE_VERSION)
  ]);
}
