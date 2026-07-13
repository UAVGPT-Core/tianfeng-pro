#!/usr/bin/env python3
"""
LGOX 联邦节点能力注册表 v1.0 — Node Capability Registry
═══════════════════════════════════════════════════
每个节点运行→自检硬件/软件/负载→上报联邦桥→灵龙分析匹配任务
基于九层金字塔 L3分析层: 能力匹配→最优分配

用法: python3 node-capability.py --register
"""

import json, os, sys, platform, subprocess, time, socket, psutil, datetime, urllib.request

BRIDGE = os.environ.get("LGOX_BRIDGE", "http://100.100.89.2:8765")
NODE = os.environ.get("LGOX_NODE", socket.gethostname())

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
    except: return ""

def detect_capabilities():
    """自检节点全维度能力"""
    cap = {
        "node": NODE,
        "hostname": socket.gethostname(),
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "platform": {},
        "hardware": {},
        "software": {},
        "resources": {},
        "roles": [],
        "load": {},
    }
    
    # ── 平台 ──
    sys_platform = platform.system()
    cap["platform"] = {
        "os": sys_platform,
        "version": platform.version()[:60],
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    
    # ── 硬件 ──
    try:
        cap["hardware"]["cpu_count"] = psutil.cpu_count(logical=True)
        cap["hardware"]["cpu_physical"] = psutil.cpu_count(logical=False)
        mem = psutil.virtual_memory()
        cap["hardware"]["memory_gb"] = round(mem.total / (1024**3), 1)
        disk = psutil.disk_usage("/")
        cap["hardware"]["disk_gb"] = round(disk.total / (1024**3), 1)
        cap["hardware"]["disk_free_gb"] = round(disk.free / (1024**3), 1)
    except: pass
    
    # GPU检测
    if sys_platform == "Darwin":
        gpu = run("system_profiler SPDisplaysDataType 2>/dev/null | grep 'Chip' | head -1")
        if gpu:
            cap["hardware"]["gpu"] = gpu.split(":")[-1].strip()
            cap["hardware"]["has_gpu"] = True
    elif sys_platform == "Linux":
        gpu = run("nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1")
        if gpu:
            cap["hardware"]["gpu"] = gpu
            cap["hardware"]["has_gpu"] = True
        else:
            cap["hardware"]["has_gpu"] = False
    elif sys_platform == "Windows":
        gpu = run("wmic path win32_videocontroller get name 2>nul | findstr /v \"Name\"")
        if gpu:
            cap["hardware"]["gpu"] = gpu.strip()[:80]
            cap["hardware"]["has_gpu"] = True
    
    # 屏幕检测
    cap["hardware"]["has_screen"] = (sys_platform == "Darwin" and "MacBook" not in platform.version()) or \
                                    (sys_platform == "Windows")
    
    # ── 软件 ──
    software = {}
    for tool in ["python3", "python", "ollama", "docker", "nginx", "node", "git"]:
        path = run(f"which {tool} 2>/dev/null || where {tool} 2>nul")
        if path and "not found" not in path.lower():
            software[tool] = True
        else:
            software[tool] = False
    
    # Ollama模型检测
    if software.get("ollama"):
        models = run("ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | tr '\\n' ','")
        if models:
            software["ollama_models"] = models.strip(",")
    
    # Docker容器
    if software.get("docker"):
        containers = run("docker ps --format '{{.Names}}' 2>/dev/null | tr '\\n' ','")
        if containers:
            software["docker_containers"] = containers.strip(",")
    
    cap["software"] = software
    
    # ── 资源 ──
    try:
        cpu_pct = psutil.cpu_percent(interval=1)
        mem_pct = psutil.virtual_memory().percent
        disk_pct = psutil.disk_usage("/").percent
        cap["resources"] = {
            "cpu_percent": cpu_pct,
            "memory_percent": mem_pct,
            "disk_percent": disk_pct,
            "available": cpu_pct < 80 and mem_pct < 80 and disk_pct < 90,
        }
    except: pass
    
    # ── 负载等级 ──
    load_pct = cap["resources"].get("cpu_percent", 50)
    if load_pct < 30:
        cap["load"]["level"] = "idle"
        cap["load"]["can_take"] = "any"
    elif load_pct < 60:
        cap["load"]["level"] = "moderate"
        cap["load"]["can_take"] = "light"
    elif load_pct < 85:
        cap["load"]["level"] = "busy"
        cap["load"]["can_take"] = "critical_only"
    else:
        cap["load"]["level"] = "overloaded"
        cap["load"]["can_take"] = "none"
    
    # ── 角色推导 ──
    roles = []
    if cap["hardware"].get("has_gpu") and software.get("ollama"):
        roles.append("inference")       # 推理节点
    if cap["hardware"].get("has_screen"):
        roles.append("display")         # 展示节点
    if software.get("docker"):
        roles.append("container")       # 容器节点
    if software.get("nginx"):
        roles.append("web")             # Web节点
    if cap["hardware"].get("memory_gb", 0) >= 32:
        roles.append("compute")         # 计算节点
    if sys_platform == "Linux" and not cap["hardware"].get("has_screen"):
        roles.append("server")          # 服务器节点
    if sys_platform == "Windows":
        roles.append("windows_test")    # Windows测试节点
    roles.append("universal")           # 通用节点
    
    # 联邦角色
    if cap["resources"].get("available", True):
        roles.append("worker")          # 可接任务
    
    cap["roles"] = roles
    
    return cap

def register(cap):
    """上报能力到联邦桥"""
    try:
        msg = json.dumps({"type": "capability_report", "capability": cap}, ensure_ascii=False).encode()
        payload = json.dumps({"to": "灵龙", "from": NODE, "content": msg.decode()}).encode()
        req = urllib.request.Request(f"{BRIDGE}/messages/send", data=payload,
            headers={"Content-Type":"application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"注册失败: {e}")
        return False

if __name__ == "__main__":
    cap = detect_capabilities()
    print(json.dumps(cap, ensure_ascii=False, indent=2))
    
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--register", action="store_true", help="注册到联邦桥")
    p.add_argument("--node", default="", help="节点名")
    p.add_argument("--bridge", default="", help="联邦桥地址")
    args = p.parse_args()
    
    if args.node: NODE = args.node
    if args.bridge: BRIDGE = args.bridge
    cap["node"] = NODE  # override
    
    if args.register:
        if register(cap):
            print(f"\n✅ {NODE} 能力已注册到联邦桥")
            roles = cap.get("roles", [])
            print(f"   角色: {', '.join(roles)}")
            print(f"   负载: {cap['load']['level']}")
            print(f"   可用: {'是' if cap['resources'].get('available') else '否'}")
        else:
            print(f"\n❌ {NODE} 注册失败")
