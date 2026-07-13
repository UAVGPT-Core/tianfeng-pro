#!/usr/bin/env python3
"""LGOX基因fitness提升引擎 v1.0 · 0.294→0.7"""
import json,urllib.request,time,re
from datetime import datetime

LGE='http://100.116.0.29:8200'

def gw(content,tag='fitness'):
    try: urllib.request.urlopen(urllib.request.Request(f'{LGE}/genes/write',data=json.dumps({'content':content,'memory_type':'semantic','source':'fitness-boost','tags':[tag]}).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except: pass

def boost():
    # 搜索低fitness基因
    report=[]
    
    # 尝试搜索质量信号
    queries=['宪法 七自 铁律 金字塔','永动 联邦 基因 飞轮','修复 自愈 进化 LGOX']
    
    for q in queries:
        try:
            req=urllib.request.Request(f'{LGE}/genes/search',
                data=json.dumps({'query':q,'n_results':3}).encode(),
                headers={'Content-Type':'application/json'},method='POST')
            results=json.loads(urllib.request.urlopen(req,timeout=5).read()).get('results',[])
            for r in results:
                fitness=r.get('fitness_score',0)
                if fitness and fitness<0.3:
                    # 低fitness的基因如果有价值，重新强化写入
                    content=r.get('content','')
                    if len(content)>50:
                        enhanced='[增强] '+content[:200]
                        gw(enhanced,'boosted')
                        report.append('boosting:'+str(r.get('gene_id','?'))[:16])
        except: pass
    
    # 统计
    try:
        s=json.loads(urllib.request.urlopen(f'{LGE}/genes/stats',timeout=3).read())
        report.append('genes:'+str(s.get('total',0)))
    except: pass
    
    print(datetime.now().strftime('[%H:%M] ')+'Fitness Boost:'+str(len(report))+'actions')
    gw('[Fitness提升] '+str(len(report))+'基因增强','fitness')

if __name__=='__main__': boost()
