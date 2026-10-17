const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync('router/sidebar_layout.inc.js','utf8'),c);
for(const [width,height,header,top] of [[978,808,78,90],[1280,720,40,60],[1024,600,50,100],[800,480,50,62],[1280,300,40,52]]){
 const g=c.sidebarGeometry(height,top,header,width);assert.equal(g.mobile,false);assert(g.top>=header+12);assert(Math.max(g.top,top)+g.height<=height-12);assert(g.height>0);
}
assert.equal(c.sidebarGeometry(300,52,40,1280).tiny,true);
for(const width of [360,414,640,760])assert.equal(c.sidebarGeometry(360,100,80,width).mobile,true);
console.log('PASS: constrained-height sidebar geometry, external header clearance, tiny-panel fallback and mobile wrap');
