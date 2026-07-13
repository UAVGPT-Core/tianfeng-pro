#!/usr/bin/env python3
"""
LGOX飞轮营养率引擎 v1.0
追踪有效产出/总操作 → 低营养自动诊断修复
永动营养: 4%→30% · 基因fitness: 0.294→0.7
"""
import json,urllib.request,time,subprocess,os,sqlite3
from datetime import datetime

LGE='http://100.116.0.29:8200'
BRIDGE='http://127.0.0.1:8765'

def gw(content,tag='nutrition'):
    try: urllib.request.urlopen(urllib.request.Request(f'{LGE}/genes/write',data=json.dumps({'content':content,'memory_type':'procedural','source':'nutrition-engine','tags':[tag]}).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except Exception as e: pass

def nutrition_score(effective,total):
    return effective*100//total if total else 0

def analyze():
    report={}
    
    # 1. 消息营养率
    try:
        db=sqlite3.connect(os.path.expanduser('~/.hermes/fed_messages.db'))
        d24=db.execute("SELECT COUNT(*) FROM messages WHERE ts>datetime('now','-24 hours')").fetchone()[0]
        k24=db.execute("SELECT COUNT(*) FROM messages WHERE msg_type IN ('knowledge_pack','knowledge','action') AND ts>datetime('now','-24 hours')").fetchone()[0]
        noise=db.execute("SELECT COUNT(*) FROM messages WHERE (msg_type='' OR msg_type='ack') AND ts>datetime('now','-24 hours')").fetchone()[0]
        db.close()
        report['message']={'effective':k24,'total':d24,'noise':noise,'nutrition':nutrition_score(k24,d24)}
    except Exception as e: pass
    
    # 2. 飞轮营养率(cron在线率+产出)
    fws={}
    for name,kw in [('永动','permanent-green'),('知识','knowledge-flywheel'),('基因','gene-evolution'),
        ('质量','gene-quality'),('雷达','external-radar'),('交易','stockagent-super'),
        ('对话','xiaoshu-tianxun'),('AB','ab-experiment'),('自治','autonomy-flywheel'),
        ('生态','flywheel-ecosystem'),('营养','flywheel-nutrition')]:
        r=subprocess.run(['bash','-c',f'crontab -l 2>/dev/null|grep -q {kw}'],capture_output=True)
        fws[name]=r.returncode==0
    report['flywheels']={'total':len(fws),'online':sum(fws.values()),'nutrition':sum(fws.values())*100//len(fws)}
    
    # 3. 基因fitness
    try:
        s=json.loads(urllib.request.urlopen(f'{LGE}/genes/stats',timeout=3).read())
        report['genes']={'total':s.get('total',0),'active':s.get('active',0),'fitness':s.get('avg_fitness',0.294)}
    except Exception as e: pass
    
    # 4. 营养率评分
    msg_n=report.get('message',{}).get('nutrition',0)
    fw_n=report.get('flywheels',{}).get('nutrition',0)
    gf=report.get('genes',{}).get('fitness',0.29);fitness_val=gf*100 if isinstance(gf,(int,float)) else 29
    overall=int(msg_n*0.3+fw_n*0.3+fitness_val*0.4)
    report['overall']=overall
    
    return report

def diagnose(r):
    """自动诊断低营养环节"""
    fixes=[]
    msg=r.get('message',{})
    if msg.get('nutrition',0)<15:
        noise=msg.get('noise',0)
        fixes.append(f'消息噪音{noise}条·需降ACK')
    genes=r.get('genes',{})
    gf=genes.get('fitness',0.29)
    if gf is None: gf=0.29
    if isinstance(gf,(int,float)) and gf<0.5:
        fixes.append('基因fitness '+str(round(gf,3))+'·需质量飞轮优化')
    return fixes

def run():
    r=analyze()
    fixes=diagnose(r)
    
    msg=r.get('message',{})
    fw=r.get('flywheels',{})
    genes=r.get('genes',{})
    
    mn=msg.get('nutrition',0); me=msg.get('effective',0); mt=msg.get('total',0)
    fn=fw.get('online',0); ft=fw.get('total',0); fnr=fw.get('nutrition',0)
    gf2=genes.get('fitness',0.29); gt=genes.get('total',0)
    if gf2 is None: gf2=0.29
    lines=[
        f'[{datetime.now():%H:%M}] 飞轮营养率: {r["overall"]}分',
        f'  消息营养:{mn}%({me}/{mt})·噪音{msg.get("noise",0)}',
        f'  飞轮在线:{fn}/{ft}·{fnr}%',
        f'  基因fitness:{round(gf2,3)}·{gt:,}总'
    ]
    if fixes:
        fix_str='; '.join(fixes[:2])
        lines.append('  待修复: '+fix_str)
    
    print('\n'.join(lines))
    
    # 纳基因
    msg_n=msg.get('nutrition',0); fw_n=fw.get('nutrition',0)
    gen_f=genes.get('fitness',0.29)
    gw('[营养率引擎·'+datetime.now().strftime('%m%d%H%M')+'] 综合'+str(r['overall'])+'分·消息'+str(msg_n)+'%·飞轮'+str(fw_n)+'%·fitness'+str(gen_f),'nutrition')
    
    # 桥通报
    try:
        overall_score=r.get('overall',0)
        urllib.request.urlopen(urllib.request.Request(BRIDGE+'/messages/send',
            data=json.dumps({'to':'天枢','from':'营养率引擎','content':'营养率'+str(overall_score)+'分','type':'status','topic':'nutrition'}).encode(),
            headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except Exception as e: pass

if __name__=='__main__': run()
