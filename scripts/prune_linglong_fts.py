#!/usr/bin/env python3
"""灵龙 state.db FTS清空"""
import sqlite3, os, time

DB = os.path.expanduser("~/.hermes/state.db")
SIZE_BEFORE = os.path.getsize(DB)

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

log(f"清前: {SIZE_BEFORE/(1024**3):.2f}GB")

db = sqlite3.connect(DB)
db.execute("PRAGMA synchronous=OFF")

# 先删trigram索引（DELETE FROM 太慢，用DROP重建）
log("重建FTS表结构（最快方式）...")
db.executescript("""
    DROP TABLE IF EXISTS messages_fts;
    DROP TABLE IF EXISTS messages_fts_data;
    DROP TABLE IF EXISTS messages_fts_idx;
    DROP TABLE IF EXISTS messages_fts_content;
    DROP TABLE IF EXISTS messages_fts_docsize;
    DROP TABLE IF EXISTS messages_fts_config;
    DROP TABLE IF EXISTS messages_fts_trigram;
    DROP TABLE IF EXISTS messages_fts_trigram_data;
    DROP TABLE IF EXISTS messages_fts_trigram_idx;
    DROP TABLE IF EXISTS messages_fts_trigram_content;
    DROP TABLE IF EXISTS messages_fts_trigram_docsize;
    DROP TABLE IF EXISTS messages_fts_trigram_config;
""")
log("旧FTS表已删")

# 重建空FTS表
db.executescript("""
    CREATE VIRTUAL TABLE messages_fts USING fts5(content, content_rowid="id", tokenize="trigram");
    CREATE VIRTUAL TABLE messages_fts_trigram USING fts5(content, tokenize='trigram');
    CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages BEGIN
        INSERT INTO messages_fts(rowid, content) VALUES (
            new.id,
            COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
        );
    END;
    CREATE TRIGGER messages_fts_delete AFTER DELETE ON messages BEGIN
        DELETE FROM messages_fts WHERE rowid = old.id;
    END;
    CREATE TRIGGER messages_fts_update AFTER UPDATE ON messages BEGIN
        DELETE FROM messages_fts WHERE rowid = old.id;
        INSERT INTO messages_fts(rowid, content) VALUES (
            new.id,
            COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
        );
    END;
    CREATE TRIGGER messages_fts_trigram_insert AFTER INSERT ON messages BEGIN
        INSERT INTO messages_fts_trigram(rowid, content) VALUES (
            new.id,
            COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
        );
    END;
    CREATE TRIGGER messages_fts_trigram_delete AFTER DELETE ON messages BEGIN
        DELETE FROM messages_fts_trigram WHERE rowid = old.id;
    END;
    CREATE TRIGGER messages_fts_trigram_update AFTER UPDATE ON messages BEGIN
        DELETE FROM messages_fts_trigram WHERE rowid = old.id;
        INSERT INTO messages_fts_trigram(rowid, content) VALUES (
            new.id,
            COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
        );
    END;
""")
log("FTS表已重建为空")
db.commit()

# VACUUM
log("VACUUM...")
db.execute("VACUUM")
db.commit()

SIZE_AFTER = os.path.getsize(DB)
log(f"清后: {SIZE_AFTER/(1024**3):.2f}GB")
log(f"释放: {(SIZE_BEFORE-SIZE_AFTER)/(1024**3):.2f}GB")
db.close()
log("===")
