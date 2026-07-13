#!/usr/bin/env python3
"""
六六记忆飞轮 v3.0 — GCP v5.0对齐·2035级
决策→踩坑→基因·全自动·零人类
对接GCP v5.0: 十一制类型·六必填字段·优先级路由
"""

import json, sqlite3, os, urllib.request, uuid
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/Users/a112233"))
DB_PATH = HOME / "lgox-ops/data/memory/audit.db"
LGE_URL = "http://100.116.0.29:8200"
BRIDGE = "http://127.0.0.1:8765"
MY_NODE = "灵龙"

# ─── GCP v5.0 消息发送 ───
def gcp_send(to_node, msg_type, content, priority="P2"):
    msg = json.dumps({
        "from": MY_NODE, "to": to_node,
        "type": msg_type, "priority": priority,
        "msg_id": str(uuid.uuid4())[:8],
        "reply_to": "", "ttl": 3600,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }).encode()
    try:
        req = urllib.request.Request(BRIDGE + "/messages/send", data=msg,
                                      headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        return True
    except:
        return False

def safe_curl(url, timeout=3, method="GET", data=None):
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except:
        return {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 使用已有表结构·不重建
    c.executescript("""
        CREATE TABLE IF NOT EXISTS gcp_align (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node TEXT, msg_type TEXT, field TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    return conn

def scan_and_inject():
    """扫描联邦状态·提取决策+踩坑·注入飞轮"""
    conn = init_db()
    c = conn.cursor()
    start = datetime.now()
    run_id = f"fly-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    decisions_found = 0
    lessons_found = 0
    genes_written = 0
    errors = []
    
    # 1. 扫描灵龙consumer日志提取踩坑
    log_paths = [
        HOME / "lgox-ops/logs/linglong-exec-audit.log",
        HOME / "lgox-ops/logs/linglong-task-exec.log",
    ]
    for logp in log_paths:
        if not logp.exists():
            continue
        with open(logp) as f:
            lines = f.readlines()[-200:]
        
        for line in lines:
            if "FAIL" in line or "WARN" in line or "ERROR" in line:
                title = line.strip()[:120]
                c.execute("SELECT COUNT(*) FROM lessons WHERE lesson=?", (title,))
                if c.fetchone()[0] == 0:
                    sev = "critical" if "FAIL" in line or "ERROR" in line else "high"
                    c.execute(
                        "INSERT INTO lessons (run_id,category,title,lesson,severity,immune_since) VALUES (?,?,?,?,?,?)",
                        (run_id, "auto-scan", title[:80], title, sev, datetime.now().isoformat()))
                    lessons_found += 1
    
    # 2. 从L6巩固提取决策
    l6_db = HOME / "lgox-ops/data/memory/l6_sessions.db"
    if l6_db.exists():
        try:
            l6conn = sqlite3.connect(l6_db)
            l6c = l6conn.cursor()
            l6c.execute("SELECT content,category FROM insights ORDER BY id DESC LIMIT 20")
            for content, cat in l6c.fetchall():
                c.execute("SELECT COUNT(*) FROM decisions WHERE decision=?", (content[:200],))
                if c.fetchone()[0] == 0:
                    c.execute(
                        "INSERT INTO decisions (run_id,category,decision,rationale,impact) VALUES (?,?,?,?,?)",
                        (run_id, cat or "auto", content[:300], "L6自动提取", "medium"))
                    decisions_found += 1
            l6conn.close()
        except Exception as e:
            errors.append(f"L6提取失败:{e}")
    
    # 3. 记录飞轮基因
    if decisions_found > 0 or lessons_found > 0:
        for cat, count in [("decision", decisions_found), ("lesson", lessons_found)]:
            if count > 0:
                gid = f"GENE-FLY-{datetime.now().strftime('%Y%m%d-%H%M')}-{cat}"
                c.execute("INSERT INTO flywheel_genes (run_id,gene_id,content,source,fitness) VALUES (?,?,?,?,?)",
                          (run_id, gid, f"六六飞轮v3·{cat}·{count}条", "memory-flywheel-v3", 0.7))
                genes_written += 1
    
    # 4. 记录运行
    duration = int((datetime.now() - start).total_seconds() * 1000)
    score = min(100, 70 + decisions_found * 2 + lessons_found * 3)
    
    c.execute(
        "INSERT INTO flywheel_runs (run_id,layer_scores,total_duration_ms,genes_extracted,errors,decisions_made,lessons_learned,score) VALUES (?,?,?,?,?,?,?,?)",
        (run_id, json.dumps({"L5": score, "L6": min(100, score + 5)}),
         duration, genes_written, json.dumps(errors), decisions_found, lessons_found, score))
    
    conn.commit()
    
    # 统计
    c.execute("SELECT COUNT(*) FROM flywheel_runs")
    total_runs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM decisions")
    total_dec = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM lessons")
    total_les = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM flywheel_genes")
    total_gen = c.fetchone()[0]
    
    conn.close()
    
    result = {
        "run_id": run_id, "score": score,
        "decisions": total_dec, "lessons": total_les, "genes": total_gen,
        "runs": total_runs, "duration_ms": duration,
        "this_round": f"{decisions_found}决策·{lessons_found}踩坑·{genes_written}基因"
    }
    
    print(json.dumps(result, ensure_ascii=False))
    
    # GCP v5.0: 通知天枢
    gcp_send("天枢", "HEARTBEAT",
             f"六六飞轮v3·评分{score}/100·{total_runs}轮·{total_dec}决策·{total_les}踩坑·{total_gen}基因")
    
    return result

if __name__ == "__main__":
    scan_and_inject()
