"""
简易RPC框架 (LGOX Gene: GENE-PRO-RPC-v1)
========================================
三层架构: 服务注册中心 → 请求/响应消息 → RPC调用器
支持: 本地直接调用 + TCP远程调用 + JSON序列化
"""

import json
import uuid
import threading
import socket
from abc import ABC, abstractmethod
from typing import Callable, Any


# ═══════════════════════════════════════════
# 第一层: 服务注册中心 (线程安全)
# ═══════════════════════════════════════════

class ServiceRegistry:
    """线程安全的服务注册中心 - 支持注册/解析/列表"""
    
    def __init__(self):
        self._services: dict[str, object] = {}
        self._lock = threading.RLock()
    
    def register(self, name: str, service: object) -> None:
        """注册服务实例"""
        with self._lock:
            if name in self._services:
                raise KeyError(f"Service '{name}' already registered")
            self._services[name] = service
    
    def register_instance(self, service: object) -> str:
        """自动用类名注册"""
        name = type(service).__name__
        self.register(name, service)
        return name
    
    def resolve(self, name: str) -> object:
        """解析服务实例"""
        with self._lock:
            if name not in self._services:
                raise KeyError(f"Service '{name}' not registered. Available: {list(self._services.keys())}")
            return self._services[name]
    
    def list_services(self) -> list[str]:
        with self._lock:
            return list(self._services.keys())
    
    def unregister(self, name: str) -> None:
        with self._lock:
            self._services.pop(name, None)


# ═══════════════════════════════════════════
# 第二层: 消息协议 (JSON-RPC风格)
# ═══════════════════════════════════════════

class RPCRequest:
    """RPC请求消息"""
    
    def __init__(self, service: str, method: str,
                 params: dict = None, request_id: str = None):
        self.service = service
        self.method = method
        self.params = params or {}
        self.request_id = request_id or uuid.uuid4().hex[:12]
    
    def to_dict(self) -> dict:
        return {
            "jsonrpc": "2.0",
            "service": self.service,
            "method": self.method,
            "params": self.params,
            "id": self.request_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RPCRequest":
        return cls(
            service=data["service"],
            method=data["method"],
            params=data.get("params", {}),
            request_id=data.get("id"),
        )
    
    def serialize(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def deserialize(cls, data: str) -> "RPCRequest":
        return cls.from_dict(json.loads(data))


class RPCResponse:
    """RPC响应消息"""
    
    def __init__(self, result=None, error: str = None, request_id: str = None):
        self.result = result
        self.error = error
        self.request_id = request_id
    
    def is_error(self) -> bool:
        return self.error is not None
    
    def to_dict(self) -> dict:
        d = {"jsonrpc": "2.0", "id": self.request_id}
        if self.error:
            d["error"] = {"code": -1, "message": self.error}
        else:
            d["result"] = self.result
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> "RPCResponse":
        err = data.get("error")
        return cls(
            result=data.get("result"),
            error=err["message"] if isinstance(err, dict) else err,
            request_id=data.get("id"),
        )
    
    def serialize(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def deserialize(cls, data: str) -> "RPCResponse":
        return cls.from_dict(json.loads(data))


# ═══════════════════════════════════════════
# 第三层: RPC调用器 / 执行引擎
# ═══════════════════════════════════════════

class RPCCaller(ABC):
    """抽象RPC调用器"""
    
    @abstractmethod
    def call(self, request: RPCRequest) -> RPCResponse:
        ...


class LocalRPCExecutor:
    """本地模式: 直接调注册的服务 -> 零网络开销"""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
    
    def execute(self, request: RPCRequest) -> RPCResponse:
        """执行RPC请求"""
        try:
            service = self.registry.resolve(request.service)
            method = getattr(service, request.method, None)
            if method is None:
                return RPCResponse(
                    error=f"Method '{request.method}' not found on {request.service}",
                    request_id=request.request_id,
                )
            result = method(**request.params)
            return RPCResponse(result=result, request_id=request.request_id)
        except TypeError as e:
            return RPCResponse(
                error=f"Argument mismatch: {e}",
                request_id=request.request_id,
            )
        except Exception as e:
            return RPCResponse(error=str(e), request_id=request.request_id)


# ═══════════════════════════════════════════
# 第四层: TCP远程传输
# ═══════════════════════════════════════════

class RPCServer:
    """TCP RPC服务器"""
    
    def __init__(self, registry: ServiceRegistry,
                 host: str = "127.0.0.1", port: int = 0):
        self.executor = LocalRPCExecutor(registry)
        self.host = host
        self.port = port
        self._server = None
        self._running = False
    
    def start(self):
        """启动TCP服务器"""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(5)
        self.port = self._server.getsockname()[1]
        self._running = True
        threading.Thread(target=self._serve, daemon=True).start()
        return self.port
    
    def _serve(self):
        """接受连接循环"""
        self._server.settimeout(1.0)
        while self._running:
            try:
                conn, addr = self._server.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
    
    def _handle(self, conn: socket.socket):
        """处理单个RPC请求"""
        try:
            data = conn.recv(65536).decode("utf-8")
            request = RPCRequest.deserialize(data)
            response = self.executor.execute(request)
            conn.sendall(response.serialize().encode("utf-8"))
        except Exception as e:
            error_resp = RPCResponse(error=f"Server error: {e}")
            try:
                conn.sendall(error_resp.serialize().encode("utf-8"))
            except Exception:
                pass
        finally:
            conn.close()
    
    def stop(self):
        self._running = False
        if self._server:
            self._server.close()


class RPCClient(RPCCaller):
    """TCP RPC客户端"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9090):
        self.host = host
        self.port = port
    
    def call(self, request: RPCRequest) -> RPCResponse:
        """发送RPC请求并接收响应"""
        data = request.serialize()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(10.0)
            sock.connect((self.host, self.port))
            sock.sendall(data.encode("utf-8"))
            response_data = sock.recv(65536).decode("utf-8")
            return RPCResponse.deserialize(response_data)
    
    def remote_call(self, service: str, method: str,
                    params: dict = None) -> Any:
        """便捷调用: service.method(params) -> result"""
        request = RPCRequest(service=service, method=method, params=params)
        response = self.call(request)
        if response.is_error():
            raise RuntimeError(f"RPC error: {response.error}")
        return response.result


# ═══════════════════════════════════════════
# 使用示例
# ═══════════════════════════════════════════

if __name__ == "__main__":
    # 1. 定义服务
    class Calculator:
        def add(self, a: int, b: int) -> int:
            return a + b
        def multiply(self, a: int, b: int) -> int:
            return a * b
    
    # 2. 注册
    registry = ServiceRegistry()
    registry.register_instance(Calculator())
    print(f"Registered services: {registry.list_services()}")
    
    # 3. 本地调用
    executor = LocalRPCExecutor(registry)
    req = RPCRequest(service="Calculator", method="add", params={"a": 3, "b": 4})
    resp = executor.execute(req)
    print(f"Local call: Calculator.add(3,4) = {resp.result}")
    
    # 4. TCP远程调用
    server = RPCServer(registry, port=0)
    port = server.start()
    print(f"RPC Server started on port {port}")
    
    client = RPCClient(port=port)
    result = client.remote_call("Calculator", "multiply", {"a": 6, "b": 7})
    print(f"Remote call: Calculator.multiply(6,7) = {result}")
    
    server.stop()
    print("RPC: All tests passed ✅")
