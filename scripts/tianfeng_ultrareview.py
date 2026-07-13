#!/usr/bin/env python3
"""
天锋PRO UltraReview v3.0 — DeepSeek API 单文件逐审
扫描目录下所有.py文件, 每文件调DeepSeek审查, 输出/tmp/ultrareview_report.md
"""
import os
import sys
import json
import time
import httpx

# ═══════════════════════════════════
# DeepSeek API 配置
# ═══════════════════════════════════
DEEPSEEK_URL = "http://100.118.207.31:8000/v1/chat/completions"
EXTRA_BODY = {"reasoning": {"enabled": False}}
REVIEW_MODEL = "deepseek-v4-flash"
REQUEST_TIMEOUT = 180.0  # 单文件超时(秒)
MAX_CODE_CHARS = 40000   # 单文件最大提交字符数

# 跳过目录
SKIP_DIRS = {
    '.git', '__pycache__', '.venv', 'venv', 'node_modules',
    'dist', 'build', '.next', '.tox', '.eggs', '.mypy_cache',
    '.pytest_cache', '.ruff_cache', 'site-packages',
}

REVIEW_SYSTEM_PROMPT = """You are a senior code reviewer for a production Python system. 
Analyze the code and report real issues only — no fluff, no style nitpicks.

For each issue found, output:

### 🔴 Critical / 🟡 Warning / 🔵 Suggestion
- **Line**: approximate line number
- **Category**: security | logic | performance | error_handling | maintainability
- **Problem**: one-line description
- **Why it matters**: one-line impact
- **Fix**: one-line suggestion

If no issues found: "✅ No issues detected."

Rules:
- Only report confirmed problems, not speculation.
- Ignore: missing type hints, docstring formatting, import order, line length.
- Focus: crashes, data loss, security holes, resource leaks, dead code."""

REVIEW_USER_TEMPLATE = """Review this Python file for bugs.

## File: {relpath}

```python
{code}
```"""


def collect_py_files(root_path: str) -> list:
    """递归收集所有.py文件, 跳过非代码目录"""
    py_files = []
    abs_root = os.path.abspath(root_path)
    for dirpath, dirnames, filenames in os.walk(abs_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if fname.endswith('.py'):
                py_files.append(os.path.join(dirpath, fname))
    py_files.sort()
    return py_files


def review_single_file(client: httpx.Client, filepath: str, root: str) -> dict:
    """调DeepSeek审查单个.py文件, 返回 {file, review|error}"""
    relpath = os.path.relpath(filepath, root)

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            code = f.read()
    except Exception as e:
        return {"file": filepath, "relpath": relpath, "error": f"读取失败: {e}"}

    if not code.strip():
        return {"file": filepath, "relpath": relpath, "review": "✅ 空文件，无需审查。"}

    # 截断过长代码
    if len(code) > MAX_CODE_CHARS:
        code = code[:MAX_CODE_CHARS] + "\n\n# ... (truncated by UltraReview)"

    payload = {
        "model": REVIEW_MODEL,
        "messages": [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": REVIEW_USER_TEMPLATE.format(relpath=relpath, code=code)},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
        "extra_body": EXTRA_BODY,
    }

    try:
        resp = client.post(DEEPSEEK_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        review_text = data["choices"][0]["message"]["content"]
        return {"file": filepath, "relpath": relpath, "review": review_text}
    except httpx.TimeoutException:
        return {"file": filepath, "relpath": relpath, "error": "请求超时"}
    except httpx.HTTPStatusError as e:
        return {"file": filepath, "relpath": relpath, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"file": filepath, "relpath": relpath, "error": f"请求异常: {e}"}


def build_report(results: list, root: str, elapsed: float) -> str:
    """汇总审查结果为markdown报告"""
    lines = []
    lines.append("# 🔬 天锋PRO UltraReview v3.0 代码审查报告")
    lines.append("")
    lines.append(f"- **审查路径**: `{root}`")
    lines.append(f"- **审查时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **审查文件数**: {len(results)}")
    lines.append(f"- **耗时**: {elapsed:.1f}s")
    lines.append(f"- **审查引擎**: DeepSeek Chat API @ `{DEEPSEEK_URL}`")
    lines.append("")

    # 统计
    ok_count = sum(1 for r in results if "review" in r)
    err_count = sum(1 for r in results if "error" in r)
    critical_count = sum(1 for r in results if "review" in r and "🔴" in r["review"])
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| ✅ 成功审查 | {ok_count} |")
    lines.append(f"| ❌ 审查失败 | {err_count} |")
    lines.append(f"| 🔴 含严重问题 | {critical_count} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        rel = r.get("relpath", os.path.basename(r.get("file", "?")))
        lines.append(f"## 📄 `{rel}`")
        lines.append("")
        lines.append(f"**路径**: `{r['file']}`")
        lines.append("")
        if "error" in r:
            lines.append(f"❌ **审查失败**: {r['error']}")
        else:
            lines.append(r["review"])
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def ultra_review(path: str) -> str:
    """
    扫描path下所有.py文件, 每文件调DeepSeek审查, 输出报告到 /tmp/ultrareview_report.md
    返回报告文件路径
    """
    abs_path = os.path.abspath(path)
    if not os.path.isdir(abs_path):
        print(f"❌ 路径不存在或不是目录: {abs_path}")
        sys.exit(1)

    py_files = collect_py_files(abs_path)
    total = len(py_files)
    if total == 0:
        print(f"⚠️  未找到.py文件于: {abs_path}")
        # 仍然产出空报告
        py_files = []

    print(f"🔍 扫描到 {total} 个 .py 文件")
    print(f"📡 API: {DEEPSEEK_URL}")
    print(f"📝 开始逐文件审查...")
    print("")

    t0 = time.time()
    results = []

    client = httpx.Client(timeout=httpx.Timeout(REQUEST_TIMEOUT))
    try:
        for i, fp in enumerate(py_files, 1):
            rel = os.path.relpath(fp, abs_path)
            print(f"  [{i:>{len(str(total))}}/{total}] 🔎 {rel}")
            result = review_single_file(client, fp, abs_path)
            results.append(result)
            if "error" in result:
                print(f"         ❌ {result['error'][:80]}")
            else:
                # 取首行预览
                preview = result["review"].split("\n")[0][:80] if result["review"] else "(空)"
                print(f"         {preview}")
            # 间隔避免打爆API
            if i < total:
                time.sleep(0.2)
    finally:
        client.close()

    elapsed = time.time() - t0
    print("")
    print(f"⏱️  总耗时: {elapsed:.1f}s")

    report = build_report(results, abs_path, elapsed)

    output_path = "/tmp/ultrareview_report.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 报告已写入: {output_path}")
    return output_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    ultra_review(target)
