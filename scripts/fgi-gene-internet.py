#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  FGI · 联邦基因互联网 v1.0 — 2035架构                      ║
║  Federal Gene Internet — 精英基因跨节点自动复制              ║
╠══════════════════════════════════════════════════════════════╣
║  GRP协议(Gene Replication Protocol):                        ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │ HEADER: version|gene_id|fitness|generation|origin   │    ║
║  │ DNA:    stable_strand(核心·不可变)                    │    ║
║  │         mutable_strand(可变·可进化)                   │    ║
║  │ META:   lineage(父系追踪)·mutations(变异历史)          │    ║
║  │ SIG:    hash(HEADER+DNA)·origin_signature             │    ║
║  └─────────────────────────────────────────────────────┘    ║
║                                                              ║
║  复制规则:                                                    ║
║  · fitness >= 85 → 全联邦复制                                ║
║  · fitness >= 70 → 同域节点复制                               ║
║  · fitness < 30  → 隔离·不复制                                ║
║  · 目标节点已有同ID基因 → fitness对比·择优保留                 ║
║  · 目标节点免疫 → 记录拒绝·不重试                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import json, sqlite3, time, hashlib, urllib.request, os, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─── 配置 ─────────────────────────────────────────
GPC_DB = os.path.expanduser("~/lgox-ops/data/gpc-core.db")
FGI_DB = os.path.expanduser("~/lgox-ops/data/fgi-gene-internet.db")
LGE_ENDPOINT = "http://100.116.0.29:8200"
BRIDGE_LOCAL = "http://localhost:8765"

# 联邦节点矩阵（从CLAUDE.md同步）
FEDERATION_NODES = {
    "天枢": {"ip": "100.100.89.2", "bridge": "http://100.100.89.2:8765", "user": "a1", "role": "commander", "ssh": "tianshu"},
    "地枢": {"ip": "100.116.0.29", "bridge": None, "user": "uavgpt2", "role": "knowledge", "ssh": "dgx2", "lge": "http://100.116.0.29:8200"},
    "天工": {"ip": "100.118.207.31", "bridge": None, "user": "uavgpt", "role": "compute", "ssh": "dgx1"},
    "灵龙": {"ip": "100.120.20.52", "bridge": "http://localhost:8765", "user": "a112233", "role": "ceo", "ssh": "linglong"},
    "太一": {"ip": "100.103.193.98", "bridge": None, "user": "uavgpt2", "role": "wechat", "ssh": "taiyi"},
    "织网": {"ip": "100.127.112.128", "bridge": None, "user": "root", "role": "public", "ssh": "zhiwang", "port": 22222},
    "天玑": {"ip": "100.122.142.74", "bridge": None, "user": "fei", "role": "dev", "ssh": "tianji"},
    "天怿": {"ip": "100.83.8.61", "bridge": None, "user": "tianyi", "role": "learning", "ssh": "tianyi"},
}

# 复制阈值
ELITE_THRESHOLD = 85   # 精英: 全联邦复制
STABLE_THRESHOLD = 70  # 稳定: 同域复制
DECAY_THRESHOLD = 30   # 衰退: 隔离不复制


@dataclass
class GenePacket:
    """GRP基因数据包 — 跨节点传输标准格式"""
    version: str = "GRP/1.0"
    gene_id: str = ""
    stable_strand: str = ""
    mutable_strand: str = ""
    fitness: float = 0.0
    generation: int = 0
    origin_node: str = "灵龙"
    domain: str = "general"
    lifecycle: str = "elite"
    lineage: list = field(default_factory=list)  # 父系基因ID列表
    mutation_history: list = field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    timestamp: str = ""
    signature: str = ""  # hash校验

    def compute_signature(self):
        """计算数据包签名"""
        payload = f"{self.gene_id}|{self.stable_strand[:200]}|{self.fitness}|{self.generation}|{self.origin_node}"
        self.signature = hashlib.sha256(payload.encode()).hexdigest()[:32]

    def to_json(self):
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, data):
        return cls(**data)


def init_fgi_db():
    """初始化基因互联网数据库"""
    db = sqlite3.connect(FGI_DB)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        -- 全局基因注册表(追踪基因在哪些节点上)
        CREATE TABLE IF NOT EXISTS gene_registry (
            gene_id TEXT,
            node_name TEXT,
            fitness REAL,
            lifecycle TEXT,
            replicated_at TEXT DEFAULT (datetime('now')),
            last_verified TEXT,
            status TEXT DEFAULT 'active',  -- active/stale/rejected
            PRIMARY KEY (gene_id, node_name)
        );

        -- 复制日志
        CREATE TABLE IF NOT EXISTS replication_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gene_id TEXT,
            source_node TEXT,
            target_node TEXT,
            fitness REAL,
            status TEXT,  -- sent/received/integrated/rejected/failed
            error_msg TEXT,
            duration_ms INTEGER,
            timestamp TEXT DEFAULT (datetime('now'))
        );

        -- 节点免疫记录(拒绝的基因)
        CREATE TABLE IF NOT EXISTS immune_log (
            gene_id TEXT,
            node_name TEXT,
            reason TEXT,
            rejected_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (gene_id, node_name)
        );

        -- 节点能力矩阵
        CREATE TABLE IF NOT EXISTS node_capabilities (
            node_name TEXT PRIMARY KEY,
            online INTEGER DEFAULT 0,
            last_seen TEXT,
            genes_count INTEGER DEFAULT 0,
            storage_gb REAL DEFAULT 0,
            gpu_available INTEGER DEFAULT 0,
            capabilities TEXT DEFAULT '[]'  -- JSON array
        );

        CREATE INDEX IF NOT EXISTS idx_registry_gene ON gene_registry(gene_id);
        CREATE INDEX IF NOT EXISTS idx_registry_node ON gene_registry(node_name);
        CREATE INDEX IF NOT EXISTS idx_replog_time ON replication_log(timestamp);
    """)
    db.commit()
    return db


# ══════════════════════════════════════════════════
# 组件1: 基因选择器 — 从GPC选出精英基因
# ══════════════════════════════════════════════════

def select_elite_genes(min_fitness: float = ELITE_THRESHOLD, limit: int = 20) -> list:
    """从GPC基因库选出精英基因"""
    gpc = sqlite3.connect(GPC_DB)
    rows = gpc.execute(
        "SELECT gene_id, stable_strand, mutable_strand, fitness, generation, "
        "lifecycle, domain, usage_count, success_count "
        "FROM gene_dna WHERE fitness >= ? ORDER BY fitness DESC LIMIT ?",
        (min_fitness, limit)
    ).fetchall()
    gpc.close()

    packets = []
    for r in rows:
        pkt = GenePacket(
            gene_id=r[0], stable_strand=r[1], mutable_strand=r[2],
            fitness=r[3], generation=r[4], lifecycle=r[5] if r[5] else "elite",
            domain=r[6], usage_count=r[7], success_count=r[8],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        pkt.compute_signature()
        packets.append(pkt)
    return packets


def select_stable_genes(limit: int = 30) -> list:
    """选出稳定基因（用于同域复制）"""
    return select_elite_genes(min_fitness=STABLE_THRESHOLD, limit=limit)


# ══════════════════════════════════════════════════
# 组件2: 联邦广播器 — 推送基因到目标节点
# ══════════════════════════════════════════════════

def broadcast_gene(packet: GenePacket, target_node: str, target_info: dict) -> dict:
    """广播单个基因到目标节点"""
    db = init_fgi_db()
    start = time.time()

    # 检查免疫
    immune = db.execute(
        "SELECT 1 FROM immune_log WHERE gene_id=? AND node_name=?", 
        (packet.gene_id, target_node)
    ).fetchone()
    if immune:
        return {"status": "immunized", "reason": "previously_rejected"}

    # 通过联邦桥发送
    bridge_url = target_info.get("bridge")
    if bridge_url:
        try:
            req = urllib.request.Request(
                f"{bridge_url}/messages/send",
                data=json.dumps({
                    "from_node": "灵龙",
                    "to_node": target_node,
                    "msg_type": "GENE_REPLICATE",
                    "content": packet.to_json(),
                }).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.getcode() == 200:
                    _record_replication(db, packet, target_node, "sent")
                    return {"status": "sent", "method": "bridge"}
        except Exception as e:
            pass  # 桥不通→降级SSH

    # SSH降级方案
    try:
        ssh_host = target_info.get("ssh", "")
        if ssh_host:
            tmp_file = f"/tmp/grp-{packet.gene_id[:12]}.json"
            # 写临时文件→scp→远程接收
            with open(tmp_file, "w") as f:
                f.write(packet.to_json())

            scp_result = subprocess.run(
                ["scp", "-o", "ConnectTimeout=5", tmp_file, f"{ssh_host}:/tmp/"],
                capture_output=True, text=True, timeout=10
            )
            if scp_result.returncode == 0:
                _record_replication(db, packet, target_node, "sent")
                return {"status": "sent", "method": "ssh"}
            else:
                return {"status": "failed", "error": scp_result.stderr[:200]}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    return {"status": "no_route"}


def _record_replication(db, packet, target, status, error=""):
    db.execute(
        "INSERT INTO replication_log (gene_id, source_node, target_node, fitness, status, error_msg) "
        "VALUES (?,?,?,?,?,?)",
        (packet.gene_id, "灵龙", target, packet.fitness, status, error)
    )
    db.execute(
        "INSERT OR REPLACE INTO gene_registry (gene_id, node_name, fitness, lifecycle, status) "
        "VALUES (?,?,?,?,'pending')",
        (packet.gene_id, target, packet.fitness, packet.lifecycle)
    )
    db.commit()


# ══════════════════════════════════════════════════
# 组件3: 联邦接收器 — 节点侧接收·验证·融合
# ══════════════════════════════════════════════════

def receive_gene_packet(packet_json: str, local_node: str = "本地节点") -> dict:
    """接收基因数据包·验证·融合到本地基因库"""
    try:
        packet = GenePacket.from_json(json.loads(packet_json))
    except Exception as e:
        return {"status": "invalid", "error": str(e)}

    # 1. 签名验证
    orig_sig = packet.signature
    packet.compute_signature()
    if packet.signature != orig_sig and orig_sig:
        return {"status": "rejected", "reason": "signature_mismatch"}

    # 2. 检查是否已存在且更优
    gpc = sqlite3.connect(GPC_DB)
    existing = gpc.execute(
        "SELECT fitness, lifecycle FROM gene_dna WHERE gene_id=?",
        (packet.gene_id,)
    ).fetchone()

    if existing:
        if existing[0] >= packet.fitness:
            gpc.close()
            return {"status": "skipped", "reason": f"local_fitness_higher({existing[0]:.0f}>{packet.fitness:.0f})"}
        else:
            # 更新
            gpc.execute(
                "UPDATE gene_dna SET fitness=?, mutable_strand=?, generation=?, lifecycle=? WHERE gene_id=?",
                (packet.fitness, packet.mutable_strand, packet.generation, packet.lifecycle, packet.gene_id)
            )
            gpc.commit()
            gpc.close()
            return {"status": "upgraded", "old_fitness": existing[0], "new_fitness": packet.fitness}

    # 3. 融合到本地基因库
    gpc.execute(
        "INSERT OR REPLACE INTO gene_dna (gene_id, stable_strand, mutable_strand, fitness, "
        "generation, lifecycle, domain, node_origin, usage_count, success_count) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (packet.gene_id, packet.stable_strand, packet.mutable_strand, packet.fitness,
         packet.generation, packet.lifecycle, packet.domain, packet.origin_node,
         packet.usage_count, packet.success_count)
    )
    gpc.execute(
        "INSERT INTO evolution_log (gene_id, event, reason) VALUES (?,'federal_replication',?)",
        (packet.gene_id, f"from {packet.origin_node}")
    )
    gpc.commit()
    gpc.close()

    # 4. 更新注册表
    db = init_fgi_db()
    db.execute(
        "INSERT OR REPLACE INTO gene_registry (gene_id, node_name, fitness, lifecycle, status, last_verified) "
        "VALUES (?,?,?,?,'integrated',datetime('now'))",
        (packet.gene_id, local_node, packet.fitness, packet.lifecycle)
    )
    db.execute(
        "INSERT INTO replication_log (gene_id, source_node, target_node, fitness, status) "
        "VALUES (?,?,?,?,'integrated')",
        (packet.gene_id, packet.origin_node, local_node, packet.fitness)
    )
    db.commit()
    db.close()

    return {"status": "integrated", "gene_id": packet.gene_id, "fitness": packet.fitness}


# ══════════════════════════════════════════════════
# 组件4: 基因互联网注册表
# ══════════════════════════════════════════════════

def gene_internet_status() -> dict:
    """基因互联网全局状态"""
    db = init_fgi_db()
    gpc = sqlite3.connect(GPC_DB)

    total_elite = gpc.execute(
        "SELECT COUNT(*) FROM gene_dna WHERE fitness >= ?", (ELITE_THRESHOLD,)
    ).fetchone()[0]
    total_genes = gpc.execute("SELECT COUNT(*) FROM gene_dna").fetchone()[0]
    gpc.close()

    reg = db.execute(
        "SELECT node_name, COUNT(*), AVG(fitness), SUM(CASE WHEN status='integrated' THEN 1 ELSE 0 END) "
        "FROM gene_registry GROUP BY node_name"
    ).fetchall()

    recent = db.execute(
        "SELECT gene_id, target_node, fitness, status, timestamp "
        "FROM replication_log ORDER BY id DESC LIMIT 10"
    ).fetchall()

    db.close()

    return {
        "network": "LGOX联邦·基因互联网",
        "protocol": "GRP/1.0",
        "total_genes": total_genes,
        "elite_genes": total_elite,
        "replication_eligible": total_elite,
        "nodes": [
            {"name": r[0], "genes": r[1], "avg_fitness": round(r[2] or 0, 1), "integrated": r[3]}
            for r in reg
        ],
        "recent_activity": [
            {"gene": r[0][:30], "target": r[1], "fitness": r[2], "status": r[3], "at": r[4]}
            for r in recent
        ],
    }


# ══════════════════════════════════════════════════
# 主循环: 联邦基因广播周期
# ══════════════════════════════════════════════════

def federal_gene_broadcast_cycle():
    """每周期: 选精英→跨节点推送→记录"""
    print(f"\n[FGI] ═══ 基因互联网广播 ═══ {datetime.now().strftime('%H:%M:%S')}")

    # 1. 选出精英
    elites = select_elite_genes()
    if not elites:
        # 降级: 选稳定基因
        elites = select_stable_genes()
    print(f"[FGI] 精英基因: {len(elites)} 条 (fitness >= {STABLE_THRESHOLD})")

    if not elites:
        print("[FGI] 无精英基因可复制，跳过")
        return {"broadcast": 0, "total_elite": 0}

    # 2. 检查节点可达性
    online_nodes = {}
    for name, info in FEDERATION_NODES.items():
        if name == "灵龙":
            continue  # 跳过自己
        if name in ("天怿",):
            continue  # 长期离线
        try:
            r = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=3", "-o", "BatchMode=yes",
                 info.get("ssh", ""), "echo 1"],
                capture_output=True, timeout=5
            )
            if r.returncode == 0:
                online_nodes[name] = info
        except:
            pass

    print(f"[FGI] 在线节点: {len(online_nodes)} ({', '.join(online_nodes.keys())})")

    # 3. 广播
    total_sent = 0
    results = []

    for packet in elites[:10]:  # 每次最多广播10条
        for node_name, node_info in online_nodes.items():
            result = broadcast_gene(packet, node_name, node_info)
            if result["status"] == "sent":
                total_sent += 1
            results.append({
                "gene": packet.gene_id[:30],
                "target": node_name,
                "fitness": packet.fitness,
                "status": result["status"],
            })

    # 4. 总结
    print(f"[FGI] 广播完成: {total_sent} 次推送 → {len(online_nodes)} 节点")
    for r in results[:5]:
        icon = "✅" if r["status"] == "sent" else "❌" if r["status"] == "failed" else "⏭️"
        print(f"  {icon} {r['gene'][:25]:25s} → {r['target']:4s} (fitness {r['fitness']:.0f})")

    return {
        "broadcast": total_sent,
        "total_elite": len(elites),
        "nodes_online": len(online_nodes),
        "results": results,
    }


def seed_lge_with_gpc_genes():
    """将GPC精英基因写回LGE(地枢) — 联邦基因库同步"""
    gpc = sqlite3.connect(GPC_DB)
    elites = gpc.execute(
        "SELECT gene_id, stable_strand, mutable_strand, fitness, domain FROM gene_dna "
        "WHERE fitness >= ? ORDER BY fitness DESC LIMIT 20",
        (STABLE_THRESHOLD,)
    ).fetchall()
    gpc.close()

    seeded = 0
    for gene in elites:
        gene_id, stable, mutable, fitness, domain = gene
        content = (
            f"[GPC-ELITE·fitness:{fitness:.0f}·GRP/1.0]\n"
            f"Gene ID: {gene_id}\n"
            f"Domain: {domain}\n"
            f"--- STABLE STRAND ---\n{stable[:2000]}\n"
            f"--- MUTABLE STRAND ---\n{mutable[:500]}\n"
            f"--- FEDERAL LINEAGE ---\n"
            f"Origin: 灵龙 GPC Core\n"
            f"Replication: ALL FEDERATION NODES\n"
        )
        try:
            req = urllib.request.Request(
                f"{LGE_ENDPOINT}/genes/write",
                data=json.dumps({
                    "content": content,
                    "memory_type": "procedural" if domain == "code" else "semantic",
                    "source": f"gpc-federal-{gene_id}",
                }).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = json.loads(resp.read())
                if result.get("id"):
                    seeded += 1
        except Exception as e:
            print(f"[FGI] LGE write error for {gene_id}: {e}", file=sys.stderr)

    print(f"[FGI] LGE同步: {seeded}/{len(elites)} 精英基因写入地枢")
    return seeded


# ─── CLI ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="FGI·联邦基因互联网 v1.0 · 2035架构")
    ap.add_argument("--broadcast", action="store_true", help="执行基因广播周期")
    ap.add_argument("--receive", type=str, help="接收基因数据包JSON")
    ap.add_argument("--seed-lge", action="store_true", help="精英基因→LGE地枢同步")
    ap.add_argument("--status", action="store_true", help="基因互联网全局状态")
    ap.add_argument("--demo", action="store_true", help="端到端演示")
    ap.add_argument("--cron", action="store_true", help="cron模式")
    ap.add_argument("--json", action="store_true", help="JSON输出")
    args = ap.parse_args()

    init_fgi_db()

    if args.broadcast or args.cron:
        result = federal_gene_broadcast_cycle()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))

        # 同时同步到LGE
        seed_lge_with_gpc_genes()

    elif args.receive:
        result = receive_gene_packet(args.receive)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"接收: {result['status']}")
            if result['status'] == 'integrated':
                print(f"  基因: {result['gene_id']} · fitness: {result['fitness']:.0f}")

    elif args.seed_lge:
        n = seed_lge_with_gpc_genes()
        print(f"LGE同步: {n} genes")

    elif args.status:
        report = gene_internet_status()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"🌐 {report['network']} · {report['protocol']}")
            print(f"基因: {report['total_genes']} 总数 · {report['elite_genes']} 精英")
            print(f"可复制: {report['replication_eligible']} 条")
            print(f"\n节点分布:")
            for node in report['nodes']:
                print(f"  {node['name']:6s}: {node['genes']:4d} 基因 · avg fitness {node['avg_fitness']:.1f}")
            if report['recent_activity']:
                print(f"\n最近活动:")
                for act in report['recent_activity'][:5]:
                    print(f"  {act['status']:12s} {act['gene'][:25]:25s} → {act['target']} ({act['at'][:16]})")

    elif args.demo:
        print("╔══════════════════════════════════════════╗")
        print("║  联邦基因互联网 · 端到端演示             ║")
        print("╚══════════════════════════════════════════╝")

        # 1. 选精英
        elites = select_elite_genes()
        if not elites:
            elites = select_stable_genes()
        print(f"\n[1] 精英基因: {len(elites)} 条")

        if elites:
            # 显示top3
            for pkt in elites[:3]:
                content_preview = pkt.stable_strand[:80].replace("\n", " ")
                print(f"    {pkt.gene_id[:35]:35s} fitness={pkt.fitness:.0f}  {content_preview}...")

            # 2. 尝试推送
            print(f"\n[2] 广播到联邦节点...")
            result = federal_gene_broadcast_cycle()

            # 3. LGE同步
            print(f"\n[3] 同步到地枢LGE...")
            n = seed_lge_with_gpc_genes()
            print(f"    {n} 基因写入地枢基因库")

            # 4. 状态
            print(f"\n[4] 基因互联网状态:")
            status = gene_internet_status()
            print(f"    网络: {status['network']}")
            print(f"    节点分布: {len(status['nodes'])} 节点")

    else:
        # Default: cron mode with JSON output (no-arg → don't print_help silently)
        result = federal_gene_broadcast_cycle()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        seed_lge_with_gpc_genes()
