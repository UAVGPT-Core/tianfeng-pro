#!/usr/bin/env python3
"""Fix broken string literal"""
path = "/Users/a1/ai-gateway/gateway_extensions.py"
with open(path) as f:
    lines = f.readlines()

# Line 831 (0-indexed: 830) — fix the broken string
for i, line in enumerate(lines):
    if 'ensure_ascii=False)+"' in line and i+1 < len(lines) and lines[i+1].strip() == '")':
        # Fix: join with chr(10) instead of multi-line string
        lines[i] = line.rstrip() + 'chr(10))\n'
        lines[i+1] = ''  # remove broken continuation
        print(f"Fixed line {i+1}")
        break

with open(path, "w") as f:
    f.writelines(lines)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 语法OK")
except py_compile.PyCompileError as e:
    print(f"❌ {e}")
