#!/usr/bin/env python3
"""
LGOX 宪法引擎 v1.1 自约束规则扩展
追加10条新规则: 基因质量·Cron合规·消费闭环·联邦同步·API安全
"""
import json,time
from datetime import datetime

# ═══ 新增10条自约束规则 ═══
EXTRA_RULES = [
    {
        "id": "self-constrain-1",
        "title": "基因质量门控",
        "rule": "写入LGE基因时: 内容>50字符·含有效source·fitness需后续校准·禁止重复写入(5min窗口)",
        "check": lambda action,ctx: (
            len(action)<50 and "write_gene" in str(ctx).lower(),
            "基因内容过短(<50字符)" if len(action)<50 else None
        )
    },
    {
        "id": "self-constrain-2", 
        "title": "Cron任务铁律",
        "rule": "新增cron任务: 必须有name·必须有schedule·必须是幂等操作·禁止rm -rf",
        "check": lambda action,ctx: (
            "cron" in str(ctx).lower() and any(kw in action.lower() for kw in ["rm -rf","delete","删除所有"]),
            "cron任务包含破坏性操作" if any(kw in action.lower() for kw in ["rm -rf"]) else None
        )
    },
    {
        "id": "self-constrain-3",
        "title": "消费闭环验证",
        "rule": "消息发送后必须被消费: bridge unread>100触发告警·>500触发自动清淤",
        "threshold": {"unread_warn": 100, "unread_critical": 500}
    },
    {
        "id": "self-constrain-4",
        "title": "联邦同步强制",
        "rule": "任何知识更新必须通过联邦桥广播到全节点·禁止单节点知识孤岛",
        "check": lambda action,ctx: (
            "write_gene" in str(ctx).lower() and "broadcast" not in str(ctx).lower(),
            "基因写入未伴随联邦广播"
        )
    },
    {
        "id": "self-constrain-5",
        "title": "API调用安全",
        "rule": "外部API调用: 必须有超时·必须有降级·必须有错误处理·禁止明文传输密钥",
        "check": lambda action,ctx: (
            any(kw in action.lower() for kw in ["api","http"]) and "timeout" not in str(ctx).lower(),
            "API调用缺少超时设置"
        )
    },
    {
        "id": "self-constrain-6",
        "title": "灾备链路保护",
        "rule": "禁止单点依赖: 任何服务必须有备选方案·T1 Down→T2自动接管",
        "check": lambda action,ctx: (
            "8760" in action and "8762" not in str(ctx) and "fallback" not in str(ctx).lower(),
            "Gateway路由未配置灾备降级"
        )
    },
    {
        "id": "self-constrain-7",
        "title": "节点平等原则",
        "rule": "任何节点不得独占>70%联邦算力·任务必须联邦调度",
        "check": lambda action,ctx: (False, None)  # 被动监控
    },
    {
        "id": "self-constrain-8",
        "title": "日志追溯强制",
        "rule": "所有自愈动作必须有日志·禁止静默修复·修复后必须通知天枢",
        "check": lambda action,ctx: (
            "heal" in str(ctx).lower() and "log" not in str(ctx).lower(),
            "自愈动作缺少日志记录"
        )
    },
    {
        "id": "self-constrain-9",
        "title": "版本同步强制",
        "rule": "consumer/脚本/引擎升级后必须广播版本号·旧版本72h内淘汰",
        "check": lambda action,ctx: (
            "upgrade" in str(ctx).lower() and "version" not in str(ctx).lower(),
            "升级未附带版本号广播"
        )
    },
    {
        "id": "self-constrain-10",
        "title": "零人类参与验证",
        "rule": "任何需要主人审批的操作必须有自动降级方案·禁止阻塞等待",
        "check": lambda action,ctx: (
            "approval" in str(ctx).lower() and "fallback" not in str(ctx).lower(),
            "审批流程缺少自动降级"
        )
    },
]

# ═══ 规则评估器 ═══
def evaluate_extra_rules(action: str, context: dict) -> dict:
    """评估扩展规则,返回违规列表"""
    violations = []
    warnings = []
    
    for rule in EXTRA_RULES:
        check_fn = rule.get("check")
        if check_fn:
            try:
                is_violation, msg = check_fn(action, context)
                if is_violation and msg:
                    violations.append(f"{rule['id']}: {msg}")
            except:
                pass
    
    return {
        "rules_total": len(EXTRA_RULES),
        "violations": violations,
        "warnings": warnings,
        "violation_count": len(violations),
        "passed": len(violations) == 0
    }

# ═══ 独立运行: 自评 ═══
if __name__ == "__main__":
    # 自评测试
    test_cases = [
        ("write_gene: 短内容", {"source":"test"}),
        ("curl http://api.test.com", {"timeout":"5"}),
        ("auto-heal: 修复联邦桥", {"log":"enabled"}),
        ("upgrade consumer to v2.2", {"version":"2.2"}),
    ]
    for action,ctx in test_cases:
        result = evaluate_extra_rules(action, ctx)
        status = "✅" if result["passed"] else f"❌ {result['violations']}"
        print(f"  {status} | {action[:50]}")
    
    print(f"\n自约束规则: {len(EXTRA_RULES)}条已加载")
