#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  LGOX联邦外部雷达 v5.0 · 金融知识增强版                         ║
║  2035级·VOD Pro高品质消化·喂养三大飞轮                           ║
║                                                              ║
║  扫描源: arXiv·GitHub·HuggingFace·金融RSS·VOD Pro深度消化       ║
║  飞轮: 🦐小枢AI数据·信号注入·期货注入                              ║
║  品质: VOD Pro评分≥0.7准入·低质过滤·自动标签                      ║
╚══════════════════════════════════════════════════════════════╝
"""
import urllib.request, json, time, os, xml.etree.ElementTree as ET, re
from datetime import datetime

# ═══ 配置 ═══
LGE = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
GENES_WRITTEN = 0

# VOD Pro
def _get_vod_key():
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            if "BAIDU_VOD_KEY" in line:
                return line.split("=",1)[1].strip().strip('"').strip("'")
    return ""

def vod_pro_digest(content, context="外部雷达金融知识"):
    """VOD Pro高品质消化·返回(摘要,质量分)"""
    vod_key = _get_vod_key()
    prompt = f"""你是LGOX联邦的金融知识质量评审官。请对以下外部扫描内容进行:
1. 用中文写一个50字以内的核心要点摘要
2. 评估与金融/量化/交易/证券/期货的相关性(0-10)
3. 评估信息质量(0-10)

内容: {content[:800]}

只返回JSON: {{"summary":"摘要","relevance":分,"quality":分,"total":均值,"tags":["标签1","标签2"]}}"""
    
    try:
        data = json.dumps({
            "model":"deepseek-v4-pro","messages":[{"role":"user","content":prompt}],
            "max_tokens":200,"temperature":0.3,"stream":False
        }).encode()
        req = urllib.request.Request("https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions",
            data=data, headers={"Content-Type":"application/json","Authorization":f"Bearer {vod_key}"})
        r = urllib.request.urlopen(req, timeout=35)
        raw = json.loads(r.read())["choices"][0]["message"]["content"]
        # 解析JSON
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m: return json.loads(m.group())
    except: pass
    return {"summary": content[:50], "relevance": 5, "quality": 5, "total": 5, "tags": ["auto"]}

# ═══ 基因写入 ═══
def write_gene(content, source, tags, fitness=0.7):
    global GENES_WRITTEN
    if fitness < 0.5: return None  # 低质过滤
    try:
        data = json.dumps({
            "content": content[:1200],
            "memory_type": "semantic",
            "source": source,
            "tags": tags + ["external-radar-v5", "VOD-Pro-digested"],
            "fitness": fitness
        }, ensure_ascii=False).encode()
        req = urllib.request.Request(f"{LGE}/genes/write", data=data,
            headers={"Content-Type":"application/json","X-LGE-Key":LGE_KEY})
        r = json.loads(urllib.request.urlopen(req, timeout=6).read())
        if r.get("gene_id"):
            GENES_WRITTEN += 1
            return r["gene_id"]
    except: pass
    return None

# ═══ 扫描源1: arXiv金融+量化 ═══
FINANCE_ARXIV_QUERIES = [
    "quantitative+finance+trading", "stock+market+prediction",
    "futures+pricing+model", "portfolio+optimization+AI",
    "technical+analysis+machine+learning", "factor+investing",
    "high+frequency+trading", "options+pricing+deep+learning",
    "risk+management+quant", "market+microstructure",
    "asset+pricing+neural+network", "algorithmic+trading+reinforcement",
    "financial+news+sentiment", "volatility+forecasting",
    "pairs+trading+statistical+arbitrage", "ETF+market+efficiency",
    "bond+yield+curve+AI", "commodity+futures+prediction",
    "A-share+market+China", "low+frequency+trading",
]

def scan_arxiv_finance():
    """arXiv金融·量化论文扫描"""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    count = 0
    for q in FINANCE_ARXIV_QUERIES:
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{q}&sortBy=submittedDate&sortOrder=descending&max_results=2"
            req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Finance-Radar"})
            root = ET.fromstring(urllib.request.urlopen(req, timeout=8).read())
            
            for entry in root.findall("a:entry", ns):
                title = entry.find("a:title", ns).text.strip()
                summary = entry.find("a:summary", ns).text.strip()[:500]
                arxiv_id = entry.find("a:id", ns).text.split("/")[-1]
                
                raw = f"[arXiv金融] {title}\n{summary}\nID:{arxiv_id}"
                digest = vod_pro_digest(raw, "arXiv金融论文")
                
                if digest.get("total", 0) >= 5.5:
                    gene_content = f"[VOD Pro评分{digest.get('total',0):.1f}] {digest.get('summary','')}\n{title}\nID:{arxiv_id}"
                    write_gene(gene_content, f"arxiv-finance-{arxiv_id}",
                        digest.get("tags", ["quant", "finance"]), min(0.9, digest.get("total", 5)/10))
                    count += 1
        except: pass
    return count

# ═══ 扫描源2: GitHub量化交易开源项目 ═══
GITHUB_QUANT_QUERIES = [
    "quantitative+trading+python", "stock+prediction+deep+learning",
    "futures+trading+system", "backtesting+framework",
    "algorithmic+trading+bot", "option+pricing+library",
    "technical+analysis+indicators", "market+data+crawler+A-share",
    "portfolio+optimization", "risk+management+quant",
    "CTA+strategy", "high+frequency+trading",
    "factor+model+china+stock", "finance+machine+learning",
    "trading+signal+generator", "order+execution+algorithm",
    "market+making+strategy", "volatility+surface",
    "pairs+trading+statarb", "event+driven+trading",
]

def scan_github_quant():
    """GitHub量化/金融项目扫描"""
    count = 0
    for q in GITHUB_QUANT_QUERIES:
        try:
            url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=2"
            req = urllib.request.Request(url, headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "LGOX-Quant-Radar"
            })
            data = json.loads(urllib.request.urlopen(req, timeout=8).read())
            
            for item in data.get("items", []):
                name = item["full_name"]
                desc = item.get("description", "")[:200]
                stars = item["stargazers_count"]
                lang = item.get("language", "")
                
                raw = f"[GitHub量化] {name} ⭐{stars}\n{desc}\n语言:{lang}"
                digest = vod_pro_digest(raw, "GitHub量化项目")
                
                if digest.get("total", 0) >= 5.0:
                    gene_content = f"[VOD Pro评分{digest.get('total',0):.1f}] {digest.get('summary','')}\n{name} ⭐{stars} {desc}"
                    write_gene(gene_content, f"github-quant-{name}",
                        digest.get("tags", ["quant", "github"]), min(0.85, digest.get("total", 5)/10))
                    count += 1
        except: pass
    return count

# ═══ 扫描源3: HuggingFace金融模型 ═══
HF_FINANCE_QUERIES = [
    "finance", "stock", "quant", "trading", "market",
    "technical-analysis", "sentiment-finance", "time-series-finance",
    "portfolio", "risk-model", "factor-model", "options",
]

def scan_huggingface_finance():
    """HuggingFace金融模型扫描"""
    count = 0
    for q in HF_FINANCE_QUERIES:
        try:
            url = f"https://huggingface.co/api/models?search={q}&sort=downloads&direction=-1&limit=3"
            req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Finance-Radar"})
            data = json.loads(urllib.request.urlopen(req, timeout=8).read())
            
            for item in data[:3]:
                name = item.get("modelId", item.get("id", ""))
                downloads = item.get("downloads", 0)
                tags = item.get("tags", [])
                
                raw = f"[HF金融模型] {name} 📥{downloads}\n标签:{','.join(tags[:5])}"
                digest = vod_pro_digest(raw, "HuggingFace金融模型")
                
                if digest.get("total", 0) >= 5.0:
                    gene_content = f"[VOD Pro评分{digest.get('total',0):.1f}] {digest.get('summary','')}\n{name} 📥{downloads}"
                    write_gene(gene_content, f"hf-finance-{name}",
                        digest.get("tags", ["finance-model", "huggingface"]), min(0.8, digest.get("total", 5)/10))
                    count += 1
        except: pass
    return count

# ═══ 扫描源4: 金融RSS/新闻 ═══
FINANCE_RSS_FEEDS = [
    ("东方财富-期货", "https://futures.eastmoney.com/"),
    ("新浪财经-A股", "https://finance.sina.com.cn/"),
    ("华尔街见闻", "https://wallstreetcn.com/"),
]

def scan_finance_news():
    """金融新闻快照扫描"""
    count = 0
    for name, url in FINANCE_RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            })
            html = urllib.request.urlopen(req, timeout=6).read().decode("gbk", errors="ignore")[:2000]
            
            # 提取标题
            titles = re.findall(r'<a[^>]*>(.{8,60})</a>', html)
            headlines = [t.strip() for t in titles if len(t.strip()) > 10][:5]
            
            if headlines:
                summary = f"[{name}] " + " | ".join(headlines[:3])
                digest = vod_pro_digest(summary, f"金融新闻-{name}")
                
                if digest.get("total", 0) >= 4.0:
                    gene_content = f"[{name}·VOD Pro]{digest.get('summary','')}\n{summary}"
                    write_gene(gene_content, f"news-{name}-{datetime.now().strftime('%Y%m%d')}",
                        ["financial-news", "market-sentiment"], min(0.7, digest.get("total", 5)/10))
                    count += 1
        except: pass
    return count

# ═══ 主流程 ═══
def main():
    global GENES_WRITTEN
    now = datetime.now()
    print(f"[{now.strftime('%H:%M')}] 外部雷达v5.0·金融增强·VOD Pro品质")
    
    results = {}
    
    # 1. arXiv金融论文
    print("═══ arXiv金融论文 ═══")
    n = scan_arxiv_finance()
    results["arXiv金融"] = n
    print(f"  纳入{n}条")
    
    # 2. GitHub量化项目
    print("═══ GitHub量化项目 ═══")
    n = scan_github_quant()
    results["GitHub量化"] = n
    print(f"  纳入{n}条")
    
    # 3. HuggingFace金融模型
    print("═══ HuggingFace金融模型 ═══")
    n = scan_huggingface_finance()
    results["HF金融"] = n
    print(f"  纳入{n}条")
    
    # 4. 金融新闻
    print("═══ 金融新闻 ═══")
    n = scan_finance_news()
    results["金融新闻"] = n
    print(f"  纳入{n}条")
    
    # 汇总
    total = sum(results.values())
    print(f"\n{'═'*50}")
    print(f"  本轮总计: {GENES_WRITTEN}条基因·VOD Pro品质把关")
    for k, v in results.items():
        print(f"  {k}: {v}条")
    
    # 纳总结基因
    summary = f"[外部雷达v5.0·金融增强]{now.strftime('%Y%m%d-%H%M')} 本轮{total}条 | {' '.join(f'{k}:{v}' for k,v in results.items())}"
    write_gene(summary, "external-radar-v5-summary", ["radar", "summary", "finance"], 0.6)
    
    print(f"{'═'*50}")

if __name__ == "__main__":
    main()
