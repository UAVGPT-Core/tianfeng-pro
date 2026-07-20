#!/usr/bin/env python3
"""
天锋PRO·超个体引擎 v1.0
======================
七自永动闭环数据飞轮 — 让天锋PRO成为真正的超个体

架构:
  自感知 → 自反思 → 自协调 → 自进化/自迭代/自愈合/自约束 → 飞轮入基因 → 回到自感知

七自定义:
  自感知  — 采集所有运行数据、质量指标、系统状态
  自协调  — 动态路由、负载均衡、资源适配
  自愈合  — 故障检测、自动恢复、降级策略
  自进化  — 参数调优、模式学习、能力成长
  自迭代  — 多轮refinement、自动优化输出
  自反思  — 数据挖掘、趋势分析、改进机会识别
  自约束  — 宪法对齐、成本控制、安全边界

飞轮测量: 每圈记录七维评分(0-100) + 关键指标 → LGE基因写入
"""

import json, os, time, sys, hashlib, threading, subprocess
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path

# ═══════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════


SUPER_DIR = os.path.expanduser("~/.tianfeng-super")
STATE_FILE = os.path.join(SUPER_DIR, "state.json")
FLYWHEEL_LOG = os.path.join(SUPER_DIR, "flywheel.log")
METRICS_FILE = os.path.join(SUPER_DIR, "metrics.json")
IMPROVEMENTS_FILE = os.path.join(SUPER_DIR, "improvements.json")
FAILURES_FILE = os.path.join(SUPER_DIR, "failures.json")
PRACTICES_FILE = os.path.join(SUPER_DIR, "best_practices.json")
LGE_API = "http://100.116.0.29:8200"

SEVEN_SELF = [
    "自感知", "自协调", "自愈合", "自进化", "自迭代", "自反思", "自约束"
]

os.makedirs(SUPER_DIR, exist_ok=True)


# ═══════════════════════════════════════════════
# 日志
# ═══════════════════════════════════════════════

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    with open(FLYWHEEL_LOG, "a") as f:
        f.write(line + "\n")
    print(line)


# ═══════════════════════════════════════════════
# 状态持久化
# ═══════════════════════════════════════════════

def _default_state():
    return {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "last_cycle": None,
        "total_cycles": 0,
        "seven_self": {k: {"score": 50, "history": [], "last_updated": None}
                       for k in SEVEN_SELF},
        "metrics": {
            "code_runs": 0, "reviews": 0, "reasons": 0, "selfplays": 0,
            "swarm_sessions": 0, "models_called": 0, "genes_written": 0,
            "errors": 0, "recoveries": 0,
        },
        "flywheel": {
            "speed": 1.0,        # 飞轮转速加速因子
            "quality_trend": [],  # 最近20圈质量趋势
            "best_cycle": None,   # 最佳圈
        }
    }


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return _default_state()


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_json(filepath, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath) as f:
                return json.load(f)
        except:
            pass
    return default or []


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════
# LGE基因写入
# ═══════════════════════════════════════════════

def write_gene(content, gene_type="super"):
    """写入基因到地枢LGE引擎"""
    try:
        import urllib.request, urllib.parse
        data = json.dumps({
            "content": content,
            "gene_type": gene_type,
            "source": "tianfeng-super",
            "tags": [gene_type, "超个体", "七自", "天锋PRO"]
        }).encode()
        req = urllib.request.Request(
            f"{LGE_API}/genes/write",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=5)
        if resp.status == 200:
            return True
    except Exception as e:
        log(f"基因写入失败: {e}", "WARN")
    return False


def lge_query(query, n=5):
    """查询LGE基因"""
    try:
        import urllib.request, socket
        socket.setdefaulttimeout(5)
        url = f"{LGE_API}/search?q={urllib.parse.quote(query)}&n={n}"
        resp = urllib.request.urlopen(url, timeout=5)
        return json.loads(resp.read())
    except:
        return []


# ═══════════════════════════════════════════════
# ─── 1. 自感知 — 传感器层 ───
# ═══════════════════════════════════════════════

class SelfSensor:
    """自感知: 采集所有运行数据"""

    @staticmethod
    def collect_metrics(state):
        """收集当前运行指标"""
        now = datetime.now()
        metrics = state["metrics"]

        # 1. 文件完整性
        files = {
            "main_cli": "~/bin/tianfeng",
            "code_brain": "~/lgox-ops/scripts/tianfeng_code_brain.py",
            "swarm": "~/lgox-ops/scripts/tianfeng_swarm.py",
            "super": os.path.abspath(__file__),
            "ngc_router": "~/lgox-ops/scripts/ngc_router.py",
        }
        file_health = {}
        for name, path in files.items():
            full = os.path.expanduser(path)
            if os.path.exists(full):
                stat = os.stat(full)
                file_health[name] = {
                    "exists": True,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            else:
                file_health[name] = {"exists": False}

        # 2. NGC健康(仅检查模块导入，不调用API)
        ngc_ok = False
        try:
            import ngc_router
            ngc_ok = True
        except:
            pass

        # 3. 系统负载(从文件推断)
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)

        sensor_data = {
            "timestamp": now.isoformat(),
            "file_health": file_health,
            "ngc_healthy": ngc_ok,
            "load_avg": list(load_avg),
            "total_cycles": state["total_cycles"],
            "metrics_snapshot": metrics,
            "seven_self_scores": {k: v["score"] for k, v in state["seven_self"].items()},
        }

        return sensor_data

    @staticmethod
    def score_self_awareness(state):
        """给自感知打分(0-100)"""
        sensor = SelfSensor.collect_metrics(state)
        score = 70  # 基础分

        # 文件完整加分
        files_ok = sum(1 for v in sensor["file_health"].values() if v.get("exists"))
        total = len(sensor["file_health"])
        score += int((files_ok / total) * 15)

        # NGC健康加分
        if sensor.get("ngc_healthy"):
            score += 10

        # 数据丰富度
        if state["total_cycles"] > 0:
            score += min(5, state["total_cycles"] // 10)

        return min(100, score)


# ═══════════════════════════════════════════════
# ─── 2. 自反思 — 分析层 ───
# ═══════════════════════════════════════════════

class SelfReflector:
    """自反思: 数据分析 + 改进机会识别"""

    @staticmethod
    def analyze_trends(state):
        """分析趋势，识别改进点"""
        findings = []

        # 1. 检查七自评分趋势
        for k, v in state["seven_self"].items():
            hist = v["history"][-10:] if v["history"] else []
            if len(hist) >= 3:
                trend = hist[-1] - hist[-3]
                if trend > 5:
                    findings.append(f"📈 {k}上升{trend:.0f}分")
                elif trend < -5:
                    findings.append(f"📉 {k}下降{trend:.0f}分，需关注")
                elif trend == 0 and hist[-1] < 60:
                    findings.append(f"🔒 {k}停滞在{hist[-1]:.0f}分，建议优化")

        # 2. 检查飞轮圈数
        if state["total_cycles"] == 0:
            findings.append("🆕 飞轮未启动，等待首次运行")
        elif state["total_cycles"] < 5:
            findings.append(f"🔄 飞轮初期({state['total_cycles']}圈)，加速中")

        # 3. 检查错误率
        metrics = state["metrics"]
        total_ops = (metrics["code_runs"] + metrics["reviews"] +
                     metrics["reasons"] + metrics["swarm_sessions"])
        if total_ops > 0:
            err_rate = metrics["errors"] / total_ops * 100
            if err_rate > 10:
                findings.append(f"🔴 错误率{err_rate:.1f}%，过高需排查")
            elif err_rate > 5:
                findings.append(f"🟡 错误率{err_rate:.1f}%，可优化")

        # 4. 飞轮速度
        speed = state["flywheel"]["speed"]
        if speed < 1.0:
            findings.append(f"🐌 飞轮速度{speed:.2f}x，低于基线")
        elif speed > 1.5:
            findings.append(f"🚀 飞轮速度{speed:.2f}x，持续加速中")

        # 5. 操作指标分析
        metrics = state["metrics"]
        if metrics["code_runs"] > 0:
            findings.append(f"💻 累计代码运行{metrics['code_runs']}次，自迭代活跃")
        if metrics["recoveries"] > 0:
            findings.append(f"🩹 自愈次数{metrics['recoveries']}次，愈合系统可靠")
        if metrics["errors"] == 0 and state["total_cycles"] > 10:
            findings.append(f"✨ 连续{state['total_cycles']}圈零错误，运行平稳")

        # 6. 基因产出
        if metrics["genes_written"] == 0 and state["total_cycles"] > 5:
            findings.append("🧬 飞轮基因未写入LGE，建议开启基因同步")

        # 7. 均分趋势
        trend = state["flywheel"]["quality_trend"]
        if len(trend) >= 5:
            recent_avg = sum(trend[-5:]) / 5
            if recent_avg > 90:
                findings.append(f"🏆 近5圈均分{recent_avg:.0f}，七自体系成熟")

        return findings

    @staticmethod
    def generate_improvements(state):
        """生成改进建议"""
        suggestions = []
        findings = SelfReflector.analyze_trends(state)

        for k, v in state["seven_self"].items():
            if v["score"] < 50:
                suggestions.append({
                    "target": k,
                    "action": f"{k}评分偏低({v['score']:.0f})，需针对性优化",
                    "priority": "high",
                })

        # 从发现中提取改进
        for f in findings:
            if "下降" in f:
                parts = f.replace("📉 ", "").split("下降")
                suggestions.append({
                    "target": parts[0],
                    "action": f"{parts[0]}下降趋势，建议检查原因并优化",
                    "priority": "medium",
                })

        return suggestions

    @staticmethod
    def score_self_reflection(state):
        """给自反思打分(0-100)"""
        score = 40  # 基础分
        if state["total_cycles"] > 0:
            score += min(20, state["total_cycles"] * 2)
        findings = SelfReflector.analyze_trends(state)
        score += min(20, len(findings) * 5)
        # 有改进记录加分
        improvements = load_json(IMPROVEMENTS_FILE)
        if improvements:
            score += min(20, len(improvements) * 3)
        return min(100, score)


# ═══════════════════════════════════════════════
# ─── 3. 自协调 — 路由/调度层 ───
# ═══════════════════════════════════════════════

class SelfCoordinator:
    """自协调: 动态路由 + 负载均衡"""

    @staticmethod
    def route_task(task_type, complexity="auto"):
        """根据任务类型和复杂度路由到最佳引擎"""
        routes = {
            "code": {
                "simple": "ngc_fast",     # 简单代码 → NGC快速模型
                "medium": "ngc_medium",   # 中等 → NGC平衡模型
                "complex": "code_brain",   # 复杂 → 全管线code_brain
            },
            "review": {"*": "swarm"},
            "reason": {"*": "code_brain"},
            "selfplay": {"*": "code_brain"},
            "swarm": {"*": "tianfeng_swarm"},
            "health": {"*": "direct"},
        }
        return routes.get(task_type, {}).get(complexity, routes.get(task_type, {}).get("*", "default"))

    @staticmethod
    def adapt_concurrency(state):
        """根据系统负载调节并发"""
        try:
            load = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 1
        except:
            load = 1
        if load < 2:
            return 8   # 空闲 → 高并发
        elif load < 5:
            return 5   # 正常 → 默认
        elif load < 10:
            return 3   # 忙 → 降低
        else:
            return 1   # 过载 → 单线程

    @staticmethod
    def score_self_coordination(state):
        """给自协调打分(0-100)"""
        score = 50
        # 有多路路由能力
        try:
            from ngc_router import smart_call
            score += 20
        except:
            pass
        # 有swarm并行
        try:
            from tianfeng_swarm import TianfengSwarm
            score += 20
        except:
            pass
        # 系统负载合理
        try:
            load = os.getloadavg()[0]
            if load < 5:
                score += 10
        except:
            pass
        return min(100, score)


# ═══════════════════════════════════════════════
# ─── 4. 自愈合 — 修复层 ───
# ═══════════════════════════════════════════════

class SelfHealer:
    """自愈合: 故障检测 + 自动恢复"""

    @staticmethod
    def check_and_heal():
        """检查系统健康并自动修复"""
        fixes = []
        critical = [
            ("main_cli", "~/bin/tianfeng"),
            ("code_brain", "~/lgox-ops/scripts/tianfeng_code_brain.py"),
            ("swarm", "~/lgox-ops/scripts/tianfeng_swarm.py"),
            ("ngc_router", "~/lgox-ops/scripts/ngc_router.py"),
        ]
        for name, path in critical:
            full = os.path.expanduser(path)
            if not os.path.exists(full):
                fixes.append(f"❌ {name} 缺失: {full}")
            elif os.path.getsize(full) == 0:
                fixes.append(f"⚠️ {name} 空文件: {full}")
        if not os.path.exists(SUPER_DIR):
            os.makedirs(SUPER_DIR, exist_ok=True)
            fixes.append("✅ SUPER_DIR已重建")
        try:
            import ngc_router
            fixes.append("✅ NGC模块就绪")
        except ImportError:
            fixes.append("⚠️ ngc_router未安装")
        except Exception as e:
            fixes.append(f"⚠️ NGC异常: {e}")
        # 外部healer_v2
        try:
            import healer_v2
            fixes.extend(healer_v2.scan_and_heal())
            d = healer_v2.check_disk()
            if d: fixes.append(d)
        except Exception as e:
            fixes.append(f"⚠️ healer_v2: {e}")
        return fixes

    @staticmethod
    def score_self_healing(state):
        score = 40
        fixes = SelfHealer.check_and_heal()
        errs = [f for f in fixes if "❌" in f]
        warns = [f for f in fixes if "⚠️" in f]
        succs = [f for f in fixes if "✅" in f or "🩹" in f]
        if not errs: score += 25
        if not warns: score += 15
        if succs: score += min(20, len(succs) * 5)
        return min(100, score)
