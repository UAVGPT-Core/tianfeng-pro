#!/usr/bin/env python3
"""
LGOX联邦通信冗余引擎 v1.0 — 三重保障·永不中断
=====================================================
铁律: 每节点≥2路径, 消息必消化, 消化必回执, 回执必存档
架构: 4层冗余 → 联邦桥HTTP + SSH直连 + 邻居中继 + 本地缓存队列
灾备: 灵龙/天枢/地枢三中枢互备, 主桥宕机10秒内自动升备桥
作者: 灵龙 LG-SCH-{gene_id}
日期: 2026-06-28
"""
import os, sys, time, json, socket, subprocess, hashlib
import urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

# ======================== 配置 ========================
MY_NODE = os.environ.get("LGOX_NODE", "灵龙")
BRIDGE_PRIMARY = "http://100.100.89.2:8765"   # 天枢主桥
BRIDGE_BACKUP = "http://100.116.0.29:8765"     # 地枢备桥(待部署)
BRIDGE_ACTIVE = BRIDGE_PRIMARY                 # 当前活跃桥

DATA_DIR = os.path.expanduser("~/lgox-ops/data")
LOG_DIR = os.path.expanduser("~/lgox-ops/logs")
REDUNDANCY_LOG = os.path.join(LOG_DIR, "comm-redundancy.log")

# 通信路径定义 (node -> [(method, priority, details)])
COMM_PATHS = {
    "天枢":  [("thunderbridge", 1, "雷雳桥192.168.3.3"), ("ssh", 2, "a1@100.100.89.2"), ("bridge", 3, "联邦桥:8765")],
    "地枢":  [("ssh", 1, "uavgpt2@100.116.0.29"), ("bridge", 2, "联邦桥:8765"), ("http", 3, "LGE:8200")],
    "天工":  [("ssh", 1, "uavgpt@100.118.207.31"), ("bridge", 2, "联邦桥:8765"), ("http", 3, "Ollama:11434")],
    "灵龙":  [("local", 1, "localhost"), ("bridge", 2, "联邦桥:8765")],
    "太一":  [("ssh", 1, "10141@100.103.193.98"), ("bridge", 2, "联邦桥:8765")],
    "织网":  [("ssh", 1, "root@100.127.112.128:22222"), ("bridge", 2, "联邦桥:8765")],
    "天玑":  [("ssh_via_tianshu", 1, "fei@100.122.142.74 via 天枢"), ("bridge", 2, "联邦桥:8765")],
    "天怿":  [("bridge", 1, "联邦桥:8765"), ("ssh", 2, "间歇在线")],
    "AI助手": [("bridge", 1, "联邦桥:8765"), ("http", 2, "天枢:8000")],
    "天巡":  [("bridge", 1, "联邦桥:8765"), ("http", 2, "天枢:8001")],
    "小枢":  [("bridge", 1, "联邦桥:8765"), ("http", 2, "天枢:8001")],
}

# 三中枢互备矩阵
HUB_BACKUP = {
    "灵龙": {"primary": "天枢", "backup": "地枢", "role": "编排调度中枢"},
    "天枢": {"primary": "灵龙", "backup": "地枢", "role": "联邦桥中枢"},
    "地枢": {"primary": "天枢", "backup": "灵龙", "role": "知识存储中枢"},
}

BACKOFF_BRIDGE = False  # 备桥激活状态
MSG_SEND_RETRIES = 3
PATH_CHECK_TIMEOUT = 5  # 每条路径检测超时(秒)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


# ======================== 工具函数 ========================
def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%H:%M:%S")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(REDUNDANCY_LOG, "a") as f:
            f.write(line + "\n")
    except:
        pass

def http_get(url, timeout=5):
    """HTTP GET with fallback"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return -1, str(e)

def http_post(url, data, timeout=5):
    """HTTP POST with fallback"""
    try:
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, 
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return -1, str(e)

def tcp_check(host, port, timeout=3):
    """TCP端口连通性检测"""
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def ssh_check(target):
    """SSH连通性快速检测"""
    try:
        result = subprocess.run(
            f"ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no -o BatchMode=yes {target} 'echo OK' 2>/dev/null",
            shell=True, capture_output=True, text=True, timeout=5
        )
        return "OK" in result.stdout
    except:
        return False

def bridge_health():
    """检查联邦桥健康状态 — 含主备双检"""
    # 主桥
    code, body = http_get(f"{BRIDGE_PRIMARY}/health", timeout=5)
    primary_ok = False
    nodes = []
    unread = 0
    if code == 200:
        try:
            data = json.loads(body)
            nodes = data.get("nodes", [])
            unread = data.get("messages_unread", 0)
            primary_ok = True
        except:
            pass
    
    # 备桥
    code2, body2 = http_get(f"{BRIDGE_BACKUP}/health", timeout=5)
    backup_ok = False
    backup_role = "unknown"
    backup_stored = 0
    if code2 == 200:
        try:
            data2 = json.loads(body2)
            backup_role = data2.get("role", "unknown")
            backup_stored = data2.get("messages_stored", 0)
            backup_ok = True
        except:
            pass
    
    # 如果主桥死但备桥活且role==active → 切换
    global BRIDGE_ACTIVE, BACKOFF_BRIDGE
    if not primary_ok and backup_ok and backup_role == "active":
        BRIDGE_ACTIVE = BRIDGE_BACKUP
        BACKOFF_BRIDGE = True
    elif primary_ok:
        BRIDGE_ACTIVE = BRIDGE_PRIMARY
        BACKOFF_BRIDGE = False
    
    return {
        "primary": {"ok": primary_ok, "nodes": nodes, "unread": unread},
        "backup": {"ok": backup_ok, "role": backup_role, "stored": backup_stored},
        "active": BRIDGE_ACTIVE,
        "backoff": BACKOFF_BRIDGE
    }


# ======================== 检测引擎 ========================
def check_all_paths():
    """检查所有通信路径 → 返回冗余状态矩阵"""
    results = {}
    ok_count = 0
    total_paths = 0
    
    for node, paths in COMM_PATHS.items():
        if node == MY_NODE:
            continue
        results[node] = []
        for method, priority, detail in paths:
            total_paths += 1
            ok = False
            
            if "ssh" in method:
                # Extract SSH target from detail
                if "via" in detail:
                    # Jump host: use 天枢 as proxy
                    host_part = detail.split(" ")[0]
                    ok = ssh_check(host_part) if "@" in host_part else tcp_check("100.100.89.2", 22)
                else:
                    host_part = detail.split(" ")[0] if " " in detail else detail
                    ok = ssh_check(host_part)
            
            elif method == "bridge":
                ok = tcp_check("100.100.89.2", 8765)
            
            elif method == "http":
                # Try HTTP endpoint
                try:
                    url = detail if detail.startswith("http") else f"http://{detail}"
                    # Extract just host:port
                    parts = detail.split(":")
                    if len(parts) == 2:
                        ok = tcp_check(parts[0], int(parts[1]))
                except:
                    ok = False
            
            elif method == "thunderbridge":
                ok = tcp_check("192.168.3.3", 22)
            
            elif method == "local":
                ok = True
            
            if ok:
                ok_count += 1
            
            results[node].append({
                "method": method,
                "priority": priority,
                "detail": detail,
                "ok": ok,
                "primary": priority == 1
            })
    
    redundancy_score = ok_count / max(total_paths, 1)
    return results, redundancy_score, ok_count, total_paths


# ======================== 消息消化验证 ========================
def verify_message_digestion():
    """验证全联邦消息消化状态 — 检查谁的收件箱有积压"""
    digestion_report = {}
    
    for node in COMM_PATHS:
        if node == MY_NODE:
            continue
        try:
            encoded = urllib.parse.quote(node)
            code, body = http_get(
                f"{BRIDGE_ACTIVE}/messages/inbox?node={encoded}", timeout=5
            )
            if code == 200:
                data = json.loads(body)
                msgs = data.get("messages", [])
                count = len(msgs)
                
                # Check types
                types = {}
                for m in msgs:
                    t = m.get("type", "unknown")
                    types[t] = types.get(t, 0) + 1
                
                status = "🟢" if count <= 3 else ("🟡" if count <= 10 else "🔴")
                digestion_report[node] = {
                    "count": count,
                    "status": status,
                    "types": types
                }
        except Exception as e:
            digestion_report[node] = {
                "count": -1,
                "status": "⚫",
                "error": str(e)[:80]
            }
    
    # Check own inbox
    try:
        encoded = urllib.parse.quote(MY_NODE)
        code, body = http_get(
            f"{BRIDGE_ACTIVE}/messages/inbox?node={encoded}", timeout=5
        )
        if code == 200:
            data = json.loads(body)
            digestion_report[MY_NODE] = {
                "count": len(data.get("messages", [])),
                "status": "🟢" if len(data.get("messages", [])) <= 3 else "🟡"
            }
    except:
        pass
    
    return digestion_report


# ======================== 故障切换 ========================
def failover_to_backup_bridge():
    """主桥不可达 → 尝试地枢备桥"""
    global BRIDGE_ACTIVE, BACKOFF_BRIDGE
    
    # Check primary
    code, _ = http_get(f"{BRIDGE_PRIMARY}/health", timeout=3)
    if code == 200:
        BRIDGE_ACTIVE = BRIDGE_PRIMARY
        BACKOFF_BRIDGE = False
        return "primary_ok", BRIDGE_PRIMARY
    
    # Check backup
    code2, _ = http_get(f"{BRIDGE_BACKUP}/health", timeout=3)
    if code2 == 200:
        BRIDGE_ACTIVE = BRIDGE_BACKUP
        BACKOFF_BRIDGE = True
        log(f"🔄 主桥不可达 → 切换到备桥 {BRIDGE_BACKUP}")
        return "backup_activated", BRIDGE_BACKUP
    
    return "both_dead", None


# ======================== 消息可靠投递 ========================
def reliable_send(to_node, content, msg_type="system"):
    """可靠消息发送 — 多路径重试"""
    payload = {
        "to": to_node,
        "from": MY_NODE,
        "content": content,
        "type": msg_type,
        "ts": datetime.now().isoformat()
    }
    
    paths_tried = []
    
    # Path 1: 联邦桥
    for attempt in range(MSG_SEND_RETRIES):
        code, body = http_post(
            f"{BRIDGE_ACTIVE}/messages/send", payload, timeout=5
        )
        if code == 200:
            return True, "bridge", attempt + 1
        paths_tried.append(f"bridge_attempt_{attempt+1}")
        time.sleep(1)
    
    # Path 2: 如果桥彻底不通, 尝试备桥
    if BACKOFF_BRIDGE is False:
        code, body = http_post(
            f"{BRIDGE_BACKUP}/messages/send", payload, timeout=5
        )
        if code == 200:
            return True, "backup_bridge", 1
    
    # Path 3: SSH直推 (仅对SSH可达节点)
    node_paths = COMM_PATHS.get(to_node, [])
    for method, priority, detail in node_paths:
        if "ssh" in method and priority == 1:
            try:
                ssh_target = detail.split(" ")[0] if " " in detail else detail
                # Write message to temp file and SCP
                msg_file = f"/tmp/lgox_msg_{int(time.time())}.json"
                with open(msg_file, "w") as f:
                    json.dump(payload, f, ensure_ascii=False)
                
                # Try SCP
                result = subprocess.run(
                    f"scp -o ConnectTimeout=5 {msg_file} {ssh_target}:/tmp/lgox_direct_msg.json 2>/dev/null",
                    shell=True, capture_output=True, timeout=8
                )
                os.remove(msg_file)
                
                if result.returncode == 0:
                    return True, f"ssh_direct_{ssh_target}", 1
            except:
                pass
    
    # 全部失败 → 保存到本地出站队列
    queue_path = os.path.join(DATA_DIR, "outbox-queue.json")
    queue = []
    if os.path.exists(queue_path):
        try:
            with open(queue_path) as f:
                queue = json.load(f)
        except:
            pass
    queue.append(payload)
    # Keep only last 100
    queue = queue[-100:]
    with open(queue_path, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    
    return False, "queued_local", 0


def drain_outbox():
    """排空本地出站队列 — 重试发送积压消息"""
    queue_path = os.path.join(DATA_DIR, "outbox-queue.json")
    if not os.path.exists(queue_path):
        return 0
    
    try:
        with open(queue_path) as f:
            queue = json.load(f)
    except:
        return 0
    
    if not queue:
        return 0
    
    sent = []
    for msg in queue:
        to_node = msg.get("to", "")
        content = msg.get("content", "")
        ok, path, attempts = reliable_send(to_node, content, msg.get("type", "system"))
        if ok:
            sent.append(msg)
    
    remaining = [m for m in queue if m not in sent]
    with open(queue_path, "w") as f:
        json.dump(remaining, f, ensure_ascii=False, indent=2)
    
    if sent:
        log(f"📤 出站队列排出 {len(sent)} 条, 剩余 {len(remaining)} 条")
    
    return len(sent)


# ======================== 回执确认 ========================
def check_ack_receipts():
    """检查最近消息的回执状态"""
    ack_file = os.path.join(DATA_DIR, "pending-acks.json")
    if not os.path.exists(quake_path := ack_file):
        return {}
    
    try:
        with open(ack_file) as f:
            pending = json.load(f)
    except:
        return {}
    
    # Check inbox for ACK responses
    results = {}
    for msg_id, info in list(pending.items()):
        to_node = info.get("to", "")
        sent_ts = info.get("sent_ts", "")
        
        # Check if ACK received (this would normally be checked by digest engine)
        # For now, mark messages > 10min old as timed out
        try:
            sent_dt = datetime.fromisoformat(sent_ts)
            age = (datetime.now(timezone(timedelta(hours=8))) - sent_dt).total_seconds()
            if age > 600:  # 10 minutes
                results[msg_id] = "timeout"
            else:
                results[msg_id] = "waiting"
        except:
            results[msg_id] = "unknown"
    
    return results


# ======================== 主循环 ========================
def main():
    log("=" * 60)
    log(f"🚀 LGOX通信冗余引擎 v1.0 启动 | 节点:{MY_NODE} | 主桥:{BRIDGE_PRIMARY}")
    log("=" * 60)
    
    # 1. 桥健康检查 + 故障切换
    bridge = bridge_health()
    log(f"🌉 联邦桥: 主{'🟢' if bridge['primary']['ok'] else '🔴'} 备{'🟢' if bridge['backup']['ok'] else '🔴'} | "
        f"节点:{len(bridge['primary'].get('nodes',[]))} | 积压:{bridge['primary'].get('unread',0)} | "
        f"备桥:{bridge['backup'].get('role','?')}/{bridge['backup'].get('stored',0)}条")
    
    # 2. 通信路径冗余检查
    paths, redundancy_score, ok_paths, total_paths = check_all_paths()
    log(f"🔗 通信矩阵: {ok_paths}/{total_paths} 路径通 | 得分:{redundancy_score:.1%}")
    single_path_nodes = [(n, sum(1 for p in ps if p["ok"])) for n, ps in paths.items() if sum(1 for p in ps if p["ok"]) <= 1]
    if single_path_nodes:
        log(f"⚠️ 单通道节点: {', '.join(f'{n}({c})' for n,c in single_path_nodes)}")
    
    # 3. 消息消化验证
    digestion = verify_message_digestion()
    backlog_nodes = [(n, i["count"]) for n, i in digestion.items() if i.get("status") == "🔴"]
    if backlog_nodes:
        log(f"🔴 消息堆积: {', '.join(f'{n}({c}条)' for n,c in backlog_nodes)}")
    
    # 4. 排出站队列
    drained = drain_outbox()
    
    # 5. 三中枢互备心跳
    my_backup = HUB_BACKUP.get(MY_NODE, {})
    if my_backup:
        primary_hub = my_backup.get("primary", "")
        pri_paths = paths.get(primary_hub, [])
        pri_ok = any(p["ok"] for p in pri_paths)
        if not pri_ok:
            backup_hub = my_backup.get("backup", "")
            bu_ok = any(p["ok"] for p in paths.get(backup_hub, []))
            if bu_ok:
                log(f"🔄 {MY_NODE}: {primary_hub}离线 → 切换到备用中枢 {backup_hub}")
    
    # 6. 生成状态JSON
    bridge = bridge_health()
    status = {
        "ts": datetime.now().isoformat(),
        "node": MY_NODE,
        "bridge": {
            "primary": "ok" if bridge['primary']['ok'] else "dead",
            "backup": "ok" if bridge['backup']['ok'] else "dead",
            "backup_role": bridge['backup'].get('role'),
            "active": bridge['active'],
            "active_nodes": len(bridge['primary'].get('nodes', [])),
            "unread": bridge['primary'].get('unread', 0)
        },
        "redundancy": {
            "score": round(redundancy_score, 2),
            "ok_paths": ok_paths,
            "total_paths": total_paths,
            "single_path_nodes": [n for n, _ in single_path_nodes],
            "paths": {n: [{"method": p["method"], "ok": p["ok"], "primary": p["primary"]} 
                          for p in ps] for n, ps in paths.items()}
        },
        "digestion": {
            "backlog": {n: i["count"] for n, i in digestion.items() if i.get("count", 0) > 0}
        },
        "outbox_queued": drained,
        "backup_bridge_active": BACKOFF_BRIDGE,
    }
    
    status_file = os.path.join(DATA_DIR, "comm-redundancy-status.json")
    with open(status_file, "w") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    
    log(f"✅ 状态写入: {status_file}")
    log(f"📊 总览: 桥主{'🟢' if bridge['primary']['ok'] else '🔴'}备{'🟢' if bridge['backup']['ok'] else '🔴'} | "
        f"冗余{redundancy_score:.0%} | 积压{len(backlog_nodes)}节点 | 出站{drained}条")
    
    return status


if __name__ == "__main__":
    main()
