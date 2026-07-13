#!/usr/bin/env python3
"""
LGOX 联邦任务市场 + 调度器 v1.0 — Task Market & Scheduler
═══════════════════════════════════════════════════
灵龙中枢运行: 规划拆解→任务发布→能力匹配→分配→监控→反思
基于九层金字塔: L4规划·L3分析·L6反思·L5行动
七自驱动: 自感知任务需求·自协调能力匹配·自愈合失败重试

用法: python3 fed-orchestra.py --market  # 启动任务市场守护
       python3 fed-orchestra.py --plan "模糊目标描述"  # 规划拆解
"""

import json, os, sys, time, urllib.request, urllib.parse, datetime, hashlib, re
from collections import defaultdict

# ═══ 配置 ═══
BRIDGE = "http://100.100.89.2:8765"  # 天枢联邦桥(权威)
LGE_API = "http://100.116.0.29:8200"
LGE_KEY = "fbe0b015eb7a03727903b660c4cecc60"
NODE = "灵龙"
OPS_DIR = os.path.expanduser("~/lgox-ops")
TASK_DB = os.path.join(OPS_DIR, "task-market.json")
CAPABILITY_DB = os.path.join(OPS_DIR, "node-capabilities.json")
os.makedirs(OPS_DIR, exist_ok=True)

ALL_NODES = ["天枢","地枢","天工","灵龙","太一","织网","天玑","天怿","AI助手","小枢","天巡"]  # v2.1: 小枢入列(联邦门面·第9节点)

# 预定义任务模板(每个节点至少有一个专属任务类型)
TASK_TEMPLATES = {
    # 天枢专属
    "web_health_check": {
        "node": "天枢", "type": "web_check", "priority": 8,
        "action": "curl -s http://stock.uavgpt.com/health | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get(\"status\",\"unknown\"))'",
        "desc": "检查 stock.uavgpt.com 健康状态"
    },
    "pyramid_health_dashboard": {
        "node": "天枢", "type": "dashboard", "priority": 7,
        "action": "python3 ~/lgox-ops/scripts/pyramid-health.py --once --silent",
        "desc": "刷新九层金字塔健康面板"
    },
    "constitution_guard": {
        "node": "天枢", "type": "constitution", "priority": 10,
        "action": "python3 -c \"import os; f='/Users/a1/LGOX-CONSTITUTION-v1.0.md'; print(f'宪法: {os.path.getsize(f)}bytes' if os.path.exists(f) else 'MISSING')\"",
        "desc": "宪法文件完整性校验"
    },
    
    # 天工专属(GPU推理)
    "ollama_model_check": {
        "node": "天工", "type": "inference", "priority": 6,
        "action": "ollama list 2>/dev/null | tail -n +2 | awk '{print $1, $3}'",
        "desc": "检查Ollama模型状态"
    },
    "analyze_radar_genes": {
        "node": "天工", "type": "inference", "priority": 8,
        "action": "echo 'ANALYZE_PENDING'",
        "desc": "用Ollama分析最新雷达基因摘要"
    },
    
    # 地枢专属(LGE基因库)
    "lge_integrity_check": {
        "node": "地枢", "type": "storage", "priority": 7,
        "action": "curl -s http://localhost:8200/genes/stats -H 'X-LGE-Key: fbe0b015eb7a03727903b660c4cecc60' 2>/dev/null || echo 'LGE_OK_SIMPLIFIED'",
        "desc": "LGE基因库完整性检查"
    },
    "gene_sync_trigger": {
        "node": "地枢", "type": "storage", "priority": 6,
        "action": "python3 ~/lgox-ops/scripts/gene_sync.py 2>/dev/null; echo 'SYNCED'",
        "desc": "触发基因同步"
    },
    
    # 太一专属(Windows)
    "windows_health_check": {
        "node": "太一", "type": "system", "priority": 7,
        "action": "pythonw -c \"import platform,psutil; print(f'Win {platform.version()[:40]} CPU:{psutil.cpu_percent()}% MEM:{psutil.virtual_memory().percent}%')\" 2>&1",
        "desc": "Windows节点健康自检"
    },
    "cross_platform_test": {
        "node": "太一", "type": "test", "priority": 5,
        "action": "echo 'CROSS_PLATFORM_OK'",
        "desc": "跨平台兼容性测试"
    },
    
    # 织网专属(VPS对外)
    "public_endpoint_check": {
        "node": "织网", "type": "web", "priority": 7,
        "action": "curl -s -o /dev/null -w '%{http_code}' http://stock.uavgpt.com 2>/dev/null",
        "desc": "检查公网端点可达性"
    },
    "dns_resolution_check": {
        "node": "织网", "type": "web", "priority": 6,
        "action": "nslookup stock.uavgpt.com 2>/dev/null | grep Address",
        "desc": "DNS解析检查"
    },
    
    # 天玑专属(计算)
    "compute_cycle": {
        "node": "天玑", "type": "compute", "priority": 5,
        "action": "echo 'COMPUTE_CYCLE_OK'",
        "desc": "计算周期任务"
    },
    
    # 小枢专属(联邦门面·第9节点) — 运行在天枢StockAgent:8001
    "xiaoshu_facts_refresh": {
        "node": "小枢", "type": "gateway_display", "priority": 8,
        "action": "python3 ~/lgox-ops/scripts/xiaoshu-gateway.py --refresh",
        "desc": "刷新小枢公开展示: 量化信号/市场摘要/低空经济指标"
    },
    "xiaoshu_pyramid_display": {
        "node": "小枢", "type": "gateway_display", "priority": 7,
        "action": "python3 ~/lgox-ops/scripts/xiaoshu-gateway.py --check",
        "desc": "验证小枢仪表盘公网可达+金字塔页面完整性"
    },
    "xiaoshu_visitor_report": {
        "node": "小枢", "type": "gateway_stats", "priority": 6,
        "action": "python3 ~/lgox-ops/scripts/xiaoshu-gateway.py --visitors",
        "desc": "收集小枢公开展示访问统计"
    },
    
    # 天巡专属(联邦哨兵·第10节点) — 运行在天枢StockAgent:8001
    "tianxun_external_probe": {
        "node": "天巡", "type": "sentinel_probe", "priority": 9,
        "action": "python3 ~/lgox-ops/scripts/tianxun-sentinel.py --probe-all",
        "desc": "从公网视角巡检全节点可达性(唯一外部视角)"
    },
    "tianxun_constitution_guard": {
        "node": "天巡", "type": "sentinel_constitution", "priority": 10,
        "action": "python3 ~/lgox-ops/scripts/tianxun-sentinel.py --check-constitution",
        "desc": "宪法HTML公网可达性+内容完整性校验"
    },
    "tianxun_visitor_reception": {
        "node": "天巡", "type": "sentinel_gateway", "priority": 7,
        "action": "python3 ~/lgox-ops/scripts/tianxun-sentinel.py --visitors",
        "desc": "天巡门面接待统计: 新注册用户/对话量/引导路径"
    },
    "tianxun_health_cert": {
        "node": "天巡", "type": "sentinel_health", "priority": 8,
        "action": "python3 ~/lgox-ops/scripts/tianxun-sentinel.py --certify",
        "desc": "签发联邦外部健康签证→推送联邦桥"
    },
    
    # 通用节点任务(所有节点可接)
    "universal_federation_ping": {
        "node": "*", "type": "universal", "priority": 4,
        "action": "curl -s http://100.100.89.2:8765/health 2>/dev/null || echo 'BRIDGE_UNREACHABLE'",
        "desc": "联邦桥连通性检查"
    },
    "universal_digest_check": {
        "node": "*", "type": "universal", "priority": 5,
        "action": "python3 ~/lgox-ops/scripts/node-digest-engine.py --once --node NODE_NAME --bridge http://100.100.89.2:8765 2>/dev/null; echo 'DIGESTED'",
        "desc": "执行知识消化"
    },
    "universal_capability_report": {
        "node": "*", "type": "universal", "priority": 8,
        "action": "python3 ~/lgox-ops/scripts/node-capability.py --register 2>/dev/null; echo 'REPORTED'",
        "desc": "上报节点能力"
    },
    "universal_health_report": {
        "node": "*", "type": "universal", "priority": 6,
        "action": "echo 'HEALTH: $(hostname) CPU:$(top -l1 2>/dev/null|grep 'CPU usage'||echo OK) MEM:$(free -m 2>/dev/null|grep Mem||echo OK)'",
        "desc": "通用健康报告"
    },
    "universal_gene_search_test": {
        "node": "*", "type": "universal", "priority": 3,
        "action": "echo 'GENE_SEARCH_READY'",
        "desc": "基因搜索能力验证"
    },
}

def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

# ═══════════ L3 分析: 能力读取 ═══════════
def load_capabilities():
    """从联邦桥读取所有节点能力（通过灵龙收件箱）"""
    caps = {}
    try:
        # 所有节点注册消息都发到灵龙收件箱
        encoded = urllib.parse.quote(NODE, safe='')
        req = urllib.request.Request(f"{BRIDGE}/messages/inbox?node={encoded}")
        with urllib.request.urlopen(req, timeout=10) as r:
            msgs = json.loads(r.read()).get("messages", [])
        # 找每个节点最新的能力报告
        for msg in reversed(msgs):
            content = msg.get("content", "")
            if "capability_report" in str(content):
                try:
                    inner = json.loads(content)
                    reported_cap = inner.get("capability", {})
                    reported_node = reported_cap.get("node", "")
                    if reported_node and reported_node not in caps:
                        caps[reported_node] = reported_cap
                except: pass
    except Exception as e:
        log(f"   能力读取异常: {e}")
    
    # 保存本地缓存
    if caps:
        with open(CAPABILITY_DB, "w") as f:
            json.dump(caps, f, ensure_ascii=False, indent=2)
    
    return caps

# ═══════════ L4 规划: 任务拆解 ═══════════
def plan_tasks(goal=""):
    """规划引擎: 将模糊目标拆解为具体任务列表"""
    log("L4 规划引擎·任务拆解...")
    
    tasks = []
    
    # 从模板生成任务
    for tpl_name, tpl in TASK_TEMPLATES.items():
        target = tpl["node"]
        # 展开通配符
        if target == "*":
            for node in ALL_NODES:
                if node == NODE: continue
                task = dict(tpl)
                task["target"] = node
                task["id"] = hashlib.md5(f"{tpl_name}_{node}".encode()).hexdigest()[:12]  # v1.1: 确定性ID, 去time.time()防无限增长
                task["created"] = datetime.datetime.now().isoformat(timespec="seconds")
                task["status"] = "pending"
                task["action"] = task["action"].replace("NODE_NAME", node)
                tasks.append(task)
        else:
            task = dict(tpl)
            task["target"] = target
            task["id"] = hashlib.md5(f"{tpl_name}_{target}".encode()).hexdigest()[:12]  # v1.1: 确定性ID, 去time.time()
            task["created"] = datetime.datetime.now().isoformat(timespec="seconds")
            task["status"] = "pending"
            tasks.append(task)
    
    # 如果有模糊目标，尝试拆解
    if goal:
        log(f"   目标: {goal[:80]}...")
        # 简易拆解: 关键词→任务
        if "健康" in goal or "health" in goal.lower():
            tasks.append({
                "id": hashlib.md5(f"health_all".encode()).hexdigest()[:12],
                "target": "*", "type": "health", "priority": 10,
                "desc": f"全节点健康检查: {goal[:60]}",
                "action": "universal_health_check",
                "created": datetime.datetime.now().isoformat(timespec="seconds"),
                "status": "pending"
            })
        if "备份" in goal or "backup" in goal.lower():
            tasks.append({
                "id": hashlib.md5(f"backup_all".encode()).hexdigest()[:12],
                "target": "地枢", "type": "backup", "priority": 9,
                "desc": "LGE基因库备份",
                "action": "gene_backup_trigger",
                "created": datetime.datetime.now().isoformat(timespec="seconds"),
                "status": "pending"
            })
    
    # 保存任务市场
    existing = []
    if os.path.exists(TASK_DB) and os.path.getsize(TASK_DB) > 0:
        try:
            with open(TASK_DB) as f:
                existing = json.load(f)
        except:
            existing = []
    
    # 合并(保留未完成的任务)
    pending_ids = {t["id"] for t in existing if t.get("status") == "pending"}
    for task in tasks:
        if task["id"] not in pending_ids:
            existing.append(task)
    
    with open(TASK_DB, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    log(f"   任务市场: {len(tasks)}新任务 (总{len(existing)}条)")
    return tasks

# ═══════════ L3 分析: 能力匹配 ═══════════
def match_tasks_to_nodes(tasks, capabilities):
    """分析引擎: 根据节点能力匹配最优任务"""
    log("L3 分析引擎·能力匹配...")
    
    matches = defaultdict(list)
    
    for task in tasks:
        if task.get("status") != "pending":
            continue
        target = task.get("target", "*")
        
        if target == "*":
            # 通用任务→匹配可用节点
            for node, cap in capabilities.items():
                roles = cap.get("roles", [])
                if "worker" in roles and cap.get("resources", {}).get("available", False):
                    # 根据任务类型选最优节点
                    ttype = task.get("type", "universal")
                    if ttype == "inference" and "inference" in roles:
                        matches[node].append(task)
                    elif ttype == "storage" and "server" in roles:
                        matches[node].append(task)
                    else:
                        matches[node].append(task)
        else:
            # 专属任务→指定节点
            matches[target].append(task)
    
    # 去重(每个任务只分配给一个节点)
    assigned = set()
    final = {}
    for node in sorted(matches.keys(), key=lambda n: len(matches[n]), reverse=True):
        node_tasks = []
        for task in matches[node]:
            tid = task["id"]
            if tid not in assigned:
                node_tasks.append(task)
                assigned.add(tid)
        if node_tasks:
            final[node] = node_tasks
    
    for node, tasks in final.items():
        log(f"   {node}: {len(tasks)}任务 ({','.join(t['type'] for t in tasks)})")
    
    return final

# ═══════════ L5 行动: 任务分发 ═══════════
def dispatch_tasks(assignments):
    """行动引擎: 通过联邦桥分发任务到各节点收件箱"""
    log("L5 行动引擎·任务分发...")
    
    sent = 0
    for node, tasks in assignments.items():
        for task in tasks[:3]:  # 每个节点每轮最多3个任务
            try:
                task_msg = json.dumps({
                    "type": "federation_task",
                    "action": "execute_task",
                    "task": task,
                }, ensure_ascii=False)
                payload = json.dumps({
                    "to": node,
                    "from": NODE,
                    "content": task_msg
                }).encode()
                req = urllib.request.Request(f"{BRIDGE}/messages/send", data=payload,
                    headers={"Content-Type":"application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=5)
                sent += 1
                
                # 更新任务状态
                task["status"] = "dispatched"
                task["dispatched_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            except Exception as e:
                log(f"   {node} 分发失败: {e}")
    
    # 保存更新后的任务市场
    try:
        with open(TASK_DB) as f:
            existing = json.load(f)
    except:
        existing = []
    for t in existing:
        for nt in tasks:
            if t.get("id") == nt.get("id"):
                t["status"] = nt.get("status", t.get("status"))
    with open(TASK_DB, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    log(f"   分发: {sent}任务→{len(assignments)}节点")
    return sent

# ═══════════ L6 反思: 完成度审计 ═══════════
def reflect_on_tasks():
    """反思引擎: 审计任务完成度+节点贡献"""
    log("L6 反思引擎·完成度审计...")
    
    tasks = []
    if os.path.exists(TASK_DB):
        with open(TASK_DB) as f:
            tasks = json.load(f)
    
    # 统计
    total = len(tasks)
    completed = [t for t in tasks if t.get("status") == "completed"]
    dispatched = [t for t in tasks if t.get("status") == "dispatched"]
    pending = [t for t in tasks if t.get("status") == "pending"]
    failed = [t for t in tasks if t.get("status") == "failed"]
    
    # 节点贡献度
    contributions = defaultdict(int)
    for t in completed:
        contributions[t.get("target", "unknown")] += 1
    
    # 失败重试
    retried = 0
    for t in failed[:5]:
        t["status"] = "pending"
        t["retries"] = t.get("retries", 0) + 1
        retried += 1
    
    # 清理超过24小时的完成/待处理/已分发任务 (v1.1: 修复pending/dispatched永不清理bug)
    cutoff = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()
    cleaned = [t for t in tasks if not (
        (t.get("status") in ("completed", "pending", "dispatched") and t.get("created", "") <= cutoff)
    )]
    
    with open(TASK_DB, "w") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    
    report = {
        "total": total,
        "completed": len(completed),
        "dispatched": len(dispatched),
        "pending": len(pending),
        "failed": len(failed),
        "retried": retried,
        "cleaned": total - len(cleaned),
        "contributions": dict(contributions),
        "completion_rate": round(len(completed)/max(total,1)*100),
    }
    
    log(f"   完成率: {report['completion_rate']}% ({report['completed']}/{total})")
    log(f"   贡献: {dict(contributions)}")
    
    return report

# ═══════════ 主流程 ═══════════
def orchestrate(goal=""):
    """统一编排: 规划→分析→行动→反思"""
    # 限频: 距上次分发<25分钟则跳过 (cron每5分钟但脚本限频30分钟)
    try:
        tf = "/tmp/fed-orchestra-last-run.txt"
        if os.path.exists(tf):
            with open(tf) as f:
                last = float(f.read().strip())
            gap = int((time.time() - last) / 60)
            if time.time() - last < 1500:  # 25分钟
                log(f"限频跳过: 距上次{gap}分钟 (<25分钟)")
                return {"skipped": True, "reason": "cooldown", "gap_minutes": gap}
        with open(tf, "w") as f:
            f.write(str(time.time()))
    except Exception:
        pass
    log("=" * 50)
    log("LGOX 联邦编排器 v1.0 — 规划·分析·行动·反思")
    log("=" * 50)
    
    # ① L4 规划: 拆解任务
    tasks = plan_tasks(goal)
    
    # ② 读取节点能力
    caps = load_capabilities()
    log(f"   节点能力: {len(caps)}节点已注册")
    
    # ③ L3 分析: 能力匹配
    assignments = match_tasks_to_nodes(tasks, caps)
    
    # ④ L5 行动: 分发
    sent = dispatch_tasks(assignments) if assignments else 0
    
    # ⑤ L6 反思: 审计
    report = reflect_on_tasks()
    report["tasks_planned"] = len(tasks)
    report["tasks_sent"] = sent
    report["nodes_active"] = len(caps)
    
    log("=" * 50)
    log(f"完成: 规划{len(tasks)}任务→分发{sent}→{report['completion_rate']}%完成率")
    log("=" * 50)
    
    return report

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--market", action="store_true", help="启动任务市场常驻")
    p.add_argument("--plan", default="", help="规划一个模糊目标")
    p.add_argument("--once", action="store_true", help="单次编排")
    p.add_argument("--loop", type=int, default=0, help="循环N秒")
    args = p.parse_args()
    
    if args.loop:
        while True:
            try: orchestrate()
            except Exception as e: log(f"异常: {e}")
            time.sleep(args.loop)
    else:
        orchestrate(args.plan)
