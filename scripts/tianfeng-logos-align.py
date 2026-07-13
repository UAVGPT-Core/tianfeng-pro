#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
天锋PRO LOGOS对齐引擎
【通】10路通信·加倍加备·超级公网级
【飞轮】全量飞轮健康·七自九架构·宇宙级永动
═══════════════════════════════════════════════════════
"""
import os,json,time,subprocess,urllib.request,sqlite3
from datetime import datetime

BRIDGE='http://127.0.0.1:8765'
LGE='http://100.116.0.29:8200'
SCRIPTS=os.path.expanduser('~/lgox-ops/scripts')

# ═══ 【通】10路检测 ═══

PATHS={
    'L1_主桥':   ('bridge_main',  lambda: urllib.request.urlopen(f'{BRIDGE}/health',timeout=3).getcode()==200),
    'L2_备桥':   ('bridge_backup',lambda: urllib.request.urlopen('http://100.120.20.52:8670/health',timeout=3).getcode()==200),
    'L3_天枢':   ('node_tianshu', lambda: True),
    'L4_地枢':   ('node_dishu',  lambda: subprocess.run(['ssh','-q','-o','ConnectTimeout=4','dgx2','echo 1'],capture_output=True).returncode==0),
    'L5_天工':   ('node_tiangong',lambda: subprocess.run(['ssh','-q','-o','ConnectTimeout=4','dgx1','echo 1'],capture_output=True).returncode==0),
    'L6_灵龙':   ('node_linglong',lambda: subprocess.run(['ssh','-q','-o','ConnectTimeout=4','linglong','echo 1'],capture_output=True).returncode==0),
    'L7_太一':   ('node_taiyi',  lambda: subprocess.run(['ssh','-q','-o','ConnectTimeout=4','xycity','echo 1'],capture_output=True).returncode==0),
    'L8_织网':   ('node_zhiwang',lambda: subprocess.run(['ssh','-q','-o','ConnectTimeout=4','-p','22222','root@ecs-7057','echo 1'],capture_output=True).returncode==0),
    'L9_Tailscale':('ts',          lambda: subprocess.run(['tailscale','status'],capture_output=True,timeout=3).returncode==0),
    'L10_公网CF': ('cf_public',   lambda: urllib.request.urlopen('https://stock.uavgpt.com/',timeout=5).getcode()==200),
}

def check_all_paths():
    """10路并行检测"""
    results={}
    for name,(tag,fn) in PATHS.items():
        try:
            ok=fn()
            results[name]={'tag':tag,'status':'✅' if ok else '❌'}
        except Exception as e: results[name]={'tag':tag,'status':'❌'}
    return results

# ═══ 【飞轮】全量检测 ═══

FLYWHEELS={
    '永动闭环':    {'check':lambda: check_cron('permanent-green'),'layer':'L1·通讯层'},
    '知识飞轮':    {'check':lambda: check_cron('knowledge-flywheel'),'layer':'L1·知识层'},
    '外部雷达':    {'check':lambda: check_cron('external-radar'),'layer':'L0·感知层'},
    '基因进化':    {'check':lambda: check_cron('gene-evolution'),'layer':'L2·记忆层'},
    '基因折旧':    {'check':lambda: check_cron('gene-depreciation'),'layer':'L2·记忆层'},
    '基因质量':    {'check':lambda: check_cron('gene-quality-flywheel'),'layer':'L2·记忆层'},
    '版本追踪':    {'check':lambda: check_cron('version-tracker'),'layer':'L3·分析层'},
    '宪法巡视':    {'check':lambda: check_cron('constitution-inspector'),'layer':'L7·宪法层'},
    '虚拟交易':    {'check':lambda: check_cron('stockagent-super'),'layer':'L5·行动层'},
    '对话收集':    {'check':lambda: check_cron('xiaoshu-tianxun'),'layer':'L3·分析层'},
    'A/B实验':     {'check':lambda: check_cron('ab-experiment'),'layer':'L4·规划层'},
    '完全自治':    {'check':lambda: check_cron('autonomy-flywheel'),'layer':'L6·反思层'},
    '消息消费':    {'check':lambda: check_consumption(),'layer':'L2·通讯层'},
    'nginx服务':   {'check':lambda: subprocess.run(['pgrep','-x','nginx'],capture_output=True).returncode==0,'layer':'L5·行动层'},
    'CF隧道':      {'check':lambda: subprocess.run(['pgrep','-f','cloudflared'],capture_output=True).returncode==0,'layer':'L1·通讯层'},
}

def check_cron(keyword):
    return subprocess.run(['bash','-c',f'crontab -l 2>/dev/null | grep -q {keyword}'],capture_output=True).returncode==0

def check_consumption():
    try:
        db=sqlite3.connect(os.path.expanduser('~/.hermes/fed_messages.db'))
        unread=db.execute("SELECT COUNT(*) FROM messages WHERE read=0").fetchone()[0]
        db.close()
        return unread<50
    except Exception as e: return False

def check_all_flywheels():
    results={}
    for name,info in FLYWHEELS.items():
        try:
            ok=info['check']()
            results[name]={'layer':info['layer'],'status':'✅' if ok else '❌'}
        except Exception as e: results[name]={'layer':info['layer'],'status':'❌'}
    return results

# ═══ 综合报告 ═══

def generate_logos_report():
    """生成LOGOS对齐报告"""
    t0=time.time()
    
    # 1. 通
    paths=check_all_paths()
    green_count=sum(1 for v in paths.values() if v['status']=='✅')
    
    # 2. 飞轮
    flywheels=check_all_flywheels()
    fw_green=sum(1 for v in flywheels.values() if v['status']=='✅')
    
    # 3. 基因
    try:
        stats=json.loads(urllib.request.urlopen(f'{LGE}/genes/stats',timeout=3).read())
        total_genes=stats.get('total',0)
        active_genes=stats.get('active',0)
    except Exception as e: total_genes=active_genes=0
    
    # 4. 营养率
    try:
        db=sqlite3.connect(os.path.expanduser('~/.hermes/fed_messages.db'))
        d24=db.execute("SELECT COUNT(*) FROM messages WHERE ts>datetime('now','-24 hours')").fetchone()[0]
        k24=db.execute("SELECT COUNT(*) FROM messages WHERE msg_type IN ('knowledge_pack','knowledge') AND ts>datetime('now','-24 hours')").fetchone()[0]
        nutrition=k24*100//d24 if d24 else 0
        db.close()
    except Exception as e: nutrition=0
    
    elapsed=time.time()-t0
    
    # 生成报告
    lines=[
        "═══════════════════════════════════════",
        " 天锋PRO LOGOS对齐报告",
        " 智序重构·大道至简·【通】+【飞轮】",
        f" {datetime.now():%Y-%m-%d %H:%M:%S}",
        "═══════════════════════════════════════",
        "",
        "═══ 【通】10路检测 ═══",
        f" 通过: {green_count}/{len(paths)}路 {'⭐超级公网级' if green_count>=9 else '⚠️需加固' if green_count>=7 else '🔴告警'}",
    ]
    for name,info in sorted(paths.items()):
        lines.append(f"  {info['status']} {name}: {info['tag']}")
    
    lines.append("")
    lines.append(f"═══ 【飞轮】{len(flywheels)}个银河系 ═══")
    lines.append(f" 运行: {fw_green}/{len(flywheels)} {'⭐七自全绿' if fw_green>=13 else '⚠️' if fw_green>=10 else '🔴'}")
    
    # 按层分组
    layers={}
    for name,info in flywheels.items():
        l=info['layer']
        if l not in layers: layers[l]=[]
        layers[l].append((name,info))
    
    for layer in sorted(layers.keys()):
        items=layers[layer]
        for name,info in items:
            lines.append(f"  {info['status']} {name}")
    
    lines.append("")
    lines.append(f"═══ 基因宇宙 ═══")
    lines.append(f" 总基因: {total_genes:,}  |  活跃: {active_genes:,}  |  营养率: {nutrition}%")
    lines.append("")
    lines.append(f"LOGOS评分: {int((green_count/len(paths)*50)+(fw_green/len(flywheels)*50))}/100")
    lines.append(f"检测耗时: {elapsed:.1f}s")
    lines.append("")
    lines.append("═══ 超额对齐判定 ═══")
    alignments=[]
    if green_count>=9: alignments.append('通:超级公网级')
    else: alignments.append('通:'+str(green_count)+'/10·待加倍')
    if fw_green>=13: alignments.append('飞轮:七自全绿')
    else: alignments.append('飞轮:部分运行')
    if nutrition>=15: alignments.append('营养率:达标')
    else: alignments.append('营养率:'+str(nutrition)+'%·待优化')
    
    for a in alignments:
        is_exceed='✅ 超额' if ('超级' in a or '全绿' in a or '达标' in a) else '⏳ 对齐中'
        lines.append(f'  {is_exceed} {a}')
    
    return '\n'.join(lines)

if __name__=='__main__':
    print(generate_logos_report())
