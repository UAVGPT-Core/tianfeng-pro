#!/usr/bin/env python3
"""
天锋PRO Swarm模式 v1.0 — 移植自Kimi Code Swarm架构
支持: 模板化多Agent并行/批量代码审查/权限策略/XML结果
架构: Agent级开关 + Session级批调度器
"""
import json, os, time, threading, queue, re, sys

# 确保能找到导入模块
_SCRIPTS_DIR = os.path.expanduser("~/lgox-ops/scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

# ============================================================
# 1. Swarm服务 — Agent级(Session内多Agent)
# ============================================================

class SwarmConfig:
    """Swarm模式配置"""
    def __init__(self):
        self.enabled = False
        self.max_concurrency = 5          # 最大并行数
        self.max_subagents = 128           # 最多子Agent数
        self.timeout_per_agent = 300       # 每个Agent超时(秒)
        self.auto_approve = True           # Swarm模式自动审批
        self.result_format = 'xml'         # xml|json|text

    def to_dict(self):
        return {
            'enabled': self.enabled,
            'max_concurrency': self.max_concurrency,
            'max_subagents': self.max_subagents,
            'auto_approve': self.auto_approve,
        }


class SubAgentSpec:
    """子Agent规格"""
    def __init__(self, agent_id: str, prompt: str, agent_type='coder'):
        self.agent_id = agent_id
        self.prompt = prompt
        self.agent_type = agent_type  # coder|reviewer|planner|explorer
        self.result = None
        self.status = 'pending'  # pending|running|done|error
        self.error = None
        self.start_time = None
        self.end_time = None


class AgentSwarmTool:
    """
    Swarm工具: 模板化多Agent并行
    用法:
        swarm = AgentSwarmTool()
        results = swarm.run(
            description="审查这些文件",
            prompt_template="审查以下代码: {{item}}",
            items=["file1.py", "file2.py"],
            agent_type="reviewer"
        )
    """
    
    def __init__(self, config: SwarmConfig = None):
        self.config = config or SwarmConfig()
        self._agents = {}  # agent_id -> SubAgentSpec
    
    def render_prompt(self, template: str, item: str) -> str:
        """渲染模板: {{item}} -> 实际内容"""
        return template.replace('{{item}}', str(item))
    
    def run(self, description: str, prompt_template: str, items: list,
            agent_type='coder', resume_agents: dict = None,
            max_concurrency: int = None) -> list:
        """
        执行Swarm任务
        
        Args:
            description: 任务描述(给模型理解)
            prompt_template: 模板,含{{item}}
            items: 子项列表
            agent_type: 子Agent类型
            resume_agents: {agent_id: prompt} 恢复已存在的Agent
            max_concurrency: 最大并行数(默认config)
        
        Returns:
            list of {agent_id, prompt, result, status}
        """
        mc = max_concurrency or self.config.max_concurrency
        
        # 构建Agent规格
        specs = []
        
        # 恢复已有Agent
        if resume_agents:
            for aid, aprompt in resume_agents.items():
                specs.append(SubAgentSpec(aid, aprompt, agent_type))
        
        # 新建Agent
        for i, item in enumerate(items[:self.config.max_subagents]):
            rid = f'swarm-{i+1}'
            rendered = self.render_prompt(prompt_template, item)
            specs.append(SubAgentSpec(rid, rendered, agent_type))
        
        if not specs:
            return []
        
        print(f'[Swarm] 启动 {len(specs)}个子Agent (并发{mc})')
        print(f'[Swarm] 描述: {description[:60]}')
        
        # 用线程池执行
        results = []
        lock = threading.Lock()
        
        def execute_one(spec: SubAgentSpec):
            spec.status = 'running'
            spec.start_time = time.time()
            try:
                # TODO: 对接实际LLM调用(ngc_router.smart_call)
                # 这里使用占位实现
                result = self._mock_agent_call(spec)
                spec.result = result
                spec.status = 'done'
            except Exception as e:
                spec.error = str(e)
                spec.status = 'error'
            finally:
                spec.end_time = time.time()
                with lock:
                    results.append(spec)
        
        with ThreadPoolExecutor(max_workers=mc) as ex:
            fs = {ex.submit(execute_one, s): s for s in specs}
            for f in as_completed(fs):
                pass  # 结果已通过execute_one收集
        
        # 生成报告
        done = sum(1 for r in results if r.status == 'done')
        err = sum(1 for r in results if r.status == 'error')
        print(f'[Swarm] 完成: {done}成功/{err}失败')
        
        return self._format_results(results)
    
    def _mock_agent_call(self, spec: SubAgentSpec) -> str:
        """调用NGC智能路由实现Agent"""
        try:
            from ngc_router import smart_call
            prompt = spec.prompt[:500]  # 截断防止超长
            result = smart_call(prompt, tier='fast', max_tokens=512)
            if result:
                return result
        except Exception as e:
            pass
        return f'[Swarm:{spec.agent_type}] {spec.prompt[:60]}... 完成(占位)'
    
    def _format_results(self, results: list) -> list:
        """格式化输出结果(Kimi Code使用XML格式)"""
        if self.config.result_format == 'xml':
            return self._to_xml(results)
        return [{'id': r.agent_id, 'result': r.result, 'status': r.status} for r in results]
    
    def _to_xml(self, results: list) -> list:
        """XML格式结果"""
        xml_parts = ['<swarm_results>']
        for r in results:
            xml_parts.append(f'  <agent id="{r.agent_id}" status="{r.status}">')
            xml_parts.append(f'    <prompt>{r.prompt[:100]}</prompt>')
            xml_parts.append(f'    <result>{r.result or r.error or ""}</result>')
            xml_parts.append('  </agent>')
        xml_parts.append('<tianfeng swarm_results>')
        return [{'xml': '\n'.join(xml_parts)}]
    
    def cancel(self, agent_id: str = None):
        """取消指定的Agent(或全部)"""
        if agent_id:
            if agent_id in self._agents:
                self._agents[agent_id].status = 'cancelled'
        else:
            for a in self._agents.values():
                if a.status == 'running':
                    a.status = 'cancelled'


# ============================================================
# 2. Session级Swarm协调器(跨多次对话)
# ============================================================

class SessionSwarmCoordinator:
    """
    Session级Swarm协调: 跨多轮对话管理多个Swarm批次
    对应Kimi Code的ISessionSwarmService
    """
    
    def __init__(self, max_concurrency: int = 5):
        self.max_concurrency = max_concurrency
        self._batches = {}  # batch_id -> AgentRunBatch
        self._current_batch_id = 0
    
    def run_batch(self, specs: list, description: str = '') -> str:
        """
        执行一批Swarm任务
        Returns: batch_id
        """
        self._current_batch_id += 1
        bid = f'batch-{self._current_batch_id}'
        
        batch = AgentRunBatch(
            batch_id=bid,
            specs=specs,
            max_concurrency=self.max_concurrency
        )
        self._batches[bid] = batch
        batch.run()
        return bid
    
    def get_batch(self, batch_id: str) -> Optional['AgentRunBatch']:
        return self._batches.get(batch_id)
    
    def get_results(self, batch_id: str) -> list:
        batch = self._batches.get(batch_id)
        if not batch: return []
        return batch.results
    
    def cancel_batch(self, batch_id: str):
        batch = self._batches.get(batch_id)
        if batch: batch.cancel()
    
    def status(self) -> dict:
        return {
            'total_batches': len(self._batches),
            'active_batches': sum(1 for b in self._batches.values() if b.is_running),
            'max_concurrency': self.max_concurrency,
        }


class AgentRunBatch:
    """单个Swarm批次"""
    
    def __init__(self, batch_id: str, specs: list, max_concurrency: int = 5):
        self.batch_id = batch_id
        self.specs = specs  # list of SubAgentSpec
        self.max_concurrency = max_concurrency
        self.results = []
        self.is_running = False
        self.start_time = None
        self.end_time = None
        self._lock = threading.Lock()
    
    def run(self):
        self.is_running = True
        self.start_time = time.time()
        
        def execute(spec):
            spec.status = 'running'
            spec.start_time = time.time()
            try:
                # TODO: 对接ngc_router
                time.sleep(1)
                spec.result = f'Batch:{self.batch_id} Agent:{spec.agent_id} Done'
                spec.status = 'done'
            except Exception as e:
                spec.error = str(e)
                spec.status = 'error'
            finally:
                spec.end_time = time.time()
                with self._lock:
                    self.results.append(spec)
        
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as ex:
            fs = {ex.submit(execute, s): s for s in self.specs}
            for f in as_completed(fs):
                pass
        
        self.is_running = False
        self.end_time = time.time()
    
    def cancel(self):
        self.is_running = False
        for s in self.specs:
            if s.status == 'running':
                s.status = 'cancelled'


# ============================================================
# 3. 权限策略(Swarm模式自动审批)
# ============================================================

class SwarmPermissionPolicy:
    """
    Swarm模式权限策略
    - 独占-拒绝: Swarm工具调用时禁止其他工具
    - 自动审批: Swarm模式下自动批准操作
    """
    
    MODE_MANUAL = 'manual'
    MODE_AUTO = 'auto'  
    MODE_YOLO = 'yolo'
    
    def __init__(self, mode='auto'):
        self.mode = mode
        self._exclusive_tool = None  # 当前独占的工具
    
    def acquire_exclusive(self, tool_name: str) -> bool:
        """获取独占权限(Swarm工具专用)"""
        if self._exclusive_tool and self._exclusive_tool != tool_name:
            return False  # 已被其他工具独占
        self._exclusive_tool = tool_name
        return True
    
    def release_exclusive(self):
        self._exclusive_tool = None
    
    def check_permission(self, action: str) -> bool:
        """检查操作权限"""
        if self.mode == self.MODE_YOLO:
            return True
        if self.mode == self.MODE_AUTO and self._exclusive_tool:
            return True  # Swarm模式下自动审批
        return self.mode == self.MODE_AUTO
    
    def is_exclusive(self) -> bool:
        return self._exclusive_tool is not None


# ============================================================
# 4. CLI接口
# ============================================================

class SwarmCLI:
    """天锋PRO Swarm命令行"""
    
    @staticmethod
    def parse_args(args: list) -> dict:
        """解析tianfeng swarm命令参数"""
        params = {
            'description': '',
            'template': '',
            'items': [],
            'agent_type': 'coder',
            'concurrency': 5,
        }
        i = 0
        while i < len(args):
            if args[i] == '--desc' and i+1 < len(args):
                params['description'] = args[i+1]; i+=2
            elif args[i] == '--template' and i+1 < len(args):
                params['template'] = args[i+1]; i+=2
            elif args[i] == '--items' and i+1 < len(args):
                params['items'] = args[i+1].split(','); i+=2
            elif args[i] == '--type' and i+1 < len(args):
                params['agent_type'] = args[i+1]; i+=2
            elif args[i] == '--concurrency' and i+1 < len(args):
                params['concurrency'] = int(args[i+1]); i+=2
            else:
                i+=1
        return params
    
    @staticmethod
    def print_help():
        print('''Swarm模式 - 多Agent并行执行
用法: tianfeng swarm --desc "任务描述" --template "模板(含{{item}})" --items "a,b,c" [options]

选项:
  --desc        任务描述
  --template    提示模板(用{{item}}占位)
  --items       子项列表(逗号分隔)
  --type        Agent类型: coder|reviewer|planner|explorer
  --concurrency 并发数(默认5)

示例:
  tianfeng swarm --desc "审查以下文件" --template "审查代码审查代码: {{item}}" --items "main.py,utils.py" --type reviewer
''')


# ============================================================
# 5. 天锋PRO集成入口
# ============================================================

class TianfengSwarm:
    """天锋PRO Swarm集成"""
    
    def __init__(self):
        self.config = SwarmConfig()
        self.coordinator = SessionSwarmCoordinator()
        self.permission = SwarmPermissionPolicy()
        self._tool = None
    
    @property
    def tool(self):
        if not self._tool:
            self._tool = AgentSwarmTool(self.config)
        return self._tool
    
    def enable(self):
        self.config.enabled = True
        self.permission.mode = 'auto'
        print('[Swarm] 已启用 (自动审批·并发{})'.format(self.config.max_concurrency))
    
    def disable(self):
        self.config.enabled = False
        self.permission.mode = 'manual'
        print('[Swarm] 已禁用')
    
    def handle_command(self, args: list) -> str:
        """处理tianfeng swarm命令"""
        if not args or args[0] in ('help', '--help'):
            SwarmCLI.print_help()
            return ''
        
        if args[0] == 'on':
            self.enable()
            return 'Swarm模式已开启'
        elif args[0] == 'off':
            self.disable()
            return 'Swarm模式已关闭'
        elif args[0] == 'status':
            s = self.config.to_dict()
            return json.dumps(s, indent=2, ensure_ascii=False)
        
        params = SwarmCLI.parse_args(args)
        if not params['template'] or not params['items']:
            return '错误: 需要--template和--items'
        
        if not self.config.enabled:
            self.enable()
        
        results = self.tool.run(
            description=params['description'],
            prompt_template=params['template'],
            items=params['items'],
            agent_type=params['agent_type'],
            max_concurrency=params['concurrency'],
        )
        
        return self._format_response(results)
    
    def _format_response(self, results: list) -> str:
        lines = ['## Swarm执行结果\n']
        for r in results:
            if 'xml' in r:
                lines.append(r['xml'])
            else:
                lines.append(f"- Agent {r['id']}: {r['status']}")
        return '\n'.join(lines)


# ============================================================
# 测试入口
# ============================================================

if __name__ == '__main__':
    import sys
    swarm = TianfengSwarm()
    if len(sys.argv) > 1:
        result = swarm.handle_command(sys.argv[1:])
        print(result)
    else:
        # 演示
        print('=== 天锋PRO Swarm模式 v1.0 ===')
        print()
        swarm.enable()
        print()
        results = swarm.tool.run(
            description='审查代码文件',
            prompt_template='审查以下文件: {{item}}',
            items=['main.py', 'utils.py', 'config.py', 'api.py', 'models.py'],
            agent_type='reviewer',
            max_concurrency=3,
        )
        print()
        print('=== 坐标状态 ===')
        print(json.dumps(swarm.coordinator.status(), indent=2, ensure_ascii=False))
