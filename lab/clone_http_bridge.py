"""Container-side byte-preserving HTTP bridge; never logs request/session data."""
from serial_clone import require_clone
require_clone()
import base64
import http.client
import json
import sys
request=json.load(sys.stdin)
if request['method'] not in ('GET','POST','HEAD'):raise SystemExit('method refused')
body=base64.b64decode(request.get('body',''),validate=True)
if len(body)>2*1024*1024:raise SystemExit('request too large')
connection=http.client.HTTPConnection('127.0.0.1',8081,timeout=35)
try:
    connection.request(request['method'],request['path'],body=body or None,headers=request['headers'])
    response=connection.getresponse();payload=response.read(3*1024*1024+1)
    if len(payload)>3*1024*1024:raise SystemExit('response too large')
    print(json.dumps({'status':response.status,'headers':response.getheaders(),'body':base64.b64encode(payload).decode()}))
finally:connection.close()
