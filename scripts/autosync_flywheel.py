#!/usr/bin/env python3
"""天锋PRO 双仓自动同步飞轮 v2.0·GitHub+Gitee"""
import subprocess, os, time, sys
from pathlib import Path

R = Path.home() / "lgox-ops"
K = Path.home() / ".ssh/id_ed25519"
REMOTES = [
    {"name": "GitHub", "url": "git@github.com:UAVGPT-Core/tianfeng-pro.git", "remote": "origin", "type": "ssh"},
    {"name": "Gitee",  "url": "git@gitee.com:uavgpt/tianfeng-pro.git", "remote": "gitee", "type": "ssh"},
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
            env["GIT_SSH_COMMAND"] = f"ssh -i {K} -o IdentitiesOnly=yes -o ConnectTimeout=10 -o ServerAliveInterval=30"
            ok, out, err = run(["git", "push", remote["remote"], "main"], timeout=120, env=env)
            if not ok:
                # Remote diverged — fetch, merge (NOT rebase) to avoid divergent history
                run(["git", "fetch", remote["remote"], "main"], timeout=30, env=env)
                # Merge remote into local (accept remote's version on conflicts)
                ok_merge, _, merge_err = run(
                    ["git", "merge", f"FETCH_HEAD", "--no-edit", "-m",
                     f"auto: merge {remote['name']} {time.strftime('%m%d-%H%M')}"],
                    timeout=30, env=env
                )
                if not ok_merge:
                    # Abort merge if it failed
                    run(["git", "merge", "--abort"], timeout=10)
                    run(["git", "reset", "--hard", "HEAD~1"], timeout=10)
                    results.append(f"{remote['name']}: ❌ merge-conflict-needs-manual")
                    continue
                # Retry push after merge
                ok, out, err = run(["git", "push", remote["remote"], "main"], timeout=120, env=env)
            results.append(f"{remote['name']}: {'✅' if ok else '❌ '+err[:60]}")
        except Exception as e:
            results.append(f"{remote['name']}: {str(e)[:60]}")

    return " | ".join(results)

if __name__ == "__main__":
    r = auto_sync()
    print(f"🔄 {r}")
