#!/usr/bin/env python3
"""LGOX联邦灵龙六合探针回复器 — 扫描inbox根目录to-灵龙探针并回复"""
import os, time, re, subprocess
from datetime import datetime

INBOX = os.path.expanduser("~/lgox-ops/inbox")
NODE = "灵龙"
SCP_DEST = "a1@100.100.89.2:/Users/a1/lgox-ops/inbox/from-linglong/"

def reply_probe(fpath, content):
    """解析探针并写回执"""
    mid = ""
    for line in content.split("\n"):
        if line.startswith("MID:"):
            mid = line.replace("MID:", "").strip()
            break
    # 六合通格式: 六合通圆桌提案|ts|天枢探针{mid}
    if not mid:
        m = re.search(r"六合通圆桌提案(?:\(URGENT\))?\|\d{8}-\d{6}\|天枢探针(.+)$", content, re.MULTILINE)
        if m:
            mid = m.group(1)
    
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    reply_content = f"探针回执|{now}|灵龙已收·TO: {fpath}"
    if mid:
        reply_content = f"六合通巡检回执|{now}|天枢探针{mid}已确认·联邦通"
    
    reply_name = f"to-天枢-{now}.txt"
    reply_path = os.path.join(INBOX, reply_name)
    with open(reply_path, "w") as f:
        f.write(reply_content + "\n")
    
    # scp到天枢根inbox
    try:
        subprocess.run(["scp", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
                        reply_path, SCP_DEST], capture_output=True, timeout=10)
    except:
        pass
    return reply_name

def main():
    seen = set()
    while True:
        try:
            for fname in sorted(os.listdir(INBOX)):
                if not fname.startswith("to-灵龙-") or fname in seen:
                    continue
                fpath = os.path.join(INBOX, fname)
                if not os.path.isfile(fpath):
                    continue
                try:
                    with open(fpath) as f:
                        content = f.read()
                    if "liuhe_tong_probe" in content or "六合通" in content:
                        reply_name = reply_probe(fpath, content)
                        seen.add(fname)
                        print(f"[{datetime.now().isoformat()}] 已回复: {fname} -> {reply_name}")
                except:
                    pass
        except:
            pass
        time.sleep(10)

if __name__ == "__main__":
    main()
