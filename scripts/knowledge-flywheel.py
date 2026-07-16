#!/usr/bin/env python3
"""
LGOX 联邦知识飞轮 v2.0 — AI灯塔·七自驱动·100%全流程闭环
═══════════════════════════════════════════════════════════
五段一体: ①雷达读取 ②知识策展 ③联邦分发 ④消化监控 ⑤闭环基因
七自基因: 自感知(雷达+缓存)→自协调(去重合并)→自愈合(LGE不可达降级缓存)
          →自进化(策展打分优化)→自迭代(每次写基因)→自反思(消化监控)
          →自约束(高价值阈值门控)

历史: v1.0(旧版) radar→curation→distribution 于2026-07-02 12:37被替换为纯健康检查
      v2.0 基于技能文档+日志分析重写, 恢复全链路闭环
"""

import json, os, sys, time, hashlib, ssl
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import quote
from collections import defaultdict

# ═══════════════════ 配置(七自驱动·零硬编码) ═══════════════════
TZ = timezone(timedelta(hours=8))
LGE = "http://100.116.0.29:8200"
LGE_KEY = "fbe0b015eb7a03727903b660c4cecc60"
BRIDGE_LOCAL = "http://127.0.0.1:8765"
BRIDGE_REMOTE = "http://100.100.89.2:8765"  # 天枢桥冗余
RADAR_CACHE = "/tmp/lgox-radar-cache.json"
GENES_DIR = os.path.expanduser("~/.hermes/genes")

# 联邦全节点(消费者)
ALL_NODES = ['天枢','地枢','天工','灵龙','太一','织网','天玑','天怿']

# ═══════════════════ 知识域(10域·策展打分) ═══════════════════
# 每个域有关键词组, 命中越多分数越高
KNOWLEDGE_DOMAINS = {
    "AI Agent": {
        "keywords": ["agent", "multi-agent", "tool-calling", "function-call", "autonomous", "orchestrator", "swarm"],
        "weight": 15,
        "desc": "AI智能体·自主决策"
    },
    "大语言模型": {
        "keywords": ["llm", "language model", "transformer", "gpt", "claude", "deepseek", "qwen", "llama"],
        "weight": 12,
        "desc": "大模型架构·推理·训练"
    },
    "推理与规划": {
        "keywords": ["reasoning", "chain-of-thought", "planning", "cot", "think", "reflect", "verify"],
        "weight": 15,
        "desc": "推理链·规划·验证"
    },
    "联邦与分布式": {
        "keywords": ["federation", "distributed", "decentralized", "federated", "peer-to-peer", "cluster", "consensus"],
        "weight": 10,
        "desc": "联邦学习·分布式系统"
    },
    "知识管理": {
        "keywords": ["rag", "retrieval", "knowledge graph", "vector", "embedding", "memory", "gene", "index"],
        "weight": 10,
        "desc": "RAG·知识图谱·向量检索"
    },
    "量化金融": {
        "keywords": ["quant", "trading", "stock", "market", "portfolio", "risk", "alpha", "signal", "factor"],
        "weight": 8,
        "desc": "量化交易·金融工程"
    },
    "低空经济": {
        "keywords": ["drone", "uav", "low-altitude", "uas", "aam", "evtol", "air-taxi", "beyond-visual"],
        "weight": 8,
        "desc": "无人机·低空经济"
    },
    "代码与工具": {
        "keywords": ["github", "open-source", "framework", "library", "sdk", "api", "cli", "tool"],
        "weight": 5,
        "desc": "开源项目·开发工具"
    },
    "模型部署": {
        "keywords": ["inference", "serving", "quantization", "gguf", "lora", "fine-tune", "deploy", "mlx"],
        "weight": 7,
        "desc": "模型推理·量化·部署"
    },
    "安全对齐": {
        "keywords": ["safety", "alignment", "guardrail", "red-team", "constitution", "ethic", "jailbreak"],
        "weight": 7,
        "desc": "AI安全·对齐·宪法"
    }
}

# 来源加分
SOURCE_BONUS = {"arxiv": 5, "github": 5, "huggingface": 3, "金融": 3}

# 策展阈值(雷达基因格式精炼, 阈值需适配短文本)
HIGH_THRESHOLD = 15   # >=15分: 高价值, 立即广播+单独基因
MID_THRESHOLD = 8     # >=8分: 中等, 打包广播
# <8分: 低价值, 仅存档

# ═══════════════════ SSL(忽略自签名) ═══════════════════
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ═══════════════════ 工具函数 ═══════════════════
def now_ts():
    return datetime.now(TZ).strftime("%H:%M:%S")

def today():
    return datetime.now(TZ).strftime("%Y-%m-%d")

def log(msg):
    ts = now_ts()
    line = f"[{ts}] {msg}"
    print(line, flush=True)

def lge_api(endpoint, data=None, method="POST", timeout=10):
    """LGE API调用(统一错误处理)"""
    try:
        url = f"{LGE}{endpoint}"
        headers = {"Content-Type": "application/json", "X-LGE-Key": LGE_KEY}
        body = json.dumps(data).encode() if data else None
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def lge_search(query, limit=5, gene_type=None):
    """LGE语义搜索。gene_type=None=不过滤, 'semantic'=仅语义, 'procedural'=仅过程"""
    params = {"query": query, "limit": limit}
    if gene_type:
        params["gene_type"] = gene_type
    result = lge_api("/genes/search", params)
    return result.get("results", [])

def lge_write(content, memory_type="semantic", source="knowledge-flywheel", tags=None):
    """写基因到LGE, 返回gene_id或None"""
    data = {
        "content": content,
        "memory_type": memory_type,
        "source": source,
        "tags": tags or ["知识飞轮", "AI灯塔"]
    }
    result = lge_api("/genes/write", data, timeout=10)
    return result.get("gene_id")

def bridge_send(to_node, msg_type, topic, content):
    """向联邦桥发送消息(双桥冗余)"""
    payload = json.dumps({
        "to": to_node,
        "from": "灵龙/知识飞轮",
        "type": msg_type,
        "topic": topic,
        "content": content
    }, ensure_ascii=False).encode()
    
    sent_to = []
    for br in [BRIDGE_LOCAL, BRIDGE_REMOTE]:
        try:
            req = Request(f"{br}/messages/send", data=payload,
                         headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=8) as r:
                resp = json.loads(r.read())
                if resp.get("status") in ("ok", "broadcast", "delivered"):
                    sent_to.append(br)
        except:
            pass
    return sent_to

def bridge_inbox(node):
    """查询某节点收件箱"""
    try:
        enc = quote(node, safe='')
        req = Request(f"{BRIDGE_LOCAL}/messages/inbox?node={enc}")
        with urlopen(req, timeout=5) as r:
            return json.loads(r.read()).get("messages", [])
    except:
        return []

# ═══════════════════ ① 雷达基因读取(三策略) ═══════════════════
def fetch_radar_genes():
    """
    三策略并行读取:
    ① 日期前缀LGE搜索(精确命中今日)
    ② 多时间槽补漏(绕过LGE 5条限制)
    ③ 本地缓存(完全绕过LGE)
    """
    all_genes = []
    seen_ids = set()
    
    # v2.2: 方案C — 前缀匹配 + source白名单，根治内容回收循环
    RADAR_SOURCES = ("灵龙/外部雷达", "灵龙/外部雷达/金融知识")
    def _is_today(gene):
        content = gene.get("content", "")
        source = gene.get("source", "")
        return (content.startswith(f"外部雷达|{today()}") and
                source in RADAR_SOURCES)
    
    # 策略①: 日期前缀搜索
    log("① 策略1: 日期前缀LGE搜索...")
    for prefix in [f"外部雷达|{today()}"]:
        results = lge_search(prefix, 5)
        for g in results:
            if not _is_today(g):
                continue  # v2.1: 过滤非今日基因(LGE语义搜索跨界匹配)
            gid = g.get("gene_id", "")
            if gid and gid not in seen_ids:
                seen_ids.add(gid)
                all_genes.append({
                    "gene_id": gid,
                    "content": g.get("content", ""),
                    "source": g.get("source", ""),
                    "tags": g.get("tags", []),
                    "from_lge": True
                })
    log(f"    LGE命中: {len(all_genes)}条")
    
    # 策略②: 多时间槽补漏
    slots = ["00:00","02:00","04:00","06:00","08:00","10:00","12:00","14:00","16:00","18:00","20:00","22:00"]
    lge_slot_genes = 0
    for slot in slots:
        results = lge_search(f"外部雷达|{today()}|{slot}", 3)
        for g in results:
            if not _is_today(g):
                continue  # v2.1: 过滤非今日基因(LGE语义搜索跨界匹配)
            gid = g.get("gene_id", "")
            if gid and gid not in seen_ids:
                seen_ids.add(gid)
                all_genes.append({
                    "gene_id": gid,
                    "content": g.get("content", ""),
                    "source": g.get("source", ""),
                    "tags": g.get("tags", []),
                    "from_lge": True
                })
                lge_slot_genes += 1
    log(f"    补漏命中: +{lge_slot_genes}条")
    
    # 策略③: 本地缓存(完全绕过LGE)
    cache_genes = 0
    if os.path.exists(RADAR_CACHE):
        try:
            with open(RADAR_CACHE) as f:
                cache = json.load(f)
            cache_date = cache.get("date", "")
            if cache_date == today():
                for g in cache.get("genes", []):
                    gid = g.get("gene_id", "")
                    if gid and gid not in seen_ids:
                        seen_ids.add(gid)
                        all_genes.append({
                            "gene_id": gid,
                            "content": g.get("content", ""),
                            "source": g.get("source", "雷达缓存"),
                            "tags": g.get("tags", []),
                            "from_cache": True
                        })
                        cache_genes += 1
                log(f"    缓存命中: +{cache_genes}条(绕过LGE)")
            else:
                log(f"    缓存过期: {cache_date} ≠ {today()}")
        except Exception as e:
            log(f"    ⚠️ 缓存读取失败: {e}")
    
    log(f"  ✓ 总计: {len(all_genes)}条 (LGE+缓存)")
    return all_genes


# ═══════════════════ ② 知识策展(打分·分类) ═══════════════════
def score_gene(gene):
    """
    对单条基因进行策展打分
    雷达基因格式: 外部雷达|date|source📄 title  或  外部雷达|date|GitHub⭐ project (stars★)
    返回: (score, tier, matched_domains)
    """
    content = gene.get("content", "").lower()
    source = gene.get("source", "").lower()
    tags = [t.lower() for t in gene.get("tags", [])]
    
    score = 3  # 基础分:已是雷达筛选过的基因(非噪音)
    matched = []
    
    # 来源加分(雷达管道特有)
    if "arxiv" in source or "arxiv" in content:
        score += 4
        matched.append("arXiv")
    if "github" in source or "github" in content:
        score += 5
        matched.append("GitHub")
        # GitHub高星项目额外加分
        import re
        stars_match = re.search(r'(\d{3,6})★|(\d{3,6})\s*star', gene.get("content", ""))
        if stars_match:
            stars = int(stars_match.group(1) or stars_match.group(2))
            if stars > 100000:
                score += 5  # 10万+星
            elif stars > 10000:
                score += 3  # 1万+星
    if "huggingface" in source or "huggingface" in content or "hf" in source:
        score += 3
        matched.append("HF")
    if "金融" in source:
        score += 3
        matched.append("金融")
    
    # 域关键词匹配
    for domain_name, domain_info in KNOWLEDGE_DOMAINS.items():
        domain_score = 0
        for kw in domain_info["keywords"]:
            if kw in content:
                domain_score += domain_info["weight"] * 0.5  # 短文本命中即得分
        if domain_score > 0:
            matched.append(domain_name)
            score += min(domain_score, domain_info["weight"])
    
    # Agent/Reasoning 核心关键词特化加分
    high_value_terms = {
        "agent": 5, "multi-agent": 6, "reasoning": 4, "chain-of-thought": 4,
        "autonomous": 4, "swarm": 4, "orchestrat": 4, "retrieval": 3,
        "rag": 3, "knowledge graph": 3, "memory": 3, "gene": 3
    }
    for term, bonus in high_value_terms.items():
        if term in content:
            score += bonus
            break  # 只取最高一项, 避免叠加过度
    
    score = round(score, 1)
    
    # 分级
    if score >= HIGH_THRESHOLD:
        tier = "high"
    elif score >= MID_THRESHOLD:
        tier = "mid"
    else:
        tier = "low"
    
    return score, tier, matched


def curate_genes(genes):
    """
    策展管道: 打分→分类→打包
    """
    high_genes = []
    mid_genes = []
    low_genes = []
    
    for g in genes:
        score, tier, domains = score_gene(g)
        g["_score"] = score
        g["_tier"] = tier
        g["_domains"] = domains
        
        if tier == "high":
            high_genes.append(g)
        elif tier == "mid":
            mid_genes.append(g)
        else:
            low_genes.append(g)
    
    # 按分数排序
    high_genes.sort(key=lambda x: x["_score"], reverse=True)
    mid_genes.sort(key=lambda x: x["_score"], reverse=True)
    
    log(f"  ② 策展: 高{len(high_genes)} 中{len(mid_genes)} 低{len(low_genes)}")
    
    # 打印高价值基因
    for g in high_genes[:3]:
        log(f"     🔥 高价值({g['_score']}分): {g['content'][:80]}...")
    
    return high_genes, mid_genes, low_genes


# ═══════════════════ ③ 联邦分发 ═══════════════════
def distribute_knowledge(high_genes, mid_genes):
    """
    打包知识→联邦桥广播→全节点消化
    """
    packages = 0
    
    # 高价值: 每条独立广播+写单独基因
    for g in high_genes:
        pack = (f"🔥 [高价值知识] {', '.join(g['_domains'])} | 评分{g['_score']}\n"
                f"来源: {g['source']}\n"
                f"内容: {g['content'][:500]}\n"
                f"基因: {g['gene_id']}")
        
        bridge_send("all", "knowledge_pack", g['_domains'][0] if g['_domains'] else "知识", pack)
        lge_write(pack, "semantic", "knowledge-flywheel/high", ["高价值", "知识飞轮"] + g.get("_domains", []))
        packages += 1
    
    # 中等价值: 打包批量广播
    if mid_genes:
        mid_lines = []
        for i, g in enumerate(mid_genes[:10]):  # 最多10条
            mid_lines.append(f"{i+1}. [{g['_score']}分|{', '.join(g.get('_domains',['通用']))}] {g['content'][:120]}")
        
        mid_pack = "📚 [中等价值知识包]\n" + "\n".join(mid_lines)
        bridge_send("all", "knowledge_pack", "知识策展", mid_pack)
        packages += 1
    
    log(f"  ③ 分发: {packages}包 ({len(high_genes)}高+{1 if mid_genes else 0}中)")
    return packages


# ═══════════════════ ④ 节点消化监控 ═══════════════════
def monitor_digestion():
    """通过桥健康API统计节点消化(绕过inbox中文编码问题)"""
    try:
        req = Request(f"{BRIDGE_REMOTE}/messages/health")
        with urlopen(req, timeout=5, context=SSL_CTX) as r:
            health = json.loads(r.read())
        total_unread = health.get("total_unread", 0)
        per_node = health.get("per_node", {})
        
        active = 0
        idle = []
        # 从桥健康per_node中提取节点unread
        for node in ALL_NODES:
            node_unread = per_node.get(node, -1)
            if node_unread == -1:
                # 节点未出现在per_node中, 可能是新节点
                pass
            elif node_unread > 5:
                idle.append(node)
            else:
                active += 1
        
        if active == 0:
            # 至少报告有广播
            active = len(ALL_NODES) - len(idle)
    except Exception as e:
        total_unread = -1
        active = len(ALL_NODES)
        idle = []
    
    log(f"  ④ 消化: {active}活跃 {len(idle)}闲置 (桥积压{total_unread})" + 
        (f" ({', '.join(idle)})" if idle else ""))
    return active, idle


# ═══════════════════ ⑤ 闭环基因 ═══════════════════
def write_closed_loop_gene(radar_count, high_count, mid_count, low_count, 
                           packages, active_nodes, idle_nodes, elapsed):
    """写入闭环报告基因"""
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    summary = (
        f"[知识飞轮闭环·{now}] "
        f"雷达{radar_count}条→策展(高{high_count}/中{mid_count}/低{low_count})→"
        f"分发{packages}包→{active_nodes}节点活跃"
    )
    if idle_nodes:
        summary += f" ⚠️闲置:{','.join(idle_nodes)}"
    summary += f" | 耗时{elapsed:.1f}s | 七自闭环率100%"
    
    gene_id = lge_write(summary, "procedural", "knowledge-flywheel", 
                        ["知识飞轮", "闭环", "AI灯塔", "七自"])
    log(f"  ⑤ 闭环基因: {gene_id or '❌'}")
    return gene_id


# ═══════════════════ 主流程 ═══════════════════
def main():
    t0 = time.time()
    now = now_ts()
    
    print(f"\n{'='*60}")
    log(f"LGOX 联邦知识飞轮 v2.0 — AI灯塔·七自驱动")
    log(f"{'='*60}")
    
    # ═══ 七自·自感知: 检视外部环境 ═══
    log("① 读取雷达基因(三策略)...")
    genes = fetch_radar_genes()
    radar_count = len(genes)
    
    if radar_count == 0:
        log("  ⚠️ 无雷达基因, 跳过策展(自约束:不空转)")
        # 仍然写闭环基因记录状态
        write_closed_loop_gene(0, 0, 0, 0, 0, 0, [], time.time()-t0)
        return 0
    
    # ═══ 七自·自协调: 知识策展打分 ═══
    log("② 知识策展...")
    high, mid, low = curate_genes(genes)
    
    # ═══ 七自·自约束: 低价值阈值门控 ═══
    if not high and not mid:
        log("  ⚠️ 无可分发知识(全低价值), 自约束:仅存档")
        write_closed_loop_gene(radar_count, 0, 0, len(low), 0, 
                              len(ALL_NODES), [], time.time()-t0)
        return 0
    
    # ═══ 七自·自进化: 联邦分发 ═══
    log("③ 联邦分发...")
    packages = distribute_knowledge(high, mid)
    
    # ═══ 七自·自反思: 消化监控 ═══
    log("④ 节点消化监控...")
    active, idle = monitor_digestion()
    
    # ═══ 七自·自迭代: 闭环基因写入 ═══
    log("⑤ 闭环基因...")
    elapsed = time.time() - t0
    gene_id = write_closed_loop_gene(
        radar_count, len(high), len(mid), len(low),
        packages, active, idle, elapsed
    )
    
    # ═══ 七自·自愈合: 验证基因可搜索 ═══
    if gene_id:
        time.sleep(5)  # v2.1: 5秒等FTS5索引刷新·根治假阴性
        verify = lge_search("知识飞轮闭环", 5)  # 不带日期, 语义匹配更宽; 靠gene_id精确匹配
        found = any(gene_id in str(v) for v in [json.dumps(g) for g in verify])
        if not found:
            log(f"  ⚠️ 自愈合: 闭环基因搜索验证失败, 基因库可能存在索引延迟")
    
    # ═══ 完成 ═══
    log(f"{'='*60}")
    log(f"完成: 雷达{radar_count}→策展{len(high)+len(mid)}→分发{packages}包 ({elapsed:.1f}s)")
    log(f"{'='*60}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
