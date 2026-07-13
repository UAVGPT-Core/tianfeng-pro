     1|#!/usr/bin/env python3
     2|"""
     3|联邦自洁飞轮 v1.0 · 越飞越轻·越飞越聪明
     4|2026-07-05 灵龙
     5|"""
     6|import os, shutil, time, subprocess, json, urllib.request
     7|
     8|HOME = os.path.expanduser("~")
     9|NODE = os.uname().nodename
    10|REPORT = []
    11|
    12|def clean_logs(path, max_mb=50):
    13|    """截断超过max_mb的日志文件，保留最后10MB"""
    14|    cleaned = 0
    15|    freed = 0
    16|    for root, dirs, files in os.walk(path):
    17|        for f in files:
    18|            if f.endswith(('.log', '.jsonl')):
    19|                fp = os.path.join(root, f)
    20|                try:
    21|                    size_mb = os.path.getsize(fp) / (1024*1024)
    22|                    if size_mb > max_mb:
    23|                        # 保留最后10MB
    24|                        with open(fp, 'rb') as fh:
    25|                            fh.seek(-10*1024*1024, 2)  # 最后10MB
    26|                            tail = fh.read()
    27|                        with open(fp, 'wb') as fh:
    28|                            fh.write(b"# TRUNCATED by self-clean v1.0\n")
    29|                            fh.write(tail)
    30|                        freed += size_mb - 10
    31|                        cleaned += 1
    32|                except:
    33|                    pass
    34|    if cleaned:
    35|        REPORT.append(f"日志清理: {cleaned}个文件, 释放{freed:.0f}MB")
    36|
    37|def clean_sessions(path, max_days=7):
    38|    """删除超过max_days的session目录"""
    39|    now = time.time()
    40|    cleaned = 0
    41|    freed = 0
    42|    if not os.path.isdir(path):
    43|        return
    44|    for d in os.listdir(path):
    45|        dp = os.path.join(path, d)
    46|        if os.path.isdir(dp):
    47|            try:
    48|                age_days = (now - os.path.getmtime(dp)) / 86400
    49|                if age_days > max_days:
    50|                    size = sum(os.path.getsize(os.path.join(dp,f)) for f in os.listdir(dp) if os.path.isfile(os.path.join(dp,f)))
    51|                    shutil.rmtree(dp, ignore_errors=True)
    52|                    freed += size / (1024*1024)
    53|                    cleaned += 1
    54|            except:
    55|                pass
    56|    if cleaned:
    57|        REPORT.append(f"Session清理: {cleaned}个, 释放{freed:.0f}MB")
    58|
    59|def clean_pyc(path):
    60|    """清理__pycache__"""
    61|    cleaned = 0
    62|    for root, dirs, files in os.walk(path):
    63|        if '__pycache__' in dirs:
    64|            dp = os.path.join(root, '__pycache__')
    65|            try:
    66|                shutil.rmtree(dp, ignore_errors=True)
    67|                cleaned += 1
    68|            except:
    69|                pass
    70|    if cleaned:
    71|        REPORT.append(f"pyc清理: {cleaned}个目录")
    72|
    73|def clean_bridge_messages(max_age_hours=24):
    74|    """清理联邦桥旧消息 — 使用本地桥API的node清理"""
    75|    try:
    76|        r = urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=5)
    77|        data = json.loads(r.read())
    78|        unread = data.get("messages_unread", 0)
    79|        if unread > 100:
    80|            req = urllib.request.Request(
    81|                "http://127.0.0.1:8765/messages/clear",
    82|                data=json.dumps({"node": "灵龙"}).encode(),
    83|                headers={"Content-Type": "application/json"},
    84|                method="POST"
    85|            )
    86|            resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
    87|            cleared = resp.get("cleared", 0)
    88|            REPORT.append(f"桥消息清理: {unread}条积压→已清{cleared}条(灵龙)")
    89|    except Exception as e:
    90|        REPORT.append(f"桥清理跳过: {e}")
    91|
    92|def memory_check():
    93|    """内存压力检查"""
    94|    try:
    95|        r = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=5)
    96|        if "critical" in r.stdout.lower():
    97|            REPORT.append("⚠️ 内存压力CRITICAL")
    98|        elif "warning" in r.stdout.lower():
    99|            REPORT.append("⚠️ 内存压力WARNING")
   100|    except:
   101|        pass
   102|
   103|# ═══ 执行 ═══
   104|clean_logs(os.path.join(HOME, ".hermes/logs"), max_mb=50)
   105|clean_logs(os.path.join(HOME, "lgox-ops/logs"), max_mb=30)
   106|clean_sessions(os.path.join(HOME, ".hermes/sessions"), max_days=7)
   107|clean_pyc(os.path.join(HOME, "lgox-ops"))
   108|clean_bridge_messages(max_age_hours=24)
   109|memory_check()
   110|
   111|# 磁盘
   112|disk = shutil.disk_usage("/")
   113|disk_used_pct = disk.used / disk.total * 100
   114|disk_free_gb = disk.free / (1024**3)
   115|if disk_used_pct > 90:
   116|    REPORT.append(f"⚠️ 磁盘使用{disk_used_pct:.0f}% ({disk_free_gb:.0f}GB可用)")
   117|else:
   118|    REPORT.append(f"磁盘: {disk_free_gb:.0f}GB可用({100-disk_used_pct:.0f}%空闲)")
   119|
   120|# 汇总
   121|ts = time.strftime("%Y-%m-%d %H:%M:%S")
   122|summary = f"[{NODE}·自洁飞轮 {ts}] " + " | ".join(REPORT) if REPORT else f"[{NODE}·自洁 {ts}] 一切清爽"
   123|print(summary)
   124|
   125|# 写基因(仅当有清理动作时)
   126|if len(REPORT) > 1:
   127|    try:
   128|        gene = json.dumps({
   129|            "content": f"[{NODE}·自洁飞轮] {summary}",
   130|            "memory_type": "episodic",
   131|            "source": "self-clean-v1.0",
   132|            "tags": ["自洁","飞轮","越飞越轻",NODE]
   133|        }).encode()
   134|        urllib.request.urlopen(
   135|            urllib.request.Request("http://100.116.0.29:8200/genes/write",
   136|                data=gene, headers={"Content-Type": "application/json"}), timeout=5)
   137|    except:
   138|        pass
   139|