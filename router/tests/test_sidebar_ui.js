const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync('router/sidebar_layout.inc.js','utf8'),c);
for(const [width,height,header,top] of [[978,808,78,90],[1280,720,40,60],[1024,600,50,100],[800,480,50,62],[1280,300,40,52]]){
 const g=c.sidebarGeometry(height,top,header,width);assert.equal(g.mobile,false);assert(g.top>=header+12);assert(Math.max(g.top,top)+g.height<=height-12);assert(g.height>0);
}
assert.equal(c.sidebarGeometry(300,52,40,1280).tiny,true);
for(const width of [360,414,640,760])assert.equal(c.sidebarGeometry(360,100,80,width).mobile,true);
console.log('PASS: constrained-height sidebar geometry, external header clearance, tiny-panel fallback and mobile wrap');

// Opening another page always scrolls to the top; the first draw and refreshes of the same page do not.
{
  const fs3=require('fs'),a3=require('assert');
  const menu=JSON.parse(fs3.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
  const page=fs3.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+menu['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
  const start=page.indexOf('function showPage(key){');a3(start>0);
  const body=page.slice(start,page.indexOf('\n    }',start));
  a3(body.includes('var oldTab=activeTab;'));
  a3(/if\(oldTab!==key\)\{try\{window\.scrollTo\(0,0\)/.test(body),'scroll only on a real page change');
  // showPage must set activeTab before it compares, so a refresh of the same page never jumps.
  a3(body.indexOf('var oldTab=activeTab;')<body.indexOf('window.scrollTo(0,0)'));
  console.log('PASS: switching pages scrolls to the top');
}
