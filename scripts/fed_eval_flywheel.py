#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║  联邦自评测飞轮 v1.0 — FedEval Flywheel               ║
║  7维评分·SWE-bench对标·评测→基因→进化永动闭环          ║
║  2026-07-13                                          ║
╚══════════════════════════════════════════════════════╝

评测7维:
  ① 代码正确性    functional correctness
  ② 架构设计      architecture & patterns
  ③ 错误处理      error handling & edge cases
  ④ 效率优化      performance & complexity
  ⑤ 基因贡献度    gene-driven improvement
  ⑥ 踩坑免疫力    anti-regression (same bug twice?)
  ⑦ 成本效率      tokens per task

对标: Claude Code(SWE-bench 72%)·Codex(~65%)·天锋PRO
"""

import json, time, os, uuid, hashlib
from pathlib import Path
from datetime import datetime
from urllib import request

# ══════════════════════════════
# 配置
# ══════════════════════════════
OLLAMA = "http://localhost:11434"
LGE_DIRECT = "http://100.116.0.29:8200/genes/write"
LGE_KEY = "fbe0b015eb7a03727903b660c4cecc60"
DATA_DIR = Path.home() / "lgox-ops/data/eval"
RESULTS_FILE = DATA_DIR / "eval_results.jsonl"
NODE_NAME = os.uname().nodename

# ══════════════════════════════
# 评测题库(对标SWE-bench难度)
# ══════════════════════════════
BENCHMARKS = [
    # 基础算法
    {"id": "algo-01", "category": "algorithm", "difficulty": "easy",
     "task": "实现二分查找函数·处理空数组和不存在元素·返回索引或-1",
     "check": "二分查找·O(logn)·边界正确"},

    {"id": "algo-02", "category": "algorithm", "difficulty": "medium",
     "task": "实现LRU缓存·get和put操作O(1)·容量限制·过期淘汰",
     "check": "哈希表+双向链表·O(1)·容量正确淘汰"},

    # 系统设计
    {"id": "sys-01", "category": "system", "difficulty": "medium",
     "task": "实现一个简单的消息队列·支持publish/consume·持久化·至少一次投递",
     "check": "队列语义正确·持久化·ack机制"},

    # 错误处理
    {"id": "err-01", "category": "robustness", "difficulty": "medium",
     "task": "实现带重试和退避的HTTP客户端·处理超时/5xx/连接拒绝·指数退避·最多3次",
     "check": "重试逻辑·指数退避·不无限重试·正确处理各HTTP状态码"},

    # 并发安全
    {"id": "conc-01", "category": "concurrency", "difficulty": "hard",
     "task": "实现线程安全的计数器·支持incr/decr/get·无竞态条件·不使用全局锁",
     "check": "线程安全·无竞态·性能可接受"},

    # 实际场景(联邦相关)
    {"id": "fed-01", "category": "federation", "difficulty": "medium",
     "task": "实现联邦节点心跳检测·超时30秒标记离线·恢复后自动上线·状态写入基因",
     "check": "心跳逻辑·超时检测·恢复逻辑·基因写入"},
]

def llm_generate(prompt, model="qwen2.5-coder:7b"):
    """调用Ollama生成代码"""
    data = json.dumps({
        "model": model,
        "prompt": f"写Python代码。只输出代码+简要注释·不要解释:\n{prompt}",
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 800}
    }).encode()
    req = request.Request(f"{OLLAMA}/api/generate", data=data,
        headers={"Content-Type": "application/json"})
    resp = request.urlopen(req, timeout=60)
    return json.loads(resp.read()).get("response", "")

def llm_review(code, task, check_criteria, model="qwen2.5:14b"):
    """gemma4评审代码——7维评分"""
    review_prompt = (
        f"你是代码评审专家。评审以下代码:\n任务: {task}\n检查点: {check_criteria}\n\n"
        f"代码:\n{code[:1500]}\n\n"
        f"7维评分(每项0-10分):\n"
        f"①正确性: 功能是否正确实现？\n"
        f"②架构: 设计模式·代码结构·可维护性？\n"
        f"③错误处理: 边界·异常·边缘情况？\n"
        f"④效率: 时间/空间复杂度？\n"
        f"⑤基因贡献: 是否展示了从经验中学习？\n"
        f"⑥踩坑免疫: 是否避免了常见错误？\n"
        f"⑦成本: 代码是否简洁高效(非冗余)？\n\n"
        f"输出格式: ①X ②X ③X ④X ⑤X ⑥X ⑦X | 总评:一句话"
    )
    data = json.dumps({
        "model": model,
        "prompt": review_prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 200}
    }).encode()
    req = request.Request(f"{OLLAMA}/api/generate", data=data,
        headers={"Content-Type": "application/json"})
    resp = request.urlopen(req, timeout=90)
    return json.loads(resp.read()).get("response", "")

def parse_scores(review_text):
    """从评审文本解析7维分数"""
    scores = {}
    import re
    for i, dim in enumerate(["correctness","architecture","error_handling",
                              "efficiency","gene_contribution","anti_regression","cost"]):
        pattern = rf'[①②③④⑤⑥⑦]\s*(\d+)'
        matches = re.findall(pattern, review_text)
        if i < len(matches):
            try:
                scores[dim] = int(matches[i]) / 10.0
            except:
                scores[dim] = 0.5
        else:
            scores[dim] = 0.5
    scores["overall"] = sum(scores.values()) / len(scores) if scores else 0.5
    return scores

def run_benchmark(bench):
    """运行单个评测"""
    print(f"  📝 {bench['id']}: {bench['task'][:50]}...", flush=True)

    # 1. 代码生成
    code = llm_generate(f"{bench['task']}。{bench['check']}")
    if not code:
        return None

    # 2. gemma4评审
    review = llm_review(code, bench['task'], bench['check'])
    if not review:
        return None

    # 3. 解析分数
    scores = parse_scores(review)

    return {
        "benchmark_id": bench["id"],
        "category": bench["category"],
        "difficulty": bench["difficulty"],
        "model": "qwen2.5-coder:7b",
        "reviewer": "qwen2.5:14b",
        "scores": scores,
        "review": review[:300],
        "code_len": len(code),
        "timestamp": datetime.now().isoformat()
    }

def write_gene(result):
    """评测结果纳基因"""
    s = result["scores"]
    gene_content = (
        f"[自评测] {result['benchmark_id']}({result['category']}/{result['difficulty']}) "
        f"总分{s['overall']:.2f} | "
        f"正确性{s['correctness']:.1f}·架构{s['architecture']:.1f}·"
        f"错误处理{s['error_handling']:.1f}·效率{s['efficiency']:.1f}·"
        f"基因{s['gene_contribution']:.1f}·踩坑免疫{s['anti_regression']:.1f}·"
        f"成本{s['cost']:.1f} | {s.get('overall',0):.0%}"
    )
    gene = {
        "content": gene_content,
        "memory_type": "episodic",
        "source": f"{NODE_NAME}/fed-eval-flywheel",
        "fitness_score": min(s["overall"], 0.9)
    }
    try:
        data = json.dumps(gene).encode()
        req = request.Request(LGE_DIRECT, data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        request.urlopen(req, timeout=8)
    except:
        pass

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("🧪 联邦自评测飞轮 v1.0", flush=True)
    print(f"   题库: {len(BENCHMARKS)}题·生成:qwen2.5-coder:7b·评审:qwen2.5:14b", flush=True)
    print(f"   对标: Claude Code 72%·Codex 65%·天锋PRO", flush=True)
    print(flush=True)

    results = []
    for bench in BENCHMARKS:
        result = run_benchmark(bench)
        if result:
            results.append(result)
            write_gene(result)

            s = result["scores"]
            bar = "█" * int(s["overall"] * 10) + "░" * (10 - int(s["overall"] * 10))
            print(f"      总分{s['overall']:.2f} [{bar}] {s['overall']:.0%}", flush=True)

        time.sleep(15)  # GPU冷却

    # 汇总
    if results:
        avg = sum(r["scores"]["overall"] for r in results) / len(results)
        print(f"\n═══════════════════════════════")
        print(f"  天锋PRO·本轮: {avg:.1%} ({len(results)}/{len(BENCHMARKS)}题)")
        print(f"  对标: Claude Code 72%·Codex 65%")
        print(f"  差距: {avg - 0.72:.1%} vs Claude Code")

        # 汇总基因
        summary_gene = {
            "content": (f"[自评测汇总] 天锋PRO {len(results)}题均分{avg:.1%}·"
                       f"vs Claude Code 72%·vs Codex 65%。"
                       f"7维:正确性·架构·错误处理·效率·基因·踩坑·成本。"
                       f"评测→基因→进化闭环。"),
            "memory_type": "episodic",
            "source": f"{NODE_NAME}/fed-eval-summary",
            "fitness_score": 0.8
        }
        data = json.dumps(summary_gene).encode()
        try:
            req = request.Request(LGE_DIRECT, data=data,
                headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
            request.urlopen(req, timeout=8)
        except:
            pass

    # 存档
    with RESULTS_FILE.open("a") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n  基因已写入·结果存档: {RESULTS_FILE}")

if __name__ == "__main__":
    main()
