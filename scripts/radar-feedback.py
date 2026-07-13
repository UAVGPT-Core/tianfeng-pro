#!/usr/bin/env python3
"""
雷达反馈闭环 v1.0 · 天巡+小枢引用追踪
追踪:对话中引用了哪条雷达基因 → 加分 → 同类雷达优先
"""
import sqlite3, json, os
from collections import Counter
from datetime import datetime

FED_DB = os.path.expanduser("~/.hermes/fed_messages.db")
TRACK_DB = os.path.expanduser("~/lgox-ops/data/radar-feedback.db")
LGE = "http://100.116.0.29:8200"

def setup():
    db = sqlite3.connect(TRACK_DB)
    db.execute("""CREATE TABLE IF NOT EXISTS feedback (
        gene_id TEXT, radar_topic TEXT, source TEXT, 
        used_by TEXT, conversation TEXT, score INT DEFAULT 1,
        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    db.commit()
    return db

def scan_conversations(db, hours=24):
    """扫描天巡+小枢最近对话·匹配雷达关键词"""
    fed = sqlite3.connect(FED_DB)
    
    # 关键词库(从雷达基因常见topic)
    radar_topics = {
        "大疆": "无人机·竞对",
        "极飞": "无人机·竞对", 
        "商汤": "AI·竞对",
        "华为": "AI·竞对",
        "字节": "AI·竞对",
        "阿里": "AI·竞对",
        "腾讯": "AI·竞对",
        "Transformer": "大模型·基础",
        "LoRA": "微调·技术",
        "RAG": "检索·应用",
        "Agent": "智能体·趋势",
        "vLLM": "推理·工程",
        "ReAct": "Agent·范式",
        "多模态": "视觉·趋势",
        "无人机": "低空·核心",
        "巡检": "低空·应用",
        "机巢": "低空·产品",
        "基因": "LGOX·内核",
        "联邦": "LGOX·架构",
        "金字塔": "LGOX·架构",
        "七自": "LGOX·宪法",
    }
    
    # 找天巡消息
    tx_msgs = fed.execute(
        "SELECT content, ts FROM messages WHERE from_node LIKE '%天巡%' AND ts>datetime('now',? ) ORDER BY ts DESC LIMIT 100",
        (f"-{hours} hours",)
    ).fetchall()
    
    # 找小枢消息  
    xs_msgs = fed.execute(
        "SELECT content, ts FROM messages WHERE from_node LIKE '%小枢%' AND ts>datetime('now',? ) ORDER BY ts DESC LIMIT 100",
        (f"-{hours} hours",)
    ).fetchall()
    
    hits = []
    for topic, category in radar_topics.items():
        tx_hits = sum(1 for m in tx_msgs if topic in str(m[0]))
        xs_hits = sum(1 for m in xs_msgs if topic in str(m[0]))
        total = tx_hits + xs_hits
        if total > 0:
            db.execute("INSERT INTO feedback (radar_topic, source, used_by, score, conversation) VALUES (?,?,?,?,?)",
                (topic, category, f"天巡{tx_hits}/小枢{xs_hits}", total, f"{tx_hits+xs_hits}次引用"))
            hits.append((topic, total, category))
    
    db.commit()
    fed.close()
    return hits

def boost_radar_priority(hits):
    """高频引用话题→同类雷达提升优先级"""
    if not hits: return
    hits.sort(key=lambda x: x[1], reverse=True)
    top3 = hits[:3]
    
    print("🔥 高频引用雷达(同类优先):")
    for topic, count, category in top3:
        print(f"  {topic}: {count}次 → {category}类雷达优先级+{count}")
        try:
            import urllib.request
            data = {"content": f"[反馈闭环] {topic}被天巡/小枢引用{count}次→{category}类雷达提升", 
                    "memory_type": "semantic", "source": "雷达反馈闭环", "fitness": min(0.9, 0.5+count*0.1),
                    "tags": [topic, "反馈闭环", category]}
            urllib.request.urlopen(urllib.request.Request(f"{LGE}/genes/write",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"}, method="POST"), timeout=3)
        except: pass

def get_dashboard_stats(db):
    """仪表盘用统计"""
    total = db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    recent = db.execute("SELECT COUNT(*) FROM feedback WHERE ts>datetime('now','-24 hours')").fetchone()[0]
    top = db.execute("SELECT radar_topic,SUM(score) as s FROM feedback WHERE ts>datetime('now','-7 days') GROUP BY radar_topic ORDER BY s DESC LIMIT 5").fetchall()
    return total, recent, top

# ═══ 主流程 ═══
print(f"[{datetime.now().strftime('%H:%M')}] 🔄 雷达反馈闭环 v1.0")
db = setup()
hits = scan_conversations(db, hours=24)
boost_radar_priority(hits)

total, recent, top5 = get_dashboard_stats(db)
print(f"\n📊 累计: {total}条引用·近24h:{recent}条")
if top5:
    print("🏆 7天TOP5:")
    for t in top5:
        print(f"  {t[0]}: {t[1]}次")
print("✅ 反馈闭环: 引用→加分→同类优先")
