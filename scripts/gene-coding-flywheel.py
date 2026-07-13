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

import json, sqlite3, os, urllib.request, uuid, time, subprocess
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/Users/a112233"))
# LGE基因库集群（三级降级: 地枢主库→天枢LGE→灵龙LGA本地）
LGE_POOL = [
    "http://100.116.0.29:8200",   # 【主】地枢DGX2（791K基因）
    "http://100.100.89.2:8201",   # 【备1】天枢LGE Studio（829基因）
    "http://127.0.0.1:8202",      # 【备2】灵龙LGA本地代理（33基因）
]
LGE_URL = "http://100.116.0.29:8200"  # 保留原变量名作为默认首选
FTS5_DB = HOME / "lge-studio/data/lge_fts.db"  # 不存在于灵龙，仅在天枢
FLYWHEEL_DB = HOME / "lgox-ops/data/gene-coding-flywheel.db"
MY_NODE = "灵龙"

# 节点连通性缓存（减少重试）
_connectivity_cache = {}

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
    """基因感知: 多词短搜索+LGE检索（LGE不支持长中文/特殊字符查询）"""
    results = []
    
    # 提取任务关键词（去特殊字符，拆短词）
    import re
    clean = re.sub(r'[⚡·—•→★🐛🗄️🤖🔧📊🔄📦]', ' ', task_description)
    # 从任务描述提取有意义的关键词
    words = [w.strip() for w in clean.replace(':', ' ').replace('/', ' ').split() if len(w.strip()) >= 2]
    
    # 用每个关键词独立搜索（LGE不支持长query）
    for word in words[:5]:
        q = word[:20]  # 确保不超长
        r = search_lge(q, 3)
        if r:
            results.extend(r)
    
    # 如果没搜到，尝试泛编程查询
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
                        "Dijkstra", "Kadane", "二分", "动态规划", "回溯"]
    for pk in pattern_keywords:
        if pk in code: score += 2; details.append(f"模式:{pk}+2")
    
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
    import sys
    sys.path.insert(0, str(HOME / "lgox-ops/scripts"))
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
    
    # ① 感知: 检索基因
    genes = extract_coding_genes(task_desc)
    total_genes = len(genes)
    
    # ② 注入: 构建Prompt
    prompt = build_gene_prompt(task_desc, genes)
    total_injected = min(len(genes), 8)
    
    # ③ 评分: 如果有现有的代码基因库，计算平均分
    c.execute("SELECT AVG(score) FROM code_genes")
    avg_score = c.fetchone()[0] or 0
    
    # ④ 纳库: 将检索到的优质基因标记
    for g in genes[:5]:
        gid = f"GENE-CODE-{uuid.uuid4().hex[:8]}"
        content = g[:300]
        score, _ = score_code(content)
        if score >= 60:
            c.execute("INSERT OR IGNORE INTO code_genes (gene_id,category,content,source,score) VALUES (?,?,?,?,?)",
                      (gid, "injected", content, "gene-coding-flywheel", score))
            total_new += 1
    
    # ⑤ 记录运行
    duration = int((datetime.now() - start).total_seconds() * 1000)
    flywheel_score = min(100, 50 + total_genes * 3 + total_new * 5)
    
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
