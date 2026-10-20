"""Bounded strict RPC JSON decoder; authentication remains the rpcd ACL boundary."""
import json
import math

def decode_request(request):
    if len(request)>65536:raise ValueError('RPC-INPUT-SIZE')
    def pairs(rows):
        result={}
        for key,value in rows:
            if key in result:raise ValueError('RPC-DUPLICATE-FIELD')
            result[key]=value
        return result
    def constant(value):raise ValueError('RPC-NONFINITE-NUMBER')
    try:arguments=json.loads(request,object_pairs_hook=pairs,parse_constant=constant) if request.strip() else {}
    except RecursionError:raise ValueError('RPC-INPUT-DEPTH') from None
    except ValueError as error:
        # Our own codes pass through; a library message (it can quote the request) becomes a fixed code.
        raise ValueError(str(error) if str(error).startswith('RPC-') else 'RPC-INPUT-INVALID') from None
    if not isinstance(arguments,dict):raise ValueError('RPC-INPUT-OBJECT')
    stack=[(arguments,0)];nodes=0
    while stack:
        value,depth=stack.pop();nodes+=1
        if depth>64 or nodes>10000:raise ValueError('RPC-INPUT-COMPLEXITY')
        if isinstance(value,float) and not math.isfinite(value):raise ValueError('RPC-NONFINITE-NUMBER')
        if isinstance(value,dict):stack.extend((item,depth+1) for item in value.values())
        elif isinstance(value,list):stack.extend((item,depth+1) for item in value)
    arguments.pop('ubus_rpc_session',None)
    return arguments
