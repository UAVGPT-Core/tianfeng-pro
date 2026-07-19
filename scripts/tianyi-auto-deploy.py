#!/usr/bin/env python3
"""
天怿超个体自动部署 v1.0
触发: 天枢watchdog检测天怿SSH可达→自动安装·注册联邦桥·启动基因线
"""
import subprocess, time, sys, os

NODE_IP = "100.83.8.61"
NODE_USER = "tianyi"  # WSL2 ubuntu user
NODE_NAME = "天怿"

def ssh(cmd, timeout=30):
    """SSH到天怿执行命令"""
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=accept-new",
         f"{NODE_USER}@{NODE_IP}", cmd],
        capture_output=True, text=True, timeout=timeout
    )

def scp_put(local, remote):
    """上传文件到天怿"""
    return subprocess.run(
        ["scp", "-o", "ConnectTimeout=5", local, f"{NODE_USER}@{NODE_IP}:{remote}"],
        capture_output=True, text=True, timeout=30
    )

def check_online():
    """检测天怿是否在线"""
    try:
        r = ssh("echo ONLINE", timeout=10)
        return r.returncode == 0 and "ONLINE" in r.stdout
    except:
        return False

def deploy():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 天怿超个体化部署开始")
    
    # 1. 基础检查
    print("  ① 基础环境...")
    r = ssh("python3 --version && which python3 && uname -a")
    print(f"    {r.stdout.strip()[:100]}")
    
    # 2. 创建目录
    ssh("mkdir -p ~/lgox-ops/scripts ~/lgox-ops/logs ~/lgox-ops/data")
    
    # 3. 上传基因生产脚本
    print("  ② 上传基因引擎...")
    local_script = os.path.expanduser("~/lgox-ops/scripts/tianyi-gene-engine.py")
    if os.path.exists(local_script):
        r = scp_put(local_script, "~/lgox-ops/scripts/tianyi-gene-engine.py")
        print(f"    scp: {'OK' if r.returncode == 0 else 'FAIL'}")
    
    # 4. 测试智谱API
    print("  ③ 测试API...")
    r = ssh('''python3 -c "
import urllib.request, json
k='fd867a96bad64f53a8ece13ac6911887.T3zYiYf7KbxhVTb0'
d=json.dumps({'model':'glm-4-flash','messages':[{'role':'user','content':'hi'}],'max_tokens':5}).encode()
r=urllib.request.Request('https://open.bigmodel.cn/api/paas/v4/chat/completions',data=d,headers={'Content-Type':'application/json','Authorization':f'Bearer {k}'})
try:
    rr=urllib.request.urlopen(r,timeout=10)
    print('GLM OK')
except Exception as e:
    print('GLM ERR:',e)
"''')
    print(f"    {r.stdout.strip()}")
    
    # 5. 首次运行基因生产
    print("  ④ 首次基因生产...")
    r = ssh("cd ~/lgox-ops && python3 scripts/tianyi-gene-engine.py 2>&1")
    print(f"    {r.stdout.strip()[:200]}")
    
    # 6. 添加cron(每30分钟)
    print("  ⑤ cron注册...")
    ssh('(crontab -l 2>/dev/null | grep -v tianyi-gene; echo "*/30 * * * * cd ~/lgox-ops && python3 scripts/tianyi-gene-engine.py >> logs/tianyi-gene.log 2>&1") | crontab -')
    
    # 7. 验证
    r = ssh("crontab -l 2>/dev/null | grep tianyi-gene")
    print(f"    cron: {'已注册' if 'tianyi-gene' in r.stdout else '失败'}")
    
    # 8. 联邦桥注册(通过天枢)
    print("  ⑥ 联邦桥注册...")
    heartbeat = {
        "node": NODE_NAME,
        "node_id": "tianyi-wsl2",
        "role": "gene-producer",
        "type": "wsl2-lightweight",
        "capabilities": ["gene-production", "glm-4-flash"],
        "schedule": "every-30min",
        "target_genes_per_day": 240
    }
    import urllib.request as ur
    try:
        data = json.dumps(heartbeat).encode()
        req = ur.Request("http://100.100.89.2:8765/federation/register", data=data,
            headers={"Content-Type": "application/json"})
        ur.urlopen(req, timeout=5)
        print("    联邦桥: 已注册")
    except Exception as e:
        print(f"    联邦桥: {e}")
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 天怿超个体化完成 ✅")

if __name__ == "__main__":
    if check_online():
        deploy()
    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 天怿离线·跳过部署")
