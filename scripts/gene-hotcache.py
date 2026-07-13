#!/usr/bin/env python3
"""
本地基因热缓存 v1.0 · 灵龙
从地枢LGE同步TOP5000高频基因到本地SQLite
每60分钟刷新 · 天巡/小枢启动时预加载
基因ID: GENE-PRO-hotcache-v1
"""
import sqlite3, os
from datetime import datetime

DB = os.path.expanduser("~/lgox-ops/data/gene-hotcache.db")
MIRROR_DB = os.path.expanduser("~/.hermes/lge-mirror/lge_mirror.db")
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
    """从灵龙本地LGE灾备镜像同步高频基因到热缓存
    
    降级策略: 地枢spark-5438离线时自动使用本地SQLite镜像(649K基因)
    字段映射: memory_type→gene_type, fitness_score→fitness, source→domain
    """
    try:
        mirror = sqlite3.connect(MIRROR_DB)
        mirror.row_factory = sqlite3.Row
        
        # 多维度采样: 按fitness取TOP + 按类型分散采样
        all_genes = []
        seen = set()
        
        # 1) TOP N by fitness_score (高频基因优先)
        rows = mirror.execute(
            "SELECT * FROM genes WHERE status='active' AND fitness_score > 0 "
            "ORDER BY fitness_score DESC LIMIT ?", (limit,)
        ).fetchall()
        for r in rows:
            gid = r["gene_id"]
            if gid and gid not in seen:
                seen.add(gid)
                all_genes.append(dict(r))
        
        # 2) 按类型补充采样(semantic/episodic/procedural各取一些)
        for mtype in ("semantic", "episodic", "procedural"):
            if len(all_genes) >= limit:
                break
            rows = mirror.execute(
                "SELECT * FROM genes WHERE status='active' AND memory_type=? "
                "ORDER BY fitness_score DESC LIMIT ?",
                (mtype, max((limit - len(all_genes)) // 3, 500))
            ).fetchall()
            for r in rows:
                gid = r["gene_id"]
                if gid and gid not in seen:
                    seen.add(gid)
                    all_genes.append(dict(r))
        
        mirror.close()
        
        if not all_genes:
            print(f"[{datetime.now():%H:%M}] ⚠️ 镜像查询返回空·保留现有缓存")
            return 0

        conn.execute("DELETE FROM hot_genes")
        conn.execute("DELETE FROM hot_genes_fts")
        
        for g in all_genes[:limit]:
            gid = g.get("gene_id", "")
            content = str(g.get("content", ""))[:500]  # 可能是JSON
            gtype = g.get("memory_type", "unknown")
            fitness = g.get("fitness_score", 0)
            domain = g.get("source", "general")
            conn.execute("INSERT OR REPLACE INTO hot_genes VALUES (?,?,?,?,?,0,'','')",
                (gid, content, gtype, fitness, domain))
            conn.execute("INSERT INTO hot_genes_fts VALUES (?,?)", (gid, content))

        conn.commit()
        print(f"[{datetime.now():%H:%M}] ✅ 热缓存刷新: {len(all_genes[:limit])}条 "
              f"(fitness>0:{len([g for g in all_genes[:limit] if g.get('fitness_score',0)>0])})")
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
