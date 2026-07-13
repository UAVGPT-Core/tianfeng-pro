#!/usr/bin/env python3
"""
天锋PRO 基因消费环 v1.0
每次行动前搜索LGE历史基因·参考过去的成功案例
指标仪表盘·成功率·修复率·进化速度
"""
import sqlite3,json,urllib.request,os,time
from datetime import datetime
from collections import defaultdict

LGE='http://100.116.0.29:8200'
METRICS_DB=os.path.expanduser('~/.tianfeng/metrics.db')

def init_db():
    os.makedirs(os.path.dirname(METRICS_DB),exist_ok=True)
    db=sqlite3.connect(METRICS_DB)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS operations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT, target TEXT, status TEXT,
            genes_found INTEGER, genes_used INTEGER,
            duration_ms INTEGER, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS daily_stats(
            date TEXT PRIMARY KEY,
            total_ops INTEGER, success_ops INTEGER,
            genes_consumed INTEGER, skills_crystallized INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_ops_cmd ON operations(command);
    """)
    db.commit()
    return db

def consume_gene(context: str, n: int = 5) -> dict:
    """消费基因: 从LGE搜索相关历史经验"""
    try:
        search_data=json.dumps({'query':context,'n_results':n}).encode()
        req=urllib.request.Request(f'{LGE}/genes/search',data=search_data,
            headers={'Content-Type':'application/json'},method='POST')
        resp=json.loads(urllib.request.urlopen(req,timeout=5).read())
        results=resp.get('results',[])
        
        genes=[]
        for r in results[:n]:
            genes.append({
                'id':r.get('gene_id',r.get('id','?')),
                'content':(r.get('content','') or '')[:200],
                'source':r.get('source','?'),
                'score':r.get('score',r.get('fitness_score',0))
            })
        return {'found':len(genes),'genes':genes,'context':context}
    except:
        return {'found':0,'genes':[],'error':'LGE不可达'}

def record_operation(command: str, target: str, status: str, genes_found: int, genes_used: int, duration_ms: int):
    """记录操作到指标库"""
    try:
        db=sqlite3.connect(METRICS_DB)
        db.execute("""INSERT INTO operations(command,target,status,genes_found,genes_used,duration_ms,created_at)
            VALUES(?,?,?,?,?,?,?)""",
            (command,target or '',status,genes_found,genes_used,duration_ms,datetime.now().isoformat()))
        db.commit()
        db.close()
    except: pass

def update_daily_stats():
    """更新每日统计"""
    try:
        db=sqlite3.connect(METRICS_DB)
        today=datetime.now().strftime('%Y-%m-%d')
        row=db.execute("SELECT COUNT(*),SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) FROM operations WHERE date(created_at)=?",(today,)).fetchone()
        total=row[0] or 0; success=row[1] or 0
        genes=db.execute("SELECT SUM(genes_consumed) FROM daily_stats WHERE date=?",(today,)).fetchone()[0] or 0
        
        db.execute("""INSERT OR REPLACE INTO daily_stats(date,total_ops,success_ops,genes_consumed,skills_crystallized)
            VALUES(?,?,?,?,?)""",(today,total,success,genes,0))
        db.commit()
        db.close()
    except: pass

def get_metrics() -> dict:
    """获取指标仪表盘"""
    init_db()
    db=sqlite3.connect(METRICS_DB)
    
    # 今日
    today=datetime.now().strftime('%Y-%m-%d')
    today_ops=db.execute("SELECT COUNT(*),SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) FROM operations WHERE date(created_at)=?",(today,)).fetchone()
    
    # 7天
    week_ops=db.execute("SELECT COUNT(*),SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) FROM operations WHERE created_at>datetime('now','-7 days')").fetchone()
    
    # 总基因消费
    total_genes=db.execute("SELECT SUM(genes_found) FROM operations").fetchone()[0] or 0
    
    # 按命令统计成功率
    cmd_stats=db.execute("""SELECT command,COUNT(*) t,SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) s 
        FROM operations WHERE created_at>datetime('now','-7 days') 
        GROUP BY command ORDER BY t DESC""").fetchall()
    
    # 进化速度: 最近7天vs前7天
    week1=db.execute("SELECT COUNT(*) FROM operations WHERE created_at BETWEEN datetime('now','-14 days') AND datetime('now','-7 days')").fetchone()[0] or 1
    week2=db.execute("SELECT COUNT(*) FROM operations WHERE created_at>datetime('now','-7 days')").fetchone()[0] or 1
    evolution_speed=week2*100//week1 if week1 else 100
    
    db.close()
    
    return {
        'today_ops':today_ops[0] or 0,'today_success':today_ops[1] or 0,
        'week_ops':week_ops[0] or 0,'week_success':week_ops[1] or 0,
        'total_genes_consumed':total_genes,
        'evolution_speed':evolution_speed,
        'cmd_stats':cmd_stats
    }

def get_dashboard(metrics: dict) -> str:
    """生成仪表盘"""
    today_sr=metrics['today_success']*100//metrics['today_ops'] if metrics['today_ops'] else 0
    week_sr=metrics['week_success']*100//metrics['week_ops'] if metrics['week_ops'] else 0
    
    lines=[
        "══════ 天锋PRO 指标仪表盘 ══════",
        "",
        f"今日操作: {metrics['today_ops']}次 · 成功率 {today_sr}%",
        f"7天操作:  {metrics['week_ops']}次 · 成功率 {week_sr}%",
        f"基因消费: {metrics['total_genes_consumed']}条 · 进化速度 {metrics['evolution_speed']}%",
        "",
        "7天命令统计:"
    ]
    for cmd,total,success in metrics['cmd_stats'][:5]:
        sr=success*100//total if total else 0
        bar='█'*(sr//10)+'░'*((100-sr)//10)
        lines.append(f"  {cmd:10s}: {total:3d}次·{sr:3d}% {bar}")
    
    return '\n'.join(lines)

if __name__=='__main__':
    # 自检
    init_db()
    print("基因消费环就绪 ✅")
    
    # 测试消费
    result=consume_gene('永动闭环 联邦 基因')
    print(f"消费测试: {result['found']}条基因")
    if result['genes']:
        print(f"  样例: {result['genes'][0]['content'][:100]}")
    
    # 仪表盘
    record_operation('status','self','success',result['found'],min(result['found'],1),150)
    update_daily_stats()
    print()
    print(get_dashboard(get_metrics()))
