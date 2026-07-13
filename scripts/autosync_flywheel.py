#!/usr/bin/env python3
"""天锋PRO 双仓自动同步飞轮 v2.0·GitHub+Gitee"""
import subprocess, os, time, sys
from pathlib import Path

R = Path.home() / "lgox-ops"
K = Path.home() / ".ssh/id_ed25519"
REMOTES = [
    {"name": "GitHub", "url": "git@github.com:UAVGPT-Core/tianfeng-pro.git"},
    {"name": "Gitee",  "url": "https://uavgpt:PLACEHOLDER@gitee.com/uavgpt/tianfeng-pro.git"},
]

def run(cmd_list, cwd=R, timeout=30, env=None):
    try:
        r = subprocess.run(cmd_list, capture_output=True, text=True, cwd=str(cwd), timeout=timeout, env=env)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except: return False, "", "timeout"

def auto_sync():
    os.chdir(str(R))
    ok, s, _ = run(["git", "status", "-s"])
    if not s: return "clean"

    n = len(s.split("\n"))
    run(["git", "add", "-A"])
    msg = f"auto: sync {time.strftime('%m%d-%H%M')} {n}f"
    ok, _, err = run(["git", "commit", "-m", msg])
    if not ok and "nothing to commit" in err: return "skip"

    results = []
    for remote in REMOTES:
        try:
            env = os.environ.copy()
            if remote["name"] == "GitHub":
                env["GIT_SSH_COMMAND"] = f"ssh -i {K} -o IdentitiesOnly=yes -o ConnectTimeout=10"
                ok, out, err = run(["git", "push", "origin", "main"], timeout=60, env=env)
            else:
                # Gitee HTTPS push with token from env
                gt = os.environ.get("GITEE_TOKEN", "")
                if not gt:
                    results.append(f"Gitee: 缺token")
                    continue
                gitee_url = remote["url"].replace("PLACEHOLDER", gt)
                ok, out, err = run(["git", "push", gitee_url, "main"], timeout=60)
            
            results.append(f"{remote['name']}: {'✅' if ok else '❌ '+err[:50]}")
        except Exception as e:
            results.append(f"{remote['name']}: {str(e)[:50]}")
    
    return " | ".join(results)

if __name__ == "__main__":
    r = auto_sync()
    print(f"🔄 {r}")
