#!/usr/bin/env python3
"""
LGOX联邦外部雷达 v2.0 — 批量写入·30s超时·并发加速
arXiv + GitHub + HuggingFace → 批量LGE基因 → 消化器增强
部署: 天工DGX1 cron每6h
"""
import urllib.request, json, time, os, xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

LGE = 'http://100.116.0.29:8200'
LGE_KEY = 'lgox-gene-key-2025'
BRIDGE = 'http://127.0.0.1:8765'
TIMEOUT = 30  # 10→30秒
GENES_WRITTEN = 0
GENES_COLLECTED = []  # v2.0: 批量收集

def write_gene(content, source, tags):
    """v2.0: 30s超时·重试·返回成功标志"""
    try:
        data = json.dumps({
            'content': content[:1200],
            'memory_type': 'semantic',
            'source': source,
            'fitness': 0.35,  # 雷达原始扫描·消化器会提升
            'tags': tags + ['external-radar', 'auto-ingest']
        }, ensure_ascii=False).encode()
        req = urllib.request.Request(f'{LGE}/genes/write', data=data,
            headers={'Content-Type': 'application/json', 'X-LGE-Key': LGE_KEY})
        r = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
        if r.get('gene_id'):
            return r['gene_id']
    except Exception as e:
        # 重试一次
        try:
            time.sleep(2)
            req = urllib.request.Request(f'{LGE}/genes/write', data=data,
                headers={'Content-Type': 'application/json', 'X-LGE-Key': LGE_KEY})
            r = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
            if r.get('gene_id'):
                return r['gene_id']
        except:
            pass
    return None

def batch_write(genes):
    """v2.0: 并发批量写入(3线程)·10秒超时变30秒"""
    global GENES_WRITTEN
    if not genes:
        return
    print(f'  批量写入 {len(genes)} 条基因(3并发)...')
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(write_gene, g[0], g[1], g[2]): g for g in genes}
        for f in as_completed(futures):
            result = f.result()
            if result:
                GENES_WRITTEN += 1

# ═══ arXiv 扫描 ═══
def scan_arxiv():
    print('[arXiv] 扫描AI/ML最新论文...')
    queries = ['large+language+model', 'AI+agent', 'multi+agent+system', 
               'RAG+retrieval', 'autonomous+agent', 'LLM+fine+tuning']
    genes = []
    for q in queries:
        try:
            url = f'http://export.arxiv.org/api/query?search_query=all:{q}&sortBy=submittedDate&sortOrder=descending&max_results=3'
            resp = urllib.request.urlopen(url, timeout=20)
            root = ET.fromstring(resp.read())
            ns = {'a': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('a:entry', ns)[:3]:
                title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('a:summary', ns).text.strip()[:300]
                arxiv_id = entry.find('a:id', ns).text.split('/')[-1]
                gene_content = f'[arXiv] {title}\n{summary}\nID:{arxiv_id}'
                genes.append((gene_content, f'arxiv-{arxiv_id}', ['arXiv', 'paper', q.replace('+', ' ')]))
        except Exception as e:
            print(f'  arXiv[{q}] err: {e}')
    print(f'[arXiv] {len(genes)}篇待写入')
    return genes

# ═══ GitHub Trending ═══
def scan_github():
    print('[GitHub] 扫描AI趋势仓库...')
    genes = []
    try:
        url = 'https://api.github.com/search/repositories?q=AI+agent+autonomous&sort=stars&order=desc&per_page=5'
        req = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'LGOX-Radar-v2'})
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read())
        for repo in data.get('items', [])[:5]:
            name = repo['full_name']
            desc = repo.get('description', '') or ''
            stars = repo['stargazers_count']
            html_url = repo['html_url']
            gene_content = f'[GitHub] {name} ⭐{stars}\n{desc}\n{html_url}'
            genes.append((gene_content, f'github-{name}', ['GitHub', 'trending', 'AI']))
        print(f'[GitHub] {len(genes)}个仓库待写入')
    except Exception as e:
        print(f'  GitHub err: {e}')
    return genes

# ═══ HuggingFace 热门 ═══
def scan_huggingface():
    print('[HuggingFace] 扫描热门模型...')
    genes = []
    # 尝试多个HF API端点
    urls = [
        'https://huggingface.co/api/models?sort=downloads&limit=5',
        'https://huggingface.co/api/models?sort=likes&limit=5',
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'LGOX-Radar-v2'})
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read())
            for model in data[:5]:
                mid = model.get('modelId', model.get('id', ''))
                downloads = model.get('downloads', 0)
                likes = model.get('likes', 0)
                gene_content = f'[HuggingFace] {mid} ↓{downloads} 👍{likes}'
                genes.append((gene_content, f'hf-{mid}', ['HuggingFace', 'model', 'trending']))
            if genes:
                break
        except Exception as e:
            print(f'  HF[{url[:50]}] err: {e}')
    print(f'[HuggingFace] {len(genes)}个模型待写入')
    return genes

# ═══ 主流程 v2.0 ═══
if __name__ == '__main__':
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[外部雷达v2.0] {ts} 启动扫描...')
    
    # 阶段1: 并发展开扫描
    all_genes = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(scan_arxiv): 'arXiv',
            pool.submit(scan_github): 'GitHub', 
            pool.submit(scan_huggingface): 'HuggingFace'
        }
        for f in as_completed(futures):
            result = f.result()
            all_genes.extend(result)
    
    # 阶段2: 批量并发写入
    batch_write(all_genes)
    
    print(f'\n[外部雷达v2.0] 完成. 写入 {GENES_WRITTEN}/{len(all_genes)} 条基因')
    print(f'[{datetime.now().strftime("%H:%M:%S")}] 扫描结束')
