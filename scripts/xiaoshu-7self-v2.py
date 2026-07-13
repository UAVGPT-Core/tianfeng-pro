#!/usr/bin/env python3
"""小枢 自协调+自反思 注入 v2 — 精准定位"""
path = "/Users/a1/stockagent-backend/main.py"
with open(path) as f:
    code = f.read()

# Find stream function boundary
stream_idx = code.find("async def xiaoshu_chat_stream")
if stream_idx < 0:
    print("STREAM FUNCTION NOT FOUND")
    exit(1)

chat_section = code[:stream_idx]

# Find the LAST return statement in chat handler (our target)
# Search backwards from stream_idx
last_return = chat_section.rfind("    return result\n")
if last_return < 0:
    last_return = chat_section.rfind("    return result")
if last_return < 0:
    print("RETURN NOT FOUND")
    exit(1)

# New block to insert before return
new_block = '''    # --- 自协调: 联邦桥消息(金融分析→通知天枢) ---
    if result and isinstance(result, dict):
        _xs_reply2 = result.get("response", "")
        if len(message) > 10 and len(_xs_reply2) > 80:
            import threading as _xs_th
            def _xs_bridge():
                try:
                    import json as _xs_jb, urllib.request as _xs_urb
                    _xs_bd = _xs_jb.dumps({
                        "from_node": "小枢",
                        "node_id": 9,
                        "type": "xiaoshu_analysis",
                        "ts": __import__("time").time(),
                        "u": message[:80],
                        "a": _xs_reply2[:120]
                    }).encode()
                    _xs_urb.urlopen(_xs_urb.Request(
                        "http://100.100.89.2:8765/api/message",
                        data=_xs_bd,
                        headers={"Content-Type": "application/json"}), timeout=1.5)
                except:
                    pass
            _xs_th.Thread(target=_xs_bridge, daemon=True).start()

    # --- 自反思: 对话日志+质量审计 ---
    if result and isinstance(result, dict):
        import threading as _xs_th2, os as _xs_os2, json as _xs_js2
        def _xs_reflect():
            try:
                _xs_d = _xs_os2.path.expanduser("~/lgox-ops/data")
                _xs_os2.makedirs(_xs_d, exist_ok=True)
                _xs_ts = __import__("datetime").datetime.now()
                # 对话日志
                _xs_log = _xs_os2.path.join(_xs_d, "chat_logs_xiaoshu", "chat_" + _xs_ts.strftime("%Y%m%d") + ".log")
                _xs_os2.makedirs(_xs_os2.path.dirname(_xs_log), exist_ok=True)
                _xs_entry = _xs_js2.dumps({"u": message[:200], "a": _xs_reply2[:300], "t": _xs_ts.isoformat()}, ensure_ascii=False)
                open(_xs_log, "a", encoding="utf-8").write(_xs_entry + "\\n")
                # 质量审计
                _xs_audit = _xs_os2.path.join(_xs_d, "xiaoshu-quality.json")
                _xs_audit_data = {}
                try:
                    if _xs_os2.path.exists(_xs_audit):
                        _xs_audit_data = _xs_js2.load(open(_xs_audit))
                except:
                    pass
                _xs_audit_data["last_chat"] = _xs_ts.isoformat()
                _xs_audit_data["total_chats"] = _xs_audit_data.get("total_chats", 0) + 1
                # 质量检测
                _xs_issues = []
                if len(_xs_reply2) < 20:
                    _xs_issues.append("回复过短")
                if len(_xs_reply2) > 2000:
                    _xs_issues.append("回复过长")
                import re as _xs_re3
                if _xs_re3.search(r"PE[=＝]\\s*\\d+", _xs_reply2) or _xs_re3.search(r"ROE[=＝]\\s*\\d+", _xs_reply2):
                    _xs_issues.append("含编造PE/ROE")
                if _xs_issues:
                    _xs_audit_data.setdefault("issues", []).append({
                        "ts": _xs_ts.isoformat(), "issues": _xs_issues, "msg": message[:60]
                    })
                _xs_js2.dump(_xs_audit_data, open(_xs_audit, "w"), ensure_ascii=False, indent=2)
            except:
                pass
        _xs_th2.Thread(target=_xs_reflect, daemon=True).start()

    return result'''

code = code[:last_return] + new_block + code[last_return + len("    return result"):]

with open(path, "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 小枢 自协调+自反思 注入成功 → 七自7/7满格")
except py_compile.PyCompileError as e:
    print("SYNTAX ERROR:", e)
