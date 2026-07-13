#!/usr/bin/env python3
"""
本地基因热缓存 v1.0 · 灵龙
从地枢LGE同步TOP5000高频基因到本地SQLite
每60分钟刷新 · 天巡/小枢启动时预加载
基因ID: GENE-PRO-hotcache-v1
"""
import sqlite3, json, urllib.request, time, os
from datetime import datetime

DB = os.path.expanduser("~/lgox-ops/data/gene-hotcache.db")
LGE_BASE = "http://100.116.0.29:8200"
SYNC_INTERVAL = 3600  # 60分钟

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hot_genes (
            gene_id TEXT PRIMARY KEY,
            content TEXT,
            gene_type TEXT,
            fitness REAL,
            domain TEXT,
            hit_count INTEGER DEFAULT 0,
            last_used TEXT,
            created_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fitness ON hot_genes(fitness DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON hot_genes(gene_type)")
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS hot_genes_fts USING fts5(gene_id, content)")
    conn.commit()
    return conn

def sync_from_lge(conn, limit=5000):
    """从地枢LGE拉取高频基因·多域采样"""
    try:
        queries = ["联邦 节点 通讯", "金字塔 七自 基因", "Python async 修复",
                   "SSH Tailscale 部署", "Widget V3 天巡", "金融 行情 信号",
                   "无人机 巡检 机巢", "DeepSeek Ollama 模型", "nginx CORS 跨域",
                   "踩坑 修复 基因", "LGOX 联邦 标准", "AI Box 入网"]
        seen = set()
        all_genes = []
        
        for q in queries:
            payload = json.dumps({"query": q, "n_results": 50}).encode()
            req = urllib.request.Request(f"{LGE_BASE}/genes/search",
                data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            for g in data.get("results", []):
                gid = g.get("gene_id", "")
                if gid not in seen:
                    seen.add(gid)
                    all_genes.append(g)
        
        if not all_genes:
            print(f"[{datetime.now():%H:%M}] ⚠️ 多域查询返回空·保留现有缓存")
            return 0

        conn.execute("DELETE FROM hot_genes")
        conn.execute("DELETE FROM hot_genes_fts")
        
        for g in all_genes[:limit]:
            gid = g.get("gene_id", "")
            content = g.get("content", "")[:500]
            gtype = g.get("type", "unknown")
            fitness = g.get("fitness", g.get("fitness_score", 0))
            domain = g.get("domain", "general")
            conn.execute("INSERT OR REPLACE INTO hot_genes VALUES (?,?,?,?,?,0,'','')",
                (gid, content, gtype, fitness, domain))
            conn.execute("INSERT INTO hot_genes_fts VALUES (?,?)", (gid, content))

        conn.commit()
        print(f"[{datetime.now():%H:%M}] ✅ 热缓存刷新: {len(all_genes[:limit])}条({len(queries)}域采样)")
        return len(all_genes[:limit])
    except Exception as e:
        print(f"[{datetime.now():%H:%M}] ❌ 同步失败: {e}")
        return 0

def search_local(query, conn, limit=5):
    """本地搜索热基因"""
    try:
        rows = conn.execute(
            "SELECT gene_id, content, fitness FROM hot_genes_fts WHERE hot_genes_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit)
        ).fetchall()
        if rows:
            return [{"gene_id": r[0], "content": r[1][:120], "fitness": r[2]} for r in rows]
        # FTS无结果→fallback按fitness
        rows = conn.execute(
            "SELECT gene_id, content, fitness FROM hot_genes WHERE content LIKE ? ORDER BY fitness DESC LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [{"gene_id": r[0], "content": r[1][:120], "fitness": r[2]} for r in rows]
    except:
        return []

def get_stats(conn):
    count = conn.execute("SELECT COUNT(*) FROM hot_genes").fetchone()[0]
    avg_f = conn.execute("SELECT AVG(fitness) FROM hot_genes").fetchone()[0] or 0
    return {"count": count, "avg_fitness": round(avg_f, 3)}

if __name__ == "__main__":
    conn = init_db()
    stats_before = get_stats(conn)
    print(f"[{datetime.now():%H:%M}] 热缓存同步前: {stats_before['count']}条·fitness均值{stats_before['avg_fitness']}")
    synced = sync_from_lge(conn, limit=5000)
    stats_after = get_stats(conn)
    print(f"[{datetime.now():%H:%M}] 热缓存同步后: {stats_after['count']}条·fitness均值{stats_after['avg_fitness']}")
    conn.close()
