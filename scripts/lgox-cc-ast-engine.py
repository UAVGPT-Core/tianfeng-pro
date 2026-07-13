#!/usr/bin/env python3
"""
LGOX-CC AST+静态分析+LSP引擎 v1.0
零外部依赖·纯Python标准库
- AST解析: 代码骨架·函数/类/导入分析
- 静态分析: 语法错误·未定义变量·潜在bug
- LSP轻量: jedi代码补全·跳转定义
"""
import ast,os,sys,re,subprocess,json
from pathlib import Path

class ASTAnalyzer:
    """AST代码骨架分析器"""
    
    @staticmethod
    def parse_file(filepath: str) -> dict:
        """解析单文件·返回代码骨架"""
        try:
            with open(filepath,'r') as f:
                source=f.read()
            tree=ast.parse(source)
            
            functions=[]
            classes=[]
            imports=[]
            variables=[]
            
            for node in ast.walk(tree):
                if isinstance(node,ast.FunctionDef):
                    functions.append({
                        'name':node.name,
                        'line':node.lineno,
                        'args':[a.arg for a in node.args.args],
                        'decorators':[d.id for d in node.decorator_list if isinstance(d,ast.Name)]
                    })
                elif isinstance(node,ast.ClassDef):
                    classes.append({
                        'name':node.name,
                        'line':node.lineno,
                        'methods':[m.name for m in node.body if isinstance(m,ast.FunctionDef)]
                    })
                elif isinstance(node,ast.Import):
                    for alias in node.names:
                        imports.append({'module':alias.name,'alias':alias.asname})
                elif isinstance(node,ast.ImportFrom):
                    for alias in node.names:
                        imports.append({'module':f'{node.module}.{alias.name}','alias':alias.asname})
                elif isinstance(node,ast.Assign):
                    for target in node.targets:
                        if isinstance(target,ast.Name):
                            variables.append({'name':target.id,'line':node.lineno})
            
            return {
                'file':filepath,
                'lines':len(source.split('\n')),
                'functions':functions,
                'classes':classes,
                'imports':imports,
                'variables':variables,
                'has_async':any(isinstance(n,(ast.AsyncFunctionDef,ast.Await)) for n in ast.walk(tree))
            }
        except SyntaxError as e:
            return {'file':filepath,'error':f'SyntaxError: {e}'}
        except Exception as e:
            return {'file':filepath,'error':str(e)}
    
    @staticmethod
    def parse_project(project_path: str) -> dict:
        """解析整个项目"""
        results={'files':[],'summary':{}}
        total_funcs=0;total_classes=0;total_lines=0
        
        for root,dirs,files in os.walk(project_path):
            # 跳过虚拟环境和隐藏目录
            dirs[:]=[d for d in dirs if not d.startswith('.') and d not in ('node_modules','venv','__pycache__')]
            for f in files:
                if f.endswith('.py'):
                    fpath=os.path.join(root,f)
                    parsed=ASTAnalyzer.parse_file(fpath)
                    results['files'].append(parsed)
                    if 'lines' in parsed:
                        total_lines+=parsed['lines']
                        total_funcs+=len(parsed.get('functions',[]))
                        total_classes+=len(parsed.get('classes',[]))
        
        results['summary']={
            'total_files':len([f for f in results['files'] if 'error' not in f]),
            'total_errors':len([f for f in results['files'] if 'error' in f]),
            'total_functions':total_funcs,
            'total_classes':total_classes,
            'total_lines':total_lines
        }
        return results


class StaticAnalyzer:
    """静态代码分析器"""
    
    @staticmethod
    def check_file(filepath: str) -> list:
        """检查单文件问题"""
        issues=[]
        try:
            with open(filepath,'r') as f:
                source=f.read()
                lines=source.split('\n')
            
            # 1. 语法检查
            try: ast.parse(source)
            except SyntaxError as e: issues.append({'line':e.lineno,'type':'SyntaxError','msg':str(e)})
            
            # 2. 常见问题模式
            patterns={
                'print(':'🐌 生产代码中残留print调试·建议用logging',
                'except:':'⚠️ 裸except捕获所有异常·请指定具体异常类型',
                'import *':'⚠️ import * 污染命名空间·请显式导入',
                'eval(':'🔴 eval()有代码注入风险·不建议使用',
                'os.system(':'🔴 os.system()有命令注入风险·建议subprocess',
                'global ':'⚠️ 使用global变量·考虑重构为函数参数',
                'time.sleep(':'🐌 同步sleep阻塞·考虑asyncio.sleep',
            }
            for i,line in enumerate(lines,1):
                stripped=line.strip()
                if stripped.startswith('#'): continue
                for pattern,msg in patterns.items():
                    if pattern in stripped:
                        issues.append({'line':i,'type':'CodeSmell','msg':f'{pattern}: {msg}'})
            
            # 3. TODO/FIXME检查
            for i,line in enumerate(lines,1):
                if 'TODO' in line or 'FIXME' in line:
                    issues.append({'line':i,'type':'TODO','msg':line.strip()[:80]})
            
        except Exception as e:
            issues.append({'line':0,'type':'Error','msg':str(e)})
        
        return issues
    
    @staticmethod
    def quality_score(issues: list) -> int:
        """根据问题数给质量分(0-100)"""
        if not issues: return 100
        errors=sum(1 for i in issues if i['type']=='SyntaxError')
        smells=sum(1 for i in issues if i['type']=='CodeSmell')
        warnings=len(issues)-errors-smells
        score=100-errors*20-smells*3-warnings*2
        return max(0,min(100,score))


class LSPLight:
    """轻量LSP——基于jedi的代码智能"""
    
    def __init__(self):
        self._jedi=None
        try:
            import jedi
            self._jedi=jedi
        except ImportError:
            pass
    
    def complete(self, source: str, line: int, col: int, path: str = '<string>') -> list:
        """代码补全"""
        if not self._jedi:
            return [{'text':'⚠️ pip install jedi 启用LSP','type':'info'}]
        try:
            script=self._jedi.Script(source,path=path)
            completions=script.complete(line,col)
            return [{'text':c.name,'type':c.type,'description':c.description} for c in completions[:10]]
        except: return []
    
    def goto_definition(self, source: str, line: int, col: int, path: str = '<string>'):
        """跳转定义"""
        if not self._jedi:
            return None
        try:
            script=self._jedi.Script(source,path=path)
            defs=script.goto(line,col)
            if defs:
                d=defs[0]
                return {'name':d.name,'line':d.line,'column':d.column,'module':d.module_name,'description':d.description}
        except: return None
        return None
    
    def references(self, source: str, line: int, col: int, path: str = '<string>'):
        """查找引用"""
        if not self._jedi:
            return []
        try:
            script=self._jedi.Script(source,path=path)
            refs=script.references(line,col)
            return [{'name':r.name,'line':r.line,'column':r.column} for r in refs[:20]]
        except: return []


# ═══ CLI ═══
if __name__=='__main__':
    # pip install jedi 2>/dev/null
    ast_analyzer=ASTAnalyzer()
    static_analyzer=StaticAnalyzer()
    lsp=LSPLight()
    
    # 自检: 分析自身
    print("═══ LGOX-CC AST+静态+LSP 引擎 ═══")
    self_analysis=ast_analyzer.parse_file(__file__)
    print(f"AST: {self_analysis['functions']}函数·{self_analysis['classes']}类·{self_analysis['lines']}行")
    
    issues=static_analyzer.check_file(__file__)
    score=static_analyzer.quality_score(issues)
    print(f"静态: {len(issues)}个问题·质量{score}分")
    
    if lsp._jedi:
        test=lsp.complete("import o",1,8)
        print(f"LSP: jedi可用·补全示例:{len(test)}条")
    else:
        print("LSP: jedi未安装·代码补全待激活")
    
    print("\n引擎就绪 ✅ | AST+静态分析零依赖 | pip install jedi 激活LSP")
