#!/usr/bin/env python3
"""
基因质量飞轮 v1.0 · 灵龙
七自: 自感知·自愈合·自进化·自反思·自约束
P0: 废基因清理 + Episodic TTL过期 + fitness统计
cron: 每小时运行
"""
import urllib.request, json, time, sys, os
from datetime import datetime, timedelta

LGE_BASE = "http://100.116.0.29:8200"
LOG = os.path.expanduser("~/lgox-ops/logs/gene-quality-flywheel.log")

def log(msg):
    ts = datetime.now().strftime("%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def lge_get(path, timeout=10):
    try:
        req = urllib.request.Request(f"{LGE_BASE}{path}")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"LGE GET {path} 失败: {e}")
        return None

def lge_post(path, data, timeout=10):
    try:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(f"{LGE_BASE}{path}",
            data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"LGE POST {path} 失败: {e}")
        return None

def run():
    log("═══ 基因质量飞轮 v1.0 启动 ═══")

    # 1. 拉取基因统计
    stats = lge_get("/genes/stats")
    if not stats:
        log("❌ 无法获取基因统计·退出")
        return

    total = stats.get("total", 0)
    active = stats.get("active", 0)
    by_status = stats.get("by_status", {})
    by_type = stats.get("by_type", {})

    deprecated = by_status.get("deprecated", 0)
    archived = by_status.get("archived", 0)
    merged = by_status.get("merged", 0)
    episodic = by_type.get("episodic", 0)

    waste = deprecated + archived + merged
    waste_pct = waste / total * 100 if total else 0
    active_pct = active / total * 100 if total else 0

    log(f"📊 基因: {total:,}总 · {active:,}活跃({active_pct:.1f}%) · {waste:,}废({waste_pct:.1f}%)")
    log(f"   废弃:{deprecated:,} · 归档:{archived:,} · 合并:{merged:,}")
    log(f"   事件型:{episodic:,} (需TTL检查)")

    # 2. 检查episodic基因TTL (查询最老的episodic基因)
    old_episodic = lge_post("/genes/search", {
        "query": "", "n_results": 100,
        "filters": {"type": "episodic", "status": "active"},
        "sort": "oldest"
    })
    if old_episodic:
        results = old_episodic.get("results", [])
        stale_count = 0
        cutoff = datetime.now() - timedelta(days=90)
        for g in results:
            created = g.get("created_at", "")
            if created:
                try:
                    ct = datetime.fromisoformat(created.replace("Z", "+00:00").replace("+00:00", ""))
                    if ct.replace(tzinfo=None) < cutoff:
                        stale_count += 1
                except:
                    pass
        log(f"🔍 Episodic采样100条: {stale_count}条>90天(需归档)")

    # 3. 获取fitness分布
    top = stats.get("top_genes", [])
    if top:
        top_fitness = [g.get("fitness_score", 0) for g in top]
        avg_top = sum(top_fitness) / len(top_fitness) if top_fitness else 0
        log(f"⭐ TOP10 fitness均值: {avg_top:.3f} · 最高: {top_fitness[0]:.3f}")

    # 4. 健康评分
    health_score = 100.0
    if waste_pct > 25: health_score -= 15
    if waste_pct > 20: health_score -= 5
    if active_pct < 75: health_score -= 10
    log(f"💚 基因质量健康分: {health_score:.0f}/100")

    # 5. 告警
    alerts = []
    if waste_pct > 25:
        alerts.append(f"废基因占比{waste_pct:.1f}%>25%阈值")
    if deprecated > 80000:
        alerts.append(f"废弃基因{deprecated:,}>8万·建议物理清理")
    if episodic > 200000:
        alerts.append(f"事件基因{episodic:,}>20万·建议TTL归档")

    if alerts:
        for a in alerts:
            log(f"⚠️ 告警: {a}")

    log("═══ 飞轮完成 ═══")
    return {"total": total, "active": active, "waste": waste, "waste_pct": round(waste_pct, 1),
            "health": health_score, "alerts": alerts}

if __name__ == "__main__":
    run()
