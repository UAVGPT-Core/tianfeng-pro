#!/usr/bin/env python3
"""灵龙 — 删更老的cron消息(7天前) + 空壳会话 + VACUUM"""
import sqlite3, os, time

DB = os.path.expanduser("~/.hermes/state.db")
SIZE_BEFORE = os.path.getsize(DB)

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

log(f"DB: {SIZE_BEFORE/(1024**3):.2f}GB | {SIZE_BEFORE} bytes")

db = sqlite3.connect(DB)
db.execute("PRAGMA synchronous=OFF")
db.execute("PRAGMA journal_mode=WAL")

# 删7天前所有cron会话
cutoff = time.time() - 7 * 86400
cron_ids = [r[0] for r in db.execute(
    "SELECT id FROM sessions WHERE source='cron' AND started_at < ?", (cutoff,)).fetchall()]
log(f"7天前cron会话: {len(cron_ids)}条")

if cron_ids:
    # 分批删消息
    B=500
    for i in range(0, len(cron_ids), B):
        ids = cron_ids[i:i+B]
        p = ",".join(["?"]*len(ids))
        db.execute(f"DELETE FROM messages WHERE session_id IN ({p})", ids)
        db.commit()
        if i % 2000 == 0:
            log(f"  消息: {i}/{len(cron_ids)}")
    
    for sid in cron_ids:
        db.execute("DELETE FROM sessions WHERE id=?", (sid,))
    db.commit()
    log(f"cron已删: {len(cron_ids)}")

# 删所有message_count=0的空壳会话
null_sessions = [r[0] for r in db.execute(
    "SELECT id FROM sessions WHERE message_count=0 OR message_count IS NULL").fetchall()]
log(f"空壳会话: {len(null_sessions)}条")
for sid in null_sessions:
    db.execute("DELETE FROM sessions WHERE id=?", (sid,))
db.commit()
log(f"空壳已删: {len(null_sessions)}")

rows = db.execute("SELECT source, COUNT(*) FROM sessions GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
msg_cnt = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
log(f"剩余: {rows}")
log(f"消息: {msg_cnt}")

# 统计各source的数据量
log("数据量统计...")
for eng in ["cron","cli"]:
    cnt = db.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(content)),0) FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE source=?)", (eng,)).fetchone()
    log(f"  {eng}: {cnt[0]}条消息, {cnt[1]/(1024**3):.2f}GB")

db.close()

# 简单VACUUM
log("VACUUM...")
db2 = sqlite3.connect(DB)
db2.execute("VACUUM")
db2.close()

SIZE_AFTER = os.path.getsize(DB)
log(f"清后DB: {SIZE_AFTER/(1024**3):.2f}GB")
log(f"释放: {(SIZE_BEFORE-SIZE_AFTER)/(1024**3):.2f}GB")
log("===")
