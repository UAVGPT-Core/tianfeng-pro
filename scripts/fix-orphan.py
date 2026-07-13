#!/usr/bin/env python3
"""Fix L4 patch: remove orphaned JSONResponse block"""
path = "/Users/a1/ai-gateway/gateway_extensions.py"
with open(path) as f:
    code = f.read()

# Remove the orphaned block
orphan = """            # 联邦知识检索({
                    "choices": [{"message": {"role": "assistant", "content": pre_block}}],
                    "lgox_meta": {"route": "constitution_block", "model": "none", "cached": False}
                })
            
            # 联邦知识检索
            async def fetch_knowledge():"""

replacement = """            # 联邦知识检索
            async def fetch_knowledge():"""

if orphan in code:
    code = code.replace(orphan, replacement)
    print("✅ 孤儿JSONResponse块已清除")
else:
    print("Orphan block not found, checking...")
    if "constitution_block" in code:
        # Find the orphan
        idx = code.find('"constitution_block"')
        print(f"  Found at offset {idx}: {code[idx:idx+60]}")

with open(path, "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 语法验证通过")
except py_compile.PyCompileError as e:
    print(f"❌ {e}")
