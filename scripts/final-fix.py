#!/usr/bin/env python3
"""最终修复: bg7阈值+local fallback+孤儿块+缩进"""
path = "/Users/a1/ai-gateway/gateway_extensions.py"
with open(path) as f:
    code = f.read()

# Fix 1: orphan print + indent
code = code.replace(
    'print("[天巡全绿v3.0] ✅ L7宪法预检+L0多节探测+L2联邦桥+L4圆桌 已注入")\n\n    import os as _over',
    'import os as _over'
)

# Fix 2: bg7 threshold (just change the length check)
code = code.replace(
    'if len(u2)>5 and len(a2)>30:',
    'if len(u2)>3 and len(a2)>40:  # v1.0 全量对话→基因+本地fallback'
)

# Fix 3: add local fallback after gene write except
old_exc_line = '                                        except:pass'
new_exc_block = '''                                        except:
                                            try:
                                                _fb=_o7.path.join(_d,"gene-fallback-tianxun.log")
                                                _fe=_j7.dumps({"ts":_ts.isoformat(),"u":u2[:60]},ensure_ascii=False)
                                                open(_fb,"a",encoding="utf-8").write(_fe+"\\n")
                                            except:
                                                pass'''

if old_exc_line in code:
    code = code.replace(old_exc_line, new_exc_block)

with open(path, "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 全部修复完成·语法OK")
except py_compile.PyCompileError as e:
    print(f"❌ {e}")
