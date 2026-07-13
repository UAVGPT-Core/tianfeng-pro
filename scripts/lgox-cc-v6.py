#!/usr/bin/env python3
"""LGOX-CC v6.0 统一集入入口·8引擎·一键调用"""
import os,sys,json

SCRIPTS=os.path.dirname(os.path.abspath(__file__)) or os.path.expanduser('~/lgox-ops/scripts')

E = {
    'ast':    'lgox-cc-ast-engine.py',
    'patch':  'lgox-cc-batch-refactor.py',
    'fed':    'lgox-cc-federated-engine.py',
    'fable':  'lgox-cc-fable-engine.py',
    'claude': 'lgox-cc-claude-fusion.py',
    'trade':  'stockagent-super-flywheel.py',
}

D = {
    'ast':    'AST骨架+静态分析+LSP补全',
    'patch':  '批量Patch+AST重构+自动备份',
    'fed':    '联邦协同·6节点并行处理',
    'fable':  'Fable验证+依赖追踪+浏览器测试',
    'claude': 'Claude Hook+对抗审查+Handoff',
    'trade':  '虚拟交易飞轮+基因产出',
}

def run(name):
    if name=='status': status(); return
    if name not in E: print('引擎:', ','.join(E.keys())); return
    path=os.path.join(SCRIPTS,E[name])
    if not os.path.exists(path): print(f'MISS: {path}'); return
    try:
        exec(open(path).read(),{'__name__':'__main__'})
    except SystemExit: pass
    except Exception as e: print(f'FAIL {name}: {e}')

def status():
    names=['ast','patch','fed','fable','claude','trade']
    for n in names:
        ok='YES' if os.path.exists(os.path.join(SCRIPTS,E[n])) else 'NO'
        print(f'{n:8s} {ok:4s} {D[n]}')
    print('集成入口就绪: python3 lgox-cc-v6.py [ast|patch|fed|fable|claude|trade|status]')

if __name__=='__main__':
    if len(sys.argv)>1: run(sys.argv[1])
    else: status()
