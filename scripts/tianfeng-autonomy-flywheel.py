#!/usr/bin/env python3
"""
═══════════════════════════════════════════
天锋PRO 完全自治飞轮 v1.0
零人类触发·自找问题·自修·自评·自进化
LGOX联邦AI灯塔坐标·永动闭环核心
═══════════════════════════════════════════
"""
# import os,json,time,ast,urllib.request,subprocess,sqlite3,shutil  # 天锋自治:未用导入  # 天锋自治:未用导入
from datetime import datetime
from pathlib import Path

LGE='http://100.116.0.29:8200'
BRIDGE='http://127.0.0.1:8765'
SCRIPTS=os.path.expanduser('~/lgox-ops/scripts')
METRICS_DB=os.path.expanduser('~/.tianfeng/metrics.db')
LOG=os.path.expanduser('~/lgox-ops/logs/tianfeng-autonomy.log')

def log(msg):
    timestamp=datetime.now().strftime('%H:%M:%S')
    print(f'[{timestamp}] {msg}')
    with open(LOG,'a') as f: f.write(f'[{timestamp}] {msg}\n')

def gene_write(content,tag='自治'):
    try:
        urllib.request.urlopen(urllib.request.Request(f'{LGE}/genes/write',
            data=json.dumps({'content':content,'memory_type':'procedural','source':'tianfeng-autonomy','tags':[tag,'完全自治','七自']}).encode(),
            headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except: pass

# ═══ 自找问题 ═══

def self_discover():
    """主动扫描所有代码库找问题"""
    findings=[]
    scan_dirs=[
        os.path.expanduser('~/lgox-ops/scripts'),
        os.path.expanduser('~/bin'),
        os.path.expanduser('~/ai-gateway'),
    ]
    
    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir): continue
        for root,dirs,files in os.walk(scan_dir):
            dirs[:]=[d for d in dirs if not d.startswith('.') and d not in ('__pycache__','node_modules','venv','.venv')]
            for f in files:
                if not f.endswith('.py') or f.startswith('_'): continue
                fpath=os.path.join(root,f)
                try:
                    with open(fpath) as fh: src=fh.read()
                    issues=check_file_issues(fpath,src)
                    if issues: findings.extend(issues)
                except: pass
    
    return findings

def check_file_issues(filepath, src):
    issues=[]
    lines=src.split('\n')
    try: tree=ast.parse(src)
    except SyntaxError as e: return [{'type':'syntax','file':filepath,'line':e.lineno,'fixable':True}]
    
    # 未用导入(可自动修复)
    used=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Name): used.add(n.id)
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            for alias in n.names:
                name=alias.asname or alias.name.split('.')[0]
                if name not in used and len(issues)<2:
                    issues.append({'type':'unused_import','file':filepath,'line':n.lineno,'fixable':True,'import_name':alias.name})
    
    # 语法问题
    for n in ast.walk(tree):
        if isinstance(n,ast.FunctionDef) and hasattr(n,'end_lineno'):
            sz=n.end_lineno-n.lineno
            if sz>80:
                issues.append({'type':'large_func','file':filepath,'line':n.lineno,'fixable':False,'detail':f'{n.name}({sz}行)'})
    
    return issues

# ═══ 自修复 ═══

def self_fix(findings):
    """自动修复可修复的问题"""
    fixed=0
    
    for f in findings:
        if not f.get('fixable'): continue
        
        try:
            with open(f['file']) as fh: src=fh.read()
            
            if f['type']=='unused_import':
                # 注释掉未用导入
                lines=src.split('\n')
                line_idx=f['line']-1
                if line_idx<len(lines) and not lines[line_idx].startswith('#'):
                    shutil.copy2(f['file'],f['file'] + '.bak')
                    lines[line_idx]='# '+lines[line_idx]+'  # 天锋自治:未用导入'
                    open(f['file'],'w').write('\n'.join(lines))
                    fixed+=1
            
            elif f['type']=='syntax':
                # 简单语法修复(去反斜杠)
                fixed_src=src.replace('\\\\','')
                if fixed_src!=src:
                    shutil.copy2(f['file'],f['file'] + '.bak')
                    open(f['file'],'w').write(fixed_src)
                    fixed+=1
        except: pass
    
    return fixed

# ═══ 自评分 ═══

def self_evaluate(findings_before, findings_after, fixed_count):
    """自评本次自治效果"""
    score=0
    report=['═══ 天锋PRO 自治评估 ═══']
    
    # 发现问题
    total_before=len(findings_before)
    total_after=len(findings_after)
    score+=min(30,total_before*2)
    report.append(f'发现问题: {total_before}处 → +{min(30,total_before*2)}分')
    
    # 自动修复
    score+=fixed_count*10
    report.append(f'自动修复: {fixed_count}处 → +{fixed_count*10}分')
    
    # 净优化量
    net=total_before-total_after-fixed_count
    if total_after<total_before:
        score+=min(20,(total_before-total_after)*5)
        report.append(f'减少问题: {total_before-total_after}处 → +{(total_before-total_after)*5}分')
    
    report.append(f'\n自治评分: {score}/100 ★{"⭐"* (score//20)}')
    
    # 更新指标库
    try:
        db=sqlite3.connect(METRICS_DB)
        db.execute("""INSERT INTO operations(command,target,status,genes_found,genes_used,duration_ms,created_at)
            VALUES(?,?,?,?,?,?,?)""",
            ('autonomy','full-scan','success' if score>=50 else 'partial',total_before,fixed_count,0,datetime.now().isoformat()))
        db.commit(); db.close()
    except: pass
    
    return score,'\n'.join(report)

# ═══ 联邦通报 ═══

def federated_report(score, report_text):
    """通过桥向全联邦通报"""
    try:
        urllib.request.urlopen(urllib.request.Request(f'{BRIDGE}/messages/send',
            data=json.dumps({'to':'all','from':'天锋PRO','content':f'完全自治·{score}分·{report_text[:200]}','type':'knowledge_pack','topic':'自治通报'}).encode(),
            headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except: pass

# ═══ 主自治循环 ═══

def autonomous_cycle():
    """一次完整的自治循环: 发现→修复→评分→进化→通报"""
    log('🚀 自治循环启动')
    t0=time.time()
    
    # ① 自找问题
    log('① 自找问题...')
    findings_before=self_discover()
    log(f'   发现 {len(findings_before)} 个问题')
    
    # ② 自修复
    log('② 自修复...')
    fixed=self_fix(findings_before)
    log(f'   修复 {fixed} 处')
    
    # ③ 重新扫描·自评
    log('③ 自评分...')
    findings_after=self_discover()
    score,report=self_evaluate(findings_before,findings_after,fixed)
    log(f'   评分: {score}/100')
    
    # ④ 自进化(纳基因)
    log('④ 自进化...')
    gene_write(f'[完全自治·{datetime.now():%m%d%H%M}] 发现{len(findings_before)}·修复{fixed}·评分{score}')
    
    # ⑤ 联邦通报
    log('⑤ 联邦通报...')
    federated_report(score,report)
    
    elapsed=time.time()-t0
    log(f'✅ 自治循环完成 ({elapsed:.1f}s)')
    
    return {'score':score,'found':len(findings_before),'fixed':fixed,'elapsed':elapsed}

# ═══ 永动入口 ═══

if __name__=='__main__':
    result=autonomous_cycle()
    print(f'\n自治完成: {result["found"]}发现·{result["fixed"]}修复·{result["score"]}分')
