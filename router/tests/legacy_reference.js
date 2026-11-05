// The approved page (03.11.2026, router/ui) reuses the display LOGIC of the legacy pipeline: router/build_sidebar_ui.py
// runs router/legacy_page_build.py in memory and extracts freshness, health, traffic-channel, Auto/manual/monitor,
// journal and catalogue functions from it. Tests that require this module keep guarding that logic against the legacy
// page it is extracted from (qa/legacy-page/, written by the same build, never packaged). Only the current page names
// are redirected; frozen historical files (dashboard25/61/104, ui39.css) are read as before.
'use strict';
const fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'..','..');
const app=JSON.parse(fs.readFileSync(path.join(ROOT,'VERSION.json'),'utf8').replace(/^﻿/,'')).application;
const MAP=[['router/files/www/luci-static/resources/view/homensai-vpn/'+app.ui_module+'.js','qa/legacy-page/dashboard.js'],
  ['router/files/www/luci-static/resources/view/homensai-vpn/'+app.ui_stylesheet,'qa/legacy-page/ui.css'],
  ['router/build_sidebar_ui.py','router/legacy_page_build.py']];
const original=fs.readFileSync;
function target(p){
  if(typeof p!=='string')return null;
  const norm=path.resolve(process.cwd(),p).replace(/\\/g,'/').toLowerCase();
  for(const [from,to] of MAP)if(norm===path.join(ROOT,from).replace(/\\/g,'/').toLowerCase())return path.join(ROOT,to);
  return null;
}
fs.readFileSync=function(p,...rest){const t=target(p);return original.call(fs,t||p,...rest);};
module.exports={ROOT,MAP,readShipped:(p,...rest)=>original.call(fs,p,...rest)};
