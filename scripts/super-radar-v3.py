#!/usr/bin/env python3
"""
LGOX超级雷达v3 — 多进程并行版
Phase 1: 扫描全部8源 (串行网络请求)
Phase 2: 并行GLM摘要 (multiprocessing)
Phase 3: 并行LGE写入
"""
import json, os, sys, time, re, hashlib, urllib.request, urllib.parse
from xml.etree import ElementTree
from datetime import datetime
from multiprocessing import Pool, cpu_count

# ── Load env ──
ENV_PATH = os.path.expanduser("~/.hermes/.env")
def load_env():
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line: continue
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
load_env()

ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "")
LGE_KEY = os.environ.get("LGE_KEY", "")
LGE_WRITE_URL = "http://100.116.0.29:8200/genes/write"

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 LGOX-Radar/3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

# ── Scanners ──
def scan_arxiv(cat, n=10):
    results = []
    url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&max_results={n}"
    try:
        xml_data = http_get(url, 25)
        root = ElementTree.fromstring(xml_data)
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry")[:n]:
            t = entry.find("{http://www.w3.org/2005/Atom}title")
            s = entry.find("{http://www.w3.org/2005/Atom}summary")
            l = entry.find("{http://www.w3.org/2005/Atom}id")
            results.append({
                "title": re.sub(r'\s+',' ',(t.text or "").strip()),
                "text": re.sub(r'\s+',' ',(s.text or "")[:500].strip()),
                "url": (l.text or "").strip(), "src": f"arxiv-{cat}",
            })
    except Exception as e:
        print(f"  arXiv {cat} error: {e}")
    return results

def scan_github(kw, n=10):
    results = []
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(kw)}+sort:stars&per_page={n}&sort=stars"
    try:
        data = json.loads(http_get(url, 15))
        for item in data.get("items", [])[:n]:
            d = item.get("description","") or ""
            results.append({
                "title": item.get("full_name",""), "src": f"github-{kw[:12]}",
                "text": f"{d[:300]} | stars:{item.get('stargazers_count',0)} | {item.get('language','')}",
                "url": item.get("html_url",""),
            })
    except:
        pass
    return results

def scan_hf(task, n=10):
    results = []
    url = f"https://huggingface.co/api/models?search={task}&sort=downloads&direction=-1&limit={n}"
    try:
        data = json.loads(http_get(url, 15))
        for item in data[:n]:
            mid = item.get("modelId","") or item.get("id","")
            desc = item.get("description","") or item.get("cardData",{}).get("summary","") or ""
            results.append({
                "title": mid, "src": f"hf-{task[:15]}",
                "text": f"{desc[:200]} | downloads:{item.get('downloads',0)} likes:{item.get('likes',0)}",
                "url": f"https://huggingface.co/{mid}",
            })
    except:
        pass
    return results

def scan_google_news(kw, n=6):
    results = []
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(kw)}&hl=zh-CN&gl=CN"
    try:
        xml_data = http_get(url, 15)
        root = ElementTree.fromstring(xml_data)
        for item in list(root.iter("item"))[:n]:
            t = item.findtext("title","")
            d = item.findtext("description","") or ""
            l = item.findtext("link","")
            results.append({"title": t, "text": d[:300], "url": l or "", "src": f"news-{kw[:10]}"})
    except:
        pass
    return results

def scan_nvidia(n=15):
    results = []
    # Try NVIDIA blog via news route (direct RSS timeout)
    try:
        xml_data = http_get("https://nvidianews.nvidia.com/feed.xml", 15)
        root = ElementTree.fromstring(xml_data)
        for item in list(root.iter("item"))[:n]:
            t = item.findtext("title","")
            d = item.findtext("description","") or ""
            l = item.findtext("link","")
            results.append({"title": t, "text": d[:300], "url": l or "", "src": "nvidia-blog"})
    except:
        pass
    # Fallback: NVIDIA AI blog via alternate feed
    if len(results) < 5:
        try:
            xml_data = http_get("https://blogs.nvidia.com/feed/", 15)
            root = ElementTree.fromstring(xml_data)
            for item in list(root.iter("item"))[:n]:
                t = item.findtext("title","")
                d = item.findtext("description","") or ""
                l = item.findtext("link","")
                results.append({"title": t, "text": d[:300], "url": l or "", "src": "nvidia-blog"})
        except:
            pass
    return results[:n]

def scan_dji(n=10):
    results = []
    for base in ["https://developer.dji.com/documentation/","https://developer.dji.com/api-reference/"]:
        try:
            html = http_get(base, 15).decode("utf-8",errors="replace")
            links = re.findall(r'href=["\']([^"\']+)["\']', html)
            for link in links:
                if any(x in link.lower() for x in ("document","api","guide","sdk")):
                    title = link.split("/")[-1].replace("-"," ").replace("_"," ").replace(".html","")
                    results.append({
                        "title": title[:80] or link, "src": "dji-docs",
                        "text": "DJI Dev: " + link,
                        "url": link if link.startswith("http") else f"https://developer.dji.com{link}",
                    })
                    if len(results)>=n: break
        except:
            pass
        if len(results)>=n: break
    return results[:n]

def scan_zh_news(n=15):
    results = []
    for q in ["人工智能 大模型 最新","无人机 AI 巡检","AI Agent 智能体"]:
        try:
            xml_data = http_get(f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-CN&gl=CN", 12)
            root = ElementTree.fromstring(xml_data)
            for item in list(root.iter("item"))[:5]:
                results.append({
                    "title": item.findtext("title",""), "text": (item.findtext("description","") or "")[:300],
                    "url": item.findtext("link","") or "", "src": "zh-ai-news",
                })
        except:
            pass
    return results[:n]

def scan_gov(n=10):
    results = []
    try:
        xml_data = http_get(f"https://news.google.com/rss/search?q={urllib.parse.quote('中国 人工智能 政策 算力 补贴')}&hl=zh-CN&gl=CN", 12)
        root = ElementTree.fromstring(xml_data)
        for item in list(root.iter("item"))[:n]:
            results.append({
                "title": item.findtext("title",""), "text": (item.findtext("description","") or "")[:300],
                "url": item.findtext("link","") or "", "src": "gov-policy",
            })
    except:
        pass
    return results

# ── Worker functions (top-level for multiprocessing) ──
def summarize_one(item):
    """GLM-4-Flash summarization"""
    key = ZHIPU_KEY
    if not key or not item.get("text"):
        item["summary"] = item.get("text","")[:150]
        item["tokens"] = 0
        return item
    
    title = item.get("title","")
    text = item.get("text","")[:1500]
    
    prompt = json.dumps({
        "model": "glm-4-flash", "temperature": 0.2, "max_tokens": 300,
        "messages": [{"role": "user", "content": f"用中文一句话摘要(≤150字):\n{title}\n{text}"}],
    }).encode()
    
    req = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        data=prompt,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            r = json.loads(resp.read())
        item["summary"] = r.get("choices",[{}])[0].get("message",{}).get("content","").strip()
        item["tokens"] = r.get("usage",{}).get("total_tokens",0)
    except Exception as e:
        item["summary"] = f"[auto] {text[:150]}"
        item["tokens"] = 0
    return item

def write_one(item):
    """Write one gene to LGE"""
    key = LGE_KEY
    summary = item.get("summary","") or item.get("text","")[:150]
    title = item.get("title","")
    src = item.get("src","")
    url = item.get("url","")
    
    content = f"# {title}\n**源**:{src}\n**链接**:{url}\n**摘要**:{summary}\n"
    payload = json.dumps({"content": content, "key": key, "fitness": 0.5}).encode()
    
    try:
        req = urllib.request.Request(LGE_WRITE_URL, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("status","ok")
    except Exception as e:
        return f"ERR:{e}"

def main():
    start = time.time()
    print(f"LGOX超级雷达v3 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"ZHIPU_KEY={'是' if ZHIPU_KEY else '否'} | LGE_KEY={'是' if LGE_KEY else '否'}")
    
    # ── Phase 1: Scan ──
    print(f"\n── 阶段1: 全源扫描 ({time.time()-start:.0f}s) ──")
    all_raw = []
    
    scans = [
        ("arXiv cs.CL", scan_arxiv("cs.CL",10)),
        ("arXiv cs.CV", scan_arxiv("cs.CV",10)),
        ("arXiv cs.AI", scan_arxiv("cs.AI",10)),
        ("arXiv cs.LG", scan_arxiv("cs.LG",10)),
        ("GitHub LLM agent", scan_github("LLM agent",10)),
        ("GitHub drone AI", scan_github("drone AI",10)),
        ("GitHub quant trading", scan_github("quantitative trading",10)),
        ("GitHub RAG pipeline", scan_github("RAG pipeline",10)),
        ("GitHub vision transformer", scan_github("vision transformer",10)),
        ("HF text-generation", scan_hf("text-generation",10)),
        ("HF image-classification", scan_hf("image-classification",10)),
        ("HF object-detection", scan_hf("object-detection",10)),
        ("News AI", scan_google_news("Artificial Intelligence",6)),
        ("News LLM", scan_google_news("large language model",6)),
        ("News robot", scan_google_news("AI robot",6)),
        ("News deep learning", scan_google_news("deep learning",6)),
        ("News autonomous", scan_google_news("autonomous driving",6)),
        ("NVIDIA Blog", scan_nvidia(15)),
        ("DJI Docs", scan_dji(10)),
        ("中文AI新闻", scan_zh_news(15)),
        ("政府政策", scan_gov(10)),
    ]
    
    for name, items in scans:
        all_raw.extend(items)
        print(f"  {name}: {len(items)}")
    
    # Dedup
    seen = set()
    deduped = []
    for it in all_raw:
        key = hashlib.md5((it.get("title","") or "").encode()).hexdigest()[:16]
        if key not in seen:
            seen.add(key)
            deduped.append(it)
    
    total = len(deduped)
    print(f"\n共采集 {len(all_raw)} 条 → 去重后 {total} 条")
    # Priority: ensure coverage across ALL sources
    priority_sources = ["zh-ai-news","gov-policy","nvidia-blog","dji-docs","news-","arxiv-"]
    priority = []
    rest = []
    for it in deduped:
        if any(it.get("src","").startswith(s) for s in priority_sources):
            priority.append(it)
        else:
            rest.append(it)
    batch = (priority + rest)[:100]
    print(f"优先排序: {len(priority)}条优先级源, {len(rest)}条普通源, 共处理: {len(batch)}条")
    
    # ── Phase 2: Parallel GLM summary ──
    n_workers = min(cpu_count(), 8)
    print(f"\n── 阶段2: 并行GLM摘要 ({n_workers} workers) [{time.time()-start:.0f}s] ──")
    t1 = time.time()
    with Pool(processes=n_workers) as pool:
        summarized = list(pool.imap_unordered(summarize_one, batch, chunksize=5))
    t2 = time.time()
    total_tokens = sum(it.get("tokens",0) for it in summarized)
    print(f"  GLM用时: {t2-t1:.1f}s | 消耗 {total_tokens} tokens")
    
    # ── Phase 3: Parallel LGE write ──
    print(f"\n── 阶段3: 并行LGE写入 ({n_workers} workers) [{time.time()-start:.0f}s] ──")
    t3 = time.time()
    with Pool(processes=n_workers) as pool:
        results = list(pool.imap_unordered(write_one, summarized, chunksize=5))
    t4 = time.time()
    
    written = sum(1 for r in results if "ERR" not in str(r))
    errors = sum(1 for r in results if "ERR" in str(r))
    print(f"  LGE写入用时: {t4-t3:.1f}s")
    
    # ── Report ──
    elapsed = time.time() - start
    src_counts = {}
    for it in batch:
        s = it.get("src","?")
        src_counts[s] = src_counts.get(s, 0) + 1
    
    print(f"\n{'='*60}")
    print(f"📡 LGOX超级雷达v3 完成报告")
    print(f"⏱ 总耗时: {elapsed:.1f}s")
    print(f"✅ 写入基因: {written}/{len(batch)}")
    print(f"❌ 失败: {errors}")
    print(f"🆓 GLM-4-Flash tokens: {total_tokens}")
    print(f"\n📊 源分布:")
    for s, c in sorted(src_counts.items(), key=lambda x:-x[1]):
        print(f"  {s}: {c}")
    
    report = json.dumps({"elapsed": round(elapsed,1), "written": written,
                         "errors": errors, "glm_tokens": total_tokens,
                         "sources": src_counts,
                         "timestamp": datetime.now().isoformat()}, ensure_ascii=False)
    print(f"\nJSON_REPORT:" + report)

if __name__ == "__main__":
    main()
