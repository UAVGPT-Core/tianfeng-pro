#!/usr/bin/env python3
"""
联邦基因永动引擎 v2.0 — 智谱GLM-4-Flash驱动·2035视角
修复: v1依赖Ollama(无)+NGC(Key丢失) → v2全走智谱免费API
部署: 天枢 cron每10min | 目标50条/次 → ~7,200条/天
智谱: 200万token/天免费·温度0.3·max256精简
"""
import json, os, sys, time, sqlite3, hashlib, re
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

VERSION = "2.0.0-glm"
NODE = "天枢"
DATA_DIR = Path.home() / "lgox-ops" / "data" / "perpetual-gene"
DB_PATH = DATA_DIR / "genes.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 智谱GLM-4-Flash 免费API (200万token/天)
GLM_KEY = "fd867a96bad64f53a8ece13ac6911887.T3zYiYf7KbxhVTb0"
GLM_API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_MODEL = "glm-4-flash"

LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"

CONCURRENCY = 4
TARGET_COUNT = 50
GENE_MAX_LENGTH = 600

def glm_chat(messages, max_tokens=300, temperature=0.7):
    data = json.dumps({
        "model": GLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }).encode()
    req = urllib.request.Request(GLM_API, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GLM_KEY}"
    })
    r = urllib.request.urlopen(req, timeout=30)
    return json.loads(r.read())["choices"][0]["message"]["content"]

def log(msg):
    print(f"[{datetime.now().strftime('%m%d-%H%M%S')}] {msg}")

DOMAINS = {
    "ai-agent": {
        "name": "AI Agent架构", "weight": 25,
        "topics": [
            "多智能体协作协议设计模式",
            "Agent长期记忆与RAG混合检索架构",
            "MCP工具调用安全边界与权限模型",
            "自主Agent决策链的验证与回滚机制",
            "Agent自我进化触发条件与评估指标",
            "联邦学习在Agent知识共享中的应用",
            "人机协作Agent的信任建立机制",
            "Agent行为的可解释性与审计日志",
            "工具编排的错误恢复与降级策略",
            "多模型路由与成本优化的Agent实践",
        ],
    },
    "uav-drone": {
        "name": "无人机与低空", "weight": 20,
        "topics": [
            "无人机自主巡检的路径规划算法",
            "AI机巢的自动化调度与能源管理",
            "视觉SLAM在GPS拒止环境下的定位",
            "无人机集群协同编队控制策略",
            "低空经济空域管理与法规框架",
            "5G+边缘AI在无人机实时图传中应用",
            "深度学习在桥梁裂缝检测中的实践",
            "多光谱传感器数据融合技术",
            "无人机电池管理与续航优化",
            "对抗天气条件下的飞行稳定性",
        ],
    },
    "edge-computing": {
        "name": "边缘计算与推理", "weight": 15,
        "topics": [
            "边缘设备上的模型量化与剪枝技术",
            "WASM在浏览器端AI推理的应用",
            "端侧大模型的KV缓存优化策略",
            "边缘联邦学习的通信效率优化",
            "移动端GPU推理框架对比分析",
            "模型蒸馏在边缘部署中的实践",
            "ONNX运行时优化与硬件加速",
            "边缘AI的能耗管理与热控制",
            "TinyML在物联网传感器中的应用",
            "边缘-云协同推理架构设计",
        ],
    },
    "federation": {
        "name": "联邦架构", "weight": 15,
        "topics": [
            "P2P知识同步的冲突检测与合并",
            "联邦节点的自愈协议与心跳机制",
            "基因引擎的五原语设计与版本控制",
            "跨节点Docker特权系统管理方案",
            "联邦桥消息队列的持久化与去重",
            "多节点共识算法在知识联邦中的应用",
            "联邦拓扑的动态发现与重新平衡",
            "零信任架构在AI联邦中的落地",
            "联邦仪表盘的实时数据聚合方案",
            "DNA双螺旋基因同步协议设计",
        ],
    },
    "mlops": {
        "name": "MLOps与训练", "weight": 15,
        "topics": [
            "LoRA微调的内存优化与合并策略",
            "RLHF训练中的人类反馈质量评估",
            "分布式训练的通信拓扑优化",
            "模型版本管理与回滚的最佳实践",
            "A/B测试框架在模型部署中的应用",
            "ML流水线的自动化测试与持续交付",
            "GPU集群的任务调度与资源分配",
            "模型监控的漂移检测与自动重训练",
            "向量数据库的索引优化与扩展",
            "特征工程管道的自动化构建",
        ],
    },
    "security": {
        "name": "AI安全与合规", "weight": 10,
        "topics": [
            "大模型的越狱攻击防御策略",
            "训练数据投毒检测与防护",
            "模型水印与知识产权保护",
            "AI生成内容的溯源与认证",
            "联邦节点的零信任访问控制",
            "敏感数据的联邦脱敏学习",
            "AI供应链安全与依赖审计",
            "推理侧信道攻击的防御",
            "GDPR在AI训练数据中的合规",
            "模型逆向工程的风险缓解",
        ],
    },
}

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS genes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT, domain TEXT, fitness_score REAL,
        quality_grade TEXT, gene_hash TEXT UNIQUE,
        production_batch TEXT, created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS batches (
        batch_id TEXT PRIMARY KEY, gene_count INTEGER,
        avg_fitness REAL, status TEXT, created_at TEXT
    )""")
    conn.commit()
    return conn

def produce_gene(domain_key, topic, batch_id):
    prompt = f"生成一条技术知识(150-300字)，领域:{DOMAINS[domain_key]['name']}，主题:{topic}。格式: ###标题 | 核心概念50字 | 技术细节100字 | 联邦应用50字 | 相关技术3项。纯技术·可验证。"
    try:
        content = glm_chat([{"role": "user", "content": prompt}], 400, 0.7)
        if len(content) > 50:
            return {"content": content[:GENE_MAX_LENGTH], "domain": DOMAINS[domain_key]["name"], "domain_key": domain_key, "topic": topic, "batch_id": batch_id}
    except Exception as e:
        pass
    return None

def glm_quality_score(gene):
    prompt = f"Rate this tech knowledge 0.0-1.0. Reply ONLY number.\n{gene['content'][:300]}\nScore:"
    try:
        text = glm_chat([{"role": "user", "content": prompt}], 5, 0.1)
        nums = re.findall(r'[\d.]+', text)
        return min(0.95, max(0.05, float(nums[0]))) if nums else 0.45
    except:
        return 0.45

def production_line(batch_id):
    log(f"量产启动·目标{TARGET_COUNT}条·{CONCURRENCY}并发")
    tasks = []
    total_weight = sum(d["weight"] for d in DOMAINS.values())
    for dk, dc in DOMAINS.items():
        count = max(1, int(TARGET_COUNT * dc["weight"] / total_weight))
        for i in range(count):
            tasks.append((dk, dc["topics"][i % len(dc["topics"])]))
    
    genes = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(produce_gene, dk, topic, batch_id): i for i, (dk, topic) in enumerate(tasks[:TARGET_COUNT])}
        for f in as_completed(futures):
            r = f.result()
            if r: genes.append(r)
    
    log(f"量产:{len(genes)}/{len(tasks)}条·成功率{100*len(genes)//max(1,len(tasks))}%")
    return genes

def quality_filter(genes, conn):
    log(f"质量过滤·{len(genes)}条待审")
    passed = []
    for gene in genes[:50]:
        score = glm_quality_score(gene)
        gene["fitness_score"] = score
        gene["quality_grade"] = "A" if score >= 0.70 else "B" if score >= 0.50 else "C"
        gene["gene_hash"] = hashlib.md5(gene["content"][:200].encode()).hexdigest()[:16]
        if score >= 0.30:
            passed.append(gene)
            try:
                conn.execute("INSERT OR IGNORE INTO genes (content,domain,fitness_score,quality_grade,gene_hash,production_batch) VALUES (?,?,?,?,?,?)",
                    (gene["content"][:500], gene["domain"], score, gene["quality_grade"], gene["gene_hash"], gene.get("batch_id","")))
            except: pass
    conn.commit()
    if passed:
        log(f"通过:{len(passed)}条·均分{sum(g['fitness_score'] for g in passed)/len(passed):.2f}")
    return passed

def write_to_lge(genes):
    written = 0
    for gene in genes:
        try:
            data = json.dumps({"content": gene["content"], "memory_type": "semantic", "source": "永动引擎V2", "fitness": gene.get("fitness_score", 0.5)}).encode()
            req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data, headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
            urllib.request.urlopen(req, timeout=10)
            written += 1
        except: pass
    return written

def main():
    batch_id = datetime.now().strftime("B%Y%m%d-%H%M")
    log(f"═══ DNA双螺旋·永动循环 V2(GLM) ═══")
    conn = init_db()
    genes = production_line(batch_id)
    if not genes:
        log("❌ 量产失败")
        return
    passed = quality_filter(genes, conn)
    written = write_to_lge(passed)
    log(f"✅ 完成·{len(passed)}条·写入LGE:{written}条")
    avg_f = sum(g["fitness_score"] for g in passed) / max(1, len(passed))
    conn.execute("INSERT INTO batches VALUES (?,?,?,?,?)", (batch_id, len(passed), round(avg_f, 3), "completed", datetime.now().isoformat()))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
