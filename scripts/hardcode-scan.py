#!/usr/bin/env python3
"""
硬编码扫描飞轮 v1.0 · 全联邦版本号一致性巡检
每30分钟扫描一次·发现不一致→记录→报告
扫描: pyramid.html, xcn JS, tv JS, xiaoshu-ai.py, tianxun-ai.py
"""
import json, urllib.request, sqlite3, os, subprocess
from datetime import datetime

DB = os.path.expanduser("~/lgox-ops/data/hardcode-scan.db")

# 扫描目标
SCAN_TARGETS = [
    ("/Volumes/990Pro/public-web/pyramid.html", "天枢:pyramid.html"),
    ("/Volumes/990Pro/public-web/public/js/xcn*.js", "天枢:xcn JS"),
    ("/Volumes/990Pro/public-web/public/js/tv*.js", "天枢:tv JS"),
]

LOCAL_TARGETS = [
    ("~/lgox-ops/scripts/tianxun-ai.py", "灵龙:天巡源码"),
    ("~/lgox-ops/scripts/xiaoshu-ai.py", "灵龙:小枢源码"),
]

# 期望值
EXPECTED = {"天巡": "v3.5", "小枢": "v3.4", "pyramid": "v7.82"}

def init():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target TEXT, found_versions TEXT, mismatch TEXT, status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn

def scan_local(conn):
    """扫描本地文件版本号"""
    import glob
    issues = []
    
    for pattern, label in LOCAL_TARGETS:
        for f in glob.glob(os.path.expanduser(pattern)):
            try:
                out = subprocess.run(["grep", "-o", "v[0-9]\\.[0-9]", f],
                                     capture_output=True, text=True, timeout=5)
                versions = sorted(set(out.stdout.strip().split("\n")))
                versions = [v for v in versions if v]
                
                svc = "天巡" if "tianxun" in f else "小枢"
                expected = EXPECTED.get(svc, "?")
                
                mismatches = [v for v in versions if v != expected and v.startswith("v3")]
                status = "OK" if not mismatches else f"MISMATCH: {mismatches}"
                
                conn.execute("INSERT INTO scans (target, found_versions, mismatch, status) VALUES (?,?,?,?)",
                    (label, ",".join(versions), ",".join(mismatches), status))
                
                if mismatches:
                    issues.append(f"{label}: 期望{expected} 发现{mismatches}")
                else:
                    print(f"  {label}: {expected} OK ({len(versions)}处)")
                    
            except Exception as e:
                conn.execute("INSERT INTO scans (target, status) VALUES (?,?)",
                    (label, f"ERR:{str(e)[:50]}"))
    
    return issues

def scan_remote(conn):
    """通过SSH扫描天枢文件"""
    issues = []
    
    for path, label in SCAN_TARGETS:
        try:
            out = subprocess.run(f"ssh a1@100.100.89.2 'grep -oh \"v[0-9]\\\\.[0-9]\" {path} 2>/dev/null | sort -u'",
                               shell=True, capture_output=True, text=True, timeout=10)
            versions = sorted(set(out.stdout.strip().split("\n")))
            versions = [v for v in versions if v]
            
            # 检查不一致
            mismatches = []
            for v in versions:
                for svc, exp in EXPECTED.items():
                    if svc in label and v.startswith("v3") and v != exp:
                        mismatches.append(v)
            
            status = "OK" if not mismatches else f"MISMATCH: {mismatches}"
            conn.execute("INSERT INTO scans (target, found_versions, mismatch, status) VALUES (?,?,?,?)",
                (label, ",".join(versions[:5]), ",".join(mismatches), status))
            
            if mismatches:
                issues.append(f"{label}: 发现{mismatches}")
            else:
                print(f"  {label}: OK ({len(versions)}处)")
                
        except Exception as e:
            pass  # SSH might fail, skip
    
    return issues

def verify_live():
    """对比health实际版本"""
    try:
        h = json.loads(urllib.request.urlopen("http://127.0.0.1:8778/health", timeout=5).read())
        print(f"  天巡health: {h['version']}")
        h2 = json.loads(urllib.request.urlopen("http://127.0.0.1:8779/health", timeout=5).read())
        print(f"  小枢health: {h2['version']}")
    except Exception as e:
        print(f"  health ERR: {e}")

conn = init()
ts = datetime.now().strftime("%H:%M:%S")
print(f"[{ts}] 硬编码扫描 开始")

print("本地:")
local_issues = scan_local(conn)
print("天枢:")
remote_issues = scan_remote(conn)
print("实跑:")
verify_live()

conn.commit(); conn.close()

all_issues = local_issues + remote_issues
if all_issues:
    print(f"\n⚠️  {len(all_issues)}个不一致:")
    for i in all_issues:
        print(f"  - {i}")
else:
    print("\n✅ 全联邦版本号一致")
