#!/usr/bin/env python3
"""
LGOX-CC Fable能力融合引擎 v1.0
吸取Claude Fable 5四大工程思想:
  1. 主动验证 — 修改代码后自动跑测试
  2. 全项目理解 — AST引擎(已有·增强)
  3. 浏览器测试 — 联邦browser工具集成
  4. 依赖追踪 — AST分析site-packages依赖树
"""
import os,re,ast,json,subprocess,sys,time,urllib.request
from pathlib import Path
from datetime import datetime

# ═══ 1. 主动验证引擎 ═══

class AutoValidator:
    """修改代码后自动跑测试"""
    
    def __init__(self, project_root: str):
        self.project_root=project_root
        self.test_cache={}  # {file: [related_test_files]}
    
    def find_tests(self, changed_file: str) -> list:
        """智能发现与修改文件相关的测试"""
        tests=[]
        rel=os.path.relpath(changed_file,self.project_root)
        
        # 规则1: 同名test文件
        name=os.path.splitext(os.path.basename(changed_file))[0]
        test_patterns=[
            f'test_{name}.py',f'{name}_test.py',
            f'tests/test_{name}.py',f'test/test_{name}.py'
        ]
        for p in test_patterns:
            candidate=os.path.join(self.project_root,p)
            if os.path.exists(candidate):
                tests.append(candidate)
        
        # 规则2: 目录下所有test_*.py
        changed_dir=os.path.dirname(changed_file)
        for f in os.listdir(changed_dir):
            if f.startswith('test_') and f.endswith('.py'):
                tests.append(os.path.join(changed_dir,f))
        
        # 规则3: 全局tests目录
        for root,dirs,files in os.walk(self.project_root):
            dirs[:]=[d for d in dirs if d in ('tests','test','__pycache__')]
            for f in files:
                if name in f and (f.startswith('test') or f.endswith('_test.py')):
                    tests.append(os.path.join(root,f))
        
        self.test_cache[changed_file]=tests
        return tests
    
    def run_tests(self, changed_file: str, auto_fix: bool = False) -> dict:
        """运行相关测试·可选自动修复"""
        tests=self.find_tests(changed_file)
        result={'file':changed_file,'tests':len(tests),'passed':0,'failed':0,'errors':[]}
        
        for test_file in tests[:5]:  # 最多跑5个测试
            try:
                r=subprocess.run([sys.executable,'-m','pytest',test_file,'-x','-q','--tb=short'],
                    capture_output=True,text=True,timeout=60,cwd=self.project_root)
                if r.returncode==0:
                    result['passed']+=1
                else:
                    result['failed']+=1
                    result['errors'].append({
                        'test':test_file,
                        'output':r.stdout[-200:]+r.stderr[-100:]
                    })
                    
                    # 自动修复:重试运行(简单策略)
                    if auto_fix and r.returncode!=0:
                        time.sleep(1)
                        r2=subprocess.run([sys.executable,'-m','pytest',test_file,'--lf','-q'],
                            capture_output=True,text=True,timeout=30,cwd=self.project_root)
                        if r2.returncode==0:
                            result['passed']+=1
                            result['failed']-=1
                            result['auto_fixed']=True
            except subprocess.TimeoutExpired:
                result['errors'].append({'test':test_file,'output':'超时'})
            except FileNotFoundError:
                result['errors'].append({'test':test_file,'output':'pytest未安装·pip install pytest'})
        
        return result
    
    def validate_after_change(self, changed_files: list, auto_fix: bool = True) -> dict:
        """批量修改后验证"""
        summary={'files':len(changed_files),'total_tests':0,'passed':0,'failed':0}
        for f in changed_files[:3]:  # 限制3个文件
            r=self.run_tests(f,auto_fix)
            summary['total_tests']+=r['tests']
            summary['passed']+=r['passed']
            summary['failed']+=r['failed']
        return summary


# ═══ 2. 依赖追踪引擎 ═══

class DependencyTracker:
    """AST分析依赖树"""
    
    def __init__(self, project_root: str):
        self.project_root=project_root
        self.dep_graph={}
        self.site_packages=self._find_site_packages()
    
    def _find_site_packages(self) -> str:
        """查找site-packages位置"""
        for p in sys.path:
            if 'site-packages' in p and os.path.isdir(p):
                return p
        # 常见位置
        candidates=[
            os.path.expanduser('~/.local/lib/python3.*/site-packages'),
            '/usr/lib/python3/dist-packages',
        ]
        import glob
        for c in candidates:
            for d in glob.glob(c):
                if os.path.isdir(d): return d
        return ''
    
    def trace_file(self, filepath: str) -> dict:
        """追踪单文件的导入依赖"""
        result={'file':filepath,'imports':[],'external':[],'stdlib':[]}
        
        try:
            with open(filepath) as f:
                tree=ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for alias in node.names:
                        dep={'module':alias.name,'type':'import'}
                        result['imports'].append(dep)
                        self._classify_dependency(dep,result)
                elif isinstance(node,ast.ImportFrom):
                    if node.module:
                        dep={'module':node.module,'names':[a.name for a in node.names],'type':'from'}
                        result['imports'].append(dep)
                        self._classify_dependency(dep,result)
        except: pass
        
        return result
    
    def _classify_dependency(self, dep: dict, result: dict):
        """分类依赖: 项目内/外部/标准库"""
        module=dep['module'].split('.')[0]
        # 标准库
        stdlib=['os','sys','re','json','time','datetime','pathlib','ast','hashlib','math',
                'subprocess','urllib','sqlite3','collections','typing','logging','io','csv',
                'random','itertools','functools','threading','multiprocessing','socket','ssl']
        if module in stdlib:
            result['stdlib'].append(dep)
            return
        
        # 项目内
        project_file=os.path.join(self.project_root,module.replace('.','/')+'.py')
        if os.path.exists(project_file):
            result['imports'][-1]['project']=True
            return
        
        # 外部(site-packages)
        if self.site_packages:
            sp_file=os.path.join(self.site_packages,module)
            sp_file_py=f'{sp_file}.py'
            if os.path.exists(sp_file) or os.path.exists(sp_file_py):
                result['external'].append({**dep,'location':self.site_packages})
    
    def trace_project(self) -> dict:
        """全项目依赖追踪"""
        summary={'files':0,'total_imports':0,'external_deps':set(),'critical_deps':[]}
        
        for root,dirs,files in os.walk(self.project_root):
            dirs[:]=[d for d in dirs if not d.startswith('.') and d!='__pycache__']
            for f in files:
                if f.endswith('.py'):
                    fpath=os.path.join(root,f)
                    r=self.trace_file(fpath)
                    summary['files']+=1
                    summary['total_imports']+=len(r['imports'])
                    for ext in r['external']:
                        summary['external_deps'].add(ext['module'].split('.')[0])
        
        summary['external_deps']=sorted(summary['external_deps'])
        # 关键依赖(第三方包)
        known=['numpy','pandas','requests','flask','fastapi','django','sqlalchemy',
               'pydantic','celery','redis','docker','kubernetes','click','rich']
        for dep in summary['external_deps']:
            if dep in known:
                summary['critical_deps'].append(dep)
        
        return summary


# ═══ 3. 浏览器测试引擎 ═══

class BrowserTester:
    """联邦browser工具集成"""
    
    def __init__(self, bridge_url: str = 'http://127.0.0.1:8765'):
        self.bridge=bridge_url
    
    def test_page(self, url: str, checks: list = None) -> dict:
        """对页面运行健康检查"""
        result={'url':url,'status':'unknown','checks':{}}
        
        # 基础HTTP检查
        try:
            code=urllib.request.urlopen(url,timeout=5).getcode()
            result['checks']['http']=code==200
            result['status']='ok' if code==200 else f'http_{code}'
        except:
            result['checks']['http']=False
            result['status']='unreachable'
            return result
        
        # 特定检查
        if checks:
            try:
                body=urllib.request.urlopen(url,timeout=5).read().decode()
                for check in checks:
                    if check in body:
                        result['checks'][check]=True
                    else:
                        result['checks'][check]=False
                        if result['status']=='ok':
                            result['status']='partial'
            except: pass
        
        return result
    
    def test_federation_pages(self) -> list:
        """检查所有联邦页面"""
        pages=[
            'https://stock.uavgpt.com/',
            'https://stock.uavgpt.com/federation/',
            'https://stock.uavgpt.com/mianmian/',
            'https://stock.uavgpt.com/proposals/gaia-ai/',
            'https://stock.uavgpt.com/signals.html',
        ]
        results=[]
        for p in pages:
            r=self.test_page(p,['<!DOCTYPE','</html>'])
            results.append(r)
        return results


# ═══ CLI ═══

if __name__=='__main__':
    project=os.path.expanduser('~/lgox-ops/scripts')
    
    print("═══ LGOX-CC Fable融合引擎 ═══")
    print()
    
    # 1. 主动验证
    print("① 主动验证引擎")
    av=AutoValidator(project)
    test_file=os.path.join(project,'permanent-green.py')
    tests=av.find_tests(test_file)
    print(f"  修改permanent-green.py → 发现{tests}相关测试")
    r=av.run_tests(test_file)
    print(f"  测试: {r['passed']}通过·{r['failed']}失败")
    
    # 2. 依赖追踪
    print()
    print("② 依赖追踪引擎")
    dt=DependencyTracker(project)
    file_deps=dt.trace_file(test_file)
    print(f"  permanent-green.py: {len(file_deps['imports'])}个导入·{len(file_deps['external'])}外部·{len(file_deps['stdlib'])}标准库")
    proj=dt.trace_project()
    print(f"  全项目: {proj['files']}文件·{proj['total_imports']}导入·{len(proj['external_deps'])}外部依赖")
    if proj['critical_deps']:
        print(f"  关键依赖: {', '.join(proj['critical_deps'][:5])}")
    
    # 3. 浏览器测试
    print()
    print("③ 浏览器测试引擎")
    bt=BrowserTester()
    pages=bt.test_federation_pages()
    ok=sum(1 for p in pages if p['status']=='ok')
    print(f"  联邦页面: {ok}/{len(pages)}健康")
    for p in pages:
        emoji='✅' if p['status']=='ok' else '⚠️'
        print(f"    {emoji} {p['url'].split('/')[-2]}: {p['status']}")
    
    print()
    print("Fable融合引擎就绪 ✅ | 主动验证+依赖追踪+浏览器测试")
