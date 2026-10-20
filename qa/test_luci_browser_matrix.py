"""Only explicit slow-VM mode may extend local ubus POST deadlines."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


class BrowserMatrix(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node is required for browser harness checks')
    def test_repeated_locale_and_viewport_always_request_a_new_document(self):
        script=r"""
const fs=require('fs'),assert=require('assert'),source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function navigationTarget('),end=source.indexOf('\n  async function load(',start);
const target=new Function('let navigationSequence=0;'+source.slice(start,end)+';return navigationTarget;')();
const urls=['en','en','ru','ru','ru'].map(lang=>new URL(target(lang),'http://127.0.0.1:18912'));
assert.strictEqual(new Set(urls.map(url=>url.pathname+url.search)).size,urls.length);
urls.forEach((url,index)=>{assert.strictEqual(url.pathname,'/cgi-bin/luci/admin/services/homensai-vpn');assert.strictEqual(url.searchParams.get('lang'),index<2?'en':'ru');assert.strictEqual(url.hash,'#overview');assert.strictEqual(url.searchParams.get('hv_lab_nav'),String(index+1));});
assert.throws(()=>target('invalid'),/ACTUAL-LANGUAGE-INVALID/);
assert.strictEqual((source.match(/f\.src=navigationTarget\(group\.lang\)/g)||[]).length,3);
assert(source.includes('if(d===previousDocument)return false;'));
"""
        result=subprocess.run(['node','-e',script,str(ROOT/'lab/luci_browser_matrix.js')],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_readonly_terms_mode_refuses_acceptance_before_target_access(self):
        import importlib.util
        import sys
        from unittest.mock import patch
        with patch.object(sys,'path',[str(ROOT/'lab')]+sys.path):
            spec=importlib.util.spec_from_file_location('matrix_readonly_test',ROOT/'lab/run_luci_browser_matrix.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            with patch.object(sys,'argv',['matrix','--container','unused','--out',str(ROOT/'private/unused-test'),'--terms-only','--accept-terms-version','1']),patch.object(module,'clone_identity') as target:
                with self.assertRaisesRegex(ValueError,'READ-ONLY-TERMS-MODE-CANNOT-ACCEPT'):module.main()
                target.assert_not_called()

    @unittest.skipUnless(shutil.which('node'),'Node is required for browser harness checks')
    def test_terms_ui_requires_explicit_exact_version_before_any_click(self):
        script=r"""
const fs=require('fs'),assert=require('assert'),source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function acceptTermsGate('),end=source.indexOf('\n  function localRpc(',start);
const accept=new Function('return ('+source.slice(start,end).trim()+');')();
let clicks=0;
const button={disabled:true,click:()=>{clicks++;}},boxes=[0,1].map(()=>({checked:false,click(){clicks++;this.checked=true;button.disabled=!boxes.every(b=>b.checked);}}));
const gate={getAttribute:()=> '1',querySelectorAll:()=>boxes,querySelector:()=>button};
assert.throws(()=>accept(gate,null),/ACTUAL-CONSENT-REQUIRED/);assert.strictEqual(clicks,0);
assert.throws(()=>accept(gate,'2'),/ACTUAL-CONSENT-CONTROLS-INVALID/);assert.strictEqual(clicks,0);
const record=accept(gate,'1');assert.strictEqual(clicks,3);assert.strictEqual(record.version,'1');
assert.strictEqual(record.acceptedBefore,false);assert.strictEqual(record.acceptedAfter,false);assert(record.clickedAt>0);
"""
        result=subprocess.run(['node','-e',script,str(ROOT/'lab/luci_browser_matrix.js')],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node is required for browser harness checks')
    def test_rpc_override_is_local_bounded_opt_in_and_does_not_record_bodies(self):
        script=r"""
const fs=require('fs'),assert=require('assert'),source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function localRpc('),end=source.indexOf('\n  function safeName(',start);
function fixture(deadline){
 const metrics={requests:0,timeouts:0,overDefault:0,maxDurationMs:0,samples:[]},documents=new WeakSet();
 let now=0;
 class XHR{
  constructor(){this.timeout=20000;this.status=200;this.events={};}
  open(method,url){this.originalUrl=url;}
  send(body){this.originalBody=body;}
  addEventListener(name,fn){this.events[name]=fn;}
 }
 const w={location:{href:'http://127.0.0.1:18912/cgi-bin/luci/admin/services/homensai-vpn'},performance:{now:()=>now},XMLHttpRequest:XHR};
 const install=new Function('rpcDocuments','rpcMetrics','CFG',source.slice(start,end)+';return installRpcDeadline;')(documents,metrics,{rpcTimeout:deadline});
 const doc={};install(w,doc);const opened=XHR.prototype.open;install(w,doc);assert.strictEqual(XHR.prototype.open,opened);
 return {XHR,metrics,tick:value=>{now=value;}};
}
for(const deadline of [20,60]){
 const {XHR,metrics,tick}=fixture(deadline);
 for(const [method,url,local] of [['POST','/ubus/',true],['POST','/cgi-bin/luci/admin/ubus',true],['GET','/ubus/',false],['POST','http://192.168.8.1/ubus/',false],['POST','/luci-static/resources/a.js',false]]){
  const xhr=new XHR();xhr.open(method,url);xhr.send('PRIVATE_BODY_SESSION_SENTINEL');
  assert.strictEqual(xhr.timeout,local&&deadline===60?60000:20000);
  assert.strictEqual(xhr.originalBody,'PRIVATE_BODY_SESSION_SENTINEL');
  if(local){tick(25000);xhr.events.loadend();}
 }
 assert.strictEqual(metrics.requests,2);assert(!JSON.stringify(metrics).includes('PRIVATE_BODY_SESSION_SENTINEL'));
 assert(metrics.samples.every(row=>row.deadlineMs===(deadline===60?60000:20000)));
 const timed=new XHR();timed.open('POST','/ubus/');timed.send('PRIVATE');timed.events.timeout();tick(90000);timed.events.loadend();
 assert.strictEqual(metrics.timeouts,1);
 for(let i=0;i<300;i++){const xhr=new XHR();xhr.open('POST','/ubus/');xhr.send('PRIVATE');xhr.events.loadend();}
 assert.strictEqual(metrics.samples.length,256);
}
console.log('Local-only deadline opt-in, real timeout counter, body privacy and bounded samples PASS');
"""
        result=subprocess.run(['node','-e',script,str(ROOT/'lab/luci_browser_matrix.js')],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
