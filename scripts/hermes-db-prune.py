#!/usr/bin/env python3
"""
灵龙 Mac-mini state.db cron会话清理脚本
安全: 只删cron源会话+关联消息, 保留所有cli真人对话
用法: python3 hermes-db-prune.py <保留天数>
"""
import sqlite3
import os
import sys
import time
from datetime import datetime, timezone

DB_PATH = os.path.expanduser("~/.hermes/state.db")
LOG_PATH = os.path.expanduser("~/.hermes/logs/db-prune.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

def main():
    keep_days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    cutoff = time.time() - keep_days * 86400
    
    log(f"=== 灵龙 state.db 瘦身开始, 保留 {keep_days} 天 ===")
    
    # Check DB exists
    if not os.path.exists(DB_PATH):
        log(f"ERROR: {DB_PATH} 不存在")
        sys.exit(1)
    
    size_before = os.path.getsize(DB_PATH)
    log(f"清理前 size: {size_before / (1024**3):.2f}GB")
    
    db = sqlite3.connect(DB_PATH)
    
    # Count cron sessions
    total_cron = db.execute("SELECT COUNT(*) FROM sessions WHERE source='cron'").fetchone()[0]
    log(f"总 cron 会话数: {total_cron}")
    
    # Find cron sessions to delete
    # Use a subquery to get IDs first (more efficient)
    log(f"查找 {datetime.fromtimestamp(cutoff).strftime('%Y-%m-%d')} 之前的旧会话...")
    
    old_ids = db.execute(
        "SELECT id FROM sessions WHERE source='cron' AND started_at < ?",
        (cutoff,)
    ).fetchall()
    
    old_count = len(old_ids)
    log(f"待删除旧 cron 会话: {old_count}")
    
    if old_count == 0:
        log("没有旧会话需要清理")
        db.close()
        return
    
    # Delete in batches to avoid locking issues
    BATCH = 5000
    deleted_sessions = 0
    deleted_messages = 0
    
    for i in range(0, old_count, BATCH):
        batch = old_ids[i:i+BATCH]
        batch_ids = tuple(row[0] for row in batch)
        placeholders = ','.join('?' * len(batch_ids))
        
        # Delete messages first (FK), then sessions
        cur = db.execute(f"DELETE FROM messages WHERE session_id IN ({placeholders})", batch_ids)
        deleted_messages += cur.rowcount
        
        cur = db.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", batch_ids)
        deleted_sessions += cur.rowcount
        
        if (i // BATCH) % 5 == 0:
            log(f"  进度: {min(i + BATCH, old_count)}/{old_count}")
    
    db.commit()
    log(f"已删除: {deleted_sessions} sessions + {deleted_messages} messages")
    
    # Count remaining
    remaining_cron = db.execute("SELECT COUNT(*) FROM sessions WHERE source='cron'").fetchone()[0]
    remaining_cli = db.execute("SELECT COUNT(*) FROM sessions WHERE source='cli'").fetchone()[0]
    log(f"剩余: {remaining_cron} cron + {remaining_cli} cli")
    
    db.close()
    
    # VACUUM to reclaim space
    log("执行 VACUUM 回收磁盘空间 (会暂时占用额外空间)...")
    os.system(f"sqlite3 '{DB_PATH}' 'VACUUM;'")
    
    size_after = os.path.getsize(DB_PATH)
    freed_gb = (size_before - size_after) / (1024**3)
    log(f"清理后 size: {size_after / (1024**3):.2f}GB, 释放 {freed_gb:.2f}GB")
    log("=== 清理完成 ===")

if __name__ == "__main__":
    main()
