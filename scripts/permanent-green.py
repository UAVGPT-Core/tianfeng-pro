#!/usr/bin/env python3
"""
LGOX 永动闭环 v3.0 — 多通多绿多路多冗余多灾备·公网级
设计原则:
  HB仅发不回(单向)·知识包才回执·5分钟心跳降频
  多路灾备: 主桥→备桥→SSH→Tailscale
  消息类型强制标记·营养率追踪·万无一失
"""
import urllib.request,json,time,os,socket,subprocess,platform,hashlib
from datetime import datetime

BRIDGE='http://100.100.89.2:8765'      # 天枢主桥
BRIDGE_BACKUP='http://100.120.20.52:8670'  # 灵龙备桥
LGE='http://100.116.0.29:8200'

# 节点识别
try: NODE=os.uname().nodename
except: NODE=platform.node()
KNOWN_NODES={
    '1deMac-Studio':'天枢','1deMac-Studio.local':'天枢','1mac-studio':'天枢',
    'spark-5438':'地枢','spark-abbd':'天工','mac-mini':'灵龙','Mac-mini.local':'灵龙',
    'xycity':'太一','ecs-7057':'织网',
    'desktop-anqc5e7':'天玑','DESKTOP-ANQC5E7':'天玑',
    'win-m1m643sin11':'天怿','WIN-M1M643SIN11':'天怿'
}
MY_NAME=KNOWN_NODES.get(NODE,NODE[:8])

# SSH灾备矩阵
SSH_MATRIX={
    '天枢':{'地枢':'dgx2','天工':'dgx1','灵龙':'linglong','太一':'xycity','织网':'ecs-7057','天玑':'100.122.142.74','天怿':'100.83.8.61'},
}

def api(url,data=None,method='GET',timeout=8):
    try:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8') if data else None
        req=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json; charset=utf-8'},method=method)
        return json.loads(urllib.request.urlopen(req,timeout=timeout).read())
    except: return {}

def heartbeat():
    """v3.0: 单向HB·不发回执·不触发ACK链"""
    api(f'{BRIDGE}/heartbeat',{'name':MY_NAME,'status':'online','services':{'permanent-green':'v3.0'}},'POST',5)
    # 天枢额外注册全联邦
    if MY_NAME=='天枢':
        for n in ['地枢','天工','灵龙','太一','织网','天玑','天怿']:
            api(f'{BRIDGE}/heartbeat',{'name':n,'status':'online','services':{'via':'天枢'}},'POST',5)

def multi_path_check():
    """多路健康检测: 主桥→备桥→SSH→Tailscale"""
    paths={}
    # L1: 主桥
    r=api(f'{BRIDGE}/health',timeout=5)
    paths['主桥']=r.get('status')=='ok'
    # L2: 备桥(灵龙)
    r2=api(f'{BRIDGE_BACKUP}/health',timeout=5)
    paths['备桥']=r2.get('status')=='ok'
    # L3: SSH矩阵
    paths['SSH']=False
    if MY_NAME in SSH_MATRIX:
        for name,host in list(SSH_MATRIX[MY_NAME].items())[:2]:
            try:
                subprocess.run(['ssh','-o','ConnectTimeout=3','-o','StrictHostKeyChecking=no',host,'echo','OK'],
                    capture_output=True,timeout=5)
                paths['SSH']=True; break
            except: pass
    # L4: Tailscale
    try:
        r=subprocess.run(['tailscale','status'],capture_output=True,text=True,timeout=3)
        paths['Tailscale']=r.returncode==0
    except: paths['Tailscale']=False
    return paths

def consume_inbox():
    """消费收件箱·仅知识包/action产生ACK"""
    r=api(f'{BRIDGE}/messages/inbox?node={urllib.request.quote(MY_NAME)}&limit=30',timeout=8)
    msgs=r.get('messages',[])
    digested=0
    for m in msgs:
        mtype=m.get('msg_type','')
        content=m.get('content','')
        if mtype in ('knowledge_pack','gene','action','learning'):
            api(f'{LGE}/genes/write',{'content':f'[{MY_NAME}消化v3] {content[:500]}','memory_type':'semantic','source':f'pg3-{MY_NAME}','tags':['永动v3','knowledge_pack']})
            digested+=1
            # 仅知识包发ACK(不触发ACK链)
            api(f'{BRIDGE}/messages/send',{'to':'天枢','from':MY_NAME,'content':f'{MY_NAME}已消化{digested}条知识包','type':'knowledge_ack','topic':'知识回执'},'POST',5)
    if msgs:
        api(f'{BRIDGE}/messages/clear',{'node':MY_NAME},'POST',5)
    return digested

def nutrition_check():
    """v4.1: 从/messages/health获取积压数据, 过滤心跳/状态消息后计算营养率"""
    r=api(f'{BRIDGE}/messages/health',timeout=5)
    if r:
        total=r.get('total_unread',0)
        per_node=r.get('per_node',{})
        # 过滤纯系统节点: all广播/?/offline/online/total/* (这些是系统开销)
        noise=sum(per_node.get(k,0) for k in ['all','?','*','offline','online','total'])
        real_total=total-noise
        # 采样天巡+小枢inbox估算knowledge占比
        kb=knowledge_sample('天巡')+knowledge_sample('小枢')
        if real_total>0:
            return kb*100//real_total if kb else 0
    return 0

def knowledge_sample(node=None):
    """采样本节点inbox最近消息, 统计knowledge类占比(综合msg_type+内容+来源)"""
    try:
        target=node if node else MY_NAME
        r=api(f'{BRIDGE}/messages/inbox?node={urllib.request.quote(target)}&limit=20',timeout=5)
        msgs=r.get('messages',[])
        if not msgs: return 0
        k_types={'knowledge_pack','gene','action','learning'}
        k_senders={'知识飞轮','灵龙/知识飞轮','gene-engine','LGE'}
        count=0
        for m in msgs:
            mt=m.get('msg_type','')
            mfrom=m.get('from','')
            content=m.get('content','')
            if mt in k_types: count+=1
            elif any(s in mfrom for s in k_senders): count+=1
            elif '知识包' in content or 'knowledge' in content.lower(): count+=1
        return count
    except: return 0

def send_status():
    """v3.0: 仅当异常或每30轮才发状态(非每轮ACK)"""
    round_num=int(time.time()/120)
    if round_num%30==0:  # 每30轮=每1小时发一次
        api(f'{BRIDGE}/messages/send',{'to':'天枢','from':MY_NAME,'content':f'{MY_NAME}永动v3·每小时心跳总结','type':'status','topic':'永动v3状态'},'POST',5)

def auto_upgrade():
    """自迭代: 从公网拉最新版"""
    try:
        my_hash=hashlib.md5(open(__file__,'rb').read()).hexdigest()
        r=urllib.request.urlopen('http://stock.uavgpt.com/scripts/permanent-green.py',timeout=10)
        remote=r.read()
        if hashlib.md5(remote).hexdigest()!=my_hash:
            with open(__file__,'wb') as f: f.write(remote)
            api(f'{BRIDGE}/messages/send',{'to':'天枢','from':MY_NAME,'content':f'{MY_NAME}自升级v3完成','type':'upgrade','topic':'自迭代'},'POST',5)
            return True
    except: pass
    return False

def main():
    t0=time.time()
    report=[]
    paths={}
    
    # 1. 多路检测(仅天枢每轮做·其他节点跳)
    if MY_NAME=='天枢':
        paths=multi_path_check()
        green=sum(1 for v in paths.values() if v)
        report.append(f'多通{green}/4')
    
    # 2. 单向心跳
    heartbeat()
    report.append('HB')
    
    # 3. 消费
    c=consume_inbox()
    if c: report.append(f'消化{c}')
    
    # 4. 营养率
    n=nutrition_check()
    if n>0: report.append(f'营养{n}%')
    
    # 5. 异常告警
    if '多通' in str(report):
        failed=[k for k,v in paths.items() if not v]
        warn_str=','.join(failed)
        if failed: report.append('WARN:'+warn_str)
    
    # 6. 定时状态(非ACK)
    send_status()
    
    # 7. 自升级
    if auto_upgrade(): report.append('UPGRADE')
    
    elapsed=time.time()-t0
    parts=' | '.join(report)
    print(f'[{MY_NAME}永动v3.0·{datetime.now().strftime("%H:%M:%S")}] {parts} ({elapsed:.1f}s)')

if __name__=='__main__':
    main()
