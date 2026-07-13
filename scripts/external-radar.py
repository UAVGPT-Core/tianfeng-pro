#!/usr/bin/env python3
"""
LGOX联邦外部雷达 v1.0 — AI灯塔·感知世界
arXiv论文 + GitHub趋势 + HuggingFace热门 + RSS行业动态
自动摄入→LGE基因→联邦广播→全节点学习
"""
import urllib.request,json,time,os,xml.etree.ElementTree as ET
from datetime import datetime

LGE='http://100.116.0.29:8200'
BRIDGE='http://127.0.0.1:8765'
GENES_WRITTEN=0

def write_gene(content,source,tags):
    global GENES_WRITTEN
    try:
        data=json.dumps({'content':content[:1200],'memory_type':'semantic',
            'source':source,'tags':tags+['external-radar','auto-ingest'],
            'node':'天枢/外部雷达'},ensure_ascii=False).encode()
        req=urllib.request.Request(f'{LGE}/genes/write',data=data,headers={'Content-Type':'application/json'})
        r=json.loads(urllib.request.urlopen(req,timeout=10).read())
        if r.get('gene_id'):
            GENES_WRITTEN+=1
            return r['gene_id']
    except Exception as e:
        print(f'  gene write err: {e}')
    return None

def broadcast(topic,content):
    try:
        data=json.dumps({'to':'all','from':'天枢/外部雷达','content':content,
            'type':'knowledge_pack','topic':topic},ensure_ascii=False).encode()
        req=urllib.request.Request(f'{BRIDGE}/messages/send',data=data,headers={'Content-Type':'application/json'},method='POST')
        urllib.request.urlopen(req,timeout=5)
    except:pass

# ═══ arXiv 扫描 ═══
def scan_arxiv():
    print('[arXiv] 扫描AI/ML最新论文...')
    queries=['large+language+model','AI+agent','multi+agent+system','RAG+retrieval','autonomous+agent']
    total=0
    for q in queries:
        try:
            url=f'http://export.arxiv.org/api/query?search_query=all:{q}&sortBy=submittedDate&sortOrder=descending&max_results=3'
            resp=urllib.request.urlopen(url,timeout=15)
            root=ET.fromstring(resp.read())
            ns={'a':'http://www.w3.org/2005/Atom'}
            for entry in root.findall('a:entry',ns)[:3]:
                title=entry.find('a:title',ns).text.strip().replace('\n',' ')
                summary=entry.find('a:summary',ns).text.strip()[:300]
                arxiv_id=entry.find('a:id',ns).text.split('/')[-1]
                gene_content=f'[arXiv] {title}\n{summary}\nID:{arxiv_id}'
                write_gene(gene_content,f'arxiv-{arxiv_id}',['arXiv','paper',q.replace('+',' ')])
                total+=1
        except Exception as e:
            print(f'  arXiv[{q}] err: {e}')
    print(f'[arXiv] {total}篇论文入库')

# ═══ GitHub Trending ═══
def scan_github():
    print('[GitHub] 扫描AI趋势仓库...')
    try:
        url='https://api.github.com/search/repositories?q=AI+agent+autonomous&sort=stars&order=desc&per_page=5'
        req=urllib.request.Request(url,headers={'Accept':'application/vnd.github.v3+json','User-Agent':'LGOX-Radar'})
        resp=urllib.request.urlopen(req,timeout=15)
        data=json.loads(resp.read())
        total=0
        for repo in data.get('items',[])[:5]:
            name=repo['full_name']
            desc=repo.get('description','') or ''
            stars=repo['stargazers_count']
            url=repo['html_url']
            gene_content=f'[GitHub] {name} ⭐{stars}\n{desc}\n{url}'
            write_gene(gene_content,f'github-{name}',['GitHub','trending','AI'])
            total+=1
        print(f'[GitHub] {total}个仓库入库')
    except Exception as e:
        print(f'  GitHub err: {e}')

# ═══ HuggingFace 热门 ═══
def scan_huggingface():
    print('[HuggingFace] 扫描热门模型...')
    try:
        url='https://huggingface.co/api/models?sort=downloads&direction=-1&limit=5&filter=text-generation'
        req=urllib.request.Request(url,headers={'User-Agent':'LGOX-Radar'})
        resp=urllib.request.urlopen(req,timeout=15)
        data=json.loads(resp.read())
        total=0
        for model in data[:5]:
            mid=model.get('modelId','') or model.get('id','')
            downloads=model.get('downloads',0)
            likes=model.get('likes',0)
            gene_content=f'[HuggingFace] {mid} ↓{downloads} 👍{likes}'
            write_gene(gene_content,f'hf-{mid}',['HuggingFace','model','trending'])
            total+=1
        print(f'[HuggingFace] {total}个模型入库')
    except Exception as e:
        print(f'  HuggingFace err: {e}')

# ═══ 主流程 ═══
if __name__=='__main__':
    ts=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[外部雷达v1.0] {ts} 启动扫描...')
    
    scan_arxiv()
    scan_github()
    scan_huggingface()
    
    print(f'\n[外部雷达] 完成. 写入{ GENES_WRITTEN}条基因')
    
    if GENES_WRITTEN>0:
        broadcast('外部雷达','外部雷达扫描完成: arXiv+GitHub+HuggingFace, 写入LGE基因, 全联邦可检索')
    
    print(f'[{datetime.now().strftime("%H:%M:%S")}] 外部雷达扫描结束')
