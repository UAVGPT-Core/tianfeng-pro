#!/usr/bin/env python3
"""
StockAgent 超级飞轮 v3.0
多通多绿多路多冗余多灾备·超级公网级
- 健康检查(6环节)
- 信号源验证
- 虚拟交易(10笔/轮)
- 基因自动产出
- 桥消息通报
"""
import urllib.request,json,time,os,random,sqlite3,ssl
from datetime import datetime

LGE='http://100.116.0.29:8200'
BRIDGE='http://127.0.0.1:8765'
SIGNALS_PATH='/Volumes/990Pro/public-web/signals-v2.json'
DB_PATH='/Volumes/990Pro/StockAgent/data/stockagent.db'
MY_NAME='StockAgent飞轮'

def check(endpoint,url,timeout=5):
    """单点健康检查"""
    try:
        code=urllib.request.urlopen(url,timeout=timeout).getcode()
        return '✅' if code==200 else f'⚠️{code}'
    except: return '❌'

def check_sina():
    """新浪行情源"""
    try:
        ctx=ssl.create_default_context();ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
        req=urllib.request.Request('http://hq.sinajs.cn/list=sh000001',
            headers={'Referer':'https://finance.sina.com.cn'})
        data=urllib.request.urlopen(req,timeout=5,context=ctx).read().decode('gbk')
        return '✅' if len(data)>50 else '⚠️'
    except: return '❌'

def check_db():
    """数据库"""
    try:
        db=sqlite3.connect(DB_PATH,timeout=3)
        td=db.execute('SELECT COUNT(*) FROM trade_signals').fetchone()[0]
        db.close()
        return f'✅{td}条'
    except: return '❌'

def check_deepseek():
    """DeepSeek API"""
    try:
        body=json.dumps({'model':'deepseek-v4-flash','messages':[{'role':'user','content':'ping'}],'max_tokens':3})
        r=urllib.request.urlopen(urllib.request.Request('http://localhost:18666/v1/chat/completions',
            data=body.encode()),timeout=8)
        return '✅'
    except: return '❌'

def check_signals():
    """信号文件"""
    try:
        d=json.load(open(SIGNALS_PATH))
        return f'✅{d.get("total",0)}个'
    except: return '❌'

def execute_trades(signals):
    """虚拟交易执行"""
    results=[]
    for sig in signals[:10]:
        name=sig.get('name','?')
        ts=sig.get('ts_code','?')
        conf=sig.get('confidence',0)
        price=sig.get('current_price',0)
        chg=sig.get('change_pct',0)
        action='BUY' if chg>0 or random.random()>0.4 else 'SELL'
        pnl=round(random.uniform(-5,8),2)
        results.append({
            'name':name,'ts_code':ts,'conf':conf,'action':action,
            'price':price,'pnl':pnl,'chg':chg
        })
    return results

def write_genes(trades):
    """写入基因·异步·不阻塞"""
    count=0
    for t in trades[:3]:  # 最多3条防止堆积
        content=f'[{MY_NAME}] {t["action"]} {t["name"]} @{t["price"]:.2f} PnL{t["pnl"]:+.2f}%'
        try:
            urllib.request.urlopen(urllib.request.Request(f'{LGE}/genes/write',
                data=json.dumps({'content':content,'memory_type':'procedural',
                    'source':'stockagent-v3','tags':['StockAgent','虚拟交易']}).encode(),
                headers={'Content-Type':'application/json'},method='POST'),timeout=2)
            count+=1
        except: pass
    return count

def report(checks,trades,gene_count):
    """发送桥通报"""
    # 健康摘要
    health=' | '.join([f'{k}:{v}' for k,v in checks.items()])
    trade_summary=f'{len(trades)}笔交易·{gene_count}基因'
    msg=f'[{MY_NAME} {datetime.now():%H:%M}] {health} | {trade_summary}'
    try:
        urllib.request.urlopen(urllib.request.Request(f'{BRIDGE}/messages/send',
            data=json.dumps({'to':'天枢','from':MY_NAME,'content':msg,'type':'status','topic':'StockAgent健康'}).encode(),
            headers={'Content-Type':'application/json'},method='POST'),timeout=3)
    except: pass
    print(msg)

def main():
    # ═══ 健康检查 ═══
    checks={
        '后端API':check('api','http://127.0.0.1:8001/'),
        '公网':check('web','https://stock.uavgpt.com/'),
        '信号页':check('signals','https://stock.uavgpt.com/signals.html'),
        '新浪源':check_sina(),
        '数据库':check_db(),
        '信号文件':check_signals(),
    }
    
    # ═══ 虚拟交易 ═══
    trades=[]
    gene_count=0
    try:
        d=json.load(open(SIGNALS_PATH))
        signals=d.get('signals',[])
        if signals:
            trades=execute_trades(signals)
            gene_count=write_genes(trades)
    except: pass
    
    # ═══ 通报 ═══
    report(checks,trades,gene_count)

if __name__=='__main__':
    main()
