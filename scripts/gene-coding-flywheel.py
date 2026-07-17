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
# ─── 导入基因注入引擎的内置模式库（高频模式·免查LGE·零token）
# 注意：保存本地定义的补充模式，避免被import覆盖
sys.path.insert(0, str(HOME / "lgox-ops/scripts"))
try:
    from gene_injection_engine import BUILTIN_PATTERNS as _IMPORTED_PATTERNS
    _HAS_BUILTIN = True
except ImportError:
    try:
        import importlib
        if not (HOME / "lgox-ops/scripts/gene_injection_engine.py").exists():
            os.system(f"ln -sf {HOME}/lgox-ops/scripts/gene-injection-engine.py {HOME}/lgox-ops/scripts/gene_injection_engine.py")
        from gene_injection_engine import BUILTIN_PATTERNS as _IMPORTED_PATTERNS
        _HAS_BUILTIN = True
    except:
        _IMPORTED_PATTERNS = {}
        _HAS_BUILTIN = False
BUILTIN_PATTERNS = dict(_IMPORTED_PATTERNS)  # Start with imported patterns
# Merge with locally-defined patterns (attention, memory, algorithms)
_ATTENTION_PATTERNS = {

    "attention_scaled_dot_product": [
        "# PATTERN: Scaled Dot-Product Attention (GENE-PRO-ATTN-v1)",
        "import numpy as np",
        "",
        "def scaled_dot_product_attention(Q, K, V, mask=None):",
        "    \"\"\"",
        "    Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V",
        "    Args:",
        "        Q: Query tensor (batch, seq_len, d_k)",
        "        K: Key tensor   (batch, seq_len, d_k)",
        "        V: Value tensor (batch, seq_len, d_v)",
        "        mask: Optional mask (batch, seq_len) for causal/padding",
        "    Returns:",
        "        output: (batch, seq_len, d_v)",
        "        weights: attention_weights (batch, seq_len, seq_len)",
        "    \"\"\"",
        "    d_k = Q.shape[-1]",
        "    # QK^T · scale by 1/sqrt(d_k) for stable gradients",
        "    scores = np.matmul(Q, K.transpose(0, 2, 1)) / np.sqrt(d_k)",
        "    ",
        "    if mask is not None:",
        "        # causal mask: upper triangular → -inf (so softmax zeros them)",
        "        # padding mask: bool → 0 for keep, large neg for ignore",
        "        scores = np.where(mask, scores, -1e9)",
        "    ",
        "    # Softmax along last axis (attention over keys)",
        "    exp_scores = np.exp(scores - np.max(scores, axis=-1, keepdims=True))",
        "    weights = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)",
        "    ",
        "    # Weighted sum of values",
        "    output = np.matmul(weights, V)",
        "    return output, weights",
        "",
        "# PyTorch version (GPU-friendly)",
        "import torch",
        "import torch.nn.functional as F",
        "",
        "def attention_torch(Q, K, V, mask=None, dropout_p=0.0):",
        "    d_k = Q.size(-1)",
        "    scores = torch.matmul(Q, K.transpose(-2, -1)) / (d_k ** 0.5)",
        "    if mask is not None:",
        "        scores = scores.masked_fill(mask == 0, float('-inf'))",
        "    attn_weights = F.dropout(F.softmax(scores, dim=-1), p=dropout_p)",
        "    return torch.matmul(attn_weights, V), attn_weights",
        "",
        "# 乘法效率比较: QK^T O(n²·d) vs 滑动窗口 O(n·w·d)",
        "# 优化技巧:",
        "#  - Flash Attention: 分块计算softmax减少显存 O(n) instead of O(n²)",
        "#  - 对长序列(>2048)用稀疏/滑动窗口/线性attention",
    ],
    "multi_head_attention": [
        "# PATTERN: Multi-Head Attention (GENE-PRO-MHA-v1)",
        "class MultiHeadAttention:",
        "    \"\"\"多头注意力: 将Q/K/V投影到h个头, 并行计算, 拼接输出\"\"\"",
        "    def __init__(self, d_model, num_heads, dropout=0.0):",
        "        assert d_model % num_heads == 0",
        "        self.d_k = d_model // num_heads",
        "        self.num_heads = num_heads",
        "        self.W_q = np.random.randn(d_model, d_model) * 0.02",
        "        self.W_k = np.random.randn(d_model, d_model) * 0.02",
        "        self.W_v = np.random.randn(d_model, d_model) * 0.02",
        "        self.W_o = np.random.randn(d_model, d_model) * 0.02",
        "        self.dropout = dropout",
        "",
        "    def forward(self, Q, K, V, mask=None):",
        "        batch_size = Q.shape[0]",
        "        ",
        "        # Linear projections + reshape to (batch, heads, seq, d_k)",
        "        Q = np.dot(Q, self.W_q).reshape(batch_size, -1, self.num_heads, self.d_k).transpose(0, 2, 1, 3)",
        "        K = np.dot(K, self.W_k).reshape(batch_size, -1, self.num_heads, self.d_k).transpose(0, 2, 1, 3)",
        "        V = np.dot(V, self.W_v).reshape(batch_size, -1, self.num_heads, self.d_k).transpose(0, 2, 1, 3)",
        "        ",
        "        # Scaled dot-product attention per head",
        "        out, weights = scaled_dot_product_attention(Q, K, V, mask)",
        "        ",
        "        # Concatenate heads + final projection",
        "        out = out.transpose(0, 2, 1, 3).reshape(batch_size, -1, self.num_heads * self.d_k)",
        "        return np.dot(out, self.W_o), weights",
        "",
        "# PyTorch高效实现",
        "class MultiHeadAttentionTorch(torch.nn.Module):",
        "    def __init__(self, d_model, num_heads, dropout=0.0):",
        "        super().__init__()",
        "        self.W_q = torch.nn.Linear(d_model, d_model)",
        "        self.W_k = torch.nn.Linear(d_model, d_model)",
        "        self.W_v = torch.nn.Linear(d_model, d_model)",
        "        self.W_o = torch.nn.Linear(d_model, d_model)",
        "        self.dropout = torch.nn.Dropout(dropout)",
        "        self.num_heads = num_heads",
        "        self.d_k = d_model // num_heads",
        "    def forward(self, Q, K, V, mask=None):",
        "        B = Q.size(0)",
        "        Q = self.W_q(Q).view(B, -1, self.num_heads, self.d_k).transpose(1, 2)",
        "        K = self.W_k(K).view(B, -1, self.num_heads, self.d_k).transpose(1, 2)",
        "        V = self.W_v(V).view(B, -1, self.num_heads, self.d_k).transpose(1, 2)",
        "        attn_out, _ = attention_torch(Q, K, V, mask, self.dropout.p if self.training else 0)",
        "        attn_out = attn_out.transpose(1, 2).contiguous().view(B, -1, Q.size(-1) * self.num_heads)",
        "        return self.W_o(attn_out)",
    ],
}
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

    "visitor_pattern": [
        "# PATTERN: 访问者模式 (GENE-DP-VISITOR-v1)",
        "from abc import ABC, abstractmethod",
        "",
        "class Visitor(ABC):",
        "    @abstractmethod",
        "    def visit_element_a(self, element): pass",
        "    @abstractmethod",
        "    def visit_element_b(self, element): pass",
        "",
        "class Element(ABC):",
        "    @abstractmethod",
        "    def accept(self, visitor: Visitor): pass",
        "",
        "class ConcreteElementA(Element):",
        "    def accept(self, visitor):",
        "        visitor.visit_element_a(self)",
        "    def operation_a(self): return 'A'",
        "",
        "class ConcreteElementB(Element):",
        "    def accept(self, visitor):",
        "        visitor.visit_element_b(self)",
        "    def operation_b(self): return 'B'",
        "",
        "class ConcreteVisitor1(Visitor):",
        "    def visit_element_a(self, element):",
        "        print(f'V1操作A: {element.operation_a()}')",
        "    def visit_element_b(self, element):",
        "        print(f'V1操作B: {element.operation_b()}')",
        "",
        "# 访问者模式: 对象结构稳定但操作频繁增减时使用",
    ],
    "chain_of_responsibility_pattern": [
        "# PATTERN: 责任链模式 (GENE-DP-CHAIN-v1)",
        "from abc import ABC, abstractmethod",
        "class Handler(ABC):",
        "    def set_next(self, handler):",
        "        self._next = handler; return handler",
        "    @abstractmethod",
        "    def handle(self, request): pass",
    ],
    "state_machine_pattern": [
        "# PATTERN: 有限状态机 (GENE-DP-STATE-v1)",
        "class StateMachine:",
        "    def __init__(self):",
        "        self._state = 'idle'",
        "        self._transitions = {}",
        "    def add_transition(self, state, event, next_state, action=None):",
        "        self._transitions.setdefault(state, {})[event] = (next_state, action)",
    ],
    "command_pattern": [
        "# PATTERN: 命令模式 (GENE-DP-COMMAND-v1)",
        "from abc import ABC, abstractmethod",
        "class Command(ABC):",
        "    @abstractmethod",
        "    def execute(self): pass",
        "    @abstractmethod",
        "    def undo(self): pass",
    ],
    "decorator_pattern": [
        "# PATTERN: 装饰器模式 (GENE-DP-DECORATOR-v1)",
        "import functools",
        "def log_call(fn):",
        "    @functools.wraps(fn)",
        "    def wrapper(*args, **kwargs):",
        "        print(f'CALL: {fn.__name__}')",
        "        return fn(*args, **kwargs)",
        "    return wrapper",
    ],
    "builder_pattern": [
        "# PATTERN: 建造者模式 (GENE-DP-BUILDER-v1)",
        "class Builder:",
        "    def __init__(self): self._product = {}",
        "    def set_name(self, name):",
        "        self._product['name'] = name; return self",
        "    def build(self): return self._product",
    ],
    "composite_pattern": [
        "# PATTERN: 组合模式 (GENE-DP-COMPOSITE-v1)",
        "from abc import ABC, abstractmethod",
        "class Component(ABC):",
        "    @abstractmethod",
        "    def operation(self): pass",
        "class Composite(Component):",
        "    def __init__(self): self.children = []",
        "    def add(self, c): self.children.append(c); return self",
        "    def operation(self):",
        "        return '+'.join(c.operation() for c in self.children)",
    ],
    "adapter_pattern": [
        "# PATTERN: 适配器模式 (GENE-DP-ADAPTER-v1)",
        "class Target:",
        "    def request(self): return 'Target'",
        "class Adaptee:",
        "    def specific_request(self): return 'Adaptee'",
        "class Adapter(Target):",
        "    def __init__(self, adaptee): self.adaptee = adaptee",
        "    def request(self):",
        "        return f'Adapter: {self.adaptee.specific_request()}'",
    ],
    "prototype_pattern": [
        "# PATTERN: 原型模式 (GENE-DP-PROTOTYPE-v1)",
        "import copy",
        "class Prototype:",
        "    def clone(self): return copy.deepcopy(self)",
    ],
    "facade_pattern": [
        "# PATTERN: 门面模式 (GENE-DP-FACADE-v1)",
        "class Facade:",
        "    def __init__(self):",
        "        self.sub1 = SubSystem1()",
        "        self.sub2 = SubSystem2()",
        "    def operation(self):",
        "        return f'{self.sub1.do()} + {self.sub2.do()}'",
    ],
    "bridge_pattern": [
        "# PATTERN: 桥接模式 (GENE-DP-BRIDGE-v1)",
        "class Implementation:",
        "    def operation_impl(self): pass",
        "class Abstraction:",
        "    def __init__(self, impl): self.impl = impl",
        "    def operation(self):",
        "        return self.impl.operation_impl()",
    ],
    "di_container_pattern": [
        "# PATTERN: 依赖注入容器 (GENE-DP-DI-v1)",
        "class DIContainer:",
        "    def __init__(self): self._registry = {}",
        "    def register(self, cls):",
        "        self._registry[cls.__name__] = cls; return self",
        "    def resolve(self, name):",
        "        return self._registry[name]()",
    ],
    "pipeline_filter_pattern": [
        "# PATTERN: 管道过滤器 (GENE-DP-PIPELINE-v1)",
        "class Pipeline:",
        "    def __init__(self): self.filters = []",
        "    def add_filter(self, fn): self.filters.append(fn); return self",
        "    def execute(self, data):",
        "        for f in self.filters: data = f(data)",
        "        return data",
    ],

    # ── 系统设计/存储/分块上传模式 ──
    "object_storage_pattern": [
        "# PATTERN: 对象存储·块存储引擎 (GENE-PRO: STORAGE-v1)",
        "# 分块上传模式:",
        "def upload_chunk(file_path, chunk_index, chunk_data, upload_id):",
        "    \"\"\"分块上传·支持断点续传\"\"\"",
        "    chunk_key = f'{upload_id}/chunk_{chunk_index:06d}'",
        "    # 保存到临时存储",
        "    with open(f'/tmp/staging/{chunk_key}', 'wb') as f:",
        "        f.write(chunk_data)",
        "    # 记录分块元数据",
        "    metadata[chunk_key] = {'size': len(chunk_data), 'hash': hashlib.md5(chunk_data).hexdigest()}",
        "    return chunk_key",
        "",
        "def complete_upload(upload_id, total_chunks):",
        "    \"\"\"合并分块完成上传\"\"\"",
        "    with open(f'/data/final/{upload_id}.bin', 'wb') as out:",
        "        for i in range(total_chunks):",
        "            chunk_key = f'{upload_id}/chunk_{i:06d}'",
        "            if chunk_key not in metadata:",
        "                # 检查缺失块并尝试恢复",
        "                raise MissingChunkError(f'Missing chunk {i}')",
        "            with open(f'/tmp/staging/{chunk_key}', 'rb') as f:",
        "                out.write(f.read())",
        "    return upload_id",
        "",
        "# 断点续传:",
        "def list_uploaded_chunks(upload_id):",
        "    \"\"\"返回已上传的分块索引列表\"\"\"",
        "    return [k for k in metadata if k.startswith(f'{upload_id}/chunk_')]",
        "",
        "# 存储引擎抽象:",
        "class StorageBackend(ABC):",
        "    @abstractmethod",
        "    def put(self, key, data): pass",
        "    @abstractmethod",
        "    def get(self, key): pass",
        "    @abstractmethod",
        "    def delete(self, key): pass",
        "class FileSystemBackend(StorageBackend):",
        "    def put(self, key, data): Path(key).write_bytes(data)",
        "    def get(self, key): return Path(key).read_bytes()",
        "    def delete(self, key): Path(key).unlink(missing_ok=True)",
    ],

    }
# ── 字符串编码模式（2026-07-16 补: Bug修复·easy维度缺口）──
ENCODING_PATTERNS = {
    "string_encoding_utf8": [
        "# PATTERN: Python字符串编码/解码 (GENE-PRO: ENCODING-UTF8-v1)",
        "# 中英文混排编码铁律:",
        "#  - Python3字符串=str(Unicode), 不是 bytes",
        "#  - len()对str返回字符数(中文1字符), 对bytes返回字节数(中文3字节)",
        "#  - 截断时用 str[:n] 按字符截断, 不要按字节截断!",
        "#  - encode('utf-8') 得到bytes, decode('utf-8') 得到str",
        "#",
        "# 常见Bug场景:",
        "#  - b'中文'[:3] 只截到半个中文字符 → UnicodeDecodeError",
        "#  - 数据库字段长度按字节定义 → 超长截断会破坏UTF-8序列",
        "#  - JSON序列化时 ensure_ascii=False 保留中文",
        "#",
        "# 安全截断模板:",
        "def safe_truncate(text, max_chars):",
        "    \"\"\"按字符数安全截断字符串(不破坏UTF-8)\"\"\"",
        "    return text[:max_chars] if isinstance(text, str) else text",
        "",
        "def safe_byte_truncate(text, max_bytes):",
        "    \"\"\"按字节数安全截断(不破坏UTF-8序列)\"\"\"",
        "    encoded = text.encode('utf-8')",
        "    if len(encoded) <= max_bytes:",
        "        return text",
        "    # 从max_bytes往回找, 直到不在多字节序列中部",
        "    while max_bytes > 0 and (encoded[max_bytes] & 0xC0) == 0x80:",
        "        max_bytes -= 1",
        "    return encoded[:max_bytes].decode('utf-8')",
        "",
        "# 编码修复:",
        "def fix_mojibake(text, src_encoding='latin-1', dst_encoding='utf-8'):",
        "    \"\"\"修复乱码: 先用错误编码解成bytes, 再重新decode\"\"\"",
        "    if isinstance(text, str):",
        "        text = text.encode(dst_encoding, errors='replace')",
        "    return text.decode(src_encoding, errors='replace')",
    ],
    "json_encoding_safe": [
        "# PATTERN: JSON安全序列化 (GENE-PRO: JSON-ENCODING-v1)",
        "import json",
        "",
        "# 中文字符不转义:",
        "json.dumps(data, ensure_ascii=False)  # 保留中文和Unicode字符",
        "",
        "# bytes字段处理:",
        "class BytesEncoder(json.JSONEncoder):",
        "    def default(self, obj):",
        "        if isinstance(obj, bytes):",
        "            return obj.decode('utf-8', errors='replace')",
        "        return super().default(obj)",
        "",
        "# 大JSON流式写入:",
        "def write_json_stream(items, filepath):",
        "    with open(filepath, 'w', encoding='utf-8') as f:",
        "        f.write('[')",
        "        for i, item in enumerate(items):",
        "            if i > 0: f.write(',')",
        "            f.write(json.dumps(item, ensure_ascii=False))",
        "        f.write(']')",
    ],
    "str_bytes_mismatch": [
        "# PATTERN: 字符串/字节串混用修复 (GENE-PRO: STR-BYTES-v1)",
        "# 排查チェックリスト:",
        "#  □ 所有open()指定encoding='utf-8'",
        "#  □ API返回值: resp.text (str) vs resp.content (bytes)",
        "#  □ 数据库: str存Unicode, bytes存BLOB",
        "#  □ 文件读写: 'r' vs 'rb' / 'w' vs 'wb'",
        "#  □ 正则: re.match(r'pattern', text) 需要str不是bytes",
        "#  □ hashlib: sha256(data.encode()) 输入必须bytes",
        "#  □ HTTP头: headers中的值必须是str不能是bytes",
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
    'lru_cache_pattern': [
        '# PATTERN: LRU缓存 (GENE-SEM-b4c77ea27c5c78cc)',
    ],
    'skiplist_memtable_pattern': [
        '# PATTERN: SkipList跳表·MemTable (GENE-SEM-SKIPLIST-MEMTABLE-v1)',
        'import random',
        '',
        'class SkipListNode:',
        '    def __init__(self, key, value, level):',
        '        self.key = key',
        '        self.value = value',
        '        self.forward = [None] * (level + 1)',
        '',
        'class SkipList:',
        '    \"\"\"概率平衡的跳表·O(log n)期望\"\"\"',
        '    def __init__(self, max_level=16, p=0.5):',
        '        self.max_level = max_level',
        '        self.p = p',
        '        self.header = SkipListNode(None, None, max_level)',
        '        self.level = 0',
        '',
        '    def _random_level(self):',
        '        level = 0',
        '        while random.random() < self.p and level < self.max_level:',
        '            level += 1',
        '        return level',
        '',
        '    def insert(self, key, value):',
        '        update = [None] * (self.max_level + 1)',
        '        cur = self.header',
        '        for i in range(self.level, -1, -1):',
        '            while cur.forward[i] and cur.forward[i].key < key:',
        '                cur = cur.forward[i]',
        '            update[i] = cur',
        '        cur = cur.forward[0]',
        '        if cur and cur.key == key:',
        '            cur.value = value  # update',
        '        else:',
        '            new_level = self._random_level()',
        '            if new_level > self.level:',
        '                for i in range(self.level + 1, new_level + 1):',
        '                    update[i] = self.header',
        '                self.level = new_level',
        '            new_node = SkipListNode(key, value, new_level)',
        '            for i in range(new_level + 1):',
        '                new_node.forward[i] = update[i].forward[i]',
        '                update[i].forward[i] = new_node',
        '',
        '    def search(self, key):',
        '        cur = self.header',
        '        for i in range(self.level, -1, -1):',
        '            while cur.forward[i] and cur.forward[i].key < key:',
        '                cur = cur.forward[i]',
        '        cur = cur.forward[0]',
        '        if cur and cur.key == key:',
        '            return cur.value',
        '        return None',
        '',
        '    def delete(self, key):',
        '        update = [None] * (self.max_level + 1)',
        '        cur = self.header',
        '        for i in range(self.level, -1, -1):',
        '            while cur.forward[i] and cur.forward[i].key < key:',
        '                cur = cur.forward[i]',
        '            update[i] = cur',
        '        cur = cur.forward[0]',
        '        if cur and cur.key == key:',
        '            for i in range(self.level + 1):',
        '                if update[i].forward[i] != cur:',
        '                    break',
        '                update[i].forward[i] = cur.forward[i]',
        '            while self.level > 0 and not self.header.forward[self.level]:',
        '                self.level -= 1',
        '            return cur.value',
        '        return None',
        '',
        '# MemTable: 基于SkipList的内存表',
        'class MemTable:',
        '    \"\"\"LSM Tree的内存写缓存·SkipList保证有序\"\"\"',
        '    def __init__(self, max_size=1000):',
        '        self.skiplist = SkipList()',
        '        self.size = 0',
        '        self.max_size = max_size',
        '',
        '    def insert(self, key, value):',
        '        self.skiplist.insert(key, value)',
        '        self.size += 1',
        '        if self.size >= self.max_size:',
        '            self.flush()',
        '',
        '    def search(self, key):',
        '        return self.skiplist.search(key)',
        '',
        '    def flush(self):',
        '        \"\"\"刷盘为SSTable (compaction触发)\"\"\"',
        '        self.skiplist = SkipList()',
        '        self.size = 0',
        '        return True',
        '',
        '# ⚠️ 踩坑:',
        '# (1) random_level的p参数: p=0.5时平均每层元素减半',
        '# (2) 删除时需更新self.level防止搜索跳过已删高层',
        '# (3) MemTable满时需要flush到SSTable(LSM核心)',
    ],
    'lru_cache_pattern': [
        '# PATTERN: LRU缓存 (GENE-SEM-b4c77ea27c5c78cc)',
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
    'binary_search_pattern': [
        '# PATTERN: 二分查找模板 (GENE-SEM-4815231711e126aa)',
        'def binary_search(nums, target):',
        '    left, right = 0, len(nums) - 1',
        '    while left <= right:',
        '        mid = left + (right - left) // 2',
        '        if nums[mid] == target: return mid',
        '        elif nums[mid] < target: left = mid + 1',
        '        else: right = mid - 1',
        '    return -1',
    ],
    'linked_list_pattern': [
        '# PATTERN: 链表+最小堆·合并K个有序链表 (GENE-SEM-LINKED-HEAP-v1)',
        'import heapq',
        '',
        'class ListNode:',
        '    def __init__(self, val=0, next=None):',
        '        self.val = val; self.next = next',
        '',
        'def merge_k_lists(lists):',
        '    """合并K个升序链表·最小堆 O(NlogK)"""',
        '    heap = []',
        '    # 初始化: 每个链表头入堆 (val, idx, node)',
        '    for i, node in enumerate(lists):',
        '        if node:',
        '            heapq.heappush(heap, (node.val, i, node))',
        '    dummy = ListNode(0)',
        '    cur = dummy',
        '    while heap:',
        '        val, i, node = heapq.heappop(heap)',
        '        cur.next = ListNode(val)',
        '        cur = cur.next',
        '        if node.next:',
        '            heapq.heappush(heap, (node.next.val, i, node.next))',
        '    return dummy.next',
        '',
        '# 变体: 两两合并分治法 O(NlogK)',
        'def merge_k_lists_divide_conquer(lists):',
        '    def merge_two(l1, l2):',
        '        dummy = ListNode(0); cur = dummy',
        '        while l1 and l2:',
        '            if l1.val < l2.val:',
        '                cur.next = l1; l1 = l1.next',
        '            else:',
        '                cur.next = l2; l2 = l2.next',
        '            cur = cur.next',
        '        cur.next = l1 or l2',
        '        return dummy.next',
        '    if not lists: return None',
        '    while len(lists) > 1:',
        '        merged = []',
        '        for i in range(0, len(lists), 2):',
        '            if i+1 < len(lists):',
        '                merged.append(merge_two(lists[i], lists[i+1]))',
        '            else:',
        '                merged.append(lists[i])',
        '        lists = merged',
        '    return lists[0]',
    ],
    'heap_pattern': [
        '# PATTERN: 最小堆/优先队列 (GENE-SEM-HEAP-v1)',
        'import heapq',
        '',
        '# 最小堆(默认): heapq保证heap[0]最小',
        'heap = []',
        'heapq.heappush(heap, 5)',
        'heapq.heappush(heap, 1)',
        'smallest = heapq.heappop(heap)  # → 1',
        '',
        '# 最大堆: 存入负值',
        'max_heap = []',
        'heapq.heappush(max_heap, -5)',
        'largest = -heapq.heappop(max_heap)  # → 5',
        '',
        '# 取TopK',
        'top3 = heapq.nlargest(3, [1,5,3,8,2])',
        'bottom3 = heapq.nsmallest(3, [1,5,3,8,2])',
        '',
        '# 堆化 O(n)',
        'data = [5,1,3,8,2]',
        'heapq.heapify(data)  # → [1,2,3,8,5]',
        '',
        '# 元素更新(需先标记再重新push)',
        '# 或使用heapq._siftdown/heapreplace效率更高',
        '',
        '# 模板: 合并K个有序数组/链表',
        'def merge_k_sorted(arrays):',
        '    """合并K个升序数组"""',
        '    heap = [(arr[0], i, 0) for i, arr in enumerate(arrays) if arr]',
        '    heapq.heapify(heap)',
        '    result = []',
        '    while heap:',
        '        val, arr_idx, pos = heapq.heappop(heap)',
        '        result.append(val)',
        '        if pos + 1 < len(arrays[arr_idx]):',
        '            heapq.heappush(heap, (arrays[arr_idx][pos+1], arr_idx, pos+1))',
        '    return result',
    ],
    'bst_pattern': [
        '# PATTERN: 二叉树/二叉搜索树 (GENE-SEM-BST-v1)',
        'class TreeNode:',
        '    def __init__(self, val=0, left=None, right=None):',
        '        self.val = val; self.left = left; self.right = right',
        '',
        '# 前序: 根→左→右',
        'def preorder(root):',
        '    return [root.val] + preorder(root.left) + preorder(root.right) if root else []',
        '',
        '# 中序: 左→根→右 (BST升序)',
        'def inorder(root):',
        '    return inorder(root.left) + [root.val] + inorder(root.right) if root else []',
        '',
        '# 后序: 左→右→根',
        'def postorder(root):',
        '    return postorder(root.left) + postorder(root.right) + [root.val] if root else []',
        '',
        '# 层序 (BFS)',
        'from collections import deque',
        'def levelorder(root):',
        '    if not root: return []',
        '    q = deque([root]); res = []',
        '    while q:',
        '        node = q.popleft(); res.append(node.val)',
        '        if node.left: q.append(node.left)',
        '        if node.right: q.append(node.right)',
        '    return res',
        '',
        '# BST验证',
        'def is_valid_bst(root, lo=float(\"-inf\"), hi=float(\"inf\")):',
        '    if not root: return True',
        '    if not (lo < root.val < hi): return False',
        '    return is_valid_bst(root.left, lo, root.val) and is_valid_bst(root.right, root.val, hi)',
    ],
    'interval_tree_pattern': [
        '# PATTERN: 区间树/线段树 (GENE-SEM-INTERVAL-TREE-v1)',
        '# 区间树(Interval Tree) vs 线段树(Segment Tree):',
        '# 区间树: 存储区间, 支持O(log n)重叠查询',
        '# 线段树: 数组上的区间操作(求和/最值), 支持O(log n)更新和查询',
        '',
        '# 区间树实现(基于BST, 按区间中点分割):',
        'class IntervalTreeNode:',
        '    def __init__(self, interval):',
        '        self.interval = interval  # (start, end)',
        '        self.max_end = interval[1]',
        '        self.left = None',
        '        self.right = None',
        '',
        'class IntervalTree:',
        '    """区间树: 插入区间+重叠查询, O(log n)"""',
        '    def __init__(self):',
        '        self.root = None',
        '',
        '    def insert(self, interval):',
        '        """插入区间, 更新max_end"""',
        '        def _insert(node, interval):',
        '            if node is None:',
        '                return IntervalTreeNode(interval)',
        '            mid = node.interval[0]',
        '            if interval[0] < mid:',
        '                node.left = _insert(node.left, interval)',
        '            else:',
        '                node.right = _insert(node.right, interval)',
        '            node.max_end = max(node.max_end, interval[1])',
        '            return node',
        '        self.root = _insert(self.root, interval)',
        '',
        '    def overlap_search(self, interval):',
        '        """查询与给定区间重叠的任意区间"""',
        '        def _search(node, interval):',
        '            if node is None:',
        '                return None',
        '            # 检查当前节点是否重叠',
        '            if interval[0] <= node.interval[1] and interval[1] >= node.interval[0]:',
        '                return node.interval',
        '            # 如果左子树的max_end >= 查询区间start, 搜索左子树',
        '            if node.left and node.left.max_end >= interval[0]:',
        '                return _search(node.left, interval)',
        '            # 否则搜索右子树',
        '            return _search(node.right, interval)',
        '        return _search(self.root, interval)',
        '',
        '    def all_overlaps(self, interval):',
        '        """查询所有重叠区间(DFS遍历)"""',
        '        result = []',
        '        def _collect(node, interval):',
        '            if node is None:',
        '                return',
        '            if interval[0] <= node.interval[1] and interval[1] >= node.interval[0]:',
        '                result.append(node.interval)',
        '            if node.left and node.left.max_end >= interval[0]:',
        '                _collect(node.left, interval)',
        '            _collect(node.right, interval)',
        '        _collect(self.root, interval)',
        '        return result',
        '',
        '# 线段树实现(Segment Tree):',
        'class SegmentTree:',
        '    """线段树: 区间求和+点更新, O(log n)"""',
        '    def __init__(self, arr):',
        '        self.n = len(arr)',
        '        self.tree = [0] * (4 * self.n)',
        '        if self.n > 0:',
        '            self._build(arr, 1, 0, self.n - 1)',
        '',
        '    def _build(self, arr, node, l, r):',
        '        if l == r:',
        '            self.tree[node] = arr[l]',
        '            return',
        '        mid = (l + r) // 2',
        '        self._build(arr, node*2, l, mid)',
        '        self._build(arr, node*2+1, mid+1, r)',
        '        self.tree[node] = self.tree[node*2] + self.tree[node*2+1]',
        '',
        '    def update(self, idx, val):',
        '        """点更新: O(log n)"""',
        '        def _update(node, l, r):',
        '            if l == r:',
        '                self.tree[node] = val',
        '                return',
        '            mid = (l + r) // 2',
        '            if idx <= mid:',
        '                _update(node*2, l, mid)',
        '            else:',
        '                _update(node*2+1, mid+1, r)',
        '            self.tree[node] = self.tree[node*2] + self.tree[node*2+1]',
        '        _update(1, 0, self.n - 1)',
        '',
        '    def query(self, ql, qr):',
        '        """区间查询求和: O(log n)"""',
        '        def _query(node, l, r):',
        '            if ql > r or qr < l:',
        '                return 0',
        '            if ql <= l and r <= qr:',
        '                return self.tree[node]',
        '            mid = (l + r) // 2',
        '            return _query(node*2, l, mid) + _query(node*2+1, mid+1, r)',
        '        return _query(1, 0, self.n - 1)',
        '',
        '# 使用示例:',
        '# tree = IntervalTree()',
        '# tree.insert((15, 20))',
        '# tree.insert((10, 30))',
        '# tree.insert((5, 8))',
        '# overlap = tree.overlap_search((14, 16))  # 重叠 → (15,20)',
        '# overlaps = tree.all_overlaps((14, 16))     # 所有重叠',
    ],
    'singleton_pattern': [
        '# PATTERN: 线程安全单例模式 (GENE-PRO-SINGLETON-v1)',
        'import threading',
        '',
        'class Singleton:',
        '    """线程安全单例(双重检查锁定)"""',
        '    _instance = None',
        '    _lock = threading.Lock()',
        '',
        '    def __new__(cls, *args, **kwargs):',
        '        # 第一重检查(无锁)',
        '        if cls._instance is None:',
        '            with cls._lock:',
        '                # 第二重检查(有锁)',
        '                if cls._instance is None:',
        '                    cls._instance = super().__new__(cls)',
        '        return cls._instance',
        '',
        '    def __init__(self):',
        '        # __init__只初始化一次',
        '        if not getattr(self, "_initialized", False):',
        '            self._initialized = True',
        '',
        '# Pythonic方式: 模块级单例(天然线程安全)',
        '# _instance = Singleton()  # import时创建·无需锁',
        '',
        '# 装饰器版本:',
        'def singleton(cls):',
        '    """线程安全单例装饰器(双重检查锁定)"""',
        '    instances = {}',
        '    lock = threading.Lock()',
        '    def get_instance(*args, **kwargs):',
        '        if cls not in instances:',
        '            with lock:',
        '                if cls not in instances:',
        '                    instances[cls] = cls(*args, **kwargs)',
        '        return instances[cls]',
        '    return get_instance',
    ],
}
# ─── 系统设计模式（当gene_injection_engine.py import失败时作为内置fallback）───
# 涵盖: 指数退避重试·熔断器·令牌桶限流·后台任务·线程池·分布式锁
# 对应keyword_map中6个系统设计常用模式, 避免LGE不可用时得分=50
SYSTEM_DESIGN_PATTERNS = {
    "retry_backoff": [
        "# PATTERN: 指数退避重试 (GENE-PRO-b4c7f6a8)",
        "import time, random",
        "def retry_with_backoff(fn, max_retries=3, base_delay=1.0, max_delay=60.0):",
        "    for attempt in range(max_retries):",
        "        try:",
        "            return fn()",
        "        except Exception as e:",
        "            if attempt == max_retries - 1: raise",
        "            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.1), max_delay)",
        "            time.sleep(delay)",
        "            logger.warning(f'Retry {attempt+1}/{max_retries}: {e}')",
        "",
        "# async version (asyncio)",
        "async def retry_async(fn, max_retries=3, base_delay=1.0):",
        "    for attempt in range(max_retries):",
        "        try:",
        "            return await fn()",
        "        except Exception:",
        "            if attempt == max_retries - 1: raise",
        "            await asyncio.sleep(base_delay * (2 ** attempt))",
        "",
        "# 装饰器版本",
        "def retry(max_retries=3, base_delay=1.0):",
        "    def decorator(fn):",
        "        @functools.wraps(fn)",
        "        def wrapper(*args, **kwargs):",
        "            last_exc = None",
        "            for i in range(max_retries):",
        "                try: return fn(*args, **kwargs)",
        "                except Exception as e:",
        "                    last_exc = e",
        "                    time.sleep(base_delay * (2 ** i))",
        "            raise last_exc",
        "        return wrapper",
        "    return decorator",
    ],
    "circuit_breaker": [
        "# PATTERN: 熔断器三状态 (GENE-PRO-CB-v1)",
        "class CircuitBreaker:",
        "    CLOSED, OPEN, HALF_OPEN = 'CLOSED', 'OPEN', 'HALF_OPEN'",
        "    def __init__(self, threshold=5, recovery_timeout=30):",
        "        self.state = self.CLOSED; self.failures = 0",
        "        self.threshold = threshold; self.last_failure = 0",
        "        self.recovery_timeout = recovery_timeout",
        "    def call(self, fn, *args, **kwargs):",
        "        if self.state == self.OPEN:",
        "            if time.time() - self.last_failure > self.recovery_timeout:",
        "                self.state = self.HALF_OPEN",
        "            else: raise CircuitBreakerOpenError",
        "        try:",
        "            result = fn(*args, **kwargs)",
        "            if self.state == self.HALF_OPEN: self.state = self.CLOSED",
        "            self.failures = 0; return result",
        "        except Exception as e:",
        "            self.failures += 1; self.last_failure = time.time()",
        "            if self.failures >= self.threshold: self.state = self.OPEN",
        "            raise",
    ],
    "rate_limiting": [
        "# PATTERN: 令牌桶限流器 (GENE-PRO-TOKENBUCKET-v1)",
        "import time, threading",
        "class TokenBucket:",
        "    def __init__(self, rate, capacity):",
        "        self.rate = rate; self.capacity = capacity",
        "        self.tokens = capacity; self.last_refill = time.monotonic()",
        "        self.lock = threading.Lock()",
        "    def _refill(self):",
        "        now = time.monotonic(); elapsed = now - self.last_refill",
        "        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)",
        "        self.last_refill = now",
        "    def consume(self, tokens=1):",
        "        with self.lock:",
        "            self._refill()",
        "            if self.tokens >= tokens:",
        "                self.tokens -= tokens; return True",
        "            return False",
    ],
    "background_job": [
        "# PATTERN: 后台任务队列+worker (GENE-PRO-BGJOB-v1)",
        "from queue import Queue",
        "from threading import Thread",
        "class BackgroundWorker:",
        "    def __init__(self, workers=3):",
        "        self.queue = Queue(); self.running = True",
        "        self.threads = [Thread(target=self._work, daemon=True) for _ in range(workers)]",
        "        for t in self.threads: t.start()",
        "    def _work(self):",
        "        while self.running:",
        "            fn, args, kwargs = self.queue.get()",
        "            try: fn(*args, **kwargs)",
        "            except Exception as e: logger.error(f'Job failed: {e}')",
        "    def submit(self, fn, *args, **kwargs): self.queue.put((fn, args, kwargs))",
        "    def shutdown(self): self.running = False",
    ],
    "thread_pool_pattern": [
        "# PATTERN: 线程池 (GENE-PRO-TPOOL-v1)",
        "from concurrent.futures import ThreadPoolExecutor, as_completed",
        "with ThreadPoolExecutor(max_workers=4) as executor:",
        "    futures = {executor.submit(task, arg): arg for arg in args}",
        "    for future in as_completed(futures):",
        "        result = future.result(timeout=30)",
    ],
    "batch_norm_pattern": [
        "# PATTERN: Batch Normalization · 前向+反向 (GENE-PRO-BN-v1)",
        "import numpy as np",
        "",
        "class BatchNorm1d:",
        "    \"\"\"Batch Normalization层的forward和backward实现\"\"\"",
        "    def __init__(self, num_features, eps=1e-5, momentum=0.9):",
        "        self.eps = eps",
        "        self.momentum = momentum",
        "        # 可学习参数",
        "        self.gamma = np.ones(num_features)   # 缩放",
        "        self.beta = np.zeros(num_features)   # 偏移",
        "        # 运行时统计（推理模式使用）",
        "        self.running_mean = np.zeros(num_features)",
        "        self.running_var = np.ones(num_features)",
        "        self.training = True",
        "        # 缓存（反向传播用）",
        "        self.cache = None",
        "",
        "    def forward(self, x):",
        "        \"\"\"前向传播",
        "        x: (N, D) N=batch_size, D=num_features",
        "        \"\"\"",
        "        if self.training:",
        "            # 沿batch维度计算均值和方差",
        "            mu = np.mean(x, axis=0)           # (D,)",
        "            var = np.var(x, axis=0)           # (D,)",
        "            # 更新运行时统计（滑动平均）",
        "            self.running_mean = self.momentum * self.running_mean + (1 - self.momentum) * mu",
        "            self.running_var = self.momentum * self.running_var + (1 - self.momentum) * var",
        "        else:",
        "            # 推理模式用运行时统计",
        "            mu = self.running_mean",
        "            var = self.running_var",
        "",
        "        # 归一化: x_hat = (x - mu) / sqrt(var + eps)",
        "        x_hat = (x - mu) / np.sqrt(var + self.eps)",
        "        # 缩放偏移: y = gamma * x_hat + beta",
        "        y = self.gamma * x_hat + self.beta",
        "",
        "        if self.training:",
        "            self.cache = (x, x_hat, mu, var, y)",
        "        return y",
        "",
        "    def backward(self, dy):",
        "        \"\"\"反向传播计算梯度",
        "        dy: 上游梯度 (N, D)",
        "        返回: dx, dgamma, dbeta",
        "        \"\"\"",
        "        x, x_hat, mu, var, y = self.cache",
        "        N = x.shape[0]",
        "        D = x.shape[1]",
        "        std_inv = 1.0 / np.sqrt(var + self.eps)  # (D,)",
        "",
        "        # 梯度: beta梯度 = sum(dy, axis=0)",
        "        dbeta = np.sum(dy, axis=0)",
        "        # 梯度: gamma梯度 = sum(dy * x_hat, axis=0)",
        "        dgamma = np.sum(dy * x_hat, axis=0)",
        "",
        "        # 梯度: x_hat梯度 = dy * gamma",
        "        dx_hat = dy * self.gamma  # (N, D)",
        "",
        "        # 梯度: var梯度",
        "        dvar = np.sum(dx_hat * (x - mu) * (-0.5) * (var + self.eps) ** (-1.5), axis=0)",
        "",
        "        # 梯度: mu梯度",
        "        dmu = np.sum(dx_hat * (-std_inv), axis=0) + dvar * np.sum(-2 * (x - mu), axis=0) / N",
        "",
        "        # 梯度: x梯度（完整链式法则）",
        "        dx = dx_hat * std_inv + dvar * 2 * (x - mu) / N + dmu / N",
        "",
        "        return dx, dgamma, dbeta",
        "",
        "# PyTorch等效实现",
        "# import torch.nn as nn",
        "# bn = nn.BatchNorm1d(num_features=128)",
        "# y = bn(x)  # forward自动处理",
        "# y.backward()  # 自动微分",
        "",
        "# 训练/推理模式切换:",
        "# bn.train() / bn.eval()",
        "# 关键: 推理时running_mean/var代替batch统计",
        "",
        "# 常用变体:",
        "# - LayerNorm: 沿特征维归一化, 用于Transformer (nn.LayerNorm)",
        "# - InstanceNorm: 每个样本独立归一化, 用于风格迁移",
        "# - GroupNorm: 将通道分组归一化, 适用于小batch",
    ],
    "data_normalization_pattern": [
        "# PATTERN: 数据归一化 — Min-Max缩放 + Z-score标准化 (GENE-PRO-DATANORM-v1)",
        "import numpy as np",
        "from typing import List, Optional",
        "",
        "class MinMaxScaler:",
        "    # Min-Max归一化: 将数据缩放到[0,1]区间",
        "    def __init__(self, feature_range: tuple = (0, 1)):",
        "        self.min_val = None",
        "        self.max_val = None",
        "        self.data_min_ = None",
        "        self.data_max_ = None",
        "        self.range_min, self.range_max = feature_range",
        "",
        "    def fit(self, X: np.ndarray) -> 'MinMaxScaler':",
        "        # 计算每列的最小值和最大值",
        "        self.data_min_ = X.min(axis=0)",
        "        self.data_max_ = X.max(axis=0)",
        "        # 防止除零: 若某列max==min, 设为0",
        "        self.data_range_ = np.where(",
        "            self.data_max_ - self.data_min_ != 0,",
        "            self.data_max_ - self.data_min_,",
        "            1.0",
        "        )",
        "        return self",
        "",
        "    def transform(self, X: np.ndarray) -> np.ndarray:",
        "        # X_scaled = (X - min) / (max - min) * (rmax - rmin) + rmin",
        "        X_std = (X - self.data_min_) / self.data_range_",
        "        return X_std * (self.range_max - self.range_min) + self.range_min",
        "",
        "    def inverse_transform(self, X_scaled: np.ndarray) -> np.ndarray:",
        "        # 还原到原始尺度",
        "        X_std = (X_scaled - self.range_min) / (self.range_max - self.range_min)",
        "        return X_std * self.data_range_ + self.data_min_",
        "",
        "    def fit_transform(self, X: np.ndarray) -> np.ndarray:",
        "        return self.fit(X).transform(X)",
        "",
        "",
        "class StandardScaler:",
        "    # Z-score标准化: (x - mu) / sigma, 使数据均值为0, 标准差为1",
        "    def __init__(self):",
        "        self.mean_ = None",
        "        self.std_ = None",
        "",
        "    def fit(self, X: np.ndarray) -> 'StandardScaler':",
        "        # 计算每列的均值和标准差",
        "        self.mean_ = X.mean(axis=0)",
        "        self.std_ = X.std(axis=0, ddof=0)  # 总体标准差",
        "        # 防止除零: 若某列标准差为0, 设为1",
        "        self.std_ = np.where(self.std_ != 0, self.std_, 1.0)",
        "        return self",
        "",
        "    def transform(self, X: np.ndarray) -> np.ndarray:",
        "        # z = (x - mu) / sigma",
        "        return (X - self.mean_) / self.std_",
        "",
        "    def inverse_transform(self, X_scaled: np.ndarray) -> np.ndarray:",
        "        # x = z * sigma + mu",
        "        return X_scaled * self.std_ + self.mean_",
        "",
        "    def fit_transform(self, X: np.ndarray) -> np.ndarray:",
        "        return self.fit(X).transform(X)",
        "",
        "",
        "# sklearn兼容接口 (直接导入sklearn也可)",
        "# from sklearn.preprocessing import MinMaxScaler, StandardScaler",
        "",
        "# 实用函数: 快速归一化",
        "def normalize_data(X, method='zscore'):",
        "    # 快捷归一化入口",
        "    if method == 'minmax':",
        "        return MinMaxScaler().fit_transform(X)",
        "    elif method == 'zscore':",
        "        return StandardScaler().fit_transform(X)",
        "    raise ValueError(f'Unsupported method: {method}')",
        "",
        "# 使用示例:",
        "# if __name__ == '__main__':",
        "#     X = np.array([[1, 2], [3, 4], [5, 6]], dtype=float)",
        "#     mm = MinMaxScaler().fit_transform(X)  # [[0,0], [0.5,0.5], [1,1]]",
        "#     zs = StandardScaler().fit_transform(X)  # [[-1.22,-1.22], [0,0], [1.22,1.22]]",
        "#",
        "# ⚠️ 踩坑:",
        "# (1) Min-Max对异常值敏感 — 一个极端值会把正常数据压到很小区间",
        "# (2) Z-score假设数据近似正态分布 — 否则标准化后分布形态不变",
        "# (3) 测试集用训练集的fit统计量: scaler.fit(X_train); X_test_scaled = scaler.transform(X_test)",
        "# (4) 防止伪造规范: 训练前做归一化, 不要对整个数据集做fit再split",
        "# (5) 多维数组: axis=0沿列(特征维)计算, 不是沿行",
        "# (6) 稀疏数据: Min-Max破坏稀疏性 → 用MaxAbsScaler",
        "    ],",
    ],
    "distributed_lock_pattern": [
        "# PATTERN: 分布式锁·Redis SETNX (GENE-PRO-DLOCK-v1)",
        "class DistributedLock:",
        "    def __init__(self, redis_client, lock_key, ttl=30):",
        "        self.redis = redis_client; self.key = lock_key; self.ttl = ttl",
        "    def acquire(self):",
        "        return self.redis.setnx(self.key, 1) and self.redis.expire(self.key, self.ttl)",
        "    def release(self): self.redis.delete(self.key)",
        "    @contextmanager",
        "    def __call__(self):",
        "        if self.acquire():",
        "            try: yield self",
        "            finally: self.release()",
    ],
}
# ── 联邦关键fallback模式（import失败时确保keyword_map能找到这些pattern name）──
FALLBACK_PATTERNS = {
    "async_pattern": [
        "# PATTERN: 异步并发+限流 (GENE-PRO-d9e3b2c4)",
        "async with asyncio.Semaphore(MAX_CONCURRENT):",
        "    async with aiohttp.ClientSession() as session:",
        "        tasks = [fetch(session, url) for url in urls]",
        "        results = await asyncio.gather(*tasks, return_exceptions=True)",
    ],
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
}
BUILTIN_PATTERNS.update(ALGORITHM_PATTERNS)
BUILTIN_PATTERNS.update(MEMORY_PATTERNS)
BUILTIN_PATTERNS.update(_ATTENTION_PATTERNS)
BUILTIN_PATTERNS.update(SYSTEM_DESIGN_PATTERNS)
BUILTIN_PATTERNS.update(ENCODING_PATTERNS)
BUILTIN_PATTERNS.update(FALLBACK_PATTERNS)  # 确保import失败时也有基础fallback

# LGE基因库集群（三级降级: 地枢主库→天枢LGE→灵龙LGA本地）
LGE_POOL = [
    "http://100.116.0.29:8200",   # 【主】地枢DGX2（791K基因）
    "http://100.100.89.2:8201",   # 【备1】天枢LGE Studio（829基因）
    "http://127.0.0.1:8210",      # 【备2】灵龙LGE镜像（644K基因·GET API）
    "http://127.0.0.1:8202",      # 【备3】灵龙LGA本地代理（35基因）
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

    # 第四级: SSH代理到天枢（直连全部失败时通过天枢访问LGE）
    if _connectivity_cache.get(LGE_POOL[1]) is not True and _connectivity_cache.get(LGE_POOL[0]) is not True:
        try:
            import subprocess as sp
            qjson = json.dumps({"query": query, "n_results": limit})
            # 使用stdin管道(-d @-)代替shell拼接，避免引号转义问题
            ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                       "a1@100.100.89.2",
                       "curl -s --max-time 10 -X POST http://100.100.89.2:8201/genes/search -H 'Content-Type: application/json' -d @-"]
            result = sp.run(ssh_cmd, input=qjson, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                results = [r.get("content", "") for r in data.get("results", [])]
                if results:
                    print(f"  [OK] search_lge(SSH→天枢) → {len(results)}条", file=__import__('sys').stderr)
                    _connectivity_cache[LGE_POOL[1]] = True  # 标记可达
                    return results
        except json.JSONDecodeError:
            print(f"  [WARN] SSH天枢返回非JSON: {result.stdout[:80]}", file=__import__('sys').stderr)
        except Exception as e:
            print(f"  [WARN] SSH天枢代理失败: {str(e)[:50]}", file=__import__('sys').stderr)

    return []  # 所有节点都不可达


def _try_http_search(url, query, limit):
    """直接HTTP搜索LGE节点（POST优先·405时回退GET）"""
    from urllib.error import HTTPError
    import urllib.parse as url_parse
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
    except HTTPError as e:
        if e.code == 405:
            # 尝试GET（镜像节点如127.0.0.1:8210使用GET API）
            get_url = f"{url}/genes/search?q={url_parse.quote(query)}&limit={limit}"
            try:
                get_resp = urllib.request.urlopen(get_url, timeout=5)
                get_data = json.loads(get_resp.read())
                get_results = [r.get("content", "") for r in get_data.get("results", [])]
                if get_results:
                    _connectivity_cache[url] = True
                    print(f"  [OK] search_lge({url}·GET) → {len(get_results)}条", file=__import__('sys').stderr)
                    return get_results
                _connectivity_cache[url] = True
            except Exception as get_e:
                print(f"  [WARN] {url} GET也失败: {str(get_e)[:40]}", file=__import__('sys').stderr)
                _connectivity_cache[url] = False
        elif e.code == 500:
            _connectivity_cache[url] = False
        else:
            print(f"  [WARN] {url} HTTP {e.code}", file=__import__('sys').stderr)
            _connectivity_cache[url] = False
    except Exception as e:
        print(f"  [WARN] {url}不可达: {str(e)[:40]}", file=__import__('sys').stderr)
        _connectivity_cache[url] = False
    return None


def extract_coding_genes(task_description):
    """基因感知: 多粒度中文关键词分解 + LGE检索（25s硬超时防护）"""
    results = []
    import re, time
    
    _extract_deadline = time.time() + 25  # 全局25秒硬超时，超时后让内置fallback接管
    
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
        # 超时防护：直接终止搜索
        if time.time() > _extract_deadline:
            print("  [TIME] extract_coding_genes超时(25s)·转内置fallback", file=__import__('sys').stderr)
            return []
    
    # ③ 合并所有候选词
    all_terms = list(dict.fromkeys(raw_words + decomposed))  # 去重保序
    
    # ④ 按优先级搜索: 短词优先(更可能匹配)
    # 先过滤掉难度标签和通用词
    _DIFFICULTY_TAGS = {"easy", "medium", "hard", "extreme"}
    _GENERIC_WORDS = {"easy", "medium", "hard", "extreme", "title", "description", "label", "icon", "target"}
    tech_terms = [t for t in all_terms if t.isascii() and len(t) >= 2 and t.lower() not in _GENERIC_WORDS]
    # 如果没有过滤后的技术词，再尝试包含难度标签的
    if not tech_terms:
        tech_terms = [t for t in all_terms if t.isascii() and len(t) >= 2]
    for t in tech_terms[:5]:
        q = t[:15]
        r = search_lge(q, 3)
        if r:
            results.extend(r)
            break  # 一个技术词搜到就够了
        if time.time() > _extract_deadline:
            print("  [TIME] extract_coding_genes超时(25s)·转内置fallback", file=__import__('sys').stderr)
            return []
    
    # 再搜中文词
    if not results:
        cn_terms = [t for t in all_terms if not t.isascii() and len(t) >= 2]
        for t in cn_terms[:3]:
            r = search_lge(t[:10], 3)
            if r:
                results.extend(r)
                break
            if time.time() > _extract_deadline:
                print("  [TIME] extract_coding_genes超时(25s)·转内置fallback", file=__import__('sys').stderr)
                return []
    
    # ⑤ 如果全没搜到，用泛编程fallback
    if not results:
        fallbacks = ["编程", "算法", "Python", "设计模式", "代码"]
        for fb in fallbacks:
            r = search_lge(fb, 2)
            if r:
                results.extend(r)
                break
            if time.time() > _extract_deadline:
                print("  [TIME] extract_coding_genes超时(25s)·转内置fallback", file=__import__('sys').stderr)
                return []
    
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
    if not BUILTIN_PATTERNS:
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
        "链表|linked list|listnode|双向链表|反轉|反转链表|合并K个|升序链表|merge k": "linked_list_pattern",
        "最小堆|堆|heap|heapq|priority queue|优先级队列|priorityqueue|堆排序|top k|topk": "heap_pattern",
        "区间树|interval tree|线段树|segment tree|树状数组|fenwick|区间查询|区间更新|重叠查询|range query|range update|interval overlap": "interval_tree_pattern",
        "二叉树|bst|binary tree|二叉搜索树|树|遍历|前序|中序|后序|层次|tree node|treenode|binary search": "bst_pattern",
        "lru|cache缓存|缓存淘汰|最近最少使用|lru缓存|cache实现|least recently|ordereddict": "lru_cache_pattern",
        "测试|test|断言|assert|unittest|pytest|mock|快照|snapshot|验证|验证|集成|unit|覆盖率": "error_handling",
        "跳表|skiplist|skiplistnode|skip list|跳表插入|跳表删除|跳表查找|跳表搜索|memtable|mem_table|memory table|lsm tree|lsm树|lsm存储引擎|sstable|compaction": "skiplist_memtable_pattern",
        "接雨水|trapping rain|双指针|two pointer|two-pointer|相向|快慢指针|滑动窗口|左右指针": "two_pointer_pattern",
        "动态规划|dp|递推|状态转移|最优子结构|背包|fibonacci|斐波那契|LCS|LIS|子序列": "dp_pattern",
        "lru缓存|lru|最近最少使用|cache淘汰|ordereddict|淘汰策略|least recently": "lru_cache_pattern",
        "二分查找|binary search|二分法|二分搜索|二分答案|对数时间|log n": "binary_search_pattern",
        "访问者|visitor|访问者模式|对象结构|新操作": "visitor_pattern",
        "责任链|chain of responsibility|审批流程|处理链": "chain_of_responsibility_pattern",
        "状态机|有限状态|state machine|状态转移|状态模式": "state_machine_pattern",
        "命令模式|command|命令队列|撤销|重做|undo|redo|操作历史": "command_pattern",
        '模板方法|template method|算法骨架|子类实现': 'template_method_pattern',
        '单例|singleton|单例模式|双重检查|双重检查锁定|double check|thread safe|线程安全': 'singleton_pattern',
        '备忘录|memento|状态快照|快照|状态保存': 'memento_pattern',
        "建造者|builder|链式调用|构建复杂对象": "builder_pattern",
        "适配器|adapter|不兼容接口|兼容|转换接口": "adapter_pattern",
        "原型|prototype|克隆|clone|对象副本": "prototype_pattern",
        "门面|facade|简单接口|复杂子系统|统一接口": "facade_pattern",
        "桥接|bridge|抽象与实现|分离实现": "bridge_pattern",
        "组合|composite|树形结构|统一处理|组件树": "composite_pattern",
        "装饰器|decorator|装饰|before/after|增强|钩子": "decorator_pattern",
        "di容器|依赖注入|ioc|注入容器|自动注入|inversion of control": "di_container_pattern",
        "actor|actor模型|消息传递|状态隔离|并发actor": "actor_model_pattern",
        "管道|pipeline|过滤器|filter|数据流|处理链": "pipeline_filter_pattern",
        "actor|actor模型|消息传递|状态隔离|并发actor": "actor_model_pattern",
        "管道|pipeline|过滤器|filter|数据流|处理链": "pipeline_filter_pattern",
        "attention|注意力机制|scaled dot-product|softmax attention|query key value|多头注意|self-attention|transformer|QK|d_k|num_heads": "attention_scaled_dot_product",
        "min-max|min_max|z-score|zscore|数据归一化|feature scale|MinMaxScaler|StandardScaler|数据标准化|最大最小|数据缩放|preprocessing": "data_normalization_pattern",
        "batch|batch_norm|batchnorm|normalization|BN层|batch normalization|layer norm|layer_norm|instance norm|训练模式|推理模式|running_mean|running_var|gamma|beta|moving_average|momentum|梯度计算|dy|dx|dgamma|dbeta|反向传播|backward": "batch_norm_pattern",
        "OOM|内存泄漏|内存泄露|gc|垃圾回收|垃圾收集|tracemalloc|内存溢出|memory leak|memory profiler|堆内存|heap|大对象": "memory_leak_debug",
        "weakref|弱引用|循环引用|circular reference": "weakref_pattern",
        "gc|垃圾回收|垃圾收集|gc阈值|gc调优|garbage collector|垃圾": "gc_tuning_pattern",
        "tracemalloc|内存追踪|memory trace|内存分配|对象分配|对象大小": "tracemalloc_pattern",
        "内存监控|监控内存|memory usage|rss|mem_usage|内存使用|psutil": "mem_usage_monitor",
        "对象存储|块存储|分块上传|断点续传|chunk|upload_id|resume|storage backend|object storage|storage engine": "object_storage_pattern",
        "编码|字符串|encode|decode|unicode|utf|gbk|乱码|中英文|混排|截断|mojibake|byte|bytes|charset|字符集": "string_encoding_utf8",
        "json.*中文|json.*unicode|序列化.*中文|中文.*json|ensure_ascii": "json_encoding_safe",
        "str.*bytes|bytes.*str|字符串.*字节|类型不匹配|类型错误.*编码": "str_bytes_mismatch",
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
    
    # 检查LGE基因是否有真正的编码模式（不含PATTERN标记=假阳性）
    lge_has_real_pattern = any("PATTERN" in g for g in genes[:3]) if genes else False
    lge_is_valid = genes and lge_has_real_pattern
    
    # 内置模式fallback（两个触发条件）:
    #   a) LGE全离线/全空 → 直接取代
    #   b) LGE返回假阳性（无PATTERN标记）但有更好的内置模式 → 优先用内置
    if BUILTIN_PATTERNS:
        builtin_genes = search_builtin_patterns(task_desc)
        if not genes and builtin_genes:
            # 条件a: LGE全空
            print(f"  [OK] LGE全离线·使用内置模式fallback → {len(builtin_genes)}条", file=sys.stderr)
            genes = builtin_genes
        elif genes and not lge_is_valid and builtin_genes:
            # 条件b: LGE假阳性但内置匹配→以内置为准
            print(f"  [OK] LGE假阳性({len(genes)}条无代码模式)·以内置模式替代({len(builtin_genes)}条)", file=sys.stderr)
            genes = builtin_genes
    
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
