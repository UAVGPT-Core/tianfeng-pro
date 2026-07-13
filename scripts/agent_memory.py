#!/usr/bin/env python3
"""
LGOX联邦 共享记忆引擎 v1.0
SQLite持久化 · 会话记忆 · 跨Agent共享
"""
import sqlite3, json, time, os, hashlib
from datetime import datetime

DB_PATH = os.path.expanduser("~/lgox-ops/data/agent-memory.db")

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=2000")
    return c

def init():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            last_active TEXT DEFAULT (datetime('now')),
            summary TEXT,
            turn_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            evidence TEXT,
            ts TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            topic TEXT NOT NULL,
            insight TEXT NOT NULL,
            source_session TEXT,
            ts TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_learn_agent ON learnings(agent);
        CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent);
    """)
    c.commit()
    c.close()

def new_session(agent: str) -> str:
    sid = hashlib.md5(f"{agent}{time.time()}".encode()).hexdigest()[:12]
    c = _conn()
    c.execute("INSERT INTO sessions(id,agent) VALUES(?,?)", (sid, agent))
    c.commit()
    c.close()
    return sid

def save_message(session_id: str, role: str, content: str, evidence: str = ""):
    c = _conn()
    c.execute("INSERT INTO messages(session_id,role,content,evidence) VALUES(?,?,?,?)",
              (session_id, role, content, evidence[:500]))
    c.execute("UPDATE sessions SET last_active=datetime('now'), turn_count=turn_count+1 WHERE id=?",
              (session_id,))
    c.commit()
    c.close()

def get_history(session_id: str, limit: int = 10) -> list:
    c = _conn()
    rows = c.execute(
        "SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (session_id, limit)).fetchall()
    c.close()
    return [{"role": r, "content": c} for r, c in reversed(rows)]

def get_recent_sessions(agent: str, limit: int = 5) -> list:
    c = _conn()
    rows = c.execute(
        "SELECT id,summary,turn_count,last_active FROM sessions WHERE agent=? ORDER BY last_active DESC LIMIT ?",
        (agent, limit)).fetchall()
    c.close()
    return [{"id": r[0], "summary": r[1], "turns": r[2], "last": r[3]} for r in rows]

def update_summary(session_id: str, summary: str):
    c = _conn()
    c.execute("UPDATE sessions SET summary=? WHERE id=?", (summary[:200], session_id))
    c.commit()
    c.close()

def save_learning(agent: str, topic: str, insight: str, session_id: str = ""):
    c = _conn()
    c.execute("INSERT INTO learnings(agent,topic,insight,source_session) VALUES(?,?,?,?)",
              (agent, topic, insight[:300], session_id))
    c.commit()
    c.close()

def get_learnings(agent: str, limit: int = 10) -> list:
    c = _conn()
    rows = c.execute(
        "SELECT topic,insight,ts FROM learnings WHERE agent=? ORDER BY id DESC LIMIT ?",
        (agent, limit)).fetchall()
    c.close()
    return [{"topic": r[0], "insight": r[1], "ts": r[2]} for r in rows]

def get_cross_agent_context(agent: str, query: str) -> str:
    """获取跨Agent上下文: 对方最近学到了什么"""
    other = "天巡" if "小枢" in agent else "小枢"
    learnings = get_learnings(other, 3)
    if not learnings:
        return ""
    ctx = f"\n【{other}最近学到】\n"
    for l in learnings:
        ctx += f"  [{l['ts'][:16]}] {l['topic']}: {l['insight'][:100]}\n"
    return ctx

# 初始化
init()
print(f"记忆引擎就绪: {DB_PATH}")
