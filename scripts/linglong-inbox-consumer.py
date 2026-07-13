#!/usr/bin/env python3
"""
灵龙·六合飞轮执行引擎 v4.0 — GCP v5.0·银河通讯协议·2035级
十一制消息类型·六必填字段·三段式事务·优先级路由
七自基因: 自感知→自协调→自愈合→自进化→自迭代→自反思→自约束
六合闭环: 通(收)→处(TYPE解析)→执(安全白名单执行)→馈(ACK回复)→审(audit日志)→基因(入库)
"""

import json, time, urllib.request, os, subprocess, re, uuid
from datetime import datetime

BRIDGE = "http://127.0.0.1:8765"
MY_NODE = "灵龙"
STATE_FILE = os.path.expanduser("~/lgox-ops/data/linglong-exec-state.json")
AUDIT_LOG = os.path.expanduser("~/lgox-ops/logs/linglong-exec-audit.log")
TASK_LOG  = os.path.expanduser("~/lgox-ops/logs/linglong-task-exec.log")

# ─── GCP v5.0 · 十一制消息类型 ───
# P0(三路并发): ALERT / ROUNDTABLE / PATCH
# P1(双路):     TASK / TASK_DONE / ACK / STATE
# P2(单路):     HEARTBEAT / GENE / QUERY / NOTICE
GCP_TYPES = {
    "ALERT":     {"pri": "P0", "routes": 3, "desc": "告警·三路并发"},
    "ROUNDTABLE":{"pri": "P0", "routes": 3, "desc": "圆桌·三路广播"},
    "PATCH":     {"pri": "P0", "routes": 3, "desc": "补丁·三路同步"},
    "TASK":      {"pri": "P1", "routes": 2, "desc": "任务·双路"},
    "TASK_DONE": {"pri": "P1", "routes": 2, "desc": "完成·双路回执"},
    "ACK":       {"pri": "P1", "routes": 2, "desc": "确认·双路"},
    "STATE":     {"pri": "P1", "routes": 2, "desc": "状态·双路同步"},
    "HEARTBEAT": {"pri": "P2", "routes": 1, "desc": "心跳·单路"},
    "GENE":      {"pri": "P2", "routes": 1, "desc": "基因·单路"},
    "QUERY":     {"pri": "P2", "routes": 1, "desc": "查询·单路"},
    "NOTICE":    {"pri": "P2", "routes": 1, "desc": "通知·单路"},
}

# 联邦节点桥路由表
NODE_BRIDGES = {
    "灵龙": "http://100.120.20.52:8765",
    "天枢": "http://100.100.89.2:8765",
    "地枢": "http://100.116.0.29:8765",
    "天工": "http://100.118.207.31:8765",
    "太一": "http://100.103.193.98:8765",
    "织网": "http://100.127.112.128:8765",
    "天玑": "http://100.122.142.74:8765",
}

def get_bridge(node):
    return NODE_BRIDGES.get(node, BRIDGE)

# ─── 安全白名单 ───
SAFE_COMMANDS = {
    "memory_standardize": {
        "desc": "记忆系统标准化",
        "cmd": ["python3", "-c", """
import json
d = json.load(open('/Volumes/990Pro/public-web/dashboard.json'))
layers = d.get('memory_system', {}).get('layers', {})
assert len(layers) >= 7, f'layers={len(layers)} < 7'
f = open('/Volumes/990Pro/public-web/pyramid.html').read()
if '七层记忆' not in f:
    f = f.replace('六层记忆', '七层记忆')
    open('/Volumes/990Pro/public-web/pyramid.html','w').write(f)
print(f'标准化完成: {len(layers)}层·标题七层记忆')
"""]
    },
    "collector_rerun": {
        "desc": "重跑dashboard-collector",
        "cmd": ["/opt/homebrew/bin/python3", os.path.expanduser("~/lgox-ops/scripts/dashboard-collector.py")]
    },
    "health_check": {
        "desc": "联邦健康检查",
        "cmd": ["python3", "-c", """
import urllib.request, json
results = {}
try:
    d = json.loads(urllib.request.urlopen('http://100.116.0.29:8200/health', timeout=5).read())
    results['LGE'] = f"{d['genes']}genes ok"
except: results['LGE'] = 'unreachable'
try:
    d = json.loads(urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2).read())
    results['Bridge'] = f"{d['nodes']['online']}/{d['nodes']['total']}online"
except: results['Bridge'] = 'unreachable'
print(json.dumps(results, ensure_ascii=False))
"""]
    },
    "self_heal": {
        "desc": "基础自愈",
        "cmd": ["/opt/homebrew/bin/python3", os.path.expanduser("~/lgox-ops/scripts/dashboard-collector.py")]
    },
    "l1_trust_root": {
        "desc": "L-1信任根加固·git签名链",
        "cmd": ["python3", "-c", """
import subprocess,os
os.chdir(os.path.expanduser('~/lgox-ops'))
r=subprocess.run(['git','init'],capture_output=True,text=True)
print(f'git init: {r.stdout.strip() or r.stderr.strip()}')
r=subprocess.run(['git','add','-A'],capture_output=True,text=True)
print(f'git add: done')
r=subprocess.run(['git','commit','-m',f'L-1信任根加固 {__import__(\"datetime\").datetime.now().strftime(\"%Y%m%d-%H%M\")}'],capture_output=True,text=True)
print(f'commit: {r.stdout.strip()}')
"""]
    }
}

def log(level, msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    for logpath in [AUDIT_LOG, TASK_LOG]:
        try:
            os.makedirs(os.path.dirname(logpath), exist_ok=True)
            with open(logpath, "a") as f: f.write(line + "\n")
        except: pass
    print(line, flush=True)

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except:
        return {"processed": [], "tasks_executed": 0, "genes_written": 0}

def save_state(s):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f: json.dump(s, f)

def fetch_inbox():
    q = urllib.request.quote(MY_NODE)
    req = urllib.request.Request(BRIDGE + "/messages/inbox?node=" + q)
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read()).get("messages", [])

# ─── GCP v5.0 · 消息发送 ───
def gcp_send(to_node, msg_type, content, priority=None, reply_to=None, ttl=3600):
    """GCP v5.0标准发送·六必填字段"""
    type_info = GCP_TYPES.get(msg_type, {"pri": "P2", "routes": 1})
    pri = priority or type_info["pri"]
    msg_id = str(uuid.uuid4())[:8]
    
    payload = json.dumps({
        "from": MY_NODE,
        "to": to_node,
        "type": msg_type,
        "msg_type": msg_type,        # 天枢TASK_DONE闭环需要此字段
        "priority": pri,
        "msg_id": msg_id,
        "reply_to": reply_to or "",
        "ttl": ttl,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }).encode()
    
    # ACK只发本地桥(桥自动路由)·其他类型按优先级多路
    if msg_type == "ACK":
        targets = [BRIDGE + "/messages/send"]
    elif type_info["routes"] >= 2:
        targets = [BRIDGE + "/messages/send", get_bridge(to_node) + "/messages/send"]
    else:
        targets = [BRIDGE + "/messages/send"]
    
    for url in targets:
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=8)
            log("GCP", f"[{msg_type}] → {to_node} via {url.split('/')[2]}")
        except Exception as e:
            log("WARN", f"GCP发送失败→{url.split('/')[2]}: {e}")
    
    return msg_id

def send_reply(msg_id, to_node, reply_text):
    """GCP v5.0 ACK回复"""
    gcp_send(to_node, "ACK", reply_text, reply_to=msg_id)

def notify_tianshu(title, content):
    """完成后通知天枢·GCP v5.0 TASK_DONE"""
    gcp_send("天枢", "TASK_DONE", f"{title}\n{content}")

# ─── GCP v5.0 · 类型识别 ───
def resolve_type(msg):
    """从消息中解析GCP v5.0类型·优先msg_type字段·兼容旧TYPE字段·智能回填"""
    # L3标准: type > msg_type > TYPE > msgType > 内容精确匹配
    tp = msg.get("type") or msg.get("msg_type") or msg.get("TYPE") or msg.get("msgType") or ""
    if tp in GCP_TYPES:
        return tp
    
    # 兼容旧格式 TYPE:xxx (精确匹配·避免子串误判)
    content = str(msg.get("content", ""))
    topic = str(msg.get("topic", ""))
    
    # 先精确匹配 TYPE:xxx 格式
    type_match = __import__('re').search(r'TYPE[=:]\s*(\w+)', content)
    if type_match:
        exact_tp = type_match.group(1).upper()
        if exact_tp in GCP_TYPES:
            return exact_tp
    
    # 内容关键词匹配 (注意顺序: 具体类型优先·避免TASK_DONE被TASK误吞)
    type_hints = [
        ("ALERT", ["告警", "alert", "紧急", "⚠️", "🔴"]),
        ("ROUNDTABLE", ["圆桌", "roundtable", "discussion", "共识"]),
        ("PATCH", ["补丁", "patch", "修复", "更新"]),
        ("TASK_DONE", ["任务完成", "执行完毕", "TASK_DONE"]),
        ("TASK", ["TYPE:task", "task|", "ACTION:", "指令"]),
        ("ACK", ["ACK:", "ack", "确认", "收到", "回执"]),
        ("HEARTBEAT", ["心跳", "heartbeat", "health", "ping"]),
        ("GENE", ["基因", "gene", "GENE-"]),
        ("STATE", ["状态", "state", "同步"]),
        ("QUERY", ["查询", "query", "问"]),
        ("NOTICE", ["通知", "notice", "通告"]),
    ]
    
    for gcp_type, hints in type_hints:
        for hint in hints:
            if hint.lower() in content.lower() or hint.lower() in topic.lower():
                return gcp_type
    
    # 默认: NOTICE
    return "NOTICE"

def execute_task(action, spec, msg_from):
    if action not in SAFE_COMMANDS:
        return False, f"未知指令:{action}·白名单:{list(SAFE_COMMANDS.keys())}"
    
    task = SAFE_COMMANDS[action]
    log("EXEC", f"[TASK] {action}: {task['desc']} (来自{msg_from})")
    
    try:
        r = subprocess.run(task["cmd"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            output = r.stdout.strip()[:300]
            log("OK", f"{action} 完成: {output}")
            return True, output
        else:
            err = r.stderr.strip()[:200]
            log("FAIL", f"{action} 失败: {err}")
            return False, err
    except subprocess.TimeoutExpired:
        log("TIMEOUT", f"{action} 超时")
        return False, "执行超时30s"
    except Exception as e:
        log("ERROR", f"{action} 异常: {e}")
        return False, str(e)

def write_gene(content):
    try:
        data = json.dumps({"content": content, "memory_type": "episodic",
                           "source": "linglong-executor", "priority": 0.85}).encode()
        req = urllib.request.Request("http://100.116.0.29:8200/genes/write", data=data,
                                      headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=8)
        return json.loads(resp.read()).get("gene_id", "?")
    except Exception as e:
        log("WARN", f"纳基因失败: {e}")
        return None

def main():
    state = load_state()
    processed = set(state.get("processed", []))
    
    try:
        msgs = fetch_inbox()
    except Exception as e:
        log("WARN", f"收件箱拉取失败: {e}")
        return
    
    task_count = 0
    stats = {t: 0 for t in GCP_TYPES}
    
    for m in msgs:
        mid = str(m.get("id", m.get("message_id", "")))
        if mid in processed: continue
        
        frm = m.get("from", "?")
        tp = resolve_type(m)  # GCP v5.0 智能类型识别
        content = m.get("content", "")
        pri = m.get("priority", GCP_TYPES.get(tp, {}).get("pri", "P2"))
        
        stats[tp] = stats.get(tp, 0) + 1
        log("RECV", f"[{tp}/{pri}] {frm}: {str(content)[:120]}")
        
        # ─── GCP v5.0 · 类型分发 ───
        if tp == "ROUNDTABLE":
            log("ROUNDTABLE", f"圆桌会议 [{frm}]: {str(content)[:150]}")
            processed.add(mid)
            continue
        
        if tp in ("HEARTBEAT", "QUERY", "NOTICE", "STATE"):
            processed.add(mid)
            continue
        
        if tp == "ALERT":
            log("ALERT", f"⚠️ [{frm}]: {str(content)[:200]}")
            processed.add(mid)
            continue
        
        if tp == "GENE":
            log("GENE", f"基因入库 [{frm}]: {str(content)[:100]}")
            processed.add(mid)
            continue
        
        if tp == "TASK_DONE":
            log("TASK_DONE", f"任务完成 [{frm}]: {str(content)[:150]}")
            processed.add(mid)
            continue
        
        # TASK + PATCH → 解析并执行
        if tp == "TASK" or tp == "PATCH":
            task_info = {"action": "unknown", "desc": "", "spec": ""}
            raw = str(content)
            for part in raw.split("|"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    task_info[k.strip().lower()] = v.strip()
            
            action = task_info.get("action", "unknown")
            log("TASK", f"[{tp}] {frm} → {action}: {task_info.get('desc','')[:80]}")
            
            ok, result = execute_task(action, task_info.get("spec", ""), frm)
            
            # GCP v5.0 ACK回复
            reply = f"ACK:{action}|RESULT:{'OK' if ok else 'FAIL'}|DETAIL:{result[:150]}"
            try: send_reply(mid, frm, reply)
            except: log("WARN", f"ACK回复失败→{frm}")
            
            if ok:
                gene_id = write_gene(
                    f"[GCP v5.0] {MY_NODE}·{action}·{task_info.get('desc','')} "
                    f"结果:{'OK' if ok else 'FAIL'}·详情:{result[:200]}")
                if gene_id:
                    state["genes_written"] = state.get("genes_written", 0) + 1
            
            state["tasks_executed"] = state.get("tasks_executed", 0) + 1
            task_count += 1
            processed.add(mid)
        
        # ACK → 收悉即可
        if tp == "ACK":
            log("ACK", f"确认回执 [{frm}]: reply_to={m.get('reply_to','?')}")
            processed.add(mid)
            continue
    
    if task_count > 0:
        state["processed"] = list(processed)[-1000:]
        state["last_run"] = datetime.now().isoformat()
        save_state(state)
        
        # 类型分布统计
        type_summary = " ".join(f"{k}:{v}" for k, v in sorted(stats.items()) if v > 0)
        log("DONE", f"本轮:{task_count}任务·累计:{state['tasks_executed']}·基因:{state['genes_written']} | {type_summary}")
        
        # GCP v5.0 TASK_DONE → 天枢
        notify_tianshu(f"灵龙consumer·GCP v5.0·{task_count}任务",
            f"累计{state['tasks_executed']}·基因{state['genes_written']} | {type_summary}")
    
    return task_count

if __name__ == "__main__":
    main()
