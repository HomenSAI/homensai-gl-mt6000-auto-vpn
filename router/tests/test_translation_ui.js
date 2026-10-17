const fs=require('fs'),vm=require('vm'),assert=require('assert');
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const moduleName=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const source=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+moduleName+'.js','utf8');
const dictionary=JSON.parse(source.match(/var translations = (.*);\r?\n/)[1]);
const literals=Array.from(source.matchAll(/\btr\(("(?:[^"\\]|\\.)*")\)/g),match=>JSON.parse(match[1]));
const russian=literals.filter(value=>/[А-Яа-яЁё]/.test(value));
assert(russian.length>20,'the generated runtime should contain the actual translated calls');
for(const value of russian){assert(Object.prototype.hasOwnProperty.call(dictionary,value),'Missing English translation: '+value);assert(!/[А-Яа-яЁё]/.test(dictionary[value]),'Russian remains in English translation');}
assert(source.includes("savedLanguage='en'"));assert(source.includes("localStorage.setItem('homensai-vpn-language',chosen)"));
console.log('PASS: '+russian.length+' generated Russian literals have English translations; English default and explicit language persistence');
