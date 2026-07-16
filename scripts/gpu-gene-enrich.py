#!/usr/bin/env python3
"""
GPU基因富化引擎 v1.0 · 天工DGX1
七自: 自感知·自进化·自反思·自愈合·自约束
职能: 利用闲置GPU → 拉取低fitness基因 → 本地LLM重写提升 → 写回LGE
cron: 每小时·零成本·天工GPU本地推理
"""
import urllib.request, json, time, os, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

LGE = "http://100.116.0.29:8200"
LOG = os.path.expanduser("~/lgox-ops/logs/gpu-enrich.log")
BATCH_SIZE = 20         # 每批处理
ENRICH_CONCURRENT = 4   # GPU并发(天工GB10·保守)
LOW_FITNESS = 0.25      # 低于此值触发富化
TARGET_FITNESS = 0.55   # 富化目标

def log(msg):
    ts = datetime.now().strftime("%m%d-%H%M%S")
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
        return None

def lge_post(path, data, timeout=15):
    try:
        req = urllib.request.Request(f"{LGE}{path}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except:
        return None

def ollama_gen(model, prompt, max_tokens=400, timeout=60):
    """调用本地Ollama"""
    try:
        proc = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=timeout
        )
        result = proc.stdout.strip()
        if result and len(result) > 20:
            return result[:max_tokens]
    except Exception as e:
        pass
    return None

def fetch_low_fitness(n=BATCH_SIZE):
    """从LGE拉取低fitness基因候选"""
    # 用多种query尝试获取低质量基因
    queries = [
        "临时 草稿 TODO 未完成 待补充",
        "简单 基础 入门 示例 测试",
        "问题 错误 失败 修复 调试",
        "概述 简介 摘要 初步 框架"
    ]
    candidates = []
    for q in queries:
        r = lge_post("/genes/search", {"query": q, "n_results": 10})
        if r:
            for g in r.get("results", []):
                fid = g.get("fitness_score", g.get("fitness", 0.5))
                if isinstance(fid, (int, float)) and fid < LOW_FITNESS:
                    if g.get("gene_id") not in [c.get("gene_id") for c in candidates]:
                        candidates.append(g)
        if len(candidates) >= n:
            break
    return candidates[:n]

def enrich_gene(gene):
    """用GPU LLM富化单个基因"""
    gid = gene.get("gene_id", "?")
    content = gene.get("content", gene.get("preview", ""))
    fitness = gene.get("fitness_score", gene.get("fitness", 0))

    # 构建富化提示
    prompt = f"""You are a gene quality enhancer. Given a low-quality knowledge gene, rewrite it to be:
1. Specific and data-driven (include concrete numbers/facts)
2. Actionable (what can someone DO with this knowledge)
3. Structured (clear bullet points or sections)
4. Authoritative (cite context/source if available)

Original gene (fitness={fitness}):
{content[:500]}

Rewrite as a HIGH-QUALITY knowledge gene (<600 chars):
"""
    enriched = ollama_gen("qwen2.5:14b", prompt, max_tokens=600, timeout=90)
    if not enriched or len(enriched) < 60:
        return None

    # 自我评分
    score_prompt = f"Rate this knowledge gene's quality on a scale of 0.0 to 1.0. Reply with just the number:\n\n{enriched[:400]}"
    score_str = ollama_gen("qwen2.5:14b", score_prompt, max_tokens=10, timeout=30)
    try:
        score = float(score_str.strip()) if score_str else 0.6
        score = max(0.3, min(0.95, score))
    except:
        score = 0.6

    return {
        "content": f"[GPU富化·天工DGX1] {enriched}",
        "memory_type": "semantic",
        "source": "gpu-enrich-engine",
        "fitness_score": score,
        "enriched_from": gid
    }

def main():
    log("═══ GPU基因富化引擎·启动 ═══")

    # 1. 拉取候选
    candidates = fetch_low_fitness(BATCH_SIZE)
    if not candidates:
        log(f"未找到低fitness候选(<{LOW_FITNESS})·跳过")
        return

    f_vals = [c.get("fitness_score", c.get("fitness", 0)) for c in candidates]
    avg_before = sum(f_vals) / len(f_vals)
    log(f"候选: {len(candidates)}条·均分{avg_before:.3f}")

    # 2. 并发富化
    enriched_count = 0
    with ThreadPoolExecutor(max_workers=ENRICH_CONCURRENT) as ex:
        futures = {ex.submit(enrich_gene, g): g for g in candidates}
        for fut in as_completed(futures):
            try:
                result = fut.result(timeout=120)
                if result:
                    r = lge_post("/genes/write", result, timeout=15)
                    if r:
                        enriched_count += 1
                        log(f"  ✅ {result['enriched_from'][:20]} → fitness={result['fitness_score']:.2f}")
            except Exception as e:
                pass

    # 3. 汇总
    log(f"═══ 富化完成: {enriched_count}/{len(candidates)}条 ═══")

    # 4. 统计更新
    stats = lge_get("/genes/stats")
    if stats:
        log(f"LGE: {stats.get('total',0):,}总·{stats.get('active',0):,}活跃")

if __name__ == "__main__":
    main()
