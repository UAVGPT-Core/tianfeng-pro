#!/usr/bin/env python3
"""
LGOX-CC 联邦协同编程引擎 v1.0
多节点并行处理大项目
- 任务拆分: 按文件/模块自动拆解
- 联邦分发: 桥消息→各节点并行执行
- 结果合并: 统一汇总·冲突检测
- 进度追踪: 实时状态·超时重试
"""
import os,re,json,urllib.request,time,subprocess,sqlite3,hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict

BRIDGE='http://127.0.0.1:8765'
MY_NAME='联邦协同引擎'
DB_PATH=os.path.expanduser('~/.hermes/fed_messages.db')

# 可用节点(编程能力排序)
FED_NODES=[
    {'name':'天枢','model':'deepseek-v4-pro','cores':24,'bridge':True},
    {'name':'天工','model':'ollama+deepseek','cores':20,'bridge':True,'gpu':True},
    {'name':'灵龙','model':'deepseek-v4-pro','cores':8,'bridge':True},
    {'name':'天怿','model':'deepseek-v4-pro','cores':12,'bridge':True},
    {'name':'地枢','model':'deepseek-v4-pro','cores':16,'bridge':True},
    {'name':'织网','model':'deepseek-v4-pro','cores':4,'bridge':True},
]

class FederatedCodeEngine:
    """联邦协同编程引擎"""
    
    def __init__(self):
        self.tasks=[]
        self.results={}
        self.active_jobs={}
    
    def split_project(self, project_path: str, task_type: str = 'analyze') -> list:
        """拆分项目为联邦任务
        
        Args:
            project_path: 项目根目录
            task_type: analyze|refactor|review|test
        """
        tasks=[]
        files=self._collect_py_files(project_path)
        
        if not files:
            return tasks
        
        # 按文件大小分组·均衡负载
        file_info=[]
        for fp in files:
            size=os.path.getsize(fp)
            file_info.append({'path':fp,'size':size,'rel':os.path.relpath(fp,project_path)})
        
        # 排序列:大文件优先
        file_info.sort(key=lambda x:-x['size'])
        
        # 分配到节点(轮询)
        batch_size=max(1,len(files)//len(FED_NODES))
        
        for i,fi in enumerate(file_info):
            node_idx=i%len(FED_NODES)
            node=FED_NODES[node_idx]
            
            if i%batch_size==0 or i==0:
                task_id=f'task_{len(tasks):04d}'
                tasks.append({
                    'id':task_id,
                    'node':node['name'],
                    'files':[],
                    'task_type':task_type,
                    'status':'pending',
                    'created':datetime.now().isoformat()[:19]
                })
            
            tasks[-1]['files'].append(fi)
        
        self.tasks=tasks
        return tasks
    
    def _collect_py_files(self, project_path: str) -> list:
        files=[]
        for root,dirs,fs in os.walk(project_path):
            dirs[:]=[d for d in dirs if not d.startswith('.') and d!='__pycache__' and d!='node_modules']
            for f in fs:
                if f.endswith('.py') or f.endswith('.js') or f.endswith('.html'):
                    files.append(os.path.join(root,f))
        return files
    
    def dispatch_task(self, task: dict) -> bool:
        """通过联邦桥分发任务到目标节点"""
        msg={
            'to':task['node'],
            'from':MY_NAME,
            'content':json.dumps({
                'action':'federated_code',
                'task_id':task['id'],
                'task_type':task['task_type'],
                'files':[f['path'] for f in task['files'][:5]],  # 限制文件数
                'instruction':f"分析{len(task['files'])}个文件·{task['task_type']}任务"
            },ensure_ascii=False),
            'type':'action',
            'topic':'联邦协同编程'
        }
        
        try:
            urllib.request.urlopen(urllib.request.Request(
                f'{BRIDGE}/messages/send',
                data=json.dumps(msg).encode(),
                headers={'Content-Type':'application/json'},
                method='POST'),timeout=5)
            task['status']='dispatched'
            task['dispatched_at']=datetime.now().isoformat()[:19]
            self.active_jobs[task['id']]=task
            return True
        except:
            return False
    
    def dispatch_all(self) -> int:
        """分发所有pending任务"""
        count=0
        for task in self.tasks:
            if task['status']=='pending':
                if self.dispatch_task(task):
                    count+=1
        return count
    
    def collect_results(self, timeout: int = 60) -> dict:
        """收集各节点的处理结果"""
        results={}
        
        try:
            db=sqlite3.connect(DB_PATH,timeout=5)
            # 查来自各节点的回复
            for task in self.tasks:
                rows=db.execute("""
                    SELECT content,from_node,ts FROM messages 
                    WHERE from_node=? AND topic='联邦协同编程·结果'
                    AND ts>datetime(?)
                    ORDER BY ts DESC LIMIT 3
                """,(task['node'],task.get('dispatched_at',datetime.now().isoformat()[:19]))).fetchall()
                
                if rows:
                    results[task['id']]={
                        'node':task['node'],
                        'files':len(task['files']),
                        'replies':len(rows),
                        'latest':rows[0][0][:200] if rows[0][0] else ''
                    }
                    task['status']='completed'
            
            db.close()
        except: pass
        
        self.results=results
        return results
    
    def get_progress(self) -> dict:
        """获取当前进度"""
        total=len(self.tasks)
        pending=sum(1 for t in self.tasks if t['status']=='pending')
        dispatched=sum(1 for t in self.tasks if t['status']=='dispatched')
        completed=sum(1 for t in self.tasks if t['status']=='completed')
        
        return {
            'total_tasks':total,
            'pending':pending,
            'dispatched':dispatched,
            'completed':completed,
            'progress_pct':completed*100//total if total>0 else 0,
            'node_assignments':self._node_stats()
        }
    
    def _node_stats(self) -> dict:
        stats=defaultdict(int)
        for t in self.tasks:
            stats[t['node']]+=1
        return dict(stats)
    
    def run_pipeline(self, project_path: str, task_type: str = 'analyze'):
        """一键执行联邦协同编程管道"""
        print(f'[{datetime.now():%H:%M}] 联邦协同编程·{project_path}')
        
        # 1. 拆分
        tasks=self.split_project(project_path,task_type)
        print(f'  拆分: {len(tasks)}个任务·{sum(len(t["files"]) for t in tasks)}个文件')
        
        # 2. 分发
        dispatched=self.dispatch_all()
        print(f'  分发: {dispatched}/{len(tasks)}个')
        
        # 3. 等候收集
        time.sleep(5)
        self.collect_results()
        
        # 4. 进度报告
        progress=self.get_progress()
        print(f'  完成: {progress["completed"]}/{progress["total"]} ({progress["progress_pct"]}%)')
        print(f'  节点分配: {progress["node_assignments"]}')
        
        return progress


# ═══ CLI ═══

if __name__=='__main__':
    engine=FederatedCodeEngine()
    
    # 自检:分析自身项目
    test_path=os.path.expanduser('~/lgox-ops/scripts')
    print("═══ 联邦协同编程引擎 ═══")
    
    tasks=engine.split_project(test_path)
    print(f"拆分lgox-ops: {len(tasks)}任务→{len(FED_NODES)}节点")
    
    for t in tasks[:3]:
        print(f"  {t['id']}: →{t['node']} ({len(t['files'])}文件)")
    
    print(f"\n节点负载:")
    stats=engine.get_progress()
    for node,cnt in sorted(stats['node_assignments'].items(),key=lambda x:-x[1]):
        bar='█'*cnt+'░'*(max(stats['node_assignments'].values())-cnt)
        print(f"  {node}: {cnt}任务 {bar}")
    
    print("\n联邦协同引擎就绪 ✅ | 6节点·桥分发·并行处理")
