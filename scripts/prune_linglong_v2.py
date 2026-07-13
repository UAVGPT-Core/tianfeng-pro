#!/usr/bin/env python3
"""灵龙 state.db — 重建FTS + VACUUM"""
import sqlite3, os, time

DB = os.path.expanduser("~/.hermes/state.db")
SIZE_BEFORE = os.path.getsize(DB)

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

log(f"清前DB: {SIZE_BEFORE/(1024**3):.2f}GB")

db = sqlite3.connect(DB)
db.execute("PRAGMA synchronous=OFF")

# 1. 重建FTS索引（先清空再插入）
log("重建FTS...")
db.executescript("""
    DELETE FROM messages_fts;
    INSERT INTO messages_fts(rowid, content) 
    SELECT id, COALESCE(content,'') FROM messages;
""")
log("FTS重建完成")

db.commit()

# 2. 重建trigram FTS
log("重建trigram FTS...")
db.executescript("""
    DELETE FROM messages_fts_trigram;
    INSERT INTO messages_fts_trigram(rowid, content)
    SELECT id, COALESCE(content,'') FROM messages;
""")
log("trigram FTS重建完成")

db.commit()
db.close()

# 3. VACUUM
log("VACUUM...")
db2 = sqlite3.connect(DB)
db2.execute("VACUUM")
db2.close()

SIZE_AFTER = os.path.getsize(DB)
log(f"清后DB: {SIZE_AFTER/(1024**3):.2f}GB")
log(f"释放: {(SIZE_BEFORE-SIZE_AFTER)/(1024**3):.2f}GB")
log("===")
