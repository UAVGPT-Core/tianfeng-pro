#!/usr/bin/env python3
"""
LGOX联邦外部雷达 v3.0 · 多通多绿·永不丢基因
四路写入: LGE直写 → 联邦桥中转 → 本地灾备 → 消化器补偿
部署: 天工DGX1 cron每6h
"""
import urllib.request, json, time, os, xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

LGE = 'http://100.116.0.29:8200'
LGE_KEY = 'lgox-gene-key-2025'
BRIDGE = 'http://100.100.89.2:8765'  # 天枢联邦桥
LOCAL_BACKUP = Path.home() / 'lgox-ops' / 'data' / 'radar-backup'
TIMEOUT = 30
GENES_WRITTEN = 0
GENES_BACKED_UP = 0

Path(LOCAL_BACKUP).mkdir(parents=True, exist_ok=True)

# ═══ 四路写入引擎 ═══
def write_gene_quad(content, source, tags):
    """
    四路写入·任一成功即返回
    路1: LGE直写(主)
    路2: LGE直写重试(间隔2s)
    路3: 联邦桥federated-store(天枢中转)
    路4: 本地JSON灾备(兜底·消化器会拾取)
    """
    data_bytes = json.dumps({
        'content': content[:1200],
        'memory_type': 'semantic',
        'source': source,
        'fitness': 0.35,
        'tags': tags + ['external-radar-v3', 'auto-ingest']
    }, ensure_ascii=False).encode()
    
    # 路1: LGE直写(30s超时)
    try:
        req = urllib.request.Request(f'{LGE}/genes/write', data=data_bytes,
            headers={'Content-Type': 'application/json', 'X-LGE-Key': LGE_KEY})
        r = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
        if r.get('gene_id'):
            return ('lge', r['gene_id'])
    except:
        pass
    
    # 路2: LGE重试(间隔2s)
    try:
        time.sleep(2)
        req = urllib.request.Request(f'{LGE}/genes/write', data=data_bytes,
            headers={'Content-Type': 'application/json', 'X-LGE-Key': LGE_KEY})
        r = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
        if r.get('gene_id'):
            return ('lge-retry', r['gene_id'])
    except:
        pass
    
    # 路3: 联邦桥中转
    try:
        bridge_data = json.dumps({
            'session_id': f'radar-{int(time.time())}',
            'role': 'user',
            'content': content[:1200],
            'source': source,
            'tags': tags
        }, ensure_ascii=False).encode()
        req = urllib.request.Request(f'{BRIDGE}/federated-store', data=bridge_data,
            headers={'Content-Type': 'application/json'})
        r = json.loads(urllib.request.urlopen(req, timeout=15).read())
        if r.get('status') == 'ok' or r.get('gene_id'):
            return ('bridge', r.get('gene_id', 'ok'))
    except:
        pass
    
    # 路4: 本地JSON灾备(永不丢)
    try:
        backup_file = LOCAL_BACKUP / f'radar-{int(time.time())}-{hash(content)%10000}.json'
        backup_file.write_text(json.dumps({
            'content': content[:1200], 'source': source, 'tags': tags,
            'timestamp': datetime.now().isoformat(), 'memory_type': 'semantic',
            'fitness': 0.35
        }, ensure_ascii=False))
        return ('backup', str(backup_file))
    except:
        return ('failed', None)
    
    return ('failed', None)

def batch_write_quad(genes):
    """四路并发批量写入"""
    global GENES_WRITTEN, GENES_BACKED_UP
    stats = {'lge': 0, 'lge-retry': 0, 'bridge': 0, 'backup': 0, 'failed': 0}
    
    print(f'  四路批量写入 {len(genes)} 条基因(3并发)...')
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(write_gene_quad, g[0], g[1], g[2]): g for g in genes}
        for f in as_completed(futures):
            path, result = f.result()
            stats[path] = stats.get(path, 0) + 1
            if path != 'failed':
                GENES_WRITTEN += 1
            if path == 'backup':
                GENES_BACKED_UP += 1
    
    print(f'    LGE直写:{stats["lge"]} 重试:{stats["lge-retry"]} 桥:{stats["bridge"]} 灾备:{stats["backup"]} 失败:{stats["failed"]}')
    return stats

# ═══ 扫描器(同v2) ═══
def scan_arxiv():
    print('[arXiv] 扫描中...')
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
                genes.append((f'[arXiv] {title}\n{summary}\nID:{arxiv_id}',
                    f'arxiv-{arxiv_id}', ['arXiv', 'paper', q.replace('+', ' ')]))
        except Exception as e:
            print(f'  arXiv[{q}] err: {e}')
    print(f'[arXiv] {len(genes)}篇')
    return genes

def scan_github():
    print('[GitHub] 扫描中...')
    genes = []
    try:
        url = 'https://api.github.com/search/repositories?q=AI+agent+autonomous&sort=stars&order=desc&per_page=5'
        req = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'LGOX-Radar-v3'})
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read())
        for repo in data.get('items', [])[:5]:
            name = repo['full_name']
            desc = repo.get('description', '') or ''
            stars = repo['stargazers_count']
            gene_content = f'[GitHub] {name} ⭐{stars}\n{desc}\n{repo["html_url"]}'
            genes.append((gene_content, f'github-{name}', ['GitHub', 'trending', 'AI']))
    except Exception as e:
        print(f'  GitHub err: {e}')
    print(f'[GitHub] {len(genes)}个仓库')
    return genes

def scan_huggingface():
    print('[HuggingFace] 扫描中...')
    genes = []
    for url in [
        'https://huggingface.co/api/models?sort=downloads&limit=5',
        'https://hf-mirror.com/api/models?sort=downloads&limit=5',
    ]:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'LGOX-Radar-v3'})
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read())
            for model in data[:5]:
                mid = model.get('modelId', model.get('id', ''))
                gene_content = f'[HuggingFace] {mid} ↓{model.get("downloads",0)}'
                genes.append((gene_content, f'hf-{mid}', ['HuggingFace', 'model', 'trending']))
            if genes: break
        except Exception as e:
            print(f'  HF[{url[:40]}] err: {e}')
    print(f'[HuggingFace] {len(genes)}个模型')
    return genes

# ═══ 灾备消化器(拾取本地备份·重新写入LGE) ═══
def drain_backups():
    """将本地灾备基因重新尝试写入LGE"""
    backups = list(LOCAL_BACKUP.glob('*.json'))
    if not backups:
        return 0
    
    print(f'\n[灾备消化] {len(backups)}条本地备份·重新写入LGE...')
    recovered = 0
    for backup_file in backups[:50]:  # 每次最多50条
        try:
            data = json.loads(backup_file.read_text())
            content = data.get('content', '')
            source = data.get('source', 'backup-recovery')
            tags = data.get('tags', [])
            
            data_bytes = json.dumps({
                'content': content[:1200], 'memory_type': 'semantic',
                'source': source, 'fitness': 0.35, 'tags': tags
            }, ensure_ascii=False).encode()
            
            req = urllib.request.Request(f'{LGE}/genes/write', data=data_bytes,
                headers={'Content-Type': 'application/json', 'X-LGE-Key': LGE_KEY})
            r = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
            if r.get('gene_id'):
                backup_file.unlink()  # 成功→删除备份
                recovered += 1
        except:
            pass  # 保留备份·下次再试
    
    print(f'  灾备恢复: {recovered}/{len(backups)}')
    return recovered

# ═══ 主流程 v3.0 ═══
if __name__ == '__main__':
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[外部雷达v3.0·多通多绿] {ts} 启动...')
    
    # ① 先消化本地灾备
    drain_backups()
    
    # ② 三源并发展开扫描
    all_genes = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(scan_arxiv): 'arXiv',
            pool.submit(scan_github): 'GitHub',
            pool.submit(scan_huggingface): 'HuggingFace'
        }
        for f in as_completed(futures):
            all_genes.extend(f.result())
    
    # ③ 四路写入
    stats = batch_write_quad(all_genes)
    
    # ④ 汇总
    remaining = len(list(LOCAL_BACKUP.glob('*.json')))
    print(f'\n[外部雷达v3.0] 完成.')
    print(f'  入库: {GENES_WRITTEN}/{len(all_genes)}')
    print(f'  通路: LGE{stats["lge"]}+重试{stats["lge-retry"]}+桥{stats["bridge"]}+灾备{stats["backup"]}')
    print(f'  灾备积压: {remaining}条')
    print(f'[{datetime.now().strftime("%H:%M:%S")}] 扫描结束')
