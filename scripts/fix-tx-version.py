#!/usr/bin/env python3
"""Fix 天巡 VERSION not updating in gene callback"""
path = "/Volumes/990Pro/public-web/public/js/tianxun-v14-living.js"
with open(path) as f:
    code = f.read()

# Old: updates only span, no VERSION update
old = "_el2.textContent='v'+new Date().toISOString().slice(2,10).replace(/-/g,'')+'.'+_gw+'w'"

# New: updates BOTH span AND VERSION, with -哨兵 suffix
new = "_el2.textContent='v'+new Date().toISOString().slice(2,10).replace(/-/g,'')+'.'+_gw+'w-哨兵';VERSION='v'+new Date().toISOString().slice(2,10).replace(/-/g,'')+'.'+_gw+'w-哨兵'"

if old in code:
    code = code.replace(old, new)
    with open(path, "w") as f:
        f.write(code)
    print("✅ 天巡 VERSION同步更新已修复")
    print(f"   旧: {old}")
    print(f"   新: {new}")
else:
    print("❌ 未找到目标字符串")
    # show what's there
    for i, line in enumerate(code.split('\n')):
        if '_el2.textContent' in line and '_gw' in line:
            print(f"   Line {i+1}: {line[:150]}")
            break
