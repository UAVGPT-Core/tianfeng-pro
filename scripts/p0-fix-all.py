#!/usr/bin/env python3
"""P0修复脚本 - 在目标节点本地执行"""
import os, sys

def fix_tianshu_gate():
    """天枢 gene-quality-gate.py 缺失"""
    path = os.path.expanduser("~/lgox-ops/scripts/gene-quality-gate.py")
    if os.path.exists(path):
        print(f"  天枢 gate: 已存在 ({os.path.getsize(path)} bytes)")
        return True
    print("  天枢 gate: 文件缺失!")
    return False

def fix_dishu_line():
    """地枢 dgx2-gene-line.py 语法错误"""
    path = os.path.expanduser("~/lgox-ops/scripts/dgx2-gene-line.py")
    if not os.path.exists(path):
        print(f"  地枢 line: 文件不存在 {path}")
        return False
    with open(path) as f:
        content = f.read()
    old = 'def _gen_single(topic, idx):(topics):'
    if old in content:
        content = content.replace(old, 'def _gen_single(topic, idx):')
        with open(path, 'w') as f:
            f.write(content)
        print("  地枢 line: 语法已修复")
        return True
    else:
        # 检查行60-65
        lines = content.split('\n')
        for i in range(58, min(66, len(lines))):
            if '_gen_single' in lines[i]:
                print(f"  地枢 line line {i+1}: {lines[i]}")
        return False

def fix_tiangong_guardian():
    """天工 ngc-gene-guardian.py 语法错误"""
    path = os.path.expanduser("~/lgox-ops/scripts/ngc-gene-guardian.py")
    if not os.path.exists(path):
        print(f"  天工 guardian: 文件不存在 {path}")
        return False
    with open(path) as f:
        content = f.read()
    # 查找未闭合括号: return _ollama_score_raw(# 改用VOD Pro(免费·强大)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '_ollama_score_raw' in line and '(' in line and ')' not in line.split('#')[0]:
            # 修复: 补上闭合括号
            old_line = line
            # 找到 # 注释符号，在其前面补 )
            comment_idx = line.find('#')
            if comment_idx > 0:
                new_line = line[:comment_idx].rstrip() + ') ' + line[comment_idx:]
            else:
                new_line = line.rstrip() + ')'
            lines[i] = new_line
            with open(path, 'w') as f:
                f.write('\n'.join(lines))
            print(f"  天工 guardian line {i+1}: 括号已闭合")
            print(f"    OLD: {old_line[:80]}")
            print(f"    NEW: {new_line[:80]}")
            return True
    print("  天工 guardian: 未找到需要修复的行")
    return False

if __name__ == "__main__":
    node = sys.argv[1] if len(sys.argv) > 1 else "all"
    if node in ("tianshu", "all"):
        print("=== 天枢 ===")
        fix_tianshu_gate()
    if node in ("dishu", "all"):
        print("=== 地枢 ===")
        fix_dishu_line()
    if node in ("tiangong", "all"):
        print("=== 天工 ===")
        fix_tiangong_guardian()
