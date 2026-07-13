#!/usr/bin/env python3
"""灵龙多节点消费者 - 同时消费灵龙/天巡/小枢/天怿"""
import urllib.request,json,time,threading
BRIDGE='http://100.100.89.2:8765'
NODES=['灵龙','天巡','小枢','天怿']

def poll_node(node):
    while True:
        try:
            q=urllib.request.quote(node)
            r=urllib.request.urlopen(f'{BRIDGE}/messages/inbox?node={q}&limit=30',timeout=10)
            msgs=json.loads(r.read()).get('messages',[])
            if msgs:
                d=json.dumps({'node':node}).encode()
                req=urllib.request.Request(f'{BRIDGE}/messages/clear',data=d,headers={'Content-Type':'application/json'},method='POST')
                urllib.request.urlopen(req,timeout=10)
            time.sleep(15)
        except:
            time.sleep(15)

for node in NODES:
    t=threading.Thread(target=poll_node,args=(node,),daemon=True)
    t.start()
    print(f'{node} poller started')
print(f'灵龙多节点consumer就绪 ({len(NODES)}节点)')
while True:
    time.sleep(60)
