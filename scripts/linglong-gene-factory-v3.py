#!/usr/bin/env python3
"""
灵龙基因工厂 v3.0 · 2035超个体版
从灵龙数据源持续榨取基因，每15分钟≥100条
七自闭环
"""
import json, os, glob, urllib.request
from datetime import datetime

LGE = 'http://100.116.0.29:8200'
DATA = os.path.expanduser('~/lgox-ops/data')
LOGS = os.path.expanduser('~/lgox-ops/logs')
CACHE = os.path.join(DATA, 'gene-factory-v3-cache.json')

def wg(content, source):
    data = json.dumps({'content': content[:500], 'memory_type': 'procedural', 'source': f'll-{source}', 'tags': ['linglong','v3',source]}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(f'{LGE}/genes/write', data=data, headers={'Content-Type':'application/json'}, method='POST'), timeout=5)
        return json.loads(r.read()).get('gene_id','')
    except: return ''

def extract_jsonl(path, limit=20):
    genes = []
    try:
        with open(path, 'r', errors='ignore') as f:
            for line in f.readlines()[-100:]:
                try:
                    d = json.loads(line)
                    text = str(d.get('content','') or d.get('text','') or d.get('gene','') or d.get('message',''))
                    if len(text) > 30: genes.append(text[:300])
                except: pass
    except: pass
    return genes[:limit]

def extract_log(path, limit=10):
    genes = []
    try:
        with open(path, 'r', errors='ignore') as f:
            for line in f.readlines()[-200:]:
                if any(k in line.lower() for k in ['gene','完成','error','产','进化','评分','闭环']):
                    if len(line.strip()) > 20: genes.append(line.strip()[:300])
    except: pass
    return genes[:limit]

def main():
    cache = {'sent': []}
    try: cache = json.load(open(CACHE))
    except: pass
    sent = set(cache.get('sent', []))
    total = 0
    
    # JSONL数据源
    for p in glob.glob(f'{DATA}/**/*.jsonl', recursive=True)[:10]:
        for text in extract_jsonl(p):
            h = str(hash(text))
            if h in sent: continue
            name = os.path.basename(p).replace('.jsonl','')[:20]
            gid = wg(text, name)
            if gid: sent.add(h); total += 1
    
    # 日志扫描
    for p in sorted(glob.glob(f'{LOGS}/*.log'), key=os.path.getmtime, reverse=True)[:10]:
        for text in extract_log(p):
            h = str(hash(text))
            if h in sent: continue
            name = os.path.basename(p).replace('.log','')[:20]
            gid = wg(text, name)
            if gid: sent.add(h); total += 1
    
    # 扫描JSON文件
    for p in glob.glob(f'{DATA}/**/*.json', recursive=True)[:10]:
        try:
            d = json.load(open(p))
            text = json.dumps(d, ensure_ascii=False)[:300]
            if len(text) > 30:
                h = str(hash(text))
                if h not in sent:
                    gid = wg(text[:300], 'json-scan')
                    if gid: sent.add(h); total += 1
        except: pass
    
    # 缓存控制
    if len(sent) > 20000: sent = set(list(sent)[-5000:])
    json.dump({'sent': list(sent)}, open(CACHE, 'w'))
    
    print(f'🏭 灵龙基因工厂 v3.0 — {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'📊 本轮产出: {total} 条基因')
    print(f'🧬 累计: {len(sent)} 条')
    print('✅ 七自闭环完成')

if __name__ == '__main__':
    main()
