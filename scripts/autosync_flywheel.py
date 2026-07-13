#!/usr/bin/env python3
"""
天锋PRO · 自动同步飞轮 v1.0
本地修改 → 自动commit → GitHub推送 → PyPI发布 → 全闭环
2026-07-13 · 零token·cron永动
"""
import subprocess, os, json, time, sys
from pathlib import Path

REPO_DIR = Path.home() / "lgox-ops"
GIT_SSH = "ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=10"

def run(cmd_list, cwd=REPO_DIR, timeout=30):
    try:
        r = subprocess.run(cmd_list, capture_output=True, text=True, 
                          cwd=str(cwd), timeout=timeout)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except:
        return False, "", "timeout"

def auto_sync():
    os.chdir(str(REPO_DIR))

    # 1. 检查未提交变更
    ok, status, _ = run(["git", "status", "-s"])
    if not status:
        return {"status": "clean", "msg": "无变更"}

    changes = len(status.split("\n"))
    
    # 2. 自动提交
    run(["git", "add", "-A"])
    commit_msg = "auto: 同步飞轮 {} {}文件".format(time.strftime("%m%d-%H%M"), changes)
    ok, out, err = run(["git", "commit", "-m", commit_msg])
    if not ok:
        return {"status": "skip", "msg": f"commit跳过: {err[:100]}"}

    # 3. GitHub推送
    import os as _os
    env = _os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -i {}/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=10".format(str(Path.home()))
    try:
        r = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, 
                          cwd=str(REPO_DIR), timeout=60, env=env)
        ok = r.returncode == 0
        out = r.stdout.strip()
        err = r.stderr.strip()
    except:
        ok, out, err = False, "", "timeout"
    if not ok:
        return {"status": "push_failed", "msg": err[:200]}

    pushed = True
    msg = f"✅ GitHub: {changes}个文件"

    # 4. PyPI发布(仅当setup.py变更时)
    ok2, diff, _ = run(["git", "diff", "HEAD~1", "--name-only"])
    if "setup.py" in diff:
        msg += " | PyPI: 跳过(非版本升级)"  # 保守策略·仅手动发布PyPI

    return {"status": "synced", "msg": msg, "changes": changes, "pushed_github": True}

def status():
    """当前同步状态"""
    os.chdir(str(REPO_DIR))
    ok, remote, _ = run(["git", "remote", "-v"])
    ok2, branch, _ = run(["git", "branch", "--show-current"])
    ok3, last, _ = run(["git", "log", "--oneline", "-1"])
    ok4, unstaged, _ = run(["git", "status", "-s"])
    unpushed = len(unstaged.split("\n")) if unstaged else 0

    print(f"""
╔══════════════════════════════════════╗
║  天锋PRO · 自动同步飞轮               ║
╠══════════════════════════════════════╣
║  远程: GitHub SSH                     ║
║  分支: {branch:30s} ║
║  最后: {last[:45]:45s} ║
║  待推: {unpushed:>4} 文件                   ║
╚══════════════════════════════════════╝""")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if cmd == "sync":
        result = auto_sync()
        print(f"🔄 {result['msg']}")
    elif cmd == "status":
        status()
    elif cmd == "force":
        result = auto_sync()
        print(result)
