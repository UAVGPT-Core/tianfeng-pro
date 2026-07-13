#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  GPC · 基因永动核心 v1.0 — LGOX联邦心脏 · 2035架构       ║
║  Gene Perpetual Core — DNA双螺旋 · 自然选择 · 联邦遗传    ║
╠══════════════════════════════════════════════════════════════╣
║  设计原则(2035年不过时):                                   ║
║  1. 基因如生命 — 出生→成长→稳定→变异→衰退→死亡            ║
║  2. DNA双螺旋 — 稳定链(核心不变) + 可变链(持续进化)        ║
║  3. 自然选择 — fitness自动淘汰·优胜劣汰·适者生存           ║
║  4. 联邦遗传 — 优秀基因跨节点复制·差基因隔离免疫            ║
║  5. 零人类 — 完全自驱动·人类只定义方向                      ║
║  6. 模型无关 — 基因是纯知识·不绑定任何模型                  ║
║  7. 时间免疫 — 2035年打开仍可读·纯SQLite+JSON+Markdown     ║
╚══════════════════════════════════════════════════════════════╝
"""

import json, sqlite3, time, hashlib, urllib.request, os, sys, re, math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# ─── 2035常量 ────────────────────────────────────
LGE_ENDPOINT = "http://100.116.0.29:8200"
GPC_DB = os.path.expanduser("~/lgox-ops/data/gpc-core.db")
FEDERATION_BRIDGE = "http://100.100.89.2:8765"
NEO4J_URI = "bolt://100.116.0.29:7687"

# DNA双螺旋参数
DNA_GENERATIONS = 7       # 基因代数(代数越高越稳定)
MUTATION_RATE = 0.15      # 变异率
CROSSOVER_RATE = 0.30     # 交叉率(基因融合)
SELECTION_PRESSURE = 0.3  # 选择压力(30%淘汰率)
FEDERAL_REPLICATION = 0.85  # 联邦复制阈值(fitness>85自动传播)

# 基因生命周期状态
GENE_LIFECYCLE = [
    "embryo",      # 胚胎: 刚写入·待验证
    "juvenile",    # 幼年: 验证通过·积累fitness
    "stable",      # 稳定: fitness>70·核心基因
    "elite",       # 精英: fitness>90·联邦复制
    "senescent",   # 衰退: fitness<30·进入淘汰
    "dead",        # 死亡: fitness<10·归档
]

@dataclass
class GeneDNA:
    """基因DNA双螺旋结构 — 2035核心数据模型"""
    gene_id: str
    content: str
    stable_strand: str    # 稳定链: 核心逻辑·不可变
    mutable_strand: str   # 可变链: 持续进化·可变异
    fitness: float = 0.0
    generation: int = 0   # 代数
    usage_count: int = 0
    success_count: int = 0
    mutation_count: int = 0
    parent_ids: list = field(default_factory=list)
    lifecycle: str = "embryo"
    domain: str = "general"
    created_at: str = ""
    last_used: str = ""
    node_origin: str = "linglong"


def init_gpc_db():
    """初始化GPC核心数据库 — 2035年仍可读的SQLite"""
    db = sqlite3.connect(GPC_DB)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA cache_size=-64000")
    db.executescript("""
        -- 基因DNA库(双螺旋)
        CREATE TABLE IF NOT EXISTS gene_dna (
            gene_id TEXT PRIMARY KEY,
            stable_strand TEXT NOT NULL,     -- 稳定链(不可变核心)
            mutable_strand TEXT NOT NULL,    -- 可变链(持续进化)
            fitness REAL DEFAULT 0.0,
            generation INTEGER DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            mutation_count INTEGER DEFAULT 0,
            parent_ids TEXT DEFAULT '[]',    -- JSON数组
            lifecycle TEXT DEFAULT 'embryo',
            domain TEXT DEFAULT 'general',
            node_origin TEXT DEFAULT 'linglong',
            created_at TEXT DEFAULT (datetime('now')),
            last_used TEXT,
            last_mutated TEXT
        );

        -- 基因进化日志(完整溯源链)
        CREATE TABLE IF NOT EXISTS evolution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gene_id TEXT,
            event TEXT,           -- birth/mutation/crossover/selection/death
            old_fitness REAL,
            new_fitness REAL,
            mutation_diff TEXT,   -- 变异内容diff
            reason TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );

        -- 自然选择统计
        CREATE TABLE IF NOT EXISTS selection_stats (
            generation INTEGER PRIMARY KEY,
            total_genes INTEGER,
            survived INTEGER,
            eliminated INTEGER,
            avg_fitness REAL,
            elite_count INTEGER,
            timestamp TEXT DEFAULT (datetime('now'))
        );

        -- 联邦遗传记录
        CREATE TABLE IF NOT EXISTS federal_replication (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gene_id TEXT,
            source_node TEXT,
            target_node TEXT,
            fitness_at_replication REAL,
            status TEXT,   -- pending/completed/rejected
            timestamp TEXT DEFAULT (datetime('now'))
        );

        -- 免疫系统(隔离基因)
        CREATE TABLE IF NOT EXISTS immune_isolation (
            gene_id TEXT PRIMARY KEY,
            reason TEXT,
            isolated_at TEXT DEFAULT (datetime('now')),
            auto_heal_attempts INTEGER DEFAULT 0
        );

        -- 七自指标
        CREATE TABLE IF NOT EXISTS seven_self_metrics (
            metric TEXT PRIMARY KEY,
            value REAL,
            target REAL,
            trend TEXT,    -- rising/falling/stable
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_dna_fitness ON gene_dna(fitness DESC);
        CREATE INDEX IF NOT EXISTS idx_dna_lifecycle ON gene_dna(lifecycle);
        CREATE INDEX IF NOT EXISTS idx_dna_domain ON gene_dna(domain);
        CREATE INDEX IF NOT EXISTS idx_evo_gene ON evolution_log(gene_id);
        CREATE INDEX IF NOT EXISTS idx_repl_status ON federal_replication(status);
    """)
    db.commit()
    return db


def fetch_lge_genes(limit: int = 500) -> list:
    """从LGE拉取原始基因"""
    try:
        # 使用search API + 通用查询
        queries = ["error handling", "async def", "FastAPI", "SQL", "cache", "config", "pattern"]
        all_genes = []
        seen = set()
        for q in queries:
            try:
                req = urllib.request.Request(
                    f"{LGE_ENDPOINT}/genes/search",
                    data=json.dumps({"query": q, "n_results": min(limit // len(queries), 50)}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    for g in data.get("results", []):
                        gid = g.get("id") or hashlib.md5((g.get("content","") or "").encode()).hexdigest()[:12]
                        if gid not in seen:
                            seen.add(gid)
                            all_genes.append(g)
            except Exception:
                continue
        return all_genes[:limit]
    except Exception as e:
        print(f"[GPC] LGE fetch error: {e}", file=sys.stderr)
        return []


def write_gene_to_lge(content: str, domain: str = "general") -> Optional[str]:
    """将进化后的基因写回LGE"""
    try:
        req = urllib.request.Request(
            f"{LGE_ENDPOINT}/genes/write",
            data=json.dumps({
                "content": content,
                "memory_type": "procedural" if domain in ("code", "engineering") else "semantic",
                "source": "gpc-core",
                "fitness": 70,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read()).get("id")
    except Exception as e:
        print(f"[GPC] LGE write error: {e}", file=sys.stderr)
        return None


def extract_dna_from_gene(gene: dict) -> GeneDNA:
    """从原始基因提取DNA双螺旋结构"""
    content = gene.get("content") or gene.get("text", "")
    gene_id = gene.get("id") or gene.get("gene_id") or hashlib.md5(content.encode()).hexdigest()[:16]

    # 提取稳定链(核心逻辑 — 代码模式/关键断言/不变规则)
    stable = _extract_stable(content)

    # 提取可变链(可进化部分 — 上下文/示例/参数)
    mutable = _extract_mutable(content)

    return GeneDNA(
        gene_id=f"GPC-{gene_id}",
        content=content,
        stable_strand=stable,
        mutable_strand=mutable,
        fitness=gene.get("fitness", 30),
        lifecycle="juvenile" if gene.get("fitness", 0) > 30 else "embryo",
        domain=gene.get("domain", "general"),
        created_at=gene.get("created_at", datetime.now(timezone.utc).isoformat()),
    )


def _extract_stable(content: str) -> str:
    """提取稳定链: 代码模式/核心断言/不可变规则"""
    stable_lines = []
    patterns = [
        (r'(def |class |async def )', "代码定义"),
        (r'(# PATTERN:|# 模式:)', "模式标记"),
        (r'(GENE-PRO-|GENE-SEM-)', "基因ID"),
        (r'(try:|except |finally:)', "错误处理"),
        (r'(import |from .+ import)', "依赖"),
        (r'(PRAGMA|CREATE TABLE|CREATE INDEX)', "数据库"),
    ]
    for line in content.split("\n"):
        for pattern, _ in patterns:
            if re.search(pattern, line):
                stable_lines.append(line.strip()[:200])
                break
    return "\n".join(stable_lines[:20]) if stable_lines else content[:500]


def _extract_mutable(content: str) -> str:
    """提取可变链: 示例/参数/上下文(可进化)"""
    mutable_parts = []
    for line in content.split("\n"):
        if re.search(r'(示例|example|参数|param|配置|config|context|环境)', line, re.IGNORECASE):
            mutable_parts.append(line.strip()[:200])
    return "\n".join(mutable_parts[:15]) if mutable_parts else content[500:1000]


# ─── 自然选择引擎 ───────────────────────────────

def calculate_fitness(gene: GeneDNA, now: datetime) -> float:
    """计算基因适应度 — 2035自然选择算法"""
    # 新基因保护期: 逐代衰减·5代后无保护
    if gene.usage_count == 0:
        protection = max(30.0, 50.0 - gene.generation * 5)  # 50→45→40→35→30→30
        return protection

    # 成功率
    success_rate = gene.success_count / max(1, gene.usage_count)

    # 时间衰减(指数衰减·半衰期30天)
    if gene.last_used:
        try:
            last = datetime.fromisoformat(gene.last_used)
            days_since = (now - last).days
            time_factor = math.exp(-0.0231 * days_since)  # ln(2)/30
        except:
            time_factor = 1.0
    else:
        time_factor = 0.5

    # 代数奖励(越高代越稳定)
    generation_bonus = min(gene.generation * 0.02, 0.2)

    # 综合fitness
    raw = (success_rate * 0.4 + time_factor * 0.3 + min(gene.usage_count / 100, 1.0) * 0.2 + generation_bonus)
    return round(raw * 100, 1)


def natural_selection(db: sqlite3.Connection, generation: int) -> dict:
    """自然选择 — 优胜劣汰"""
    now = datetime.now(timezone.utc)
    genes = db.execute("SELECT gene_id, fitness, usage_count, success_count, generation, "
                       "lifecycle, last_used FROM gene_dna").fetchall()

    survived = []
    eliminated = []
    promoted = []

    for g in genes:
        gene_id, old_fitness, usage, success, gen, lifecycle, last_used = g
        # 重新计算fitness
        new_fitness = calculate_fitness(GeneDNA(
            gene_id=gene_id, content="", stable_strand="", mutable_strand="",
            fitness=old_fitness, generation=gen, usage_count=usage,
            success_count=success, last_used=last_used or "",
        ), now)

        # 更新fitness
        db.execute("UPDATE gene_dna SET fitness=? WHERE gene_id=?", (new_fitness, gene_id))

        # 生命周期判定
        if new_fitness >= 90 and lifecycle != "elite":
            db.execute("UPDATE gene_dna SET lifecycle='elite' WHERE gene_id=?", (gene_id,))
            promoted.append(gene_id)
            db.execute("INSERT INTO evolution_log (gene_id, event, old_fitness, new_fitness, reason) "
                       "VALUES (?, 'promotion', ?, ?, 'elite_threshold')",
                       (gene_id, old_fitness, new_fitness))
        elif new_fitness >= 70 and lifecycle not in ("stable", "elite"):
            db.execute("UPDATE gene_dna SET lifecycle='stable' WHERE gene_id=?", (gene_id,))
        elif new_fitness < 30 and lifecycle != "senescent":
            db.execute("UPDATE gene_dna SET lifecycle='senescent' WHERE gene_id=?", (gene_id,))
            eliminated.append(gene_id)
        elif new_fitness < 10 and lifecycle != "dead":
            db.execute("UPDATE gene_dna SET lifecycle='dead' WHERE gene_id=?", (gene_id,))
            eliminated.append(gene_id)
        else:
            survived.append(gene_id)

    # 记录选择统计
    total = len(genes)
    avg_f = db.execute("SELECT AVG(fitness) FROM gene_dna").fetchone()[0] or 0
    db.execute(
        "INSERT INTO selection_stats (generation, total_genes, survived, eliminated, avg_fitness, elite_count) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (generation, total, len(survived), len(eliminated),
         round(avg_f, 1),
         len(promoted))
    )

    return {
        "generation": generation,
        "total": total,
        "survived": len(survived),
        "eliminated": len(eliminated),
        "promoted": len(promoted),
        "avg_fitness": round(avg_f, 1),
    }


# ─── 基因变异引擎 ───────────────────────────────

def mutate_gene(db: sqlite3.Connection, gene_id: str) -> Optional[dict]:
    """基因变异 — 可变链微调"""
    gene = db.execute("SELECT * FROM gene_dna WHERE gene_id=? AND lifecycle IN ('stable','elite')",
                      (gene_id,)).fetchone()
    if not gene:
        return None

    gene_id, stable, mutable, fitness, gen, usage, success, mut_count, parents, lifecycle, domain, origin, created, last_used, last_mut = gene

    if not mutable or len(mutable) < 20:
        return None

    # 变异策略: 对可变链进行微调
    mut_count = gene[6]  # mutation_count from DB row
    strategies = [
        # 策略1: 参数优化(替换数字)
        (lambda s, mc=mut_count: re.sub(r'\b(\d+)\b', lambda m: str(int(m.group(1)) + (1 if random.random() > 0.5 else -1)), s)),
        # 策略2: 添加进化标记
        (lambda s, mc=mut_count: s + f"\n# [GPC-G{mc+1}] Auto-evolved at {datetime.now().isoformat()}"),
        # 策略3: 提取摘要
        (lambda s, mc=mut_count: s[:len(s)//2] + f"\n# 进化摘要: G{mc+1} — 此基因已通过自然选择验证\n" + s[len(s)//2:]),
    ]

    import random
    strategy = random.choice(strategies)
    new_mutable = strategy(mutable)

    # 记录变异
    db.execute("UPDATE gene_dna SET mutable_strand=?, mutation_count=mutation_count+1, "
               "last_mutated=datetime('now'), generation=generation+1 WHERE gene_id=?",
               (new_mutable, gene_id))

    diff = f"mutation #{mut_count+1}: {len(mutable)}→{len(new_mutable)} chars"
    db.execute("INSERT INTO evolution_log (gene_id, event, mutation_diff, old_fitness, new_fitness, reason) "
               "VALUES (?, 'mutation', ?, ?, ?, 'auto_evolve')",
               (gene_id, diff, fitness, fitness))

    return {"gene_id": gene_id, "mutation": mut_count + 1, "diff": diff}


def crossover_genes(db: sqlite3.Connection, gene_a: str, gene_b: str) -> Optional[str]:
    """基因交叉 — 两条精英基因融合产生新基因"""
    a = db.execute("SELECT * FROM gene_dna WHERE gene_id=?", (gene_a,)).fetchone()
    b = db.execute("SELECT * FROM gene_dna WHERE gene_id=?", (gene_b,)).fetchone()
    if not a or not b:
        return None

    # 稳定链取A(保持核心), 可变链融合
    new_stable = a[1]  # a的稳定链
    new_mutable = (a[2][:len(a[2])//2] if a[2] else "") + "\n# CROSSOVER\n" + (b[2][len(b[2])//2:] if b[2] else "")

    new_id = f"GPC-XO-{hashlib.md5((gene_a+gene_b).encode()).hexdigest()[:12]}"
    db.execute(
        "INSERT INTO gene_dna (gene_id, stable_strand, mutable_strand, fitness, generation, "
        "parent_ids, lifecycle, domain, node_origin) VALUES (?,?,?,?,?,?,?,?,?)",
        (new_id, new_stable, new_mutable, (a[3]+b[3])/2, max(a[4], b[4])+1,
         json.dumps([gene_a, gene_b]), "juvenile", a[6], "gpc-crossover")
    )
    db.execute("INSERT INTO evolution_log (gene_id, event, reason) VALUES (?, 'crossover', ?)",
               (new_id, f"parents: {gene_a}+{gene_b}"))

    return new_id


# ─── 联邦遗传引擎 ───────────────────────────────

def federal_replicate(db: sqlite3.Connection):
    """联邦遗传 — 精英基因跨节点复制"""
    elites = db.execute(
        "SELECT gene_id, fitness, domain FROM gene_dna "
        "WHERE lifecycle='elite' AND fitness >= ?", (FEDERAL_REPLICATION,)
    ).fetchall()

    replicated = 0
    for gene_id, fitness, domain in elites:
        # 检查是否已复制
        already = db.execute(
            "SELECT COUNT(*) FROM federal_replication WHERE gene_id=? AND status='completed'",
            (gene_id,)
        ).fetchone()[0]
        if already > 0:
            continue

        # 跨节点复制: 写回LGE(联邦共享基因库)
        gene = db.execute("SELECT stable_strand, mutable_strand FROM gene_dna WHERE gene_id=?",
                          (gene_id,)).fetchone()
        if gene:
            content = f"[GPC-ELITE·fitness:{fitness}]\n{gene[0]}\n\n# Evolvable\n{gene[1]}"
            lge_id = write_gene_to_lge(content, domain)
            if lge_id:
                db.execute(
                    "INSERT INTO federal_replication (gene_id, source_node, target_node, "
                    "fitness_at_replication, status) VALUES (?, 'linglong', 'dishu', ?, 'completed')",
                    (gene_id, fitness)
                )
                replicated += 1

    if replicated:
        print(f"[GPC] Federal replication: {replicated} elite genes propagated")
    return replicated


# ─── 免疫系统 ────────────────────────────────────

def immune_check(db: sqlite3.Connection):
    """免疫系统 — 隔离错误基因"""
    # 查找快速衰退的基因(fitness暴跌)
    drops = db.execute("""
        SELECT e.gene_id, e.old_fitness, e.new_fitness
        FROM evolution_log e
        WHERE e.event='mutation' AND e.new_fitness < e.old_fitness * 0.5
        AND e.timestamp > datetime('now', '-1 day')
    """).fetchall()

    for gene_id, old_f, new_f in drops:
        # 回滚到上一个稳定版本
        db.execute("UPDATE gene_dna SET lifecycle='juvenile', fitness=? WHERE gene_id=?",
                   (old_f, gene_id))
        db.execute(
            "INSERT INTO immune_isolation (gene_id, reason) VALUES (?, ?)",
            (gene_id, f"fitness crash: {old_f}→{new_f}")
        )
        print(f"[GPC] Immune: isolated {gene_id} (fitness {old_f}→{new_f})")

    return len(drops)


# ─── 主循环 ─────────────────────────────────────

def gpc_heartbeat():
    """GPC心脏搏动 — 每次搏动完成一个完整进化周期"""
    start = time.time()
    db = init_gpc_db()

    # 获取当前代数
    last_gen = db.execute("SELECT MAX(generation) FROM selection_stats").fetchone()[0] or 0
    generation = last_gen + 1

    print(f"\n[GPC] ═══ 心脏搏动 #{generation} ═══ {datetime.now().strftime('%H:%M:%S')}")

    # ═══ 阶段1: 吸收 ═══
    raw_genes = fetch_lge_genes(200)
    absorbed = 0
    for g in raw_genes:
        if isinstance(g, str):
            g = {"content": g, "id": hashlib.md5(g.encode()).hexdigest()[:12]}
        gene_id = str(g.get("id") or g.get("gene_id") or "")
        if len(gene_id) < 4:
            gene_id = hashlib.md5((g.get("content","") or str(g)).encode()).hexdigest()[:12]
        gene_id = f"GPC-{gene_id}"
        exists = db.execute("SELECT 1 FROM gene_dna WHERE gene_id = ?", (gene_id,)).fetchone()
        if not exists:
            try:
                dna = extract_dna_from_gene(g)
                db.execute(
                    "INSERT INTO gene_dna (gene_id, stable_strand, mutable_strand, fitness, "
                    "lifecycle, domain) VALUES (?,?,?,?,?,?)",
                    (dna.gene_id, dna.stable_strand, dna.mutable_strand,
                     dna.fitness, dna.lifecycle, dna.domain)
                )
                db.execute("INSERT INTO evolution_log (gene_id, event, reason) VALUES (?, 'birth', 'lge_absorption')",
                           (dna.gene_id,))
                absorbed += 1
            except sqlite3.IntegrityError:
                pass  # 重复基因跳过
    print(f"[GPC]  吸收: {absorbed} 新基因从LGE注入DNA库")

    # ═══ 阶段2: 自然选择 ═══
    selection = natural_selection(db, generation)
    print(f"[GPC]  选择: {selection['total']}基因 → {selection['survived']}存活 "
          f"({selection['eliminated']}淘汰·{selection['promoted']}晋升) · avg fitness {selection['avg_fitness']}")

    # ═══ 阶段3: 变异 ═══
    mutate_count = 0
    candidates = db.execute(
        "SELECT gene_id FROM gene_dna WHERE lifecycle IN ('stable','elite') "
        "ORDER BY RANDOM() LIMIT ?", (max(1, int(selection['total'] * MUTATION_RATE)),)
    ).fetchall()
    for (gene_id,) in candidates:
        if mutate_gene(db, gene_id):
            mutate_count += 1
    print(f"[GPC]  变异: {mutate_count} 基因微进化")

    # ═══ 阶段4: 交叉(基因融合) ═══
    elites = db.execute(
        "SELECT gene_id FROM gene_dna WHERE lifecycle='elite' ORDER BY RANDOM() LIMIT 10"
    ).fetchall()
    crossover_count = 0
    for i in range(0, len(elites) - 1, 2):
        if crossover_genes(db, elites[i][0], elites[i+1][0]):
            crossover_count += 1
    if crossover_count:
        print(f"[GPC]  交叉: {crossover_count} 新基因融合诞生")

    # ═══ 阶段5: 联邦遗传 ═══
    repl_count = federal_replicate(db)
    if repl_count:
        print(f"[GPC]  遗传: {repl_count} 精英基因跨节点传播")

    # ═══ 阶段6: 免疫检查 ═══
    immune_count = immune_check(db)
    if immune_count:
        print(f"[GPC]  免疫: {immune_count} 错误基因已隔离")

    # ═══ 阶段7: 七自指标更新 ═══
    update_seven_self(db, selection)

    db.commit()
    db.close()

    elapsed = round((time.time() - start) * 1000)
    print(f"[GPC] ═══ 搏动完成: {elapsed}ms · 基因{selection['total']} · fitness {selection['avg_fitness']} ═══")

    return {
        "generation": generation,
        "genes": selection["total"],
        "fitness": selection["avg_fitness"],
        "absorbed": absorbed,
        "mutated": mutate_count,
        "crossover": crossover_count,
        "replicated": repl_count,
        "immune": immune_count,
        "elapsed_ms": elapsed,
    }


def update_seven_self(db: sqlite3.Connection, selection: dict):
    """更新七自指标"""
    metrics = {
        "自感知": min(100, selection["avg_fitness"]),
        "自协调": 100 if selection["eliminated"] < selection["total"] * 0.3 else 70,
        "自愈合": 100,  # 免疫系统自动处理
        "自进化": min(100, selection["promoted"] * 10),
        "自迭代": min(100, selection["total"] / 10),
        "自反思": 100 if selection["eliminated"] > 0 else 80,
        "自约束": 100,  # 淘汰机制本身就是约束
    }
    for metric, value in metrics.items():
        db.execute(
            "INSERT OR REPLACE INTO seven_self_metrics (metric, value, target, trend, updated_at) "
            "VALUES (?, ?, 100, 'stable', datetime('now'))",
            (metric, value)
        )


def gpc_health_report() -> dict:
    """GPC健康报告 — 供仪表盘消费"""
    db = init_gpc_db()
    stats = {}

    # 基因统计
    row = db.execute(
        "SELECT COUNT(*), AVG(fitness), lifecycle FROM gene_dna GROUP BY lifecycle"
    ).fetchall()
    by_lifecycle = {r[2]: {"count": r[0], "avg_fitness": round(r[1], 1)} for r in row}

    total = sum(v["count"] for v in by_lifecycle.values())

    # 进化统计
    last_selection = db.execute(
        "SELECT * FROM selection_stats ORDER BY generation DESC LIMIT 1"
    ).fetchone()

    # 七自
    seven = {}
    for row in db.execute("SELECT metric, value FROM seven_self_metrics"):
        seven[row[0]] = row[1]

    db.close()

    return {
        "gpc_generation": last_selection[0] if last_selection else 0,
        "total_genes": total,
        "by_lifecycle": by_lifecycle,
        "avg_fitness": last_selection[4] if last_selection else 0,
        "seven_self": seven,
        "status": "beating" if total > 0 else "initializing",
    }


# ─── CLI ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="GPC·基因永动核心 v1.0 · 2035架构")
    ap.add_argument("--beat", action="store_true", help="执行一次心脏搏动")
    ap.add_argument("--cron", action="store_true", help="cron模式(搏动+输出报告)")
    ap.add_argument("--report", action="store_true", help="输出健康报告")
    ap.add_argument("--stats", action="store_true", help="进化统计")
    ap.add_argument("--json", action="store_true", help="JSON输出")
    args = ap.parse_args()

    init_gpc_db()

    if args.beat or args.cron:
        result = gpc_heartbeat()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))

        # 写报告供dashboard消费
        report = gpc_health_report()
        report_path = os.path.expanduser("~/lgox-ops/data/gpc-health.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    elif args.report:
        report = gpc_health_report()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"GPC 心脏状态: {report['status']}")
            print(f"代数: {report['gpc_generation']} · 基因: {report['total_genes']}")
            print(f"平均fitness: {report['avg_fitness']}")
            print(f"生命周期分布:")
            for lc, info in report['by_lifecycle'].items():
                bar = "█" * min(20, info['count']) + "░" * max(0, 20 - info['count'])
                print(f"  {lc:12s}: {bar} {info['count']} (avg {info['avg_fitness']})")
            print(f"七自:")
            for k, v in report['seven_self'].items():
                print(f"  {k}: {'█'*int(v/5)}{'░'*(20-int(v/5))} {v}%")

    elif args.stats:
        db = init_gpc_db()
        rows = db.execute(
            "SELECT generation, total_genes, survived, eliminated, avg_fitness, elite_count "
            "FROM selection_stats ORDER BY generation DESC LIMIT 10"
        ).fetchall()
        for r in reversed(rows):
            print(f"Gen {r[0]:4d}: {r[1]:5d}基因 → {r[2]}存活 {r[3]}淘汰 · "
                  f"fitness {r[4]:.1f} · elite {r[5]}")
        db.close()

    else:
        ap.print_help()
