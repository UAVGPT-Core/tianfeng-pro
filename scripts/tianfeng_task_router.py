#!/usr/bin/env python3
"""
联邦任务调度引擎 v1.0 — 跨节点任务标准协议
===========================================
让联邦作业从"手动SSH"升级为"标准化任务分发+结果回流"

协议:
  1. 创建任务包 → JSON格式
  2. 通过联邦桥消息队列分发到目标节点
  3. 目标节点执行并返回结果
  4. 结果自动写入LGE基因

用法:
  python3 tianfeng_task_router.py dispatch --target 天枢 --command "ls -la"
  python3 tianfeng_task_router.py dispatch --target 灵龙 --command "tianfeng super status"
  python3 tianfeng_task_router.py poll                     # 轮询待处理任务
  python3 tianfeng_task_router.py status                   # 查看任务状态
"""
import json, os, sys, uuid, subprocess, urllib.request, time
from datetime import datetime
from pathlib import Path

VERSION = "1.0"
TASK_DIR = os.path.expanduser("~/.federation-tasks")
os.makedirs(TASK_DIR, exist_ok=True)
os.makedirs(f"{TASK_DIR}/sent", exist_ok=True)
os.makedirs(f"{TASK_DIR}/received", exist_ok=True)
os.makedirs(f"{TASK_DIR}/results", exist_ok=True)

LGE_API = "http://100.116.0.29:8200"

NODES = {
    "太一": {"host": "127.0.0.1", "user": "root", "key": "~/.ssh/id_ed25519"},
    "天枢": {"host": "100.100.89.2", "user": "a1", "key": "~/.ssh/id_ed25519"},
    "灵龙": {"host": "100.120.20.52", "user": "a112233", "key": "~/.ssh/id_ed25519"},
}

# 节点能力路由表
NODE_CAPABILITIES = {
    "天枢": ["code", "review", "super", "swarm", "mlge", "pentagon", "gpc", "fgi", "api", "ngc_router"],
    "灵龙": ["code", "review", "super", "swarm", "mlge", "pentagon", "gpc", "fgi", "api"],
    "太一": ["miner", "evo", "memory_sync", "fed_bridge"],
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def new_id():
    return uuid.uuid4().hex[:12]


# ─── 任务创建 ───

def create_task(target, command, description="", timeout=120):
    """创建标准化任务包"""
    task = {
        "id": new_id(),
        "type": "federation_task",
        "version": VERSION,
        "source": NODES["太一"]["host"],
        "target": target,
        "command": command,
        "description": description or command[:60],
        "timeout": timeout,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
    }
    # 保存到本地
    path = f"{TASK_DIR}/sent/{task['id']}.json"
    with open(path, "w") as f:
        json.dump(task, f, indent=2)
    return task


def execute_ssh(node_name, command, timeout=120):
    """通过SSH在目标节点执行命令"""
    cfg = NODES.get(node_name)
    if not cfg:
        return {"error": f"未知节点: {node_name}"}

    if cfg["host"] == "127.0.0.1":
        # 本地执行
        try:
            r = subprocess.run(command, shell=True, capture_output=True,
                             text=True, timeout=timeout)
            return {
                "stdout": r.stdout[-3000:],
                "stderr": r.stderr[-1000:],
                "exit_code": r.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"超时({timeout}s)", "stdout": "", "exit_code": -1}
        except Exception as e:
            return {"error": str(e), "exit_code": -1}
    else:
        # SSH远程执行
        key = os.path.expanduser(cfg["key"])
        cmd = [
            "ssh", "-i", key,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-o", f"ServerAliveInterval={min(30, timeout//2)}",
            f"{cfg['user']}@{cfg['host']}",
            command
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return {
                "stdout": r.stdout[-3000:],
                "stderr": r.stderr[-1000:],
                "exit_code": r.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"SSH超时({timeout}s)", "exit_code": -1}
        except Exception as e:
            return {"error": str(e), "exit_code": -1}


def write_result_gene(task, result):
    """将任务结果写入LGE基因"""
    status = "✅" if result.get("exit_code") == 0 else "❌"
    stdout_preview = result.get("stdout", "")[:200].replace("\n", "; ")
    gene = f"""[FED-TASK-{task['id']}]
[联邦任务] {task['description']}
来源: {task['source']} → 目标: {task['target']}
状态: {status} (exit_code={result.get('exit_code','?')})
结果: {stdout_preview}
"""

    data = json.dumps({
        "content": gene.strip(),
        "gene_type": "federation_task",
        "source": "federation-task-router",
        "tags": ["联邦任务", task['target'], status]
    }).encode()

    try:
        req = urllib.request.Request(
            f"{LGE_API}/genes/write",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200
    except:
        return False


# ─── 智能路由 ───

def smart_route(description):
    """根据任务描述自动路由到最合适的节点"""
    desc_lower = description.lower()

    # 能力映射
    capability_map = {
        "super": ["天枢", "灵龙"],
        "swarm": ["天枢", "灵龙"],
        "mlge": ["天枢", "灵龙"],
        "ngc_router": ["天枢"],
        "code": ["天枢", "灵龙"],
        "review": ["天枢", "灵龙"],
        "gpc": ["天枢", "灵龙"],
        "fgi": ["天枢", "灵龙"],
    }

    for capability, nodes in capability_map.items():
        if capability in desc_lower:
            return nodes[0]  # 返回第一个可用节点

    # 默认路由到天枢（最强节点）
    return "天枢"


# ─── CLI命令 ───

def cmd_dispatch(args):
    """调度任务到目标节点"""
    target = None
    command = None
    desc = ""
    timeout = 120

    i = 0
    while i < len(args):
        if args[i] == "--target" and i+1 < len(args):
            target = args[i+1]; i += 2
        elif args[i] == "--command" and i+1 < len(args):
            command = args[i+1]; i += 2
        elif args[i] == "--desc" and i+1 < len(args):
            desc = args[i+1]; i += 2
        elif args[i] == "--timeout" and i+1 < len(args):
            timeout = int(args[i+1]); i += 2
        else:
            i += 1

    if not target:
        # 自动路由
        target = smart_route(command or "")
        log(f"自动路由到: {target}")

    if not command:
        print("需要 --command")
        return

    task = create_task(target, command, desc or command[:60], timeout)
    log(f"任务 {task['id']} → {target}: {command[:60]}")

    result = execute_ssh(target, command, timeout)
    task["status"] = "done" if result.get("exit_code") == 0 else "failed"
    task["result"] = result

    # 保存结果
    result_path = f"{TASK_DIR}/results/{task['id']}.json"
    with open(result_path, "w") as f:
        json.dump(task, f, indent=2, ensure_ascii=False)

    # 写入LGE
    write_result_gene(task, result)

    # 输出
    if result.get("stdout"):
        print(result["stdout"])
    if result.get("stderr"):
        print(f"[stderr] {result['stderr']}", file=sys.stderr)
    if result.get("error"):
        print(f"[ERROR] {result['error']}")

    log(f"任务完成: exit_code={result.get('exit_code')}")


def cmd_status():
    """查看任务状态"""
    sent = [f for f in os.listdir(f"{TASK_DIR}/sent") if f.endswith(".json")]
    results = [f for f in os.listdir(f"{TASK_DIR}/results") if f.endswith(".json")]

    print(f"联邦任务调度引擎 v{VERSION}")
    print(f"  待发送: {len([f for f in sent if not os.path.exists(f'{TASK_DIR}/results/'+f)])}")
    print(f"  已完成: {len(results)}")

    if results:
        print(f"\n最近任务:")
        results.sort(reverse=True)
        for r_file in results[-5:]:
            with open(f"{TASK_DIR}/results/{r_file}") as f:
                task = json.load(f)
            icon = "✅" if task.get("status") == "done" else "❌"
            print(f"  {icon} {task['id'][:8]} → {task.get('target','?')}: {task.get('description','')[:40]}")


def cmd_route(description):
    """测试路由"""
    target = smart_route(description)
    caps = NODE_CAPABILITIES.get(target, [])
    print(f"任务: {description}")
    print(f"路由到: {target}")
    print(f"可用能力: {', '.join(caps[:5])}")


# ─── 主入口 ───

def print_help():
    print(f"""联邦任务调度引擎 v{VERSION}

用法:
  dispatch --target <节点> --command "<命令>" [--desc "描述"] [--timeout 秒]
    调度任务(不指定target则自动路由)
  
  status        查看任务状态
  route <描述>   测试路由决策

示例:
  python3 tianfeng_task_router.py dispatch --target 天枢 --command "tianfeng super status"
  python3 tianfeng_task_router.py dispatch --command "tianfeng super flywheel 1"
  python3 tianfeng_task_router.py status
  python3 tianfeng_task_router.py route "跑一圈超个体飞轮"
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
    elif sys.argv[1] == "dispatch":
        cmd_dispatch(sys.argv[2:])
    elif sys.argv[1] == "status":
        cmd_status()
    elif sys.argv[1] == "route":
        desc = " ".join(sys.argv[2:])
        cmd_route(desc)
    else:
        print_help()
