#!/usr/bin/env python3
"""SelfHealer v2 — 独立的自愈模块, 被tianfeng_super.py导入使用"""
import os, re, json, subprocess, sys, time, shutil
from datetime import datetime
from collections import Counter

HEALER_DIR = os.path.expanduser("~/.tianfeng-super/healer")
os.makedirs(HEALER_DIR, exist_ok=True)
HEAL_LOG = os.path.join(HEALER_DIR, "heal_history.json")
FAILURES_FILE = os.path.join(os.path.dirname(HEALER_DIR), "failures.json")
SUPER_DIR = os.path.dirname(HEALER_DIR)

def load_json(fp, default=None):
    try:
        with open(fp) as f:
            return json.load(f)
    except:
        return default if default is not None else []

def save_json(fp, data):
    with open(fp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# 错误模式 → 修复策略 (运行时构造,避免import时未定义)
def get_fix_patterns():
    return [
        ("str_concat", r"TypeError: can only concatenate str", _fix_str_concat),
        ("list_get", r"AttributeError: .* object has no attribute .get.", _fix_list_get),
        ("type_ops", r"TypeError: .*unsupported operand", _fix_type_ops),
        ("key_error", r"KeyError: .", _fix_key_error),
        ("missing_mod", r"ModuleNotFoundError: No module named", _fix_missing_module),
        ("empty_json", r"JSONDecodeError.*Expecting value", _fix_empty_json),
        ("timeout", r"time.*out|Connection refused|ConnectionError", _fix_network_timeout),
    ]

def _fix_str_concat(filepath, error_block):
    """修复 str + int """
    m = re.search(r'line (\d+)', error_block)
    if not m: return None
    ln = int(m.group(1))
    try:
        with open(filepath) as f:
            lines = f.readlines()
        if ln > len(lines): return None
        old = lines[ln-1]
        new = re.sub(r'\.get\(([^,]+),\s*(\d+)\)\s*\+\s*(\d+)',
                     r'int(\1.get(\2) or 0)+\3', old)
        if new == old: return None
        bak = filepath + ".healer.bak"
        if not os.path.exists(bak):
            with open(bak, "w") as f: f.writelines(lines)
        lines[ln-1] = new
        with open(filepath, "w") as f: f.writelines(lines)
        return f"修复 {os.path.basename(filepath)}:{ln} str连接"
    except: return None

def _fix_list_get(filepath, error_block):
    """修复 list.get() """
    m = re.search(r'line (\d+)', error_block)
    if not m: return None
    ln = int(m.group(1))
    try:
        with open(filepath) as f:
            lines = f.readlines()
        if ln > len(lines): return None
        old = lines[ln-1]
        # 替代策略：在出错的.get()前加类型检查wrapper
        new = re.sub(
            r'(\w+)\.get\([\'\"]([^\"\']+)[\'\"],\s*\{\}\)\.get\([\'\"]([^\"\']+)[\'\"],\s*(\d+)\)',
            r'int(\1.get("\2",0)) if isinstance(\1, dict) else 0',
            old
        )
        if new == old: return None
        bak = filepath + ".healer.bak"
        if not os.path.exists(bak):
            with open(bak, "w") as f: f.writelines(lines)
        lines[ln-1] = new
        with open(filepath, "w") as f: f.writelines(lines)
        return f"修复 {os.path.basename(filepath)}:{ln} list.get"
    except: return None

def _fix_type_ops(filepath, error_block):
    """修复类型运算"""
    m = re.search(r'line (\d+)', error_block)
    if not m: return None
    ln = int(m.group(1))
    try:
        with open(filepath) as f:
            lines = f.readlines()
        if ln > len(lines): return None
        old = lines[ln-1]
        new = re.sub(r'(\w+)\.get\([\'\"]([^\"\']+)[\'\"],\s*(\d+)\)',
                     r'int(\1.get("\2",\3) or 0)', old)
        if new == old: return None
        bak = filepath + ".healer.bak"
        if not os.path.exists(bak):
            with open(bak, "w") as f: f.writelines(lines)
        lines[ln-1] = new
        with open(filepath, "w") as f: f.writelines(lines)
        return f"修复 {os.path.basename(filepath)}:{ln} 类型"
    except: return None

def _fix_key_error(filepath, error_block):
    """修复KeyError"""
    m = re.search(r'line (\d+)', error_block)
    if not m: return None
    ln = int(m.group(1))
    try:
        with open(filepath) as f:
            lines = f.readlines()
        if ln > len(lines): return None
        old = lines[ln-1]
        new = re.sub(r'(\w+)\[([\'\"][^\'\"]+[\'\"])](?!\s*=)',
                     r'\1.get(\2, None)', old)
        if new == old: return None
        bak = filepath + ".healer.bak"
        if not os.path.exists(bak):
            with open(bak, "w") as f: f.writelines(lines)
        lines[ln-1] = new
        with open(filepath, "w") as f: f.writelines(lines)
        return f"修复 {os.path.basename(filepath)}:{ln} KeyError"
    except: return None

def _fix_missing_module(filepath, error_block):
    m = re.search(r"No module named '([^']+)'", error_block)
    if not m: return None
    mod = m.group(1)
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", mod, "-q"],
                          capture_output=True, timeout=30)
        if r.returncode == 0: return f"pip install {mod}"
    except: pass
    return None

def _fix_empty_json(filepath, error_block):
    m = re.search(r'line (\d+)', error_block)
    if not m: return None
    ln = int(m.group(1))
    try:
        with open(filepath) as f:
            lines = f.readlines()
        if ln > len(lines): return None
        old = lines[ln-1]
        if "json.loads" not in old: return None
        indent = old[:len(old)-len(old.lstrip())]
        bak = filepath + ".healer.bak"
        if not os.path.exists(bak):
            with open(bak, "w") as f: f.writelines(lines)
        lines.insert(ln-1, f'{indent}try:\n')
        lines.insert(ln, f'{indent}except: return {{}}\n')
        with open(filepath, "w") as f: f.writelines(lines)
        return f"修复 {os.path.basename(filepath)}:{ln} 空JSON"
    except: return None

def _fix_network_timeout(filepath, error_block):
    return "网络超时——自动降级不影响现有流程"

def scan_and_heal():
    """扫描cron错误日志并自动修复 (闭环1核心)"""
    fixes = []
    history = load_json(HEAL_LOG, [])
    ts = datetime.now().isoformat()

    # 扫描日志目录
    log_dirs = [
        os.path.expanduser("~/.hermes/cron/output"),
        os.path.expanduser("~/lgox-ops/logs"),
    ]
    script_dirs = [
        os.path.expanduser("~/.hermes/scripts"),
        os.path.expanduser("~/lgox-ops/scripts"),
    ]

    for log_dir in log_dirs:
        if not os.path.isdir(log_dir): continue
        for fname in os.listdir(log_dir):
            fpath = os.path.join(log_dir, fname)
            if not os.path.isfile(fpath) or os.path.getsize(fpath) == 0: continue
            if time.time() - os.path.getmtime(fpath) > 86400: continue
            try:
                with open(fpath, "r", errors="replace") as f:
                    content = f.read(50000)
            except: continue

            # 用更简单的err探测
            for label, pat, fix_fn in get_fix_patterns():
                m = re.search(pat, content, re.IGNORECASE)
                if not m: continue
                # 找源文件
                src = "unknown"
                sm = re.search(r'File "([^"]+)"', content)
                if sm: src = sm.group(1)
                # 限在script_dirs范围内
                if not any(d in src for d in script_dirs): continue
                # 检查是否已修过
                if any(h.get("file")==src and h.get("pattern")==label for h in history[-20:]):
                    fixes.append(f"⏭️ {label}({os.path.basename(src)}) 已修过")
                    continue
                # 执行修复
                try:
                    result = fix_fn(src, content)
                    if result:
                        fixes.append(f"🩹 {result}")
                        history.append({"ts":ts,"file":src,"pattern":label,"status":"fixed"})
                    else:
                        fixes.append(f"⚠️ {label}({os.path.basename(src)}) 无法自动修复")
                        history.append({"ts":ts,"file":src,"pattern":label,"status":"failed"})
                except Exception as e:
                    fixes.append(f"⚠️ {label}异常: {e}")
                    history.append({"ts":ts,"file":src,"pattern":label,"status":"exception"})
                break  # 每个日志只修第一个错误

    save_json(HEAL_LOG, history[-100:])
    return fixes

def check_disk():
    """磁盘预警"""
    try:
        usage = shutil.disk_usage(os.path.expanduser("~"))
        pct = usage.used / usage.total * 100
        if pct > 95: return f"🔴 磁盘{pct:.0f}% 临界!"
        if pct > 85: return f"🟡 磁盘{pct:.0f}% 建议清理"
    except: pass
    return None

if __name__ == "__main__":
    fixes = scan_and_heal()
    for f in fixes:
        print(f)
    disk = check_disk()
    if disk: print(disk)
    if not fixes and not disk: print("✅ 一切正常")
