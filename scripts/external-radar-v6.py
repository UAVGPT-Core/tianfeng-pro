#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  联邦外部雷达 v6.0 · 20万条/天 · 百炼驱动                     ║
║  联邦缺什么扫什么·12源并行·智能去重·基因入库                   ║
╚══════════════════════════════════════════════════════════════╝
"""
import urllib.request, json, time, hashlib, os, sys, re, ssl, random, xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict

# ═══ 配置 ═══
NODE = os.uname().nodename
LGE_URL = "http://100.116.0.29:8200"
BAILIAN_KEY = "sk-ws-H.EHIYEYI.f6jb.MEUCIQCIyhdJsPiCjC_cWV5_zUNuyXuV9nZTOqY306dXA5jLCgIgYGqATo6q1EAxrcP4jBJe-MttLkdjv_1KOinp24UvTi8"
BAILIAN_BASE = "https://llm-mk03ginx8m9js38k.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
BATCH = 200     # 每批200条
CONCURRENCY = 5

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

seen_hashes = set()
total_written = 0

def log(msg):
    print(f"[{datetime.now().strftime('%H%M%S')}] 📡 {msg}", flush=True)

# ═══ 12大知识源 ═══
SOURCES = OrderedDict({
    # arXiv RSS feeds (免费·实时)
    "arxiv_cs_ai": "http://export.arxiv.org/rss/cs.AI",
    "arxiv_cs_lg": "http://export.arxiv.org/rss/cs.LG",
    "arxiv_cs_cl": "http://export.arxiv.org/rss/cs.CL",
    "arxiv_cs_cv": "http://export.arxiv.org/rss/cs.CV",
    "arxiv_cs_dc": "http://export.arxiv.org/rss/cs.DC",
    "arxiv_cs_cr": "http://export.arxiv.org/rss/cs.CR",
    "arxiv_stat_ml": "http://export.arxiv.org/rss/stat.ML",
    # GitHub Trending (免费API)
    "github_trending": "https://api.github.com/search/repositories?q=ai+machine+learning+created:>2026-07-01&sort=stars&per_page=30",
    # HuggingFace (模型趋势)
    "huggingface_models": "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=30",
    # Papers With Code
    "paperswithcode": "https://paperswithcode.com/api/v1/papers/?ordering=-publication_date&items_per_page=20",
    # HackerNews (科技新闻)
    "hackernews_top": "https://hacker-news.firebaseio.com/v0/topstories.json",
    # Reddit ML
    "reddit_ml": "https://www.reddit.com/r/MachineLearning/hot.json?limit=25",
})

def fetch_url(url, timeout=10):
    """智能抓取·带UA"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "LGOX-Radar/6.0", "Accept": "application/json,application/rss+xml,text/xml"
        })
        r = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        return r.read()
    except: return None

def parse_arxiv_rss(xml_data):
    """解析arXiv RSS"""
    items = []
    try:
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('.//item'):
            title = entry.find('title').text.strip() if entry.find('title') is not None else ""
            desc = entry.find('description').text.strip() if entry.find('description') is not None else ""
            link = entry.find('link').text.strip() if entry.find('link') is not None else ""
            if title and len(title) > 10:
                items.append({"title": title, "desc": desc[:300], "link": link, "source": "arXiv"})
    except: pass
    return items

def parse_hf_models(data):
    """解析HF模型列表"""
    items = []
    try:
        models = json.loads(data)
        for m in models[:30]:
            name = m.get("modelId", m.get("id", ""))
            tags = m.get("tags", m.get("pipeline_tag", ""))
            downloads = m.get("downloads", 0)
            if name:
                items.append({"title": f"HF模型: {name}", "desc": f"标签:{tags} 下载:{downloads}", "source": "HuggingFace"})
    except: pass
    return items

def parse_github(data):
    """解析GitHub trending"""
    items = []
    try:
        repos = json.loads(data).get("items", [])
        for r in repos[:30]:
            name = r.get("full_name", "")
            desc = r.get("description", "") or ""
            stars = r.get("stargazers_count", 0)
            if name:
                items.append({"title": f"GitHub: {name} ⭐{stars}", "desc": desc[:250], "source": "GitHub"})
    except: pass
    return items

def parse_pwc(data):
    """解析Papers With Code"""
    items = []
    try:
        papers = json.loads(data).get("results", [])
        for p in papers[:20]:
            title = p.get("title", "")
            abstract = p.get("abstract", "")[:200]
            if title:
                items.append({"title": title, "desc": abstract, "source": "PapersWithCode"})
    except: pass
    return items

def parse_hn(data):
    """解析HackerNews top stories"""
    items = []
    try:
        ids = json.loads(data)[:20]
        for sid in ids[:20]:
            try:
                url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                story = json.loads(fetch_url(url, 5) or b"{}")
                title = story.get("title", "")
                if title and any(k in title.lower() for k in ["ai","ml","data","gpu","llm","model","code","learn"]):
                    items.append({"title": f"HN: {title}", "desc": story.get("url", "")[:100], "source": "HackerNews"})
            except: pass
            if len(items) >= 10: break
    except: pass
    return items

def parse_reddit(data):
    """解析Reddit r/ML"""
    items = []
    try:
        posts = json.loads(data).get("data", {}).get("children", [])
        for p in posts[:20]:
            d = p.get("data", {})
            title = d.get("title", "")
            ups = d.get("ups", 0)
            if title and ups > 5:
                items.append({"title": f"Reddit: {title} 👍{ups}", "desc": d.get("selftext", "")[:150], "source": "Reddit"})
    except: pass
    return items

def fetch_all_sources():
    """并行抓取12源"""
    all_items = []
    log(f"并行抓取{len(SOURCES)}个源...")
    
    futures = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for name, url in SOURCES.items():
            futures[ex.submit(fetch_url, url, 12)] = name
    
    for f in as_completed(futures):
        name = futures[f]
        try:
            data = f.result()
            if not data: continue
            
            if "arxiv" in name:
                items = parse_arxiv_rss(data)
            elif "huggingface" in name:
                items = parse_hf_models(data)
            elif "github" in name:
                items = parse_github(data)
            elif "paperswithcode" in name:
                items = parse_pwc(data)
            elif "hackernews" in name:
                items = parse_hn(data)
            elif "reddit" in name:
                items = parse_reddit(data)
            else:
                items = []
            
            all_items.extend(items)
            log(f"  {name}: {len(items)}条")
        except: pass
    
    return all_items

def bailian_summarize(title, desc):
    """百炼qwen-turbo摘要+纳基因"""
    global total_written
    prompt = f"""Convert this technical finding into a concise knowledge gene (100-250 chars, Markdown):
Title: {title}
Details: {desc}

Output as: ### [Title]
**Key Insight**: (1 sentence)
**Relevance**: (why matters for AI federation)

Be specific. Include metrics if available."""
    
    try:
        body = json.dumps({"model":"qwen-turbo","messages":[{"role":"user","content":prompt}],
            "max_tokens":300,"temperature":0.5}).encode()
        req = urllib.request.Request(f"{BAILIAN_BASE}/chat/completions", data=body,
            headers={"Content-Type":"application/json","Authorization":f"Bearer {BAILIAN_KEY}"})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read())
        content = d["choices"][0]["message"]["content"].strip()
        
        if len(content) > 50:
            h = hashlib.md5(content.encode()).hexdigest()[:12]
            if h in seen_hashes: return False
            seen_hashes.add(h)
            
            # 写LGE
            try:
                data = json.dumps({"content":content,"memory_type":"semantic",
                    "source":"外部雷达v6","tags":["external","radar","scanned"],
                    "fitness":0.45}).encode()
                urllib.request.urlopen(urllib.request.Request(
                    f"{LGE_URL}/genes/write", data=data,
                    headers={"Content-Type":"application/json"}), timeout=5)
                total_written += 1
                return True
            except: pass
    except: pass
    return False

def run():
    global total_written
    ts = datetime.now().strftime("%m%d-%H%M")
    log(f"═══ 联邦外部雷达 v6.0 · 20万/天目标 ═══")
    
    # ① 抓取
    items = fetch_all_sources()
    log(f"抓取总计: {len(items)}条原始数据")
    
    # ② 去重+排序
    unique = []
    seen_titles = set()
    for it in items:
        t = it["title"][:80].lower()
        if t not in seen_titles:
            seen_titles.add(t)
            unique.append(it)
    random.shuffle(unique)
    unique = unique[:BATCH]
    
    log(f"去重后: {len(unique)}条·准备百炼摘要")
    
    # ③ 百炼并行摘要+入库
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = [ex.submit(bailian_summarize, it["title"], it["desc"]) for it in unique]
        for f in as_completed(futures):
            f.result()  # 结果在bailian_summarize中处理
    
    elapsed = time.time() - t0
    log(f"✅ 完成: +{total_written}基因 · {elapsed:.1f}s · {total_written/elapsed:.1f}条/s")
    
    # ④ 本轮产能估算
    rate = total_written / elapsed if elapsed > 0 else 0
    estimate_24h = int(rate * 3600 * 24)
    log(f"当前速率: {rate:.1f}条/s → 日产{estimate_24h:,}条")

if __name__ == "__main__":
    run()
