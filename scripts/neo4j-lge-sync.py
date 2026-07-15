#!/usr/bin/env python3
"""
neo4j-lge-sync.py — LGOX联邦 Neo4j图谱+LGE数据同步 (STANDALONE)
=================================================================
Cron invoked (no_agent mode) — standalone script, no hermes_tools dependency.

从灵龙SSH到地枢DGX2 → 13条Cypher查询 → LGE健康 → 写入graph-data.json
目标: /Users/a112233/.hermes/data/graph-data.json
服务: g-refine-status.py:8770 → /api/graph-data

特征:
- SSH别名抗缺失: 直连IP 100.116.0.29
- Neo4j容器自动重启恢复
- cypher-shell CSV格式解析(无DictReader陷阱)
- Top基因噪音过滤 (CJK宽门+窄门 → 稳定7条)
- 列名前缀剥离 (p.name→name, l.name→name等)
- 时间戳防双时区
- 保留已有 top_fitness_genes 字段

部署路径: /Users/a112233/lgox-ops/scripts/neo4j-lge-sync.py
Cron任务: 6ddff9cbcc58 (Hermes, every 60m, no_agent=true)
"""

import subprocess
import json
import csv
import io
import shutil
import time
import sys
import os
import urllib.request

SSH = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15", "dgx2"]
DATA_PATH = os.path.expanduser("~/.hermes/data/graph-data.json")

def run(cmd, timeout=30):
    """Run a command and return stdout as string."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        print(f"[ERR] {cmd[0] if cmd else '?'}: {e}", file=sys.stderr)
        return ""

def ssh(cmd_str, timeout=30):
    """Run a command on dgx2 via SSH."""
    return run(SSH + [cmd_str], timeout=timeout)

def cypher(query, timeout=30):
    """Run a Cypher query via cypher-shell on dgx2. Escapes single quotes."""
    safe = query.replace("'", "'\\''")
    return ssh(f"docker exec neo4j cypher-shell -u neo4j -p lgox2026 '{safe}'", timeout=timeout)

# ── 0. Neo4j alive check ──
status = ssh("docker ps --filter name=neo4j --format '{{.Status}}'", timeout=10).strip()
print(f"[0] Neo4j container: {status[:80]}")

if "Up" not in status:
    print("[0] Neo4j not running — restarting...")
    ssh("docker restart neo4j", timeout=15)
    time.sleep(15)
    status2 = ssh("docker ps --filter name=neo4j --format '{{.Status}}'", timeout=10).strip()
    print(f"[0] After restart: {status2[:80]}")

# ── 0.5. Warmup query (prevents first-query empty-return bug) ──
_warmup = cypher("RETURN 1 AS test", timeout=20)
print(f"[0.5] Warmup: {len(_warmup)} chars")

# ── 1. All 13 Cypher queries ──
queries = {
    "total_nodes":    "MATCH (n) RETURN count(n) AS total_nodes",
    "gene_count":     "MATCH (g:Gene) RETURN count(g) AS gene_count",
    "labels":         "CALL db.labels()",
    "total_rels":     "MATCH ()-[r]->() RETURN count(r) AS total_rels",
    "rel_types":      "CALL db.relationshipTypes()",
    "label_counts":   "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC",
    "rel_counts":     "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS cnt ORDER BY cnt DESC",
    "physical_nodes": "MATCH (p:PhysicalNode) RETURN p.name, p.ip, p.role",
    "top_concepts":   "MATCH (g:Gene)-[:BELONGS_TO]->(c:Concept) RETURN c.name AS concept, count(g) AS genes ORDER BY genes DESC LIMIT 15",
    "top_genes":      "MATCH (g:Gene)-[r]-() RETURN g.name AS gene, count(r) AS connections ORDER BY connections DESC LIMIT 100",
    "services":       "MATCH (s:Service) RETURN s.name, s.port, s.node",
    "logical_nodes":  "MATCH (l:LogicalNode) RETURN l.name, l.role",
    "federation_edges":"MATCH (a)-[f:FEDERATED_WITH]->(b) RETURN a.name AS from_node, b.name AS to_node",
}

# Critical queries (retry on empty)
CRITICAL = {"total_nodes", "gene_count", "labels"}

results = {}
for key, q in queries.items():
    results[key] = cypher(q)
    # Retry critical queries if empty (up to 2 retries)
    if key in CRITICAL:
        for attempt in range(2):
            if results[key] and len(results[key]) > 5:
                break
            print(f"[1] {key}: empty, retry {attempt+1}...")
            time.sleep(3)
            results[key] = cypher(q)
    print(f"[1] {key}: {len(results[key])} chars")

# ── 2. LGE health (🔴 不要加 -H "X-LGE-Key:..." — LGE v2.0 会返回 genes=0)
lge_raw = ssh(
    'curl -sf --max-time 10 http://127.0.0.1:8200/health',
    timeout=15
).strip()
print(f"[2] LGE health: {len(lge_raw)} chars")

# ── 3. Parse helpers ──
def parse_csv_stripped(out):
    lines = [l.strip() for l in out.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return []
    header = [h.strip().strip('"') for h in lines[0].split(",")]
    rows = []
    for line in lines[1:]:
        try:
            reader = csv.reader(io.StringIO(line))
            vals = next(reader)
        except StopIteration:
            continue
        row = {}
        for i, h in enumerate(header):
            val = vals[i].strip().strip('"') if i < len(vals) else ""
            row[h] = val
        rows.append(row)
    return rows

def parse_scalar(out, key):
    rows = parse_csv_stripped(out)
    if rows:
        try: return int(rows[0].get(key, "0"))
        except: return 0
    return 0

total_nodes = parse_scalar(results["total_nodes"], "total_nodes")
gene_count = parse_scalar(results["gene_count"], "gene_count")
total_rels = parse_scalar(results["total_rels"], "total_rels")
print(f"[3] Counts: nodes={total_nodes} genes={gene_count} rels={total_rels}")

# Labels
labels = [r.get("label", "") for r in parse_csv_stripped(results["labels"])]

# Label counts
label_counts = {}
for r in parse_csv_stripped(results["label_counts"]):
    k = r.get("label", "").strip().strip('"')
    try: label_counts[k] = int(r.get("cnt", "0"))
    except: label_counts[k] = 0

# Relation counts
rel_counts = {}
for r in parse_csv_stripped(results["rel_counts"]):
    k = r.get("rel_type", "").strip().strip('"')
    try: rel_counts[k] = int(r.get("cnt", "0"))
    except: rel_counts[k] = 0

# Strip column prefixes
def strip_prefix(rows):
    cleaned = []
    for r in rows:
        node = {}
        for k, v in r.items():
            nk = k.split(".")[-1]
            v = v.strip().strip('"').strip()
            node[nk] = None if v in ("NULL", "null", "") else v
        cleaned.append(node)
    return cleaned

phys = strip_prefix(parse_csv_stripped(results["physical_nodes"]))
svcs = strip_prefix(parse_csv_stripped(results["services"]))
log_nodes = strip_prefix(parse_csv_stripped(results["logical_nodes"]))

# Federation edges
fed_edges = []
for r in parse_csv_stripped(results["federation_edges"]):
    edge = {}
    for k, v in r.items():
        nk = k.replace("from_node", "from").replace("to_node", "to")
        edge[nk] = v.strip().strip('"').strip()
    fed_edges.append(edge)

# Top concepts
top_concepts = []
for r in parse_csv_stripped(results["top_concepts"]):
    concept = r.get("concept", "").strip().strip('"')
    try: genes = int(r.get("genes", "0"))
    except: genes = 0
    top_concepts.append({"concept": concept, "genes": genes})

# ── 4. Top genes — noise filter ──
def is_valid_gene(name):
    if not name or name in ('NULL', 'null'):
        return False
    for ch in name:
        cp = ord(ch)
        if (0x4e00 <= cp <= 0x9fff or 0x3000 <= cp <= 0x303f or 0xff00 <= cp <= 0xffef):
            return False
    if '_' not in name and '-' not in name:
        return False
    if len(name) > 60:
        return False
    if name.startswith('{') or name.startswith('```') or name.startswith('#'):
        return False
    for noise in ('好奇心', '天巡', '飞书'):
        if noise in name:
            return False
    return True

top_genes = []
for line in results["top_genes"].strip().split('\n'):
    line = line.strip()
    if not line or line.startswith('gene') or line.startswith('"gene'):
        continue
    idx = line.rfind('", ')
    if idx < 0:
        continue
    name = line[1:idx]
    count_str = line[idx+3:].strip()
    try:
        count = int(count_str)
    except ValueError:
        continue
    if is_valid_gene(name):
        top_genes.append({"gene": name, "connections": count})

top_genes = top_genes[:7]

# ── 5. LGE health parse ──
try:
    lge_health = json.loads(lge_raw)
except:
    lge_health = {"status": "unknown", "raw": lge_raw[:200]}

# ── 6. Density ──
density = round((2 * total_rels) / (total_nodes * (total_nodes - 1)), 6) if total_nodes > 1 else 0.0

# ── 7. Timestamp ──
ts = subprocess.run(["date", "+%Y-%m-%d %H:%M+08"], capture_output=True, text=True).stdout.strip()
updated_at = ts[:10] + "T" + ts[11:16] + ":00+08:00"

# ── 8. Preserve existing top_fitness_genes ──
existing_tfg = None
try:
    with open(DATA_PATH) as f:
        old = json.load(f)
    if "top_fitness_genes" in old:
        existing_tfg = old["top_fitness_genes"]
except:
    pass

# ── 9. Assemble and write ──
lge_total_genes = lge_health.get("genes", 0) if isinstance(lge_health, dict) else 0
lge_active_genes = lge_health.get("active", 0) if isinstance(lge_health, dict) else 0

output = {
    "timestamp": ts,
    "updated_at": updated_at,
    "source": "地枢 Neo4j + LGE :8200 → /api/graph-data",
    "total_nodes": total_nodes,
    "gene_count": gene_count,
    "total_relationships": total_rels,
    "density": density,
    "labels": labels,
    "label_counts": label_counts,
    "relation_types": rel_counts,
    "physical_nodes": phys,
    "services": svcs,
    "logical_nodes": log_nodes,
    "federation_edges": fed_edges,
    "top_concepts": top_concepts,
    "top_genes": top_genes,
    "lge_health": lge_health,
    "lge_total_genes": lge_total_genes,
    "lge_active_genes": lge_active_genes,
    "lge_status": f"synced from dishu:8200 ({lge_total_genes} genes, {lge_active_genes} active)",
    "dishu_status": "online",
    "neo4j_status": "ok",
}
if existing_tfg:
    output["top_fitness_genes"] = existing_tfg

os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

# Backup existing before overwrite
if os.path.exists(DATA_PATH):
    shutil.copy2(DATA_PATH, DATA_PATH + ".bak")

with open(DATA_PATH, "w") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ WRITTEN: nodes={total_nodes} genes={gene_count} rels={total_rels} density={density} lge={lge_total_genes}")
print(f"   path={DATA_PATH}")

# ── 10. SCP to 天枢 (公网数据流关键) ──
TIANSHU_PATH = "/Users/a1/.hermes/data/graph-data.json"
scp_rc = os.system(f"scp -o ConnectTimeout=10 {DATA_PATH} tianshu:{TIANSHU_PATH}")
print(f"[SCP] to tianshu: exit={scp_rc}")

# ── 11. Verify local :8770 + :8799 (graph_data_server may be killed) ──
for port in [8770, 8799]:
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/graph-data", timeout=5)
        v = json.loads(req.read())
        print(f"[API:{port}] nodes={v.get('total_nodes')}, ts={v.get('timestamp','?')[:19]}")
    except Exception as e:
        print(f"[API:{port}] error: {e}")

# ── 12. Verify public endpoint (stock.uavgpt.com) ──
try:
    req = urllib.request.urlopen(f"https://stock.uavgpt.com/api/graph-data?v={int(time.time())}", timeout=10)
    v = json.loads(req.read())
    print(f"[API-public] nodes={v.get('total_nodes')}, ts={v.get('timestamp','?')[:19]}, lge={v.get('lge_total_genes','?')}")
except Exception as e:
    print(f"[API-public] error: {e}")

# ── 13. Verify tianshu file (avoid shell escaping — use subprocess + python3 -c) ──
# 🔴 NOT curl|python3 — use python3 reading the file directly on tianshu
try:
    out = run(["ssh", "-o", "ConnectTimeout=8", "tianshu",
        "python3 -c \"import json; d=json.load(open('/Users/a1/.hermes/data/graph-data.json')); print(f'nodes={d[\\\"total_nodes\\\"]}, ts={d[\\\"timestamp\\\"][:19]}, lge={d.get(\\\"lge_total_genes\\\",0)}')\""],
        timeout=15)
    print(f"[TIANSHU-file] {out.strip()}")
except Exception as e:
    print(f"[TIANSHU-file] error: {e}")

print("\n✅ SYNC COMPLETE")
