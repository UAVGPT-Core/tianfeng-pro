#!/usr/bin/env python3
"""验证Mock对象实现的正确性 — 10个全维度测试"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/lgox-ops/scripts"))

from mock_impl import Mock, create_autospec, patch, _MockMethod

passed = 0
failed = 0

# --- Test 1: 基本Mock创建和调用计数 ---
print("Test 1: 调用计数")
mock = Mock(name="test")
mock.some_method()
mock.some_method()
assert mock.some_method.call_count == 2, f"Expected 2, got {mock.some_method.call_count}"
passed += 1; print("  ✅ 通过")

# --- Test 2: 返回值预设 ---
print("Test 2: 返回值预设(method.return_value = 42)")
mock2 = Mock()
mock2.get_data.return_value = 42
result = mock2.get_data()
assert result == 42, f"Expected 42, got {result}"
passed += 1; print("  ✅ 通过")

# --- Test 3: 调用参数追踪 ---
print("Test 3: 调用参数追踪")
mock3 = Mock()
mock3.process("hello", key="world")
args, kw = mock3.process.call_args
assert args == ("hello",), f"Expected args ('hello',), got {args}"
mock3.process.assert_called_with("hello", key="world")
passed += 1; print("  ✅ 通过")

# --- Test 4: side_effect异常 ---
print("Test 4: side_effect异常")
mock4 = Mock()
def raiser(x, y):
    raise ValueError(f"error: {x}")
mock4.calc.side_effect = raiser
try:
    mock4.calc(1, 2)
    print("  ❌ 应该抛出异常")
    failed += 1
except ValueError as e:
    passed += 1; print("  ✅ 通过")

# --- Test 5: assert_called_once ---
print("Test 5: assert_called_once验证")
mock5 = Mock()
mock5.do()
mock5.do.assert_called_once()
mock5.do()  # 第二次调用
try:
    mock5.do.assert_called_once()
    print("  ❌ 应该失败(call_count=2)")
    failed += 1
except AssertionError:
    passed += 1; print("  ✅ 通过")

# --- Test 6: reset_mock ---
print("Test 6: reset_mock")
mock6 = Mock()
mock6.work()
assert mock6.work.called, "should be called before reset"
mock6.work.reset_mock()
assert not mock6.work.called, "should not be called after reset"
passed += 1; print("  ✅ 通过")

# --- Test 7: create_autospec ---
print("Test 7: create_autospec")
class MyService:
    def fetch(self, id: int) -> str:
        return f"data_{id}"
    def save(self, data: str) -> bool:
        return True

auto_mock = create_autospec(MyService)
auto_mock.fetch(1)
assert auto_mock.fetch.called
assert not auto_mock.save.called  # save未调用
# 测试自动spec创建的方法存在
assert hasattr(auto_mock, 'fetch')
assert hasattr(auto_mock, 'save')
passed += 1; print("  ✅ 通过")

# --- Test 8: 链式调用 ---
print("Test 8: 链式调用")
mock8 = Mock()
mock8.db.query.return_value = [1, 2, 3]
result = mock8.db.query("SELECT *")
assert result == [1, 2, 3], f"Expected [1,2,3], got {result}"
assert mock8.db.query.call_count == 1
passed += 1; print("  ✅ 通过")

# --- Test 9: assert_not_called ---
print("Test 9: assert_not_called")
mock9 = Mock()
mock9.unused.assert_not_called()
passed += 1; print("  ✅ 通过")

# --- Test 10: 多次调用不同参数 ---
print("Test 10: 多调用追踪")
mock10 = Mock()
mock10.handler("a")
mock10.handler("b")
mock10.handler("c")
assert mock10.handler.call_count == 3
assert len(mock10.handler.call_args_list) == 3
last_args, _ = mock10.handler.call_args
assert last_args == ("c",), f"Expected ('c',), got {last_args}"
passed += 1; print("  ✅ 通过")

# --- Test 11: Mock对象自身call_count ---
print("Test 11: Mock对象自身可调用")
m = Mock(name="func_mock")
m()
m("arg1")
assert m.call_count == 2, f"Expected 2, got {m.call_count}"
assert m.called
try:
    m.assert_called_once()  # should fail (call_count=2)
    print("  ❌ 应该失败(call_count=2)")
    failed += 1
except AssertionError:
    passed += 1; print("  ✅ 通过")

# --- Test 12: return_values多次返回值 ---
print("Test 12: return_values多次返回值")
m12 = Mock()
m12.get.return_values = ["first", "second", "third"]
assert m12.get() == "first"
assert m12.get() == "second"
assert m12.get() == "third"
passed += 1; print("  ✅ 通过")

# --- Test 13: side_effect列表 ---
print("Test 13: side_effect列表")
m13 = Mock()
m13.run.side_effect = [10, 20, 30]
assert m13.run() == 10
assert m13.run() == 20
assert m13.run() == 30
passed += 1; print("  ✅ 通过")

# --- Test 14: reset_mock完整清零(子方法) ---
print("Test 14: 子方法reset")
m14 = Mock()
m14.a()
m14.b("x")
assert m14.a.called
assert m14.b.called
m14.reset_mock()
assert not m14.a.called
assert not m14.b.called
passed += 1; print("  ✅ 通过")

# --- Test 15: __str__和__repr__ ---
print("Test 15: Mock字符串表示")
m15 = Mock(name="MyMock")
assert "MyMock" in str(m15)
assert "MyMock" in repr(m15)
passed += 1; print("  ✅ 通过")

print(f"\n{'='*40}")
print(f"测试结果: {passed}通过 / {failed}失败 / {passed+failed}总计")
sys.exit(0 if failed == 0 else 1)
