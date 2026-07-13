#!/usr/bin/env python3
"""
灵龙LGA v1.0 · 本地基因代理 · 端口8202
2035架构: 三级降级第一级·本地基因+双写+联邦查询
查询: LGA(0ms) → 天枢8201 → 地枢8200
写入: 本地+地枢双写
GENE-PRO-lga-v1
"""
import json, os, sqlite3, urllib.request, asyncio, time, hashlib
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="灵龙LGA·本地基因代理", version="v1.0")

DB = os.path.expanduser("~/lgox-ops/data/lga.db")
LGE_MASTER = "http://100.116.0.29:8200"
TIANSHU_LGE = "http://100.100.89.2:8201"  # 天枢LGE Studio v2.0·829基因
PORT = 8202

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS genes (
        gene_id TEXT PRIMARY KEY, content TEXT, gene_type TEXT,
        fitness REAL, domain TEXT, source TEXT, created_at TEXT,
        synced INTEGER DEFAULT 0
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fitness ON genes(fitness DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_synced ON genes(synced)")
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS genes_fts USING fts5(gene_id, content)")
    conn.commit()
    return conn

# ═══ 本地操作 ═══
def local_search(conn, query, limit=5):
    try:
        rows = conn.execute(
            "SELECT g.gene_id, g.content, g.fitness FROM genes_fts fts JOIN genes g ON fts.gene_id = g.gene_id WHERE genes_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit)).fetchall()
        if rows:
            return [{"gene_id": r[0], "content": r[1][:150], "fitness": r[2], "source": "灵龙LGA"} for r in rows]
    except Exception as e:
        pass
    # LIKE fallback
    rows = conn.execute(
        "SELECT gene_id, content, fitness FROM genes WHERE content LIKE ? ORDER BY fitness DESC LIMIT ?",
        (f"%{query}%", limit)).fetchall()
    return [{"gene_id": r[0], "content": r[1][:150], "fitness": r[2], "source": "灵龙LGA"} for r in rows]

def local_write(conn, gene_id, content, gene_type="semantic", fitness=0.6):
    conn.execute("INSERT OR REPLACE INTO genes VALUES (?,?,?,?,?,?,?,1)",
        (gene_id, content[:500], gene_type, fitness, "general", "灵龙本地", time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.execute("INSERT INTO genes_fts VALUES (?,?)", (gene_id, content[:500]))
    conn.commit()

def local_stats(conn):
    count = conn.execute("SELECT COUNT(*) FROM genes").fetchone()[0]
    synced = conn.execute("SELECT COUNT(*) FROM genes WHERE synced=1").fetchone()[0]
    avg_f = conn.execute("SELECT AVG(fitness) FROM genes WHERE fitness>0").fetchone()[0] or 0
    return {"total": count, "synced": synced, "local_only": count-synced, "avg_fitness": round(avg_f,3)}

# ═══ 远程代理 ═══
def remote_search(url, query, limit=5, timeout=8):
    try:
        payload = json.dumps({"query": query, "n_results": limit}).encode()
        req = urllib.request.Request(f"{url}/genes/search",
            data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("results", [])
    except:
        return None

def remote_write(content, gene_type="semantic", fitness=0.6):
    """双写地枢"""
    try:
        gid = "GENE-LGA-" + hashlib.sha256(content.encode()).hexdigest()[:16]
        payload = json.dumps({"content": content, "gene_id": gid,
            "type": gene_type, "domain": "general", "fitness": fitness,
            "source": "灵龙LGA"}).encode()
        req = urllib.request.Request(f"{LGE_MASTER}/genes/write",
            data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except:
        return None

def sync_hot_genes(conn, limit=3000):
    """从地枢拉取热基因到本地"""
    queries = ["联邦 通讯 节点", "金字塔 七自", "Python 部署", "天巡 Widget",
               "LGOX 标准", "SSH 修复", "DeepSeek Ollama"]
    seen = set()
    all_genes = []
    for q in queries:
        results = remote_search(LGE_MASTER, q, limit=30)
        if results:
            for g in results:
                gid = g.get("gene_id","")
                if gid and gid not in seen:
                    seen.add(gid)
                    all_genes.append(g)
    if all_genes:
        for g in all_genes[:limit]:
            conn.execute("INSERT OR REPLACE INTO genes VALUES (?,?,?,?,?,?,?,1)",
                (g.get("gene_id",""), g.get("content","")[:500], g.get("type","semantic"),
                 g.get("fitness",0.5), g.get("domain","general"), "地枢同步",
                 g.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S"))))
            conn.execute("INSERT OR REPLACE INTO genes_fts VALUES (?,?)",
                (g.get("gene_id",""), g.get("content","")[:500]))
        conn.commit()
    return len(all_genes[:limit])

# ═══ API ═══
@app.get("/health")
async def health():
    conn = sqlite3.connect(DB)
    s = local_stats(conn)
    conn.close()
    return {"status": "ok", "service": "灵龙LGA v1.0", "port": PORT,
            "stats": s, "fallback": [TIANSHU_LGE, LGE_MASTER],
            "role": "三级降级·第一级·本地基因代理"}

@app.post("/genes/search")
async def search(request: Request):
    try: data = await request.json()
    except: return JSONResponse({"error": "invalid json"}, status_code=400)
    query = data.get("query", data.get("q", ""))
    if not query: return JSONResponse({"error": "query required"}, status_code=400)
    limit = min(data.get("n_results", data.get("limit", 5)), 10)

    conn = sqlite3.connect(DB)

    # 第一级: 本地LGA
    local = local_search(conn, query, limit)
    if local:
        conn.close()
        return {"results": local, "source": "灵龙LGA(0ms)", "total": len(local)}

    conn.close()

    # 第二级: 天枢副本
    tianshu = remote_search(TIANSHU_LGE, query, limit, timeout=3)
    if tianshu:
        return {"results": tianshu, "source": "天枢8201", "total": len(tianshu)}

    # 第三级: 地枢主库
    master = remote_search(LGE_MASTER, query, limit, timeout=8)
    if master:
        return {"results": master, "source": "地枢8200(主库)", "total": len(master)}

    return {"results": [], "source": "无结果"}

@app.post("/genes/write")
async def write(request: Request):
    try: data = await request.json()
    except: return JSONResponse({"error": "invalid json"}, status_code=400)
    content = data.get("content", "")
    if not content: return JSONResponse({"error": "content required"}, status_code=400)

    gid = "GENE-LGA-" + hashlib.sha256(content.encode()).hexdigest()[:16]
    gene_type = data.get("type", "semantic")
    fitness = data.get("fitness", 0.6)

    # 双写: 本地+地枢
    conn = sqlite3.connect(DB)
    local_write(conn, gid, content, gene_type, fitness)
    conn.close()

    # 异步写地枢(非阻塞)
    master_result = remote_write(content, gene_type, fitness)

    return {"status": "written", "gene_id": gid,
            "local": True, "master": master_result is not None,
            "master_gene_id": master_result.get("gene_id","") if master_result else ""}

@app.get("/genes/stats")
async def stats():
    conn = sqlite3.connect(DB)
    s = local_stats(conn)
    conn.close()
    return s

if __name__ == "__main__":
    conn = init_db()
    print(f"灵龙LGA v1.0 :{PORT} | 同步热基因中...")
    synced = sync_hot_genes(conn)
    s = local_stats(conn)
    conn.close()
    print(f"本地基因: {s['total']}条 | 端口:{PORT} | 三级降级第一级")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
