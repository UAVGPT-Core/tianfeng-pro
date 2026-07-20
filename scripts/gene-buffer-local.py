#!/usr/bin/env python3
"""
LGOX联邦基因本地缓冲 — 地枢LGE离线时自动暂存→恢复后批量同步
部署: 天工DGX1 和 天枢Mac Studio
触发: 每2分钟cron·写入目标LGE失败时自动缓冲
"""
import sqlite3, json, time, os, urllib.request
from datetime import datetime

DB = os.path.expanduser('~/lgox-ops/data/gene-buffer.db')
LGE_URL = 'http://100.116.0.29:8200'  # 地枢Tailscale
LGE_KEY = 'lgox-gene-key-2025'
SYNC_INTERVAL = 120  # 每2分钟

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS buffer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        memory_type TEXT DEFAULT 'semantic',
        source TEXT DEFAULT '天工',
        tags TEXT DEFAULT '[]',
        fitness REAL DEFAULT 0.5,
        buffered_at TEXT,
        synced INTEGER DEFAULT 0
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_synced ON buffer(synced)')
    conn.commit()
    return conn

def buffer_gene(conn, content, source='天工', memory_type='semantic', tags=None, fitness=0.5):
    conn.execute('''INSERT INTO buffer (content, memory_type, source, tags, fitness, buffered_at)
        VALUES (?,?,?,?,?,?)''',
        (content, memory_type, source, json.dumps(tags or []), fitness, datetime.now().isoformat()))
    conn.commit()
    return True

def lge_health():
    try:
        r = urllib.request.urlopen(f'{LGE_URL}/health', timeout=3)
        return json.loads(r.read()).get('status') == 'ok'
    except:
        return False

def sync_to_lge(conn, batch=50):
    """批量同步缓冲基因到LGE"""
    genes = conn.execute('SELECT id,content,memory_type,source,tags,fitness FROM buffer WHERE synced=0 LIMIT ?', (batch,)).fetchall()
    if not genes:
        return 0
    
    synced = 0
    for gid, content, mtype, source, tags, fitness in genes:
        try:
            data = json.dumps({
                'content': content,
                'memory_type': mtype,
                'source': source,
                'tags': json.loads(tags) if isinstance(tags, str) else tags,
                'fitness': fitness
            }).encode()
            req = urllib.request.Request(f'{LGE_URL}/genes/write', data=data,
                headers={'Content-Type': 'application/json', 'X-API-Key': LGE_KEY})
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
            if resp.get('status') == 'ok':
                conn.execute('UPDATE buffer SET synced=1 WHERE id=?', (gid,))
                synced += 1
        except Exception as e:
            print(f'  ⚠️ 同步失败 id={gid}: {e}')
    
    conn.commit()
    return synced

def stats(conn):
    total = conn.execute('SELECT COUNT(*) FROM buffer').fetchone()[0]
    unsynced = conn.execute('SELECT COUNT(*) FROM buffer WHERE synced=0').fetchone()[0]
    synced = total - unsynced
    return total, unsynced, synced

if __name__ == '__main__':
    conn = init_db()
    lge_ok = lge_health()
    
    total, unsynced, synced = stats(conn)
    
    if lge_ok and unsynced > 0:
        n = sync_to_lge(conn, batch=100)
        total2, unsynced2, synced2 = stats(conn)
        print(f'[{datetime.now().strftime("%m%d-%H%M%S")}] 🟢 LGE在线·同步{n}条·缓冲区{total2}条·待同步{unsynced2}')
    elif lge_ok and unsynced == 0:
        print(f'[{datetime.now().strftime("%m%d-%H%M%S")}] 🟢 LGE在线·缓冲区空·{total}条已全部同步')
    else:
        print(f'[{datetime.now().strftime("%m%d-%H%M%S")}] 🔴 LGE离线·缓冲区{total}条·待同步{unsynced}条')
