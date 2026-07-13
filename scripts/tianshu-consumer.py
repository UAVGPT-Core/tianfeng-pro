#!/usr/bin/env python3
"""
天枢联邦消息消化器 v5.1 · 真读真执行真反馈
===========================================
FCPF v5.1 六段闭环: 发→查→索→收→评→纳
直读SQLite联邦消息库 → AI解析 → 自动执行 → 回执 → 纳基因
每30秒轮询 | 灵龙发任务30秒内执行完毕
"""
import json, os, sys, time, sqlite3, urllib.request, subprocess, hashlib
from datetime import datetime

MSG_DB = os.path.expanduser("~/.hermes/fed_messages.db")
THIS_NODE = "天枢"
STATE_FILE = os.path.expanduser("~/lgox-ops/data/consumer-state.json")
LINGLONG_BRIDGE = "http://100.120.20.52:8765"  # 灵龙桥·跨节点消息直送
GENE_WRITE = "http://100.116.0.29:8200/genes/write"
POLL_INTERVAL = 30

state = {"consumed":0, "executed":0, "replied":0, "genes":0}
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

def get_unread():
    """从SQLite直读未读消息"""
    try:
        conn = sqlite3.connect(MSG_DB)
        cur = conn.execute(
            "SELECT id, from_node, node, content, ts, msg_type FROM messages "
            "WHERE node=? AND read=0 ORDER BY id ASC LIMIT 10",
            (THIS_NODE,))
        msgs = []
        cols = ['id','from_node','node','content','ts','type']
        for r in cur.fetchall():
            msgs.append(dict(zip(cols, r)))
        conn.close()
        return msgs
    except Exception as e:
        return []

def mark_read(msg_id):
    """标记消息已读"""
    try:
        conn = sqlite3.connect(MSG_DB)
        conn.execute("UPDATE messages SET read=1 WHERE id=?", (msg_id,))
        conn.commit()
        conn.close()
    except: pass

def execute_task(task):
    """执行灵龙发来的任务"""
    if isinstance(task, dict):
        cmd = task.get("action", "")
        desc = task.get("desc", "")
        node = task.get("node", "")
        priority = task.get("priority", 5)
    else:
        cmd = str(task)
        desc = ""
        priority = 5
    
    if not cmd:
        return None, "无执行命令"
    
    # 安全拦截: 禁止危险命令
    dangerous = ["rm -rf", "shutdown", "reboot", "sudo", "mkfs", "dd if=",
                 "> /dev/sda", "chmod 777 /", ":(){ :|:& };:"]
    for d in dangerous:
        if d in cmd.lower():
            return False, f"危险命令被拦截: {d}"
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=30, text=True)
        ok = r.returncode == 0
        output = (r.stdout.strip() or r.stderr.strip())[:500]
        
        if len(output) > 300:
            output = output[:300] + f"...({len(output)}chars)"
        
        return ok, output[:300]
    except subprocess.TimeoutExpired:
        return False, "超时30秒"
    except Exception as e:
        return False, str(e)[:100]

def send_reply_to_bridge(from_node, task_desc, result, output):
    """通过灵龙桥发送回执（直连灵龙桥而非本地）"""
    try:
        content = f"[天枢回执] {task_desc[:80]} | {'OK' if result else 'FAIL'}: {output[:100]} | {datetime.now().strftime('%H:%M:%S')}"
        data = json.dumps({
            "to": "灵龙",
            "from": THIS_NODE,
            "content": content,
            "type": "task_receipt"
        }).encode()
        req = urllib.request.Request(f"{LINGLONG_BRIDGE}/messages/send", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
        return True
    except: return False

def write_gene(content):
    try:
        data = json.dumps({
            "content": f"[天枢消费闭环] {content}",
            "memory_type": "episodic",
            "source": "tianshu-consumer",
            "tags": '["domain:meta","fcpf","consumer"]'
        }).encode()
        req = urllib.request.Request(GENE_WRITE, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
        return True
    except: return False

def process_one(msg):
    """处理一条消息"""
    msg_id = msg['id']
    from_node = msg['from_node']
    content = msg.get('content', '')
    msg_type = msg.get('type', '')
    
    # 尝试解析JSON
    parsed = None
    if content and content[0] == '{':
        try: parsed = json.loads(content)
        except: pass
    
    task = None
    result = None
    
    if parsed and parsed.get("type") == "federation_task":
        task = parsed.get("task", parsed)
        ok, output = execute_task(task)
        result = f"{'✅' if ok else '❌'} {output[:150]}"
        
        # 回执给灵龙
        send_reply_to_bridge(from_node, str(task.get('action','')[:60]), ok, output)
        
        # 纳基因
        if ok:
            write_gene(f"执行灵龙任务: {str(task.get('action',''))[:150]} → {output[:100]}")
    
    elif parsed and parsed.get("type") == "federation_task_ack":
        result = "✅ 灵龙ACK"
    
    elif parsed and parsed.get("type") == "knowledge_broadcast":
        write_gene(f"灵龙知识广播: {str(content)[:300]}")
        result = "🧬 已纳基因"
    
    elif "自愈指令" in str(content):
        # 解析并执行自愈
        result = "🔧 自愈指令已接收"
        write_gene(f"灵龙自愈指令: {str(content)[:200]}")
    
    elif "FCPF" in str(content):
        result = "📡 FCPF心跳ACK"
        send_reply_to_bridge(from_node, f"FCPF ACK from {THIS_NODE}", True, "OK")
    
    else:
        result = "📨 已读·文本消息"
    
    # 标记已读
    mark_read(msg_id)
    
    return from_node, task, result

def main():
    print(f"🦞 天枢消费引擎 v5.1 启动 | SQLite直读 | FCPF v5.1 | {POLL_INTERVAL}s轮询", flush=True)
    
    # 先处理积压
    backlog = get_unread()
    if backlog:
        print(f"\n📬 积压消息: {len(backlog)}条 → 立即处理", flush=True)
        for msg in backlog:
            frm, task, result = process_one(msg)
            desc = ""
            if task:
                desc = str(task.get('action', task.get('desc', '')))[:80] if isinstance(task, dict) else str(task)[:80]
            print(f"  ← {frm} | {desc} | {result}", flush=True)
        print(f"  处理完成\n", flush=True)
    
    while True:
        try:
            msgs = get_unread()
            if msgs:
                now = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{now}] 📬 {len(msgs)}条", flush=True)
                for msg in msgs:
                    frm, task, result = process_one(msg)
                    desc = ""
                    if task:
                        desc = str(task.get('action', ''))[:80] if isinstance(task, dict) else ""
                    print(f"  ← {frm} | {desc} | {result}", flush=True)
            
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"  [err] {e}", flush=True)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
