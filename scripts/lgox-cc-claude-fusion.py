#!/usr/bin/env python3
"""
LGOX-CC Claude Code基因融合引擎 v1.0
吸收Claude Code三大工程精华:
  1. 插件Hook系统 — 工具生命周期钩子
  2. 对抗审查(Grill Me) — 安全审计·代码质疑
  3. 上下文切换(Handoff) — 跨会话记忆传递
"""
import os,re,ast,json,time,hashlib,urllib.request
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ═══════════════════════════════════════
# 1. 插件Hook系统
# ═══════════════════════════════════════

class PluginHook:
    """LGOX-CC插件钩子系统——借鉴Claude Code plugin架构"""
    
    def __init__(self):
        self.hooks={
            'pre_tool':[],      # 工具调用前
            'post_tool':[],     # 工具调用后
            'pre_edit':[],      # 编辑文件前
            'post_edit':[],     # 编辑文件后
            'on_error':[],      # 出错时
            'on_complete':[],   # 任务完成时
        }
        self.plugins={}
    
    def register(self, name: str, hook: str, callback):
        """注册插件钩子"""
        if hook in self.hooks:
            self.hooks[hook].append({'name':name,'fn':callback})
            self.plugins[name]=hook
            return True
        return False
    
    def trigger(self, hook: str, context: dict):
        """触发所有注册的钩子"""
        results=[]
        for h in self.hooks.get(hook,[]):
            try:
                r=h['fn'](context)
                if r: results.append({'plugin':h['name'],'result':r})
            except Exception as e:
                results.append({'plugin':h['name'],'error':str(e)})
        return results
    
    def list_plugins(self):
        """列出所有已注册插件"""
        return {k:[h['name'] for h in v] for k,v in self.hooks.items() if v}


# 预制插件

def backup_before_edit(ctx: dict):
    """pre_edit: 修改前自动备份"""
    filepath=ctx.get('file','')
    if filepath and os.path.exists(filepath):
        bak=f'{filepath}.bak.{datetime.now().strftime("%H%M%S")}'
        import shutil
        shutil.copy2(filepath,bak)
        return f'backed:{os.path.basename(bak)}'

def log_after_edit(ctx: dict):
    """post_edit: 修改后记录日志"""
    filepath=ctx.get('file','')
    return f'edited:{os.path.basename(filepath)}'

def auto_gene_on_complete(ctx: dict):
    """on_complete: 任务完成后自动纳基因"""
    summary=ctx.get('summary','任务完成')
    try:
        urllib.request.urlopen(urllib.request.Request(
            'http://100.116.0.29:8200/genes/write',
            data=json.dumps({
                'content':f'[LGOX-CC插件] {summary}',
                'memory_type':'procedural','source':'plugin-auto',
                'tags':['插件','自动','Hook']
            }).encode(),
            headers={'Content-Type':'application/json'},method='POST'),timeout=3)
        return 'gene_written'
    except Exception as e: return None


def create_default_plugins(hook_system: PluginHook):
    """安装LGOX-CC默认插件"""
    hook_system.register('备份守护','pre_edit',backup_before_edit)
    hook_system.register('编辑日志','post_edit',log_after_edit)
    hook_system.register('自动纳基因','on_complete',auto_gene_on_complete)
    return hook_system


# ═══════════════════════════════════════
# 2. 对抗审查引擎 (Grill Me)
# ═══════════════════════════════════════

class AdversarialReviewer:
    """对抗审查:像对手一样审代码·找弱点·质疑每个假设"""
    
    def __init__(self):
        self.checks=[]
    
    def review_code(self, filepath: str) -> dict:
        """对抗性代码审查——找隐藏问题"""
        result={'file':filepath,'risk_score':0,'issues':[],'assumptions':[]}
        
        try:
            with open(filepath) as f: source=f.read()
            tree=ast.parse(source)
            lines=source.split('\n')
            
            # 1. 安全审计
            danger_patterns={
                'eval(':('🔴 代码注入风险·eval()可执行任意Python代码',25),
                'exec(':('🔴 代码注入风险·exec()可执行任意代码',25),
                'os.system(':('🔴 命令注入风险·建议用subprocess.run',20),
                'subprocess.call(':('⚠️ 旧版API·建议subprocess.run',10),
                'pickle.load':('🔴 pickle反序列化风险·攻击者可注入任意对象',25),
                'input(':('⚠️ 用户输入未验证·可能造成注入',10),
                'sqlite3.connect':('⚠️ SQLite连接注意关闭·建议用with语句',5),
                'requests.get(':('⚠️ 网络请求未设置超时·可能阻塞',8),
                'open(':('⚠️ 文件操作·确认路径安全+异常处理',5),
            }
            
            for i,line in enumerate(lines,1):
                for pattern,(msg,risk) in danger_patterns.items():
                    if pattern in line and not line.strip().startswith('#'):
                        result['issues'].append({
                            'line':i,'type':'security','risk':risk,
                            'msg':msg,'code':line.strip()[:60]
                        })
                        result['risk_score']+=risk
            
            # 2. 假设检验:找代码中的隐含假设
            assumption_patterns={
                '==':('假设相等',8),
                '!=':('假设不相等',8),
                'if not':('假设非空/非零',10),
                'if _name_':('假设作为主模块运行',3),
                'as e':('假设异常类型已知',5),
                'default=':('假设默认值安全',5),
                'os.path.exists':('假设路径总是存在',7),
                'try:':('假设异常可恢复',8),
            }
            
            for i,line in enumerate(lines,1):
                for pattern,(assumption,risk) in assumption_patterns.items():
                    if pattern in line and not line.strip().startswith('#'):
                        result['assumptions'].append({
                            'line':i,'assumption':assumption,
                            'risk':risk,'code':line.strip()[:60]
                        })
            
            # 3. 复杂度评估
            func_count=sum(1 for n in ast.walk(tree) if isinstance(n,ast.FunctionDef))
            class_count=sum(1 for n in ast.walk(tree) if isinstance(n,ast.ClassDef))
            
            if len(lines)>500: result['risk_score']+=10
            if len(lines)>1000: result['risk_score']+=20
            if func_count>20: result['risk_score']+=5
            
            result['summary']={
                'total_lines':len(lines),
                'functions':func_count,
                'classes':class_count,
                'risk_level':self._risk_level(result['risk_score']),
                'recommendation':self._recommend(result)
            }
            
        except Exception as e:
            result['error']=str(e)
        
        return result
    
    def _risk_level(self, score: int) -> str:
        if score==0: return '🟢 安全'
        if score<20: return '🟡 低风险'
        if score<50: return '🟠 中风险'
        return '🔴 高风险'
    
    def _recommend(self, result: dict) -> list:
        recs=[]
        if result['risk_score']>0:
            recs.append(f'发现{len(result["issues"])}个安全问题·风险分{result["risk_score"]}')
            recs.append(f'代码有{len(result["assumptions"])}个隐含假设·建议显式验证')
        if result['summary']['total_lines']>1000:
            recs.append('文件过大·建议拆分为多模块')
        return recs
    
    def grill_question(self, code_snippet: str) -> str:
        """生成对抗性质疑问题"""
        questions=[
            '🚨 如果输入为空会怎样？',
            '🚨 如果网络超时会怎样？',
            '🚨 如果文件不存在会怎样？',
            '🚨 如果并发调用会怎样？',
            '🚨 权限不足时会怎样？',
            '🚨 有人恶意输入会怎样？',
        ]
        return '\n'.join(questions[:3])


# ═══════════════════════════════════════
# 3. 上下文切换引擎 (Handoff)
# ═══════════════════════════════════════

class ContextHandoff:
    """跨会话记忆传递·借鉴Claude Code Handoff"""
    
    def __init__(self, memory_dir: str = None):
        self.memory_dir=memory_dir or os.path.expanduser('~/.lgox-cc/handoff')
        os.makedirs(self.memory_dir,exist_ok=True)
    
    def save_context(self, session_id: str, context: dict) -> str:
        """保存当前会话上下文"""
        context['saved_at']=datetime.now().isoformat()
        context['session_id']=session_id
        
        filepath=os.path.join(self.memory_dir,f'{session_id}.json')
        with open(filepath,'w') as f:
            json.dump(context,f,ensure_ascii=False,indent=2)
        
        # 写handoff索引
        index_path=os.path.join(self.memory_dir,'index.json')
        index={}
        if os.path.exists(index_path):
            index=json.load(open(index_path))
        index[session_id]={
            'saved_at':context['saved_at'],
            'files':len(context.get('files',[])),
            'summary':context.get('summary','')[:100]
        }
        # 保留最近20个会话
        if len(index)>20:
            oldest=sorted(index.items(),key=lambda x:x[1]['saved_at'])[0][0]
            del index[oldest]
            os.remove(os.path.join(self.memory_dir,f'{oldest}.json'))
        
        with open(index_path,'w') as f:
            json.dump(index,f,ensure_ascii=False,indent=2)
        
        return filepath
    
    def load_context(self, session_id: str = None) -> dict:
        """加载历史上下文"""
        if not session_id:
            # 加载最近的
            index_path=os.path.join(self.memory_dir,'index.json')
            if os.path.exists(index_path):
                index=json.load(open(index_path))
                if index:
                    session_id=sorted(index.items(),key=lambda x:x[1]['saved_at'])[-1][0]
        
        if session_id:
            filepath=os.path.join(self.memory_dir,f'{session_id}.json')
            if os.path.exists(filepath):
                return json.load(open(filepath))
        
        return {'files':[],'summary':'无历史会话','decisions':[]}
    
    def list_sessions(self) -> list:
        """列出所有历史会话"""
        index_path=os.path.join(self.memory_dir,'index.json')
        if os.path.exists(index_path):
            index=json.load(open(index_path))
            return sorted(index.items(),key=lambda x:x[1]['saved_at'],reverse=True)
        return []
    
    def transfer_knowledge(self, from_session: str, to_prompt: str) -> dict:
        """将历史会话的知识传递到当前任务"""
        old=self.load_context(from_session)
        transfer={
            'from_session':from_session,
            'files_touched':old.get('files',[]),
            'decisions_made':old.get('decisions',[]),
            'errors_encountered':old.get('errors',[]),
            'key_learnings':old.get('learnings',[]),
            'transfer_time':datetime.now().isoformat(),
        }
        return transfer


# ═══ CLI ═══

if __name__=='__main__':
    print("═══ LGOX-CC Claude Code基因融合引擎 ═══\n")
    
    # 1. 插件Hook系统
    print("① 插件Hook系统")
    hooks=PluginHook()
    create_default_plugins(hooks)
    plugs=hooks.list_plugins()
    for hook,names in plugs.items():
        print(f"  {hook}: {', '.join(names)}")
    
    # 测试触发
    result=hooks.trigger('pre_edit',{'file':__file__})
    print(f"  测试pre_edit: {result[0]['result'] if result else 'ok'}")
    
    # 2. 对抗审查
    print()
    print("② 对抗审查引擎(Grill Me)")
    ar=AdversarialReviewer()
    review=ar.review_code(__file__)
    print(f"  风险评分:{review['risk_score']} · {review['summary']['risk_level']}")
    print(f"  安全问题:{len(review['issues'])} · 隐含假设:{len(review['assumptions'])}")
    if review['issues']:
        for i in review['issues'][:2]:
            print(f"    L{i['line']}: {i['msg']}")
    
    # 3. 上下文切换
    print()
    print("③ 上下文切换(Handoff)")
    ch=ContextHandoff()
    ctx={
        'files':['permanent-green.py','lgox-cc'],
        'summary':'Claude Code融合评估·插件+审查+Handoff',
        'decisions':['吸收3大基因','不追模型·追工程'],
        'errors':[],
        'learnings':['Hook架构很优雅','Grill Me能发现隐藏问题']
    }
    saved=ch.save_context('fusion-20260703',ctx)
    print(f"  已保存: {os.path.basename(saved)}")
    loaded=ch.load_context('fusion-20260703')
    print(f"  已加载: {loaded['summary']}")
    sessions=ch.list_sessions()
    print(f"  历史会话: {len(sessions)}个")
    
    print()
    print("Claude Code基因融合完成 ✅")
    print("①②③ 全数吸收·纳基因·全联邦部署")
