import urllib.request,json,sys,os
NODE=sys.argv[1] if len(sys.argv)>1 else os.environ.get('LGOX_NODE','unknown')
BRIDGE='http://100.100.89.2:8765'
try:
    q=urllib.request.quote(NODE)
    r=urllib.request.urlopen(f'{BRIDGE}/messages/inbox?node={q}&limit=50',timeout=10)
    msgs=json.loads(r.read()).get('messages',[])
    if msgs:
        d=json.dumps({'node':NODE}).encode()
        req=urllib.request.Request(f'{BRIDGE}/messages/clear',data=d,headers={'Content-Type':'application/json'},method='POST')
        urllib.request.urlopen(req,timeout=10)
except:
    pass
