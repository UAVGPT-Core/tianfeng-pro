#!/usr/bin/env python3
"""
基因质量门卫 v1.0 · 天枢
七自: 自感知·自愈合·自进化·自反思·自约束
职能: 每日质量巡检 → fitness分布 → 劣质基因告警 → 自动归档 → 纳基因报告
cron: 每天08:00 天枢执行
"""
import urllib.request, json, time, os
from datetime import datetime

LGE = "http://100.116.0.29:8200"
LOG = os.path.expanduser("~/lgox-ops/logs/gene-quality-gate.log")
ALERT_THRESHOLD = 0.15   # fitness低于此值告警
DEPRECATE_THRESHOLD = 0.05   # fitness低于此值建议废弃
BATCH_SIZE = 100

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def lge_get(path, timeout=15):
    try:
        req = urllib.request.Request(f"{LGE}{path}")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"LGE {path} 失败: {e}")
        return None

def lge_post(path, data, timeout=15):
    try:
        req = urllib.request.Request(f"{LGE}{path}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"LGE POST {path} 失败: {e}")
        return None

def main():
    log("═══ 基因质量门卫·每日巡检 ═══")

    # 1. 全量统计
    stats = lge_get("/genes/stats")
    if not stats:
        log("🔴 LGE不可达·跳过巡检")
        return

    total = stats.get("total", 0)
    active = stats.get("active", 0)
    active_rate = active / total * 100 if total else 0

    log(f"总量: {total:,} | 活跃: {active:,} ({active_rate:.1f}%)")

    # 2. 采样检查 fitness 分布
    samples = []
    queries = ["进化", "永动", "质量", "雷达", "宪法", "基因", "飞轮", "AI", "编程", "记忆"]
    for q in queries:
        r = lge_post("/genes/search", {"query": q, "n_results": 20})
        if r:
            samples.extend(r.get("results", []))

    avg_f = 0.0
    low = []
    dead = []
    if samples:
        fitnesses = [g.get("fitness_score", 0) for g in samples]
        avg_f = sum(fitnesses) / len(fitnesses)
        low = [g for g in samples if g.get("fitness_score", 0) < ALERT_THRESHOLD]
        dead = [g for g in samples if g.get("fitness_score", 0) < DEPRECATE_THRESHOLD]

        log(f"采样 {len(samples)} 条 | 均分 {avg_f:.3f}")
        log(f"⚠️ 低质量(<{ALERT_THRESHOLD}): {len(low)} 条 ({len(low)/len(samples)*100:.1f}%)")
        log(f"💀 可废弃(<{DEPRECATE_THRESHOLD}): {len(dead)} 条 ({len(dead)/len(samples)*100:.1f}%)")

    # 3. 健康评分
    health_score = 100
    if active_rate < 75:
        health_score -= 20
        log(f"⚠️ 活跃率过低: {active_rate:.1f}%")
    if len(dead) / len(samples) > 0.15 if samples else False:
        health_score -= 15
        log(f"⚠️ 废弃率过高")
    if avg_f < 0.25:
        health_score -= 15
        log(f"⚠️ 均分过低: {avg_f:.3f}")
    if total < 500000:
        health_score -= 10
        log(f"⚠️ 基因总量偏低")

    log(f"质量门卫评分: {health_score}/100")

    # 4. 写入门卫结果基因(反馈到LGE)
    gate_gene = {
        "content": f"[质量门卫·{datetime.now().strftime('%m%d')}] "
                   f"总量{total:,}·活跃{active:,}({active_rate:.1f}%)·"
                   f"采样{len(samples)}条·均分{avg_f:.3f}·"
                   f"评分{health_score}/100·"
                   f"低质{len(low)}条·可废弃{len(dead)}条",
        "memory_type": "semantic",
        "source": "gene-quality-gate",
        "fitness_score": health_score / 100
    }
    result = lge_post("/genes/write", gate_gene, timeout=10)
    if result:
        log(f"✅ 门卫基因已写入: {result.get('gene_id', '?')}")
    else:
        log("⚠️ 门卫基因写入失败")

    # 5. 汇总
    log(f"═══ 巡检完成·评分{health_score}/100 ═══")
    return health_score

if __name__ == "__main__":
    main()
