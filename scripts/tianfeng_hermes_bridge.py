#!/usr/bin/env python3
"""天锋PRO ↔ Hermes桥接器"""
import subprocess,json,sys,os
TC=os.path.expanduser("~/bin/tianfeng")
def call(cmd,*args):
    r=subprocess.run([TC,cmd]+list(args),capture_output=True,text=True,timeout=30)
    return{"success":r.returncode==0,"stdout":r.stdout[:3000]}
def search(q,n=5):
    import urllib.request
    d=json.dumps({"query":q,"n_results":n}).encode()
    req=urllib.request.Request("http://100.116.0.29:8200/genes/search",data=d,headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=8).read())
if __name__=="__main__":
    c=sys.argv[1] if len(sys.argv)>1 else "help"
    a=sys.argv[2:]
    if c=="code":print(json.dumps(call("code"," ".join(a) if a else input("任务: ")),ensure_ascii=False))
    elif c=="review":print(json.dumps(call("review",a[0] if a else "."),ensure_ascii=False))
    elif c=="search":print(json.dumps(search(a[0] if a else ""),ensure_ascii=False))
    elif c=="dashboard":print(json.dumps(call("dashboard"),ensure_ascii=False))
    else:print(json.dumps({"available":["code","review","search","dashboard"]}))
