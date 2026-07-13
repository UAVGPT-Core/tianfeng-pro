#!/usr/bin/env python3
"""
LGOX-CC 批量重构引擎 v1.0
- 多文件批量Patch
- 智能重命名(函数/变量/类/导入)
- 重构操作: 提取函数·移动类·统一导入
- 修改前自动备份(.bak)
- 统一diff预览
"""
import os,re,ast,shutil,json,hashlib
from pathlib import Path
from datetime import datetime

# ═══ 基础工具 ═══

def backup(filepath: str) -> str:
    """自动备份·返回备份路径"""
    bak=f'{filepath}.bak.{datetime.now().strftime("%m%d%H%M%S")}'
    if os.path.exists(filepath):
        shutil.copy2(filepath,bak)
    return bak

def read_file_safe(path: str) -> str:
    with open(path,'r') as f: return f.read()

def write_file_safe(path: str, content: str):
    with open(path,'w') as f: f.write(content)

# ═══ 批量Patch ═══

class BatchPatcher:
    """多文件批量替换"""
    
    def __init__(self):
        self.results=[]
    
    def patch_files(self, pattern: str, replacement: str, files: list, regex: bool = False, dry_run: bool = True) -> dict:
        """批量替换多个文件中的模式
        
        Args:
            pattern: 查找模式
            replacement: 替换文本
            files: 文件路径列表
            regex: True=正则匹配·False=精确匹配
            dry_run: True=仅预览·False=执行
        """
        result={'files':[],'total_matches':0,'dry_run':dry_run}
        
        for fp in files:
            if not os.path.exists(fp): continue
            src=read_file_safe(fp)
            
            if regex:
                matches=list(re.finditer(pattern,src))
                new_src=re.sub(pattern,replacement,src)
            else:
                matches=[m for m in [{'start':i} for i in range(len(src)) if src.startswith(pattern,i)]]
                new_src=src.replace(pattern,replacement)
            
            count=len(matches)
            if count==0: continue
            
            if not dry_run:
                backup(fp)
                write_file_safe(fp,new_src)
            
            result['files'].append({'path':fp,'matches':count,'changed':new_src!=src})
            result['total_matches']+=count
        
        return result

# ═══ 重构引擎 ═══

class RefactorEngine:
    """AST驱动的代码重构"""
    
    def __init__(self):
        self.history=[]
    
    def rename_symbol(self, filepath: str, old_name: str, new_name: str, symbol_type: str = 'all') -> dict:
        """重命名函数/变量/类/导入
        
        Args:
            symbol_type: 'function'|'variable'|'class'|'import'|'all'
        """
        result={'file':filepath,'old':old_name,'new':new_name,'type':symbol_type,'changes':0}
        
        try:
            src=read_file_safe(filepath)
            tree=ast.parse(src)
            
            class Renamer(ast.NodeTransformer):
                def visit_FunctionDef(self,node):
                    if node.name==old_name and symbol_type in ('function','all'):
                        node.name=new_name
                        result['changes']+=1
                    return self.generic_visit(node)
                
                def visit_ClassDef(self,node):
                    if node.name==old_name and symbol_type in ('class','all'):
                        node.name=new_name
                        result['changes']+=1
                    return self.generic_visit(node)
                
                def visit_Name(self,node):
                    if node.id==old_name and symbol_type in ('variable','all'):
                        node.id=new_name
                        result['changes']+=1
                    return node
            
            new_tree=Renamer().visit(tree)
            ast.fix_missing_locations(new_tree)
            new_src=ast.unparse(new_tree)
            
            if new_src!=src:
                backup(filepath)
                write_file_safe(filepath,new_src)
                result['status']='renamed'
            else:
                result['status']='no_change'
        except SyntaxError as e:
            result['status']=f'syntax_error:{e}'
        except Exception as e:
            result['status']=f'error:{e}'
        
        self.history.append(result)
        return result
    
    def extract_function(self, filepath: str, start_line: int, end_line: int, new_func_name: str) -> dict:
        """提取一段代码为独立函数"""
        result={'file':filepath,'function':new_func_name,'lines':f'{start_line}-{end_line}'}
        
        try:
            src=read_file_safe(filepath)
            lines=src.split('\n')
            
            # 提取选中的代码块
            block='\n'.join(lines[start_line-1:end_line])
            
            # 构建新函数
            indented_block='\n    '.join(block.split('\n'))
            new_func=f'def {new_func_name}():\n    {indented_block}\n'
            
            # 替换原位置为函数调用
            original_block=lines[start_line-1:end_line+1] if end_line<len(lines) else lines[start_line-1:]
            new_src=src.replace('\n'.join(original_block),f'{new_func_name}()')
            
            # 将新函数插入文件末尾
            new_src+=f'\n\n{new_func}'
            
            backup(filepath)
            write_file_safe(filepath,new_src)
            result['status']='extracted'
        except Exception as e:
            result['status']=f'error:{e}'
        
        self.history.append(result)
        return result
    
    def bulk_rename(self, project_root: str, old_name: str, new_name: str, file_pattern: str = '*.py') -> dict:
        """项目级批量重命名"""
        result={'files':[],'total_changes':0}
        
        for root,dirs,files in os.walk(project_root):
            dirs[:]=[d for d in dirs if not d.startswith('.') and d not in ('node_modules','venv','__pycache__')]
            for f in files:
                if f.endswith('.py'):
                    fpath=os.path.join(root,f)
                    r=self.rename_symbol(fpath,old_name,new_name,'all')
                    if r['changes']>0:
                        result['files'].append(r)
                        result['total_changes']+=r['changes']
        
        return result

# ═══ Diff预览 ═══

def diff_preview(filepath: str, old_str: str, new_str: str) -> str:
    """手动diff预览(不依赖difflib——直接用+/-标记)"""
    old_lines=old_str.split('\n')
    new_lines=new_str.split('\n')
    
    diffs=[]
    max_len=max(len(old_lines),len(new_lines))
    for i in range(max_len):
        old_line=old_lines[i] if i<len(old_lines) else None
        new_line=new_lines[i] if i<len(new_lines) else None
        if old_line!=new_line:
            if old_line: diffs.append(f'- {old_line}')
            if new_line: diffs.append(f'+ {new_line}')
    
    return '\n'.join(diffs[:50])  # 最多50行


# ═══ CLI: 自检 ═══

def self_test():
    """自检——对自身做AST分析"""
    bp=BatchPatcher()
    re=RefactorEngine()
    
    # 查找自身所有print语句
    all_files=[__file__]
    result=bp.patch_files('print(','print(',all_files,dry_run=True)
    print(f"批量Patch: {len(result['files'])}文件·{result['total_matches']}处匹配")
    
    # AST自分析
    import ast as ast_mod
    src=read_file_safe(__file__)
    tree=ast_mod.parse(src)
    funcs=[n.name for n in ast_mod.walk(tree) if isinstance(n,ast_mod.FunctionDef)]
    classes=[n.name for n in ast_mod.walk(tree) if isinstance(n,ast_mod.ClassDef)]
    print(f"AST分析: {len(funcs)}函数·{len(classes)}类")
    
    print("批量重构引擎就绪 ✅")
    return True

if __name__=='__main__':
    self_test()
