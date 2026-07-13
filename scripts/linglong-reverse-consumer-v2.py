#!/usr/bin/env python3
"""灵龙反向消化器 v2.0 · 审计DB + 纳基因 · FCPF v5.1"""
import json, os, time, sqlite3, urllib.request, hashlib
from datetime import datetime

MSG_DB = os.path.expanduser("~/.hermes/fed_messages.db")
AUDIT_DB = os.path.expanduser("~/lgox-ops/data/comm-audit.db")
LGE = "http://100.116.0.29:8200/genes/write"
THIS = "灵龙"

os.makedirs(os.path.dirname(AUDIT_DB), exist_ok=True)

def init_audit():
    c = sqlite3.connect(AUDIT_DB)
    c.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,msg_id TEXT,direction TEXT,sender TEXT,receiver TEXT,content TEXT,ts TEXT,digested_at TEXT,gene_id TEXT)")
    c.commit(); c.close()

def audit_log(direction, sender, receiver, content, msg_id=None, gene_id=None):
    try:
        c = sqlite3.connect(AUDIT_DB)
        c.execute("INSERT INTO messages(msg_id,direction,sender,receiver,content,ts,digested_at,gene_id) VALUES(?,?,?,?,?,?,?,?)",
            (msg_id, direction, sender, receiver, content[:500],
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gene_id))
        c.commit(); c.close()
    except: pass

def get_unread():
    try:
        c = sqlite3.connect(MSG_DB)
        rows = c.execute("SELECT id,from_node,content,ts FROM messages WHERE node=? AND read=0 AND from_node=? ORDER BY id ASC LIMIT 10", (THIS, "天枢")).fetchall()
        msgs = [{"id": r[0], "from": r[1], "content": r[2], "ts": r[3]} for r in rows]
        c.close()
        return msgs
    except: return []

def mark_read(mid):
    try:
        c = sqlite3.connect(MSG_DB)
        c.execute("UPDATE messages SET read=1 WHERE id=?", (mid,))
        c.commit(); c.close()
    except: pass

def write_gene(content):
    try:
        d = json.dumps({"content": f"[灵龙消化天枢] {content[:400]}", "memory_type": "episodic",
            "source": "linglong-reverse", "tags": '["domain:meta","fcpg","audit"]'}).encode()
        r = urllib.request.urlopen(urllib.request.Request(LGE, data=d,
            headers={"Content-Type": "application/json"}, method="POST"), timeout=5)
        return json.loads(r.read()).get("gene_id", "")
    except: return ""

def main():
    init_audit()
    print(f"🐉 灵龙消化器 v2.0 | audit+gene | 30s", flush=True)
    while True:
        try:
            msgs = get_unread()
            if msgs:
                now = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{now}] 📬 天枢回执 x{len(msgs)}", flush=True)
                for m in msgs:
                    c = m["content"] or ""
                    mid = hashlib.sha256(c.encode()).hexdigest()[:12]
                    audit_log("RECV", "天枢", THIS, c, msg_id=mid)
                    print(f"  ← 天枢: {c[:100]}...", flush=True)
                    gid = ""
                    if c and len(c) > 20:
                        gid = write_gene(c[:400])
                        print(f"    → 🧬 {gid[:20] if gid else 'done'}", flush=True)
                    audit_log("DIGEST", THIS, THIS, f"gene:{gid[:20]}" if gid else "digested", gene_id=gid)
                    mark_read(m["id"])
            time.sleep(30)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"  [err] {e}", flush=True)
            time.sleep(30)

if __name__ == "__main__":
    main()
