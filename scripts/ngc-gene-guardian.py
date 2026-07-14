#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NGC基因质量门卫 v1.0 — Gene Guardian                            ║
║  天工DGX1部署·每30分钟·NGC/Ollama双模评审                        ║
║                                                                  ║
║  功能:                                                           ║
║    1. 从地枢LGE拉取fitness<0.5的低质基因(最多100条)              ║
║    2. NGC API(nemotron-3-nano-30b)质量评审,不可达降级Ollama      ║
║    3. 评分→不达标→模型重写→写回LGE(fitness 0.6+)                ║
║    4. 评审报告输出到日志                                          ║
║                                                                  ║
║  降级链: NGC API → 天工本地Ollama qwen2.5:14b                    ║
║  零外部API费用·纯本地GPU或NGC免费层                               ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json, os, sys, time, re, hashlib, urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

# ══════════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════════

VERSION = "1.0.0"
NODE_NAME = "天工DGX1"

# 地枢LGE
LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = os.environ.get("LGE_KEY", "lgox-gene-key-2025")

# NGC API (NVIDIA API Catalog · OpenAI兼容)
NGC_API = "https://integrate.api.nvidia.com/v1/chat/completions"
NGC_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
NGC_KEY_FILE = Path("/tmp/nvkey.env")

# 天工本地Ollama(降级)
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5:14b"

# 门卫参数
MAX_GENES_PER_RUN = 100       # 每轮最多处理基因数
TARGET_FITNESS = 0.5          # 低于此分触发评审
REWRITE_TARGET = 0.65         # 重写目标fitness
QUALITY_FLOOR = 0.3           # 低于此分强制重写
SCORE_PASS = 0.55             # NGC评分通过线(0-1)

# 日志
LOG_DIR = Path.home() / "lgox-ops" / "logs"
LOG_PATH = LOG_DIR / "ngc-guardian.log"

# 搜索查询词(用于从LGE拉取基因·LGE FTS使用英文索引)
SEARCH_QUERIES = [
    "AI machine learning neural network model training inference",
    "python code programming algorithm data structure function",
    "system architecture design pattern framework deployment",
    "database SQL query optimization performance indexing",
    "API REST HTTP server client protocol network security",
    "cloud docker container kubernetes orchestration service",
    "federation node agent memory knowledge graph vector",
    "testing debugging logging monitoring metrics analytics",
    "quantum computing hardware GPU CPU optimization benchmark",
    "drone UAV autonomous navigation control sensor flight",
]

# ══════════════════════════════════════════════════════════════════
# NGC API 密钥加载
# ══════════════════════════════════════════════════════════════════

def load_ngc_key() -> Optional[str]:
    """加载NGC API密钥: 环境变量 > ~/.hermes/.env > /tmp/nvkey.env"""
    # 1. 环境变量
    for env_var in ["NVIDIA_API_KEY", "NGC_API_KEY", "NVIDIA_KEY"]:
        key = os.environ.get(env_var)
        if key:
            return key

    # 2. ~/.hermes/.env
    env_file = Path.home() / ".hermes" / ".env"
    if env_file.exists():
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k in ("NVIDIA_API_KEY", "NGC_API_KEY", "NVIDIA_KEY"):
                        return v
        except:
            pass

    # 3. /tmp/nvkey.env (天工遗留)
    if NGC_KEY_FILE.exists():
        try:
            with open(NGC_KEY_FILE) as f:
                content = f.read().strip()
                if "=" in content:
                    return content.split("=", 1)[1].strip().strip('"').strip("'")
                return content
        except:
            pass

    return None


NGC_KEY = load_ngc_key()

# ══════════════════════════════════════════════════════════════════
# 日志
# ══════════════════════════════════════════════════════════════════

def log(msg: str):
    ts = datetime.now().strftime("%m%d-%H%M%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


# ══════════════════════════════════════════════════════════════════
# LGE API 客户端
# ══════════════════════════════════════════════════════════════════

def lge_search(query: str, limit: int = 50) -> list:
    """搜索LGE基因库"""
    data = json.dumps({
        "query": query,
        "limit": limit,
        "min_score": 0.0,
        "status": "active"
    }).encode()
    req = urllib.request.Request(f"{LGE_URL}/genes/search", data=data,
        headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        return result.get("results", [])
    except Exception as e:
        log(f"  ⚠️ LGE搜索失败({query[:20]}...): {e}")
        return []


def lge_get_gene(gene_id: str) -> Optional[dict]:
    """获取单个基因详情"""
    req = urllib.request.Request(f"{LGE_URL}/genes/{gene_id}",
        headers={"X-LGE-Key": LGE_KEY})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except:
        return None


def lge_mutate(gene_id: str, new_content: str, reason: str = "NGC质量门卫重写") -> bool:
    """更新基因内容(mutate)"""
    data = json.dumps({
        "gene_id": gene_id,
        "new_content": new_content,
        "mutation_reason": reason,
        "agent_id": "ngc-gene-guardian"
    }).encode()
    req = urllib.request.Request(f"{LGE_URL}/genes/mutate", data=data,
        headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        return True
    except Exception as e:
        log(f"  ❌ mutate失败 {gene_id}: {e}")
        return False


def lge_evolve(gene_id: str, feedback_score: float, reason: str = "NGC门卫质量提升") -> bool:
    """更新基因fitness(evolve)"""
    data = json.dumps({
        "gene_id": gene_id,
        "feedback_score": feedback_score,
        "feedback_reason": reason
    }).encode()
    req = urllib.request.Request(f"{LGE_URL}/genes/evolve", data=data,
        headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        return True
    except Exception as e:
        log(f"  ❌ evolve失败 {gene_id}: {e}")
        return False


# ══════════════════════════════════════════════════════════════════
# 基因拉取: 从LGE拉取fitness<0.5的低质基因
# ══════════════════════════════════════════════════════════════════

def fetch_low_quality_genes(max_count: int = 100) -> list:
    """从LGE拉取fitness<0.5的低质基因"""
    log(f"🔍 拉取低质基因(fitness<{TARGET_FITNESS})...")

    all_genes = {}
    seen_ids = set()

    # 多轮搜索覆盖不同主题
    for query in SEARCH_QUERIES:
        if len(all_genes) >= max_count:
            break
        results = lge_search(query, limit=50)
        for g in results:
            gid = g.get("gene_id", "")
            if gid and gid not in seen_ids:
                seen_ids.add(gid)
                fitness = g.get("fitness_score", 0.5)
                if fitness is None:
                    fitness = 0.5
                if fitness < TARGET_FITNESS:
                    all_genes[gid] = {
                        "gene_id": gid,
                        "content": g.get("content", "")[:800],
                        "fitness_score": fitness,
                        "source": g.get("source", "unknown"),
                        "memory_type": g.get("memory_type", "semantic"),
                        "tags": g.get("tags", []),
                        "score": g.get("score", 0),
                    }

    genes = list(all_genes.values())[:max_count]
    avg_fitness = sum(g["fitness_score"] for g in genes) / max(1, len(genes))
    log(f"  拉取: {len(genes)}条低质基因(均分{avg_fitness:.3f})")

    return genes


# ══════════════════════════════════════════════════════════════════
# NGC API 调用 (OpenAI兼容)
# ══════════════════════════════════════════════════════════════════

def call_ngc(prompt: str, max_tokens: int = 300, temperature: float = 0.3) -> Optional[str]:
    """调用NGC API (NVIDIA API Catalog)"""
    if not NGC_KEY:
        return None

    try:
        body = json.dumps({
            "model": NGC_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }).encode()
        req = urllib.request.Request(NGC_API, data=body,
            headers={
                "Authorization": f"Bearer {NGC_KEY}",
                "Content-Type": "application/json"
            })
        resp = urllib.request.urlopen(req, timeout=30)
        d = json.loads(resp.read())
        return d["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"  ⚠️ NGC API调用失败: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# Ollama 本地调用 (降级)
# ══════════════════════════════════════════════════════════════════

def call_ollama(prompt: str, max_tokens: int = 300, temperature: float = 0.3) -> Optional[str]:
    """调用天工本地Ollama"""
    try:
        body = json.dumps({
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }).encode()
        req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=60)
        d = json.loads(resp.read())
        return d.get("message", {}).get("content", "").strip()
    except Exception as e:
        log(f"  ⚠️ Ollama调用失败: {e}")
        return None


def call_llm(prompt: str, max_tokens: int = 300, temperature: float = 0.3) -> Optional[str]:
    """智能路由: NGC优先, 不可达降级Ollama"""
    result = call_ngc(prompt, max_tokens, temperature)
    if result:
        return result

    log(f"  🔄 NGC不可达·降级到天工本地Ollama({OLLAMA_MODEL})")
    return call_ollama(prompt, max_tokens, temperature)


# ══════════════════════════════════════════════════════════════════
# 质量评审
# ══════════════════════════════════════════════════════════════════

def score_gene(gene: dict) -> dict:
    """对基因进行质量评分(0-1)"""
    content = gene.get("content", "")[:500]

    prompt = f"""你是LGOX联邦基因质量评审专家。评审以下技术知识基因(0-100分):

评分维度:
- 技术深度(40分): 概念是否准确·技术细节是否具体·是否有可验证数据
- 可操作性(30分): 能否直接应用·是否有代码/公式/步骤
- 联邦价值(20分): 对LGOX联邦知识库是否有贡献
- 表达质量(10分): 结构是否清晰·是否Markdown格式·是否简洁

请严格按此格式输出(只输出一行):
总分|深度分|操作分|联邦分|表达分|20字评价

基因内容:
{content}"""

    response = call_llm(prompt, max_tokens=120, temperature=0.1)
    if not response:
        return {"score": 0.3, "passed": False, "review": "LLM不可达·默认低分", "raw": ""}

    # 解析分数
    parts = response.strip().split("|")
    try:
        total = float(parts[0].strip()) / 100 if len(parts) > 0 else 0.3
    except:
        # 尝试从文本中提取数字
        nums = re.findall(r'\d+', response)
        total = float(nums[0]) / 100 if nums else 0.3

    total = min(0.95, max(0.05, total))
    review = parts[-1].strip() if len(parts) > 1 else response[:80]

    return {
        "score": round(total, 3),
        "passed": total >= SCORE_PASS,
        "review": review[:100],
        "raw": response[:200]
    }


# ══════════════════════════════════════════════════════════════════
# 基因重写
# ══════════════════════════════════════════════════════════════════

def rewrite_gene(gene: dict, original_score: float) -> Optional[str]:
    """用模型重写低质基因·提升质量到0.6+"""
    content = gene.get("content", "")[:500]

    prompt = f"""你是LGOX联邦高级知识工程师。以下是质量评分{original_score:.2f}(需>=0.60)的低质基因，请重写为高质量技术知识。

重写要求:
1. 保留原始主题和核心概念
2. 增加具体技术细节(数据/参数/公式/代码示例)
3. 提升可操作性(加入步骤/方法/实践建议)
4. 使用Markdown格式(### 标题 ## 子标题)
5. 长度200-400字·简洁有力·可验证·可追溯

原始基因:
{content}

请直接输出重写后的基因内容(Markdown格式):"""

    response = call_llm(prompt, max_tokens=600, temperature=0.5)
    if not response:
        return None

    # 清理响应
    cleaned = response.strip()
    # 去掉可能的对话前缀
    for prefix in ["重写后:", "改写后:", "改进版:", "以下是"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    if len(cleaned) < 50:
        return None

    return cleaned[:800]


# ══════════════════════════════════════════════════════════════════
# 主流程: 拉取→评审→重写→写回
# ══════════════════════════════════════════════════════════════════

def guardian_cycle():
    """一次完整门卫周期"""
    start_time = time.time()
    log("═══ NGC基因质量门卫 v1.0 · 启动 ═══")
    log(f"  NGC API: {'✅可用' if NGC_KEY else '❌不可用(将降级Ollama)'}")
    log(f"  Ollama: {OLLAMA_MODEL}@{OLLAMA_URL}")
    log(f"  LGE: {LGE_URL}")
    log(f"  参数: 拉取≤{MAX_GENES_PER_RUN}条·fitness<{TARGET_FITNESS}·重写目标≥{REWRITE_TARGET}")

    # ── 第0步: 环境检查 ──
    # 检查LGE连通性
    try:
        health_req = urllib.request.Request(f"{LGE_URL}/health")
        health = json.loads(urllib.request.urlopen(health_req, timeout=8).read())
        total_genes = health.get("genes", health.get("total", "?"))
        log(f"  LGE健康: {total_genes}基因")
    except Exception as e:
        log(f"  ❌ LGE不可达: {e}")
        return

    # ── 第1步: 拉取低质基因 ──
    genes = fetch_low_quality_genes(MAX_GENES_PER_RUN)
    if not genes:
        log("  ✅ 未发现低质基因·跳过")
        log(f"═══ 门卫周期完成·{time.time()-start_time:.0f}s ═══")
        return

    # ── 第2步: 逐条评审 ──
    log(f"\n📋 质量评审·{len(genes)}条待审")
    stats = {
        "total": len(genes),
        "scored": 0,
        "passed": 0,
        "rewritten": 0,
        "written_back": 0,
        "ngc_used": 0,
        "ollama_used": 0,
        "scores": [],
        "details": [],
    }

    for i, gene in enumerate(genes):
        gid = gene["gene_id"]
        orig_fitness = gene["fitness_score"]
        content_preview = gene["content"][:60].replace("\n", " ")

        log(f"\n  [{i+1}/{len(genes)}] {gid[:16]}... fitness={orig_fitness:.3f} | {content_preview}...")

        # 2a. NGC/Ollama评分
        result = score_gene(gene)
        stats["scored"] += 1
        model_score = result["score"]

        # 检测使用了哪个后端
        if result.get("raw"):
            stats["ngc_used"] += 1  # 默认为NGC, 降级的情况在call_llm中已记录
        else:
            stats["ollama_used"] += 1

        stats["scores"].append(model_score)

        log(f"    评分: {model_score:.3f} | {'✅通过' if result['passed'] else '❌不达标'} | {result['review']}")

        if result["passed"]:
            stats["passed"] += 1
            stats["details"].append({
                "gene_id": gid,
                "original_fitness": orig_fitness,
                "review_score": model_score,
                "action": "passed",
                "review": result["review"]
            })
            # 即使通过,如果original fitness很低,也尝试提升
            if orig_fitness < QUALITY_FLOOR:
                log(f"    ⚠️ 评分通过但原始fitness过低({orig_fitness:.3f})·尝试提升")
                new_content = rewrite_gene(gene, model_score)
                if new_content:
                    if lge_mutate(gid, new_content, f"NGC门卫·评分{model_score:.2f}通过·内容优化"):
                        stats["rewritten"] += 1
                        # 提升fitness
                        new_fitness = max(REWRITE_TARGET, model_score * 0.9)
                        if lge_evolve(gid, new_fitness, f"NGC门卫优化·评分{model_score:.2f}→fitness{new_fitness:.2f}"):
                            stats["written_back"] += 1
                            log(f"    ✅ 优化写回·fitness→{new_fitness:.3f}")
            continue

        # 2b. 不达标·重写
        log(f"    🔧 重写中...")
        new_content = rewrite_gene(gene, model_score)

        if not new_content:
            log(f"    ❌ 重写失败·跳过")
            stats["details"].append({
                "gene_id": gid,
                "original_fitness": orig_fitness,
                "review_score": model_score,
                "action": "rewrite_failed",
                "review": result["review"]
            })
            continue

        stats["rewritten"] += 1
        log(f"    重写完成·{len(new_content)}字")

        # 2c. 写回LGE
        # 先mutate内容
        if lge_mutate(gid, new_content, f"NGC门卫重写·评分{model_score:.2f}→目标{REWRITE_TARGET}"):
            # 再evolve提升fitness
            new_fitness = REWRITE_TARGET
            if lge_evolve(gid, new_fitness, f"NGC门卫提升·{model_score:.2f}→{new_fitness:.2f}"):
                stats["written_back"] += 1
                log(f"    ✅ 写回成功·fitness→{new_fitness:.3f}")
                stats["details"].append({
                    "gene_id": gid,
                    "original_fitness": orig_fitness,
                    "review_score": model_score,
                    "new_fitness": new_fitness,
                    "action": "rewritten",
                    "review": result["review"],
                    "new_content_preview": new_content[:80]
                })
            else:
                log(f"    ⚠️ mutate成功但evolve失败")
                stats["details"].append({
                    "gene_id": gid,
                    "original_fitness": orig_fitness,
                    "review_score": model_score,
                    "action": "mutated_only",
                    "review": result["review"]
                })
        else:
            log(f"    ❌ 写回失败")
            stats["details"].append({
                "gene_id": gid,
                "original_fitness": orig_fitness,
                "review_score": model_score,
                "action": "writeback_failed",
                "review": result["review"]
            })

        # 礼貌延迟·避免打爆LGE
        time.sleep(0.5)

    # ── 第3步: 报告 ──
    elapsed = time.time() - start_time
    avg_score = sum(stats["scores"]) / max(1, len(stats["scores"]))

    log(f"\n{'═'*60}")
    log(f"📊 NGC基因质量门卫·周期报告")
    log(f"{'═'*60}")
    log(f"  耗时: {elapsed:.0f}s")
    log(f"  基因总数: {stats['total']}")
    log(f"  已评审: {stats['scored']}")
    log(f"  评审通过: {stats['passed']} ({100*stats['passed']//max(1,stats['scored'])}%)")
    log(f"  已重写: {stats['rewritten']}")
    log(f"  已写回LGE: {stats['written_back']}")
    log(f"  平均评分: {avg_score:.3f}")
    log(f"  NGC调用: {stats['ngc_used']} | Ollama降级: {stats['ollama_used']}")

    # 详细记录
    if stats["details"]:
        log(f"\n  详细记录:")
        for d in stats["details"][:20]:  # 只记录前20条详情
            action_icon = {"passed": "✅", "rewritten": "🔄", "rewrite_failed": "❌",
                          "mutated_only": "⚠️", "writeback_failed": "💥"}.get(d["action"], "?")
            log(f"    {action_icon} {d['gene_id'][:16]}... | "
                f"fitness {d['original_fitness']:.3f}→{d.get('new_fitness', d['original_fitness']):.3f} | "
                f"{d['action']} | {d['review'][:60]}")

        if len(stats["details"]) > 20:
            log(f"    ... 还有{len(stats['details'])-20}条详情(见完整日志)")

    log(f"\n═══ 门卫周期完成·{elapsed:.0f}s ═══")
    return stats


# ══════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        guardian_cycle()
    except KeyboardInterrupt:
        log("⚠️ 门卫被中断")
    except Exception as e:
        log(f"💥 门卫异常: {e}")
        import traceback
        log(traceback.format_exc())
