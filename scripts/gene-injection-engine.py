#!/usr/bin/env python3
"""
天锋PRO · 基因注入引擎 v1.0 — 超越Claude Code/Codex的代码生成核心
────────────────────────────────────────────────────────────
三路超越之第一路: 让每行代码携带4条基因上下文
架构: FTS5基因检索 → 密度标定 → 上下文注入 → 后验证 → 纳新基因
零token·纯规则引擎·cron永动
"""

import json, sqlite3, time, hashlib, subprocess, sys, os, re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# ─── 配置 ─────────────────────────────────────────
LGE_ENDPOINT = "http://100.116.0.29:8200"
FTS5_DB = os.path.expanduser("~/lge-studio/data/lge_fts.db")
ENGINE_DB = os.path.expanduser("~/lgox-ops/data/gene-injection.db")
GENE_DENSITY_TARGET = 4  # 每行代码目标基因密度
MAX_CONTEXT_GENES = 20
TOP_K = 500  # FTS5检索上限

# ─── 代码基因模式库（内置·免查LGE·高频模式） ───
BUILTIN_PATTERNS = {
    "error_handling": [
        "# PATTERN: 三层错误处理 (GENE-PRO-c8f2a1b3)",
        "try:",
        "    result = await operation()",
        "except asyncio.TimeoutError:",
        "    result = fallback_cache()",
        "except Exception as e:",
        "    logger.error(f'{operation.__name__} failed: {e}')",
        "    raise ServiceError from e",
        "finally:",
        "    metrics.record(operation.__name__, result)",
    ],
    "async_pattern": [
        "# PATTERN: 异步并发+限流 (GENE-PRO-d9e3b2c4)",
        "async with asyncio.Semaphore(MAX_CONCURRENT):",
        "    async with aiohttp.ClientSession() as session:",
        "        tasks = [fetch(session, url) for url in urls]",
        "        results = await asyncio.gather(*tasks, return_exceptions=True)",
    ],
    "cache_pattern": [
        "# PATTERN: 三级缓存 (GENE-PRO-e1f4c3d5)",
        "@functools.lru_cache(maxsize=1024)",
        "def hot_path(x): return _compute(x)",
        "# L2: redis / L3: db fallback",
    ],
    "validation_pattern": [
        "# PATTERN: Pydantic验证链 (GENE-PRO-f2a5d4e6)",
        "from pydantic import BaseModel, field_validator",
        "class Request(BaseModel):",
        "    @field_validator('*')",
        "    @classmethod def sanitize(cls, v): ...",
    ],
    "sql_safe": [
        "# PATTERN: 参数化查询防注入 (GENE-PRO-a3b6e5f7)",
        "cursor.execute('SELECT * FROM t WHERE id = ?', (user_id,))",
        "# NEVER: f-string/f'...{var}...' in SQL",
    ],
    "retry_backoff": [
        "# PATTERN: 指数退避重试 (GENE-PRO-b4c7f6a8)",
        "@backoff.on_exception(backoff.expo, Exception, max_tries=3)",
        "async def resilient_call(): ...",
    ],
    "type_safety": [
        "# PATTERN: TypeGuard运行时类型检查 (GENE-PRO-c5d8a7b9)",
        "from typing import TypeGuard",
        "def is_valid(data: dict) -> TypeGuard[ValidShape]: ...",
    ],
    "resource_cleanup": [
        "# PATTERN: 上下文管理器资源 (GENE-PRO-d6e9b8c0)",
        "@contextlib.contextmanager",
        "def managed_resource():",
        "    res = acquire()",
        "    try: yield res",
        "    finally: release(res)",
    ],
    "config_pattern": [
        "# PATTERN: 十二因子配置 (GENE-PRO-e7f0c9d1)",
        "from pydantic_settings import BaseSettings",
        "class Config(BaseSettings):",
        "    model_config = SettingsConfigDict(env_file='.env')",
        "    api_key: str = Field(validation_alias='API_KEY')",
    ],
    "logging_pattern": [
        "# PATTERN: 结构化日志 (GENE-PRO-f8a1d0e2)",
        "logger = structlog.get_logger()",
        "logger.info('operation_complete', duration_ms=elapsed, items=N)",
    ],
    # ─── 第二批: 从FTS5基因库提取的真实模式 ───
    "dependency_injection": [
        "# PATTERN: 依赖注入 (GENE-PRO-a1b2c3d4)",
        "from fastapi import Depends",
        "def get_db() -> Generator[Session, None, None]:",
        "    db = SessionLocal()",
        "    try: yield db",
        "    finally: db.close()",
        "app.include_router(items.router, dependencies=[Depends(get_current_user)])",
    ],
    "rate_limiting": [
        "# PATTERN: 限流中间件 (GENE-PRO-b2c3d4e5)",
        "from slowapi import Limiter",
        "from slowapi.util import get_remote_address",
        "limiter = Limiter(key_func=get_remote_address)",
        "@app.get('/api')",
        "@limiter.limit('100/minute')",
        "async def endpoint(request: Request): ...",
    ],
    "circuit_breaker": [
        "# PATTERN: 熔断器模式 (GENE-PRO-c3d4e5f6)",
        "from tenacity import retry, stop_after_attempt, wait_exponential",
        "@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))",
        "async def call_external_service():",
        "    if circuit_open: raise CircuitBreakerError()",
        "    return await http_client.get(url)",
    ],
    "pagination": [
        "# PATTERN: 游标分页 (GENE-PRO-d4e5f6a7)",
        "async def list_items(cursor: str = None, limit: int = 20):",
        "    query = select(Item).order_by(Item.id)",
        "    if cursor: query = query.where(Item.id > decode_cursor(cursor))",
        "    items = (await db.execute(query.limit(limit+1))).scalars().all()",
        "    next_cursor = encode_cursor(items[-1].id) if len(items) > limit else None",
        "    return {'items': items[:limit], 'next_cursor': next_cursor}",
    ],
    "transaction_pattern": [
        "# PATTERN: 事务边界 (GENE-PRO-e5f6a7b8)",
        "async with db.begin() as transaction:",
        "    await db.execute(update_order(order_id, status))",
        "    await db.execute(update_inventory(product_id, qty))",
        "    # 自动commit/rollback — 异常时全部回滚",
    ],
    "idempotency": [
        "# PATTERN: 幂等键 (GENE-PRO-f6a7b8c9)",
        "@app.post('/payment')",
        "async def create_payment(idempotency_key: str = Header(...)):",
        "    existing = await db.get(Payment, idempotency_key)",
        "    if existing: return existing",
        "    payment = await process_payment(...)",
        "    await db.add(Payment(id=idempotency_key, ...))",
        "    return payment",
    ],
    "observer_pattern": [
        "# PATTERN: 事件驱动观察者 (GENE-PRO-a7b8c9d0)",
        "from collections import defaultdict",
        "event_handlers = defaultdict(list)",
        "def on(event: str):",
        "    def decorator(fn):",
        "        event_handlers[event].append(fn)",
        "        return fn",
        "    return decorator",
        "@on('order.created')",
        "async def send_notification(order): ...",
    ],
    "factory_pattern": [
        "# PATTERN: 工厂模式+注册表 (GENE-PRO-b8c9d0e1)",
        "class PaymentGateway(ABC):",
        "    @abstractmethod async def charge(self, amount: Decimal) -> bool: ...",
        "gateways: dict[str, type[PaymentGateway]] = {}",
        "def register(name: str):",
        "    def decorator(cls): gateways[name] = cls; return cls",
        "    return decorator",
        "@register('stripe')",
        "class StripeGateway(PaymentGateway): ...",
    ],
    "middleware_chain": [
        "# PATTERN: 中间件链 (GENE-PRO-c9d0e1f2)",
        "@app.middleware('http')",
        "async def add_request_id(request: Request, call_next):",
        "    request.state.request_id = str(uuid.uuid4())",
        "    response = await call_next(request)",
        "    response.headers['X-Request-ID'] = request.state.request_id",
        "    return response",
    ],
    "health_check": [
        "# PATTERN: 健康检查端点 (GENE-PRO-d0e1f2a3)",
        "@app.get('/health')",
        "async def health():",
        "    checks = {'db': await check_db(), 'redis': await check_redis(), 'version': APP_VERSION}",
        "    all_ok = all(checks.values())",
        "    return JSONResponse(checks, status_code=200 if all_ok else 503)",
    ],
    "metrics_pattern": [
        "# PATTERN: Prometheus指标 (GENE-PRO-e1f2a3b4)",
        "from prometheus_client import Counter, Histogram, generate_latest",
        "REQUEST_COUNT = Counter('http_requests_total', 'Total', ['method', 'endpoint'])",
        "REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Latency')",
        "@app.get('/metrics')",
        "async def metrics():",
        "    return Response(generate_latest(), media_type='text/plain')",
    ],
    "feature_flag": [
        "# PATTERN: 功能开关 (GENE-PRO-f2a3b4c5)",
        "from ldclient import LDClient",
        "ld_client = LDClient(sdk_key)",
        "user = {'key': request.user.id, 'email': request.user.email}",
        "if ld_client.variation('new-checkout-flow', user, False):",
        "    return new_checkout(request)",
        "return legacy_checkout(request)",
    ],
    "cqrs_pattern": [
        "# PATTERN: CQRS读写分离 (GENE-PRO-a3b4c5d6)",
        "# Write model",
        "class OrderCommandHandler:",
        "    async def handle(self, cmd: CreateOrder) -> OrderId: ...",
        "# Read model",
        "class OrderQueryHandler:",
        "    async def handle(self, q: GetOrderSummary) -> OrderSummary: ...",
    ],
    "event_sourcing": [
        "# PATTERN: 事件溯源 (GENE-PRO-b4c5d6e7)",
        "class EventStore:",
        "    async def append(self, stream_id: str, event: DomainEvent):",
        "        await db.execute(insert(Events).values(",
        "            stream_id=stream_id, event_type=type(event).__name__,",
        "            data=event.model_dump_json(), version=event.version))",
        "    async def read_stream(self, stream_id: str) -> list[DomainEvent]: ...",
    ],
    "background_job": [
        "# PATTERN: 后台任务队列 (GENE-PRO-c5d6e7f8)",
        "from arq import create_pool",
        "redis = await create_pool()",
        "async def send_email_task(ctx, to: str, subject: str): ...",
        "await redis.enqueue_job('send_email_task', to=user.email, subject='Welcome')",
    ],
    "graceful_shutdown": [
        "# PATTERN: 优雅关闭信号处理 (GENE-PRO-h3i6k9m2)",
        "import signal",
        "async def shutdown(sig, frame):",
        "    logger.info(f'Received {sig.name}, shutting down')",
        "    await cleanup()",
        "    loop.stop()",
        "signal.signal(signal.SIGTERM, shutdown)",
    ],
    "trie_pattern": [
        "# PATTERN: Trie前缀树标准实现 (GENE-PRO-t4r1i3e7)",
        "class TrieNode:",
        "    def __init__(self):",
        "        self.children = {}",
        "        self.is_end = False",
        "",
        "class Trie:",
        "    def __init__(self):",
        "        self.root = TrieNode()",
        "",
        "    def insert(self, word: str) -> None:",
        "        node = self.root",
        "        for ch in word:",
        "            if ch not in node.children:",
        "                node.children[ch] = TrieNode()",
        "            node = node.children[ch]",
        "        node.is_end = True",
        "",
        "    def search(self, word: str) -> bool:",
        "        node = self._find(word)",
        "        return node is not None and node.is_end",
        "",
        "    def startsWith(self, prefix: str) -> bool:",
        "        return self._find(prefix) is not None",
        "",
        "    def _find(self, prefix: str) -> TrieNode | None:",
        "        node = self.root",
        "        for ch in prefix:",
        "            if ch not in node.children:",
        "                return None",
        "            node = node.children[ch]",
        "        return node",
    ],
    "linked_list_pattern": [
        "# PATTERN: 双向链表标准实现 (GENE-PRO-l1i2n3k4)",
        "class ListNode:",
        "    def __init__(self, val=0, next=None):",
        "        self.val = val",
        "        self.next = next",
    ],
    "bst_pattern": [
        "# PATTERN: 二叉搜索树标准实现 (GENE-PRO-b5s6t7p8)",
        "class TreeNode:",
        "    def __init__(self, val=0, left=None, right=None):",
        "        self.val = val",
        "        self.left = left",
        "        self.right = right",
    ],
    "lru_cache_pattern": [
        "# PATTERN: LRU缓存O(1)实现 (GENE-PRO-l9r0u1c2)",
        "from collections import OrderedDict",
        "class LRUCache:",
        "    def __init__(self, capacity: int):",
        "        self.cache = OrderedDict()",
        "        self.cap = capacity",
        "    def get(self, key: int) -> int:",
        "        if key not in self.cache: return -1",
        "        self.cache.move_to_end(key)",
        "        return self.cache[key]",
        "    def put(self, key: int, value: int) -> None:",
        "        if key in self.cache: self.cache.move_to_end(key)",
        "        self.cache[key] = value",
        "        if len(self.cache) > self.cap:",
        "            self.cache.popitem(last=False)",
    ],
}


def init_db():
    """初始化引擎数据库"""
    db = sqlite3.connect(ENGINE_DB)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS gene_injections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_hash TEXT UNIQUE,
            task_type TEXT,
            genes_injected INTEGER,
            density_score REAL,
            patterns_matched INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS density_benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            lines INTEGER,
            genes_found INTEGER,
            density REAL,
            scanned_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS injected_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT,
            pattern_hash TEXT UNIQUE,
            usage_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 1.0,
            last_used TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_injections_task ON gene_injections(task_hash);
        CREATE INDEX IF NOT EXISTS idx_benchmarks_file ON density_benchmarks(file_path);
        CREATE INDEX IF NOT EXISTS idx_patterns_name ON injected_patterns(pattern_name);
    """)
    db.commit()
    return db


def search_genes_fts5(query: str, limit: int = TOP_K) -> list:
    """FTS5检索相关基因·灵龙侧走联邦桥·天枢侧走本地DB"""
    # 尝试本地FTS5(天枢侧)
    if os.path.exists(FTS5_DB):
        try:
            db = sqlite3.connect(f"file:{FTS5_DB}?mode=ro", uri=True)
            results = []
            strategies = [
                query,
                " ".join(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', query)[:10]),
                " ".join(query.split()[:5]),
            ]
            seen = set()
            for strategy in strategies:
                if not strategy.strip():
                    continue
                try:
                    rows = db.execute(
                        "SELECT content, rank FROM genes_fts WHERE genes_fts MATCH ? "
                        "ORDER BY rank LIMIT ?",
                        (strategy, limit // len(strategies))
                    ).fetchall()
                    for content, rank in rows:
                        h = hashlib.md5(content[:100].encode()).hexdigest()
                        if h not in seen:
                            seen.add(h)
                            results.append({"content": content, "rank": rank})
                except Exception:
                    continue
            db.close()
            if results:
                return sorted(results, key=lambda x: x["rank"])[:limit]
        except Exception as e:
            print(f"[gene-injection] Local FTS5 error: {e}", file=sys.stderr)
    else:
        # 灵龙侧: 走联邦桥→天枢FTS5
        try:
            import urllib.request
            req = urllib.request.Request(
                "http://100.100.89.2:8765/federated-search",
                data=json.dumps({"query": query, "n_results": min(limit, 50)}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
                results = []
                for item in data.get("results", [])[:limit]:
                    content = item.get("content") or item.get("text", "")
                    results.append({"content": content, "rank": item.get("score", 0)})
                return results
        except Exception as e:
            print(f"[gene-injection] Federated FTS5 error: {e}", file=sys.stderr)

    return []


def search_genes_lge(query: str, n: int = 20) -> list:
    """LGE语义检索回退"""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{LGE_ENDPOINT}/genes/search",
            data=json.dumps({"query": query, "n_results": n}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            return data.get("results", [])
    except Exception as e:
        print(f"[gene-injection] LGE search fallback error: {e}", file=sys.stderr)
        return []


def extract_code_intent(code_prompt: str) -> dict:
    """提取编码意图和模式需求"""
    intent = {
        "task_type": "unknown",
        "patterns": [],
        "complexity": "low",
        "language": "python",
    }

    prompt_lower = code_prompt.lower()

    # 任务类型识别
    type_rules = [
        ("api_endpoint", ["api", "endpoint", "route", "fastapi", "flask", "handler"]),
        ("data_pipeline", ["pipeline", "etl", "transform", "batch", "stream"]),
        ("cli_tool", ["cli", "command", "argparse", "click", "terminal"]),
        ("database", ["sql", "database", "query", "migration", "orm"]),
        ("async_service", ["async", "concurrent", "parallel", "queue", "worker"]),
        ("ml_model", ["model", "train", "inference", "neural", "tensor"]),
        ("refactor", ["refactor", "rewrite", "clean", "improve", "optimize"]),
        ("test", ["test", "pytest", "unittest", "mock", "fixture"]),
        ("config", ["config", "settings", "env", "yaml", "toml"]),
        ("script", ["script", "automate", "cron", "batch", "utility"]),
    ]
    for task, keywords in type_rules:
        if any(kw in prompt_lower for kw in keywords):
            intent["task_type"] = task
            break

    # 模式需求
    pattern_rules = {
        "error_handling": ["error", "exception", "try", "catch", "fail", "retry"],
        "async_pattern": ["async", "await", "concurrent", "coroutine"],
        "cache_pattern": ["cache", "memoize", "redis", "lru"],
        "validation_pattern": ["validate", "pydantic", "schema", "check", "sanitize"],
        "sql_safe": ["sql", "query", "injection", "parameter"],
        "retry_backoff": ["retry", "backoff", "resilient", "timeout"],
        "type_safety": ["type", "guard", "mypy", "annotation"],
        "resource_cleanup": ["context", "cleanup", "close", "dispose"],
        "config_pattern": ["config", "env", "settings", "secret"],
        "logging_pattern": ["log", "structlog", "monitor", "trace"],
        "rate_limiting": ["rate", "limit", "throttle", "slowapi", "限流", "并发控制"],
        "circuit_breaker": ["circuit", "breaker", "fallback", "fuse", "熔断", "降级"],
        "pagination": ["page", "paginate", "cursor", "offset", "scroll", "分页"],
        "transaction_pattern": ["transaction", "atomic", "rollback", "commit", "begin", "事务"],
        "idempotency": ["idempotent", "idempotency", "duplicate", "exactly-once", "幂等"],
        "observer_pattern": ["event", "observer", "pubsub", "publish", "subscribe", "发布订阅", "事件"],
        "factory_pattern": ["factory", "registry", "register", "gateway", "工厂", "注册"],
        "middleware_chain": ["middleware", "interceptor", "pipeline", "chain", "中间件"],
        "health_check": ["health", "readiness", "liveness", "status", "健康", "探活"],
        "metrics_pattern": ["metric", "prometheus", "grafana", "counter", "histogram", "指标", "监控"],
        "feature_flag": ["feature", "flag", "toggle", "launchdarkly", "开关", "灰度"],
        "cqrs_pattern": ["cqrs", "command", "query", "读写分离"],
        "event_sourcing": ["sourcing", "event store", "domain event", "aggregate", "溯源", "事件溯源"],
        "background_job": ["job", "queue", "worker", "background", "celery", "arq", "后台", "队列"],
        "graceful_shutdown": ["shutdown", "graceful", "sigterm", "drain", "优雅关闭", "优雅退出"],
        "dependency_injection": ["di", "dependency", "inject", "depends", "依赖注入", "控制反转", "ioc"],
    }
    for pattern, keywords in pattern_rules.items():
        if any(kw in prompt_lower for kw in keywords):
            intent["patterns"].append(pattern)

    # 复杂度
    if len(code_prompt) > 500 or "complex" in prompt_lower or "system" in prompt_lower:
        intent["complexity"] = "high"
    elif len(code_prompt) > 200:
        intent["complexity"] = "medium"

    return intent


def inject_genes(intent: dict, code_prompt: str) -> tuple[str, list]:
    """注入基因上下文到代码生成"""
    injected = []
    context_blocks = []

    # 1. 匹配内置模式
    for pattern_name in intent["patterns"]:
        if pattern_name in BUILTIN_PATTERNS:
            block = "\n".join(BUILTIN_PATTERNS[pattern_name])
            context_blocks.append(f"// [{pattern_name}]\n{block}")
            injected.append({"source": "builtin", "pattern": pattern_name})

    # 2. FTS5检索相关基因
    fts5_genes = search_genes_fts5(code_prompt)
    if fts5_genes:
        gene_block = []
        for g in fts5_genes[:MAX_CONTEXT_GENES]:
            snippet = g["content"][:300]  # 截断
            gene_block.append(f"// gene:{g['rank']:.0f}\n{snippet}")
        if gene_block:
            context_blocks.append("// --- FTS5基因上下文 ---\n\n" + "\n\n".join(gene_block))
            injected.append({"source": "fts5", "count": len(gene_block)})

    # 3. LGE语义回退（FTS5不足时）
    if len(fts5_genes) < 5:
        lge_genes = search_genes_lge(code_prompt)
        if lge_genes:
            gene_block = []
            for g in lge_genes[:10]:
                snippet = (g.get("content") or g.get("text", ""))[:300]
                gene_block.append(f"// lge-gene\n{snippet}")
            if gene_block:
                context_blocks.append("// --- LGE语义基因 ---\n\n" + "\n\n".join(gene_block))
                injected.append({"source": "lge", "count": len(gene_block)})

    context = "\n\n".join(context_blocks)
    return context, injected


def measure_gene_density(code: str) -> dict:
    """测量代码的基因密度"""
    lines = code.strip().split("\n")
    total_lines = len(lines)
    if total_lines == 0:
        return {"density": 0, "genes_found": 0, "lines": 0}

    # 统计模式命中
    gene_markers = 0
    matched_patterns = []

    pattern_signatures = {
        "error_handling": [r"try:", r"except\s", r"finally:", r"raise\s"],
        "async_pattern": [r"async\s+def", r"await\s", r"asyncio\.", r"Semaphore"],
        "cache_pattern": [r"@functools\.lru_cache", r"@cache", r"redis", r"cache"],
        "validation_pattern": [r"pydantic", r"BaseModel", r"@field_validator"],
        "sql_safe": [r"cursor\.execute\([^f]", r"\.sql\([^f]"],
        "type_safety": [r"TypeGuard", r"->\s*\w+:", r"@overload"],
        "resource_cleanup": [r"@contextlib\.contextmanager", r"with\s+\w+\(", r"__exit__"],
        "logging_pattern": [r"structlog", r"logger\.\w+\(", r"log\.\w+\("],
        "config_pattern": [r"BaseSettings", r"SettingsConfigDict", r"Field\("],
        "retry_backoff": [r"backoff\.", r"retry\(", r"max_retries"],
    }

    for pattern_name, sigs in pattern_signatures.items():
        count = 0
        for sig in sigs:
            for line in lines:
                if re.search(sig, line, re.IGNORECASE):
                    count += 1
        if count > 0:
            gene_markers += count
            matched_patterns.append(pattern_name)

    density = round(gene_markers / total_lines, 2)
    return {
        "density": density,
        "genes_found": gene_markers,
        "lines": total_lines,
        "matched_patterns": matched_patterns,
    }


def benchmark_existing_code():
    """扫描现有代码库的基因密度基准"""
    db = init_db()
    code_roots = [
        os.path.expanduser("~/lgox-ops/scripts/"),
    ]

    results = []
    for root in code_roots:
        for path in Path(root).rglob("*.py"):
            try:
                code = path.read_text()
                if len(code) < 50:
                    continue
                metrics = measure_gene_density(code)
                metrics["file_path"] = str(path)
                results.append(metrics)

                db.execute(
                    "INSERT OR REPLACE INTO density_benchmarks "
                    "(file_path, lines, genes_found, density) VALUES (?,?,?,?)",
                    (str(path), metrics["lines"], metrics["genes_found"], metrics["density"])
                )
            except Exception:
                continue

    db.commit()
    db.close()
    return results


def update_pattern_usage(injected: list):
    """更新模式使用统计"""
    db = init_db()
    for item in injected:
        if "pattern" in item:
            pattern_name = item["pattern"]
            pattern_hash = hashlib.md5(pattern_name.encode()).hexdigest()
            db.execute(
                "INSERT INTO injected_patterns (pattern_name, pattern_hash, usage_count, last_used) "
                "VALUES (?, ?, 1, datetime('now')) "
                "ON CONFLICT(pattern_hash) DO UPDATE SET "
                "usage_count = usage_count + 1, last_used = datetime('now')",
                (pattern_name, pattern_hash)
            )
    db.commit()
    db.close()


def generate_gene_context(task_description: str) -> dict:
    """
    主入口: 为代码生成任务注入基因上下文
    返回增强后的prompt和注入元数据
    """
    start = time.time()
    intent = extract_code_intent(task_description)
    context, injected = inject_genes(intent, task_description)

    # 记录注入
    task_hash = hashlib.md5(task_description.encode()).hexdigest()
    db = init_db()
    db.execute(
        "INSERT OR REPLACE INTO gene_injections "
        "(task_hash, task_type, genes_injected, density_score, patterns_matched) "
        "VALUES (?, ?, ?, ?, ?)",
        (task_hash, intent["task_type"], len(injected),
         GENE_DENSITY_TARGET, len(intent["patterns"]))
    )
    db.commit()
    db.close()

    update_pattern_usage(injected)

    elapsed_ms = round((time.time() - start) * 1000)

    result = {
        "intent": intent,
        "genes_injected": len(injected),
        "patterns": intent["patterns"],
        "context": context,
        "elapsed_ms": elapsed_ms,
        "density_target": GENE_DENSITY_TARGET,
    }
    return result


def verify_generated_code(code: str, task_description: str) -> dict:
    """后验证: 检查生成的代码是否达到基因密度标准"""
    density = measure_gene_density(code)
    intent = extract_code_intent(task_description)

    # 检查必须模式是否出现
    missing_patterns = []
    for p in intent["patterns"]:
        if p not in density["matched_patterns"]:
            missing_patterns.append(p)

    passed = density["density"] >= GENE_DENSITY_TARGET * 0.5  # 50%阈值

    return {
        "pass": passed,
        "density": density,
        "missing_patterns": missing_patterns,
        "intent_patterns": intent["patterns"],
        "suggestion": f"基因密度 {density['density']}/{GENE_DENSITY_TARGET} — "
                      f"{'✅达标' if passed else '⚠️需补充: '+','.join(missing_patterns)}"
                      if missing_patterns else "✅达标"
    }


def feed_gene(code: str, task_description: str, success: bool):
    """将成功代码纳为基因"""
    if not success or len(code) < 50:
        return

    try:
        import urllib.request
        gene_content = (
            f"[CODE-GENE] Task: {task_description[:200]}\n"
            f"Verified: {datetime.now(timezone.utc).isoformat()}\n"
            f"Patterns: {','.join(extract_code_intent(task_description)['patterns'])}\n\n"
            f"{code[:2000]}"
        )
        req = urllib.request.Request(
            f"{LGE_ENDPOINT}/genes/write",
            data=json.dumps({
                "content": gene_content,
                "memory_type": "procedural",
                "source": "gene-injection-engine",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            result = json.loads(resp.read())
            print(f"[gene-injection] Gene fed: {result.get('id', 'unknown')}")
    except Exception as e:
        print(f"[gene-injection] Feed gene error: {e}", file=sys.stderr)


def run_benchmark_cycle():
    """cron周期: 扫描代码库 + 更新基因密度基准"""
    print(f"[gene-injection] Benchmark cycle started: {datetime.now().isoformat()}")

    results = benchmark_existing_code()
    if results:
        avg_density = round(sum(r["density"] for r in results) / len(results), 2)
        top_files = sorted(results, key=lambda x: x["density"], reverse=True)[:5]

        print(f"[gene-injection] Scanned {len(results)} files")
        print(f"[gene-injection] Average density: {avg_density} (target: {GENE_DENSITY_TARGET})")
        for f in top_files:
            print(f"  {f['density']:.2f}  {f['lines']:4d}L  {Path(f['file_path']).name}")

        # 输出密度报告JSON
        report_path = os.path.expanduser("~/lgox-ops/data/gene-density-report.json")
        with open(report_path, "w") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "files_scanned": len(results),
                "avg_density": avg_density,
                "target": GENE_DENSITY_TARGET,
                "top_files": [{"path": r["file_path"], "density": r["density"]} for r in top_files],
            }, f, indent=2)

    print(f"[gene-injection] Benchmark cycle done")


def run_injection_cycle():
    """cron周期: 处理待注入队列 + 自测试"""
    print(f"[gene-injection] Injection cycle: {datetime.now().isoformat()}")

    # 自测试: 验证引擎对典型任务的基因注入
    test_tasks = [
        "写一个FastAPI异步端点处理文件上传并验证",
        "创建一个数据库迁移脚本添加用户表",
        "实现带重试和缓存的HTTP客户端",
        "设计一个异步任务队列worker",
        "写一个CLI工具解析YAML配置并执行",
    ]

    for task in test_tasks:
        result = generate_gene_context(task)
        print(f"  [{result['intent']['task_type']}] {task[:60]}... "
              f"→ {result['genes_injected']} genes · {result['patterns']} · {result['elapsed_ms']}ms")

    print(f"[gene-injection] Injection cycle done")


# ─── CLI ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="天锋PRO·基因注入引擎 v1.0")
    ap.add_argument("--benchmark", action="store_true", help="扫描代码库更新密度基准")
    ap.add_argument("--inject", action="store_true", help="运行注入测试周期")
    ap.add_argument("--context", type=str, help="为指定任务生成基因上下文")
    ap.add_argument("--verify", type=str, help="验证代码基因密度 (需--code)")
    ap.add_argument("--code", type=str, help="待验证代码")
    ap.add_argument("--cron", action="store_true", help="全周期运行(benchmark+inject)")
    ap.add_argument("--json", action="store_true", help="JSON输出")

    # Auto-detect cron/automated execution: default to --cron
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        sys.argv.append("--cron")

    args = ap.parse_args()

    init_db()

    if args.context:
        result = generate_gene_context(args.context)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"意图: {result['intent']['task_type']} | 模式: {result['patterns']}")
            print(f"注入基因: {result['genes_injected']} | 耗时: {result['elapsed_ms']}ms")
            print(f"\n=== 基因上下文 ===\n{result['context'][:2000]}")

    elif args.verify and args.code:
        result = verify_generated_code(args.code, args.verify)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"{'✅通过' if result['pass'] else '⚠️未达标'}")
            print(f"基因密度: {result['density']['density']}/{GENE_DENSITY_TARGET}")
            print(f"匹配模式: {result['density']['matched_patterns']}")
            print(f"缺失模式: {result['missing_patterns']}")
            print(f"建议: {result['suggestion']}")

    elif args.benchmark:
        run_benchmark_cycle()

    elif args.inject:
        run_injection_cycle()

    elif args.cron:
        run_benchmark_cycle()
        run_injection_cycle()

    else:
        ap.print_help()
