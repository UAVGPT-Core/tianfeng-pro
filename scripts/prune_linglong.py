#!/usr/bin/env python3
"""灵龙 state.db 全量深度清理"""
import sqlite3, os, time

DB = os.path.expanduser("~/.hermes/state.db")
SIZE_BEFORE = os.path.getsize(DB)

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

log(f"清前DB: {SIZE_BEFORE/(1024**3):.2f}GB")

db = sqlite3.connect(DB)
db.execute("PRAGMA synchronous=OFF")
db.execute("PRAGMA journal_mode=WAL")

# 1. Drop FTS triggers
for t in ["messages_fts_insert","messages_fts_delete","messages_fts_update",
           "messages_fts_trigram_insert","messages_fts_trigram_delete","messages_fts_trigram_update"]:
    db.execute(f"DROP TRIGGER IF EXISTS {t}")
log("FTS触发器已删")

# 2. 获取3天前cron会话
cutoff = time.time() - 3 * 86400
cron_ids = [r[0] for r in db.execute(
    "SELECT id FROM sessions WHERE source='cron' AND started_at < ?", (cutoff,)).fetchall()]
log(f"3天前cron: {len(cron_ids)}条")

# 3. 分批删消息
batch = 200
for i in range(0, len(cron_ids), batch):
    ids = cron_ids[i:i+batch]
    placeholders = ",".join(["?"] * len(ids))
    db.execute(f"DELETE FROM messages WHERE session_id IN ({placeholders})", ids)
    db.commit()
    if i % 1000 == 0:
        log(f"  删消息: {i}/{len(cron_ids)}")

# 4. 删会话
for sid in cron_ids:
    db.execute("DELETE FROM sessions WHERE id=?", (sid,))
db.commit()
log(f"cron会话已删: {len(cron_ids)}")

# 5. 删7天前subagent
cutoff7 = time.time() - 7 * 86400
sub_ids = [r[0] for r in db.execute(
    "SELECT id FROM sessions WHERE source='subagent' AND started_at < ?", (cutoff7,)).fetchall()]
for sid in sub_ids:
    db.execute("DELETE FROM messages WHERE session_id=?", (sid,))
    db.execute("DELETE FROM sessions WHERE id=?", (sid,))
db.commit()
log(f"subagent已删: {len(sub_ids)}")

# 6. 统计
rows = db.execute("SELECT source, COUNT(*) FROM sessions GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
msg_count = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
log(f"会话剩余: {rows}")
log(f"消息剩余: {msg_count}")

db.close()

# 7. VACUUM
log("VACUUM...")
db2 = sqlite3.connect(DB)
db2.execute("VACUUM")
db2.close()

SIZE_AFTER = os.path.getsize(DB)
log(f"清后DB: {SIZE_AFTER/(1024**3):.2f}GB")
log(f"释放: {(SIZE_BEFORE-SIZE_AFTER)/(1024**3):.2f}GB")
log("===")
