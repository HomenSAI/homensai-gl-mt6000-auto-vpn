"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/"""
from pathlib import Path
import re

ROOT=Path(__file__).parent/'files/www/luci-static/resources/view/homensai-vpn'
source=(ROOT/'dashboard10.js').read_text(encoding='utf8')
source=source.replace('v0.2.0-alpha1','v0.2.0-alpha2').replace('HomenSAI Auto VPN','HomenS.AI Auto VPN')
loader="""
function loadBrand(){
  return ['brand','robot','brand-ui'].reduce(function(ready,name){return ready.then(function(){
    return new Promise(function(resolve,reject){
      var path=L.resource('view/homensai-vpn/style/js/'+name+'.js');
      if(document.querySelector('script[data-homensai-style="'+name+'"]')){resolve();return;}
      var script=document.createElement('script');script.src=path;script.setAttribute('data-homensai-style',name);
      script.onload=resolve;script.onerror=function(){script.remove();reject(new Error('Brand resource unavailable'));};document.head.appendChild(script);
    });
  });},Promise.resolve());
}
"""
source=source.replace('return view.extend({',loader+'\nreturn view.extend({',1)
source=source.replace("statusCall().catch(function(){return {error:'SERVICE-STOPPED'};})]);", "statusCall().catch(function(){return {error:'SERVICE-STOPPED'};}),loadBrand()]);")
source=source.replace("var colors=['#5268f4','#16a892','#f3a64b','#e674a3']", "var colors=['var(--accent)','var(--teal)','var(--gold)','var(--bad)']")
source=source.replace("stroke:'#e8edf5'","stroke:'var(--line)'").replace("fill:'#7b899f'","fill:'var(--muted)'")
source=source.replace("style:'background:'+colors[i%colors.length]", "'class':'hv-series-'+(i%colors.length)")
source=source.replace("[['up','#16a892'],['down','#e46673'],['unknown','#a8b3c6']]", "[['up','var(--ok)'],['down','var(--bad)'],['unknown','var(--muted)']]")
# SVG uses data dimensions instead of style attributes for histogram segments.
source=source.replace("var total=r.t.up+r.t.down+r.t.unknown,bar=E('div',{'class':'hv-stack'});", "var total=r.t.up+r.t.down+r.t.unknown,bar=document.createElementNS('http://www.w3.org/2000/svg','svg'),offset=160;bar.setAttribute('class','hv-stack');bar.setAttribute('viewBox','0 0 68 160');")
old="if(value)bar.appendChild(E('span',{style:'height:'+percent+'%;background:'+entry[1],title:entry[0]+': '+(value/3600).toFixed(2)+' h · '+percent.toFixed(1)+'%'},percent>=12?percent.toFixed(0)+'%':''));"
new="""if(value){var ns='http://www.w3.org/2000/svg',rect=document.createElementNS(ns,'rect'),title=document.createElementNS(ns,'title');var height=percent*1.6;offset-=height;rect.setAttribute('x','0');rect.setAttribute('y',offset);rect.setAttribute('width','68');rect.setAttribute('height',height);rect.setAttribute('fill',entry[1]);title.textContent=entry[0]+': '+(value/3600).toFixed(2)+' h · '+percent.toFixed(1)+'%';rect.appendChild(title);bar.appendChild(rect);if(percent>=12){var label=document.createElementNS(ns,'text');label.setAttribute('x','34');label.setAttribute('y',offset+height/2+4);label.setAttribute('text-anchor','middle');label.setAttribute('class','hv-stack-label');label.textContent=percent.toFixed(0)+'%';bar.appendChild(label);}}"""
if old not in source:raise SystemExit('Histogram adapter mismatch')
source=source.replace(old,new)
source=source.replace("return m.render().then(function(form){return E('div',{'class':'hv-app'},[", "return m.render().then(function(form){var robotHost=E('div',{'class':'robo','aria-label':bi('HomenS.AI author robot','Робот автора HomenS.AI')}),footer=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(footer,locale,'platform');setTimeout(function(){var robot=window.HomenS.robot.tvRobot(robotHost);robot.play();robotHost.addEventListener('click',function(){robot.play();});},0);return E('div',{'class':'hv-app'},[")
source=source.replace("E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui8.css')}),", "E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/charts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui11.css')}),")
source=source.replace("E('header',{'class':'hv-hero'},[", "E('header',{'class':'hv-hero'},[E('div',{'class':'hv-brand-mark'},[robotHost,E('p',{'class':'robo-word'},['HomenS',E('span',{'class':'ai'},'.AI')])]),")
source=source.replace("},'HomenS.AI Auto VPN')),E('p'", "},['HomenS',E('span',{'class':'ai'},'.AI'),E('small',{'class':'hv-product'},' Auto VPN')])),E('p'",1)
source=source.replace("E('span',{'class':'hv-version'},'v0.2.0-alpha2'),", "E('span',{'class':'hv-version'},'v0.2.0-alpha2'),E('small',{},'HomenS.AI Style 1.14.3'),")
source=source.replace("):null,form])]);});", "):null,form]),footer]);});")
source='// HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/\n'+source
(ROOT/'dashboard11.js').write_text(source,encoding='utf8')

css=(ROOT/'ui8.css').read_text(encoding='utf8')
mapping={
'#172843':'text','#75849c':'muted','#f3f6fb':'bg','#152542':'surface','#263c6b':'bg','#c0cde5':'muted','#9eafff':'teal','#5d72f6':'accent',
'#dce4f3':'line','#edf2fc':'bg','#526783':'muted','#e1e7f1':'line','#16a892':'ok','#df9554':'warn','#596cf0':'accent','#e2f6ee':'bg','#148460':'ok',
'#edf0f5':'bg','#fff0df':'bg','#ad601d':'warn','#f9fbfe':'surface','#edf0f6':'bg','#7b899f':'muted','#14243d':'pv-term','#c4d2e8':'pv-term-text',
'#dce4f1':'line','#5366d8':'accent','#d4ddff':'muted','#52648a':'line','#243959':'surface'}
css=re.sub(r'#[a-fA-F0-9]{6}',lambda m:'var(--'+mapping[m[0].lower()]+')' if m[0].lower() in mapping else m[0],css)
css=css.replace('background:white','background:var(--surface)').replace('color:white','color:var(--text)')
css=css.replace('system-ui,-apple-system,Segoe UI,sans-serif','"IBM Plex Sans",system-ui,sans-serif').replace('ui-monospace,monospace','"IBM Plex Mono",monospace')
css+='''
.hv-app{border-radius:var(--radius)}.hv-hero h2 a{color:var(--text)}.hv-app .hv-test{color:var(--accent-text)}.hv-brand-mark{flex:0 0 116px;text-align:center}.hv-brand-mark .robo{width:116px;height:116px;margin:0;border-width:3px}.hv-brand-mark .robo-word{font-size:16px;margin:8px 0 0;opacity:1}.hv-brand-mark .ai{color:var(--teal)}.hv-hero>div:nth-child(2){flex:1}.hv-hero-actions{color:var(--muted)}.hv-legend .hv-series-0{background:var(--accent)}.hv-legend .hv-series-1{background:var(--teal)}.hv-legend .hv-series-2{background:var(--gold)}.hv-legend .hv-series-3{background:var(--bad)}.hv-stack-label{fill:var(--accent-text);font-size:11px;font-weight:600}.hv-brand-footer{margin-top:24px;border-top:1px solid var(--line);padding-top:16px;font-size:12px;color:var(--muted)}.hv-app a{color:var(--accent)}.hv-log-time{color:var(--pv-term-time);font-family:"IBM Plex Mono",monospace}.hv-app pre .hv-ok{color:var(--pv-term-ok);background:transparent}.hv-app pre .hv-warn{color:var(--pv-term-bad);background:transparent}.hv-app pre .hv-idle{color:var(--pv-term-time);background:transparent}.hv-metric,.hv-server,.hv-chart-card,.hv-settings{border-radius:var(--radius)}
@media(max-width:600px){.hv-brand-mark{align-self:center}.hv-hero-actions{align-items:flex-start}.hv-hero{gap:16px}}
'''
css+='\n.hv-hero h2 .ai{color:var(--teal)}.hv-product{font-size:0.65em;font-weight:500;color:var(--muted)}\n'
(ROOT/'ui11.css').write_text('/* HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/ */\n'+css,encoding='utf8')
