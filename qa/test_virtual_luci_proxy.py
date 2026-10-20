import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lab'))
spec=importlib.util.spec_from_file_location('virtual_proxy',Path(__file__).resolve().parents[1]/'lab/virtual_luci_proxy.py')
proxy=importlib.util.module_from_spec(spec);spec.loader.exec_module(proxy)

class VirtualProxyTests(unittest.TestCase):
    def test_slow_mode_relay_deadlines_apply_only_to_ubus_posts(self):
        import base64,http.client,json,threading
        from http.server import ThreadingHTTPServer
        from types import SimpleNamespace
        response=SimpleNamespace(stdout=json.dumps({'status':200,'headers':[],'body':base64.b64encode(b'{}').decode()}).encode())
        with patch.object(proxy.subprocess,'run',return_value=response) as run:
            server=ThreadingHTTPServer(('127.0.0.1',0),proxy.Handler)
            server.clone_id='a'*64;server.rpc_timeout_seconds=60
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                for method,path,extended in (('POST','/ubus/',True),('POST','/cgi-bin/luci/admin/ubus',True),('GET','/ubus/',False),('POST','/luci-static/resources/a.js',False)):
                    client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                    client.request(method,path,body=b'{}' if method=='POST' else None);reply=client.getresponse();reply.read();client.close()
                    request=json.loads(run.call_args.kwargs['input'])
                    self.assertEqual(request['timeout'],65 if extended else 35)
                    self.assertEqual(run.call_args.kwargs['timeout'],70 if extended else 45)
            finally:server.shutdown();server.server_close();worker.join(timeout=5)

    def test_rpc_telemetry_retains_only_numeric_envelope_codes(self):
        import json
        secret='PRIVATE_SESSION_ARGUMENT_BODY_SENTINEL'
        values=[({'result':[6,{'token':secret}],'session':secret},[{'result':6,'error':None}]),
                ({'error':{'code':-32000,'message':secret}},[{'result':None,'error':-32000}]),
                ([{'result':[0,{'body':secret}]},{'result':[True]},{'result':['PRIVATE_SESSION_ARGUMENT_BODY_SENTINEL']}],
                 [{'result':0,'error':None},{'result':None,'error':None},{'result':None,'error':None}])]
        for value,expected in values:
            with self.subTest(value_type=type(value).__name__):
                row=proxy.rpc_codes(json.dumps(value).encode())
                self.assertEqual(row,expected);self.assertNotIn(secret,json.dumps(row))
        self.assertEqual(proxy.rpc_codes(b'broken'),[{'malformed':True}])

    def test_proxy_failures_report_only_safe_stage_status_type_and_elapsed(self):
        import http.client,json,subprocess,threading
        from http.server import ThreadingHTTPServer
        secret='PRIVATE_SESSION_ARGUMENT_BODY_SENTINEL'
        for stage in ('identity','bridge'):
            command_error=subprocess.TimeoutExpired([secret],45,output=secret)
            with self.subTest(stage=stage),patch.object(proxy,'clone_identity') as inspect,patch.object(proxy.subprocess,'run',side_effect=command_error) as run:
                server=ThreadingHTTPServer(('127.0.0.1',0),proxy.Handler)
                server.container='clone';server.clone_id=secret if stage=='identity' else 'a'*64;server.observed=[]
                worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
                try:
                    client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                    client.request('GET','/cgi-bin/luci/admin/services/homensai-vpn');reply=client.getresponse()
                    self.assertEqual(reply.status,502);reply.read();client.close()
                    self.assertEqual(len(server.observed),1);row=server.observed[0]
                    self.assertEqual(set(row),{'kind','status','stage','elapsed_ms','error_type'})
                    self.assertEqual(row['status'],502);self.assertEqual(row['stage'],stage)
                    self.assertIs(type(row['elapsed_ms']),int);self.assertGreaterEqual(row['elapsed_ms'],0)
                    self.assertEqual(row['error_type'],'ValueError' if stage=='identity' else 'TimeoutExpired')
                    self.assertNotIn(secret,json.dumps(row))
                    inspect.assert_not_called()
                    if stage=='identity':run.assert_not_called()
                finally:server.shutdown();server.server_close();worker.join(timeout=5)

    def test_http_bridge_uses_pinned_id_even_when_the_name_now_points_elsewhere(self):
        import base64,http.client,json,threading
        from http.server import ThreadingHTTPServer
        from types import SimpleNamespace
        class Routed(proxy.Handler):
            def do_GET(self):return self.forward_request()
        response=SimpleNamespace(stdout=json.dumps({'status':200,'headers':[],'body':base64.b64encode(b'actual-test').decode()}).encode())
        with patch.object(proxy,'clone_identity',return_value='b'*64) as inspect,patch.object(proxy.subprocess,'run',return_value=response) as run:
            server=ThreadingHTTPServer(('127.0.0.1',0),Routed);server.container='name-now-pointing-elsewhere';server.clone_id='a'*64
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                client.request('GET','/cgi-bin/luci/admin/services/homensai-vpn');reply=client.getresponse()
                self.assertEqual(reply.status,200);self.assertEqual(reply.read(),b'actual-test');client.close()
                self.assertEqual(run.call_args.args[0][3],'a'*64)
                self.assertNotIn('name-now-pointing-elsewhere',run.call_args.args[0]);inspect.assert_not_called()
            finally:server.shutdown();server.server_close();worker.join(timeout=5)
    def test_cross_site_and_host_escape_refused_before_forwarding(self):
        good=('GET','/cgi-bin/luci/admin/services/homensai-vpn','127.0.0.1:18900',None,None,18900)
        self.assertTrue(proxy.allowed_request(*good))
        for edit in ({2:'192.168.8.1'},{3:'https://example.invalid'},{4:'cross-site'},{0:'DELETE'},
                     {1:'http://192.168.8.1/'},{1:'/luci-static/%252e%252e/private'},
                     {1:'/cgi-bin/luci/%2525252525252e%2525252525252e/private'},{1:'/.git/config'},
                     {1:'/cgi-bin/luci/%00'}):
            args=list(good)
            for key,value in edit.items():args[key]=value
            with self.subTest(edit=edit):self.assertFalse(proxy.allowed_request(*args))

    def test_only_running_unprivileged_unmounted_network_none_clone_is_accepted(self):
        import json
        row={'Id':'a'*64,'State':{'Running':True},'HostConfig':{'NetworkMode':'none','Privileged':False},'Mounts':[]}
        with patch.object(proxy.subprocess,'check_output',return_value=json.dumps([row])):
            self.assertEqual(proxy.clone_identity('clone'),'a'*64)
        for field,value in (('NetworkMode','host'),('Privileged',True)):
            bad=dict(row,HostConfig=dict(row['HostConfig'],**{field:value}))
            with patch.object(proxy.subprocess,'check_output',return_value=json.dumps([bad])),self.assertRaises(ValueError):proxy.clone_identity('clone')
        for key,value in (('Mounts',[{'Source':'/'}]),('State',{'Running':False})):
            with patch.object(proxy.subprocess,'check_output',return_value=json.dumps([dict(row,**{key:value})])),self.assertRaises(ValueError):proxy.clone_identity('clone')
