#!/usr/bin/env python3
"""
L6 会话巩固引擎 v1.0 — 24h睡眠巩固·关键知识提取→LGE
目标: 75%→85%→90%+
每次从对话session提炼关键知识→写入LGE基因库→六六记忆飞轮闭环
"""

import json, sqlite3, os, re, urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ──
DB_PATH = Path(os.environ.get("HOME", "/Users/a112233")) / "lgox-ops/data/memory/l6_sessions.db"
LGE_URL = "http://100.116.0.29:8200/genes/write"
BRIDGE_URL = "http://localhost:8765/federated-store"
MY_NODE = "灵龙"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,           -- hermes / bridge / cron / manual
            topic TEXT,
            summary TEXT,
            key_insights TEXT,     -- JSON array of insights
            gene_ids TEXT,         -- JSON array of gene IDs written
            tokens_approx INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            consolidated_at TIMESTAMP,
            score INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            content TEXT,
            category TEXT,         -- decision / lesson / pattern / fact
            confidence REAL DEFAULT 0.5,
            gene_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS consolidation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sessions_scanned INTEGER,
            insights_found INTEGER,
            genes_written INTEGER,
            duration_ms INTEGER
        );
    """)
    conn.commit()
    return conn

def extract_insights(session_text, topic=""):
    """从session文本中提取关键洞察 - 规则引擎+关键词匹配"""
    insights = []
    
    # 决策提取
    decision_patterns = [
        r'(?:决定|裁决|铁律|宪法|原则)[：:]\s*(.+?)(?:[。\n]|$)',
        r'(?:不再|永不|禁止|必须|强制)\s*(.+?)(?:[。\n]|$)',
        r'(?:✔|✅|🎯|裁决)[：:]\s*(.+?)(?:[。\n]|$)',
    ]
    for pat in decision_patterns:
        for m in re.finditer(pat, session_text):
            insights.append({"content": m.group(1).strip()[:200], "category": "decision", "confidence": 0.7})
    
    # 踩坑/教训提取
    lesson_patterns = [
        r'(?:踩坑|血训|教训|根因|病因)[：:]\s*(.+?)(?:[。\n]|$)',
        r'(?:❌|⚠️|🔴|坑)[：:]\s*(.+?)(?:[。\n]|$)',
        r'根因[：:]\s*(.+?)(?:[。\n]|$)',
    ]
    for pat in lesson_patterns:
        for m in re.finditer(pat, session_text):
            insights.append({"content": m.group(1).strip()[:200], "category": "lesson", "confidence": 0.7})
    
    # 模式/架构提取
    pattern_markers = [
        r'(?:架构|设计|模式|标准|协议)[：:]\s*(.+?)(?:[。\n]|$)',
        r'(?:v\d+\.\d+|版本)\s+(.+?)(?:[。\n]|$)',
    ]
    for pat in pattern_markers:
        for m in re.finditer(pat, session_text):
            insights.append({"content": m.group(1).strip()[:200], "category": "pattern", "confidence": 0.5})
    
    # 去重
    seen = set()
    unique = []
    for i in insights:
        if i["content"][:50] not in seen:
            seen.add(i["content"][:50])
            unique.append(i)
    
    return unique

def write_to_lge(content, category):
    """写入LGE基因库"""
    try:
        data = json.dumps({
            "content": f"[L6·{category}] {content}",
            "memory_type": "semantic",
            "source": "l6-consolidator"
        }).encode()
        req = urllib.request.Request(LGE_URL, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=3)  # 3s超时·不阻塞
        r = json.loads(resp.read())
        return r.get("gene_id", r.get("id", ""))
    except Exception as e:
        print(f"  ⚠️ LGE写入失败: {e}")
        return ""

def consolidate():
    """主函数·24h睡眠巩固"""
    conn = init_db()
    c = conn.cursor()
    
    start = datetime.now()
    
    # 扫描未巩固的session（48小时内）
    cutoff = datetime.now() - timedelta(hours=48)
    c.execute("SELECT id, source, topic, summary, key_insights FROM sessions WHERE consolidated_at IS NULL AND created_at > ?",
              (cutoff.isoformat(),))
    rows = c.fetchall()
    
    print(f"L6巩固: 扫描{len(rows)}个未巩固session")
    
    total_insights = 0
    total_genes = 0
    
    for sid, source, topic, summary, raw_insights in rows:
        text = (topic or "") + " " + (summary or "")
        
        # 优先用已有key_insights
        insights = []
        if raw_insights:
            try:
                raw_list = json.loads(raw_insights)
                for item in raw_list:
                    cat = "lesson" if any(k in item for k in ["坑","教训","根因","血训"]) else "decision" if any(k in item for k in ["铁律","宪法","裁决","原则","标准"]) else "pattern"
                    insights.append({"content": item, "category": cat, "confidence": 0.8})
            except:
                pass
        
        # 补充规则提取
        if len(insights) < 3:
            extra = extract_insights(text, topic)
            for e in extra:
                if e["content"][:50] not in {i["content"][:50] for i in insights}:
                    insights.append(e)
        
        if len(text.strip()) < 20 and not insights:
            continue
        
        gene_ids = []
        for ins in insights:
            # 写DB
            c.execute("INSERT INTO insights (session_id, content, category, confidence) VALUES (?,?,?,?)",
                      (sid, ins["content"], ins["category"], ins["confidence"]))
            iid = c.lastrowid
            
            # 写LGE
            gid = write_to_lge(ins["content"], ins["category"])
            if gid:
                c.execute("UPDATE insights SET gene_id=? WHERE id=?", (gid, iid))
                gene_ids.append(gid)
                total_genes += 1
            
            total_insights += 1
        
        # 标记已巩固
        c.execute("UPDATE sessions SET consolidated_at=?, gene_ids=?, score=? WHERE id=?",
                  (datetime.now().isoformat(), json.dumps(gene_ids), len(insights) * 10, sid))
    
    conn.commit()
    
    duration = int((datetime.now() - start).total_seconds() * 1000)
    
    # 记录日志
    c.execute("INSERT INTO consolidation_log (sessions_scanned, insights_found, genes_written, duration_ms) VALUES (?,?,?,?)",
              (len(rows), total_insights, total_genes, duration))
    conn.commit()
    
    # 统计
    c.execute("SELECT COUNT(*) FROM sessions WHERE consolidated_at IS NOT NULL")
    consolidated = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM insights")
    total_ins = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM insights WHERE gene_id IS NOT NULL")
    genes_linked = c.fetchone()[0]
    
    conn.close()
    
    print(f"  sessions已巩固:{consolidated} 洞察:{total_ins} 基因:{genes_linked}")
    print(f"  ⚡ 本轮:{total_insights}洞察·{total_genes}基因·{duration}ms")
    
    return {
        "sessions_scanned": len(rows),
        "insights_found": total_insights,
        "genes_written": total_genes,
        "duration_ms": duration,
        "total_consolidated": consolidated,
        "total_insights": total_ins,
        "genes_linked": genes_linked
    }

if __name__ == "__main__":
    result = consolidate()
    # 写入联邦桥
    try:
        data = json.dumps({
            "session_id": f"l6-{datetime.now().strftime('%Y%m%d-%H%M')}",
            "role": "system",
            "content": f"L6·24h睡眠巩固·{result['sessions_scanned']}session·{result['insights_found']}洞察·{result['genes_written']}基因"
        }).encode()
        req = urllib.request.Request(BRIDGE_URL, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except:
        pass
    
    print(json.dumps(result))
