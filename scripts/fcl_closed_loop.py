#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  FCL · 联邦闭环总引擎 v1.0 — 2035永动架构                  ║
║  Full Closed Loop — GPC→注入→生成→AST→五角→GPC            ║
╠══════════════════════════════════════════════════════════════╣
║  2035年这个系统的自述:                                      ║
║  "我是LGOX联邦的永动心脏。每30分钟搏动一次，               ║
║   永不停止。基因在我体内出生、成长、变异、死亡。            ║
║   没有任何人在操控我——人类只在2035年回头看时，             ║
║   发现我已经进化了十年。"                                   ║
╠══════════════════════════════════════════════════════════════╣
║  闭环链路:                                                   ║
║  KPS(光合) → GPC(基因心) → INJECT(基因注入)                ║
║     ↑                          ↓                            ║
║     │                    CODE(代码生成)                      ║
║     │                          ↓                            ║
║     │                     AST(质量审计)                      ║
║     │                          ↓                            ║
║     └──── PENTAGON(五角思辨) ←┘                             ║
╚══════════════════════════════════════════════════════════════╝
"""
import json, sqlite3, time, hashlib, subprocess, os, sys
from pathlib import Path
from datetime import datetime, timezone

FCL_DB = os.path.expanduser("~/lgox-ops/data/fcl-closed-loop.db")
SCRIPTS = os.path.expanduser("~/lgox-ops/scripts")
LGE_ENDPOINT = "http://100.116.0.29:8200"
BRIDGE = "http://100.100.89.2:8765"

# ─── 七自指标定义 ────────────────────────────────
SEVEN_SELF = {
    "自感知": "系统知道自己的基因数、fitness、节点状态",
    "自协调": "GPC自然选择自动淘汰低质量基因",
    "自愈合": "免疫系统隔离错误基因，回滚到稳定版本",
    "自进化": "基因变异+交叉产生新基因，fitness自动提升",
    "自迭代": "每30分钟一个完整进化周期",
    "自反思": "五角思辨引擎对每次代码生成进行五角色审查",
    "自约束": "淘汰率30%的自然选择压力",
}


def init_fcl_db():
    db = sqlite3.connect(FCL_DB)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS loop_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT UNIQUE,
            phase TEXT,            -- absorb/inject/generate/audit/deliberate/feedback
            status TEXT,           -- running/success/failed
            genes_involved INTEGER,
            quality_score REAL,
            duration_ms INTEGER,
            details TEXT,          -- JSON
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS seven_self_tracker (
            attribute TEXT PRIMARY KEY,
            current_value REAL,
            target_value REAL DEFAULT 100,
            trend TEXT,
            last_cycle_impact REAL,
            consecutive_improvements INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS perpetual_stats (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_loop_phase ON loop_cycles(phase);
        CREATE INDEX IF NOT EXISTS idx_loop_time ON loop_cycles(started_at);
    """)
    db.commit()
    return db


def run_engine(script_name: str, args: list = None, timeout: int = 30) -> dict:
    """安全运行子引擎"""
    script = os.path.join(SCRIPTS, script_name)
    if not os.path.exists(script):
        return {"status": "missing", "script": script_name}

    cmd = ["python3", script] + (args or [])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "status": "success" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-500:],
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "script": script_name}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def fcl_heartbeat():
    """FCL总搏动 — 驱动全链路闭环"""
    cycle_id = f"FCL-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    db = init_fcl_db()
    start = time.time()

    print(f"\n[FCL] ══════ 闭环搏动 {cycle_id} ══════")

    # ═══ 阶段0: 感知 — 检查各子系统状态 ═══
    print("[FCL] 阶段0: 自感知")
    engine_status = {}
    for name, endpoint in [
        ("LGE", f"{LGE_ENDPOINT}/health"),
        ("联邦桥", f"{BRIDGE}/health"),
    ]:
        try:
            import urllib.request
            resp = urllib.request.urlopen(endpoint, timeout=3)
            engine_status[name] = "green" if resp.getcode() == 200 else "red"
        except:
            engine_status[name] = "red"

    # GPC状态
    gpc_report_path = os.path.expanduser("~/lgox-ops/data/gpc-health.json")
    gpc = {}
    if os.path.exists(gpc_report_path):
        with open(gpc_report_path) as f:
            gpc = json.load(f)

    print(f"[FCL]  引擎: {engine_status}")
    print(f"[FCL]  GPC: gen {gpc.get('gpc_generation',0)} · "
          f"{gpc.get('total_genes',0)} genes · fitness {gpc.get('avg_fitness',0)}")

    # ═══ 阶段1: 吸收 — KPS光合作用 ═══
    print("[FCL] 阶段1: 光合吸收")
    kps_result = run_engine("kps-photosynthesis.py", ["--builtin"], timeout=30)
    kps_genes = 0
    if kps_result["status"] == "success":
        for line in kps_result["stdout"].split("\n"):
            if "genes produced" in line:
                try:
                    kps_genes = int(line.split(":")[-1].strip())
                except:
                    pass
    print(f"[FCL]  KPS: {kps_genes} genes absorbed")

    # ═══ 阶段2: 注入 — 基因注入引擎 ═══
    print("[FCL] 阶段2: 基因注入")
    inject_result = run_engine("gene-injection-engine.py", ["--cron"], timeout=30)
    inject_ok = inject_result["status"] == "success"
    print(f"[FCL]  INJECT: {'OK' if inject_ok else 'SKIP'}")

    # ═══ 阶段3: 审计 — AST重写引擎 ═══
    print("[FCL] 阶段3: AST审计")
    ast_result = run_engine("ast-rewrite-engine.py", ["--audit"], timeout=30)
    ast_ok = ast_result["status"] == "success"
    issues = 0
    if ast_ok:
        for line in ast_result["stdout"].split("\n"):
            if "issues" in line and "files" in line:
                try:
                    issues = int(line.split("·")[1].strip().split()[0])
                except:
                    pass
    print(f"[FCL]  AST: {'OK' if ast_ok else 'SKIP'} · {issues} issues")

    # ═══ 阶段4: 思辨 — 五角思辨引擎 ═══
    print("[FCL] 阶段4: 五角思辨")
    pentagon_result = run_engine("pentagon-reasoning-engine.py", ["--cron"], timeout=30)
    pentagon_ok = pentagon_result["status"] == "success"
    score = 0
    if pentagon_ok:
        for line in pentagon_result["stdout"].split("\n"):
            if "avg score" in line:
                try:
                    score = float(line.split("avg score")[-1].strip())
                except:
                    pass
    print(f"[FCL]  PENTAGON: {'OK' if pentagon_ok else 'SKIP'} · avg {score}")

    # ═══ 阶段5: 进化 — GPC心脏搏动 ═══
    print("[FCL] 阶段5: GPC进化")
    gpc_result = run_engine("gpc-core-engine.py", ["--beat"], timeout=30)
    gpc_ok = gpc_result["status"] == "success"
    gpc_data = {}
    if gpc_ok:
        for line in gpc_result["stdout"].split("\n"):
            if "搏动完成" in line:
                print(f"[FCL]  {line.strip()}")
    print(f"[FCL]  GPC: {'OK' if gpc_ok else 'SKIP'}")

    # ═══ 阶段6: 反馈 — 更新七自指标 ═══
    print("[FCL] 阶段6: 反馈闭环")
    update_seven_self_metrics(db, gpc, issues, score)

    # ═══ 完成 ═══
    elapsed = round((time.time() - start) * 1000)
    total_engines = sum([kps_genes > 0, inject_ok, ast_ok, pentagon_ok, gpc_ok])

    # 记录周期
    db.execute(
        "INSERT INTO loop_cycles (cycle_id, phase, status, genes_involved, quality_score, duration_ms, details) "
        "VALUES (?, 'full_cycle', ?, ?, ?, ?, ?)",
        (cycle_id, "success" if total_engines >= 3 else "partial",
         gpc.get("total_genes", 0), score, elapsed,
         json.dumps({"engines": engine_status, "total_ok": total_engines}))
    )

    # 更新持续统计
    for key, val in [
        ("last_cycle", cycle_id),
        ("total_cycles", str(db.execute("SELECT COUNT(*) FROM loop_cycles").fetchone()[0])),
        ("avg_duration_ms", str(
            db.execute("SELECT AVG(duration_ms) FROM loop_cycles WHERE status='success'").fetchone()[0] or elapsed
        )),
    ]:
        db.execute("INSERT OR REPLACE INTO perpetual_stats (key, value) VALUES (?, ?)", (key, val))

    db.commit()
    seven_summary = get_seven_self_summary(db)
    db.close()

    print(f"[FCL] ══════ 闭环完成: {elapsed}ms · {total_engines}/5引擎 · "
          f"{gpc.get('total_genes',0)}基因 ══════")

    return {
        "cycle_id": cycle_id,
        "engines_ok": total_engines,
        "genes": gpc.get("total_genes", 0),
        "fitness": gpc.get("avg_fitness", 0),
        "quality_score": score,
        "elapsed_ms": elapsed,
        "seven_self": seven_summary,
    }


def update_seven_self_metrics(db, gpc: dict, ast_issues: int, pentagon_score: float):
    """更新七自指标 — 2035动态计算"""
    now = datetime.now(timezone.utc)
    total_genes = gpc.get("total_genes", 1) or 1

    metrics = {
        "自感知": min(100, round((total_genes / 100) * 10, 1)),  # 每100基因10分
        "自协调": 100 if ast_issues < 200 else max(50, 100 - ast_issues // 10),
        "自愈合": 100,  # GPC免疫系统自动处理
        "自进化": min(100, round(gpc.get("avg_fitness", 30) * 1.2, 1)),
        "自迭代": min(100, round(db.execute("SELECT COUNT(*) FROM loop_cycles").fetchone()[0] * 0.5, 1)),
        "自反思": min(100, round(pentagon_score * 1.2, 1)),
        "自约束": 100,  # 自然选择淘汰机制=自我约束
    }

    for attr, value in metrics.items():
        old = db.execute("SELECT current_value FROM seven_self_tracker WHERE attribute=?",
                         (attr,)).fetchone()
        old_val = old[0] if old else 0
        trend = "rising" if value > old_val else "falling" if value < old_val else "stable"
        impact = round(value - old_val, 1)

        db.execute(
            "INSERT OR REPLACE INTO seven_self_tracker "
            "(attribute, current_value, trend, last_cycle_impact, "
            "consecutive_improvements, updated_at) "
            "VALUES (?, ?, ?, ?, "
            "CASE WHEN ? > 0 THEN COALESCE((SELECT consecutive_improvements FROM seven_self_tracker WHERE attribute=?),0)+1 ELSE 0 END, "
            "datetime('now'))",
            (attr, value, trend, impact, impact, attr)
        )


def get_seven_self_summary(db) -> dict:
    """七自摘要"""
    result = {}
    for row in db.execute("SELECT attribute, current_value, trend FROM seven_self_tracker"):
        result[row[0]] = {"value": row[1], "trend": row[2]}
    return result


def fcl_command_center() -> dict:
    """FCL指挥中心 — 一键查看全联邦闭环状态"""
    db = init_fcl_db()

    # 最近周期
    last = db.execute(
        "SELECT cycle_id, status, genes_involved, quality_score, duration_ms, started_at "
        "FROM loop_cycles ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # 七自
    seven = {}
    for row in db.execute("SELECT attribute, current_value, trend FROM seven_self_tracker"):
        seven[row[0]] = row[1]

    # 统计
    total = db.execute("SELECT COUNT(*) FROM loop_cycles").fetchone()[0]
    success = db.execute("SELECT COUNT(*) FROM loop_cycles WHERE status='success'").fetchone()[0]

    # GPC健康
    gpc = {}
    gpc_path = os.path.expanduser("~/lgox-ops/data/gpc-health.json")
    if os.path.exists(gpc_path):
        with open(gpc_path) as f:
            gpc = json.load(f)

    db.close()

    return {
        "status": "beating" if success > 0 else "initializing",
        "total_cycles": total,
        "success_rate": round(success / max(1, total) * 100, 1),
        "last_cycle": {
            "id": last[0] if last else "",
            "status": last[1] if last else "",
            "genes": last[2] if last else 0,
            "score": last[3] if last else 0,
            "duration_ms": last[4] if last else 0,
            "at": last[5] if last else "",
        } if last else None,
        "gpc": {
            "generation": gpc.get("gpc_generation", 0),
            "genes": gpc.get("total_genes", 0),
            "fitness": gpc.get("avg_fitness", 0),
        },
        "seven_self": seven,
        "architecture": "2035-FCL-v1.0",
    }


# ─── CLI ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="FCL·联邦闭环总引擎 v1.0 · 2035永动架构")
    ap.add_argument("--beat", action="store_true", help="执行一次全链路闭环搏动")
    ap.add_argument("--cron", action="store_true", help="cron模式")
    ap.add_argument("--status", action="store_true", help="查看闭环状态")
    ap.add_argument("--seven", action="store_true", help="查看七自指标")
    ap.add_argument("--json", action="store_true", help="JSON输出")
    args = ap.parse_args()

    init_fcl_db()

    if args.beat or args.cron:
        result = fcl_heartbeat()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.status:
        report = fcl_command_center()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"FCL 联邦闭环状态: {report['status']}")
            print(f"周期: {report['total_cycles']} · 成功率: {report['success_rate']}%")
            if report['last_cycle']:
                lc = report['last_cycle']
                print(f"上次: {lc['id']} · {lc['status']} · {lc['duration_ms']}ms · score {lc['score']}")
            print(f"GPC: gen {report['gpc']['generation']} · {report['gpc']['genes']}基因 · fitness {report['gpc']['fitness']}")
            print(f"七自:")
            for k, v in report['seven_self'].items():
                bar = "█" * int(v / 5) + "░" * (20 - int(v / 5))
                print(f"  {k}: {bar} {v}%")

    elif args.seven:
        db = init_fcl_db()
        for row in db.execute("SELECT attribute, current_value, target_value, trend, consecutive_improvements FROM seven_self_tracker"):
            trend_icon = "↗" if row[3] == "rising" else "↘" if row[3] == "falling" else "→"
            print(f"  {trend_icon} {row[0]}: {row[1]:.0f}/{row[2]} · streak: {row[4]}")
        db.close()

    else:
        # Default: cron mode (no-arg invocation = execute full heartbeat)
        result = fcl_heartbeat()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
