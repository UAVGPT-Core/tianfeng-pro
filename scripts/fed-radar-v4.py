#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║  联邦外部雷达 v4.0 — NGC 121模型全火力驱动             ║
║  灵龙定义·六大扫描域·天工GPU执行·地枢LGE沉淀          ║
║  零成本·全自动·七自闭环                                ║
╚══════════════════════════════════════════════════════════╝

NGC火力分配:
  nemotron-30b → 深度分析·质量评判·战略摘要
  llama-3.1-8b → 快速扫描·分类标注
  llama-vision → arXiv图表·无人机视觉论文
  embed-e5-v5  → 去重·聚类·相似基因检测

扫描域(灵龙定义·联邦壮大最需要):
  🔬 AI Agent架构 → 多智能体·联邦学习·自主Agent·MCP协议
  🛸 无人机/低空经济 → 巡检算法·机巢·VTOL·法规政策
  🎨 3D生成/CAD → Rodin竞品·NeRF·高斯泼溅·生成式3D
  📈 量化金融 → 因子挖掘·强化学习交易·另类数据
  🧬 基因引擎 → 向量检索·知识图谱·RAG·Agent记忆
  🌐 开源兵器 → GitHub趋势·新工具·MCP服务器·AI编程
"""

import json, os, sys, time, subprocess
from datetime import datetime
from pathlib import Path
import urllib.request

# ═══ 配置 ═══════════════════════════════════════
DATA_DIR = Path.home() / "lgox-ops" / "data" / "radar-v4"
LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
TIANGONG = "http://100.118.207.31:11434"

# NGC配置(从天工走)
NGC_BASE = "https://integrate.api.nvidia.com/v1"
NGC_KEY = None  # 从天工.env读取

# 六大扫描域
SCAN_DOMAINS = {
    "ai-agent": {
        "name": "AI Agent架构",
        "arxiv_queries": ["multi-agent", "federated learning", "autonomous agent", "LLM agent framework", "MCP protocol", "agent memory"],
        "github_topics": ["ai-agent", "multi-agent", "llm-agent", "agent-framework", "mcp-server"],
        "keywords": ["agent", "multi-agent", "federation", "autonomous", "MCP", "tool-use", "agentic"],
        "priority": "P0",
    },
    "uav-lowalt": {
        "name": "无人机低空经济",
        "arxiv_queries": ["UAV inspection", "drone autonomous", "VTOL", "drone swarm", "aerial robotics", "drone navigation"],
        "github_topics": ["drone", "uav", "px4", "ardupilot", "drone-inspection"],
        "keywords": ["drone", "UAV", "inspection", "VTOL", "swarm", "aerial", "机巢", "巡检"],
        "priority": "P0",
    },
    "3d-generation": {
        "name": "3D生成/CAD",
        "arxiv_queries": ["3D generation", "NeRF", "Gaussian splatting", "text-to-3D", "image-to-3D", "CAD generation"],
        "github_topics": ["3d-generation", "nerf", "gaussian-splatting", "text-to-3d", "3d-reconstruction"],
        "keywords": ["3D", "NeRF", "splatting", "Rodin", "Tripo", "Meshy", "CAD", "mesh"],
        "priority": "P1",
    },
    "quant-finance": {
        "name": "量化金融",
        "arxiv_queries": ["quantitative finance", "reinforcement learning trading", "factor model", "market microstructure"],
        "github_topics": ["quantitative-finance", "algorithmic-trading", "rl-trading", "backtesting"],
        "keywords": ["quant", "trading", "alpha", "factor", "RL", "backtest", "signal"],
        "priority": "P1",
    },
    "gene-knowledge": {
        "name": "基因引擎/知识图谱",
        "arxiv_queries": ["vector database", "knowledge graph", "RAG retrieval", "embedding model", "graph neural network"],
        "github_topics": ["vector-database", "knowledge-graph", "rag", "embedding", "graphrag"],
        "keywords": ["vector", "embedding", "RAG", "graph", "knowledge", "retrieval", "gene"],
        "priority": "P0",
    },
    "opensource-arsenal": {
        "name": "开源兵器谱",
        "github_topics": ["ai-tool", "developer-tools", "cli", "vibe-coding", "code-agent", "mcp"],
        "keywords": ["tool", "CLI", "agent", "coding", "MCP", "automation", "open-source"],
        "priority": "P2",
    },
}

def log(msg):
    ts = datetime.now().strftime("%m%d-%H%M%S")
    print(f"[{ts}] {msg}", flush=True)

def ngc_chat(model, prompt, max_t=200, temp=0.3, timeout=20):
    """NGC推理·走天工网络"""
    cmd = f"""ssh -o ConnectTimeout=5 dgx1 'python3 -c "
import urllib.request, json
key=None
with open(\"/tmp/nvkey.env\") as f:
    key=f.read().strip().split(\"=\",1)[1].strip().strip(chr(34)).strip(chr(39))
body=json.dumps({{\"model\":\"{model}\",\"messages\":[{{\"role\":\"user\",\"content\":{json.dumps(prompt)}}}],\"max_tokens\":{max_t},\"temperature\":{temp}}}).encode()
req=urllib.request.Request(\"https://integrate.api.nvidia.com/v1/chat/completions\",data=body,headers={{\"Authorization\":f\"Bearer {{key}}\",\"Content-Type\":\"application/json\"}})
d=json.loads(urllib.request.urlopen(req,timeout={timeout}).read())
print(d[\"choices\"][0][\"message\"][\"content\"])
" 2>/dev/null'"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout+10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except:
        return ""

def tiangong_chat(prompt, max_t=150):
    """天工GPU本地推理·零成本·快速"""
    try:
        body = json.dumps({
            "model": "qwen2.5:14b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": max_t}
        }).encode()
        req = urllib.request.Request(f"{TIANGONG}/api/chat", data=body,
            headers={"Content-Type": "application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=20).read())
        return d.get("message", {}).get("content", "")
    except:
        return ""

def scan_arxiv(domain_key, domain_cfg):
    """arXiv论文扫描·NGC 30B深度分析"""
    log(f"🔬 {domain_cfg['name']}: arXiv扫描...")
    results = []
    for query in domain_cfg.get("arxiv_queries", [])[:3]:  # 每域3个查询
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.request.quote(query)}&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending"
            req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Radar/4.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            results.append({"query": query, "feed": resp.read().decode()[:5000]})
        except Exception as e:
            log(f"  arXiv {query}: {e}")

    # NGC 30B深度分析
    if results:
        summary_prompt = f"""分析以下arXiv论文摘要({domain_cfg['name']}领域)，提取3条LGOX联邦最有价值的前沿知识(每条50字内)，按格式输出:
[知识1] xxx
[知识2] xxx
[知识3] xxx

论文数据: {str(results)[:3000]}"""
        
        analysis = ngc_chat("nvidia/nemotron-3-nano-30b-a3b", summary_prompt, 200, 0.3, 25)
        if analysis:
            log(f"  NGC 30B分析: {analysis[:100]}...")
            return analysis
        else:
            # 降级天工
            return tiangong_chat(summary_prompt, 150)
    return ""

def scan_github(domain_key, domain_cfg):
    """GitHub趋势扫描·天工GPU快速分类"""
    log(f"📦 {domain_cfg['name']}: GitHub扫描...")
    findings = []
    for topic in domain_cfg.get("github_topics", [])[:2]:
        try:
            url = f"https://api.github.com/search/repositories?q=topic:{topic}+pushed:>2026-06-01&sort=stars&per_page=3"
            req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Radar/4.0", "Accept": "application/vnd.github.v3+json"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            for item in data.get("items", []):
                findings.append({
                    "name": item.get("full_name", ""),
                    "desc": item.get("description", "")[:200],
                    "stars": item.get("stargazers_count", 0),
                    "url": item.get("html_url", ""),
                    "topic": topic,
                })
        except Exception as e:
            log(f"  GitHub {topic}: {e}")

    if findings:
        # 天工快速分类
        classify_prompt = f"以下GitHub项目属于{domain_cfg['name']}领域。选出最有价值的2个·一句话说明为什么。\n项目:{json.dumps(findings,ensure_ascii=False)[:2000]}"
        result = tiangong_chat(classify_prompt, 100)
        if result:
            log(f"  天工分类: {result[:100]}...")
        return findings
    return []

def write_gene(content, fitness=0.55, memtype="semantic"):
    """写入地枢LGE基因库"""
    try:
        gene = {
            "content": f"[雷达v4.0·NGC驱动·{datetime.now().strftime('%m%d%H%M')}] {content[:500]}",
            "memory_type": memtype,
            "source": "联邦外部雷达v4.0/NGC-121模型",
            "fitness_score": fitness,
            "tags": ["雷达v4.0", "NGC", "外部吸收", "知识飞轮"]
        }
        data = json.dumps(gene).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        urllib.request.urlopen(req, timeout=8)
        return True
    except:
        return False

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log("═══ 联邦外部雷达v4.0 · NGC全火力 ═══")
    log(f"六大扫描域 · NGC 121模型 · 天工GPU执行 · 地枢LGE沉淀")

    total_genes = 0
    for key, cfg in SCAN_DOMAINS.items():
        log(f"\n{'='*40}")
        log(f"🎯 {cfg['name']} [{cfg['priority']}]")

        # arXiv深度扫描(NGC 30B)
        arxiv_insights = scan_arxiv(key, cfg)
        if arxiv_insights:
            for line in arxiv_insights.split("\n"):
                if "[知识" in line and len(line) > 15:
                    write_gene(f"[{cfg['name']}] {line.strip()}", 0.60)
                    total_genes += 1

        # GitHub趋势(天工快速)
        gh_findings = scan_github(key, cfg)
        if gh_findings:
            # 写基因
            for f in gh_findings[:2]:
                gene_content = f"[{cfg['name']}] {f['name']} ⭐{f['stars']}: {f['desc'][:200]}"
                write_gene(gene_content, 0.50)
                total_genes += 1

        time.sleep(2)  # 避免API速率限制

    # 汇总基因
    summary = f"雷达v4.0·{datetime.now().strftime('%m%d%H%M')}·NGC全火力·6域扫描·纳基因{total_genes}条"
    write_gene(summary, 0.70, "episodic")
    log(f"\n✅ 完成·纳基因{total_genes}条·{summary}")

if __name__ == "__main__":
    main()
