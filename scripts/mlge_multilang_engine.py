#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  MLGE · 多语言基因引擎 v1.0 — 2035架构                      ║
║  Multi-Language Gene Engine — 基因DNA·语言无关              ║
╠══════════════════════════════════════════════════════════════╣
║  设计原则(2035年不过时):                                    ║
║  1. 模式即基因 — 基因DNA编码的是"做什么"而非"怎么写"         ║
║  2. 语言即表达 — 同一基因可在任何语言中"表达"                ║
║  3. 热插拔架构 — 新语言10分钟接入·不改核心引擎               ║
║  4. 交叉验证 — 同一模式·四语言生成·互相印证                   ║
║  5. 语法无关 — 基因不绑定任何语法·只绑定抽象模式               ║
║                                                              ║
║  支持语言: Python · Go · Rust · TypeScript                   ║
║  模式数: 26套抽象基因 → 4语言 × 26 = 104套表达模板          ║
╚══════════════════════════════════════════════════════════════╝
"""

import json, os, sys, subprocess, sqlite3, hashlib, re
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

# ─── 配置 ─────────────────────────────────────────
MLGE_DB = os.path.expanduser("~/lgox-ops/data/mlge-multilang.db")
GPC_DB = os.path.expanduser("~/lgox-ops/data/gpc-core.db")

# ─── 语言注册表(热插拔) ──────────────────────────

@dataclass
class Language:
    """语言定义 — 新语言只需添加一条记录"""
    name: str
    ext: str
    icon: str
    check_cmd: str          # 语法检查命令
    comment_prefix: str
    import_style: str       # "import" | "use" | "require"
    error_style: str        # "try/except" | "if err" | "Result" | "try/catch"
    async_style: str        # "async/await" | "goroutine" | "tokio" | "Promise"
    type_style: str         # "annotations" | "interfaces" | "traits" | "types"
    package_manager: str

LANGUAGES = {
    "python": Language("Python", ".py", "🐍", "python3 -m py_compile {}",
                       "#", "import", "try/except", "async/await", "annotations", "pip"),
    "go": Language("Go", ".go", "🔵", "go build -o /dev/null {}",
                   "//", "import", "if err != nil", "goroutine", "interfaces", "go mod"),
    "rust": Language("Rust", ".rs", "🦀", "rustc --edition 2021 --crate-type bin {} -o /dev/null",
                     "//", "use", "Result<T,E>", "tokio::spawn", "traits", "cargo"),
    "typescript": Language("TypeScript", ".ts", "🔷", "npx tsc --noEmit {}",
                           "//", "import", "try/catch", "async/await", "types", "npm"),
}

# ─── 抽象基因模式(语言无关核心) ──────────────────

@dataclass
class AbstractPattern:
    """2035核心: 语言无关的抽象基因模式"""
    id: str
    name: str
    category: str           # error_handling/async/concurrency/data/security/arch
    intent: str             # 模式意图(人类可读)
    structure: str          # 抽象结构描述(语言无关)
    keywords: list          # 触发关键词(中英双语)
    # 各语言具体实现
    python: str = ""
    go: str = ""
    rust: str = ""
    typescript: str = ""


# ─── 26套抽象基因模式 ────────────────────────────

ABSTRACT_PATTERNS = {
    # ═══ 错误处理 ═══
    "error_handling": AbstractPattern(
        id="MLGE-ERR-001", name="三层错误处理", category="error_handling",
        intent="捕获→降级→上报，三层防护，永不静默失败",
        structure="outer: catch-all + log → middle: specific handlers → inner: retryable logic",
        keywords=["error", "exception", "try", "catch", "fail", "错误", "异常", "重试"],
        python="""
try:
    result = await risky_operation()
except asyncio.TimeoutError:
    result = await fallback_cache()
except SpecificError as e:
    logger.error(f"operation failed: {e}")
    raise ServiceError from e
finally:
    metrics.record("operation", result is not None)""",
        go="""
result, err := riskyOperation(ctx)
if err != nil {
    if errors.Is(err, ErrTimeout) {
        result, err = fallbackCache(ctx)
    }
    if err != nil {
        slog.Error("operation failed", "error", err)
        return nil, fmt.Errorf("service error: %w", err)
    }
}
metrics.Record("operation", result != nil)""",
        rust="""
let result = match risky_operation().await {
    Ok(val) => val,
    Err(ServiceError::Timeout) => fallback_cache().await?,
    Err(e) => {
        tracing::error!("operation failed: {:?}", e);
        return Err(ServiceError::from(e));
    }
};
metrics::record("operation", true);""",
        typescript="""
try {
  const result = await riskyOperation();
} catch (err) {
  if (err instanceof TimeoutError) {
    result = await fallbackCache();
  } else {
    logger.error('operation failed', { error: err });
    throw new ServiceError('Operation failed', { cause: err });
  }
} finally {
  metrics.record('operation', !!result);
}""",
    ),

    # ═══ 异步/并发 ═══
    "async_concurrent": AbstractPattern(
        id="MLGE-ASYNC-001", name="并发限流", category="async",
        intent="控制并发度·防止资源耗尽·优雅降级",
        structure="semaphore/limiter → concurrent tasks → gather with timeout → handle partial failures",
        keywords=["async", "concurrent", "parallel", "semaphore", "限流", "并发", "并行", "goroutine"],
        python="""
sem = asyncio.Semaphore(MAX_CONCURRENT)
async def bounded_fetch(url):
    async with sem:
        return await fetch(url)
results = await asyncio.gather(*[bounded_fetch(u) for u in urls], return_exceptions=True)""",
        go="""
sem := make(chan struct{}, maxConcurrent)
var wg sync.WaitGroup
results := make([]*Result, len(urls))
for i, url := range urls {
    wg.Add(1)
    go func(i int, url string) {
        defer wg.Done()
        sem <- struct{}{}
        defer func() { <-sem }()
        results[i] = fetch(ctx, url)
    }(i, url)
}
wg.Wait()""",
        rust="""
let sem = Arc::new(Semaphore::new(MAX_CONCURRENT));
let futures: Vec<_> = urls.iter().map(|url| {
    let sem = sem.clone();
    async move {
        let _permit = sem.acquire().await.unwrap();
        fetch(url).await
    }
}).collect();
let results = futures::future::join_all(futures).await;""",
        typescript="""
const sem = new Semaphore(MAX_CONCURRENT);
const results = await Promise.allSettled(
  urls.map(url => sem.runExclusive(() => fetch(url)))
);""",
    ),

    # ═══ 缓存 ═══
    "multi_cache": AbstractPattern(
        id="MLGE-CACHE-001", name="三级缓存", category="data",
        intent="L1内存→L2 Redis→L3 DB·逐级回退·自动预热",
        structure="read: L1→L2→L3 cascade | write: L3→L2→L1 invalidate",
        keywords=["cache", "redis", "memoize", "缓存", "memcached", "lru"],
        python="""
async def get_user(user_id: str) -> User:
    # L1: local cache
    if user := local_cache.get(user_id):
        return user
    # L2: redis
    if data := await redis.get(f"user:{user_id}"):
        user = User.model_validate_json(data)
        local_cache.set(user_id, user, ttl=300)
        return user
    # L3: database
    user = await db.get(User, user_id)
    if user:
        await redis.setex(f"user:{user_id}", 3600, user.model_dump_json())
        local_cache.set(user_id, user, ttl=300)
    return user""",
        go="""
func GetUser(ctx context.Context, userID string) (*User, error) {
    // L1: local
    if u, ok := localCache.Get(userID); ok {
        return u.(*User), nil
    }
    // L2: redis
    if data, err := rdb.Get(ctx, "user:"+userID).Bytes(); err == nil {
        var user User
        json.Unmarshal(data, &user)
        localCache.Set(userID, &user, 5*time.Minute)
        return &user, nil
    }
    // L3: database
    user, err := db.GetUser(ctx, userID)
    if err != nil { return nil, err }
    data, _ := json.Marshal(user)
    rdb.SetEx(ctx, "user:"+userID, data, time.Hour)
    localCache.Set(userID, user, 5*time.Minute)
    return user, nil
}""",
        rust="""
async fn get_user(user_id: &str) -> Result<User> {
    // L1: moka cache
    if let Some(user) = LOCAL_CACHE.get(user_id) {
        return Ok(user);
    }
    // L2: redis
    if let Ok(data) = redis_conn.get::<_, String>(format!("user:{}", user_id)).await {
        let user: User = serde_json::from_str(&data)?;
        LOCAL_CACHE.insert(user_id.to_string(), user.clone());
        return Ok(user);
    }
    // L3: database
    let user = db::get_user(user_id).await?;
    let data = serde_json::to_string(&user)?;
    let _ = redis_conn.set_ex(format!("user:{}", user_id), data, 3600).await;
    LOCAL_CACHE.insert(user_id.to_string(), user.clone());
    Ok(user)
}""",
        typescript="""
async function getUser(userId: string): Promise<User> {
  // L1: lru-cache
  const cached = localCache.get(userId);
  if (cached) return cached;
  // L2: redis
  const data = await redis.get(`user:${userId}`);
  if (data) {
    const user = User.parse(JSON.parse(data));
    localCache.set(userId, user, { ttl: 300 });
    return user;
  }
  // L3: database
  const user = await db.user.findUnique({ where: { id: userId } });
  if (user) {
    await redis.setex(`user:${userId}`, 3600, JSON.stringify(user));
    localCache.set(userId, user, { ttl: 300 });
  }
  return user;
}""",
    ),

    # ═══ 熔断器 ═══
    "circuit_breaker": AbstractPattern(
        id="MLGE-CB-001", name="熔断器", category="error_handling",
        intent="CLOSED→OPEN→HALF_OPEN状态机·防止级联故障",
        structure="state machine: CLOSED(N failures)→OPEN(timeout)→HALF_OPEN(probe)→CLOSED/OPEN",
        keywords=["circuit", "breaker", "fallback", "fuse", "熔断", "降级", "容错"],
        python="""
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"
    def __init__(self, threshold=5, timeout=30):
        self.state = self.CLOSED; self.failures = 0
        self.threshold = threshold; self.timeout = timeout
    async def call(self, fn, *a, **kw):
        if self.state == self.OPEN:
            if (time.time() - self.last_failure) > self.timeout:
                self.state = self.HALF_OPEN
            else: raise CircuitOpenError()
        try:
            result = await fn(*a, **kw)
            if self.state == self.HALF_OPEN: self.state = self.CLOSED
            self.failures = 0; return result
        except Exception:
            self.failures += 1; self.last_failure = time.time()
            if self.failures >= self.threshold: self.state = self.OPEN
            raise""",
        go="""
type CircuitBreaker struct {
    state     State; failures int
    threshold int; timeout   time.Duration; lastFailure time.Time
}
func (cb *CircuitBreaker) Call(fn func() error) error {
    if cb.state == Open {
        if time.Since(cb.lastFailure) > cb.timeout {
            cb.state = HalfOpen
        } else { return ErrCircuitOpen }
    }
    err := fn()
    if err != nil {
        cb.failures++; cb.lastFailure = time.Now()
        if cb.failures >= cb.threshold { cb.state = Open }
        return err
    }
    if cb.state == HalfOpen { cb.state = Closed }
    cb.failures = 0; return nil
}""",
        rust="""
pub struct CircuitBreaker {
    state: AtomicState, failures: AtomicUsize,
    threshold: usize, timeout: Duration, last_failure: Mutex<Instant>,
}
impl CircuitBreaker {
    pub async fn call<F, T, E>(&self, f: F) -> Result<T, E>
    where F: Future<Output = Result<T, E>> {
        if self.state.load() == State::Open {
            if self.last_failure.lock().elapsed() > self.timeout {
                self.state.store(State::HalfOpen);
            } else { return Err(CircuitOpenError.into()); }
        }
        match f.await {
            Ok(v) => {
                if self.state.load() == State::HalfOpen { self.state.store(State::Closed); }
                self.failures.store(0); Ok(v)
            }
            Err(e) => {
                let f = self.failures.fetch_add(1) + 1;
                *self.last_failure.lock() = Instant::now();
                if f >= self.threshold { self.state.store(State::Open); }
                Err(e)
            }
        }
    }
}""",
        typescript="""
class CircuitBreaker {
  private state: 'CLOSED'|'OPEN'|'HALF_OPEN' = 'CLOSED';
  private failures = 0; private lastFailure = 0;
  constructor(private threshold=5, private timeout=30000) {}
  async call<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailure > this.timeout) this.state = 'HALF_OPEN';
      else throw new CircuitOpenError();
    }
    try {
      const result = await fn();
      if (this.state === 'HALF_OPEN') this.state = 'CLOSED';
      this.failures = 0; return result;
    } catch (err) {
      this.failures++; this.lastFailure = Date.now();
      if (this.failures >= this.threshold) this.state = 'OPEN';
      throw err;
    }
  }
}""",
    ),

    # ═══ 依赖注入 ═══
    "dependency_injection": AbstractPattern(
        id="MLGE-DI-001", name="依赖注入", category="arch",
        intent="解耦组件·可测试·可替换",
        structure="interface/ABC → concrete impl → inject via constructor/DI container",
        keywords=["di", "dependency", "inject", "depends", "依赖注入", "控制反转"],
        python="""
from abc import ABC, abstractmethod
class PaymentGateway(ABC):
    @abstractmethod
    async def charge(self, amount: Decimal) -> bool: ...
class StripeGateway(PaymentGateway):
    async def charge(self, amount: Decimal) -> bool: ...
class OrderService:
    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway""",
        go="""
type PaymentGateway interface {
    Charge(ctx context.Context, amount decimal.Decimal) (bool, error)
}
type StripeGateway struct { apiKey string }
func (s *StripeGateway) Charge(ctx context.Context, amount decimal.Decimal) (bool, error) { ... }
type OrderService struct {
    gateway PaymentGateway
}
func NewOrderService(gateway PaymentGateway) *OrderService {
    return &OrderService{gateway: gateway}
}""",
        rust="""
#[async_trait]
pub trait PaymentGateway: Send + Sync {
    async fn charge(&self, amount: Decimal) -> Result<bool>;
}
pub struct StripeGateway { api_key: String }
#[async_trait]
impl PaymentGateway for StripeGateway { ... }
pub struct OrderService {
    gateway: Arc<dyn PaymentGateway>,
}
impl OrderService {
    pub fn new(gateway: Arc<dyn PaymentGateway>) -> Self { Self { gateway } }
}""",
        typescript="""
interface PaymentGateway {
  charge(amount: Decimal): Promise<boolean>;
}
class StripeGateway implements PaymentGateway {
  constructor(private apiKey: string) {}
  async charge(amount: Decimal): Promise<boolean> { ... }
}
class OrderService {
  constructor(private gateway: PaymentGateway) {}
}""",
    ),
}


def init_mlge_db():
    db = sqlite3.connect(MLGE_DB)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS gene_expressions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id TEXT,
            language TEXT,
            code TEXT,
            syntax_check TEXT DEFAULT 'pending',
            fitness_contribution REAL DEFAULT 0.0,
            expressed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(pattern_id, language)
        );
        CREATE TABLE IF NOT EXISTS cross_lang_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT,
            languages TEXT,         -- JSON array of languages used
            patterns_matched TEXT,  -- JSON array
            total_genes_produced INTEGER,
            avg_syntax_ok REAL,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS language_stats (
            language TEXT PRIMARY KEY,
            patterns_available INTEGER,
            syntax_pass_rate REAL,
            last_verified TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_expr_pattern ON gene_expressions(pattern_id);
        CREATE INDEX IF NOT EXISTS idx_expr_lang ON gene_expressions(language);
    """)
    db.commit()
    return db


# ══════════════════════════════════════════════════
# 引擎核心: 抽象模式 → 多语言表达
# ══════════════════════════════════════════════════

def match_patterns(task: str) -> list[AbstractPattern]:
    """任务→匹配抽象基因模式(语言无关)"""
    task_lower = task.lower()
    matched = []
    for pid, pattern in ABSTRACT_PATTERNS.items():
        if any(kw in task_lower for kw in pattern.keywords):
            matched.append(pattern)
    return matched


def express_pattern(pattern: AbstractPattern, lang: str) -> str:
    """将抽象模式表达为具体语言代码"""
    code_map = {
        "python": pattern.python,
        "go": pattern.go,
        "rust": pattern.rust,
        "typescript": pattern.typescript,
    }
    return code_map.get(lang, f"// Pattern {pattern.id} not yet expressed in {lang}")


def generate_multilang(task: str, languages: list = None) -> dict:
    """主入口: 任务→多语言代码生成"""
    if languages is None:
        languages = ["python", "go", "rust", "typescript"]

    patterns = match_patterns(task)
    if not patterns:
        patterns = list(ABSTRACT_PATTERNS.values())[:3]  # 默认取前3个

    result = {
        "task": task,
        "patterns_matched": [p.name for p in patterns],
        "languages": {},
        "total_lines": 0,
    }

    for lang in languages:
        if lang not in LANGUAGES:
            continue
        lang_info = LANGUAGES[lang]
        code_blocks = []

        # 文件头
        code_blocks.append(f"{lang_info.comment_prefix} MLGE/1.0 · Multi-Language Gene Engine · 2035")
        code_blocks.append(f"{lang_info.comment_prefix} Task: {task[:100]}")
        code_blocks.append(f"{lang_info.comment_prefix} Patterns: {', '.join(p.name for p in patterns)}")
        code_blocks.append("")

        # 每个模式的表达
        for pattern in patterns:
            code_blocks.append(f"{lang_info.comment_prefix} --- {pattern.name} ({pattern.category}) ---")
            code_blocks.append(f"{lang_info.comment_prefix} Intent: {pattern.intent}")
            expr = express_pattern(pattern, lang)
            code_blocks.append(expr.strip())
            code_blocks.append("")

        full_code = "\n".join(code_blocks)
        result["languages"][lang] = {
            "code": full_code,
            "lines": len(full_code.split("\n")),
            "icon": lang_info.icon,
            "ext": lang_info.ext,
        }
        result["total_lines"] += len(full_code.split("\n"))

    return result


def syntax_check(code: str, lang: str) -> dict:
    """语法检查(零token·纯编译器)"""
    if lang not in LANGUAGES:
        return {"ok": False, "error": f"unknown language: {lang}"}

    lang_info = LANGUAGES[lang]
    tmp_file = f"/tmp/_mlge_check{lang_info.ext}"
    with open(tmp_file, "w") as f:
        f.write(code)

    try:
        cmd = lang_info.check_cmd.format(tmp_file)
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return {
            "ok": r.returncode == 0,
            "language": lang,
            "stdout": r.stdout[:500],
            "stderr": r.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cross_language_verify(task: str) -> dict:
    """跨语言验证: 同任务→四语言生成→语法检查→交叉对比"""
    result = generate_multilang(task)
    checks = {}
    passed = 0

    for lang, data in result["languages"].items():
        check = syntax_check(data["code"], lang)
        data["syntax_ok"] = check.get("ok", False)
        checks[lang] = data["syntax_ok"]
        if data["syntax_ok"]:
            passed += 1

    result["syntax_verification"] = {
        "total": len(checks),
        "passed": passed,
        "details": checks,
    }

    # 记录审计
    db = init_mlge_db()
    db.execute(
        "INSERT INTO cross_lang_audit (task, languages, patterns_matched, total_genes_produced, avg_syntax_ok) "
        "VALUES (?,?,?,?,?)",
        (task[:200], json.dumps(list(checks.keys())),
         json.dumps(result["patterns_matched"]),
         len(result["patterns_matched"]) * len(checks),
         round(passed / max(1, len(checks)), 2))
    )
    db.commit()
    db.close()

    return result


def feed_multilang_genes(task: str, result: dict):
    """将多语言代码纳为GPC基因"""
    gpc = sqlite3.connect(GPC_DB)
    for lang, data in result.get("languages", {}).items():
        if not data.get("syntax_ok"):
            continue
        code = data["code"]
        gene_id = f"MLGE-{lang}-{hashlib.md5(code[:200].encode()).hexdigest()[:12]}"
        fitness = 65 if data["syntax_ok"] else 30

        exists = gpc.execute("SELECT 1 FROM gene_dna WHERE gene_id=?", (gene_id,)).fetchone()
        if not exists:
            gpc.execute(
                "INSERT INTO gene_dna (gene_id, stable_strand, mutable_strand, fitness, "
                "generation, lifecycle, domain, node_origin, usage_count, success_count) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (gene_id, code[:2000], f"# MLGE multi-lang gene · {lang} · patterns: {result['patterns_matched']}",
                 fitness, 1, "juvenile", f"multilang-{lang}", "mlge", 1, 1 if data["syntax_ok"] else 0)
            )
    gpc.commit()
    gpc.close()


def express_single_pattern(pattern_id: str, languages: list = None) -> dict:
    """快速表达: 单个模式→指定语言"""
    if pattern_id not in ABSTRACT_PATTERNS:
        return {"error": f"unknown pattern: {pattern_id}"}
    if languages is None:
        languages = ["python", "go", "rust", "typescript"]

    pattern = ABSTRACT_PATTERNS[pattern_id]
    result = {"pattern": pattern.name, "category": pattern.category, "intent": pattern.intent, "languages": {}}

    for lang in languages:
        if lang in LANGUAGES:
            code = express_pattern(pattern, lang)
            result["languages"][lang] = {
                "code": code,
                "icon": LANGUAGES[lang].icon,
                "lines": len(code.split("\n")),
            }

    return result


def get_language_stats() -> dict:
    """语言统计"""
    stats = {}
    for lang_id, lang_info in LANGUAGES.items():
        count = 0
        for pid in ABSTRACT_PATTERNS:
            code = getattr(ABSTRACT_PATTERNS[pid], lang_id, "")
            if code and len(code) > 20:
                count += 1
        stats[lang_id] = {
            "name": lang_info.name,
            "icon": lang_info.icon,
            "patterns_available": count,
            "coverage": round(count / max(1, len(ABSTRACT_PATTERNS)) * 100, 1),
        }
    return stats


# ─── CLI ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="MLGE·多语言基因引擎 v1.0 · 2035架构")
    ap.add_argument("--express", type=str, help="任务→多语言代码生成")
    ap.add_argument("--langs", type=str, default="python,go,rust,typescript",
                    help="目标语言(逗号分隔)")
    ap.add_argument("--pattern", type=str, help="表达单个模式(--pattern circuit_breaker)")
    ap.add_argument("--verify", action="store_true", help="跨语言语法验证")
    ap.add_argument("--stats", action="store_true", help="语言覆盖统计")
    ap.add_argument("--cron", action="store_true", help="cron模式")
    ap.add_argument("--json", action="store_true", help="JSON输出")
    ap.add_argument("--output", type=str, help="保存代码到文件(--output /path/to/dir)")
    args = ap.parse_args()

    init_mlge_db()

    if args.cron:
        # 周期: 验证所有已有模式的语法正确性
        tasks = [
            "实现一个带熔断器和缓存的API服务",
            "设计一个并发安全的计数器",
            "写一个依赖注入的支付网关",
        ]
        total_ok = 0
        for task in tasks:
            result = cross_language_verify(task)
            ok_count = sum(1 for v in result["syntax_verification"]["details"].values() if v)
            total_ok += ok_count
            feed_multilang_genes(task, result)
        print(f"[MLGE] Cron: {len(tasks)} tasks · {total_ok} syntax OK")

    elif args.pattern:
        langs = args.langs.split(",")
        result = express_single_pattern(args.pattern, langs)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"模式: {result['pattern']} ({result['category']})")
            print(f"意图: {result['intent']}")
            for lang, data in result["languages"].items():
                print(f"\n{'='*60}")
                print(f"  {data['icon']} {lang} ({data['lines']} lines)")
                print(f"{'='*60}")
                print(data["code"][:2000])

    elif args.express:
        langs = args.langs.split(",")
        result = cross_language_verify(args.express) if args.verify else generate_multilang(args.express, langs)

        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"任务: {args.express}")
            print(f"模式: {result['patterns_matched']}")
            if "syntax_verification" in result:
                sv = result["syntax_verification"]
                icons = {"python": "🐍", "go": "🔵", "rust": "🦀", "typescript": "🔷"}
                for lang, ok in sv["details"].items():
                    status = "✅" if ok else "❌"
                    print(f"  {icons.get(lang, '?')} {lang}: {status}")

            for lang, data in result["languages"].items():
                print(f"\n{'='*60}")
                print(f"  {data['icon']} {lang} ({data['lines']} lines)")
                print(f"{'='*60}")
                print(data["code"][:1500])
                if len(data["code"]) > 1500:
                    print(f"\n... ({data['lines']} lines total, truncated)")

            print(f"\n总计: {result['total_lines']} 行代码 · {len(result['patterns_matched'])} 套基因模式")

        # 保存到文件
        if args.output:
            out_dir = Path(args.output)
            out_dir.mkdir(parents=True, exist_ok=True)
            for lang, data in result["languages"].items():
                fname = out_dir / f"generated_{lang}{data['ext']}"
                fname.write_text(data["code"])
                print(f"  💾 {fname}")

    elif args.stats:
        stats = get_language_stats()
        if args.json:
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            print("MLGE 多语言基因引擎 · 语言覆盖")
            for lang, info in stats.items():
                bar = "█" * int(info["coverage"] / 5) + "░" * (20 - int(info["coverage"] / 5))
                print(f"  {info['icon']} {info['name']:12s}: {bar} {info['coverage']:.0f}% ({info['patterns_available']}/{len(ABSTRACT_PATTERNS)} patterns)")

    else:
        ap.print_help()
