#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  KPS · 知识光合作用引擎 v1.0 — 2035架构                   ║
║  Knowledge Photosynthesis — 外部世界→基因·全自动吸收       ║
╠══════════════════════════════════════════════════════════════╣
║  设计原则:                                                  ║
║  1. 像植物光合作用 — 自动吸收外部光(知识)转化为能量(基因)   ║
║  2. 多光谱吸收 — arXiv论文·GitHub趋势·HuggingFace·RSS·API  ║
║  3. 叶绿体转化 — 原始信息→结构化基因·零人类                 ║
║  4. 氧气释放 — 优秀基因自动广播联邦                           ║
║  5. 根系网络 — 联邦节点间知识共享根系                         ║
╚══════════════════════════════════════════════════════════════╝
"""
import json, sqlite3, time, hashlib, urllib.request, os, sys, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

KPS_DB = os.path.expanduser("~/lgox-ops/data/kps-photosynthesis.db")
LGE_ENDPOINT = "http://100.116.0.29:8200"       # 地枢·主LGE
LGE_FALLBACK = "http://127.0.0.1:8210"           # 灵龙·本地灾备镜像
LGE_TIMEOUT = 2                                   # 2s超时

# ─── 光谱源(免费·零成本) ────────────────────────

LIGHT_SOURCES = {
    "arxiv_cs_ai": {
        "name": "arXiv CS.AI",
        "url": "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=10",
        "type": "xml",
        "extractor": "_extract_arxiv",
        "category": "ai_research",
    },
    "arxiv_cs_se": {
        "name": "arXiv CS.SE",
        "url": "https://export.arxiv.org/api/query?search_query=cat:cs.SE&sortBy=submittedDate&sortOrder=descending&max_results=10",
        "type": "xml",
        "extractor": "_extract_arxiv",
        "category": "software_engineering",
    },
    "github_trending_python": {
        "name": "GitHub Trending Python",
        "url": "https://api.github.com/search/repositories?q=language:python+stars:>100+pushed:>2026-06-01&sort=stars&order=desc&per_page=10",
        "type": "json",
        "extractor": "_extract_github",
        "category": "open_source",
    },
    # ⛔ HuggingFace 持续不可达(No route to host) — 暂时关闭节省15s超时
    # "huggingface_models": { ... },
}

# ─── 内置知识模式(当外部源不可达时) ──────────────

BUILTIN_KNOWLEDGE = {
    "design_patterns": {
        "category": "software_engineering",
        "genes": [
            "# PATTERN: Repository Pattern\nclass Repository:\n    def __init__(self, session): self.session = session\n    async def get(self, id): return await self.session.get(Model, id)\n    async def add(self, entity): self.session.add(entity); await self.session.flush()",
            "# PATTERN: Adapter Pattern\nclass ExternalAPIAdapter:\n    def __init__(self, api_client): self.client = api_client\n    async def fetch(self, request): \n        raw = await self.client.call(request.to_external())\n        return Response.from_external(raw)",
            "# PATTERN: Strategy Pattern\nclass PricingStrategy(ABC):\n    @abstractmethod def calculate(self, order) -> Decimal: ...\nclass FlatPricing(PricingStrategy): ...\nclass TieredPricing(PricingStrategy): ...",
        ]
    },
    "ai_engineering": {
        "category": "ai_research",
        "genes": [
            "# PATTERN: RAG Pipeline\nclass RAGPipeline:\n    def __init__(self, embedder, vector_store, llm): ...\n    async def query(self, q): \n        docs = await self.retrieve(q, k=5)\n        return await self.generate(q, docs)",
            "# PATTERN: Agent Orchestration\nclass AgentOrchestrator:\n    def __init__(self, agents: list[BaseAgent]): self.agents = agents\n    async def execute(self, task): \n        plan = await self.plan(task)\n        results = await asyncio.gather(*[a.run(t) for a, t in zip(self.agents, plan)])",
            "# PATTERN: Evaluation Harness\nclass EvalHarness:\n    def __init__(self, model, benchmarks): ...\n    async def run(self): \n        scores = {}\n        for bench in self.benchmarks:\n            scores[bench.name] = await bench.evaluate(self.model)",
        ]
    },
    "operations": {
        "category": "devops",
        "genes": [
            "# PATTERN: Zero-Downtime Deploy\n1. health_check() → all green\n2. drain_traffic(old_instance)\n3. deploy(new_instance) with canary 5%\n4. verify(new_instance, 60s)\n5. switch 100% → new_instance\n6. decommission(old_instance)",
            "# PATTERN: Circuit Breaker\nstate: CLOSED→OPEN(after N failures)→HALF_OPEN(after timeout)→CLOSED(on success)\nmonitor: error_rate, latency_p99, timeout_count",
            "# PATTERN: Observability Stack\nmetrics → Prometheus\ntraces → Jaeger/Tempo\nlogs → Loki\n dashboards → Grafana\nalerts → AlertManager → PagerDuty",
        ]
    },
    "security": {
        "category": "security",
        "genes": [
            "# PATTERN: Zero Trust Architecture\n1. Never trust, always verify\n2. Least privilege access\n3. Micro-segmentation\n4. Continuous authentication\n5. Assume breach",
            "# PATTERN: Secret Management\n1. Never hardcode secrets\n2. Use vault/aws-secrets-manager\n3. Rotate every 90 days\n4. Audit all access\n5. Least privilege IAM",
            "# PATTERN: Supply Chain Security\n1. Pin dependencies with hashes\n2. SBOM (Software Bill of Materials)\n3. Scan for CVEs (dependabot/snyk)\n4. Sign artifacts (cosign)\n5. Reproducible builds",
        ]
    },
}


def init_kps_db():
    db = sqlite3.connect(KPS_DB)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS photosynthesis_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            category TEXT,
            energy_absorbed INTEGER,      -- 吸收的原始项数
            genes_produced INTEGER,        -- 转化成的基因数
            chlorophyll_efficiency REAL,   -- 转化效率
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS absorbed_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            title TEXT,
            url TEXT UNIQUE,
            summary TEXT,
            key_patterns TEXT,             -- JSON: 提取的关键模式
            gene_ids TEXT,                 -- JSON: 写入LGE的基因ID列表
            absorbed_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS chlorophyll_stats (
            source TEXT PRIMARY KEY,
            total_absorbed INTEGER DEFAULT 0,
            total_genes INTEGER DEFAULT 0,
            last_absorbed_at TEXT,
            avg_efficiency REAL DEFAULT 0.0
        );
        CREATE INDEX IF NOT EXISTS idx_photosynthesis_time ON photosynthesis_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_absorbed_source ON absorbed_knowledge(source);
    """)
    db.commit()
    return db


def _extract_arxiv(raw_text: str) -> list:
    """从arXiv XML提取论文摘要"""
    entries = []
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(raw_text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns)
            summary = entry.find('atom:summary', ns)
            link = entry.find('atom:id', ns)
            if title is not None:
                entries.append({
                    "title": (title.text or "").strip().replace("\n", " ")[:200],
                    "summary": (summary.text or "").strip().replace("\n", " ")[:500] if summary is not None else "",
                    "url": (link.text or "").strip() if link is not None else "",
                })
    except Exception:
        return _fallback_entries("arxiv")
    return entries


def _extract_github(raw_json: dict) -> list:
    """从GitHub API提取仓库信息"""
    entries = []
    for repo in raw_json.get("items", [])[:10]:
        entries.append({
            "title": repo.get("full_name", ""),
            "summary": (repo.get("description", "") or "")[:500],
            "url": repo.get("html_url", ""),
            "stars": repo.get("stargazers_count", 0),
            "language": repo.get("language", ""),
        })
    return entries


def _extract_hf(raw_json: list) -> list:
    """从HuggingFace提取模型信息"""
    entries = []
    for model in raw_json[:10]:
        entries.append({
            "title": model.get("modelId", model.get("id", "")),
            "summary": f"Downloads: {model.get('downloads', 0)}, Likes: {model.get('likes', 0)}",
            "url": f"https://huggingface.co/{model.get('modelId', '')}",
            "tags": model.get("tags", [])[:5],
        })
    return entries


def _fallback_entries(source: str) -> list:
    """外部源不可达时的内置知识"""
    return [{"title": f"Built-in knowledge ({source})", "summary": "", "url": ""}]


def absorb_light():
    """光合作用主循环 — 吸收外部光→转化为基因"""
    db = init_kps_db()
    total_absorbed = 0
    total_genes = 0

    for source_id, config in LIGHT_SOURCES.items():
        try:
            # 获取外部数据
            req = urllib.request.Request(config["url"], headers={"User-Agent": "GPC-KPS/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()

            # 提取
            if config["type"] == "xml":
                entries = _extract_arxiv(raw.decode())
            elif config["type"] == "json":
                entries = _extract_github(json.loads(raw)) if "github" in source_id else _extract_hf(json.loads(raw))
            else:
                entries = []

            if not entries:
                entries = _fallback_entries(source_id)

            total_absorbed += len(entries)

            # 转化为基因
            for entry in entries[:5]:  # 取前5条
                gene_id = _convert_to_gene(entry, config["category"], source_id)
                if gene_id:
                    total_genes += 1
                    # 记录
                    db.execute(
                        "INSERT OR IGNORE INTO absorbed_knowledge (source, title, url, summary, gene_ids) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (source_id, entry.get("title", "")[:200], entry.get("url", "")[:500],
                         entry.get("summary", "")[:1000], json.dumps([gene_id])),
                    )

            # 更新统计
            db.execute(
                "INSERT OR REPLACE INTO chlorophyll_stats (source, total_absorbed, total_genes, "
                "last_absorbed_at, avg_efficiency) VALUES (?, "
                "COALESCE((SELECT total_absorbed FROM chlorophyll_stats WHERE source=?),0)+?, "
                "COALESCE((SELECT total_genes FROM chlorophyll_stats WHERE source=?),0)+?, "
                "datetime('now'), ?)",
                (source_id, source_id, len(entries), source_id, len(entries),
                 round(total_genes / max(1, total_absorbed), 2))
            )

        except Exception as e:
            print(f"[KPS] {source_id}: {e}", file=sys.stderr)
            # 使用内置知识
            for category, data in BUILTIN_KNOWLEDGE.items():
                if data["category"] == config["category"]:
                    for gene_text in data["genes"][:3]:
                        gene_id = _write_gene(gene_text, config["category"], source_id)
                        if gene_id:
                            total_genes += 1
                            total_absorbed += 1

    # 记录光合作用周期
    efficiency = round(total_genes / max(1, total_absorbed), 2)
    db.execute(
        "INSERT INTO photosynthesis_log (source, category, energy_absorbed, genes_produced, chlorophyll_efficiency) "
        "VALUES ('multi-spectrum', 'all', ?, ?, ?)",
        (total_absorbed, total_genes, efficiency)
    )
    db.commit()
    db.close()

    print(f"[KPS] 光合作用: {total_absorbed}光粒子 → {total_genes}基因 · 效率{efficiency}")
    return {"absorbed": total_absorbed, "genes": total_genes, "efficiency": efficiency}


def _convert_to_gene(entry: dict, category: str, source: str) -> str:
    """将原始条目转化为基因"""
    title = entry.get("title", "")
    summary = entry.get("summary", "")

    # 提取关键模式
    patterns = []
    for keyword, pattern_name in [
        ("async", "async_pattern"), ("error", "error_handling"),
        ("cache", "cache_pattern"), ("security", "security"),
        ("api", "api_design"), ("database", "database"),
        ("ml", "machine_learning"), ("rag", "rag"),
        ("agent", "agent"), ("pipeline", "pipeline"),
    ]:
        if keyword in (title + summary).lower():
            patterns.append(pattern_name)

    gene_content = (
        f"[KPS-{source}] {title}\n"
        f"Category: {category}\n"
        f"Patterns: {', '.join(patterns) if patterns else 'general'}\n"
        f"Summary: {summary[:300]}\n"
        f"Source: {entry.get('url', source)}\n"
        f"Absorbed: {datetime.now(timezone.utc).isoformat()}"
    )

    return _write_gene(gene_content, category, source)


def _write_gene(content: str, category: str, source: str) -> str:
    """写基因到LGE — 主LGE→本地灾备自动降级"""
    endpoints = [LGE_ENDPOINT, LGE_FALLBACK]
    for ep in endpoints:
        try:
            req = urllib.request.Request(
                f"{ep}/genes/write",
                data=json.dumps({
                    "content": content,
                    "memory_type": "semantic",
                    "source": f"kps-{source}",
                }).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=LGE_TIMEOUT) as resp:
                gene_id = json.loads(resp.read()).get("id", "")
                if gene_id:
                    return gene_id
        except Exception:
            continue
    return ""


def run_builtin_photosynthesis():
    """使用内置知识进行光合作用(离线模式)"""
    db = init_kps_db()
    total = 0

    for category, data in BUILTIN_KNOWLEDGE.items():
        for gene_text in data["genes"]:
            gene_id = _write_gene(gene_text, data["category"], f"builtin-{category}")
            if gene_id:
                db.execute(
                    "INSERT OR IGNORE INTO absorbed_knowledge (source, title, url, summary, gene_ids) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (f"builtin-{category}", gene_text[:100], "",
                     gene_text[:500], json.dumps([gene_id]))
                )
                total += 1

    db.execute(
        "INSERT INTO photosynthesis_log (source, category, energy_absorbed, genes_produced, chlorophyll_efficiency) "
        "VALUES ('builtin', 'all', ?, ?, 1.0)",
        (total, total)
    )
    db.commit()
    db.close()
    print(f"[KPS] 内置光合作用: {total} genes produced")
    return total


def kps_report() -> dict:
    """光合作用报告"""
    db = init_kps_db()
    stats = {}
    for row in db.execute("SELECT source, total_absorbed, total_genes, avg_efficiency FROM chlorophyll_stats"):
        stats[row[0]] = {"absorbed": row[1], "genes": row[2], "efficiency": row[3]}

    last = db.execute(
        "SELECT energy_absorbed, genes_produced, chlorophyll_efficiency, timestamp "
        "FROM photosynthesis_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    db.close()
    return {
        "sources": len(stats),
        "stats": stats,
        "last_cycle": {
            "absorbed": last[0] if last else 0,
            "genes": last[1] if last else 0,
            "efficiency": last[2] if last else 0,
            "timestamp": last[3] if last else "",
        } if last else None,
        "status": "photosynthesizing" if stats else "initializing",
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="KPS·知识光合作用引擎 v1.0 · 2035架构")
    ap.add_argument("--absorb", action="store_true", help="执行一次光合作用")
    ap.add_argument("--builtin", action="store_true", help="内置知识光合作用(离线)")
    ap.add_argument("--cron", action="store_true", help="cron模式")
    ap.add_argument("--report", action="store_true", help="输出报告")
    ap.add_argument("--json", action="store_true", help="JSON输出")
    args = ap.parse_args()

    init_kps_db()

    if args.builtin:
        run_builtin_photosynthesis()

    elif args.absorb or args.cron:
        # 先尝试外部吸收，失败时用内置
        result = absorb_light()
        if result["genes"] == 0:
            print("[KPS] External absorption empty, using builtin...")
            result["genes"] = run_builtin_photosynthesis()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.report:
        report = kps_report()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"KPS 状态: {report['status']}")
            print(f"光源: {report['sources']}")
            for src, info in report['stats'].items():
                print(f"  {src}: {info['absorbed']}吸收·{info['genes']}基因·效率{info['efficiency']}")
            if report['last_cycle']:
                print(f"上次: {report['last_cycle']['genes']}基因·{report['last_cycle']['timestamp']}")

    else:
        # cron no-agent mode: default to --absorb with json output
        result = absorb_light()
        if result["genes"] == 0:
            print("[KPS] External absorption empty, using builtin...")
            result["genes"] = run_builtin_photosynthesis()
        print(json.dumps(result, indent=2, ensure_ascii=False))
