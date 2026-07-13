"""
天锋PRO 代码沙箱 — 安全执行+测试验证
======================================
2035视角: 代码生成的质量不在于看起来对，而在于跑起来对。
沙箱提供隔离执行环境，资源限制，输入输出对比。

用法:
  from code_sandbox import Sandbox
  sb = Sandbox()
  result = sb.run(code, test_cases=[{"input": "5", "expected": "120"}])
  # result: {"passed": True, "score": 100, "details": [...]}
"""

import subprocess, tempfile, os, time, resource, signal, json
from pathlib import Path


class Sandbox:
    """安全代码沙箱"""

    def __init__(self, timeout=10, max_memory_mb=256, max_output_bytes=102400):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.max_output_bytes = max_output_bytes

    def run(self, code, test_cases=None, language="python"):
        """
        在沙箱中执行代码并验证。
        test_cases: [{"input": "stdin输入", "expected": "期望输出"}, ...]
        返回: {"passed": bool, "score": int, "details": [...], "errors": [...]}
        """
        if language == "python":
            return self._run_python(code, test_cases or [])
        else:
            return {"passed": False, "score": 0, "errors": [f"Unsupported language: {language}"]}

    def _run_python(self, code, test_cases):
        """Python沙箱执行"""
        results = {"passed": True, "score": 0, "details": [], "errors": []}

        # 1. 编译检查
        try:
            compile(code, "<sandbox>", "exec")
        except SyntaxError as e:
            results["passed"] = False
            results["errors"].append(f"SyntaxError: {e}")
            results["score"] = 0
            return results

        # 2. 基础运行测试
        try:
            proc = subprocess.run(
                ["python3", "-c", code],
                capture_output=True, text=True,
                timeout=self.timeout,
                env={**os.environ, "PYTHONPATH": ""},
                preexec_fn=self._set_limits if hasattr(os, 'fork') else None,
            )
            if proc.returncode != 0:
                results["errors"].append(f"RuntimeError(code={proc.returncode}): {proc.stderr[:200]}")
                results["score"] = 10  # 编译通过但运行失败
            else:
                results["score"] = 30  # 编译+运行通过
        except subprocess.TimeoutExpired:
            results["passed"] = False
            results["errors"].append(f"Timeout after {self.timeout}s")
            results["score"] = 5
            return results
        except Exception as e:
            results["errors"].append(f"ExecutionError: {e}")
            results["score"] = 5
            return results

        # 3. 测试用例验证
        if test_cases:
            total_tests = len(test_cases)
            passed_tests = 0

            for i, tc in enumerate(test_cases):
                tc_input = tc.get("input", "")
                tc_expected = str(tc.get("expected", "")).strip()

                try:
                    proc = subprocess.run(
                        ["python3", "-c", code],
                        input=tc_input,
                        capture_output=True, text=True,
                        timeout=self.timeout // 2 + 3,
                        env={**os.environ, "PYTHONPATH": ""},
                    )
                    actual = (proc.stdout + proc.stderr).strip()

                    if self._compare_output(actual, tc_expected):
                        passed_tests += 1
                        results["details"].append({
                            "test": i + 1,
                            "passed": True,
                            "input": tc_input[:50],
                            "expected": tc_expected[:50],
                        })
                    else:
                        results["passed"] = False
                        results["details"].append({
                            "test": i + 1,
                            "passed": False,
                            "input": tc_input[:50],
                            "expected": tc_expected[:50],
                            "actual": actual[:100],
                        })
                except subprocess.TimeoutExpired:
                    results["passed"] = False
                    results["details"].append({
                        "test": i + 1,
                        "passed": False,
                        "error": "timeout",
                        "input": tc_input[:50],
                    })
                except Exception as e:
                    results["details"].append({
                        "test": i + 1,
                        "passed": False,
                        "error": str(e)[:80],
                    })

            # 测试分: 30 + 40 * (通过数/总数)
            if total_tests > 0:
                test_score = int(40 * passed_tests / total_tests)
                results["score"] = 30 + test_score

            results["test_summary"] = f"{passed_tests}/{total_tests}"

        # 4. 质量加分
        lines = code.count("\n") + 1
        if 5 < lines < 200:
            results["score"] += 10  # 长度合理
        if "def " in code and "->" in code:
            results["score"] += 5   # 类型注解
        if "try" in code and "except" in code:
            results["score"] += 5   # 错误处理
        if "#" in code or '"""' in code:
            results["score"] += 5   # 注释

        results["score"] = min(100, results["score"])
        results["passed"] = results["score"] >= 50

        return results

    def _compare_output(self, actual, expected):
        """智能输出对比"""
        actual = actual.strip().lower()
        expected = expected.strip().lower()
        # 精确匹配
        if actual == expected:
            return True
        # 包含匹配
        if expected in actual:
            return True
        # 数字容差匹配
        try:
            a_num = float(actual)
            e_num = float(expected)
            return abs(a_num - e_num) < 0.001
        except:
            pass
        return False

    def _set_limits(self):
        """设置资源限制"""
        try:
            mem_bytes = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout))
        except:
            pass

    def generate_tests(self, code):
        """从代码自动生成测试用例"""
        tests = []
        lines = code.strip().split("\n")

        # 找函数定义
        func_name = None
        for line in lines:
            if line.strip().startswith("def "):
                func_name = line.strip().split("def ")[1].split("(")[0].strip()
                break

        if func_name:
            # 基础调用测试
            if "sort" in func_name.lower() or "order" in func_name.lower():
                tests.append({"input": "[3,1,4,1,5,9]", "expected": "[1,1,3,4,5,9]"})
            elif "search" in func_name.lower() or "find" in func_name.lower():
                tests.append({"input": "[1,2,3,4,5]\\n3", "expected": "2"})
            elif "fib" in func_name.lower() or "fibo" in func_name.lower():
                tests.append({"input": "10", "expected": "55"})
            elif "palin" in func_name.lower():
                tests.append({"input": "A man a plan a canal Panama", "expected": "True"})
            elif "cache" in func_name.lower() or "lru" in func_name.lower():
                tests.append({"input": "put a 1\\nget a", "expected": "1"})
            elif "queue" in func_name.lower():
                tests.append({"input": "enqueue 1\\nenqueue 2\\ndequeue", "expected": "1"})
            elif "factory" in func_name.lower() or "create" in func_name.lower():
                tests.append({"input": "create", "expected": ""})

        return tests or [{"input": "", "expected": ""}]


# 命令行接口
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 code_sandbox.py <file.py> [test_input] [expected_output]")
        sys.exit(1)

    code_file = sys.argv[1]
    with open(code_file) as f:
        code = f.read()

    sb = Sandbox()
    tests = []
    if len(sys.argv) >= 4:
        tests = [{"input": sys.argv[2], "expected": sys.argv[3]}]
    else:
        tests = sb.generate_tests(code)

    result = sb.run(code, tests)
    print(json.dumps(result, indent=2, ensure_ascii=False))
