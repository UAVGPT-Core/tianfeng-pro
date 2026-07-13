#!/usr/bin/env python3
"""
天锋PRO·编程质量飞轮 v1.0
==========================
五维自动评分: 正确性·性能·安全·可读·基因密度
2035核心: 每次编程都评分·每次评分都纳基因·越写越聪明

流程:
  ① 收集: 读取最近生成的代码
  ② 评分: 五维质量评估
  ③ 纳库: 优质代码→LGE基因·劣质代码→Bug题库
  ④ 蒸馏: 提取设计模式·算法·踩坑
  ⑤ 闭环: cron永动
"""

import json, sqlite3, os, urllib.request, uuid, subprocess, re
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/Users/a112233"))
LGE_URL = "http://100.116.0.29:8200"
QUALITY_DB = HOME / "lgox-ops/data/code-quality-flywheel.db"

def init_db():
    conn = sqlite3.connect(QUALITY_DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS quality_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, code_hash TEXT UNIQUE,
            correctness REAL, performance REAL, security REAL,
            readability REAL, gene_density REAL, total REAL,
            grade TEXT, patterns TEXT, issues TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS patterns_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT, category TEXT, count INTEGER DEFAULT 1,
            gene_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS flywheel_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT, codes_scanned INTEGER, codes_scored INTEGER,
            patterns_found INTEGER, genes_written INTEGER,
            avg_score REAL, duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    return conn


# ══════════════════════════════════════════
# 五维评分引擎
# ══════════════════════════════════════════

def score_correctness(code):
    """正确性评分 (0-10): 语法·逻辑·边界"""
    score = 5
    try:
        compile(code, "<test>", "exec")
        score += 3  # 语法正确
    except:
        return 0, ["语法错误"]
    
    # 基本模式检查
    checks = [
        ("def\|class", 1, "有函数或类定义"),
        ("return\|yield", 1, "有返回值"),
        ("try.*except", 1, "有异常处理"),
        ("assert\|raise", 0.5, "有断言或错误抛出"),
    ]
    details = []
    for pat, pts, desc in checks:
        if re.search(pat, code):
            score += pts
            details.append(desc)
    
    return min(10, score), details


def score_performance(code):
    """性能评分 (0-10): 复杂度·优化"""
    score = 5
    details = []
    
    # O标记
    complexity_match = re.findall(r'O\([^)]+\)', code)
    if complexity_match:
        details.append(f"复杂度标注:{complexity_match[0]}")
    
    # 优化检测
    optimizations = [
        (r"cache\|lru\|@lru_cache", 2, "缓存/LRU"),
        (r"set\s*\(|dict\s*\(|hash", 1, "哈希结构"),
        (r"sqlite\|sql\b", 1, "数据库操作"),
        (r"\.join\(", 1, "字符串优化join"),
        (r"yield\b|generator", 1, "生成器使用"),
        (r"collections\.", 1, "高效数据结构"),
        (r"with\s+.*as", 0.5, "上下文管理器"),
    ]
    for pat, pts, desc in optimizations:
        if re.search(pat, code, re.IGNORECASE):
            score += pts
            details.append(desc)
    
    # 反模式
    antipatterns = [
        (r"for\s+.*in\s+range\(len\(", -2, "len(range())反模式"),
        (r"\.append\(.*\)\s*\+\s*=", -1, "+=替代append"),
        (r"time\.sleep\(\d+\)", -1, "硬编码sleep"),
    ]
    for pat, pts, desc in antipatterns:
        if re.search(pat, code):
            score += pts
            details.append(f"⚠️ {desc}")
    
    return min(10, max(0, score)), details


def score_security(code):
    """安全评分 (0-10): 漏洞·加密·输入验证"""
    score = 8  # 默认乐观
    details = []
    
    # 危险模式
    dangers = [
        (r"exec\s*\(|eval\s*\(", -5, "🔴 exec/eval"),
        (r"os\.system\s*\(|subprocess\.call\s*\(.*shell=True", -3, "🔴 shell注入风险"),
        (r"password\s*=\s*['\"]", -3, "🔴 硬编码密码"),
        (r"pickle\.loads?\s*\(", -2, "⚠️ pickle反序列化"),
        (r"SELECT.*%.*FROM|INSERT.*%.*VALUES", -3, "🔴 SQL注入"),
    ]
    for pat, pts, desc in dangers:
        if re.search(pat, code):
            score += pts
            details.append(desc)
    
    # 安全模式
    safes = [
        (r"hashlib\.|bcrypt|argon2", 2, "✅ 密码哈希"),
        (r"urllib\.parse\.quote|html\.escape|escape\(", 1, "✅ 输入转义"),
        (r"ssl\.|https://|tls", 1, "✅ 加密通信"),
        (r"\.strip\(\)|\.sanitize|validate", 1, "✅ 输入验证"),
    ]
    for pat, pts, desc in safes:
        if re.search(pat, code, re.IGNORECASE):
            score += pts
            details.append(desc)
    
    return min(10, max(0, score)), details


def score_readability(code):
    """可读性评分 (0-10): 命名·注释·结构"""
    score = 5
    details = []
    
    # 好习惯
    goods = [
        (r'"""|\'\'\'', 2, "文档字符串"),
        (r"#\s", 1, "有注释"),
        (r"def\s+[a-z_][a-z0-9_]*\(", 1, "函数命名规范"),
        (r"class\s+[A-Z][a-zA-Z0-9]*", 1, "类命名规范"),
        (r"if\s+__name__\s*==\s*['\"]__main__", 1, "有入口保护"),
        (r"type\s+hint|->\s*\w+:|:\s*(int|str|bool|list|dict|Optional)", 2, "类型提示"),
    ]
    for pat, pts, desc in goods:
        if re.search(pat, code):
            score += pts
            details.append(desc)
    
    # 坏习惯
    bads = [
        (r"def\s+[A-Z]", -2, "函数名大写"),
        (r".{120,}", -1, "超长行"),
        (r"^\s{8,}", -0.5, "过深缩进"),
    ]
    for pat, pts, desc in bads:
        if re.search(pat, code, re.MULTILINE):
            score += pts
            details.append(f"⚠️ {desc}")
    
    return min(10, max(0, score)), details


def score_gene_density(code):
    """基因密度评分 (0-10): 是否使用了已知的编程基因模式"""
    score = 0
    details = []
    
    # 设计模式
    patterns = {
        "单例": ["__new__", "hasattr.*_instance", "Singleton"],
        "工厂": ["Factory", "create_", "build_"],
        "观察者": ["Observer", "subscribe", "notify", "add_listener"],
        "策略": ["Strategy", "strategy"],
        "装饰器": ["@", "wrapper", "decorator"],
        "LRU缓存": ["LRU", "lru_cache", "OrderedDict"],
        "Trie": ["Trie", "prefix"],
        "动态规划": ["dp\[", "@cache", "memo", "optim"],
        "二分": ["bisect", "mid\s*=", "binary_search"],
        "并查集": ["UnionFind", "find\(self", "parent\["],
        "堆": ["heapq", "heappush", "heappop"],
        "BFS": ["deque\(|popleft|queue\.append", "visited"],
        "DFS": ["def dfs", "backtrack"],
    }
    
    for pname, indicators in patterns.items():
        if all(re.search(ind, code) for ind in indicators[:2]):
            score += 1.5
            details.append(pname)
    
    return min(10, score), details


def grade(score):
    if score >= 9: return "S"
    if score >= 7.5: return "A"
    if score >= 6: return "B"
    if score >= 4: return "C"
    return "D"


def score_all(code):
    """五维全评分"""
    results = {}
    results["correctness"], _ = score_correctness(code)
    results["performance"], _ = score_performance(code)
    results["security"], _ = score_security(code)
    results["readability"], _ = score_readability(code)
    results["gene_density"], _ = score_gene_density(code)
    
    total = sum(results.values()) / 5
    results["total"] = round(total, 1)
    results["grade"] = grade(total)
    
    # 提取发现的模式
    _, patterns = score_gene_density(code)
    _, issues = score_security(code)
    results["patterns"] = patterns
    results["issues"] = [i for i in issues if "🔴" in i or "⚠️" in i]
    
    return results


# ══════════════════════════════════════════
# 主飞轮
# ══════════════════════════════════════════

def scan_code_sources():
    """扫描灵龙最近的代码产出"""
    sources = []
    
    # 扫描scripts目录最近修改的py文件
    scripts_dir = HOME / "lgox-ops/scripts"
    if scripts_dir.exists():
        for f in sorted(scripts_dir.glob("*.py"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            try:
                content = f.read_text()[:3000]  # 取前3000字符
                if len(content) > 100:
                    sources.append({
                        "path": str(f),
                        "code": content,
                        "hash": str(hash(content))
                    })
            except:
                pass
    
    # 也扫描.bin目录
    bin_dir = HOME / "bin"
    if bin_dir.exists():
        for f in sorted(bin_dir.glob("tianfeng*"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            try:
                content = f.read_text()[:3000]
                if len(content) > 50:
                    sources.append({
                        "path": str(f),
                        "code": content,
                        "hash": str(hash(content))
                    })
            except:
                pass
    
    return sources


def run_flywheel():
    conn = init_db()
    c = conn.cursor()
    start = datetime.now()
    run_id = f"cqf-{start.strftime('%Y%m%d-%H%M%S')}"
    
    sources = scan_code_sources()
    total_scored = 0
    total_patterns = 0
    total_genes = 0
    scores = []
    
    for src in sources:
        # 避免重复评分
        c.execute("SELECT id FROM quality_scores WHERE code_hash=?", (src["hash"],))
        if c.fetchone():
            continue
        
        # 五维评分
        result = score_all(src["code"])
        total_scored += 1
        scores.append(result["total"])
        
        # 写入质量DB
        c.execute("""INSERT OR IGNORE INTO quality_scores 
            (source,code_hash,correctness,performance,security,readability,gene_density,total,grade,patterns,issues)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (src["path"], src["hash"],
             result["correctness"], result["performance"],
             result["security"], result["readability"],
             result["gene_density"], result["total"],
             result["grade"],
             json.dumps(result["patterns"]),
             json.dumps(result["issues"])))
        
        # 发现的新模式纳基因
        for pattern in result.get("patterns", []):
            c.execute("SELECT count FROM patterns_found WHERE pattern=?", (pattern,))
            existing = c.fetchone()
            if existing:
                c.execute("UPDATE patterns_found SET count=count+1 WHERE pattern=?", (pattern,))
            else:
                c.execute("INSERT INTO patterns_found (pattern,category) VALUES (?,?)",
                          (pattern, "design_pattern"))
            total_patterns += 1
        
        # 优质代码纳LGE基因
        if result["grade"] in ("S", "A") and result["gene_density"] >= 5:
            try:
                gid = f"GENE-CODE-QUALITY-{uuid.uuid4().hex[:8]}"
                lge_data = json.dumps({
                    "content": f"[天锋PRO·质量飞轮·{result['grade']}级] {src['path']} "
                               f"评分{result['total']} 正确{result['correctness']} "
                               f"性能{result['performance']} 安全{result['security']}",
                    "memory_type": "semantic",
                    "source": "code-quality-flywheel"
                }).encode()
                req = urllib.request.Request(LGE_URL + "/genes/write", data=lge_data,
                                              headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=8)
                total_genes += 1
            except:
                pass
    
    conn.commit()
    
    # 运行记录
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    duration = int((datetime.now() - start).total_seconds() * 1000)
    
    c.execute("INSERT INTO flywheel_runs (run_id,codes_scanned,codes_scored,patterns_found,genes_written,avg_score,duration_ms) VALUES (?,?,?,?,?,?,?)",
              (run_id, len(sources), total_scored, total_patterns, total_genes, avg, duration))
    
    # 统计
    c.execute("SELECT COUNT(*) FROM quality_scores")
    total_quality = c.fetchone()[0]
    c.execute("SELECT AVG(total) FROM quality_scores")
    global_avg = round(c.fetchone()[0] or 0, 1)
    
    conn.commit()
    conn.close()
    
    result = {
        "run_id": run_id,
        "scanned": len(sources),
        "scored": total_scored,
        "avg_score": avg,
        "global_avg": global_avg,
        "total_quality": total_quality,
        "patterns": total_patterns,
        "genes": total_genes,
        "duration_ms": duration,
    }
    
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run_flywheel()
