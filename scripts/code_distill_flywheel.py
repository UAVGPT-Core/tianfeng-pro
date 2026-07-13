#!/usr/bin/env python3
"""
天锋PRO·代码基因蒸馏飞轮 v1.0
==============================
2035核心: 每次编程自动蒸馏为LGE基因
  成功代码 → 提取设计模式·算法·架构 → LGE基因库
  失败代码 → 提取根因 → Bug修复题库
  踩坑经验 → 提取教训 → 永久免疫

七自闭环: 自感知(扫描代码)→自协调(分类提取)→自进化(纳LGE)→
          自迭代(反馈评分)→自反思(对比历史)→自约束(阈值门控)
"""

import json, sqlite3, os, urllib.request, uuid, re
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/Users/a112233"))
LGE_URL = "http://100.116.0.29:8200"
DISTILL_DB = HOME / "lgox-ops/data/code-distill-flywheel.db"

def init_db():
    conn = sqlite3.connect(DISTILL_DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS distilled_genes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT, category TEXT,
            pattern_name TEXT, content TEXT,
            gene_id TEXT, confidence REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS bug_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT, bug_type TEXT,
            root_cause TEXT, fix_pattern TEXT,
            gene_id TEXT, severity TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS flywheel_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT, files_scanned INTEGER,
            patterns_found INTEGER, bugs_found INTEGER,
            genes_written INTEGER, duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    return conn


# ══════════════════════════════════════════
# 模式提取引擎
# ══════════════════════════════════════════

PATTERN_DETECTORS = [
    # (类别, 模式名, 检测正则, 基因描述模板)
    ("设计模式", "单例模式", 
     r"__new__.*cls.*not.*hasattr|_instance\s*=\s*None|SingletonMeta",
     "单例模式:通过__new__或元类确保全局唯一实例。线程安全需加锁"),
    ("设计模式", "工厂模式",
     r"def\s+(create|build|make|factory)_.*\(",
     "工厂模式:用工厂方法创建对象，解耦调用方和具体类。返回抽象类型"),
    ("设计模式", "观察者模式",
     r"(subscribe|unsubscribe|notify|add_listener|Observer)",
     "观察者模式:发布-订阅机制，支持一对多通知。注意内存泄漏(weakref)"),
    ("设计模式", "策略模式",
     r"(strategy|Strategy).*\.(execute|run|apply|do)",
     "策略模式:运行时切换算法。将算法封装为可替换的策略对象"),
    ("设计模式", "装饰器模式",
     r"@\w+\s*\ndef |def\s+wrapper\s*\(|functools\.wraps",
     "装饰器模式:在不修改原函数的情况下扩展功能。支持before/after钩子"),
    
    ("算法", "LRU缓存",
     r"lru_cache|LRUCache|OrderedDict.*move_to_end|@lru_cache",
     "LRU缓存:最近最少使用淘汰策略。O(1)get/put。核心:双向链表+哈希表"),
    ("算法", "动态规划",
     r"dp\s*=\s*\[|@cache\s*\ndef|cache.*memo|memoize",
     "动态规划:分解子问题，缓存中间结果。关键:状态定义+转移方程+边界"),
    ("算法", "二分查找",
     r"bisect|mid\s*=\s*.*//\s*2|binary.search|left,right\s*=",
     "二分查找:O(log n)定位。注意mid溢出(用left+(right-left)//2)"),
    ("算法", "BFS广度优先",
     r"deque\(\s*\[|popleft\(\)|queue\.append|\.popleft",
     "BFS:用deque实现队列。逐层扩展。visited集合防重复。适用于最短路径"),
    ("算法", "DFS回溯",
     r"def\s+dfs\s*\(|backtrack\s*\(|\.append.*\.pop\(\)",
     "DFS回溯:递归探索+剪枝。关键:路径记录+状态恢复(path.pop())"),
    ("算法", "Kadane算法",
     r"max_so_far|max_ending|current_sum|cur_max",
     "Kadane:最大子数组和O(n)。核心:cur=max(num,cur+num)·global=max(global,cur)"),
    
    ("架构", "上下文管理器",
     r"def\s+__enter__|def\s+__exit__|with\s+.*as\s+\w+:",
     "上下文管理器:用with确保资源释放。实现__enter__+__exit__或@contextmanager"),
    ("架构", "异常处理链",
     r"try:.*except\s+\w+\s+as\s+\w+:.*raise",
     "异常处理:捕获→日志→转换→上抛。不要吞异常。记录上下文信息"),
    ("架构", "类型提示",
     r"def\s+\w+\([^)]*:\s*(int|str|bool|list|dict|Optional|Union)",
     "类型提示:增强可读性和IDE支持。用Optional表示None·Union表示多类型"),
    
    ("踩坑免疫", "循环引用泄漏",
     r"__del__|gc\.collect|weakref|circular",
     "循环引用泄漏:__del__阻止GC。用weakref.ref打破循环。不用__del__"),
    ("踩坑免疫", "可变默认参数",
     r"def\s+\w+\(\w+=\[\]|def\s+\w+\(\w+=\{\}",
     "可变默认参数:def f(x=[])共享同一list。改为x=None→if x is None:x=[]"),
    ("踩坑免疫", "并发竞争",
     r"threading\.Lock|threading\.RLock|with\s+self\._lock|Lock\(\)",
     "并发竞争:共享数据需锁保护。用with lock确保释放。避免死锁(固定获取顺序)"),
]


def extract_patterns(code, filepath=""):
    """从代码中提取设计模式/算法/架构/踩坑"""
    found = []
    seen = set()
    
    for category, name, regex, desc in PATTERN_DETECTORS:
        if name in seen: continue
        if re.search(regex, code, re.IGNORECASE | re.DOTALL):
            found.append({
                "category": category,
                "name": name,
                "description": desc,
                "source_file": filepath,
                "confidence": 0.7 if re.search(regex, code, re.IGNORECASE) else 0.5,
            })
            seen.add(name)
    
    return found


def extract_bugs(code, filepath=""):
    """从代码中检测Bug和反模式"""
    bugs = []
    
    bug_detectors = [
        ("资源泄漏", r"open\([^)]+\)(?!.*with).*\n(?!.*close)", "high",
         "文件未用with管理，可能泄露。改用with open() as f"),
        ("裸异常", r"except\s*:", "medium",
         "裸except捕获所有异常包括KeyboardInterrupt。指定具体异常类型"),
        ("SQL注入", r"f['\"].*SELECT.*\{|format.*SELECT|%.*SELECT", "critical",
         "SQL拼接有注入风险。用参数化查询(?占位符)代替字符串拼接"),
        ("硬编码密钥", r"(api_key|secret|password|token)\s*=\s*['\"][^'\"]{8,}", "critical",
         "硬编码密钥泄露风险。从环境变量或配置文件读取"),
        ("阻塞IO", r"time\.sleep\(\d+\)|requests\.get\(.*\)\s*$", "low",
         "同步IO阻塞。考虑异步(async/await)或线程池"),
    ]
    
    for bug_type, regex, severity, fix in bug_detectors:
        if re.search(regex, code):
            bugs.append({
                "bug_type": bug_type,
                "severity": severity,
                "root_cause": f"代码中存在{bug_type}模式",
                "fix_pattern": fix,
                "source_file": filepath,
            })
    
    return bugs


# ══════════════════════════════════════════
# 主飞轮
# ══════════════════════════════════════════

def scan_files():
    """扫描灵龙最近有变更的代码文件"""
    files = []
    scripts_dir = HOME / "lgox-ops/scripts"
    if scripts_dir.exists():
        for f in sorted(scripts_dir.glob("*.py"), key=lambda x: x.stat().st_mtime, reverse=True)[:15]:
            if f.stat().st_size < 50000:
                files.append(f)
    
    bin_dir = HOME / "bin"
    if bin_dir.exists():
        for f in sorted(bin_dir.glob("*.py"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            if f.stat().st_size < 20000:
                files.append(f)
    
    return files


def run_flywheel():
    conn = init_db()
    c = conn.cursor()
    start = datetime.now()
    run_id = f"cdf-{start.strftime('%Y%m%d-%H%M%S')}"
    
    files = scan_files()
    total_patterns = 0
    total_bugs = 0
    total_genes = 0
    
    for f in files:
        try:
            code = f.read_text()[:4000]
        except:
            continue
        
        # 提取模式
        patterns = extract_patterns(code, str(f))
        for p in patterns:
            c.execute("SELECT COUNT(*) FROM distilled_genes WHERE pattern_name=? AND source_file=?",
                      (p["name"], str(f)))
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO distilled_genes (source_file,category,pattern_name,content,confidence) VALUES (?,?,?,?,?)",
                          (str(f), p["category"], p["name"], p["description"], p["confidence"]))
                total_patterns += 1
                
                # 纳LGE基因(快速超时·不阻塞)
                try:
                    lge_data = json.dumps({
                        "content": f"[天锋PRO·代码蒸馏·{p['category']}] {p['name']}: {p['description']} 来源:{f.name}",
                        "memory_type": "semantic",
                        "source": "code-distill-flywheel"
                    }).encode()
                    req = urllib.request.Request(LGE_URL + "/genes/write", data=lge_data,
                                                  headers={"Content-Type": "application/json"})
                    resp = urllib.request.urlopen(req, timeout=8)
                    gid = json.loads(resp.read()).get("gene_id", "")
                    if gid:
                        c.execute("UPDATE distilled_genes SET gene_id=? WHERE pattern_name=? AND source_file=?",
                                  (gid, p["name"], str(f)))
                        total_genes += 1
                except:
                    pass  # LGE超时不阻塞飞轮
        
        # 提取Bug
        bugs = extract_bugs(code, str(f))
        for b in bugs:
            c.execute("SELECT COUNT(*) FROM bug_lessons WHERE source_file=? AND bug_type=?",
                      (str(f), b["bug_type"]))
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO bug_lessons (source_file,bug_type,root_cause,fix_pattern,severity) VALUES (?,?,?,?,?)",
                          (str(f), b["bug_type"], b["root_cause"], b["fix_pattern"], b["severity"]))
                total_bugs += 1
    
    conn.commit()
    duration = int((datetime.now() - start).total_seconds() * 1000)
    
    c.execute("INSERT INTO flywheel_runs (run_id,files_scanned,patterns_found,bugs_found,genes_written,duration_ms) VALUES (?,?,?,?,?,?)",
              (run_id, len(files), total_patterns, total_bugs, total_genes, duration))
    
    c.execute("SELECT COUNT(*) FROM distilled_genes")
    total_distilled = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bug_lessons")
    total_bug_lessons = c.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    result = {
        "run_id": run_id,
        "files": len(files),
        "patterns": total_patterns,
        "bugs": total_bugs,
        "genes": total_genes,
        "total_distilled": total_distilled,
        "total_bugs": total_bug_lessons,
        "duration_ms": duration,
    }
    
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run_flywheel()
