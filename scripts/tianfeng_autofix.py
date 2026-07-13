#!/usr/bin/env python3
"""
天锋PRO 自动修复引擎 — 生成→测试→失败→反思→修复→再测试
==========================================================
2035视角: 真正的AI程序员不是一次生成对的，而是能从错误中学习。
这个引擎让天锋PRO拥有了Claude Code和Codex都没有的能力: 自我修复。

闭环: CodeGen → Sandbox → Fail? → Reflect → Fix → Retest → Pass → Gene
每修复一次 = 一条基因 = 下次不再犯同样错误

指数优势: Claude Code/Codex生成错误代码只能靠用户反馈，天锋PRO自动修复。
"""

import os, sys, json, time, re
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from code_sandbox import Sandbox
from tianfeng_pyramid_align import constitution_check


def auto_fix(task, language="python", max_attempts=3):
    """
    自动修复循环
    1. 生成代码
    2. 沙箱测试
    3. 如果失败 → 反思分析 → 修复 → 重新测试
    4. 最多max_attempts次
    5. 成功/失败都纳基因
    """
    from tianfeng_code_brain import generate_code, call_model, write_gene, verify_code, score_code

    log_entries = []
    sandbox = Sandbox(timeout=15)

    for attempt in range(1, max_attempts + 1):
        entry = {"attempt": attempt, "time": datetime.now().isoformat()}

        if attempt == 1:
            # 首次生成
            result = generate_code(task, language)
            code = result.get("code", "")
            entry["action"] = "generate"
        else:
            # 修复模式: 把错误和原始代码一起发给模型
            fix_prompt = f"""以下代码有错误，请修复。

原始任务: {task}

当前代码:
```{language}
{code}
```

错误信息:
{error_info}

请修复这些问题并输出修正后的完整代码。只输出代码块。"""

            try:
                resp = call_model("coder", fix_prompt, temp=0.1)
                blocks = re.findall(r'```(\w*)\n(.*?)```', resp, re.DOTALL)
                code = blocks[0][1].strip() if blocks else resp.strip()
                entry["action"] = "fix"
                entry["fix_response"] = resp[:200]
            except Exception as e:
                entry["action"] = "fix_failed"
                entry["error"] = str(e)
                log_entries.append(entry)
                break

        # 验证
        verification = verify_code(code, language)
        entry["compile"] = verification.get("compile")

        if verification.get("compile") == "fail":
            error_info = "; ".join(verification.get("errors", ["unknown"]))
            entry["status"] = "compile_failed"
            entry["error"] = error_info[:200]
            log_entries.append(entry)
            continue

        # 沙箱运行测试
        sb = Sandbox()
        tests = sb.generate_tests(code)
        sb_result = sb.run(code, tests)
        entry["sandbox_score"] = sb_result.get("score", 0)
        entry["sandbox_passed"] = sb_result.get("passed", False)
        entry["test_summary"] = sb_result.get("test_summary", "?")

        if sb_result.get("passed") and sb_result.get("score", 0) >= 60:
            entry["status"] = "success"
            # 成功纳基因
            write_gene(
                f"[AutoFix] {task[:60]} | attempts={attempt} | score={sb_result['score']} | lang={language}",
                "procedural"
            )
            log_entries.append(entry)
            break
        else:
            error_info = json.dumps(sb_result.get("details", []))[:300]
            entry["status"] = "test_failed"
            entry["error"] = error_info
            log_entries.append(entry)
            continue

    # 汇总
    final_entry = log_entries[-1]
    success = final_entry.get("status") == "success"
    final_score = final_entry.get("sandbox_score", 0)

    # 即使最终失败也纳基因（踩坑记录）
    if not success:
        write_gene(
            f"[AutoFix-FAIL] {task[:60]} | attempts={attempt} | best_score={final_score}",
            "semantic"
        )

    return {
        "task": task,
        "success": success,
        "attempts": len(log_entries),
        "final_score": final_score,
        "log": log_entries,
        "gene_impact": "success_pattern" if success else "pitfall_learned",
    }


def benchmark_suite():
    """
    基准测试套件 — 对标HumanEval的可重复测试
    """
    benchmarks = [
        # 算法
        {"id": "HE-001", "task": "写一个函数判断整数是否是2的幂", "tests": [
            {"input": "1", "expected": "True"}, {"input": "2", "expected": "True"},
            {"input": "3", "expected": "False"}, {"input": "16", "expected": "True"},
        ]},
        {"id": "HE-002", "task": "实现二分查找,返回索引,未找到返回-1", "tests": [
            {"input": "[1,2,3,4,5]\\n3", "expected": "2"},
            {"input": "[1,2,3,4,5]\\n6", "expected": "-1"},
        ]},
        {"id": "HE-003", "task": "判断字符串是否是回文,忽略大小写和标点", "tests": [
            {"input": "A man a plan a canal Panama", "expected": "True"},
            {"input": "hello", "expected": "False"},
        ]},
        # 数据结构
        {"id": "DS-001", "task": "实现LRU缓存的get和put方法,O(1)时间", "tests": [
            {"input": "put a 1\\nget a", "expected": "1"},
        ]},
        {"id": "DS-002", "task": "用两个栈实现队列,push和pop操作", "tests": [
            {"input": "push 1\\npush 2\\npop", "expected": "1"},
        ]},
        # 设计模式
        {"id": "DP-001", "task": "实现线程安全的单例模式", "tests": [
            {"input": "create", "expected": ""},
        ]},
    ]
    return benchmarks


def run_benchmark(model="coder", rounds=1):
    """
    运行基准测试套件
    输出: 通过率、均分、与Claude Code/Codex对比
    """
    from tianfeng_code_brain import generate_code, verify_code, score_code
    sandbox = Sandbox(timeout=15)

    benchmarks = benchmark_suite()
    results = []

    for bm in benchmarks:
        for r in range(rounds):
            result = generate_code(bm["task"])
            code = result.get("code", "")
            if not code:
                results.append({"id": bm["id"], "passed": False, "score": 0, "error": "no_code"})
                continue

            sb_result = sandbox.run(code, bm.get("tests", []))
            results.append({
                "id": bm["id"],
                "task": bm["task"][:40],
                "passed": sb_result.get("passed", False),
                "score": sb_result.get("score", 0),
                "test_summary": sb_result.get("test_summary", "0/0"),
                "model": result.get("model", "?"),
            })

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    avg_score = sum(r["score"] for r in results) / total if total > 0 else 0

    return {
        "benchmark": "Tianfeng-Bench V1",
        "total": total,
        "passed": passed,
        "pass_rate": f"{passed}/{total} ({round(passed/total*100,1)}%)",
        "avg_score": round(avg_score, 1),
        "results": results,
        "comparison": {
            "claude_code_estimated": "90-95%",
            "codex_estimated": "85-90%",
            "tianfeng_current": f"{round(passed/total*100,1)}%",
            "target_90days": "95%+",
        },
    }


# ========== CLI ==========

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "bench"

    if cmd == "fix":
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Task: ")
        result = auto_fix(task)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result.get("success"):
            print(f"\n✅ 自动修复成功! {result['attempts']}次尝试·最终评分:{result['final_score']}")

    elif cmd == "bench":
        print("运行基准测试套件...")
        result = run_benchmark()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "benchmark-list":
        for bm in benchmark_suite():
            print(f"  {bm['id']}: {bm['task'][:50]}")
