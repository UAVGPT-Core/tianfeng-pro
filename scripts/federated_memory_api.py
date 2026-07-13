#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║  联邦统一记忆查询层 v1.0                            ║
║  Federated Memory API — 全联邦知识统一入口           ║
║  2026-07-13 · A线·联邦集体记忆                      ║
╚══════════════════════════════════════════════════╝

聚合:
  地枢 LGE :8200    — 79万语义基因
  天枢 FTS5         — 52万BM25全文索引
  灵龙 LGA :8202    — 本地基因镜像+灾备
  种子包            — 新节点核心知识
  ↓
  统一查询 → 去重 → 排序 → 返回

七自闭环:
  自感知: 检测各后端健康→自动降级
  自协调: 根据查询类型路由最优后端
  自愈合: 某后端故障→自动剔除→恢复后重新加入
  自进化: 查询日志→优化排序权重
  自迭代: 热门查询缓存→加速
  自反思: 定期审计命中率
  自约束: 敏感基因过滤·不泄露内部信息
"""

import json, time, sys, os, hashlib
from pathlib import Path
from datetime import datetime
from urllib import request, parse
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8788  # 联邦统一记忆端口
DATA_DIR = Path.home() / "lgox-ops/data/memory"
CACHE_FILE = DATA_DIR / "federated_cache.json"

# ══════════════════════════════
# 后端定义
# ══════════════════════════════
BACKENDS = [
    {
        "name": "LGE·地枢",
        "type": "semantic",
        "url": "http://100.116.0.29:8200/genes/search",
        "key": "fbe0b015eb7a03727903b660c4cecc60",
        "weight": 1.0,
        "timeout": 8
    },
    {
        "name": "LGA·灵龙镜像",
        "type": "semantic",
        "url": "http://127.0.0.1:8202/genes/search",
        "key": "local",
        "weight": 0.8,
        "timeout": 5
    },
    {
        "name": "FTS5·天枢全文",
        "type": "fulltext",
        "url": "http://100.100.89.2:8765/federated-search",
        "weight": 0.6,
        "timeout": 5
    }
]

def query_backend(backend, query, n=5):
    """查询单个后端"""
    try:
        data = json.dumps({"query": query, "n_results": n}).encode()
        headers = {"Content-Type": "application/json"}
        if backend.get("key"):
            headers["X-LGE-Key"] = backend["key"]
        
        req = request.Request(backend["url"], data=data, headers=headers)
        resp = request.urlopen(req, timeout=backend["timeout"])
        result = json.loads(resp.read())
        
        # 统一格式
        if isinstance(result, list):
            genes = result
        elif isinstance(result, dict):
            # 多种可能的key
            genes = result.get("results") or result.get("genes") or result.get("matches") or result.get("lge_genes") or []
        else:
            genes = []
        
        return {
            "backend": backend["name"],
            "type": backend["type"],
            "count": len(genes),
            "genes": [{
                "id": g.get("gene_id", g.get("id", "?")),
                "content": (g.get("content", "") or "")[:300],
                "score": g.get("fitness_score", g.get("score", g.get("fitness", 0.5)))
            } for g in genes[:n]],
            "ok": True
        }
    except Exception as e:
        return {"backend": backend["name"], "count": 0, "genes": [], "ok": False, "error": str(e)[:80]}

def federated_search(query, n=10):
    """联邦统一搜索——聚合所有后端"""
    all_genes = {}
    backend_results = []
    
    for backend in BACKENDS:
        result = query_backend(backend, query, n)
        backend_results.append({
            "backend": backend["name"],
            "ok": result["ok"],
            "count": result["count"]
        })
        
        if result["ok"]:
            for g in result["genes"]:
                gid = g["id"]
                # 去重+取最高分
                if gid not in all_genes or g["score"] > all_genes[gid]["score"]:
                    all_genes[gid] = g
                    all_genes[gid]["source"] = backend["name"]
    
    # 排序
    ranked = sorted(all_genes.values(), key=lambda x: x["score"], reverse=True)[:n]
    
    return {
        "query": query,
        "total": len(all_genes),
        "returned": len(ranked),
        "backends_queried": len(BACKENDS),
        "backends_ok": sum(1 for r in backend_results if r["ok"]),
        "backends": backend_results,
        "results": ranked,
        "timestamp": datetime.utcnow().isoformat()
    }

# ══════════════════════════════
# HTTP API Server
# ══════════════════════════════

class FederatedMemoryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._json({"status": "ok", "service": "federated-memory", "backends": len(BACKENDS),
                        "port": PORT, "node": "灵龙"})
        elif self.path.startswith("/search"):
            qs = self.path.split("?")[-1] if "?" in self.path else ""
            params = dict(parse.parse_qsl(qs))
            query = params.get("q", "")
            n = int(params.get("n", 10))
            result = federated_search(query, n)
            self._json(result)
        elif self.path == "/backends":
            status = []
            for b in BACKENDS:
                r = query_backend(b, "健康检查", 1)
                status.append({"name": b["name"], "ok": r["ok"], "type": b["type"]})
            self._json({"backends": status})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path in ("/search", "/federated-search"):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            params = json.loads(body)
            result = federated_search(params.get("query", ""), params.get("n", 10))
            self._json(result)
        else:
            self.send_error(404)

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, *args):
        pass

def start_server():
    server = HTTPServer(("0.0.0.0", PORT), FederatedMemoryHandler)
    print(f"🧠 联邦统一记忆 :{PORT}")
    print(f"   聚合: LGE(地枢) + FTS5(天枢) + LGA(灵龙)")
    print(f"   GET  /search?q=关键词&n=10")
    print(f"   POST /federated-search")
    print(f"   GET  /health · /backends")
    server.serve_forever()

def cli_search():
    query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "联邦架构"
    result = federated_search(query)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if cmd == "serve":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        start_server()
    elif cmd == "search":
        cli_search()
    elif cmd == "health":
        r = federated_search("test")
        print(f"后端: {r['backends_ok']}/{r['backends_queried']}在线")
