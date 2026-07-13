#!/usr/bin/env python3
"""
LGOX联邦 Onyx索引健康度预测引擎 v1.0
═══════════════════════════════════════════════════
不等卡死才告警 — 预测卡死时间，提前预警。

五维监控:
  ① 索引吞吐率 (attempts created/min)
  ② 完成速率 (attempts completed/min)  
  ③ 平均完成时间 (avg minutes from start to end)
  ④ 卡死比例 (IN_PROGRESS > 30min / total)
  ⑤ 排队深度 (NOT_STARTED count)

自学习基线:
  - 每5分钟采样，24小时滑动窗口
  - 偏离基线2σ → 黄色预警
  - 偏离基线3σ → 红色告警
  - 卡死增长趋势 → 预测"将在X分钟内卡死"

预测算法: 线性回归 on 卡死比例~时间 → 预测达到阈值的时间
告警通道: 联邦桥 + 本地日志 + LGE基因写入

基因: GENE-PRO-onyx-index-predictor-v1
作者: 灵龙·LGOX联邦
日期: 2026-06-28
"""

import json, os, time, subprocess, sqlite3, statistics, math
from datetime import datetime, timezone, timedelta
from collections import deque

# ═══════ 配置 ═══════
DGX2_SSH = "dgx2"  # SSH别名
DB_PATH = os.path.expanduser("~/lgox-ops/data/onyx-predictor.db")
FED_BRIDGE = "http://100.100.89.2:8765"
NODE_NAME = os.getenv("LGOX_NODE", "灵龙")
SAMPLE_INTERVAL = 300  # 5分钟
BASELINE_WINDOW = 86400  # 24小时
STUCK_THRESHOLD = 30  # 30分钟IN_PROGRESS算卡死
ALERT_COOLDOWN = 3600  # 同类告警1小时内不重复

# 预测阈值
YELLOW_STUCK = 3    # 卡死attempt >= 3 → 黄
RED_STUCK = 8       # 卡死attempt >= 8 → 红  
YELLOW_QUEUE = 20   # 排队 >= 20 → 黄
RED_QUEUE = 50      # 排队 >= 50 → 红
YELLOW_GROWTH = 0.5  # 卡死比例30分钟内增长50% → 黄
PREDICT_THRESHOLD = 15  # 预测在N分钟内达到红区 → 预警告警

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ═══════ 数据库 ═══════
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS samples (
        ts REAL PRIMARY KEY,
        total_attempts INTEGER,
        in_progress INTEGER,
        completed INTEGER,
        failed INTEGER,
        not_started INTEGER,
        stuck_count INTEGER,
        avg_completion_min REAL,
        created_last_5min INTEGER,
        completed_last_5min INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS alerts (
        ts REAL,
        level TEXT,
        title TEXT,
        detail TEXT,
        fired INTEGER DEFAULT 1
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS baseline (
        metric TEXT PRIMARY KEY,
        mean REAL,
        stddev REAL,
        samples INTEGER,
        last_updated REAL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts)")
    conn.commit()
    conn.close()

# ═══════ 数据采集 ═══════
def _psql(sql):
    """通过SSH到地枢执行psql查询，返回stdout文本"""
    cmd = '/usr/bin/docker exec onyx-relational_db-1 psql -U postgres -d postgres -t -c "' + sql + '"'
    result = subprocess.run(
        ["ssh", DGX2_SSH, cmd],
        capture_output=True, text=True, timeout=20
    )
    return result.stdout.strip()

def collect_index_metrics():
    """SSH到地枢采集Onyx索引指标"""
    try:
        # 按状态分布 (最近2小时)
        dist_out = _psql(
            "SELECT status, count(*) as cnt FROM index_attempt"
            " WHERE time_started > now() - interval '2 hours'"
            " GROUP BY status;"
        )
        
        metrics = {
            "total": 0, "in_progress": 0, "completed": 0, 
            "failed": 0, "not_started": 0, "stuck_count": 0,
            "avg_completion_min": 0, "created_last_5min": 0, "completed_last_5min": 0
        }
        
        for line in dist_out.split("\n"):
            parts = [p.strip() for p in line.strip().split("|")]
            if len(parts) < 2:
                continue
            try:
                count = int(parts[1])
            except ValueError:
                continue
            status = parts[0]
            metrics["total"] += count
            if status == "IN_PROGRESS":
                metrics["in_progress"] = count
                # 查卡死的 (>30min)
                stuck_out = _psql(
                    "SELECT count(*) FROM index_attempt"
                    " WHERE status='IN_PROGRESS'"
                    " AND time_started < now() - interval '30 minutes';"
                )
                try: metrics["stuck_count"] = int(stuck_out)
                except: pass
            elif status in ("SUCCESS", "COMPLETED"):
                metrics["completed"] = count
            elif status == "FAILED":
                metrics["failed"] = count
            elif status == "NOT_STARTED":
                metrics["not_started"] = count
        
        # 最近5分钟新增
        try: metrics["created_last_5min"] = int(_psql(
            "SELECT count(*) FROM index_attempt"
            " WHERE time_started > now() - interval '5 minutes';"))
        except: pass
        
        # 最近10分钟完成
        try: metrics["completed_last_5min"] = int(_psql(
            "SELECT count(*) FROM index_attempt"
            " WHERE status='SUCCESS'"
            " AND time_started > now() - interval '10 minutes';"))
        except: pass
        
        # 平均完成时间 (分钟)
        try: metrics["avg_completion_min"] = round(float(_psql(
            "SELECT coalesce(avg(extract(epoch from time_updated - time_started)/60),0)"
            " FROM index_attempt WHERE status='SUCCESS'"
            " AND time_started > now() - interval '1 hour';")), 1)
        except: pass
        
        return metrics
    except Exception as e:
        print(f"[ERROR] 采集失败: {e}")
        return None

# ═══════ 基线更新 ═══════
def update_baseline():
    """从最近24小时样本更新基线"""
    conn = sqlite3.connect(DB_PATH)
    now = time.time()
    
    metrics_to_track = ["stuck_count", "not_started", "in_progress", 
                        "created_last_5min", "completed_last_5min", "avg_completion_min"]
    
    for metric in metrics_to_track:
        rows = conn.execute(
            f"SELECT {metric} FROM samples WHERE ts > ? AND {metric} IS NOT NULL",
            (now - BASELINE_WINDOW,)
        ).fetchall()
        
        if len(rows) >= 5:  # 至少5个样本才计算
            values = [r[0] for r in rows]
            mean = statistics.mean(values)
            stddev = statistics.stdev(values) if len(values) >= 2 else 0
            conn.execute(
                "INSERT OR REPLACE INTO baseline VALUES (?,?,?,?,?)",
                (metric, mean, stddev, len(values), now)
            )
    
    conn.commit()
    conn.close()

def get_baseline(metric):
    """获取指定指标的基线值"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT mean, stddev, samples FROM baseline WHERE metric=? AND last_updated > ?",
        (metric, time.time() - 3600)
    ).fetchone()
    conn.close()
    if row:
        return {"mean": row[0], "stddev": row[1], "samples": row[2]}
    return None

# ═══════ 预测引擎 ═══════
def predict_stuck_time():
    """线性回归预测卡死达到阈值的时间"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ts, stuck_count FROM samples WHERE ts > ? ORDER BY ts",
        (time.time() - 3600,)  # 最近1小时
    ).fetchall()
    conn.close()
    
    if len(rows) < 6:
        return None  # 样本不足
    
    # 简单线性回归: stuck_count = a * t + b
    t0 = rows[0][0]
    xs = [(r[0] - t0) / 60 for r in rows]  # 分钟
    ys = [r[1] for r in rows]
    
    n = len(xs)
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x*y for x,y in zip(xs, ys))
    sum_x2 = sum(x*x for x in xs)
    
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return None
    
    slope = (n * sum_xy - sum_x * sum_y) / denom
    
    if slope <= 0:
        return None  # 趋势下降或平稳
    
    # 预测达到红区(8)的时间
    current = ys[-1]
    if current >= 8:
        return {"status": "already_red", "current": current, "eta_min": 0}
    
    remaining = 8 - current
    eta_min = remaining / slope
    last_ts = rows[-1][0]
    eta_ts = last_ts + eta_min * 60
    
    return {
        "status": "predicted" if eta_min < 60 else "monitoring",
        "current": current,
        "slope": round(slope, 3),
        "eta_min": round(eta_min, 1),
        "eta_time": datetime.fromtimestamp(eta_ts).strftime("%H:%M:%S"),
        "confidence": min(0.95, len(rows) / 20)  # 样本越多置信度越高
    }

# ═══════ 告警判断 ═══════
def check_alerts(metrics):
    """多级告警判断"""
    alerts = []
    now = time.time()
    
    # 检查同类告警冷却
    conn = sqlite3.connect(DB_PATH)
    recent = conn.execute(
        "SELECT level, title FROM alerts WHERE ts > ? AND fired=1",
        (now - ALERT_COOLDOWN,)
    ).fetchall()
    recent_titles = {r[1] for r in recent}
    conn.close()
    
    stuck = metrics.get("stuck_count", 0)
    queue = metrics.get("not_started", 0)
    in_prog = metrics.get("in_progress", 0)
    
    # 1. 卡死数量
    if stuck >= RED_STUCK:
        title = f"🔴 Onyx索引卡死: {stuck}个attempt超过30分钟"
        if title not in recent_titles:
            alerts.append({"level": "red", "title": title, 
                          "detail": f"IN_PROGRESS={in_prog} 排队={queue} 卡死={stuck}"})
    elif stuck >= YELLOW_STUCK:
        title = f"🟡 Onyx索引预警: {stuck}个attempt卡死"
        if title not in recent_titles:
            alerts.append({"level": "yellow", "title": title,
                          "detail": f"IN_PROGRESS={in_prog} 排队={queue} 卡死={stuck}"})
    
    # 2. 排队深度
    if queue >= RED_QUEUE:
        title = f"🔴 Onyx索引队列严重堆积: {queue}个NOT_STARTED"
        if title not in recent_titles:
            alerts.append({"level": "red", "title": title,
                          "detail": f"排队{queue}个, 当前处理中{in_prog}个"})
    elif queue >= YELLOW_QUEUE:
        title = f"🟡 Onyx索引队列堆积: {queue}个NOT_STARTED"
        if title not in recent_titles:
            alerts.append({"level": "yellow", "title": title,
                          "detail": f"排队{queue}个, 当前处理中{in_prog}个"})
    
    # 3. 偏离基线
    for metric in ["stuck_count", "not_started"]:
        baseline = get_baseline(metric)
        if baseline and baseline["samples"] >= 5:
            val = metrics.get(metric, 0)
            if val > baseline["mean"] + 3 * baseline["stddev"] and baseline["stddev"] > 0:
                title = f"🔴 Onyx{metric}偏离基线: {val} vs {baseline['mean']:.1f}±{baseline['stddev']:.1f}"
                if title not in recent_titles:
                    alerts.append({"level": "red", "title": title, 
                                  "detail": f"3σ异常, 基线24h均值{baseline['mean']:.1f}"})
            elif val > baseline["mean"] + 2 * baseline["stddev"] and val > 0 and baseline["stddev"] > 0:
                title = f"🟡 Onyx{metric}偏离基线: {val} vs {baseline['mean']:.1f}±{baseline['stddev']:.1f}"
                if title not in recent_titles:
                    alerts.append({"level": "yellow", "title": title,
                                  "detail": f"2σ异常, 基线24h均值{baseline['mean']:.1f}"})
    
    # 4. 增长趋势检测
    conn = sqlite3.connect(DB_PATH)
    recent_stuck = conn.execute(
        "SELECT stuck_count FROM samples ORDER BY ts DESC LIMIT 6"
    ).fetchall()
    conn.close()
    if len(recent_stuck) >= 3:
        oldest = recent_stuck[-1][0]
        newest = recent_stuck[0][0]
        if oldest > 0 and newest > oldest * 2:
            title = f"🟡 Onyx卡死趋势增长: {oldest}→{newest} (30分钟内翻倍)"
            if title not in recent_titles:
                alerts.append({"level": "yellow", "title": title,
                              "detail": f"卡死从{oldest}增长到{newest}, 趋势恶化中"})
    
    # 5. 预测性告警
    prediction = predict_stuck_time()
    if prediction and prediction.get("status") in ("predicted", "already_red"):
        if prediction["status"] == "already_red":
            title = f"🔴 Onyx索引已进入红区: {prediction['current']}个卡死"
        else:
            title = f"🟡 预测Onyx将在{prediction['eta_min']:.0f}分钟内进入红区 ({prediction['eta_time']})"
        if title not in recent_titles:
            alerts.append({"level": "red" if prediction["status"]=="already_red" else "yellow",
                          "title": title,
                          "detail": f"趋势斜率={prediction['slope']}/min 置信度={prediction['confidence']:.0%}"})
    
    return alerts

# ═══════ 告警发送 ═══════
def send_alert(level, title, detail):
    """通过联邦桥发送告警"""
    try:
        import urllib.request
        msg = f"[Onyx索引预测器] {title}\n{detail}\n时间: {datetime.now().strftime('%H:%M:%S')}"
        data = json.dumps({
            "from": NODE_NAME,
            "to": "天枢",
            "content": msg
        }).encode()
        req = urllib.request.Request(
            f"{FED_BRIDGE}/messages/send",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[WARN] 联邦桥发送失败: {e}")

def save_alert(level, title, detail):
    """持久化告警记录"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO alerts VALUES (?,?,?,?,1)",
        (time.time(), level, title, detail)
    )
    conn.commit()
    conn.close()

# ═══════ LGE基因写入 ═══════
def write_gene(metrics, alerts):
    """写预测基因到LGE"""
    try:
        import urllib.request
        content = json.dumps({
            "predictor_version": "v1.0",
            "timestamp": time.time(),
            "metrics": metrics,
            "alerts": [a["title"] for a in alerts],
            "prediction": predict_stuck_time(),
        }, ensure_ascii=False)
        
        payload = json.dumps({
            "content": content,
            "memory_type": "episodic",
            "source": "灵龙/onyx-index-predictor",
            "tags": ["onyx", "index-health", "predictor", "auto-monitor"]
        }).encode()
        
        req = urllib.request.Request(
            "http://100.116.0.29:8200/genes/write",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

# ═══════ 主循环 ═══════
def main():
    init_db()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Onyx索引预测器 v1.0 启动")
    
    # 1. 采集
    metrics = collect_index_metrics()
    if not metrics:
        print("[ERROR] 采集失败, 跳过本周期")
        return
    
    print(f"  采集: total={metrics['total']} IN_PROGRESS={metrics['in_progress']} "
          f"stuck={metrics['stuck_count']} queue={metrics['not_started']} "
          f"avg={metrics['avg_completion_min']}min")
    
    # 2. 保存样本
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO samples VALUES (?,?,?,?,?,?,?,?,?,?)",
        (now, metrics["total"], metrics["in_progress"], metrics["completed"],
         metrics["failed"], metrics["not_started"], metrics["stuck_count"],
         metrics["avg_completion_min"], metrics["created_last_5min"],
         metrics["completed_last_5min"])
    )
    # 清理7天前旧样本
    conn.execute("DELETE FROM samples WHERE ts < ?", (now - 7*86400,))
    conn.commit()
    conn.close()
    
    # 3. 更新基线
    update_baseline()
    
    # 4. 预测
    prediction = predict_stuck_time()
    if prediction:
        print(f"  预测: {prediction.get('status')} 当前={prediction.get('current')} "
              f"斜率={prediction.get('slope')}/min ETA={prediction.get('eta_time')}")
    
    # 5. 告警
    alerts = check_alerts(metrics)
    if alerts:
        print(f"  告警: {len(alerts)}条")
        for a in alerts:
            print(f"    {a['level']}: {a['title']}")
            send_alert(a["level"], a["title"], a["detail"])
            save_alert(a["level"], a["title"], a["detail"])
        
        # 红色告警→写基因
        if any(a["level"] == "red" for a in alerts):
            write_gene(metrics, alerts)
    else:
        print(f"  ✅ 正常, 无告警")
    
    # 6. 基线摘要
    for metric in ["stuck_count", "not_started"]:
        bl = get_baseline(metric)
        if bl:
            print(f"  基线 {metric}: mean={bl['mean']:.1f}±{bl['stddev']:.1f} (n={bl['samples']})")

if __name__ == "__main__":
    main()
