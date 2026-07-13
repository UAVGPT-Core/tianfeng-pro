#!/usr/bin/env python3
"""仪表盘闭环: 小枢对话写入xiaoshu.db"""
path = "/Users/a1/stockagent-backend/main.py"
with open(path) as f:
    code = f.read()

# Target: in the _xs_reflect function, before the quality audit section
old = '''                _xs_audit_data["last_chat"] = _xs_ts.isoformat()'''

new = '''                _xs_audit_data["last_chat"] = _xs_ts.isoformat()
                # 仪表盘闭环: 对话写入xiaoshu.db
                try:
                    import sqlite3 as _xs_sql, uuid as _xs_uuid
                    _xs_db = _xs_os2.path.expanduser("~/.xiaoshu_nirvana/xiaoshu.db")
                    _xs_conn = _xs_sql.connect(_xs_db)
                    _xs_conn.execute(
                        "INSERT INTO conversations(id,session_id,role,content,agent_type,created) VALUES(?,?,?,?,?,?)",
                        (str(_xs_uuid.uuid4()), session_id or "xiaoshu_anon", "user", message[:500], "xiaoshu", _xs_ts.isoformat())
                    )
                    _xs_conn.execute(
                        "INSERT INTO conversations(id,session_id,role,content,agent_type,created) VALUES(?,?,?,?,?,?)",
                        (str(_xs_uuid.uuid4()), session_id or "xiaoshu_anon", "assistant", _xs_reply2[:500], "xiaoshu", _xs_ts.isoformat())
                    )
                    _xs_conn.commit()
                    _xs_conn.close()
                except:
                    pass'''

if old in code:
    code = code.replace(old, new)
    with open(path, "w") as f:
        f.write(code)
    import py_compile
    py_compile.compile(path, doraise=True)
    print("✅ 仪表盘闭环: 对话→xiaoshu.db 桥接完成")
else:
    print("MARKER NOT FOUND")
