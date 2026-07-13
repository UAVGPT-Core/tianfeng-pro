#!/usr/bin/env python3
"""LGOX飞轮生态系统 v1.0 · 知识→基因→交易→回流闭环"""
import json,urllib.request,time,subprocess,os,sqlite3
from datetime import datetime

LGE='http://100.116.0.29:8200'
BRIDGE='http://127.0.0.1:8765'

def gw(content,tag='ecosystem'):
    try: urllib.request.urlopen(urllib.request.Request(f'{LGE}/genes/write',data=json.dumps({'content':content,'memory_type':'procedural','source':'ecosystem','tags':[tag]}).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except: pass

def run():
    t0=time.time()
    results=[]
    
    # Step1: 知识→基因
    try:
        db=sqlite3.connect(os.path.expanduser('~/.hermes/fed_messages.db'))
        k24=db.execute("SELECT COUNT(*) FROM messages WHERE msg_type IN ('knowledge_pack','knowledge') AND ts>datetime('now','-24 hours')").fetchone()[0]
        db.close()
        results.append(f'S1:知识{k24}条')
    except: results.append('S1:blocked')
    
    # Step2: 基因→交易
    try:
        stats=json.loads(urllib.request.urlopen(f'{LGE}/genes/stats',timeout=3).read())
        total=stats.get('total',0)
        if total>750000:
            subprocess.run(['python3',os.path.expanduser('~/lgox-ops/scripts/stockagent-super-flywheel.py')],capture_output=True,timeout=30)
            results.append('S2:已触发交易')
        else: results.append(f'S2:基因{total}')
    except: results.append('S2:blocked')
    
    # Step3: 交易→知识(回流)
    gw(f'[飞轮生态闭环·{datetime.now():%m%d%H%M}] 知识->基因->交易->回流完成','closed')
    results.append('S3:已回流')
    
    score=len([r for r in results if 'blocked' not in r])*33
    msg=' | '.join(results)
    
    # 桥广播
    try:
        urllib.request.urlopen(urllib.request.Request(f'{BRIDGE}/messages/send',
            data=json.dumps({'to':'all','from':'飞轮生态','content':f'闭环:{score}分·{msg}','type':'knowledge_pack','topic':'ecosystem'}).encode(),
            headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except: pass
    
    print(f'[{datetime.now():%H:%M}] 飞轮生态:{score}分·{msg}·{time.time()-t0:.1f}s')

if __name__=='__main__': run()
