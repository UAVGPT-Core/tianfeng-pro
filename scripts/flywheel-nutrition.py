#!/usr/bin/env python3
"""LGOX飞轮营养仪表盘 v1.0"""
import json,urllib.request,subprocess,os,sqlite3,time
from datetime import datetime

def get_metrics():
    m={}
    # 基因
    try:
        s=json.loads(urllib.request.urlopen('http://100.116.0.29:8200/genes/stats',timeout=3).read())
        m['genes_total']=s.get('total',0); m['genes_active']=s.get('active',0)
    except: m['genes_total']=m['genes_active']=0
    
    # 飞轮
    fws=[('永动','permanent-green'),('知识','knowledge-flywheel'),('基因','gene-evolution'),
         ('折旧','gene-depreciation'),('质量','gene-quality'),('雷达','external-radar'),
         ('版本','version-tracker'),('宪法','constitution'),('交易','stockagent-super'),
         ('对话','xiaoshu-tianxun'),('AB','ab-experiment'),('自治','autonomy-flywheel'),
         ('互联','flywheel-connect')]
    green=0
    for name,kw in fws:
        r=subprocess.run(['bash','-c',f'crontab -l 2>/dev/null|grep -q {kw}'],capture_output=True)
        if r.returncode==0: green+=1
    m['fw_total']=len(fws); m['fw_green']=green; m['fw_nutrition']=green*100//len(fws)
    
    # 通信
    try:
        db=sqlite3.connect(os.path.expanduser('~/.hermes/fed_messages.db'))
        d24=db.execute("SELECT COUNT(*) FROM messages WHERE ts>datetime('now','-24 hours')").fetchone()[0]
        k24=db.execute("SELECT COUNT(*) FROM messages WHERE msg_type IN ('knowledge_pack','knowledge') AND ts>datetime('now','-24 hours')").fetchone()[0]
        m['msg_24h']=d24; m['msg_knowledge']=k24; m['msg_nutrition']=k24*100//d24 if d24 else 0
        db.close()
    except: m['msg_nutrition']=0
    
    # 评分
    m['logos_score']=int(m['fw_nutrition']*0.4 + m['msg_nutrition']*0.3 + min(50,m['genes_active']//10000)*0.3)
    return m

if __name__=='__main__':
    m=get_metrics()
    print(f"[{datetime.now():%H:%M}] 飞轮营养:{m['fw_green']}/{m['fw_total']}在线·{m['fw_nutrition']}%")
    print(f"  消息营养:{m['msg_nutrition']}% · 基因:{m['genes_total']:,}")
    print(f"  LOGOS评分:{m['logos_score']}/100")
