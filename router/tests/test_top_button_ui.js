const fs=require('fs'),assert=require('assert');
// Every page and design has a Top button (bottom right) that is wired into the app root.
const build=fs.readFileSync('router/build_sidebar_ui.py','utf8'),panel=fs.readFileSync('router/design_panel.inc.js','utf8'),css=fs.readFileSync('router/design_layer.css','utf8');
assert(build.includes('installTopButton(appRoot)'),'wired into the app');
assert(panel.includes("'class':'hv-top-button'")&&panel.includes('window.scrollTo'),'button scrolls to the top');
assert(/\.hv-app \.hv-top-button\{position:fixed;right:18px;bottom:18px/.test(css),'fixed bottom-right');
assert(panel.includes('prefers-reduced-motion'),'reduced motion respected');
console.log('PASS: Top button bottom right on every page');
