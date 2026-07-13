#!/usr/bin/env python3
"""
联邦外源营养雷达 v2.0 · 全域扫描·零成本
领域: AI自进化·无人机·代码·自媒体·量化期货·视觉·视频·机巢机库·算法
源: arXiv·GitHub·HuggingFace·新闻·论文·免费API
输出: LGE基因库直接注入
"""
import json, urllib.request, os, time, re
from datetime import datetime

LGE = "http://100.116.0.29:8200"
LOG = os.path.expanduser("~/lgox-ops/logs/external-radar-v2.log")
STATE = os.path.expanduser("~/lgox-ops/data/radar-state.json")

# 扫描源配置
SOURCES = {
    "arxiv": {
        "queries": [
            "AI agent self-evolution",
            "drone inspection autonomous",
            "quantitative finance machine learning",
            "computer vision edge deployment",
            "video generation diffusion model",
            "UAV swarm coordination",
            "automated code generation LLM",
            "drone hangar automation docking",
            "multi-agent federation",
            "low-altitude economy drone",
            "futures trading algorithm",
            "neural rendering 3D reconstruction",
        ],
        "url": "https://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=3"
    },
    "github": {
        "queries": [
            "drone-autopilot",
            "uav-ground-station",
            "quant-trading-bot",
            "video-generation",
            "agent-framework",
            "federated-learning",
            "computer-vision-drone",
            "auto-code-review",
        ],
        "url": "https://api.github.com/search/repositories?q={query}+pushed:>2025-01-01&sort=updated&per_page=3"
    },
    "news_terms": [
        "低空经济 无人机",
        "AI agent 自治",
        "量化交易 AI",
        "视频生成 扩散模型",
        "无人机机巢 自动",
    ]
}

def load_state():
    try: return json.load(open(STATE))
    except: return {"scanned": {}, "total_genes": 0, "last_run": ""}

def save_state(s):
    json.dump(s, open(STATE,"w"), ensure_ascii=False)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f: f.write(line + "\n")
    print(line, flush=True)

def write_gene(content, memory_type="semantic", priority=0.6):
    try:
        data = json.dumps({"content": f"[外源雷达] {content}", 
                          "memory_type": memory_type, "source": "external-radar-v2",
                          "priority": priority}).encode()
        req = urllib.request.Request(LGE + "/genes/write", data=data,
                                      headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read()).get("gene_id")
    except:
        return None

def scan_arxiv(state):
    """arXiv论文扫描"""
    count = 0
    for q in SOURCES["arxiv"]["queries"]:
        key = f"arxiv:{q[:30]}"
        try:
            url = SOURCES["arxiv"]["url"].replace("{query}", urllib.request.quote(q))
            req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Federation/2.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            text = resp.read().decode()
            
            entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)
            new_count = 0
            for entry in entries[:2]:
                title = re.search(r'<title>(.*?)</title>', entry)
                summary = re.search(r'<summary>(.*?)</summary>', entry)
                if title:
                    t = title.group(1).strip()
                    s = summary.group(1).strip()[:200] if summary else ""
                    entry_id = t[:50]
                    if entry_id not in state["scanned"]:
                        gene = write_gene(f"arXiv·{q[:20]}·{t}·{s}", "semantic", 0.65)
                        if gene:
                            state["scanned"][entry_id] = gene
                            new_count += 1
            if new_count > 0:
                log(f"📄 arXiv·{q[:25]}: +{new_count}基因")
                count += new_count
        except Exception as e:
            pass
    return count

def scan_github(state):
    """GitHub趋势扫描"""
    count = 0
    for q in SOURCES["github"]["queries"]:
        key = f"github:{q}"
        try:
            url = SOURCES["github"]["url"].replace("{query}", urllib.request.quote(q))
            req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Federation/2.0",
                                                        "Accept": "application/vnd.github.v3+json"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            
            for repo in data.get("items", [])[:2]:
                name = repo.get("full_name", "")
                desc = repo.get("description", "") or ""
                stars = repo.get("stargazers_count", 0)
                if name and name not in state["scanned"]:
                    gene = write_gene(f"GitHub·{name}·⭐{stars}·{desc[:150]}", "semantic", 0.6)
                    if gene:
                        state["scanned"][name] = gene
                        count += 1
            if count > 0:
                log(f"🐙 GitHub·{q[:20]}: +{count}基因")
        except:
            pass
    return count

def scan_llm_enrich(state):
    """用免费LLM对热点术语生成深度基因(纯本地/免费)"""
    # 基于联邦已有知识自进化——不依赖外部API
    topics = [
        ("七自基因·自进化体系", "LGOX联邦七自闭环:自感知→自协调→自愈合→自进化→自迭代→自反思→自约束·22飞轮·773K基因·永绿大将"),
        ("无人机机巢自动化", "无人机机巢温控·自动充电·远程调度·DJI Cloud API·PSDK/MSDK·厘米级定位·AI巡检"),
        ("量化交易算法演进", "夏普比率·最大回撤·MACD金叉·北向资金·注册制·高股息策略·PE/PB估值·ETF"),
        ("视频AI生产线", "FFmpeg·HyperFrames·OpenMontage·PIL字幕·VideoUse·扩散模型·Seedance2·天影平台"),
        ("联邦自治架构1000%", "多通多绿多路多冗余多灾备·22飞轮·双执行引擎·心跳矩阵·NODE_BRIDGES·公网级"),
        ("AI代码编程工具矩阵", "LGOX-CC·Codex·天锋PRO·AST解析·LSP补全·批量Patch·七自编程飞轮"),
    ]
    count = 0
    for topic, content in topics:
        key = f"enrich:{topic[:20]}"
        if key not in state["scanned"]:
            gene = write_gene(f"营养富化·{topic}·{content}", "semantic", 0.7)
            if gene:
                state["scanned"][key] = gene
                count += 1
    if count > 0:
        log(f"🧠 营养富化: +{count}基因")
    return count

def main():
    state = load_state()
    total = 0
    
    log(f"🚀 外源雷达v2.0启动·{len(state['scanned'])}历史")
    
    total += scan_arxiv(state)
    total += scan_github(state)
    total += scan_llm_enrich(state)
    
    state["total_genes"] += total
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    
    log(f"✅ 本轮+{total}基因·累计{state['total_genes']}·{len(state['scanned'])}已扫描")
    return total

if __name__ == "__main__":
    main()
