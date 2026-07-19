#!/opt/homebrew/bin/python3
"""
联邦搜索桥 v4.0 — WebSocket 双工通信版
双通道广播: SSE(兼容旧客户端) + WebSocket(全双工实时)
新增 /ws 端点 — 联邦聊天室基础设施
"""
import http.server
import json
import os
import threading
import time
import uuid
import sqlite3
import socket
import http.client
import urllib.parse
import sys
import struct
import hashlib
import base64
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

# ═══════════════════════════════════════════
# 环境变量配置
# ═══════════════════════════════════════════
ONYX_HOST = os.getenv("ONYX_HOST", "localhost")
ONYX_PORT = int(os.getenv("ONYX_PORT", "8088"))
ONYX_TOKEN = os.getenv("ONYX_TOKEN", "on_tiq3GLrK9Q3AsAc2G9saQSWY")
LGE_HOST = os.getenv("LGE_HOST", "100.116.0.29")
LGE_PORT = int(os.getenv("LGE_PORT", "8200"))
LGE_TOKEN = os.getenv("LGE_TOKEN", "lgox")
FTS5_DB = os.path.expanduser("~/lge-studio/data/lge_fts.db")

# SSE 连接池 (兼容旧客户端)
_SSE_CLIENTS = {}  # {node_name: [wfile, ...]}
_SSE_LOCK = threading.Lock()

# WebSocket 连接池 (新客户端 — 全双工)
_WS_CLIENTS = {}   # {node_name: [(wfile, client_id), ...]}
_WS_LOCK = threading.Lock()

# ============================================
# 查询缓存
# ============================================
_FB_QUERY_CACHE = {}
_FB_QUERY_CACHE_LOCK = threading.Lock()

# ============================================
# 权威检索层 (惰性加载)
# ============================================
_LR = None

# ═══════════════════════════════════════════
# SSE 广播函数 (保留不变)
# ═══════════════════════════════════════════
def _sse_broadcast(node_name: str, event_type: str, payload: dict):
    """向指定节点的所有 SSE 客户端推送事件"""
    with _SSE_LOCK:
        clients = _SSE_CLIENTS.get(node_name, [])[:]
    dead = []
    data_str = json.dumps(payload, ensure_ascii=False)
    msg = f"event: {event_type}\ndata: {data_str}\n\n".encode("utf-8")
    for wfile in clients:
        try:
            wfile.write(msg)
            wfile.flush()
        except Exception:
            dead.append(wfile)
    if dead:
        with _SSE_LOCK:
            lst = _SSE_CLIENTS.get(node_name, [])
            for d in dead:
                if d in lst:
                    lst.remove(d)

# ═══════════════════════════════════════════
# WebSocket 帧处理 (RFC 6455)
# ═══════════════════════════════════════════

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_TEXT   = 0x1
OP_BINARY = 0x2
OP_CLOSE  = 0x8
OP_PING   = 0x9
OP_PONG   = 0xA

def _ws_handshake(handler) -> bool:
    """在 http.server handler 上执行 WS 握手。返回 True 表示成功。"""
    # 读取HTTP请求头 (必须读完直到CRLF-CRLF)
    # 注意: do_GET已经读取了请求行，header已被 http.server 解析
    # 我们需要从 self.headers 获取
    key = handler.headers.get("Sec-WebSocket-Key", "")
    # 检查是否是WebSocket升级请求
    upgrade = handler.headers.get("Upgrade", "").lower()
    connection = handler.headers.get("Connection", "").lower()
    if upgrade != "websocket" or "upgrade" not in connection or not key:
        return False

    accept = base64.b64encode(
        hashlib.sha1((key + WS_MAGIC).encode()).digest()
    ).decode()

    handler.send_response(101, "Switching Protocols")
    handler.send_header("Upgrade", "websocket")
    handler.send_header("Connection", "Upgrade")
    handler.send_header("Sec-WebSocket-Accept", accept)
    handler.end_headers()
    return True


def _ws_encode_frame(payload: bytes, opcode: int = OP_TEXT) -> bytes:
    """Server→Client: 编码 WS 帧 (不掩码)"""
    frame = bytearray()
    frame.append(0x80 | opcode)  # FIN + opcode
    length = len(payload)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(127)
        frame.extend(struct.pack(">Q", length))
    frame.extend(payload)
    return bytes(frame)


def _ws_encode_close(code: int = 1000) -> bytes:
    """编码关闭帧"""
    return _ws_encode_frame(struct.pack(">H", code), OP_CLOSE)


def _ws_read_frame(rfile) -> dict | None:
    """从 rfile 读取一个完整的 WS 帧。Client→Server (必须掩码)。
    返回 {"opcode": int, "payload": bytes} 或 None(连接断开/错误)。
    """
    try:
        b1 = rfile.read(1)
        if not b1 or len(b1) < 1:
            return None
        b1 = b1[0]
        fin = (b1 >> 7) & 1
        opcode = b1 & 0xF

        b2 = rfile.read(1)
        if not b2 or len(b2) < 1:
            return None
        b2 = b2[0]
        masked = (b2 >> 7) & 1

        plen = b2 & 0x7F
        if plen == 126:
            ext = rfile.read(2)
            if len(ext) < 2:
                return None
            plen = struct.unpack(">H", ext)[0]
        elif plen == 127:
            ext = rfile.read(8)
            if len(ext) < 8:
                return None
            plen = struct.unpack(">Q", ext)[0]

        mask_key = b""
        if masked:
            mask_key = rfile.read(4)
            if len(mask_key) < 4:
                return None

        payload = rfile.read(plen) if plen > 0 else b""
        if len(payload) < plen:
            return None

        if masked and mask_key:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

        if opcode == OP_CLOSE:
            return {"opcode": OP_CLOSE, "payload": payload}
        if opcode == OP_PING:
            return {"opcode": OP_PING, "payload": payload}
        if opcode == OP_PONG:
            return {"opcode": OP_PONG, "payload": payload}

        return {"opcode": opcode, "payload": payload, "fin": fin == 1}
    except (OSError, ConnectionResetError, BrokenPipeError, struct.error):
        return None


def _ws_send(wfile, payload: bytes, opcode: int = OP_TEXT):
    """发送 WS 帧到客户端"""
    try:
        wfile.write(_ws_encode_frame(payload, opcode))
        wfile.flush()
    except Exception:
        pass


def _ws_broadcast(node_name: str, event_type: str, payload: dict):
    """向指定节点的所有 WS 客户端推送消息"""
    with _WS_LOCK:
        clients = _WS_CLIENTS.get(node_name, [])[:]
    dead = []
    msg = json.dumps({"type": event_type, **payload}, ensure_ascii=False)
    for wfile, cid in clients:
        try:
            wfile.write(_ws_encode_frame(msg.encode("utf-8"), OP_TEXT))
            wfile.flush()
        except Exception:
            dead.append((wfile, cid))
    if dead:
        with _WS_LOCK:
            lst = _WS_CLIENTS.get(node_name, [])
            for d in dead:
                if d in lst:
                    lst.remove(d)


def _ws_broadcast_all(event_type: str, payload: dict, exclude_node: str = None):
    """向所有连接节点的 WS 客户端广播"""
    with _WS_LOCK:
        nodes = [n for n in _WS_CLIENTS if n != exclude_node and _WS_CLIENTS[n]]
    for node in nodes:
        _ws_broadcast(node, event_type, payload)


# ═══════════════════════════════════════════
# LGE 安全检索 (保留不变)
# ═══════════════════════════════════════════

_lge_top_cache = None
_lge_top_cache_ts = 0

def _lge_get_top_candidates(n: int = 1200):
    """获取高fitness候选池 (5min缓存)"""
    global _lge_top_cache, _lge_top_cache_ts
    now = time.time()
    if _lge_top_cache and now - _lge_top_cache_ts < 300:
        return _lge_top_cache
    try:
        conn = http.client.HTTPConnection(LGE_HOST, LGE_PORT, timeout=5)
        conn.request("GET", f"/genes/top?limit={n}", headers={"X-LGE-Key": LGE_TOKEN})
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        _lge_top_cache = data.get("results", data if isinstance(data, list) else [])
        _lge_top_cache_ts = now
        return _lge_top_cache
    except Exception:
        return _lge_top_cache or []


def lge_safe_search(query: str, n_results: int = 5, min_score: float = 0.2) -> dict:
    """安全LGE检索 — 本地候选池精排 (不调用地枢/genes/search避雪崩)"""
    import re
    candidates = _lge_get_top_candidates(1200)
    if not candidates:
        return {"results": [], "engine": "safe-top-empty", "total_candidates": 0}

    qwords = set(re.findall(r'[\u4e00-\u9fff\w]+', query.lower()))
    # 混合评分: IDF-like term freq + keyword bonus
    def _score(item):
        content = (item.get("content", "") or "").lower()
        gene_id = (item.get("gene_id", "") or "").lower()
        content = (content + " " + gene_id).lower()
        score = 0.0
        for w in reversed(qwords):
            cnt = content.count(w)
            if cnt:
                score += cnt * 2.0 / (1 + len(content) / 500.0)
        return score

    scored = sorted(candidates, key=_score, reverse=True)
    results = [dict(r, _score=_score(r)) for r in scored[:n_results] if _score(r) > 0.05]
    return {"results": results, "engine": "safe-top-idf", "total_candidates": len(candidates)}

# ═══════════════════════════════════════════
# LGE FTS5 全量检索 (天枢本地, 30万基因)
# ═══════════════════════════════════════════

_fts5_db = None

def _get_fts5_db():
    global _fts5_db
    if _fts5_db is None:
        try:
            _fts5_db = sqlite3.connect(f"file:{FTS5_DB}?mode=ro", uri=True)
        except Exception:
            return None
    return _fts5_db

def lge_fts_search(query: str, n_results: int = 5) -> dict:
    """FTS5 BM25 检索"""
    import re
    db = _get_fts5_db()
    if not db:
        return {"results": [], "engine": "fts5-unavailable"}
    words = re.findall(r'[\u4e00-\u9fff\w]+', query.lower())
    if not words:
        return {"results": [], "engine": "fts5-empty-query"}
    fts_query = " OR ".join(f'"{w}"' for w in words[:10])
    try:
        cur = db.execute(f"""
            SELECT gene_id, content_preview, score, fitness, source, snapshot_ts
            FROM lge_fts WHERE lge_fts MATCH ?
            ORDER BY rank LIMIT ?""", (fts_query, n_results))
        rows = cur.fetchall()
        return {"results": [
            {"gene_id": r[0], "content": r[1], "score": r[2],
             "fitness": r[3], "source": r[4], "_fts5_match": True}
            for r in rows
        ], "engine": "fts5-bm25"}
    except Exception:
        return {"results": [], "engine": "fts5-error"}


# ═══════════════════════════════════════════
# 域名扩展映射
# ═══════════════════════════════════════════
DOMAIN_EXPANSION_MAP = {
    "general": ["general", "meta", "stock"],
    "stock": ["stock", "general", "meta"],
    "uav": ["uav", "general", "meta"],
    "meta": ["meta", "general"],
}

def expand_domain_query(query: str, domain: str, n_per_domain: int = 3) -> dict:
    domains = DOMAIN_EXPANSION_MAP.get(domain, [domain] if domain else ["general"])
    merged = {"results": [], "sources_searched": []}
    seen = set()
    for dom in domains[:4]:
        try:
            data = lge_safe_search(f"domain:{dom} {query}", n_per_domain, 0.15)
            for r in data.get("results", []):
                cid = r.get("gene_id", "") + str(r.get("content", ""))[:100]
                if cid not in seen:
                    seen.add(cid)
                    r["_source_domain"] = dom
                    merged["results"].append(r)
            merged["sources_searched"].append(dom)
        except Exception:
            merged["sources_searched"].append(f"{dom}(error)")
    merged["results"].sort(key=lambda x: x.get("score", 0), reverse=True)
    return merged

# ═══════════════════════════════════════════
# 统一认知模型 (保留不变)
# ═══════════════════════════════════════════
DOMAIN_KEYWORDS = {
    "stock": ["股票", "行情", "信号", "基金", "ETF", "交易", "量化", "买入", "卖出", "股价", "K线", "投资"],
    "uav": ["无人机", "巡检", "绝缘子", "输电", "光伏", "缺陷", "航拍", "机巢", "Dock", "Matrice"],
    "desktop": ["桌面", "截图", "OCR", "点击", "输入", "快捷键", "Peekaboo", "Browser", "Chrome", "自动化"],
    "visual": ["图像", "SD", "ComfyUI", "生成", "视觉", "缺陷图", "合成数据", "LoRA"],
    "meta": ["LGOX", "联邦", "基因", "进化", "节点", "天锋", "天枢", "天工", "宪法", "战略"],
    "general": ["分析", "研究", "报告", "方案", "对比", "评估", "总结"],
}

DOMAIN_TO_NODE = {
    "stock": "小枢(天枢)", "uav": "天巡(天枢)",
    "visual": "天工", "meta": "天枢·战略", "general": "全联邦"
}

# ═══════════════════════════════════════════
# 节点注册表
# ═══════════════════════════════════════════
FEDERATION_NODES = {}

NODE_BASELINE = {
    "天枢": {
        "ip": "100.100.89.2", "hostname": "1mac-studio", "os": "macOS",
        "role": "总指挥工作站",
        "services": {"StockAgent后端": "localhost:8001", "前端代理": "localhost:8080",
                     "联邦搜索桥": "localhost:8765", "Onyx知识库": "localhost:8088"}
    },
    "地枢": {
        "ip": "100.116.0.29", "hostname": "spark-5438", "os": "linux",
        "role": "LGE基因引擎 + Onyx + 监控",
        "services": {"LGE基因引擎": "127.0.0.1:8200", "Onyx": "100.116.0.29:8080",
                     "Grafana": "100.116.0.29:9090"}
    },
    "天工": {
        "ip": "100.118.207.31", "hostname": "spark-abbd", "os": "linux",
        "role": "Ollama降级 + GPU推理",
        "services": {"Ollama(qwen2.5:72b)": "100.118.207.31:11434"},
        "gpu": "NVIDIA GB10, 119GB统一内存"
    },
    "灵龙": {
        "ip": "100.120.20.52", "hostname": "mac-mini", "os": "macOS",
        "role": "Ollama轻量推理",
        "services": {"Ollama(hermes3/deepseek-r1)": "100.120.20.52:11434"}
    },
    "太一": {
        "ip": "100.103.193.98", "hostname": "xycity", "os": "windows",
        "role": "Windows总指挥 + WSL OpenClaw",
        "services": {"Ollama(Windows)": "100.103.193.98:11434",
                     "OpenClaw API": "100.103.193.98:18789"}
    },
    "织网": {
        "ip": "100.127.112.128", "hostname": "ecs-zhinet", "os": "linux",
        "role": "华为云ECS · 轻量服务",
        "services": {"Docker(MySQL+PG+Redis+WordPress)": "100.127.112.128"}
    },
    "天玑": {
        "ip": "100.82.185.126", "hostname": "tianji", "os": "windows+wsl2",
        "role": "第7物理节点 · WSL推理+工具箱",
        "services": {"Hermes(Windows)": "100.82.185.126:8089",
                     "Hermes(WSL)": "100.122.142.74:8090",
                     "ChromeCDP": "100.82.185.126:9222"}
    },
    "天怿": {
        "ip": None, "hostname": "tianyi", "os": "linux",
        "role": "第8物理节点 · 学习节点",
        "services": {}
    },
    "AI助手": {
        "ip": "100.100.89.2", "hostname": "1mac-studio", "os": "macOS",
        "role": "第9节点 · 联邦智能入口",
        "services": {"Widget聊天": "100.100.89.2:18901",
                     "WebSocket流式": "localhost:8001/ws"}
    },
    "天巡": {
        "ip": "100.100.89.2", "hostname": "1mac-studio", "os": "macOS",
        "role": "第10节点 · 通讯层哨兵 · 企业AI门面",
        "services": {"天巡流式": "100.100.89.2:18902"}
    },
    "小枢": {
        "ip": "100.100.89.2", "hostname": "1mac-studio", "os": "macOS",
        "role": "第11节点 · StockAgent AI助手",
        "services": {"小枢流式": "localhost:8001/chat"}
    },
}


# ═══════════════════════════════════════════
# 数据库层
# ═══════════════════════════════════════════
DB_PATH = os.path.expanduser("~/.hermes/fed_messages.db")

def _get_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            node TEXT, from_node TEXT, content TEXT,
            ts TEXT DEFAULT (datetime('now','localtime')),
            read INTEGER DEFAULT 0
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_msg_node ON messages(node)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_msg_unread ON messages(node, read)")
    # 节点注册表
    db.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            name TEXT PRIMARY KEY,
            ip TEXT, hostname TEXT, os TEXT,
            role TEXT, services TEXT,
            last_heartbeat REAL DEFAULT 0,
            status TEXT DEFAULT 'unknown',
            description TEXT DEFAULT ''
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status)")
    db.commit()
    return db


def _db_is_dup(node: str, from_node: str, content: str, window: int = 300) -> bool:
    """检查同node+from+content在window秒内是否已存在"""
    db = _get_db()
    threshold = time.time() - window
    cur = db.execute(
        "SELECT COUNT(*) FROM messages WHERE node=? AND from_node=? AND content=? AND ts>?",
        (node, from_node, content, time.strftime("%Y-%m-%d %H:%M:%S",
                                                 time.localtime(threshold))))
    return cur.fetchone()[0] > 0


def _db_save(node: str, msg_id: str, from_node: str, content: str, ts: str):
    db = _get_db()
    db.execute("INSERT OR REPLACE INTO messages(id, node, from_node, content, ts, read) VALUES(?,?,?,?,?,0)",
               (msg_id, node, from_node, content, ts))
    db.commit()


def _db_get_inbox(node: str) -> list:
    db = _get_db()
    cur = db.execute(
        "SELECT id, from_node, content, ts, node FROM messages WHERE node=? AND read=0 ORDER BY ts DESC LIMIT 50",
        (node,))
    return [{"id": r[0], "from": r[1], "content": r[2], "ts": r[3], "to": r[4]} for r in cur.fetchall()]


def _db_count_node(node: str) -> int:
    cur = _get_db().execute("SELECT COUNT(*) FROM messages WHERE node=? AND read=0", (node,))
    return cur.fetchone()[0]


def _db_count_unread() -> int:
    cur = _get_db().execute("SELECT COUNT(*) FROM messages WHERE read=0")
    return cur.fetchone()[0]


def _db_all_unread_by_node() -> list:
    cur = _get_db().execute(
        "SELECT node, COUNT(*) as cnt FROM messages WHERE read=0 GROUP BY node ORDER BY cnt DESC")
    return [{"node": r[0], "cnt": r[1]} for r in cur.fetchall()]


def _db_clear_inbox(node: str) -> int:
    db = _get_db()
    cur = db.execute("UPDATE messages SET read=1 WHERE node=? AND read=0", (node,))
    db.commit()
    return cur.rowcount


def _db_register_node(name: str, ip: str, hostname: str, os_name: str, role: str,
                      services: dict, description: str = ""):
    db = _get_db()
    svc_json = json.dumps(services, ensure_ascii=False) if services else "{}"
    db.execute(
        """INSERT OR REPLACE INTO nodes(name, ip, hostname, os, role, services, 
           last_heartbeat, status, description) VALUES(?,?,?,?,?,?,?,?,?)""",
        (name, ip, hostname, os_name, role, svc_json, time.time(),
         "online", description))
    db.commit()


def _db_heartbeat(name: str):
    db = _get_db()
    db.execute("UPDATE nodes SET last_heartbeat=?, status='online' WHERE name=?",
               (time.time(), name))
    db.commit()


def _db_get_all_nodes() -> dict:
    db = _get_db()
    cur = db.execute("SELECT name, ip, hostname, os, role, services, last_heartbeat, status, description FROM nodes")
    result = {}
    for r in cur.fetchall():
        name, ip, hostname, os_name, role, svc_json, hb, status, desc = r
        try:
            services = json.loads(svc_json) if svc_json else {}
        except Exception:
            services = {}
        result[name] = {
            "ip": ip, "hostname": hostname, "os": os_name, "role": role,
            "services": services, "last_heartbeat": hb, "status": status,
            "description": desc
        }
    return result


# ═══════════════════════════════════════════
# TCP 健康检查 + 节点管理
# ═══════════════════════════════════════════

def _tcp_check(host: str, port: int, timeout: float = 2) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def _mark_stale_offline(threshold: float = 300):
    """标记300s无心跳节点为离线"""
    db = _get_db()
    cutoff = time.time() - threshold
    db.execute("UPDATE nodes SET status='offline' WHERE last_heartbeat < ? AND status='online'", (cutoff,))
    db.commit()


def _cleanup_stale_nodes(max_age: float = 86400):
    """清理24h无心跳节点"""
    db = _get_db()
    cutoff = time.time() - max_age
    db.execute("UPDATE nodes SET status='removed' WHERE last_heartbeat < ? AND status IN ('offline','unknown')", (cutoff,))
    db.commit()


def _start_cleanup_thread():
    def _cleaner():
        while True:
            time.sleep(60)
            try:
                _mark_stale_offline()
                _cleanup_stale_nodes()
            except Exception:
                pass
    threading.Thread(target=_cleaner, daemon=True).start()


def load_nodes(ttl: float = 15) -> dict:
    """加载节点(15s TTL缓存, 空字段回退基线)"""
    global FEDERATION_NODES
    now = time.time()
    if FEDERATION_NODES and now - getattr(load_nodes, "_ts", 0) < ttl:
        return FEDERATION_NODES
    merged = dict(NODE_BASELINE)
    try:
        db_nodes = _db_get_all_nodes()
        for name, info in db_nodes.items():
            base = merged.get(name, {})
            merged[name] = {
                "ip": info.get("ip") or base.get("ip"),
                "hostname": info.get("hostname") or base.get("hostname"),
                "os": info.get("os") or base.get("os"),
                "role": info.get("role") or base.get("role"),
                "services": info.get("services") or base.get("services", {}),
                "last_heartbeat": info.get("last_heartbeat", 0),
                "status": info.get("status", "unknown"),
                "description": info.get("description", "")
            }
    except Exception:
        pass
    FEDERATION_NODES = merged
    load_nodes._ts = now
    return merged


# ═══════════════════════════════════════════
# 认知层 (保留不变)
# ═══════════════════════════════════════════
_COGNITION_CACHE = {}
_COGNITION_LOADED_AT = 0

def _load_cognition_layer(ttl: float = 300, force: bool = False):
    global _COGNITION_CACHE, _COGNITION_LOADED_AT
    now = time.time()
    if not force and now - _COGNITION_LOADED_AT < ttl:
        return _COGNITION_CACHE
    profiles = []
    try:
        nodes = load_nodes()
        for name, info in nodes.items():
            svcs = info.get("services", {})
            profiles.append({
                "gene_id": f"local-node-{name}",
                "content_preview": f"节点:{name} 角色:{info.get('role','?')} 服务:{len(svcs)}个 IP:{info.get('ip','?')} {info.get('description','')}",
                "score": 1.0,
                "source": "local_registry"
            })
    except Exception as e:
        print(f"[认知层] 本地注册表加载失败: {e}")
    try:
        data = lge_safe_search("federation node gene engine memory", 20)
        for g in data.get("results", [])[:15]:
            profiles.append({
                "gene_id": g.get("gene_id", ""),
                "content_preview": str(g.get("content", ""))[:300],
                "score": g.get("score", 0.5),
                "source": "lge"
            })
    except Exception as e:
        print(f"[认知层] LGE补充加载失败: {e}")
    _COGNITION_CACHE = {"profiles": profiles, "count": len(profiles), "loaded_at": now}
    _COGNITION_LOADED_AT = now
    print(f"[认知层] 已加载 {len(profiles)} 个认知profile")
    return _COGNITION_CACHE


# ═══════════════════════════════════════════
# HTTP + WebSocket 请求处理器
# ═══════════════════════════════════════════

class SearchHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass  # 静默日志

    def do_GET(self):
        # ── WebSocket 升级 ──
        if self.path.startswith("/ws"):
            params = parse_qs(urlparse(self.path).query)
            node_name = params.get("node", [None])[0]
            if not node_name:
                self._json(400, {"error": "需要node参数, 如 /ws?node=天枢"})
                return
            # http.server 用 latin-1 解码 path
            node_name = node_name.encode("latin-1").decode("utf-8")

            if not _ws_handshake(self):
                self._json(400, {"error": "不是合法的WebSocket升级请求"})
                return

            client_id = str(uuid.uuid4())[:6]
            with _WS_LOCK:
                _WS_CLIENTS.setdefault(node_name, []).append((self.wfile, client_id))
            online_count = len(_WS_CLIENTS.get(node_name, []))
            print(f"[WS] {node_name} 客户端 {client_id} 已连接 (WebSocket, 在线:{online_count})")

            # 发送欢迎消息
            welcome = json.dumps({
                "type": "connected",
                "node": node_name,
                "client": client_id,
                "ts": time.strftime("%H:%M:%S"),
                "ws_clients": online_count
            }, ensure_ascii=False)
            _ws_send(self.wfile, welcome.encode("utf-8"), OP_TEXT)

            # ── 消息接收循环 ──
            try:
                while True:
                    frame = _ws_read_frame(self.rfile)
                    if frame is None:
                        break
                    op = frame.get("opcode", 0)
                    if op == OP_CLOSE:
                        # 回复 Close
                        _ws_send(self.wfile, frame.get("payload", b""), OP_CLOSE)
                        break
                    elif op == OP_PING:
                        _ws_send(self.wfile, frame.get("payload", b""), OP_PONG)
                        continue
                    elif op == OP_PONG:
                        continue
                    elif op == OP_TEXT:
                        try:
                            msg = json.loads(frame.get("payload", b"{}").decode("utf-8"))
                        except Exception:
                            _ws_send(self.wfile, json.dumps({"type": "error", "msg": "无效JSON"}).encode(), OP_TEXT)
                            continue
                        # 聊天消息: {type:"chat", from:"天枢", content:"你好"}
                        if msg.get("type") == "chat":
                            chat_from = msg.get("from", "unknown")
                            chat_content = msg.get("content", "")
                            chat_to = msg.get("to", "all")
                            chat_id = str(uuid.uuid4())[:8]
                            ts = time.strftime("%Y-%m-%d %H:%M:%S")
                            # 持久化
                            _db_save(chat_to, chat_id, chat_from, chat_content, ts)
                            # 联邦广播(通过SSE+WS双通道)
                            broadcast_payload = {
                                "id": chat_id, "from": chat_from,
                                "to": chat_to, "content": chat_content,
                                "ts": ts
                            }
                            if chat_to == "all":
                                # 全联邦广播 (WS)
                                _ws_broadcast_all("chat", broadcast_payload, chat_from)
                                # SSE广播: 遍历所有在线节点
                                for n in load_nodes():
                                    if n not in (chat_from,):
                                        threading.Thread(target=_sse_broadcast,
                                                         args=(n, "chat", broadcast_payload),
                                                         daemon=True).start()
                            else:
                                _ws_broadcast(chat_to, "chat", broadcast_payload)
                                threading.Thread(target=_sse_broadcast,
                                                 args=(chat_to, "chat", broadcast_payload),
                                                 daemon=True).start()
                            # 回声给发送者
                            _ws_send(self.wfile, json.dumps({
                                "type": "ack", "id": chat_id,
                                "status": "delivered"
                            }).encode(), OP_TEXT)
                        # 心跳
                        elif msg.get("type") == "ping":
                            _ws_send(self.wfile, json.dumps({"type": "pong", "ts": time.strftime("%H:%M:%S")}).encode(), OP_TEXT)
                    else:
                        # 未知帧, 忽略
                        pass
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with _WS_LOCK:
                    lst = _WS_CLIENTS.get(node_name, [])
                    for item in lst:
                        if item[1] == client_id:
                            lst.remove(item)
                            break
                print(f"[WS] {node_name} 客户端 {client_id} 已断开 (剩余:{len(_WS_CLIENTS.get(node_name,[]))})")
            return  # WS连接结束, 不继续HTTP处理

        # ── HTTP GET 端点 (不变) ──
        if self.path == "/health":
            _mark_stale_offline()
            nodes = load_nodes()
            online = sum(1 for n in nodes.values() if n.get("status") == "online")
            offline = sum(1 for n in nodes.values() if n.get("status") == "offline")
            # WS 连接统计
            with _WS_LOCK:
                ws_total = sum(len(v) for v in _WS_CLIENTS.values())
                ws_nodes = list(_WS_CLIENTS.keys())
            with _SSE_LOCK:
                sse_total = sum(len(v) for v in _SSE_CLIENTS.values())
            self._json(200, {
                "status": "ok",
                "service": "fed-search-bridge-v4.0",
                "version": "4.0.0",
                "websocket": True,
                "ws_clients": ws_total,
                "ws_nodes": ws_nodes,
                "sse_clients": sse_total,
                "nodes": {"total": len(nodes), "online": online, "offline": offline},
                "endpoints": [
                    "GET  /health",
                    "GET  /federation/nodes",
                    "GET  /nodes",
                    "GET  /messages/inbox?node=XXX",
                    "GET  /messages/stream?node=XXX (SSE)",
                    "GET  /messages/health",
                    "GET  /ws?node=XXX  (WebSocket NEW!)",
                    "POST /federated-search",
                    "POST /federated-store",
                    "POST /messages/send",
                    "POST /messages/clear",
                    "POST /register",
                    "POST /heartbeat"
                ],
                "unread_messages": _db_count_unread()
            })

        elif self.path == "/federation/nodes":
            _mark_stale_offline()
            nodes = load_nodes()
            result = {}
            for name, info in nodes.items():
                node = dict(info)
                node["health"] = {}
                svcs = info.get("services", {})
                if isinstance(svcs, list):
                    svcs = {s.split(":")[0]: f"127.0.0.1:{s.split(':')[1]}" for s in svcs if ":" in s}
                for sn, addr in svcs.items():
                    if not isinstance(addr, str) or ":" not in str(addr):
                        continue
                    host, port = addr.rsplit(":", 1)
                    if host in ("127.0.0.1", "localhost"):
                        host = "127.0.0.1"
                    try:
                        node["health"][sn] = "up" if _tcp_check(host, int(port)) else "down"
                    except ValueError:
                        node["health"][sn] = "unknown"
                result[name] = node
            self._json(200, {
                "federation": "LGOX联邦 v1.0",
                "spirit": "遇水架桥，逢山筑路",
                "total_nodes": len(nodes),
                "nodes": result
            })

        elif self.path == "/nodes":
            nodes = load_nodes()
            result = {}
            for name, info in nodes.items():
                node = dict(info)
                node["health"] = {}
                svcs = info.get("services", {})
                if isinstance(svcs, list):
                    svcs = {s.split(":")[0]: f"127.0.0.1:{s.split(':')[1]}" for s in svcs if ":" in s}
                for sn, addr in svcs.items():
                    if not isinstance(addr, str) or ":" not in str(addr):
                        continue
                    host, port = addr.rsplit(":", 1)
                    if host in ("127.0.0.1", "localhost"):
                        host = "127.0.0.1"
                    try:
                        node["health"][sn] = "up" if _tcp_check(host, int(port)) else "down"
                    except ValueError:
                        node["health"][sn] = "unknown"
                result[name] = node
            self._json(200, {"total_nodes": len(nodes), "nodes": result})

        elif self.path.startswith("/messages/inbox"):
            params = parse_qs(urlparse(self.path).query)
            node_name = params.get("node", [None])[0]
            if not node_name:
                self._json(400, {"error": "需要node参数"})
                return
            pending = _db_get_inbox(node_name)
            self._json(200, {"node": node_name, "total_unread": len(pending), "messages": pending})

        elif self.path == "/messages/health":
            report = {}
            for row in _db_all_unread_by_node():
                report[row["node"]] = row["cnt"]
            self._json(200, {"total_unread": sum(report.values()), "per_node": report or {"all_clear": "无未读消息"}})

        elif self.path.startswith("/messages/stream"):
            # SSE 端点 (保留不变)
            params = parse_qs(urlparse(self.path).query)
            node_name = params.get("node", [None])[0]
            if not node_name:
                self._json(400, {"error": "需要node参数"})
                return
            node_name = node_name.encode("latin-1").decode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with _SSE_LOCK:
                _SSE_CLIENTS.setdefault(node_name, []).append(self.wfile)
            client_id = str(uuid.uuid4())[:6]
            print(f"[SSE] {node_name} 客户端 {client_id} 已连接 (在线:{len(_SSE_CLIENTS.get(node_name,[]))})")
            try:
                self.wfile.write(f"event: connected\ndata: {{\"node\":\"{node_name}\",\"client\":\"{client_id}\",\"ts\":\"{time.strftime('%H:%M:%S')}\"}}\n\n".encode())
                self.wfile.flush()
                unread = _db_count_node(node_name)
                self.wfile.write(f"event: status\ndata: {{\"unread\":{unread}}}\n\n".encode())
                self.wfile.flush()
                while True:
                    time.sleep(30)
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with _SSE_LOCK:
                    if node_name in _SSE_CLIENTS and self.wfile in _SSE_CLIENTS[node_name]:
                        _SSE_CLIENTS[node_name].remove(self.wfile)
                print(f"[SSE] {node_name} 客户端 {client_id} 已断开 (剩余:{len(_SSE_CLIENTS.get(node_name,[]))})")

        elif self.path == "/messages/route":
            # 智能路由 (保留不变)
            self._json(400, {"error": "/messages/route 需要POST"})
        else:
            self._json(404, {"error": "not_found", "path": self.path})

    def do_POST(self):
        body = {}
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                raw = self.rfile.read(length)
                body = json.loads(raw) if raw.strip() else {}
        except Exception:
            body = {}

        query = body.get("query", "")
        n_results = body.get("n_results", 5)
        domain = body.get("domain", None)
        cross_domain = body.get("cross_domain", False)

        if self.path == "/federated-search":
            import hashlib as _hl
            _cache_key = _hl.md5(f"{query}|{n_results}|{domain or ''}|{cross_domain}".encode()).hexdigest()
            _now = time.time()
            if _cache_key in _FB_QUERY_CACHE and _now - _FB_QUERY_CACHE[_cache_key]["ts"] < 300:
                self._json(200, _FB_QUERY_CACHE[_cache_key]["data"])
                return

            import concurrent.futures as _cf

            def _route_lge():
                if cross_domain and domain:
                    merged = expand_domain_query(query, domain, max(1, n_results // 3))
                    return {"results": merged.get("results", [])[:n_results],
                            "cross_domain_expanded": merged.get("sources_searched", []),
                            "total_raw": len(merged.get("results", []))}
                lge_r = None
                if _LR is not None and not domain:
                    try:
                        with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                            fut = _ex.submit(_LR.retrieve, query, n=n_results, rerank=True)
                            hits = fut.result(timeout=6)
                        lge_r = {"results": hits, "engine": "authoritative-v1"}
                    except Exception:
                        lge_r = None
                if lge_r is None:
                    _q = f"domain:{domain} {query}" if domain else query
                    lge_r = lge_fts_search(query, n_results)
                    if not lge_r.get("results"):
                        lge_r = lge_safe_search(query, n_results)
                return lge_r

            def _route_onyx():
                try:
                    qs = urllib.parse.urlencode({"query": query, "num_hits": n_results})
                    conn = http.client.HTTPConnection(ONYX_HOST, ONYX_PORT, timeout=4)
                    conn.request("GET", f"/api/chat/search?{qs}",
                                 headers={"Authorization": f"Bearer {ONYX_TOKEN}", "Accept": "application/json"})
                    resp = conn.getresponse()
                    data = json.loads(resp.read())
                    conn.close()
                    return {"results": data.get("results", data if isinstance(data, list) else []), "engine": "onyx"}
                except Exception as e:
                    return {"results": [], "engine": f"onyx-error:{e}"}

            with _cf.ThreadPoolExecutor(max_workers=2) as ex:
                fut_lge = ex.submit(_route_lge)
                fut_onyx = ex.submit(_route_onyx)
                lge_data = fut_lge.result(timeout=8)
                onyx_data = fut_onyx.result(timeout=5)

            lge_genes = lge_data.get("results", [])
            onyx_results = onyx_data.get("results", [])

            # 合并并去重
            seen_ids = set()
            merged = []
            for r in lge_genes:
                gid = r.get("gene_id", str(r.get("content", ""))[:50])
                if gid not in seen_ids:
                    seen_ids.add(gid)
                    merged.append(r)
            for r in onyx_results:
                gid = r.get("document_id", str(r.get("content", ""))[:50])
                if gid not in seen_ids:
                    seen_ids.add(gid)
                    merged.append(dict(r, _source="onyx"))

            result = {
                "query": query,
                "total": len(merged),
                "lge_genes": lge_genes[:n_results],
                "onyx_results": onyx_results[:n_results],
                "results": merged[:n_results * 2],
                "engines": {"lge": lge_data.get("engine", "unknown"),
                            "onyx": onyx_data.get("engine", "unknown")}
            }
            with _FB_QUERY_CACHE_LOCK:
                _FB_QUERY_CACHE[_cache_key] = {"ts": time.time(), "data": result}
            self._json(200, result)

        elif self.path == "/federated-store":
            content = body.get("content", "")
            if not content or len(content) < 5:
                self._json(400, {"error": "内容太短"})
                return
            # 噪声过滤
            noise_kw = ["收到消息", "广播测试", "测试消息", "连通检测", "hello world", "test", "ping"]
            if any(kw in content.lower() for kw in noise_kw):
                self._json(200, {"status": "filtered", "reason": "噪声过滤"})
                return
            try:
                conn = http.client.HTTPConnection("127.0.0.1", 8200, timeout=5)
                conn.request("POST", "/genes/write",
                             json.dumps({"content": content, "memory_type": body.get("memory_type", "semantic"),
                                         "source": body.get("source", "fed-bridge")}),
                             {"Content-Type": "application/json", "X-LGE-Key": LGE_TOKEN})
                resp = conn.getresponse()
                data = json.loads(resp.read())
                conn.close()
                self._json(resp.status, data if resp.status < 400 else {"status": "stored", "raw": str(data)})
            except Exception as e:
                self._json(502, {"error": str(e)})

        elif self.path == "/register":
            name = body.get("name", "")
            if not name:
                self._json(400, {"error": "缺少节点名称"})
                return
            ip = self.client_address[0] if not body.get("ip") and self.client_address[0] != "127.0.0.1" else body.get("ip", self.client_address[0])
            _db_register_node(
                name=name,
                ip=ip,
                hostname=body.get("hostname", ""),
                os_name=body.get("os", ""),
                role=body.get("role", ""),
                services=body.get("services", {}),
                description=body.get("description", "")
            )
            print(f"[注册] {name} ({ip})")
            self._json(200, {"status": "registered", "node": name})

        elif self.path == "/heartbeat":
            name = body.get("name", "")
            if not name:
                self._json(400, {"error": "缺少节点名称"})
                return
            _db_heartbeat(name)
            self._json(200, {"status": "ok", "node": name})

        elif self.path == "/messages/send":
            to_node = body.get("to", "")
            from_node = body.get("from", "天枢")
            content = body.get("content", "")
            if not content or not to_node:
                self._json(400, {"error": "消息内容或目标节点不能为空"})
                return
            msg = {
                "id": str(uuid.uuid4())[:8],
                "from": from_node,
                "to": to_node,
                "content": content,
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "read": False
            }
            # SQLite 持久化
            _db_save(to_node, msg["id"], from_node, content, msg["ts"])
            # LGE 知识留存
            try:
                conn = http.client.HTTPConnection("127.0.0.1", 8200, timeout=3)
                conn.request("POST", "/genes/write",
                             json.dumps({"type": "episodic",
                                         "content": f"[跨节点消息] {from_node}→{to_node}: {content[:500]}",
                                         "source": f"fed-message/{msg['id']}",
                                         "tags": ["cross-node-message", from_node, to_node]}),
                             {"Content-Type": "application/json", "X-LGE-Key": LGE_TOKEN})
                conn.getresponse()
                conn.close()
            except Exception:
                pass
            # 天玑/太一 特殊推送
            if to_node in ("天玑", "太一") or to_node.startswith("天玑-"):
                def _push_to_node(n, msg_content, msg_id):
                    try:
                        conn2 = http.client.HTTPConnection("127.0.0.1", 8200, timeout=3)
                        conn2.request("POST", "/genes/write", json.dumps({
                            "type": "episodic",
                            "content": f"[待收消息] 来自{from_node}: {msg_content[:500]}",
                            "source": f"fed-message/{msg_id}",
                            "tags": ["incoming-message", f"to-{n}"]
                        }), {"Content-Type": "application/json"})
                        conn2.getresponse(); conn2.close()
                    except: pass
                    if n == "天玑":
                        try:
                            pd = json.dumps({"message": f"📩 来自{from_node}: {msg_content[:300]}", "history": []}).encode()
                            conn3 = http.client.HTTPConnection("100.82.185.126", 8089, timeout=3)
                            conn3.request("POST", "/chat", pd, {"Content-Type": "application/json"})
                            conn3.getresponse(); conn3.close()
                        except: pass
                threading.Thread(target=_push_to_node, args=(to_node, content, msg["id"]), daemon=True).start()

            # ── 双通道广播 (SSE + WebSocket) ──
            broadcast_payload = {
                "id": msg["id"], "from": from_node, "to": to_node,
                "content": content, "ts": time.strftime("%H:%M:%S")
            }
            if to_node == "all":
                # 全联邦广播
                # SSE: 遍历所有在线节点
                for n in load_nodes():
                    if n not in (from_node,):
                        threading.Thread(target=_sse_broadcast, args=(n, "message", broadcast_payload), daemon=True).start()
                # WS: 全联邦广播
                _ws_broadcast_all("message", broadcast_payload, from_node)
            else:
                # 定向推送
                threading.Thread(target=_sse_broadcast, args=(to_node, "message", broadcast_payload), daemon=True).start()
                _ws_broadcast(to_node, "message", broadcast_payload)

            self._json(200, {
                "status": "delivered",
                "message_id": msg["id"],
                "to": to_node,
                "from": from_node,
                "ts": msg["ts"],
                "broadcast": "sse+ws"
            })

        elif self.path == "/messages/clear":
            node_name = body.get("node", "")
            if not node_name:
                self._json(400, {"error": "需要node参数"})
                return
            count = _db_clear_inbox(node_name)
            self._json(200, {"status": "ok", "cleared": count, "node": node_name})

        elif self.path == "/api/search":
            try:
                qs = urllib.parse.urlencode({"query": query, "num_hits": n_results})
                conn = http.client.HTTPConnection(ONYX_HOST, ONYX_PORT, timeout=3)
                conn.request("GET", f"/api/chat/search?{qs}",
                             headers={"Authorization": f"Bearer {ONYX_TOKEN}", "Accept": "application/json"})
                resp = conn.getresponse()
                data = json.loads(resp.read())
                conn.close()
                self._json(200, data)
            except Exception as e:
                self._json(502, {"error": str(e)})
        else:
            self._json(404, {"error": "unknown_endpoint", "path": self.path})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


class ThreadingHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    os.system("lsof -ti:8765 | xargs kill -9 2>/dev/null")
    time.sleep(1)
    port = 8765
    load_nodes()
    _start_cleanup_thread()
    server = ThreadingHTTPServer(("0.0.0.0", port), SearchHandler)
    print(f"🔍 联邦搜索桥 v4.0 (WebSocket双通道) 启动: http://localhost:{port}")
    print(f"   {len(load_nodes())} 个联邦节点已注册")
    for name in load_nodes():
        print(f"     - {name}")
    print(f"   GET  /health              -> 健康检查")
    print(f"   GET  /federation/nodes    -> 全节点健康状态")
    print(f"   GET  /nodes               -> 动态注册节点列表")
    print(f"   GET  /messages/inbox?node= -> 获取待收消息")
    print(f"   GET  /messages/stream?node=-> SSE实时推送 (兼容旧客户端)")
    print(f"   GET  /messages/health     -> 未读消息概览")
    print(f"   GET  /ws?node=XXX         -> WebSocket双向通信 🆕")
    print(f"   POST /federated-search    -> 联合搜索(LGE+Onyx)")
    print(f"   POST /federated-store     -> 存储知识到LGE")
    print(f"   POST /messages/send       -> 发送跨节点消息(SSE+WS双通道)")
    print(f"   POST /messages/clear      -> 批量清零节点未读")
    print(f"   POST /register            -> 节点自动注册")
    print(f"   POST /heartbeat           -> 节点心跳")
    _load_cognition_layer()
    def _cog_refresh():
        while True:
            time.sleep(300)
            _load_cognition_layer(force=True)
    threading.Thread(target=_cog_refresh, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
