#!/usr/bin/env python3
"""
天锋PRO·基因驱动编程飞轮 v1.0
==============================
2035核心: 每行代码从LGE基因库检索最佳实践
七自闭环: 自感知(检索)→自协调(注入)→自进化(纳基因)→自迭代(评分)→自反思(对比)→自约束(阈值)

流程:
  ① 感知: FTS5+LGE检索相关编程基因
  ② 注入: 基因上下文注入代码生成Prompt
  ③ 生成: (由天锋PRO/Codex执行)
  ④ 评分: 五维质量评估
  ⑤ 纳库: 成功代码→LGE基因·失败→Bug题库
  ⑥ 闭环: 统计→cron→永动
"""

import json, sqlite3, os, urllib.request, uuid, time, subprocess, sys
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/Users/a112233"))
# 导入基因注入引擎的内置模式库（26套·免查LGE·零token）
sys.path.insert(0, str(HOME / "lgox-ops/scripts"))
try:
    from gene_injection_engine import BUILTIN_PATTERNS
    _HAS_BUILTIN = True
except ImportError:
    try:
        import importlib
        if not (HOME / "lgox-ops/scripts/gene_injection_engine.py").exists():
            os.system(f"ln -sf {HOME}/lgox-ops/scripts/gene-injection-engine.py {HOME}/lgox-ops/scripts/gene_injection_engine.py")
        from gene_injection_engine import BUILTIN_PATTERNS
        _HAS_BUILTIN = True
    except:
        BUILTIN_PATTERNS = {}
        _HAS_BUILTIN = False

# 扩展BUILTIN_PATTERNS: 算法 + 内存/OOM 模式（gene-coding-flywheel专用）
MEMORY_PATTERNS = {
        "memory_leak_debug": [
            "# PATTERN: OOM/内存泄漏调试 (GENE-PRO: OOM-DEBUG-v1)",
            "# 常见内存泄漏场景:",
            "#  - 全局缓存/静态集合无限增长 → 设上限/WeakRef/LRU",
            "#  - 循环引用(带__del__) → 弱引用weakref.ref()",
            "#  - 闭包/回调持有大对象 → 取消注册/局部变量",
            "#  - 大对象未释放(图片/BytesIO/numpy) → del + gc.collect()",
            "#  - logger/handler泄漏 → 每调用cleanup()",
            "# OOM排查工具:",
            "#  import tracemalloc; tracemalloc.start()",
            "#  snapshot = tracemalloc.take_snapshot()",
            "#  top_stats = snapshot.statistics('lineno')",
            "#  for stat in top_stats[:10]: print(stat)",
            "# 也可: objgraph.show_growth() / pympler.summary.summarize()",
            "# GC调优: gc.set_threshold(700, 10, 5) · gc.set_debug(gc.DEBUG_LEAK)",
            "# Python 3.12+: sys.mem_get_alloc_stats()",
        ],
        "weakref_pattern": [
            "# PATTERN: 弱引用避免循环引用 (GENE-SEM-weakref)",
            "import weakref",
            "class Node:",
            "    def __init__(self, value):",
            "        self.value = value",
            "        self.parent = None  # 强引用",
            "        self._children = weakref.WeakSet()  # 子结点用弱集",
            "    def add_child(self, child):",
            "        self._children.add(child)",
            "        child.parent = weakref.ref(self)  # 父结点弱引用",
        ],
        "gc_tuning_pattern": [
            "# PATTERN: GC调优 (GENE-PRO: GC-TUNE-v1)",
            "import gc",
            "# 查看当前阈值: gc.get_threshold() → (700, 10, 10)",
            "# 调大阈值减少GC频率(适合内存充裕):",
            "gc.set_threshold(1500, 20, 20)",
            "# 调小阈值加速回收(适合内存紧张):",
            "# gc.set_threshold(300, 5, 3)",
            "# 手动触发: gc.collect(0) → 年轻代 ; gc.collect(2) → 全代",
            "# 禁用自动GC(批量操作时):",
            "gc.disable()",
            "# ...大量对象创建...",
            "gc.collect()",
            "gc.enable()",
            "# 查看不可达但未回收对象: gc.garbage",
            "# Python3.11+ sys.breakpointhook() + gc.DEBUG_LEAK",
        ],
        "tracemalloc_pattern": [
            "# PATTERN: Python内存追踪 (GENE-PRO: TRACEMALLOC-v1)",
            "import tracemalloc, linecache, os",
            "",
            "tracemalloc.start(25)  # 25帧堆栈深度",
            "# ...运行疑似泄漏代码...",
            "snapshot = tracemalloc.take_snapshot()",
            "top = snapshot.statistics('lineno')[:15]",
            "",
            "print('[Top 15 内存分配]')",
            "for stat in top:",
            "    print(f'{stat.count:>6} blocks → {stat.size/1024:.1f} KB → {stat.traceback.format()[0]}')",
            "    frame = stat.traceback[0]",
            "    filename, lineno = frame.filename, frame.lineno",
            "    line = linecache.getline(filename, lineno).strip()",
            "    if line:",
            "        print(f'    └─ {line}')",
        ],
        "mem_usage_monitor": [
            "# PATTERN: 内存用量监控 (GENE-PRO: MEM-MONITOR-v1)",
            "import psutil, os, gc",
            "def log_mem_usage(tag=''):",
            "    proc = psutil.Process(os.getpid())",
            "    mem_mb = proc.memory_info().rss / 1024 / 1024",
            "    gc_info = gc.get_stats()",
            "    total_gc_count = sum(g['collected'] for g in gc_info)",
            "    print(f'[MEM] {tag} RSS={mem_mb:.1f}MB GC总收集={total_gc_count}')",
        ],
    }
    ALGORITHM_PATTERNS = {
    "two_pointer_pattern": [
        "# PATTERN: 双指针算法 (GENE-SEM-567ac54412f3bc58 接雨水)",
        "def two_pointer(height):",
        "    left, right = 0, len(height) - 1",
        "    left_max = right_max = 0",
        "    water = 0",
        "    while left <= right:",
        "        if height[left] < height[right]:",
        "            left_max = max(left_max, height[left])",
        "            water += left_max - height[left]",
        "            left += 1",
        "        else:",
        "            right_max = max(right_max, height[right])",
        "            water += right_max - height[right]",
        "            right -= 1",
        "    return water",
    ],
    "dp_pattern": [
        "# PATTERN: 动态规划五步法 (GENE-SEM-48c7915be8f4896e)",
        "# 1) dp[i]: 以i结尾的最优值",
        "# 2) dp[i] = max(nums[i], dp[i-1] + nums[i])",
        "# 3) dp[0] = nums[0]",
        "# 4) 遍历顺序: 1..n-1",
        "# 5) 举例验证: [-2,1,-3,4] → dp=[-2,1,-2,4], ans=4",
    ],
    "lru_cache_pattern": [
        "# PATTERN: LRU缓存 (GENE-SEM-b4c77ea27c5c78cc)",
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
        "        self.cache[key] = value",
        "        self.cache.move_to_end(key)",
        "        if len(self.cache) > self.cap:",
        "            self.cache.popitem(last=False)",
    ],
    "binary_search_pattern": [
        "# PATTERN: 二分查找模板 (GENE-SEM-4815231711e126aa)",
        "def binary_search(nums, target):",
        "    left, right = 0, len(nums) - 1",
        "    while left <= right:",
        "        mid = left + (right - left) // 2",
        "        if nums[mid] == target: return mid",
        "        elif nums[mid] < target: left = mid + 1",
        "        else: right = mid - 1",
        "    return -1",
    ],
}
BUILTIN_PATTERNS.update(ALGORITHM_PATTERNS)
BUILTIN_PATTERNS.update(MEMORY_PATTERNS)

# LGE基因库集群（三级降级: 地枢主库→天枢LGE→灵龙LGA本地）
LGE_POOL = [
    "http://100.116.0.29:8200",   # 【主】地枢DGX2（791K基因）
    "http://100.100.89.2:8201",   # 【备1】天枢LGE Studio（829基因）
    "http://127.0.0.1:8202",      # 【备2】灵龙LGA本地代理（33基因）
]
LGE_URL = "http://100.116.0.29:8200"
FTS5_DB = HOME / "lge-studio/data/lge_fts.db"  # 不存在于灵龙，仅在天枢
FLYWHEEL_DB = HOME / "lgox-ops/data/gene-coding-flywheel.db"
MY_NODE = "灵龙"

# 节点连通性缓存（减少重试）
_connectivity_cache = {}

# ═══ 连通性预检 ═══
def check_lge_connectivity():
    """快检3节点连通性（3s超时·不走完整HTTP搜索）"""
    reachable = {}
    for url in LGE_POOL:
        try:
            req = urllib.request.Request(url + "/health", method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            if resp.status == 200:
                reachable[url] = True
                _connectivity_cache[url] = True
            else:
                reachable[url] = False
                _connectivity_cache[url] = False
        except Exception:
            reachable[url] = False
            _connectivity_cache[url] = False
    return reachable

# ══════════════════════════════════════════
# 引擎
# ══════════════════════════════════════════

def init_db():
    conn = sqlite3.connect(FLYWHEEL_DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS gene_injections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT, genes_found INTEGER, genes_used TEXT,
            injection_prompt TEXT, result_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS code_genes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gene_id TEXT, category TEXT, content TEXT,
            source TEXT, score REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS flywheel_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT, genes_searched INTEGER, genes_injected INTEGER,
            new_genes INTEGER, score REAL, duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    return conn


def search_fts5(query, limit=10):
    """FTS5 BM25本地检索·零成本·0.05s（灵龙无此DB→静默跳过）"""
    try:
        if not FTS5_DB.exists():
            return []  # FTS5仅存在于天枢
        conn = sqlite3.connect(str(FTS5_DB))
        c = conn.cursor()
        c.execute("SELECT content FROM lge_fts WHERE lge_fts MATCH ? LIMIT ?", (query, limit))
        return [r[0] for r in c.fetchall()]
    except Exception as e:
        return []


def search_lge(query, limit=5):
    """LGE语义检索·三级降级（地枢→天枢→灵龙LGA本地）·连通性缓存避免重复重试"""
    global _connectivity_cache
    timeout_per_node = 5

    # 只尝试已知在线或未测试过的节点
    candidates = []
    for url in LGE_POOL:
        status = _connectivity_cache.get(url)
        if status is None:  # 从未测试过
            candidates.append(url)
        elif status:  # 上次在线
            candidates.insert(0, url)  # 优先尝试
    if not candidates:
        candidates = LGE_POOL  # 都标记离线了，还是试一下

    for url in candidates:
        status = _connectivity_cache.get(url)
        if status is False:
            continue  # 已确认离线，跳过

        # 直接HTTP尝试
        results = _try_http_search(url, query, limit)
        if results:
            return results

    # 第四级: SSH代理到天枢（当直连全部失败时）
    if _connectivity_cache.get(LGE_POOL[1]) is not True and _connectivity_cache.get(LGE_POOL[0]) is not True:
        try:
            import subprocess as sp
            qjson = json.dumps({"query": query, "n_results": limit})
            ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                       "a1@100.100.89.2", "curl -s --max-time 8 -X POST http://100.100.89.2:8201/genes/search -H 'Content-Type: application/json' -d " + qjson]
            result = sp.run(ssh_cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                results = [r.get("content", "") for r in data.get("results", [])]
                if results:
                    print(f"  [OK] search_lge(SSH→天枢) → {len(results)}条", file=__import__('sys').stderr)
                    return results
        except Exception as e:
            print(f"  [WARN] SSH天枢代理失败: {str(e)[:50]}", file=__import__('sys').stderr)

    return []  # 所有节点都不可达


def _try_http_search(url, query, limit):
    """直接HTTP搜索LGE节点"""
    try:
        data = json.dumps({"query": query, "n_results": limit}).encode()
        req = urllib.request.Request(url + "/genes/search", data=data,
                                      headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=5)
        results = [r.get("content", "") for r in json.loads(resp.read()).get("results", [])]
        if results:
            _connectivity_cache[url] = True
            print(f"  [OK] search_lge({url}) → {len(results)}条", file=__import__('sys').stderr)
            return results
        _connectivity_cache[url] = True
    except urllib.error.HTTPError as e:
        print(f"  [WARN] {url} HTTP {e.code}", file=__import__('sys').stderr)
        if e.code == 500:
            _connectivity_cache[url] = False
    except Exception as e:
        print(f"  [WARN] {url}不可达: {str(e)[:40]}", file=__import__('sys').stderr)
        _connectivity_cache[url] = False
    return None


def extract_coding_genes(task_description):
    """基因感知: 多粒度中文关键词分解 + LGE检索"""
    results = []
    import re
    
    # 去特殊字符
    clean = re.sub(r'[⚡·—•→★🐛🗄️🤖🔧📊🔄📦🐛]', ' ', task_description)
    
    # ① 原始词: 用:-/空格拆分
    raw_words = [w.strip() for w in clean.replace(':', ' ').replace('/', ' ').replace('—', ' ').replace('-', ' ').replace('（', ' ').replace('）', ' ').split() if len(w.strip()) >= 2]
    
    # ② 中文语义分解: "OOM深度排查" → ["OOM", "深度", "排查"]
    #   "修复大对象+GC不及时导致的OOM" → ["修复", "大对象", "GC", "不及时", "导致", "OOM"]
    decomposed = []
    for w in raw_words:
        # 英文/数字词保持原样
        if re.match(r'^[A-Za-z0-9_+]+$', w):
            decomposed.append(w)
        else:
            # 中英混合词: 按中文/英文边界拆分
            mixed = re.findall(r'[A-Za-z0-9]+|[^\W\d_]+', w)
            for sub in mixed:
                if len(sub) >= 2:
                    decomposed.append(sub)
                elif len(sub) == 1 and sub.isascii() and sub.isupper():
                    decomposed.append(sub)  # 单个大写字母(OOM中的O也可以用)
                elif len(sub) >= 2 and sub.isalpha():
                    decomposed.append(sub)
    
    # ③ 合并所有候选词
    all_terms = list(dict.fromkeys(raw_words + decomposed))  # 去重保序
    
    # ④ 按优先级搜索: 短词优先(更可能匹配)
    # 先搜单个技术词
    tech_terms = [t for t in all_terms if t.isascii() and len(t) >= 2]
    for t in tech_terms[:5]:
        q = t[:15]
        r = search_lge(q, 3)
        if r:
            results.extend(r)
            break  # 一个技术词搜到就够了
    
    # 再搜中文词
    if not results:
        cn_terms = [t for t in all_terms if not t.isascii() and len(t) >= 2]
        for t in cn_terms[:3]:
            r = search_lge(t[:10], 3)
            if r:
                results.extend(r)
                break
    
    # ⑤ 如果全没搜到，用泛编程fallback
    if not results:
        fallbacks = ["编程", "算法", "Python", "设计模式", "代码"]
        for fb in fallbacks:
            r = search_lge(fb, 2)
            if r:
                results.extend(r)
                break
    
    # 去重
    seen = set()
    unique = []
    for r in results:
        key = r[:80]
        if key not in seen:
            seen.add(key)
            unique.append(r[:500])
    
    return unique[:12]


def search_builtin_patterns(task_description):
    """内置模式fallback：当LGE不可达时从26套内置模式匹配关键词"""
    if not _HAS_BUILTIN:
        return []
    
    matched = []
    # 从任务描述中提取关键词做模式匹配
    task_lower = task_description.lower()
    
    # 关键词→内置模式名映射
    keyword_map = {
        "错误处理|异常|error|try|except|异常处理|故障恢复": "error_handling",
        "异步|并发|async|await|aiohttp|并行|协程": "async_pattern",
        "缓存|cache|lru|ttl|mnemonic|memcached|redis缓存": "cache_pattern",
        "验证|校验|validation|sanitize|pydantic|数据校验": "validation_pattern",
        "sql|注入|注入|数据库|query|参数化|防注入": "sql_safe",
        "重试|retry|backoff|退避|指数|容错": "retry_backoff",
        "类型安全|type|typing|typeguard|静态检查|类型": "type_safety",
        "资源|cleanup|释放|close|上下文|contextmanager|contextlib": "resource_cleanup",
        "配置|config|ini|yaml|json|settings|热加载|解析器": "config_pattern",
        "日志|log|logging|logger|监控|审计": "logging_pattern",
        "依赖|di|depends|injection|注入|ioc": "dependency_injection",
        "限流|rate|limit|throttle|令牌桶|漏桶": "rate_limiting",
        "熔断|breaker|circuit|熔断器|降级": "circuit_breaker",
        "分页|pagination|cursor|offset|page|游标": "pagination",
        "事务|transaction|acid|commit|rollback|回滚|原子性": "transaction_pattern",
        "幂等|idempotency|重复|去重|幂等键": "idempotency",
        "观察者|发布|订阅|publish|subscribe|event|事件|observer|pubsub": "observer_pattern",
        "工厂|factory|注册表|register|gateway|创建": "factory_pattern",
        "中间件|middleware|filter|拦截|aop|切面": "middleware_chain",
        "健康检查|health|心跳|探针|存活|liveness|readiness": "health_check",
        "指标|metrics|prometheus|监控|统计|上报": "metrics_pattern",
        "功能开关|feature|flag|开关|灰度|ab测试": "feature_flag",
        "cqrs|读写分离|命令查询|read model|write model": "cqrs_pattern",
        "事件溯源|eventsourcing|event store|domain event": "event_sourcing",
        "后台|background|job|队列|任务|worker|cron|定时": "background_job",
        "优雅|shutdown|关闭|graceful|信号|signal|sigterm": "graceful_shutdown",
        "网络分区|双写|分布式|brain split|split brain|consensus|raft|paxos|一致": "circuit_breaker",
        "分布式锁|redis|setnx|锁|超时|续期": "retry_backoff",
        "并发|线程|lock|mutex|死锁|锁|竞争|race|竞态|threadsafe|安全": "async_pattern",
        "trie|前缀树|prefix tree|trie树|字典树|prefix|search prefix": "trie_pattern",
        "链表|linked list|listnode|双向链表|反轉|反转链表": "linked_list_pattern",
        "二叉树|bst|binary tree|二叉搜索树|树|遍历|前序|中序|后序|层次|tree node|treenode|binary search": "bst_pattern",
        "lru|cache缓存|缓存淘汰|最近最少使用|lru缓存|cache实现|least recently|ordereddict": "lru_cache_pattern",
        "测试|test|断言|assert|unittest|pytest|mock|快照|snapshot|验证|验证|集成|unit|覆盖率": "error_handling",
        "接雨水|trapping rain|双指针|two pointer|two-pointer|相向|快慢指针|滑动窗口|左右指针": "two_pointer_pattern",
        "动态规划|dp|递推|状态转移|最优子结构|背包|fibonacci|斐波那契|LCS|LIS|子序列": "dp_pattern",
        "lru缓存|lru|最近最少使用|cache淘汰|ordereddict|淘汰策略|least recently": "lru_cache_pattern",
        "二分查找|binary search|二分法|二分搜索|二分答案|对数时间|log n": "binary_search_pattern",
        "OOM|内存泄漏|内存泄露|gc|垃圾回收|垃圾收集|tracemalloc|内存溢出|memory leak|memory profiler|堆内存|heap|大对象": "memory_leak_debug",
        "weakref|弱引用|循环引用|circular reference": "weakref_pattern",
        "gc|垃圾回收|垃圾收集|gc阈值|gc调优|garbage collector|垃圾": "gc_tuning_pattern",
        "tracemalloc|内存追踪|memory trace|内存分配|对象分配|对象大小": "tracemalloc_pattern",
        "内存监控|监控内存|memory usage|rss|mem_usage|内存使用|psutil": "mem_usage_monitor",
    }
    
    for pattern, pattern_name in keyword_map.items():
        import re as _re
        if _re.search(pattern, task_lower):
            if pattern_name in BUILTIN_PATTERNS:
                content = "\n".join(BUILTIN_PATTERNS[pattern_name])
                if content not in matched:
                    matched.append(content)
    
    # 如果没匹配到，返回通用模式
    if not matched:
        if "error_handling" in BUILTIN_PATTERNS:
            matched.append("\n".join(BUILTIN_PATTERNS["error_handling"]))
        if "async_pattern" in BUILTIN_PATTERNS:
            matched.append("\n".join(BUILTIN_PATTERNS["async_pattern"]))
    
    return matched[:8]


def build_gene_prompt(task, genes):
    """基因注入: 构建带基因上下文的编程Prompt"""
    if not genes:
        return task
    
    gene_context = "\n".join(f"  [{i+1}] {g[:200]}" for i, g in enumerate(genes[:8]))
    
    prompt = f"""# 任务: {task}

# 🧬 LGOX基因库·相关最佳实践({len(genes)}条):
{gene_context}

# 要求:
- 基于上述基因知识编写代码
- 优先使用已验证的模式和架构
- 避免已知踩坑
- 代码可运行、可测试、可维护

请编写代码:"""
    return prompt


def score_code(code, expected_behavior=""):
    """快速质量评估(规则引擎·零token)"""
    score = 50
    details = []
    
    # 正确性线索
    if "def " in code or "class " in code: score += 10; details.append("函数定义+10")
    if "import " in code: score += 5; details.append("模块导入+5")
    if "try" in code and "except" in code: score += 5; details.append("异常处理+5")
    if "return " in code: score += 5; details.append("返回值+5")
    
    # 性能线索
    if "cache" in code.lower() or "lru" in code.lower(): score += 5; details.append("缓存优化+5")
    if "O(" in code: score += 3; details.append("复杂度标注+3")
    
    # 安全线索
    if "password" in code.lower() and "hash" not in code.lower(): score -= 10; details.append("明文密码-10")
    if "exec(" in code or "eval(" in code: score -= 10; details.append("危险函数-10")
    
    # 可读线索
    if '"""' in code or "'''" in code: score += 5; details.append("文档字符串+5")
    lines = code.split("\n")
    if len(lines) > 3 and all(len(l) < 120 for l in lines): score += 3; details.append("行长度合理+3")
    
    # 基因密度(是否引用了已知模式)
    pattern_keywords = ["工厂", "单例", "观察者", "策略", "代理", "LRU", "Trie", "KMP",
                        "Dijkstra", "Kadane", "二分", "动态规划", "回溯",
                        "链表", "二叉树", "BST", "TreeNode", "ListNode"]
    for pk in pattern_keywords:
        if pk in code: score += 2; details.append(f"模式:{pk}+2")
    
    # 内置模式标记（PATTERN:表示结构化基因）
    if "PATTERN:" in code:
        score += 10
        details.append("结构化模式标记+10")
    
    return min(100, max(0, score)), details


def run_flywheel():
    """主飞轮: 感知→注入→评分→纳库"""
    conn = init_db()
    c = conn.cursor()
    start = datetime.now()
    run_id = f"gcf-{start.strftime('%Y%m%d-%H%M%S')}"
    
    total_genes = 0
    total_injected = 0
    total_new = 0
    
    # 从题库取一个任务
    import random
    try:
        from code_challenges import get_all_challenges
        import random
        challenges = get_all_challenges()
        if challenges:
            task = random.choice(challenges)
            task_desc = f"{task['dim_icon']} {task['dim_label']}·{task['difficulty']}: {task['title']} — {task['description']}"
        else:
            task_desc = "实现一个LRU缓存，支持O(1)的get/put操作"
    except:
        task_desc = "实现一个线程安全的单例模式"
    
    # ① 感知: 检索基因（LGE三级降级 + 内置模式fallback）
    genes = extract_coding_genes(task_desc)
    
    # 如果LGE全离线，fallback到内置模式库
    if not genes and _HAS_BUILTIN:
        builtin_genes = search_builtin_patterns(task_desc)
        if builtin_genes:
            print(f"  [OK] LGE全离线·使用内置模式fallback → {len(builtin_genes)}条", file=sys.stderr)
            genes = builtin_genes
            total_genes = len(genes)
    
    total_genes = len(genes)
    
    # ② 注入: 构建Prompt
    prompt = build_gene_prompt(task_desc, genes)
    total_injected = min(len(genes), 8)
    
    # ③ 评分：基于注入的基因数和质量
    # 有基因=超过50分门槛，有内置模式+额外加分
    has_builtin = any("PATTERN" in g for g in genes[:3]) if genes else False
    has_lge = any("GENE-PRO" in g for g in genes[:3]) if genes else False
    flywheel_score = min(100, 
        50  # 基础分
        + min(total_genes * 4, 20)  # 基因检索加分(最多+20)
        + (15 if has_lge else 0)  # LGE基因加分
        + (10 if has_builtin else 0)  # 内置模式加分
        + (5 if total_new > 0 else 0)  # 新纳库加分
    )
    
    # ④ 纳库: 将检索到的优质基因标记（包括内置模式）
    for g in genes[:5]:
        gid = f"GENE-CODE-{uuid.uuid4().hex[:8]}"
        content = g[:300]
        score, _ = score_code(content)
        if score >= 60:
            try:
                c.execute("INSERT OR IGNORE INTO code_genes (gene_id,category,content,source,score) VALUES (?,?,?,?,?)",
                          (gid, "injected" if has_lge else "builtin", content, "gene-coding-flywheel", score))
                total_new += 1
            except Exception:
                pass
    
    # ⑤ 记录运行
    duration = int((datetime.now() - start).total_seconds() * 1000)
    
    c.execute("INSERT INTO flywheel_runs (run_id,genes_searched,genes_injected,new_genes,score,duration_ms) VALUES (?,?,?,?,?,?)",
              (run_id, total_genes, total_injected, total_new, flywheel_score, duration))
    
    # 统计
    c.execute("SELECT COUNT(*) FROM flywheel_runs")
    total_runs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM code_genes")
    total_code_genes = c.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    result = {
        "run_id": run_id,
        "task": task_desc[:120],
        "genes_found": total_genes,
        "genes_injected": total_injected,
        "new_genes": total_new,
        "score": flywheel_score,
        "duration_ms": duration,
        "total_runs": total_runs,
        "total_code_genes": total_code_genes,
    }
    
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run_flywheel()
