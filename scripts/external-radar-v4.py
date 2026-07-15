#!/usr/bin/env python3
"""
LGOX联邦外部雷达 v4.0 · 多通多绿·永不丢基因·无人机全覆盖
四路写入 + 四大扫描源: arXiv·GitHub·HuggingFace·无人机产业
部署: 天工DGX1 cron每6h
"""
import urllib.request, json, time, os, xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

LGE = 'http://100.116.0.29:8200'
LGE_KEY = 'lgox-gene-key-2025'
BRIDGE = 'http://100.100.89.2:8765'
LOCAL_BACKUP = Path.home() / 'lgox-ops' / 'data' / 'radar-backup'
TIMEOUT = 30
GENES_WRITTEN = 0
Path(LOCAL_BACKUP).mkdir(parents=True, exist_ok=True)

# ═══ 四路写入引擎(同v3) ═══
def write_gene_quad(content, source, tags):
    data_bytes = json.dumps({
        'content': content[:1200], 'memory_type': 'semantic',
        'source': source, 'fitness': 0.35,
        'tags': tags + ['external-radar-v4', 'auto-ingest']
    }, ensure_ascii=False).encode()
    # 路1: LGE直写
    try:
        req = urllib.request.Request(f'{LGE}/genes/write', data=data_bytes,
            headers={'Content-Type': 'application/json', 'X-LGE-Key': LGE_KEY})
        r = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
        if r.get('gene_id'): return ('lge', r['gene_id'])
    except: pass
    # 路2: LGE重试
    try:
        time.sleep(2)
        req = urllib.request.Request(f'{LGE}/genes/write', data=data_bytes,
            headers={'Content-Type': 'application/json', 'X-LGE-Key': LGE_KEY})
        r = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
        if r.get('gene_id'): return ('lge-retry', r['gene_id'])
    except: pass
    # 路3: 联邦桥
    try:
        bridge_data = json.dumps({'session_id': f'radar-{int(time.time())}',
            'role': 'user', 'content': content[:1200], 'source': source, 'tags': tags}).encode()
        req = urllib.request.Request(f'{BRIDGE}/federated-store', data=bridge_data,
            headers={'Content-Type': 'application/json'})
        r = json.loads(urllib.request.urlopen(req, timeout=15).read())
        if r.get('status') == 'ok': return ('bridge', 'ok')
    except: pass
    # 路4: 本地灾备
    try:
        backup_file = LOCAL_BACKUP / f'radar-{int(time.time())}-{hash(content)%10000}.json'
        backup_file.write_text(json.dumps({'content': content[:1200], 'source': source,
            'tags': tags, 'timestamp': datetime.now().isoformat(), 'fitness': 0.35}, ensure_ascii=False))
        return ('backup', str(backup_file))
    except: return ('failed', None)

def batch_write_quad(genes):
    global GENES_WRITTEN
    stats = {'lge': 0, 'lge-retry': 0, 'bridge': 0, 'backup': 0}
    print(f'  四路批量写入 {len(genes)} 条(3并发)...')
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(write_gene_quad, g[0], g[1], g[2]): g for g in genes}
        for f in as_completed(futures):
            path, result = f.result()
            stats[path] = stats.get(path, 0) + 1
            if path != 'failed': GENES_WRITTEN += 1
    print(f'    LGE:{stats["lge"]} 重试:{stats["lge-retry"]} 桥:{stats["bridge"]} 灾备:{stats["backup"]}')
    return stats

# ═══ 扫描器 ═══
def scan_arxiv():
    print('[arXiv] AI/ML论文...')
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
    print('[GitHub] AI趋势...')
    genes = []
    try:
        url = 'https://api.github.com/search/repositories?q=AI+agent+autonomous&sort=stars&order=desc&per_page=5'
        req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'LGOX-Radar-v4'})
        resp = urllib.request.urlopen(req, timeout=20)
        for repo in json.loads(resp.read()).get('items', [])[:5]:
            genes.append((f'[GitHub] {repo["full_name"]} ⭐{repo["stargazers_count"]}\n{repo.get("description","")}\n{repo["html_url"]}',
                f'github-{repo["full_name"]}', ['GitHub', 'trending', 'AI']))
    except Exception as e: print(f'  GitHub err: {e}')
    print(f'[GitHub] {len(genes)}个')
    return genes

def scan_huggingface():
    print('[HuggingFace] 热门模型...')
    genes = []
    for url in ['https://huggingface.co/api/models?sort=downloads&limit=5',
                'https://hf-mirror.com/api/models?sort=downloads&limit=5']:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'LGOX-Radar-v4'})
            resp = urllib.request.urlopen(req, timeout=20)
            for model in json.loads(resp.read())[:5]:
                mid = model.get('modelId', model.get('id', ''))
                genes.append((f'[HuggingFace] {mid} ↓{model.get("downloads",0)}',
                    f'hf-{mid}', ['HuggingFace', 'model', 'trending']))
            if genes: break
        except Exception as e: print(f'  HF[{url[:40]}] err: {e}')
    print(f'[HuggingFace] {len(genes)}个')
    return genes

# ═══ 🆕 无人机产业扫描 v4.0 ═══
def scan_drone_industry():
    print('[无人机] 全产业链扫描...')
    genes = []
    
    # ① arXiv: 无人机/机器人/信号处理
    drone_queries = [
        ('UAV+drone+autonomous', '无人机自主'),
        ('aerial+inspection+robot', '巡检机器人'),
        ('swarm+UAV+formation', '无人机蜂群'),
        ('PX4+ArduPilot+flight+control', '开源飞控'),
        ('edge+computing+drone', '边缘计算无人机'),
        ('computer+vision+UAV', '无人机视觉'),
        ('lidar+SLAM+UAV', '激光雷达SLAM'),
        ('low+altitude+economy', '低空经济'),
        ('drone+delivery+logistics', '无人机物流'),
        ('VTOL+eVTOL+aircraft', '垂直起降'),
    ]
    for q, label in drone_queries:
        try:
            url = f'http://export.arxiv.org/api/query?search_query=all:{q}&sortBy=submittedDate&sortOrder=descending&max_results=2'
            resp = urllib.request.urlopen(url, timeout=20)
            root = ET.fromstring(resp.read())
            ns = {'a': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('a:entry', ns)[:2]:
                title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('a:summary', ns).text.strip()[:250]
                arxiv_id = entry.find('a:id', ns).text.split('/')[-1]
                genes.append((f'[无人机·arXiv] {title}\n{summary}\nID:{arxiv_id}',
                    f'drone-arxiv-{arxiv_id}', ['drone', 'UAV', 'arXiv', label]))
        except: pass
    print(f'  无人机论文: {len(genes)}篇')
    
    # ② GitHub: 开源飞控/机巢/DJI SDK
    drone_repos = [
        ('PX4/PX4-Autopilot', 'PX4开源飞控'),
        ('ArduPilot/ardupilot', 'ArduPilot飞控'),
        ('mavlink/mavlink', 'MAVLink协议'),
        ('dji-sdk/Mobile-SDK-Android', '大疆MSDK'),
        ('dji-sdk/UXSDK-Android', '大疆UXSDK'),
    ]
    for repo, label in drone_repos:
        try:
            url = f'https://api.github.com/repos/{repo}'
            req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'LGOX-Radar-v4'})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            genes.append((f'[无人机·GitHub] {repo} ⭐{data.get("stargazers_count",0)}\n{data.get("description","")}\n{data.get("html_url","")}',
                f'drone-github-{repo.replace("/","-")}', ['drone', 'UAV', 'GitHub', label]))
        except: pass
    print(f'  无人机仓库: {len(genes)-sum(1 for g in genes if "[无人机·arXiv]" in g[0])}个')
    
    # ③ GitHub搜索: 无人机+AI
    for q in ['DJI+drone+AI', 'PX4+autonomous', 'drone+inspection+AI', 'UAV+edge+computing']:
        try:
            url = f'https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=2'
            req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'LGOX-Radar-v4'})
            resp = urllib.request.urlopen(req, timeout=15)
            for repo in json.loads(resp.read()).get('items', [])[:2]:
                genes.append((f'[无人机·GitHub] {repo["full_name"]} ⭐{repo["stargazers_count"]}\n{repo.get("description","")}\n{repo["html_url"]}',
                    f'drone-gh-{repo["full_name"].replace("/","-")}', ['drone', 'UAV', 'GitHub', 'search']))
        except: pass
    
    total_drone = len(genes)
    print(f'[无人机] 合计: {total_drone}条')
    return genes

def drain_backups():
    backups = list(LOCAL_BACKUP.glob('*.json'))
    if not backups: return 0
    print(f'\n[灾备消化] {len(backups)}条...')
    recovered = 0
    for bf in backups[:50]:
        try:
            data = json.loads(bf.read_text())
            data_bytes = json.dumps({'content': data['content'][:1200], 'memory_type': 'semantic',
                'source': data.get('source','backup'), 'fitness': 0.35, 'tags': data.get('tags',[])}, ensure_ascii=False).encode()
            req = urllib.request.Request(f'{LGE}/genes/write', data=data_bytes,
                headers={'Content-Type': 'application/json', 'X-LGE-Key': LGE_KEY})
            r = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
            if r.get('gene_id'): bf.unlink(); recovered += 1
        except: pass
    if recovered: print(f'  灾备恢复: {recovered}')
    return recovered

# ═══ 主流程 v4.0 ═══
if __name__ == '__main__':
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[外部雷达v4.0·多通多绿·无人机] {ts}')
    
    drain_backups()
    
    all_genes = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(scan_arxiv): 'arXiv',
            pool.submit(scan_github): 'GitHub',
            pool.submit(scan_huggingface): 'HuggingFace',
            pool.submit(scan_drone_industry): '无人机',
        }
        for f in as_completed(futures):
            all_genes.extend(f.result())
    
    stats = batch_write_quad(all_genes)
    remaining = len(list(LOCAL_BACKUP.glob('*.json')))
    
    print(f'\n[外部雷达v4.0] 入库:{GENES_WRITTEN}/{len(all_genes)} 通路:LGE{stats["lge"]}+R{stats["lge-retry"]}+桥{stats["bridge"]}+备{stats["backup"]} 灾备:{remaining}')
    print(f'[{datetime.now().strftime("%H:%M:%S")}] 结束')
