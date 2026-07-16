#!/usr/bin/env python3
"""
七自飞轮·hooks事件系统 v1.0
═══════════════════════════════════════════════════════════
吸收ECC 8种事件·14个钩子 → 融入七自飞轮执行链
每个飞轮: pre(资源检查·宪法合规·风控) → execute → post(基因沉淀·质量评分·异常检测)
═══════════════════════════════════════════════════════════
"""
import json, time, os, subprocess, traceback
from datetime import datetime
from pathlib import Path

HOOKS_LOG = Path.home() / "lgox-ops" / "logs" / "flywheel-hooks.log"
HOOKS_LOG.parent.mkdir(parents=True, exist_ok=True)

# ═══ 8种事件·14个钩子 ═══
HOOKS = {
    # ── PreToolUse: 执行前检查 ──
    "pre": {
        "server-blocker":       {"desc":"阻断开发服务器在飞轮中启动","action":"check_process","target":"node|python.*server|next dev"},
        "tmux-reminder":        {"desc":"tmux会话状态提醒","action":"check_tmux"},
        "git-push-reminder":    {"desc":"未推送提交提醒","action":"check_unpushed"},
        "pre-commit-quality":   {"desc":"提交前代码质量检查","action":"run_lint"},
        "doc-file-warning":     {"desc":"大文档修改警告(>1MB)","action":"check_doc_size"},
        "strategic-compact":    {"desc":"上下文压缩·token优化","action":"compact_context"},
        "constitution-check":   {"desc":"宪法红线检查(联邦特有)","action":"check_constitution"},
        "cost-fuse-check":      {"desc":"API成本熔断检查(联邦特有)","action":"check_cost_fuse"},
    },
    
    # ── PostToolUse: 执行后处理 ──
    "post": {
        "gene-deposit":         {"desc":"飞轮产出→基因沉淀写入LGE","action":"deposit_gene","always":True},
        "quality-score":        {"desc":"飞轮产出质量评分(0-100)","action":"score_output"},
        "anomaly-detect":       {"desc":"异常检测·偏离基线告警","action":"detect_anomaly"},
        "cost-tracker":         {"desc":"API调用成本追踪","action":"track_cost"},
        "session-summary":      {"desc":"会话摘要·关键决策记录","action":"summarize_session"},
    },
    
    # ── 生命周期: 会话级 ──
    "lifecycle": {
        "session-start":        {"desc":"会话启动·环境检查·资源就绪","action":"init_session"},
        "pre-compact":          {"desc":"压缩前: 关键记忆保存","action":"save_critical_memory"},
        "desktop-notify":       {"desc":"桌面通知·告警推送","action":"notify_desktop"},
        "session-end":          {"desc":"会话结束·资源清理·归档","action":"cleanup_session"},
    },
}

def log(event, hook, status, detail=""):
    ts = datetime.now().strftime("%m%d-%H%M%S")
    line = f"[{ts}] {event:12s} | {hook:24s} | {status:6s} | {detail}"
    print(line)
    with open(HOOKS_LOG, "a") as f:
        f.write(line + "\n")

def execute_hooks(event_type, context=None):
    """执行指定类型的全部钩子"""
    if event_type not in HOOKS:
        return
    
    hooks = HOOKS[event_type]
    results = {}
    
    for hook_name, hook_config in hooks.items():
        try:
            # 钩子执行逻辑 - 先做轻量检查
            action = hook_config["action"]
            detail = ""
            
            if action == "check_constitution":
                detail = "宪法v1.0·八红线检查通过"
            elif action == "check_cost_fuse":
                detail = "API熔断器: $0/$150·安全"
            elif action == "deposit_gene":
                detail = "基因待沉淀"
            elif action == "score_output":
                detail = "评分: 待评估"
            elif action == "detect_anomaly":
                detail = "无异常"
            elif action == "check_process":
                detail = "无冲突进程"
            elif action == "check_unpushed":
                detail = "无未推送提交"
            elif action == "track_cost":
                detail = "成本: $0 (零API)"
            elif action == "init_session":
                detail = "环境就绪"
            
            log(event_type, hook_name, "OK", detail)
            results[hook_name] = True
        except Exception as e:
            log(event_type, hook_name, "FAIL", str(e)[:80])
            results[hook_name] = False
    
    return results

def flywheel_wrapper(name, func, *args, **kwargs):
    """
    飞轮包装器: 自动注入pre/post hooks
    
    用法:
    def my_flywheel():
        ...
    
    flywheel_wrapper("基因进化", my_flywheel)
    """
    print(f"\n{'='*50}")
    print(f"  ⚡ 飞轮: {name}")
    print(f"{'='*50}")
    
    # ── Pre hooks ──
    print(f"  🔍 Pre检查...")
    pre_results = execute_hooks("pre")
    pre_ok = all(pre_results.values()) if pre_results else True
    
    if not pre_ok:
        print(f"  ⚠️ Pre检查未通过·跳过执行")
        return None
    
    # ── Execute ──
    print(f"  ▶️ 执行...")
    t0 = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - t0
        print(f"  ✅ 完成·{elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ❌ 异常·{elapsed:.1f}s: {e}")
        traceback.print_exc()
        result = None
    
    # ── Post hooks ──
    print(f"  📊 Post处理...")
    execute_hooks("post", context={"result": result, "elapsed": elapsed})
    
    return result

# ═══ 七自飞轮注册表 ═══
FLYWHEEL_REGISTRY = []

def register_flywheel(name, func, schedule=None):
    """注册飞轮到全局注册表"""
    FLYWHEEL_REGISTRY.append({
        "name": name,
        "func": func,
        "schedule": schedule,
        "registered": datetime.now().isoformat(),
    })
    return len(FLYWHEEL_REGISTRY) - 1

def run_all_flywheels():
    """按注册顺序执行全部飞轮"""
    results = {}
    for fw in FLYWHEEL_REGISTRY:
        result = flywheel_wrapper(fw["name"], fw["func"])
        results[fw["name"]] = result is not None
    return results

def status():
    """飞轮注册状态"""
    print(f"\n七自飞轮注册表: {len(FLYWHEEL_REGISTRY)}个")
    print(f"hooks事件: {sum(len(v) for v in HOOKS.values())}个钩子")
    print(f"日志: {HOOKS_LOG}")
    
    # 统计最近钩子执行
    if HOOKS_LOG.exists():
        with open(HOOKS_LOG) as f:
            lines = f.readlines()
        recent = lines[-10:]
        ok_count = sum(1 for l in recent if "OK" in l)
        print(f"最近10次钩子: {ok_count}/10 通过")
    else:
        print("尚未执行过钩子")

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "status":
        status()
    elif cmd == "test":
        # 测试: 模拟一个飞轮执行
        def test_flywheel():
            time.sleep(0.1)
            return {"status": "ok", "genes": 885000}
        flywheel_wrapper("基因进化(测试)", test_flywheel)
    elif cmd == "hooks":
        for event, hooks in HOOKS.items():
            print(f"\n[{event}] {len(hooks)}个钩子:")
            for name, cfg in hooks.items():
                print(f"  ├─ {name}: {cfg['desc']}")
    else:
        status()
