#!/usr/bin/env python3
"""天锋PRO 双仓自动同步飞轮 v2.0·GitHub+Gitee"""
import subprocess, os, time, sys
from pathlib import Path

R = Path.home() / "lgox-ops"
K = Path.home() / ".ssh/id_ed25519"
REMOTES = [
    {"name": "GitHub", "url": "git@github.com:UAVGPT-Core/tianfeng-pro.git", "type": "ssh"},
    {"name": "Gitee",  "url": "git@gitee.com:uavgpt/tianfeng-pro.git", "type": "ssh"},
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
            env["GIT_SSH_COMMAND"] = f"ssh -i {K} -o IdentitiesOnly=yes -o ConnectTimeout=10"
            ok, out, err = run(["git", "push", remote["url"], "main"], timeout=60, env=env)
            if not ok:
                # Remote may be ahead — pull first then retry
                run(["git", "pull", "--rebase", remote["url"], "main"], timeout=30, env=env)
                ok, out, err = run(["git", "push", remote["url"], "main"], timeout=60, env=env)
            results.append(f"{remote['name']}: {'✅' if ok else '❌ '+err[:50]}")
        except Exception as e:
            results.append(f"{remote['name']}: {str(e)[:50]}")
    
    return " | ".join(results)

if __name__ == "__main__":
    r = auto_sync()
    print(f"🔄 {r}")
