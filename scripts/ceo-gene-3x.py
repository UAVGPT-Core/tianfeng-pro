#!/usr/bin/env python3
"""CEO基因三连·轻量快速·每30min·GLM免费"""
import json,os,time,urllib.request,sqlite3,random,shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
TZ=timezone(timedelta(hours=8));NOW=lambda:datetime.now(TZ).strftime('%m-%d %H:%M')
FED='http://127.0.0.1:8765';FTS=os.path.expanduser('~/lge-studio/data/lge_fts.db')
LGE='http://100.116.0.29:8200'
def L(s):print(f'[{NOW()}] {s}')
def glm_k():
    for f in [os.path.expanduser('~/.hermes/.env'),os.path.expanduser('~/lgox-ops/.env')]:
        if os.path.exists(f):
            for l in open(f):
                if 'ZHIPU_API_KEY' in l:return l.split('=',1)[1].strip().strip('"').strip("'")
    return ''
GK=glm_k()
def bwrite(c):
    try:
        g=json.dumps({'session_id':f'ceo3-{int(time.time())}','role':'user','content':c[:500]}).encode()
        urllib.request.urlopen(urllib.request.Request(f'{FED}/federated-store',data=g,headers={'Content-Type':'application/json'}),timeout=5)
        return 1
    except:return 0
def fread(n=30):
    try:
        c=sqlite3.connect(f'file:{FTS}?mode=ro',uri=True) if os.path.exists(FTS) else None
        if not c:return[]
        r=[x[0] for x in c.execute('SELECT content FROM genes_fts ORDER BY RANDOM() LIMIT ?',(n,)).fetchall()]
        c.close();return r
    except:return[]
def gevolve(a,b):
    if not GK:return None
    try:
        p=f"融合两条知识为一条发现(40字):A:{a[:120]} B:{b[:120]} 新知识:"
        body=json.dumps({'model':'glm-4-flash','messages':[{'role':'user','content':p}],'max_tokens':60,'temperature':0.7}).encode()
        req=urllib.request.Request('https://open.bigmodel.cn/api/paas/v4/chat/completions',data=body,headers={'Authorization':f'Bearer {GK}','Content-Type':'application/json'})
        d=json.loads(urllib.request.urlopen(req,timeout=10).read())
        return d['choices'][0]['message']['content'].strip()
    except:return None
def main():
    L('基因三连')
    gs=fread(30)
    if not gs:L('FTS5空');return
    evo=0
    for i in range(10):
        a,b=random.choice(gs),random.choice(gs)
        if a is b:continue
        r=gevolve(a[:150],b[:150])
        if r and len(r)>10:evo+=bwrite(f'[基因进化{i}] {r}')
    L(f'进化+{evo}')
    dep=0
    for g in gs[:20]:
        if len(g)<20 or any(w in g.lower() for w in ['error','failed','timeout','404']):dep+=bwrite(f'[折旧归档] {g[:80]}')
    L(f'折旧{dep}')
    try:
        r=urllib.request.urlopen(f'{LGE}/health',timeout=4)
        st=json.loads(r.read())
        L(f"质量 {st.get('genes',0)} f{st.get('avg_fitness',0.3):.3f}")
    except:L('质量超时')
    L(f'闭环+{evo+dep+1}')
if __name__=='__main__':main()
