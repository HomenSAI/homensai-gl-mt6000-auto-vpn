/* The same canonical registry as documentation, without long texts in the first screen.
   VENDOR-BUSY-*: no eager name either (shipped main module budget, test_lazy_help_ui.js): the first screen shows the code, the
   whole row comes with the optional module. */
'use strict';
const write=process.stdout.write;
process.stdout.write=function(text){
 const data=JSON.parse(text),en=data.languages.en.topics.find(t=>t.id==='telegram'),ru=data.languages.ru.topics.find(t=>t.id==='telegram');
 const telegram={id:'telegram',steps:en.steps.slice(0,5).map((step,i)=>({t:[step.text,ru.steps[i].text],c:step.command}))};
 write.call(process.stdout,JSON.stringify({rows:data.errorRows.filter(row=>!row[0].startsWith('VENDOR-BUSY-')).map(row=>row.slice(0,4)),telegram}));return true;
};
require('./export_documentation.js');
