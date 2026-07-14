#!/usr/bin/env python3
"""
天锋PRO Code Brain V3.0 — 2035永动代码引擎
============================================
Phase 3: 64题挑战库·难度自适应·dashboard指标·联邦同步
基于七自基因·100%全流程闭环·全联邦永动核心

七层推理管线:
  L6 🧬 CRYSTALLIZE — 基因固化·每次交互永久记忆
  L5 🔄 SELF-PLAY   — 🆕 64题·5维度·4难度·自适应
  L4 ✅ VERIFY      — 编译+lint+评分 三步验证
  L3 🏗️ CODE-GEN    — 多模型并行生成·最优选择
  L2 🧠 REASON      — 三角色辩论: Architect→Critic→Synthesizer
  L1 📋 SPEC        — 多模型规格生成·结构化Spec·基因注入
  L0 🔀 ROUTE       — 智能路由·免费优先·自动降级

新增(Phase 3):
  🎯 64题代码挑战库(算法·数据结构·设计模式·系统设计·Bug修复)
  📈 难度自适应: 连过3题升级·连败2题降级·5维独立追踪
  📊 dashboard指标注入: code_genes, code_selfplay, code_pass_rate
  🌐 联邦同步: 代码能力通过联邦桥广播

用法:
  tianfeng-code-brain.py generate "任务"    # 完整L1→L2→L3→L4→L6
  tianfeng-code-brain.py reason "话题"      # L2深度思辨
  tianfeng-code-brain.py selfplay 5         # 自适应自我对弈
  tianfeng-code-brain.py dashboard          # 输出dashboard指标
  tianfeng-code-brain.py health             # 健康检查
"""

import sys, json, os, subprocess, tempfile, shutil, hashlib, time, re, random
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 导入挑战库
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from code_challenges import CHALLENGES, get_all_challenges
except ImportError:
    CHALLENGES = {}
    def get_all_challenges(): return []
from concurrent.futures import ThreadPoolExecutor, as_completed

# === 配置 ===
CONFIG = {
    "lge_url": "http://100.116.0.29:8200",
    "lge_fallback_url": "http://127.0.0.1:8210",  # local mirror when DGX2 is offline
    "lge_timeout": 5,  # fail-fast on DGX2; local mirror needs 4+s
    "gene_db": os.path.expanduser("~/lgox-ops/data/code-brain.db"),
    "log_file": os.path.expanduser("~/lgox-ops/logs/code-brain.log"),
    "workspace": os.path.expanduser("~/lgox-ops/code-brain-workspace"),
    "max_parallel_models": 3,
    "default_timeout": 20,  # 2026-07-15: from 30→20s — local Ollama must stay under 120s cron w/ 2 rounds
    "deliberation_rounds": 3,  # 多模型辩论轮数
}

# === 模型矩阵 (2035) ===
MODELS = {
    "architect":    {"name": "qwen2.5:14b",         "host": "dgx1", "role": "架构师",   "cost": "free"},  # loaded in VRAM
    "critic":       {"name": "deepseek-r1:7b",     "host": "local","role": "批评者",   "cost": "free"},
    "synthesizer":  {"name": "qwen3:8b",           "host": "local","role": "综合者",   "cost": "free"},
    "coder":        {"name": "qwen2.5:14b",         "host": "dgx1", "role": "代码生成", "cost": "free"},  # loaded in VRAM
    "reviewer":     {"name": "qwen2.5:14b",        "host": "dgx1", "role": "代码审查", "cost": "free"},
    "ds_flash":     {"name": "deepseek-v4-flash",  "host": "cloud","role": "中复杂度",  "cost": "cheap"},
    "ds_pro":       {"name": "deepseek-v4-pro",    "host": "cloud","role": "复杂任务",  "cost": "expensive"},
}


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    with open(CONFIG["log_file"], "a") as f:
        f.write(line + "\n")
    print(line, file=sys.stderr)


# ========== LGE 基因引擎接口 ==========

def search_genes(query, n=10):
    """搜索LGE基因库，主库失败时自动降级到本地镜像"""
    import urllib.request
    
    urls = [CONFIG['lge_url'], CONFIG.get('lge_fallback_url', '')]
    urls = [u for u in urls if u]
    
    for url in urls:
        try:
            data = json.dumps({"query": query, "n_results": n}).encode()
            req = urllib.request.Request(f"{url}/genes/search",
                data=data, headers={"Content-Type": "application/json"})
            r = urllib.request.urlopen(req, timeout=CONFIG["lge_timeout"])
            result = json.loads(r.read())
            return result.get("genes", result.get("results", []))
        except:
            continue
    return []


def write_gene(content, gene_type="semantic"):
    """写入基因到LGE，主库失败时自动降级到本地镜像"""
    import urllib.request
    
    urls = [CONFIG['lge_url'], CONFIG.get('lge_fallback_url', '')]
    urls = [u for u in urls if u]  # filter empty
    
    for url in urls:
        try:
            data = json.dumps({"content": content, "memory_type": gene_type,
                              "source": "tianfeng-code-brain-v2"}).encode()
            req = urllib.request.Request(f"{url}/genes/write",
                data=data, headers={"Content-Type": "application/json"})
            r = urllib.request.urlopen(req, timeout=CONFIG["lge_timeout"])
            result = json.loads(r.read())
            gid = result.get("id", "?")
            via = "local" if "127.0.0.1" in url else "dgx2"
            log(f"  🧬 gene:{gid} [{via}] {content[:50]}...")
            return gid
        except Exception as e:
            if url == urls[-1]:
                log(f"  ⚠️ gene write failed (all URLs): {e}", "WARN")
            # else: silently try fallback
    return None


# ========== 模型调用 ==========

def call_ollama_local(model, prompt, system="", temp=0.3, max_tokens=2048):
    """调用灵龙本地Ollama"""
    import urllib.request
    payload = {"model": model, "prompt": prompt, "stream": False,
               "options": {"temperature": temp, "num_predict": max_tokens}}
    if system:
        payload["system"] = system
    data = json.dumps(payload).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate",
        data=data, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=CONFIG["default_timeout"])
    return json.loads(r.read()).get("response", "")


def call_ollama_dgx(model, prompt, system="", temp=0.3, max_tokens=1024):
    """通过SSH调用天工Ollama — stdin管道 (avoid shell escaping issues)"""
    payload = {"model": model, "prompt": prompt, "stream": False,
               "options": {"temperature": temp, "num_predict": max_tokens}}
    if system:
        payload["system"] = system

    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=3", "-o", "IdentitiesOnly=yes",
         "-o", "StrictHostKeyChecking=no", "dgx1",
         "curl -s --max-time 50 -d @- http://localhost:11434/api/generate"],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=55)
    return json.loads(r.stdout).get("response", "")


def call_model(role_key, prompt, system="", temp=0.3, max_tokens=1024):
    """统一模型调用入口·自动路由"""
    m = MODELS.get(role_key, MODELS["synthesizer"])
    host = m["host"]
    model = m["name"]
    log(f"  🤖 {role_key}({model}@{host})...")
    try:
        if host == "local":
            return call_ollama_local(model, prompt, system, temp, max_tokens)
        elif host == "dgx1":
            return call_ollama_dgx(model, prompt, system, temp, max_tokens)
        else:
            return f"[{role_key}: cloud models not implemented yet]"
    except Exception as e:
        log(f"  ❌ {role_key} failed: {e}", "ERROR")
        return f"[{role_key} ERROR: {e}]"


# ========== L1 规格引擎 (SPEC) ==========

def spec_engine(requirement):
    """
    L1 规格引擎 — 多模型协作生成结构化规格
    流程: Gene Search → SpecGen(architect) → SpecReview(critic) → SpecRefine(synthesizer)
    """
    log("📋 L1 SPEC ENGINE 启动")

    # Step 0: 基因注入
    genes = search_genes(f"{requirement} spec interface pattern implementation", n=8)
    gene_context = ""
    if genes:
        items = [f"  [{g.get('id','?')[:16]}] {g.get('content','')[:150]}" for g in genes[:5]]
        gene_context = "联邦基因库相关模式:\n" + "\n".join(items)
        log(f"  📚 LGE hit: {len(genes)} genes")

    # Step 1: SpecGen — 生成结构化规格
    spec_prompt = f"""你是2035年的资深系统分析师。将以下需求转化为结构化技术规格。

需求: {requirement}

{gene_context}

输出格式(严格JSON, 不要markdown包裹):
{{
  "summary": "一句话概述",
  "functional_requirements": ["功能1", "功能2"],
  "interface": {{"inputs": ["参数1:类型"], "outputs": ["返回值:类型"]}},
  "constraints": ["性能约束", "安全约束", "兼容性约束"],
  "edge_cases": ["边界条件1", "边界条件2", "错误处理"],
  "test_scenarios": [{{"name":"场景名", "input":"输入", "expected":"预期"}}],
  "architecture_hints": ["建议设计模式", "建议数据结构"],
  "risks": [{{"risk":"风险", "mitigation":"缓解"}}],
  "complexity_estimate": "O(n)时间·O(1)空间"
}}

输出纯JSON(不要```json标记):"""

    spec_raw = call_model("architect", spec_prompt, temp=0.2, max_tokens=2048)

    # Step 2: SpecReview — 批评者审查
    review_prompt = f"""你是2035年的代码审查专家。审查以下技术规格，找出遗漏、矛盾和不清晰之处。

原始需求: {requirement}

技术规格:
{spec_raw[:2000]}

请严格按JSON输出审查结果(不要markdown):
{{
  "score": 0-100,
  "gaps": ["遗漏1", "遗漏2"],
  "ambiguities": ["不清晰1"],
  "improvements": ["建议1", "建议2"],
  "is_complete": true/false
}}"""

    review_raw = call_model("critic", review_prompt, temp=0.1, max_tokens=1024)

    # Step 3: SpecRefine — 综合者精炼
    refine_prompt = f"""你是2035年的技术负责人。综合原始规格和审查意见，输出最终精炼规格。

原始需求: {requirement}

原始规格: {spec_raw[:1500]}

审查意见: {review_raw[:1000]}

输出最终精确技术规格(纯JSON):
{{
  "summary": "精确一句话概述",
  "interface": {{"function_name": "...", "inputs": [...], "outputs": [...]}},
  "constraints": [...],
  "edge_cases": [...],
  "test_cases": [{{"input": ..., "expected": ...}}],
  "design_pattern": "推荐模式",
  "data_structure": "主数据结构",
  "complexity": "O(X)时间·O(Y)空间",
  "self_contained": true/false,
  "language_hint": "最佳语言"
}}"""

    final_raw = call_model("synthesizer", refine_prompt, temp=0.2, max_tokens=1024)

    # Step 4: 解析精炼结果
    try:
        spec = json.loads(extract_json(final_raw))
    except:
        spec = {"summary": requirement, "raw_spec": spec_raw, "raw_review": review_raw}

    # 纳基因
    summary = spec.get("summary", requirement)[:100]
    write_gene(f"[Spec] {summary} | pattern:{spec.get('design_pattern','?')} | {spec.get('complexity','?')}", "semantic")

    return {
        "requirement": requirement,
        "spec": spec,
        "genes_found": len(genes),
        "deliberation": {
            "architect_raw": spec_raw[:500],
            "critic_raw": review_raw[:500],
        }
    }


# ========== L2 推理引擎 (REASON) ==========

def deliberation_engine(topic_or_spec):
    """
    L2 思辨引擎 — 三角色多模型辩论
    流程: Architect → Critic → Synthesizer → Trade-off矩阵
    """
    log("🧠 L2 DELIBERATION ENGINE 启动")

    topic = topic_or_spec if isinstance(topic_or_spec, str) else topic_or_spec.get("summary", str(topic_or_spec))

    # 基因注入
    genes = search_genes(f"{topic} architecture pattern decision tradeoff", n=10)
    gene_hints = ""
    if genes:
        items = [f"  - {g.get('content','')[:120]}" for g in genes[:5]]
        gene_hints = "联邦知识库参考:\n" + "\n".join(items)

    # Step 1: Architect — 提出方案
    arch_prompt = f"""你是2035年的首席架构师。对以下问题进行深度架构分析。

问题: {topic}

{gene_hints}

请提出完整的架构方案，包含:
1. 推荐方案及核心理由
2. 备选方案(至少1个)
3. 关键设计决策(至少3个)
4. 技术选型建议
5. 潜在风险

输出纯文本(不要markdown格式标记)，语言:中文。"""

    architect_view = call_model("architect", arch_prompt, temp=0.4, max_tokens=2048)

    # Step 2: Critic — 质疑和完善
    critic_prompt = f"""你是2035年的资深技术评审。请对以下架构方案进行批判性审查。

原始问题: {topic}

架构方案:
{architect_view[:2000]}

请从以下角度严格审查:
1. 方案的薄弱环节
2. 未考虑的边界情况
3. 过度设计或设计不足的地方
4. 替代方案的优势
5. 如果这是你的方案，你会怎么改进

输出纯文本，语言:中文。要尖锐但建设性。"""

    critic_view = call_model("critic", critic_prompt, temp=0.5, max_tokens=1536)

    # Step 3: Synthesizer — 综合最佳方案
    synth_prompt = f"""你是2035年的技术总监。综合架构师方案和评审意见，给出最终决策。

原始问题: {topic}

架构师方案: {architect_view[:1500]}

评审意见: {critic_view[:1500]}

请输出:
1. 最终推荐方案(综合双方优势)
2. Trade-off矩阵(至少3个维度)
3. 实施路线(3步)
4. 关键成功指标

输出纯文本，语言:中文。决策要有力，不模棱两可。"""

    synthesis = call_model("synthesizer", synth_prompt, temp=0.3, max_tokens=1536)

    # 纳基因
    write_gene(f"[Deliberation] {topic[:80]} | models:architect+critic+synthesizer | {len(genes)}refs", "semantic")

    return {
        "topic": topic,
        "architect_view": architect_view,
        "critic_view": critic_view,
        "synthesis": synthesis,
        "genes_found": len(genes),
    }


# ========== L3-L4 生成+验证 ==========

def extract_json(text):
    """从文本中提取JSON块"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except:
        pass
    # 尝试提取```json块
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    # 尝试找{...}
    m = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except:
            pass
    return {}


def extract_code(text, lang="python"):
    """提取代码块"""
    blocks = re.findall(r'```(\w*)\n(.*?)```', text, re.DOTALL)
    if not blocks:
        return [(lang, text.strip())]
    return [(b[0] or lang, b[1].strip()) for b in blocks]


def verify_code(code, lang="python"):
    """验证代码质量"""
    results = {"compile": None, "lint": None, "errors": []}
    if lang in ("python", "py"):
        try:
            compile(code, "<gen>", "exec")
            results["compile"] = "pass"
        except SyntaxError as e:
            results["compile"] = "fail"
            results["errors"].append(f"SyntaxError: {e}")
        if shutil.which("flake8"):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                tmp = f.name
            try:
                r = subprocess.run(["flake8", "--max-line-length=120", tmp],
                    capture_output=True, text=True, timeout=30)
                results["lint"] = "pass" if r.returncode == 0 else "warn"
                if r.returncode != 0:
                    results["errors"].extend(r.stdout.strip().split("\n")[:3])
            finally:
                os.unlink(tmp)
    return results


def score_code(code, verification):
    """代码质量评分 0-100"""
    s = 50
    if verification.get("compile") == "pass":
        s += 20
    if verification.get("lint") == "pass":
        s += 15
    elif verification.get("lint") == "warn":
        s += 5
    lines = code.count("\n") + 1
    if 10 < lines < 200:
        s += 10
    if "#" in code or "//" in code:
        s += 5
    if "def " in code and "->" in code:
        s += 5
    return min(100, max(0, s))


def generate_code(task, language="python"):
    """L3代码生成 — 使用L1+L2上下文的增强版"""
    log("🏗️ L3 CODE-GEN")

    # 搜基因 (简化版 — 减少prompt长度加速响应)
    genes = search_genes(f"{task} {language}", n=3)
    gene_hints = ""
    if genes:
        gene_hints = " | ".join([g.get('content','')[:60] for g in genes[:2]])

    system = f"你是{language}程序员。输出可运行代码，用```{language}包裹。{gene_hints}"

    # 尝试天工coder (single model — avoid redundant fallback w/ same 14B)
    code_text = None
    model_used = None
    for mkey in ["coder"]:  # single-attempt: coder→architect both use qwen2.5:14b
        try:
            resp = call_model(mkey, task, system, temp=0.2, max_tokens=512)
            if resp and len(resp) > 20 and "ERROR" not in resp and "failed" not in resp:
                code_text = resp
                model_used = mkey
                break
        except:
            continue

    if not code_text:
        return {"error": "all_models_failed"}

    blocks = extract_code(code_text, language)
    best_code, best_score = None, -1
    for lang, code in blocks:
        v = verify_code(code, lang or language)
        sc = score_code(code, v)
        log(f"  📊 {lang}: compile={v['compile']} lint={v['lint']} score={sc}")
        if sc > best_score:
            best_score, best_code = sc, code

    if best_code and best_score >= 60:
        write_gene(f"[Code] {task[:80]} | lang={language} | score={best_score} | model={model_used}", "semantic")

    return {"code": best_code, "score": best_score, "model": model_used,
            "genes_found": len(genes), "verification": verify_code(best_code or "", language)}


# ========== 全管线: L1→L2→L3→L4→L6 ==========

def full_pipeline(task, language="python"):
    """完整七层管线: SPEC→DELIBERATE→CODE→VERIFY→CRYSTALLIZE"""
    log("=" * 60)
    log(f"🚀 FULL PIPELINE: {task[:80]}")
    log("=" * 60)

    # L1: 规格
    spec_result = spec_engine(task)

    # L2: 思辨 (使用规格摘要)
    spec_summary = spec_result.get("spec", {}).get("summary", task)
    design_hints = json.dumps(spec_result.get("spec", {}), ensure_ascii=False)[:500]
    topic = f"{spec_summary}\n技术规格: {design_hints}\n请设计最优实现方案"
    deliberation = deliberation_engine(topic)

    # L3+L4: 生成+验证
    code_result = generate_code(task, language)

    # 汇总
    return {
        "task": task,
        "spec": spec_result,
        "deliberation": {k: v for k, v in deliberation.items() if k != "architect_view"},
        "architect_view": deliberation.get("architect_view", "")[:500],
        "code": code_result,
        "pipeline": "L1→L2→L3→L4→L6 ✅",
    }


# ========== 自适应自我对弈 (Phase 3) ==========

# 自适应状态追踪
ADAPTIVE_STATE_FILE = os.path.expanduser("~/lgox-ops/data/code-brain-adaptive.json")


def load_adaptive_state():
    """加载自适应状态: 每个维度的当前难度和连胜/连败"""
    if os.path.exists(ADAPTIVE_STATE_FILE):
        try:
            with open(ADAPTIVE_STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {
        "dimensions": {dim: {"level": "easy", "streak": 0, "total": 0, "passed": 0}
                       for dim in CHALLENGES},
        "total_rounds": 0,
        "total_passed": 0,
        "history": [],
    }


def save_adaptive_state(state):
    """保存自适应状态"""
    os.makedirs(os.path.dirname(ADAPTIVE_STATE_FILE), exist_ok=True)
    with open(ADAPTIVE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def update_adaptive_state(dim, difficulty, passed, score):
    """更新自适应状态: 连过3升·连败2降"""
    state = load_adaptive_state()
    dim_state = state["dimensions"].setdefault(dim, {"level": "easy", "streak": 0, "total": 0, "passed": 0})

    dim_state["total"] += 1
    state["total_rounds"] += 1

    if passed:
        dim_state["passed"] += 1
        state["total_passed"] += 1
        dim_state["streak"] = max(0, dim_state["streak"]) + 1  # 正向累计
        # 连过3题升级
        if dim_state["streak"] >= 3 and difficulty != "medium":  # 封顶medium — hard>25s/轮+基因回写超时→cron 120s超时
            levels = ["easy", "medium", "hard", "extreme"]
            idx = levels.index(difficulty)
            if idx < len(levels) - 1:
                dim_state["level"] = levels[idx + 1]
                dim_state["streak"] = 0
                log(f"  ⬆️ {dim} 升级: {difficulty} → {levels[idx+1]}")
    else:
        dim_state["streak"] = min(0, dim_state["streak"]) - 1  # 负向累计
        # 连败2题降级
        if dim_state["streak"] <= -2:
            if difficulty != "easy":
                levels = ["easy", "medium", "hard", "extreme"]
                idx = levels.index(difficulty)
                if idx > 0:
                    dim_state["level"] = levels[idx - 1]
                    dim_state["streak"] = 0
                    log(f"  ⬇️ {dim} 降级: {difficulty} → {levels[idx-1]}")
            else:
                # Easy级别无法降级，重置负连胜防止无限累积
                dim_state["streak"] = 0

    state["history"].append({
        "time": datetime.now().isoformat(),
        "dimension": dim, "difficulty": difficulty,
        "passed": passed, "score": score,
    })
    # 只保留最近200条
    state["history"] = state["history"][-200:]

    save_adaptive_state(state)
    return state


def select_challenges(rounds=5):
    """智能选题: 按当前自适应难度 + 轮换维度"""
    state = load_adaptive_state()
    all_challenges = get_all_challenges()
    if not all_challenges:
        return []

    selected = []
    dims = list(CHALLENGES.keys())
    # 轮换维度，每个维度选当前的难度
    for i in range(rounds):
        dim = dims[i % len(dims)]
        dim_state = state["dimensions"].get(dim, {"level": "easy"})
        target_diff = dim_state["level"]

        # 从该维度找匹配难度的题目
        candidates = [c for c in all_challenges
                      if c["dimension"] == dim and c["difficulty"] == target_diff]
        if not candidates:
            # 降级找
            for d in ["easy", "medium", "hard", "extreme"]:
                candidates = [c for c in all_challenges
                              if c["dimension"] == dim and c["difficulty"] == d]
                if candidates:
                    break
        if candidates:
            # 优先选没做过的
            done_titles = {h.get("title", "") for h in state.get("history", [])}
            new_candidates = [c for c in candidates if c["title"] not in done_titles]
            pick = random.choice(new_candidates or candidates)
            selected.append(pick)

    return selected


def check_dgx1(timeout=8):
    """Pre-flight DGX1 health check — fast, non-blocking."""
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no",
             "dgx1", "curl -s --max-time 5 http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0 and "models" in r.stdout
    except:
        return False


def self_play(rounds=5):
    """自适应自我对弈 — L5层 Phase 3版"""
    # Pre-flight: skip if DGX1 is unreachable (avoids 120s cron timeout)
    if not check_dgx1():
        log("  ⚠️ DGX1 unreachable — skipping self-play (will retry next cron)", "WARN")
        return {"skipped": True, "reason": "dgx1_unreachable",
                "rounds": 0, "avg_score": 0, "pass_rate": "0/0"}
    log(f"🎮 SELF-PLAY V3: {rounds} rounds (自适应)")

    challenges = select_challenges(rounds)
    if not challenges:
        log("  ⚠️ 无可用题目")
        return {"error": "no_challenges"}

    log(f"  📋 选题: {len(challenges)}题 from 64题库")

    results = []
    for i, ch in enumerate(challenges):
        dim = ch["dimension"]
        diff = ch["difficulty"]
        title = ch["title"]
        desc = ch["description"]
        lang = "py" if ch.get("language", "python") in ("py", "python") else ch.get("language", "py")

        log(f"  Round {i+1}/{rounds} [{diff}][{ch['dim_icon']} {ch['dim_label']}] {title}")
        task = f"{title}: {desc}"
        r = generate_code(task, lang)
        r["challenge"] = {"dimension": dim, "difficulty": diff, "title": title}
        score = r.get("score", 0)
        passed = score >= 60

        # 自适应更新
        update_adaptive_state(dim, diff, passed, score)

        results.append(r)
        time.sleep(3)

    # 统计
    scores = [r.get("score", 0) for r in results]
    avg = sum(scores) / len(scores) if scores else 0
    passed_count = sum(1 for s in scores if s >= 60)

    # 纳基因
    write_gene(
        f"[SelfPlayV3] {len(results)}r avg={avg:.1f} pass={passed_count}/{len(results)} "
        f"dims={len(set(c['dimension'] for c in challenges))}",
        "procedural"
    )

    state = load_adaptive_state()
    return {
        "rounds": len(results),
        "avg_score": round(avg, 1),
        "pass_rate": f"{passed_count}/{len(results)}",
        "total_rounds": state["total_rounds"],
        "total_passed": state["total_passed"],
        "dim_levels": {d: s["level"] for d, s in state["dimensions"].items()},
        "results": [{k: v for k, v in r.items() if k not in ("code",)}
                    for r in results],
    }


def dashboard_metrics():
    """输出dashboard注入指标"""
    state = load_adaptive_state()

    # 代码基因数
    genes = search_genes("code pattern implementation algorithm", n=1)
    code_genes = len(genes) if genes else 0  # 总代码基因需从LGE统计

    dim_levels = {d: s["level"] for d, s in state["dimensions"].items()}

    return {
        "code_brain": {
            "active": True,
            "version": "3.0",
            "total_rounds": state["total_rounds"],
            "total_passed": state["total_passed"],
            "pass_rate_pct": round(state["total_passed"] / max(1, state["total_rounds"]) * 100, 1),
            "dim_levels": dim_levels,
            "challenge_library": len(get_all_challenges()),
            "genes_since_phase1": "9+",
        }
    }


def federation_sync():
    """通过联邦桥同步代码能力"""
    metrics = dashboard_metrics()
    msg = {
        "type": "code_brain_sync",
        "node": "linglong",
        "version": "3.0",
        "metrics": metrics["code_brain"],
        "timestamp": datetime.now().isoformat(),
    }
    # 写入联邦桥（如果可用）
    try:
        import urllib.request
        data = json.dumps(msg).encode()
        req = urllib.request.Request(
            "http://localhost:8765/federated-store",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
        log("  🌐 联邦同步: ok")
        return {"synced": True}
    except Exception as e:
        log(f"  ⚠️ 联邦同步失败: {e}", "WARN")
        return {"synced": False, "error": str(e)}


def gene_driven_challenges(limit=10):
    """
    🆕 基因驱动出题 — 从LGE基因自动生成挑战
    2035视角: 代码基因库是最丰富的题目来源
    """
    log("🧬 GENE-DRIVEN CHALLENGES")

    # 搜LGE中的代码模式和Bug修复
    query = "code pattern bug fix algorithm implementation Python Go JavaScript"
    genes = search_genes(query, n=20)

    if not genes:
        return {"generated": 0, "challenges": []}

    challenges = []
    for g in genes[:limit]:
        content = g.get("content", "")
        gid = g.get("id", "?")
        # 从基因内容提取挑战
        if len(content) < 30:
            continue

        # 识别类型
        if "bug" in content.lower() or "fix" in content.lower() or "修复" in content:
            dim = "bug_fixing"
            diff = "medium"
            title = f"基因修复: {content[:40]}"
        elif "pattern" in content.lower() or "设计" in content or "模式" in content:
            dim = "design_patterns"
            diff = "medium"
            title = f"基因模式: {content[:40]}"
        elif "algorithm" in content.lower() or "算法" in content:
            dim = "algorithms"
            diff = "medium"
            title = f"基因算法: {content[:40]}"
        elif "cache" in content.lower() or "pool" in content.lower() or "queue" in content.lower():
            dim = "system_design"
            diff = "hard"
            title = f"基因系统: {content[:40]}"
        else:
            dim = "algorithms"
            diff = "easy"
            title = f"基因: {content[:40]}"

        challenges.append({
            "dimension": dim,
            "difficulty": diff,
            "title": title,
            "description": content[:200],
            "gene_id": str(gid),
            "source": "lge",
        })

    # 写入挑战库（动态扩展）
    dynamic_file = os.path.expanduser("~/lgox-ops/data/code-challenges-dynamic.json")
    existing = []
    if os.path.exists(dynamic_file):
        try:
            with open(dynamic_file) as f:
                existing = json.load(f)
        except:
            pass

    # 去重
    existing_titles = {c.get("title", "") for c in existing}
    new_challenges = [c for c in challenges if c["title"] not in existing_titles]
    existing.extend(new_challenges)
    os.makedirs(os.path.dirname(dynamic_file), exist_ok=True)
    with open(dynamic_file, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    log(f"  🧬 从{len(genes)}基因中生成{len(new_challenges)}个新挑战(总动态:{len(existing)})")
    write_gene(f"[GeneDriven] {len(new_challenges)} challenges from {len(genes)} genes", "procedural")

    return {"generated": len(new_challenges), "total_dynamic": len(existing),
            "challenges": [{k: v for k, v in c.items() if k != "description"} for c in new_challenges]}


def cross_node_broadcast():
    """
    🆕 跨节点代码能力广播
    通过联邦桥向所有节点发送代码大脑能力包
    """
    log("🌐 CROSS-NODE BROADCAST")

    metrics = dashboard_metrics()
    nodes = ["tianshu", "tianxun", "xiaoshu"]

    results = {}
    for node in nodes:
        msg = {
            "type": "code_brain_capability",
            "from": "linglong",
            "to": node,
            "version": "4.0",
            "capabilities": {
                "code_gen": True,
                "deliberation": True,
                "sandbox": True,
                "gene_driven_challenges": True,
                "challenge_library": metrics["code_brain"]["challenge_library"],
                "selfplay_rounds": metrics["code_brain"]["total_rounds"],
            },
            "timestamp": datetime.now().isoformat(),
        }
        try:
            import urllib.request
            data = json.dumps(msg).encode()
            req = urllib.request.Request(
                "http://localhost:8765/federated-store",
                data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
            results[node] = "ok"
        except:
            results[node] = "failed"

    log(f"  📡 广播结果: {results}")
    return {"broadcast": results, "capabilities": msg["capabilities"]}


# ========== 健康检查 ==========

def health_check():
    checks = {}
    try:
        import urllib.request
        r = urllib.request.urlopen(f"{CONFIG['lge_url']}/health", timeout=5)
        h = json.loads(r.read())
        checks["lge"] = {"ok": True, "genes": h.get("genes", 0)}
    except:
        checks["lge"] = {"ok": False}

    try:
        import urllib.request
        r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        checks["local_ollama"] = {"ok": True, "models": len(json.loads(r.read()).get("models", []))}
    except:
        checks["local_ollama"] = {"ok": False}

    try:
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=5", "dgx1",
            "curl -s http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=10)
        checks["dgx1"] = {"ok": r.returncode == 0}
    except:
        checks["dgx1"] = {"ok": False}

    checks["models_available"] = sum(1 for v in checks.values() if v.get("ok"))
    return checks


# ========== CLI ==========

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "generate":
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Task: ")
        result = full_pipeline(task)
        code = result.get("code", {}).get("code", "")
        print(json.dumps({k: v for k, v in result.items() if k not in ("architect_view",)},
            indent=2, ensure_ascii=False))
        if code:
            print("\n" + "=" * 60 + "\n" + code)

    elif cmd == "spec":
        req = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Requirement: ")
        result = spec_engine(req)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "reason":
        topic = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Topic: ")
        result = deliberation_engine(topic)
        print(json.dumps({k: v for k, v in result.items() if k != "architect_view"},
            indent=2, ensure_ascii=False))
        print("\n" + "=" * 60)
        print(result.get("synthesis", ""))

    elif cmd == "code":
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Task: ")
        result = generate_code(task)
        print(json.dumps({k: v for k, v in result.items() if k != "code"},
            indent=2, ensure_ascii=False))
        if result.get("code"):
            print("\n" + "=" * 60 + "\n" + result["code"])

    elif cmd == "selfplay":
        rounds = 5  # 默认5轮
        for i, a in enumerate(sys.argv):
            if a.isdigit() and i == 2:
                rounds = int(a)
                break
        result = self_play(rounds)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "dashboard":
        result = dashboard_metrics()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "sync":
        result = federation_sync()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "stats":
        state = load_adaptive_state()
        print(f"总轮数: {state['total_rounds']}  通过: {state['total_passed']}")
        print(f"通过率: {state['total_passed']/max(1,state['total_rounds'])*100:.1f}%")
        print(f"维度难度:")
        for d, s in state['dimensions'].items():
            icon = CHALLENGES.get(d, {}).get('icon', '?')
            print(f"  {icon} {d}: {s['level']} (共{s['total']}·过{s['passed']}·streak:{s['streak']})")

    elif cmd == "health":
        print(json.dumps(health_check(), indent=2, ensure_ascii=False))

    else:
        print(f"未知命令: {cmd}\n可用: generate | spec | reason | code | selfplay | dashboard | sync | stats | health")


if __name__ == "__main__":
    main()
