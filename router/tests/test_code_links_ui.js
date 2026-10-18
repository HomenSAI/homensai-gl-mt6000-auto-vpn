const fs=require('fs'),assert=require('assert');
// Codes shown on the server-checks table, live log, incident history and Auto steps must be links to the error table.
const ui=fs.readFileSync('router/ui_logic.inc.js','utf8');
assert(ui.includes('errorCodeLink(profile.code)'),'health badge links its code');
assert(fs.readFileSync('router/fault_panel.inc.js','utf8').includes('safeCode(row.code)?errorCodeLink(row.code)'),'history codes are links');
assert(fs.readFileSync('router/auto_panel.inc.js','utf8').includes('safeCode(code)?errorCodeLink(code)'),'Auto step codes are links');
console.log('PASS: codes on checks, history and Auto steps are error-table links');
