#!/usr/bin/env python3
"""
LGOX飞轮互联引擎 v1.0
LOGOS战略: 飞轮间自动流转·产出闭环
知识飞轮→基因飞轮→交易飞轮→回流知识飞轮
"""
import json,urllib.request,time,os
from datetime import datetime

LGE='http://100.116.0.29:8200'
BRIDGE='http://127.0.0.1:8765'
LABEL='飞轮互联'

def gene_write(content,tag='飞轮互联'):
    try:
        urllib.request.urlopen(urllib.request.Request(f'{LGE}/genes/write',
            data=json.dumps({'content':content,'memory_type':'procedural','source':'flywheel-connect','tags':[tag,'飞轮互联']}).encode(),
            headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except Exception as e: pass

def check_flywheel_status():
    """检测各飞轮cron状态·返回营养率"""
    import subprocess
    fws={
        '永动闭环':'permanent-green','知识飞轮':'knowledge-flywheel',
        '基因进化':'gene-evolution','基因折旧':'gene-depreciation',
        '基因质量':'gene-quality-flywheel','外部雷达':'external-radar',
        '版本追踪':'version-tracker','宪法巡视':'constitution-inspector',
        '虚拟交易':'stockagent-super','对话收集':'xiaoshu-tianxun',
        'A/B实验':'ab-experiment','完全自治':'autonomy-flywheel',
    }
    status={}
    for name,kw in fws.items():
        r=subprocess.run(['bash','-c',f'crontab -l 2>/dev/null|grep -q {kw}'],capture_output=True)
        status[name]=r.returncode==0
    return status

def run():
    t0=time.time()
    report=[]
    
    # 1. 检测飞轮状态
    fw_status=check_flywheel_status()
    green=sum(fw_status.values())
    total=len(fw_status)
    nutrition=green*100//total if total else 0
    
    # 2. 基因统计
    try:
        stats=json.loads(urllib.request.urlopen(f'{LGE}/genes/stats',timeout=3).read())
        report.append(f'基因:{stats.get("total",0):,}·活跃:{stats.get("active",0):,}')
    except Exception as e: pass
    
    # 3. 联动: 知识飞轮产→基因
    report.append(f'飞轮营养率:{nutrition}%({green}/{total}在线)')
    
    # 4. 纳基因
    gene_write(f'[飞轮互联·{datetime.now():%H:%M}] 营养率{nutrition}%·{green}/{total}在线')
    
    # 5. 桥广播
    try:
        urllib.request.urlopen(urllib.request.Request(f'{BRIDGE}/messages/send',
            data=json.dumps({'to':'all','from':LABEL,'content':f'飞轮互联:营养率{nutrition}%·{green}/{total}在线','type':'knowledge_pack','topic':'飞轮互联'}).encode(),
            headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except Exception as e: pass
    
    elapsed=time.time()-t0
    print(f'[{datetime.now():%H:%M}] 飞轮互联: {green}/{total}在线·营养率{nutrition}%·{elapsed:.1f}s')
    print(' | '.join(report))

if __name__=='__main__':
    run()
