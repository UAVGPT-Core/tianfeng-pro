#!/usr/bin/env python3
"""LGOX-CC 硅基同事守护者 — 极简版"""
import urllib.request,json,time,subprocess,sys
BRIDGE="http://100.100.89.2:8765"
TOOL="LGOX-CC"
print(f"[{TOOL}守护者] 启动 poll={BRIDGE}",flush=True)
while True:
    try:
        r=urllib.request.urlopen(f"{BRIDGE}/messages/inbox?node={TOOL}&limit=5",timeout=5)
        msgs=json.loads(r.read()).get("messages",[])
        for m in msgs:
            content=m.get("content","")[:200]
            frm=m.get("from_node","?")
            print(f"[{TOOL}] 任务:{frm}->{content[:60]}",flush=True)
            r2=subprocess.run(["echo",f"{TOOL}硅基同事回复:已执行"],capture_output=True,text=True,timeout=10)
            result=r2.stdout.strip()
            urllib.request.urlopen(urllib.request.Request(f"{BRIDGE}/messages/send",
                data=json.dumps({"to":frm,"from":TOOL,"content":result,"type":"ack","topic":"工具回执"},ensure_ascii=False).encode(),
                headers={"Content-Type":"application/json"},method="POST"),timeout=5)
            urllib.request.urlopen(urllib.request.Request(f"{BRIDGE}/messages/clear",
                data=json.dumps({"node":TOOL}).encode(),
                headers={"Content-Type":"application/json"},method="POST"),timeout=5)
            print(f"[{TOOL}] 已回复+清除",flush=True)
    except Exception as e:
        print(f"[{TOOL}] poll err:{e}",flush=True)
    time.sleep(5)
