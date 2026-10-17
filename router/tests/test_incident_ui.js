const fs=require('fs'),vm=require('vm'),assert=require('assert');const c={};vm.createContext(c);vm.runInContext(fs.readFileSync('router/incident_panel.inc.js','utf8'),c);
const secret='123456789:'+('a'.repeat(30)),row={id:1,source:'<img src=x onerror=alert(1)>',target:'server',outcome:'unknown',codes:[secret,'password=hidden'],phases:[{state:'APPLYING',time:100}],extra:'never exported'};
const html=c.incidentHTML([row]);assert(!html.includes('<img'));assert(html.includes('&lt;img'));assert(!html.includes(secret));assert(!html.includes('hidden'));assert(!html.includes('never exported'));assert(!html.includes('<script'));assert(html.includes('default-src'));assert(html.includes('unknown'));assert(html.includes('not measured LAN outage'));
assert.equal(c.incidentFields({phases:[{time:Infinity}]}).phases[0],'unknown @ unknown');
assert(!c.incidentText('https://example.test/?token=private').includes('private'));
console.log('PASS: allowlisted incident detail, bounded printable HTML, CSP, XSS escaping, secret redaction and unknown evidence');
