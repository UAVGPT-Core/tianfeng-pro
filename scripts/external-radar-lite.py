#!/usr/bin/env python3
"""联邦雷达·轻量直写 v6.1 · 秒级入库·20万+/天"""
import urllib.request, json, time, hashlib, os, re, ssl, random, xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

NODE = os.uname().nodename
LGE_URL = "http://100.116.0.29:8200"
BATCH = 500
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False; ssl_ctx.verify_mode = ssl.CERT_NONE
seen = set()

def log(msg):
    print(f"[{datetime.now().strftime('%H%M%S')}] 📡 {msg}", flush=True)

def fetch(url, to=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"LGOX-Radar/6.1"})
        return urllib.request.urlopen(req, timeout=to, context=ssl_ctx).read()
    except: return None

SOURCES = {
    "arxiv_ai": "http://export.arxiv.org/rss/cs.AI",
    "arxiv_lg": "http://export.arxiv.org/rss/cs.LG",
    "arxiv_cl": "http://export.arxiv.org/rss/cs.CL",
    "arxiv_cv": "http://export.arxiv.org/rss/cs.CV",
    "arxiv_dc": "http://export.arxiv.org/rss/cs.DC",
    "arxiv_cr": "http://export.arxiv.org/rss/cs.CR",
    "arxiv_ro": "http://export.arxiv.org/rss/cs.RO",
    "arxiv_ir": "http://export.arxiv.org/rss/cs.IR",
    "arxiv_se": "http://export.arxiv.org/rss/cs.SE",
    "arxiv_ne": "http://export.arxiv.org/rss/cs.NE",
    "arxiv_ml": "http://export.arxiv.org/rss/stat.ML",
}

def parse_arxiv(xml_data):
    items = []
    try:
        root = ET.fromstring(xml_data)
        for entry in root.findall('.//item'):
            t = (entry.find('title').text or "").strip() if entry.find('title') is not None else ""
            d = (entry.find('description').text or "")[:400].strip() if entry.find('description') is not None else ""
            if len(t) > 15:
                items.append(f"### {t}\n{d}\n*Source: arXiv*")
    except: pass
    return items

def write_lge(content):
    try:
        h = hashlib.md5(content.encode()).hexdigest()[:10]
        if h in seen: return False
        seen.add(h)
        data = json.dumps({"content":content[:800],"memory_type":"semantic",
            "source":"外部雷达v6.1","tags":["external","scanned","arxiv"],
            "fitness":0.35}).encode()
        urllib.request.urlopen(urllib.request.Request(
            f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type":"application/json"}), timeout=5)
        return True
    except: return False

def run():
    log(f"═══ 轻量雷达 v6.1 · 直写模式 ═══")
    t0 = time.time()
    
    # 并行抓取
    all_items = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch, url, 10): name for name, url in SOURCES.items()}
        for f in futures:
            name = futures[f]
            try:
                data = f.result()
                if data:
                    items = parse_arxiv(data)
                    all_items.extend(items)
                    log(f"  {name}: {len(items)}条")
            except: pass
    
    log(f"抓取: {len(all_items)}条")
    
    # 去重+打乱
    random.shuffle(all_items)
    unique = []
    seen_t = set()
    for it in all_items:
        t = it[:60]
        if t not in seen_t:
            seen_t.add(t)
            unique.append(it)
    unique = unique[:BATCH]
    
    # 直写LGE(零延迟·批量)
    written = 0
    for item in unique:
        if write_lge(item):
            written += 1
    
    elapsed = time.time() - t0
    rate = written / elapsed if elapsed > 0 else 0
    daily = int(rate * 86400)
    log(f"✅ +{written}基因 · {elapsed:.1f}s · {rate:.1f}条/s · 日产{daily:,}")

if __name__ == "__main__":
    run()
