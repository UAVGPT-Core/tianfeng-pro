#!/usr/bin/env python3
"""
九层金字塔·智能体分层引擎 v1.0
═══════════════════════════════════════════════════════════
吸收ECC 5层30智能体 → 增强金字塔L3分析·L4规划·L5行动
每层智能体独立运行·联邦协同·七自闭环
═══════════════════════════════════════════════════════════
"""
import json, os, time
from datetime import datetime
from pathlib import Path

AGENT_DB = Path.home() / "lgox-ops" / "data" / "agent-layers.json"
AGENT_DB.parent.mkdir(parents=True, exist_ok=True)

# ═══ 五层30智能体·映射九层金字塔 ═══
AGENT_LAYERS = {
    "L3分析层": {
        "port": 8773,
        "desc": "多智能体分析层·四引擎统一查询·趋势追踪",
        "agents": {
            "analyzer":         {"role":"系统分析师","desc":"代码库结构分析·依赖关系·架构理解","model":"deepseek-v4-flash","trigger":"代码变更>10文件"},
            "trend-tracker":    {"role":"趋势追踪器","desc":"联邦健康指标趋势·异常检测·预测","model":"deepseek-v4-flash","trigger":"每小时"},
            "gene-evaluator":   {"role":"基因评估器","desc":"基因质量评分·fitness评估·去重","model":"qwen2.5:14b","trigger":"新基因>100条"},
            "cost-auditor":     {"role":"成本审计器","desc":"API调用成本追踪·熔断预警·优化建议","model":"deepseek-v4-flash","trigger":"每小时"},
            "health-monitor":   {"role":"健康监控器","desc":"节点心跳·服务可用性·飞轮状态","model":"deepseek-v4-flash","trigger":"每5min"},
            "radar-analyst":    {"role":"雷达分析师","desc":"外部雷达数据消化·趋势提取·优先级排序","model":"deepseek-v4-flash","trigger":"雷达扫描后"},
        }
    },
    
    "L4规划层": {
        "port": 8774,
        "desc": "规划调度层·圆桌会议·飞轮编排·路线规划",
        "agents": {
            "planner":          {"role":"总规划师","desc":"任务拆解·依赖分析·执行路线图","model":"deepseek-v4-pro","trigger":"新任务到达"},
            "architect":        {"role":"架构设计师","desc":"系统架构设计·技术选型·方案评审","model":"deepseek-v4-pro","trigger":"架构变更请求"},
            "scheduler":        {"role":"飞轮调度器","desc":"18飞轮编排·资源分配·冲突仲裁","model":"deepseek-v4-flash","trigger":"飞轮冲突检测"},
            "roundtable-host":  {"role":"圆桌主持","desc":"联邦discussion话题管理·共识收集·决议发布","model":"deepseek-v4-pro","trigger":"discussion创建"},
            "roadmap-keeper":   {"role":"路线守护","desc":"长期路线图跟踪·里程碑检查·偏差告警","model":"deepseek-v4-flash","trigger":"每日"},
            "resource-planner": {"role":"资源规划师","desc":"GPU/内存/API配额分配·成本优化","model":"deepseek-v4-flash","trigger":"资源使用>80%"},
        }
    },
    
    "L5行动层": {
        "port": 8775,
        "desc": "执行行动层·七自活体飞轮·达尔文进化引擎",
        "agents": {
            "code-reviewer":    {"role":"代码审查员","desc":"多维度代码审查·安全·性能·规范","model":"deepseek-v4-flash","trigger":"PR创建"},
            "security-reviewer":{"role":"安全审查员","desc":"OWASP检查·密钥泄露·依赖漏洞","model":"deepseek-v4-pro","trigger":"安全扫描"},
            "tdd-guide":        {"role":"TDD导师","desc":"测试驱动开发·红绿重构循环","model":"deepseek-v4-flash","trigger":"编码任务"},
            "build-error-resolver":{"role":"构建修复师","desc":"编译错误诊断·自动修复·回滚建议","model":"deepseek-v4-flash","trigger":"构建失败"},
            "e2e-runner":       {"role":"E2E测试员","desc":"端到端测试执行·回归检测·报告","model":"deepseek-v4-flash","trigger":"部署前"},
            "verification-loop":{"role":"验证闭环","desc":"代码→测试→部署→验证·全链闭环","model":"deepseek-v4-flash","trigger":"部署后"},
            "refactor-cleaner": {"role":"重构清理师","desc":"代码异味检测·重构建议·安全清理","model":"deepseek-v4-flash","trigger":"技术债务扫描"},
            "doc-updater":      {"role":"文档更新师","desc":"API文档·README·CHANGELOG自动更新","model":"deepseek-v4-flash","trigger":"API变更"},
            "loop-operator":    {"role":"永动操作员","desc":"飞轮循环维护·异常重试·状态恢复","model":"deepseek-v4-flash","trigger":"飞轮异常"},
            "harness-optimizer":{"role":"测试优化师","desc":"测试套件优化·覆盖率提升·速度优化","model":"deepseek-v4-flash","trigger":"测试>60s"},
            "evolution-driver": {"role":"进化驱动","desc":"基因突变·自然选择·适应度评估","model":"qwen2.5:14b","trigger":"基因周期"},
            "continuous-learner":{"role":"持续学习者","desc":"从飞轮反馈学习·策略优化·经验积累","model":"deepseek-v4-flash","trigger":"飞轮完成后"},
        }
    },
}

# ═══ 额外的规划层和执行层智能体(跨层协作) ═══
CROSS_LAYER_AGENTS = {
    "L1规划辅助": {
        "genesis-planner":  {"role":"起源规划","desc":"新项目初始化·模板生成·结构搭建"},
    },
    "L2执行辅助": {
        "patch-engineer":   {"role":"补丁工程师","desc":"批量代码修改·重构·迁移"},
        "merge-master":     {"role":"合并大师","desc":"冲突解决·分支合并·cherry-pick"},
    },
}

def get_all_agents():
    """获取全部智能体列表"""
    all_agents = {}
    for layer, info in AGENT_LAYERS.items():
        for name, agent in info["agents"].items():
            all_agents[f"{layer}/{name}"] = {
                **agent,
                "layer": layer,
                "port": info["port"],
                "name": name,
            }
    return all_agents

def save_agent_db():
    """保存智能体配置"""
    db = {
        "version": "1.0.0",
        "updated": datetime.now().isoformat(),
        "layers": AGENT_LAYERS,
        "cross_layer": CROSS_LAYER_AGENTS,
        "total_agents": sum(len(l["agents"]) for l in AGENT_LAYERS.values()),
        "pyramid_mapping": {
            "L3": "分析层·6智能体·趋势追踪·异常检测·成本审计",
            "L4": "规划层·6智能体·任务拆解·架构设计·资源规划",
            "L5": "行动层·12智能体·代码审查·测试·重构·进化",
        },
        "seven_self": {
            "自感知": "每智能体独立健康检查·心跳上报",
            "自协调": "智能体间任务队列·优先级仲裁",
            "自愈合": "智能体异常→自动重启·降级·告警",
            "自进化": "智能体从飞轮反馈学习·策略持续优化",
            "自迭代": "A/B测试智能体策略·择优升级",
            "自反思": "智能体执行后自评·质量回溯",
            "自约束": "宪法红线嵌入每个智能体·不可逾越",
        }
    }
    with open(AGENT_DB, "w") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    return db

def status():
    """智能体分层状态"""
    db = save_agent_db()
    print(f"╔══════════════════════════════════════╗")
    print(f"║  九层金字塔·智能体分层 v1.0        ║")
    print(f"║  吸收ECC·5层30智能体               ║")
    print(f"╚══════════════════════════════════════╝")
    print(f"\n总计: {db['total_agents']} 智能体 | 3层 | 端口:8773/8774/8775")
    
    for layer, info in AGENT_LAYERS.items():
        agents = info["agents"]
        print(f"\n{'='*50}")
        print(f"  {layer} (: {info['port']}) — {len(agents)}智能体")
        print(f"  {info['desc']}")
        print(f"{'='*50}")
        for name, agent in agents.items():
            print(f"  ├─ {agent['role']}")
            print(f"  │  {agent['desc']}")
            print(f"  │  模型:{agent['model']} | 触发:{agent['trigger']}")

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "status":
        status()
    elif cmd == "save":
        db = save_agent_db()
        print(f"✅ 智能体配置已保存: {AGENT_DB}")
        print(f"   层: {len(db['layers'])} | 智能体: {db['total_agents']}")
    elif cmd == "list":
        for name, agent in get_all_agents().items():
            print(f"  {name:40s} {agent['role']}")
    elif cmd == "layer":
        layer = sys.argv[2] if len(sys.argv) > 2 else "L3分析层"
        if layer in AGENT_LAYERS:
            for name, agent in AGENT_LAYERS[layer]["agents"].items():
                print(f"  {name}: {agent['role']} — {agent['desc']}")
    else:
        status()
