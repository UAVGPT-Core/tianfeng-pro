"""
Mock对象 — 支持方法替换和调用计数
====================================
设计模式: Proxy + Command
特性:
  - 方法替换: create_autospec自动mock所有方法
  - 调用计数: call_count/side_effect自动记录
  - 返回值预设: return_value/return_values
  - 调用参数追踪: call_args/call_args_list
  - 链式调用: .method.return_value.child.return_value
  - 自动建Mock: create_autospec(spec)
  - patch装饰器: 临时替换对象属性
  - 上下文管理器: with Mock() as m
"""
from typing import Any, Callable, List, Optional, Tuple, Dict
import functools
import inspect


# 真实实例属性的白名单（不被__getattr__拦截）
_REAL_ATTRS = {
    '_name', '_parent', '_return_value', '_return_values', '_side_effect',
    '_call_count', '_call_args_list', '_call_kwargs_list', '_mock_methods',
    '_spec', '_mock_name',
    # Mock的额外属性
    'return_value', 'side_effect', 'return_values',
}


class _MockCall:
    """记录一次Mock调用的信息"""
    __slots__ = ('args', 'kwargs')
    
    def __init__(self, args: Tuple, kwargs: Dict):
        self.args = args
        self.kwargs = kwargs


class _MockMethod:
    """Mock方法对象，支持替换和调用计数"""
    
    def __init__(self, name: str, parent: 'Mock' = None):
        # 必须在__setattr__白名单之前初始化
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_parent', parent)
        object.__setattr__(self, '_return_value', None)
        object.__setattr__(self, '_return_values', [])
        object.__setattr__(self, '_side_effect', None)
        object.__setattr__(self, '_call_count', 0)
        object.__setattr__(self, '_call_args_list', [])
        object.__setattr__(self, '_call_kwargs_list', [])
        object.__setattr__(self, '_mock_methods', {})
    
    def __setattr__(self, name, value):
        if name in ('return_value',):
            object.__setattr__(self, '_return_value', value)
        elif name in ('side_effect',):
            object.__setattr__(self, '_side_effect', value)
        elif name in ('return_values',):
            object.__setattr__(self, '_return_values', value)
        else:
            object.__setattr__(self, name, value)
    
    def __getattr__(self, name):
        # 特殊属性映射
        if name == 'return_value':
            return object.__getattribute__(self, '_return_value')
        if name == 'side_effect':
            return object.__getattribute__(self, '_side_effect')
        if name == 'call_count':
            return object.__getattribute__(self, '_call_count')
        if name == 'call_args':
            lst = object.__getattribute__(self, '_call_args_list')
            if not lst:
                return None
            kwlst = object.__getattribute__(self, '_call_kwargs_list')
            return (lst[-1], kwlst[-1])
        if name == 'call_args_list':
            return object.__getattribute__(self, '_call_args_list')
        if name == 'call_kwargs_list':
            return object.__getattribute__(self, '_call_kwargs_list')
        if name == 'called':
            return object.__getattribute__(self, '_call_count') > 0
        if name == 'return_values':
            return object.__getattribute__(self, '_return_values')
        
        # 私有属性 -> 正常属性访问
        if name.startswith('_'):
            raise AttributeError(f"'_MockMethod' object has no attribute '{name}'")
        
        # 方法名 -> 子Mock（链式调用支持）
        methods = object.__getattribute__(self, '_mock_methods')
        if name not in methods:
            parent = object.__getattribute__(self, '_parent')
            methods[name] = _MockMethod(name, parent)
        return methods[name]
    
    def __call__(self, *args, **kwargs):
        object.__setattr__(self, '_call_count', 
            object.__getattribute__(self, '_call_count') + 1)
        
        call_args = object.__getattribute__(self, '_call_args_list')
        call_kwargs = object.__getattribute__(self, '_call_kwargs_list')
        call_args.append(args)
        call_kwargs.append(kwargs)
        
        side_effect = object.__getattribute__(self, '_side_effect')
        if side_effect is not None:
            if isinstance(side_effect, list):
                cnt = object.__getattribute__(self, '_call_count')
                return side_effect[cnt - 1]
            elif isinstance(side_effect, type) and issubclass(side_effect, Exception):
                raise side_effect
            else:
                return side_effect(*args, **kwargs)
        
        rvs = object.__getattribute__(self, '_return_values')
        if rvs:
            cnt = object.__getattribute__(self, '_call_count')
            return rvs[cnt - 1]
        
        rv = object.__getattribute__(self, '_return_value')
        return rv if rv is not None else self
    
    def assert_called_once(self):
        cnt = object.__getattribute__(self, '_call_count')
        assert cnt == 1, f"Expected 1 call, got {cnt}"
    
    def assert_called_with(self, *args, **kwargs):
        lst = object.__getattribute__(self, '_call_args_list')
        kwlst = object.__getattribute__(self, '_call_kwargs_list')
        for a, kw in zip(lst, kwlst):
            if a == args and kw == kwargs:
                return
        assert False, f"Expected call {args} {kwargs} not found in calls"
    
    def assert_not_called(self):
        cnt = object.__getattribute__(self, '_call_count')
        assert cnt == 0, f"Expected no calls, got {cnt}"
    
    def reset_mock(self):
        object.__setattr__(self, '_call_count', 0)
        object.__setattr__(self, '_call_args_list', [])
        object.__setattr__(self, '_call_kwargs_list', [])
        for m in object.__getattribute__(self, '_mock_methods').values():
            m.reset_mock()


class Mock:
    """通用Mock对象，自动创建所有方法的MockMethod代理"""
    
    def __init__(self, spec: Optional[type] = None, name: str = "", 
                 return_value: Any = None, side_effect: Optional[Callable] = None):
        object.__setattr__(self, '_mock_name', name or type(self).__name__)
        object.__setattr__(self, '_spec', spec)
        object.__setattr__(self, '_mock_methods', {})
        object.__setattr__(self, '_return_value', return_value)
        object.__setattr__(self, '_side_effect', side_effect)
        object.__setattr__(self, '_call_count', 0)
        object.__setattr__(self, '_call_args_list', [])
        object.__setattr__(self, '_call_kwargs_list', [])
        
        if spec:
            methods = object.__getattribute__(self, '_mock_methods')
            for attr_name in dir(spec):
                if not attr_name.startswith('_') or attr_name in ('__str__', '__repr__'):
                    methods[attr_name] = _MockMethod(attr_name, self)
    
    def __setattr__(self, name, value):
        if name in ('return_value', 'side_effect', 'return_values'):
            object.__setattr__(self, f'_{name}', value)
        else:
            object.__setattr__(self, name, value)
    
    def __getattr__(self, name):
        # 特殊属性
        if name == 'return_value':
            return object.__getattribute__(self, '_return_value')
        if name == 'side_effect':
            return object.__getattribute__(self, '_side_effect')
        if name == 'call_count':
            return object.__getattribute__(self, '_call_count')
        if name == 'call_args':
            lst = object.__getattribute__(self, '_call_args_list')
            if not lst:
                return None
            kwlst = object.__getattribute__(self, '_call_kwargs_list')
            return (lst[-1], kwlst[-1])
        if name == 'called':
            return object.__getattribute__(self, '_call_count') > 0
        
        # 私有属性
        if name.startswith('_') and name not in ('__str__', '__repr__', '__call__', '__enter__', '__exit__'):
            raise AttributeError(f"'Mock' object has no attribute '{name}'")
        
        # 方法名 -> MockMethod
        methods = object.__getattribute__(self, '_mock_methods')
        if name not in methods:
            methods[name] = _MockMethod(name, self)
        return methods[name]
    
    def __call__(self, *args, **kwargs):
        object.__setattr__(self, '_call_count', 
            object.__getattribute__(self, '_call_count') + 1)
        object.__getattribute__(self, '_call_args_list').append(args)
        object.__getattribute__(self, '_call_kwargs_list').append(kwargs)
        
        se = object.__getattribute__(self, '_side_effect')
        if se is not None:
            return se(*args, **kwargs)
        
        rv = object.__getattribute__(self, '_return_value')
        return rv if rv is not None else self
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def __str__(self):
        return f"<Mock name={object.__getattribute__(self, '_mock_name')}>"
    
    def __repr__(self):
        return self.__str__()
    
    def assert_called_once(self):
        cnt = object.__getattribute__(self, '_call_count')
        assert cnt == 1, f"Expected 1 call, got {cnt}"
    
    def assert_not_called(self):
        cnt = object.__getattribute__(self, '_call_count')
        assert cnt == 0, f"Expected no calls, got {cnt}"
    
    def reset_mock(self):
        object.__setattr__(self, '_call_count', 0)
        object.__setattr__(self, '_call_args_list', [])
        object.__setattr__(self, '_call_kwargs_list', [])
        for m in object.__getattribute__(self, '_mock_methods').values():
            m.reset_mock()


def create_autospec(spec: type, **kwargs) -> Mock:
    """基于类或接口自动创建Mock，含所有公开方法"""
    return Mock(spec=spec, **kwargs)


def patch(target: str, **kwargs):
    """简化的patch装饰器 — 替换目标对象的属性为Mock"""
    import importlib
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            module_path, _, attr_name = target.rpartition('.')
            module = importlib.import_module(module_path)
            original = getattr(module, attr_name)
            mock_obj = Mock(**kwargs)
            setattr(module, attr_name, mock_obj)
            try:
                return func(mock_obj, *args, **kw)
            finally:
                setattr(module, attr_name, original)
        return wrapper
    return decorator
