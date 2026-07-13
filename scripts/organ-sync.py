#!/usr/bin/env python3
"""
LGOX联邦一体同步引擎 v1.0 — 双体一心
灵龙⇌天枢 双向全量同步：记忆·脚本·技能·基因
设计理念: 联邦=一个人, 节点=器官. 左手动了右手同步知道.
"""
import json, os, shutil, subprocess, time, hashlib
from datetime import datetime

TIANSHU = "a1@100.100.89.2"
REMOTE_HOME = "/Users/a1"

# 同步资产清单 — 双向
SYNC_ASSETS = [
    # (本地路径, 远端路径, 方向: "push"=灵龙→天枢, "pull"=天枢→灵龙, "bi"=双向)
    ("~/.hermes/l1-memory.json", f"{REMOTE_HOME}/.hermes/l1-memory.json", "push"),
    ("~/lgox-ops/data/memory-index.db", f"{REMOTE_HOME}/lgox-ops/data/memory-index.db", "push"),
    ("~/.hermes/skills/", f"{REMOTE_HOME}/.hermes/skills/", "bi"),
    ("~/lgox-ops/scripts/", f"{REMOTE_HOME}/lgox-ops/scripts/", "bi"),
    ("~/.hermes/scripts/", f"{REMOTE_HOME}/.hermes/scripts/", "push"),  # 灵龙新脚本推天枢
    ("~/lgox-ops/data/comm-redundancy-status.json", f"{REMOTE_HOME}/lgox-ops/data/comm-redundancy-status.json", "bi"),
]

LOG_FILE = os.path.expanduser("~/lgox-ops/logs/organ-sync.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def run_ssh(cmd, timeout=15):
    """在天枢上执行命令"""
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no", 
             TIANSHU, cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def file_hash(path):
    """文件MD5"""
    try:
        p = os.path.expanduser(path)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        return "DIR:" + str(sum(1 for _ in os.walk(p)) if os.path.isdir(p) else 0)
    except:
        return "ERROR"

def sync_file(local_path, remote_path, direction):
    """同步单个文件/目录"""
    local = os.path.expanduser(local_path)
    remote_info = f"{TIANSHU}:{remote_path}"
    
    if direction == "push":
        # 灵龙 → 天枢
        if not os.path.exists(local):
            return "skip", "local_missing"
        
        # 检查远端hash
        ok, rhash, _ = run_ssh(f"md5 -q {remote_path} 2>/dev/null || echo 'MISSING'")
        if not ok:
            return "fail", "ssh_error"
        
        lhash = file_hash(local_path)
        if lhash == rhash:
            return "identical", lhash[:12]
        
        # 执行同步 — 目录从灵龙本地rsync推送（避免天枢→灵龙SSH不可达）
        if os.path.isdir(local):
            try:
                subprocess.run(
                    ["rsync", "-az", "--delete", "--timeout=60",
                     f"{local}/", f"{TIANSHU}:{remote_path}/"],
                    timeout=90
                )
                return "synced", lhash[:12]
            except subprocess.TimeoutExpired:
                return "timeout", "rsync_push_90s"
        else:
            subprocess.run(["scp", "-q", local, f"{TIANSHU}:{remote_path}"], timeout=15)
            return "synced", lhash[:12]
    
    elif direction == "pull":
        # 天枢 → 灵龙
        ok, rhash, _ = run_ssh(f"md5 -q {remote_path} 2>/dev/null || echo 'MISSING'")
        if not ok or rhash == "MISSING":
            return "skip", "remote_missing"
        
        if os.path.exists(local):
            lhash = file_hash(local_path)
            if lhash == rhash:
                return "identical", rhash[:12]
        
        os.makedirs(os.path.dirname(local), exist_ok=True)
        # 目录优先rsync，文件用scp
        if os.path.isdir(local) or local_path.endswith("/"):
            try:
                subprocess.run(
                    ["rsync", "-az", "--delete", "--timeout=60",
                     f"{TIANSHU}:{remote_path}/", f"{local}/"],
                    timeout=90
                )
            except subprocess.TimeoutExpired:
                return "timeout", "rsync_pull_90s"
        else:
            subprocess.run(["scp", "-q", f"{TIANSHU}:{remote_path}", local], timeout=30)
        return "synced", rhash[:12]
    
    elif direction == "bi":
        # 双向: 取最新的
        local_ts = os.path.getmtime(local) if os.path.exists(local) else 0
        ok, remote_ts_str, _ = run_ssh(f"stat -f '%m' {remote_path} 2>/dev/null || echo '0'")
        remote_ts = int(remote_ts_str) if remote_ts_str.isdigit() else 0
        
        if local_ts > remote_ts:
            return sync_file(local_path, remote_path, "push")
        elif remote_ts > local_ts:
            return sync_file(local_path, remote_path, "pull")
        return "identical", "same_time"

def memory_merge():
    """特殊处理: L1记忆双向合并（不覆盖，取并集）"""
    local = os.path.expanduser("~/.hermes/l1-memory.json")
    if not os.path.exists(local):
        return "skip", "no_local"
    
    try:
        with open(local) as f:
            local_mem = json.load(f)
    except:
        return "fail", "local_parse_error"
    
    # 拉天枢记忆
    ok, remote_raw, _ = run_ssh(f"cat {REMOTE_HOME}/.hermes/l1-memory.json 2>/dev/null")
    if ok and remote_raw:
        try:
            remote_mem = json.loads(remote_raw)
        except:
            remote_mem = []
    else:
        remote_mem = []
    
    local_ids = {m.get("id") for m in local_mem if isinstance(m, dict)}
    remote_ids = {m.get("id") for m in remote_mem if isinstance(m, dict)}
    
    new_to_local = [m for m in remote_mem if isinstance(m, dict) and m.get("id") not in local_ids]
    new_to_remote = [m for m in local_mem if isinstance(m, dict) and m.get("id") not in remote_ids]
    
    if new_to_local:
        local_mem.extend(new_to_local)
        with open(local, "w") as f:
            json.dump(local_mem, f, ensure_ascii=False, indent=2)
    
    if new_to_remote:
        tmp = "/tmp/lgox-memory-merge.json"
        with open(tmp, "w") as f:
            json.dump(remote_mem + new_to_remote, f, ensure_ascii=False, indent=2)
        subprocess.run(["scp", "-q", tmp, f"{TIANSHU}:{tmp}"], timeout=10)
        run_ssh(f"mv {tmp} {REMOTE_HOME}/.hermes/l1-memory.json")
        os.remove(tmp)
    
    return "merged", f"+{len(new_to_local)}local +{len(new_to_remote)}remote"

def main():
    log("🫀 联邦一体同步引擎 v1.0 启动")
    
    results = {}
    total_synced = 0
    
    # 1. 文件/目录同步
    for local_p, remote_p, direction in SYNC_ASSETS:
        status, info = sync_file(local_p, remote_p, direction)
        results[local_p] = (status, info)
        if status == "synced":
            total_synced += 1
    
    # 2. 记忆合并
    m_status, m_info = memory_merge()
    results["memory-merge"] = (m_status, m_info)
    if m_status == "merged":
        total_synced += 1
    
    # 3. 汇报
    for path, (status, info) in results.items():
        if status in ("synced", "merged"):
            log(f"  ✅ {path}: {status}({info})")
        elif status == "identical":
            pass  # 静默
        else:
            log(f"  ⚠️ {path}: {status}({info})")
    
    log(f"🫀 同步完成: {total_synced}项变更, {len([s for s,_ in results.values() if s == 'identical'])}项一致")
    
    # 4. 写入状态
    status_file = os.path.expanduser("~/lgox-ops/data/organ-sync-status.json")
    with open(status_file, "w") as f:
        json.dump({
            "last_sync": datetime.now().isoformat(),
            "total_synced": total_synced,
            "details": {k: list(v) for k, v in results.items()}
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
