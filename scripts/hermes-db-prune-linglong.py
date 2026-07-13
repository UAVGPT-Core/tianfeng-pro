#!/usr/bin/env python3
"""灵龙 state.db 瘦身器 - 分批删除cron机器会话(>7天)"""
import sqlite3, time, os

DB = os.path.expanduser('~/.hermes/state.db')
RETAIN = 7
BATCH = 2000

if not os.path.exists(DB):
    print(f"DB not found: {DB}")
    exit(1)

cutoff = time.time() - RETAIN * 86400
db = sqlite3.connect(DB, timeout=120)
db.execute('PRAGMA busy_timeout=120000')

c = db.execute("SELECT COUNT(*) FROM sessions WHERE source='cron' AND started_at < ?", (cutoff,))
total = c.fetchone()[0]
print(f"Target: {total} cron sessions >{RETAIN}d")

if total == 0:
    print("Nothing to prune.")
    db.close()
    exit(0)

s = m = b = 0
t0 = time.time()

while True:
    ids = [r[0] for r in db.execute(
        "SELECT id FROM sessions WHERE source='cron' AND started_at < ? LIMIT ?",
        (cutoff, BATCH)).fetchall()]
    if not ids:
        break
    
    ph = ','.join('?' * len(ids))
    mc = db.execute(f"SELECT COUNT(*) FROM messages WHERE session_id IN ({ph})", ids).fetchone()[0]
    db.execute(f"DELETE FROM messages WHERE session_id IN ({ph})", ids)
    db.execute(f"DELETE FROM sessions WHERE id IN ({ph})", ids)
    db.commit()
    s += len(ids)
    m += mc
    b += 1
    
    if b % 5 == 0:
        elapsed = time.time() - t0
        print(f"  Batch {b}: {s} sessions, {m} msgs ({elapsed:.0f}s)")

elapsed = time.time() - t0
print(f"Done: {s} sessions, {m} messages in {elapsed:.0f}s")

pc = db.execute("PRAGMA page_count").fetchone()[0]
print(f"state.db: {pc*4/1024:.0f} MB ({pc} pages)")
db.close()
