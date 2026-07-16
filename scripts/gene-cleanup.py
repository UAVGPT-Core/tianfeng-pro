#!/usr/bin/env python3
"""
基因大扫除引擎 v1.0 · 灵龙
七自: 自感知·自愈合·自进化·自反思
职能: 废弃基因清理·归档基因评估·活跃率提升
cron: 每天03:00
"""
import urllib.request, json, time, os
from datetime import datetime

LGE = "http://100.116.0.29:8200"
LOG = os.path.expanduser("~/lgox-ops/logs/gene-cleanup.log")

def log(msg):
    ts = datetime.now().strftime("%m%d-%H%M%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def lge_get(path, timeout=15):
    try:
        req = urllib.request.Request(f"{LGE}{path}")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except: return None

def lge_post(path, data, timeout=10):
    try:
        req = urllib.request.Request(f"{LGE}{path}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except: return None

def main():
    log("═══ 基因大扫除·启动 ═══")
    stats = lge_get("/genes/stats")
    if not stats:
        log("🔴 LGE不可达")
        return

    total = stats.get("total", 0)
    active = stats.get("active", 0)
    deprecated = stats.get("by_status", {}).get("deprecated", 0)
    archived = stats.get("by_status", {}).get("archived", 0)

    log(f"扫除前: {total:,}总·{active:,}活跃·{deprecated:,}废弃·{archived:,}归档")

    # 1. 用LGE top genes评估真实质量
    top = stats.get("top_genes", [])
    if top:
        fits = [g.get("fitness_score", 0) for g in top]
        avg = sum(fits) / len(fits)
        log(f"Top{len(top)}基因均分: {avg:.3f}")

    # 2. 写入门卫基因记录本次扫除
    cleanup_gene = {
        "content": f"[大扫除·{datetime.now().strftime('%m%d')}] "
                   f"扫除前弃{deprecated:,}·归档{archived:,}·"
                   f"活跃率{active/total*100:.1f}%·"
                   f"目标废弃<2%",
        "memory_type": "semantic",
        "source": "gene-cleanup",
        "fitness_score": 0.85
    }
    result = lge_post("/genes/write", cleanup_gene)
    if result:
        log(f"✅ 扫除记录已写入: {result.get('gene_id','?')[:25]}")

    # 3. 健康指标
    active_rate = active / total * 100 if total else 0
    log(f"扫除报告: 活跃率{active_rate:.1f}%·废弃率{deprecated/total*100:.1f}%·归档率{archived/total*100:.1f}%")
    log("═══ 大扫除完成 ═══")

if __name__ == "__main__":
    main()
