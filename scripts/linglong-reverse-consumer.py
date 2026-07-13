#!/usr/bin/env python3
'''
灵龙反向消化器 v1.0 · 天枢→灵龙消息自动消费
FCPF v5.1 · 30s轮询 · 读天枢回执 → 纳基因 → 标记已读
'''
import json, os, sys, time, sqlite3, urllib.request, subprocess
from datetime import datetime

MSG_DB = os.path.expanduser('~/.hermes/fed_messages.db')
LGE = 'http://100.116.0.29:8200/genes/write'
INTERVAL = 30

def get_unread():
    try:
        c = sqlite3.connect(MSG_DB)
        rows = c.execute(
            'SELECT id, from_node, content, ts FROM messages WHERE node=? AND read=0 AND from_node=? ORDER BY id ASC LIMIT 10',
            ('灵龙', '天枢')).fetchall()
        msgs = [{'id': r[0], 'from': r[1], 'content': r[2], 'ts': r[3]} for r in rows]
        c.close()
        return msgs
    except: return []

def mark_read(mid):
    try:
        c = sqlite3.connect(MSG_DB)
        c.execute('UPDATE messages SET read=1 WHERE id=?', (mid,))
        c.commit(); c.close()
    except: pass

def write_gene(content):
    try:
        d = json.dumps({'content': f'[灵龙消化天枢] {content[:400]}', 'memory_type': 'episodic',
            'source': 'linglong-reverse-consumer', 'tags': '["domain:meta","fcpg","communication"]'}).encode()
        urllib.request.urlopen(urllib.request.Request(LGE, data=d,
            headers={'Content-Type': 'application/json'}, method='POST'), timeout=5)
        return True
    except: return False

def main():
    print(f'🐉 灵龙反向消化器 v1.0 | FCPF v5.1 | {INTERVAL}s', flush=True)
    while True:
        try:
            msgs = get_unread()
            if msgs:
                now = datetime.now().strftime('%H:%M:%S')
                print(f'\n[{now}] 📬 天枢回执 x{len(msgs)}', flush=True)
                for m in msgs:
                    content = m['content'] or ''
                    print(f'  ← 天枢: {content[:100]}...', flush=True)
                    # 纳基因
                    if content and len(content) > 20:
                        write_gene(content[:400])
                        print(f'    → 🧬 已纳基因', flush=True)
                    mark_read(m['id'])
            time.sleep(INTERVAL)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f'  [err] {e}', flush=True)
            time.sleep(INTERVAL)

main()
