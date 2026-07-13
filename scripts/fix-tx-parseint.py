#!/usr/bin/env python3
"""Fix 天巡 version: parseInt/10000 bug → parseInt alone (API already returns 万 units)"""
path = "/Volumes/990Pro/public-web/public/js/tianxun-v14-living.js"
with open(path) as f:
    code = f.read()

# BUG: _gw=parseInt(t)/10000 — API returns "77万+", parseInt=77, /10000=0.0077
# FIX: _gw=parseInt(t) — already in 万 units
old_bug = "var _gw=parseInt(t)/10000||77;"
new_fix = "var _gw=parseInt(t)||77;"

if old_bug in code:
    code = code.replace(old_bug, new_fix)
    print("✅ _gw=parseInt(t)/10000 → parseInt(t) FIXED")
else:
    print("BUG STRING NOT FOUND, checking variant...")
    for i, line in enumerate(code.split('\n')):
        if 'parseInt(t)' in line and '_gw' in line:
            print(f"  Line {i+1}: {line.strip()[:120]}")
            break

with open(path, "w") as f:
    f.write(code)
print("Done.")
