/* Server answer time over the last hour: one line per server in its own colour; hovering a line or its legend entry
   highlights it and names the server. Replaces the older single-palette chart (later function declaration wins). */
var CHART_COLORS=['#2a6fd0','#e0832b','#2e9d4f','#d64545','#8b5cf6','#0ea5b7','#b8960b','#e0529c'];
function chart(samples,rows){
  var ns='http://www.w3.org/2000/svg';
  function svgNode(name,attrs,content){var n=document.createElementNS(ns,name);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,attrs[k]);});if(content)n.textContent=content;return n;}
  var good=samples.filter(function(s){return s.metric===WEBSITE_METRIC&&Number.isFinite(s.rtt_ms)&&!s.code&&s.time;});
  if(good.length<2)return E('div',{'class':'hv-empty'},bi('The chart appears after two successful measurements. There is no artificial data here.','График появится после двух успешных измерений. Искусственных данных здесь нет.'));
  var end=Math.max.apply(null,good.map(function(s){return s.time;})),start=Math.max(end-3600,Math.min.apply(null,good.map(function(s){return s.time;})));
  good=good.filter(function(s){return s.time>=start;});
  var max=Math.max(100,Math.ceil(Math.max.apply(null,good.map(function(s){return s.rtt_ms;}))/100)*100);
  var svg=svgNode('svg',{viewBox:'0 0 820 260',role:'img','class':'hv-latency','aria-label':bi('Three-site response time through VPN, milliseconds','История среднего ответа трёх сайтов через VPN в миллисекундах')});
  [0,0.5,1].forEach(function(f){var y=215-f*180;svg.appendChild(svgNode('line',{x1:55,x2:800,y1:y,y2:y,stroke:'var(--line)'}));svg.appendChild(svgNode('text',{x:5,y:y+4,fill:'var(--muted)','font-size':12},String(Math.round(max*f))+' '+(f===1?bi('ms','мс'):'')));});
  var tip=E('div',{'class':'hv-chart-tip','hidden':'hidden','role':'status'});
  var legend=E('div',{'class':'hv-legend hv-legend-interactive'});
  var wrap=E('div',{'class':'hv-chart'},[]);
  var entries=[];
  function focus(id){
    entries.forEach(function(e){var on=id===null||id===e.id;e.path.setAttribute('class',on?'hv-line hv-line-on':'hv-line hv-line-off');e.dot.setAttribute('class',on?'hv-dot-end':'hv-dot-end hv-line-off');e.item.className='hv-legend-item'+(id===e.id?' hv-legend-active':id!==null?' hv-legend-dim':'');});
  }
  rows.filter(function(p){return good.some(function(s){return s.id===p.id;});}).forEach(function(p,i){
    var color=CHART_COLORS[i%CHART_COLORS.length],name=serverTitle(p);
    var points=good.filter(function(s){return s.id===p.id;}).sort(function(a,b){return a.time-b.time;}),path='',previous;
    points.forEach(function(s){var x=55+(s.time-start)/Math.max(1,end-start)*745,y=215-s.rtt_ms/max*180;path+=(previous&&s.time-previous<=90?' L':' M')+x.toFixed(1)+','+y.toFixed(1);previous=s.time;});
    var line=svgNode('path',{d:path,fill:'none',stroke:color,'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round','class':'hv-line hv-line-on'});
    var title=svgNode('title',{},name);line.appendChild(title);
    var hit=svgNode('path',{d:path,fill:'none',stroke:'transparent','stroke-width':16,'class':'hv-line-hit'});
    var last=points[points.length-1],lx=55+(last.time-start)/Math.max(1,end-start)*745,ly=215-last.rtt_ms/max*180;
    var dot=svgNode('circle',{cx:lx.toFixed(1),cy:ly.toFixed(1),r:4.5,fill:color,'class':'hv-dot-end'});
    var measured=points.filter(function(s){return s.time>=(samples.stats_since||0);}),weight=measured.reduce(function(a,s){return a+(s.count||1);},0),avg=weight?measured.reduce(function(a,s){return a+Math.round(s.rtt_ms*(s.count||1)*10);},0)/(weight*10):null;
    var item=E('button',{'type':'button','class':'hv-legend-item','mouseenter':function(){focus(p.id);},'mouseleave':function(){focus(null);},'focus':function(){focus(p.id);},'blur':function(){focus(null);}},[E('i',{'style':'background:'+color}),E('span',{},name),E('small',{},(avg===null?'—':websiteMs(avg))+' '+bi('ms avg','мс в среднем'))]);
    function showTip(ev){
      var box=wrap.getBoundingClientRect(),x=ev.clientX-box.left,y=ev.clientY-box.top;
      var rect=svg.getBoundingClientRect(),vx=(ev.clientX-rect.left)/rect.width*820,t=start+Math.max(0,Math.min(1,(vx-55)/745))*(end-start);
      var near=points.reduce(function(b,s){return Math.abs(s.time-t)<Math.abs(b.time-t)?s:b;},points[0]);
      tip.hidden=false;tip.style.left=Math.min(Math.max(8,x+12),Math.max(8,box.width-190))+'px';tip.style.top=Math.max(4,y-48)+'px';
      tip.textContent=name+' · '+websiteMs(near.rtt_ms)+' '+bi('ms','мс')+' · '+new Date(near.time*1000).toLocaleTimeString();
      tip.style.borderColor=color;
    }
    hit.addEventListener('mousemove',function(ev){focus(p.id);showTip(ev);});
    hit.addEventListener('mouseleave',function(){focus(null);tip.hidden=true;});
    line.addEventListener('mouseenter',function(){focus(p.id);});
    svg.appendChild(hit);svg.appendChild(line);svg.appendChild(dot);
    legend.appendChild(item);entries.push({id:p.id,path:line,dot:dot,item:item});
  });
  svg.appendChild(svgNode('text',{x:55,y:247,fill:'var(--muted)','font-size':12},new Date(start*1000).toLocaleTimeString()));
  svg.appendChild(svgNode('text',{x:800,y:247,fill:'var(--muted)','font-size':12,'text-anchor':'end'},new Date(end*1000).toLocaleTimeString()));
  [svg,tip,legend,E('small',{},bi('Three-site mean, ms, last hour. Each server has its own colour; point at a line or at a name to highlight it. Gaps longer than 90 seconds are not joined.','Среднее трёх сайтов, мс · последний час. У каждого сервера свой цвет; наведите курсор на линию или на название, чтобы выделить. Разрывы длиннее 90 секунд не соединяются.'))].forEach(function(n){wrap.appendChild(n);});
  return wrap;
}
