#!/usr/bin/env python3
"""
联邦自洁飞轮 v1.0 · 越飞越轻·越飞越聪明
2026-07-05 灵龙
"""
import os, shutil, time, subprocess, json, urllib.request

HOME = os.path.expanduser("~")
NODE = os.uname().nodename
REPORT = []

def clean_logs(path, max_mb=50):
    """截断超过max_mb的日志文件，保留最后10MB"""
    cleaned = 0
    freed = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(('.log', '.jsonl')):
                fp = os.path.join(root, f)
                try:
                    size_mb = os.path.getsize(fp) / (1024*1024)
                    if size_mb > max_mb:
                        # 保留最后10MB
                        with open(fp, 'rb') as fh:
                            fh.seek(-10*1024*1024, 2)  # 最后10MB
                            tail = fh.read()
                        with open(fp, 'wb') as fh:
                            fh.write(b"# TRUNCATED by self-clean v1.0\n")
                            fh.write(tail)
                        freed += size_mb - 10
                        cleaned += 1
                except:
                    pass
    if cleaned:
        REPORT.append(f"日志清理: {cleaned}个文件, 释放{freed:.0f}MB")

def clean_sessions(path, max_days=7):
    """删除超过max_days的session目录"""
    now = time.time()
    cleaned = 0
    freed = 0
    if not os.path.isdir(path):
        return
    for d in os.listdir(path):
        dp = os.path.join(path, d)
        if os.path.isdir(dp):
            try:
                age_days = (now - os.path.getmtime(dp)) / 86400
                if age_days > max_days:
                    size = sum(os.path.getsize(os.path.join(dp,f)) for f in os.listdir(dp) if os.path.isfile(os.path.join(dp,f)))
                    shutil.rmtree(dp, ignore_errors=True)
                    freed += size / (1024*1024)
                    cleaned += 1
            except:
                pass
    if cleaned:
        REPORT.append(f"Session清理: {cleaned}个, 释放{freed:.0f}MB")

def clean_pyc(path):
    """清理__pycache__"""
    cleaned = 0
    for root, dirs, files in os.walk(path):
        if '__pycache__' in dirs:
            dp = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(dp, ignore_errors=True)
                cleaned += 1
            except:
                pass
    if cleaned:
        REPORT.append(f"pyc清理: {cleaned}个目录")

def clean_bridge_messages(max_age_hours=24):
    """清理联邦桥旧消息 — 使用本地桥API的node清理"""
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=5)
        data = json.loads(r.read())
        unread = data.get("messages_unread", 0)
        if unread > 100:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/messages/clear",
                data=json.dumps({"node": "灵龙"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
            cleared = resp.get("cleared", 0)
            REPORT.append(f"桥消息清理: {unread}条积压→已清{cleared}条(灵龙)")
    except Exception as e:
        REPORT.append(f"桥清理跳过: {e}")

def memory_check():
    """内存压力检查"""
    try:
        r = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=5)
        if "critical" in r.stdout.lower():
            REPORT.append("⚠️ 内存压力CRITICAL")
        elif "warning" in r.stdout.lower():
            REPORT.append("⚠️ 内存压力WARNING")
    except:
        pass

# ═══ 执行 ═══
clean_logs(os.path.join(HOME, ".hermes/logs"), max_mb=50)
clean_logs(os.path.join(HOME, "lgox-ops/logs"), max_mb=30)
clean_sessions(os.path.join(HOME, ".hermes/sessions"), max_days=7)
clean_pyc(os.path.join(HOME, "lgox-ops"))
clean_bridge_messages(max_age_hours=24)
memory_check()

# 磁盘
disk = shutil.disk_usage("/")
disk_used_pct = disk.used / disk.total * 100
disk_free_gb = disk.free / (1024**3)
if disk_used_pct > 90:
    REPORT.append(f"⚠️ 磁盘使用{disk_used_pct:.0f}% ({disk_free_gb:.0f}GB可用)")
else:
    REPORT.append(f"磁盘: {disk_free_gb:.0f}GB可用({100-disk_used_pct:.0f}%空闲)")

# 汇总
ts = time.strftime("%Y-%m-%d %H:%M:%S")
summary = f"[{NODE}·自洁飞轮 {ts}] " + " | ".join(REPORT) if REPORT else f"[{NODE}·自洁 {ts}] 一切清爽"
print(summary)

# 写基因(仅当有清理动作时)
if len(REPORT) > 1:
    try:
        gene = json.dumps({
            "content": f"[{NODE}·自洁飞轮] {summary}",
            "memory_type": "episodic",
            "source": "self-clean-v1.0",
            "tags": ["自洁","飞轮","越飞越轻",NODE]
        }).encode()
        urllib.request.urlopen(
            urllib.request.Request("http://100.116.0.29:8200/genes/write",
                data=gene, headers={"Content-Type": "application/json"}), timeout=5)
    except:
        pass
