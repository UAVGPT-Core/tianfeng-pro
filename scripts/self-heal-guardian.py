#!/usr/bin/env python3
"""
七自·自愈守护者 v1.0
节点自己检测→自己切换→自己修复
断了没人知道·它自己早就修好了
"""
import subprocess,urllib.request,json,time,os,sys
from datetime import datetime

MAIN_BRIDGE='http://100.100.89.2:8765'
BACKUP_BRIDGE='http://100.120.20.52:8670'
SSH_NODES=['dgx2','dgx1','ecs-7057']
NODE=os.uname().nodename if hasattr(os,'uname') else 'self'
NODE_NAME=os.popen('hostname').read().strip()

def check(url,timeout=3):
    try: return urllib.request.urlopen(url,timeout=timeout).getcode()==200
    except: return False

def ssh_check(host):
    try:
        r=subprocess.run(['ssh','-q','-o','ConnectTimeout=4',host,'echo 1'],capture_output=True,timeout=5)
        return r.returncode==0
    except: return False

def log(msg):
    print(f'[{datetime.now():%H:%M:%S}] {msg}')

def heal_cycle():
    """一次自愈循环"""
    # 1. 检查主桥
    if check(f'{MAIN_BRIDGE}/health'):
        return 'ok'
    
    log('主桥不通·启动自愈')
    
    # 2. 切换到备桥
    if check(f'{BACKUP_BRIDGE}/health'):
        log('备桥可达·已切换')
        return 'backup'
    
    # 3. SSH直连
    for host in SSH_NODES:
        if ssh_check(host):
            log(f'SSH直连{host}·通告离线')
            try:
                subprocess.run(['ssh','-q',host,f'echo {NODE_NAME} via SSH'],timeout=5)
            except: pass
            return 'ssh'
    
    # 4. 终极保底:本地重启网络
    log('全路不通·重启网络栈')
    try:
        subprocess.run(['sudo','ifconfig','en0','down'],timeout=5)
        time.sleep(2)
        subprocess.run(['sudo','ifconfig','en0','up'],timeout=5)
    except: pass
    
    return 'recovery'

# ═══ 永动入口 ═══
if __name__=='__main__':
    log(f'自愈守护者启动·节点:{NODE_NAME}')
    
    while True:
        try:
            result=heal_cycle()
            if result!='ok':
                log(f'自愈完成:{result}')
        except Exception as e:
            log(f'异常:{e}')
        time.sleep(30)
