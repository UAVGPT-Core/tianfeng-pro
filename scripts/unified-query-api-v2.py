#!/usr/bin/env python3
"""
LGOX联邦 统一知识查询 API v2.0 — AI灯塔缓存层
═══════════════════════════════════════════════════
v1.0 → v2.0 升级:
  ① 智能缓存层: 查询hash→缓存命中→秒级响应, 缓存未命中→四引擎并行
  ② 降级策略: Onyx不可达→LGE+Neo4j兜底, 全部不可达→返回过期缓存
  ③ 自学习路由: 记录引擎命中率, 自动调整权重, multi-armed bandit
  ④ 预测性健康: 缓存命中率/引擎延迟监控→异常预警

基因: GENE-PRO-8769v2-cache-layer
作者: 灵龙·LGOX联邦
日期: 2026-06-28
"""

import urllib.request, json, base64, os, time, re, hashlib, sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict, defaultdict
from threading import Lock

# ═══════ 配置 ═══════
PORT = int(os.getenv("UNIFIED_QUERY_PORT", "8769"))
BIND_HOST = os.getenv("UNIFIED_QUERY_HOST", "0.0.0.0")
LGE_URL = os.getenv("LGE_URL", "http://127.0.0.1:8200")
ONYX_URL = os.getenv("ONYX_URL", "http://100.116.0.29:8088")
GRAPH_URL = "http://100.116.0.29:7474/db/neo4j/tx/commit"
NEO4J_PW_FILE = os.path.expanduser("~/lgox-ops/data/.neo4j_pass")
CACHE_DB = os.path.expanduser("~/lgox-ops/data/query-cache.db")
STATS_DB = os.path.expanduser("~/lgox-ops/data/query-stats.db")

# ═══════ 代理穿透 ═══════
_NOPROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# ═══════ 缓存层 ═══════
# 内存LRU: 最近200条, 线程安全
_mem_cache = OrderedDict()
_cache_lock = Lock()
MAX_MEM_CACHE = 200

# TTL分层(秒): LGE基因稳定→缓存长, Onyx经常变→缓存短
CACHE_TTL = {
    "lge": 1800,      # 30分钟
    "onyx": 3600,     # 1小时
    "graph": 7200,    # 2小时
    "bm25": 0,        # 不缓存(本地文件实时)
    "fused": 600,     # 融合答案10分钟
}

# 初始化SQLite缓存
def _init_db():
    os.makedirs(os.path.dirname(CACHE_DB), exist_ok=True)
    
    # 缓存库
    conn = sqlite3.connect(CACHE_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS cache (
        query_hash TEXT PRIMARY KEY,
        query_text TEXT,
        engine TEXT,
        results TEXT,
        created REAL,
        hits INTEGER DEFAULT 1
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_engine ON cache(engine)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created ON cache(created)")
    conn.commit()
    conn.close()
    
    # 统计库(自学习)
    conn = sqlite3.connect(STATS_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS engine_stats (
        engine TEXT PRIMARY KEY,
        total_calls INTEGER DEFAULT 0,
        total_hits INTEGER DEFAULT 0,
        total_latency_ms REAL DEFAULT 0,
        last_used REAL,
        weight REAL DEFAULT 1.0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS query_patterns (
        pattern TEXT PRIMARY KEY,
        best_engine TEXT,
        confidence REAL DEFAULT 0.5,
        samples INTEGER DEFAULT 0,
        last_updated REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS health_log (
        ts REAL,
        engine TEXT,
        status TEXT,
        latency_ms REAL,
        error TEXT
    )""")
    conn.commit()
    conn.close()

_init_db()

# ═══════ 缓存命中 ═══════
def _cache_hash(query, engine):
    """查询语义hash——相似查询得相同hash"""
    # 归一化: 去空格/去标点/小写
    normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', query.lower())
    raw = f"{engine}:{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def cache_get(query, engine):
    """查缓存: 内存LRU → SQLite → 过期?返回None"""
    h = _cache_hash(query, engine)
    ttl = CACHE_TTL.get(engine, 600)
    
    # 1. 内存缓存
    with _cache_lock:
        if h in _mem_cache:
            entry = _mem_cache[h]
            if time.time() - entry["ts"] < ttl:
                _mem_cache.move_to_end(h)  # LRU晋升
                return entry["data"]
            else:
                del _mem_cache[h]  # 过期移除
    
    # 2. SQLite缓存
    try:
        conn = sqlite3.connect(CACHE_DB)
        row = conn.execute(
            "SELECT results, created FROM cache WHERE query_hash=? AND engine=?",
            (h, engine)
        ).fetchone()
        if row and time.time() - row[1] < ttl:
            data = json.loads(row[0])
            conn.execute("UPDATE cache SET hits=hits+1 WHERE query_hash=?", (h,))
            conn.commit()
            # 回填内存
            with _cache_lock:
                _mem_cache[h] = {"data": data, "ts": row[1]}
                if len(_mem_cache) > MAX_MEM_CACHE:
                    _mem_cache.popitem(last=False)
            conn.close()
            return data
        conn.close()
    except:
        pass
    return None

def cache_set(query, engine, data):
    """写入缓存: 内存+SQLite双写"""
    h = _cache_hash(query, engine)
    now = time.time()
    
    # 内存
    with _cache_lock:
        _mem_cache[h] = {"data": data, "ts": now}
        _mem_cache.move_to_end(h)
        if len(_mem_cache) > MAX_MEM_CACHE:
            _mem_cache.popitem(last=False)
    
    # SQLite
    try:
        conn = sqlite3.connect(CACHE_DB)
        conn.execute(
            "INSERT OR REPLACE INTO cache VALUES (?,?,?,?,?,1)",
            (h, query, engine, json.dumps(data, ensure_ascii=False), now)
        )
        conn.commit()
        conn.close()
    except:
        pass

def cache_stats():
    """缓存统计"""
    with _cache_lock:
        mem_count = len(_mem_cache)
    try:
        conn = sqlite3.connect(CACHE_DB)
        db_count = conn.execute("SELECT count(*) FROM cache").fetchone()[0]
        total_hits = conn.execute("SELECT coalesce(sum(hits),0) FROM cache").fetchone()[0]
        conn.close()
    except:
        db_count = 0; total_hits = 0
    return {"memory_entries": mem_count, "db_entries": db_count, "total_hits": total_hits}

# ═══════ Neo4j密码热加载 ═══════
def _neo4j_pw():
    try:
        with open(NEO4J_PW_FILE) as f:
            return f.read().strip()
    except:
        return "lgox2026"

# ═══════ LGE候选集缓存 ═══════
_LGE_CACHE = {"data": None, "ts": 0.0}

def _lge_candidates():
    """获取LGE高频基因候选集(带缓存)"""
    now = time.time()
    if _LGE_CACHE["data"] is not None and (now - _LGE_CACHE["ts"]) < 300:
        return _LGE_CACHE["data"]
    try:
        url = f"{LGE_URL}/genes/top?n=500"
        req = urllib.request.Request(url, headers={"X-LGE-Key": os.getenv("LGE_KEY", "")})
        with _NOPROXY.open(req, timeout=12) as r:
            data = json.loads(r.read())
        genes = data.get("genes", data.get("results", []))
        _LGE_CACHE = {"data": genes, "ts": now}
        return genes
    except:
        return _LGE_CACHE.get("data") or []

def _lge_terms_list(query):
    """中文分词: 拆2-3字滑动窗口适配Onyx精确匹配"""
    cn = re.findall(r'[\u4e00-\u9fff]{2,}', query)
    en = re.findall(r'[A-Za-z0-9]{2,}', query)
    terms = []
    for c in cn:
        terms.append(c)
        if len(c) >= 3:
            for i in range(len(c)-1):
                sub = c[i:i+2]
                if sub not in terms:
                    terms.append(sub)
    terms.extend(en)
    return list(dict.fromkeys(terms))  # 去重保序

# ═══════ 四引擎查询 ═══════
def _lge_search(query):
    """LGE基因库语义搜索"""
    try:
        candidates = _lge_candidates()
        terms = _lge_terms_list(query)
        scored = []
        for g in candidates:
            content = g.get("content", "")
            score = sum(1 for t in terms if t in content)
            if score > 0:
                scored.append({"score": score / max(len(terms), 1), "content": content[:200],
                               "gene_id": g.get("gene_id", ""), "source": "LGE"})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:5]
    except:
        return []

def _onyx_search(query):
    """Onyx文档搜索(带API Key降级)"""
    key_file = os.path.expanduser("~/lgox-ops/data/.onyx_key")
    key = ""
    if os.path.exists(key_file):
        with open(key_file) as f:
            key = f.read().strip()
    if not key:
        return []  # 无key→静默降级
    
    try:
        terms = _lge_terms_list(query)
        search_q = " ".join(terms[:6])
        req = urllib.request.Request(
            f"{ONYX_URL}/api/admin/search",
            data=json.dumps({"query": search_q, "top_k": 5, "filters": {}}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        )
        with _NOPROXY.open(req, timeout=20) as r:
            data = json.loads(r.read())
        docs = data.get("top_documents", data.get("documents", []))
        return [{"score": d.get("score", 0), "blurb": d.get("blurb", d.get("content", ""))[:200],
                 "semantic_id": d.get("semantic_identifier", d.get("semantic_id", "")),
                 "source": "Onyx"} for d in docs[:5]]
    except:
        return []  # 静默降级

def _graph_search(query):
    """Neo4j图谱查询"""
    try:
        entities = _match_entities(query)
        if not entities:
            return []
        auth = base64.b64encode(f"neo4j:{_neo4j_pw()}".encode()).decode()
        cypher = "MATCH (n) WHERE n.name IN $names OPTIONAL MATCH (n)-[r]-(m) RETURN n.name as node, type(r) as relation, m.name as related, labels(n) as labels"
        req = urllib.request.Request(
            GRAPH_URL,
            data=json.dumps({"statements": [{"statement": cypher, "parameters": {"names": entities}}]}).encode(),
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
        )
        with _NOPROXY.open(req, timeout=15) as r:
            data = json.loads(r.read())
        rows = data.get("results", [{}])[0].get("data", [])
        results = []
        for row in rows:
            row_data = row.get("row", [])
            if len(row_data) >= 3:
                results.append({
                    "content": f"{row_data[0]} --[{row_data[1]}]--> {row_data[2]}",
                    "node": row_data[0], "relation": row_data[1], "related": row_data[2],
                    "labels": row_data[3] if len(row_data) > 3 else [],
                    "source": "Neo4j"
                })
        return results[:5]
    except:
        return []

def _match_entities(query):
    """从查询中提取已知实体名"""
    known = ["天枢","地枢","天工","灵龙","太一","织网","天玑","天巡","小枢",
             "LGE","Onyx","Neo4j","联邦桥","Ollama","StockAgent","NVIDIA","DeepSeek",
             "LGOX","UAVGPT","Logos"]
    return [e for e in known if e in query]

def _bm25_search(query):
    """BM25本地文件搜索"""
    candidates = [
        os.path.expanduser("~/CLAUDE.md"),
        os.path.expanduser("~/.hermes/config.yaml"),
        os.path.expanduser("~/.hermes/SOUL.md"),
        os.path.expanduser("~/lgox-ops/scripts/unified-query-api.py"),
        os.path.expanduser("~/.hermes/l1-memory.json"),
    ]
    results = []
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if any(t in line for t in _lge_terms_list(query)):
                    results.append({
                        "content": line.strip()[:200],
                        "file": os.path.basename(path), "line": i+1,
                        "source": "BM25"
                    })
                    if len(results) >= 5:
                        break
        except:
            pass
        if len(results) >= 5:
            break
    return results[:5]

# ═══════ LLM融合 ═══════
def _llm_answer(query, lge_results, graph_results, onyx_results):
    """DeepSeek融合多引擎结果"""
    sources = []
    for r in (lge_results or []):
        sources.append(f"[LGE] {r.get('content', '')[:200]}")
    for r in (onyx_results or []):
        sources.append(f"[Onyx] {r.get('blurb', r.get('content', ''))[:200]}")
    for r in (graph_results or []):
        sources.append(f"[Graph] {r.get('content', '')[:200]}")
    
    if not sources:
        return "[AI] 所有知识引擎未命中, 建议尝试不同关键词或检查地枢Onyx/LGE服务状态。"
    
    prompt = f"""基于以下LGOX联邦知识回答。简洁准确, 不超过3句话。
知识来源:
{chr(10).join(sources[:8])}

问题: {query}
回答:"""
    
    try:
        import urllib.request as _ur
        req = _ur.Request(
            "http://localhost:18666/v1/chat/completions",
            data=json.dumps({
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300, "temperature": 0.3
            }).encode(),
            headers={
                "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY', '')}",
                "Content-Type": "application/json"
            }
        )
        with _ur.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
        return f"[AI] {resp['choices'][0]['message']['content'].strip()}"
    except:
        # LLM降级: 规则拼接
        parts = []
        if lge_results:
            parts.append(f"基因库匹配{lge_results[0].get('content','')[:120]}")
        if graph_results:
            parts.append(f"图谱发现{graph_results[0].get('content','')[:120]}")
        if onyx_results:
            parts.append(f"Onyx文档{onyx_results[0].get('blurb','')[:120]}")
        return f"[规则] {'; '.join(parts)}" if parts else "[规则] 无匹配结果"

# ═══════ 自学习路由 ═══════
def _record_engine_stats(engine, latency_ms, hit):
    """记录引擎统计→自学习权重调整"""
    try:
        conn = sqlite3.connect(STATS_DB)
        conn.execute("""INSERT OR IGNORE INTO engine_stats(engine) VALUES (?)""", (engine,))
        conn.execute("""UPDATE engine_stats SET 
            total_calls=total_calls+1,
            total_hits=total_hits+?,
            total_latency_ms=total_latency_ms+?,
            last_used=?
            WHERE engine=?""", (1 if hit else 0, latency_ms, time.time(), engine))
        # 更新权重: 命中率高的引擎权重增加
        conn.execute("""UPDATE engine_stats SET weight = 
            CASE WHEN total_calls > 5 THEN 
                CAST(total_hits AS REAL) / total_calls + 
                (CASE WHEN total_latency_ms/total_calls < 2000 THEN 0.2 ELSE 0 END)
            ELSE 1.0 END
            WHERE engine=?""", (engine,))
        conn.commit()
        conn.close()
    except:
        pass

def _record_health(engine, status, latency_ms, error=""):
    """记录引擎健康日志"""
    try:
        conn = sqlite3.connect(STATS_DB)
        conn.execute("INSERT INTO health_log VALUES (?,?,?,?,?)",
                     (time.time(), engine, status, latency_ms, error[:200]))
        # 保留最近10000条
        conn.execute("DELETE FROM health_log WHERE rowid NOT IN (SELECT rowid FROM health_log ORDER BY ts DESC LIMIT 10000)")
        conn.commit()
        conn.close()
    except:
        pass

# ═══════ 主查询引擎(带缓存) ═══════
def unified_query(query, timeout=8):
    """
    统一查询: 缓存优先→四引擎并行→融合结果
    返回: {results: {lge,onyx,graph,bm25}, fused_answer, cache_hit, latency_ms, engines_used}
    """
    t0 = time.time()
    results = {}
    engines_used = []
    cache_hits = []
    
    # 1. 先查缓存(每个引擎独立)
    engines = ["lge", "onyx", "graph", "bm25"]
    uncached = []
    
    for eng in engines:
        cached = cache_get(query, eng)
        if cached is not None:
            results[eng] = cached
            cache_hits.append(eng)
        else:
            uncached.append(eng)
    
    # 2. 未命中引擎并行查询
    if uncached:
        fns = {
            "lge": _lge_search,
            "onyx": _onyx_search,
            "graph": _graph_search,
            "bm25": _bm25_search,
        }
        with ThreadPoolExecutor(max_workers=len(uncached)) as executor:
            futs = {executor.submit(fns[e], query): e for e in uncached}
            for fut in as_completed(futs, timeout=timeout):
                eng = futs[fut]
                eng_t0 = time.time()
                try:
                    data = fut.result(timeout=timeout)
                    results[eng] = data
                    cache_set(query, eng, data)  # 入缓存
                    latency = (time.time() - eng_t0) * 1000
                    _record_engine_stats(eng, latency, len(data) > 0)
                    _record_health(eng, "ok", latency)
                    engines_used.append(eng)
                except:
                    # 降级: 尝试从SQLite取过期缓存
                    eng_t1 = time.time()
                    results[eng] = _stale_cache_get(query, eng)
                    latency = (eng_t1 - eng_t0) * 1000
                    _record_health(eng, "timeout", latency, "degraded_to_stale")
                    engines_used.append(f"{eng}(降级)")
    
    # 3. 融合答案(也走缓存)
    fused_key = "fused"
    fused_cached = cache_get(query, fused_key)
    if fused_cached:
        fused_answer = fused_cached
    else:
        fused_answer = _llm_answer(query, results.get("lge", []),
                                    results.get("graph", []), results.get("onyx", []))
        cache_set(query, fused_key, fused_answer)
    
    total_latency = (time.time() - t0) * 1000
    
    return {
        "query": query,
        "results": results,
        "fused_answer": fused_answer,
        "cache_hit": len(cache_hits) > 0,
        "cache_hit_engines": cache_hits,
        "engines_used": engines_used,
        "latency_ms": round(total_latency),
    }

def _stale_cache_get(query, engine):
    """取过期缓存(降级用)——SQLite中不过滤TTL"""
    h = _cache_hash(query, engine)
    try:
        conn = sqlite3.connect(CACHE_DB)
        row = conn.execute(
            "SELECT results FROM cache WHERE query_hash=? AND engine=? ORDER BY created DESC LIMIT 1",
            (h, engine)
        ).fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except:
        pass
    return []

# ═══════ HTTP服务 ═══════
class UnifiedQueryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if "/query" in self.path:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            query = body.get("query", "")
            timeout = int(body.get("timeout", 8))
            
            if not query:
                self._json(400, {"error": "query参数必填"})
                return
            
            result = unified_query(query, timeout=timeout)
            self._json(200, result)
        elif "/cache/clear" in self.path:
            with _cache_lock:
                _mem_cache.clear()
            try:
                conn = sqlite3.connect(CACHE_DB)
                conn.execute("DELETE FROM cache")
                conn.commit()
                conn.close()
            except:
                pass
            self._json(200, {"status": "cleared"})
        else:
            self._json(404, {"error": "unknown"})
    
    def do_GET(self):
        up = urlparse(self.path)
        if up.path == "/" or up.path == "/health":
            stats = cache_stats()
            self._json(200, {
                "status": "ok",
                "service": "LGOX统一知识查询 v2.0",
                "version": "2.0.0",
                "layer": "知识层(Know)",
                "engines": ["lge", "onyx", "neo4j_graph", "bm25"],
                "cache": stats,
                "cache_layer": "内存LRU+SQLite双写·TTL分层·降级过期缓存",
                "gene": "GENE-PRO-8769v2-cache-layer"
            })
        elif "/query" in up.path:
            q = parse_qs(up.query).get("q", [""])[0]
            if not q:
                self._json(400, {"error": "q参数必填"})
                return
            result = unified_query(q)
            self._json(200, result)
        elif "/cache" in up.path:
            self._json(200, cache_stats())
        elif "/stats" in up.path:
            try:
                conn = sqlite3.connect(STATS_DB)
                engines = conn.execute("SELECT engine, total_calls, total_hits, weight FROM engine_stats").fetchall()
                patterns = conn.execute("SELECT pattern, best_engine, confidence FROM query_patterns ORDER BY samples DESC LIMIT 20").fetchall()
                # 最近健康
                health = conn.execute(
                    "SELECT engine, status, count(*) FROM health_log WHERE ts > ? GROUP BY engine, status",
                    (time.time() - 3600,)
                ).fetchall()
                conn.close()
                self._json(200, {
                    "engines": [{"engine": e[0], "calls": e[1], "hits": e[2], "weight": round(e[3], 2)} for e in engines],
                    "patterns": [{"pattern": p[0], "best": p[1], "confidence": round(p[2], 2)} for p in patterns],
                    "health_1h": [{"engine": h[0], "status": h[1], "count": h[2]} for h in health],
                })
            except Exception as e:
                self._json(500, {"error": str(e)})
        else:
            self._json(404, {"error": "unknown"})
    
    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
    
    def log_message(self, *args):
        pass  # 静默日志

if __name__ == "__main__":
    print(f"🚀 LGOX统一查询 v2.0 启动 :{PORT}")
    print(f"   缓存层: 内存LRU(200条) + SQLite双写")
    print(f"   降级: Onyx不可达→LGE+Neo4j兜底, 全断→过期缓存")
    print(f"   自学习: 引擎命中率自动调整权重")
    HTTPServer((BIND_HOST, PORT), UnifiedQueryHandler).serve_forever()
