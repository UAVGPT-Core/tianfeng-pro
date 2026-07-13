#!/usr/bin/env python3
"""
LGOX文档检索引擎 v1.0 — BM25索引·替代Onyx
索引: ~/lgox-docs/ 全部文档
查询: 关键词匹配+BM25得分+gene_id追溯
基因ID: GENE-PRO-docs-engine-v1
"""
import os, re, json, time, hashlib, math
from pathlib import Path
from collections import Counter

DOCS_DIR = Path(os.path.expanduser("~/lgox-docs"))
INDEX_FILE = Path(os.path.expanduser("~/lgox-ops/data/docs-index.json"))

class DocsEngine:
    def __init__(self):
        self.docs = []  # [{path,content,title,words,tf,size,ts}]
        self.word_df = Counter()  # 文档频率
        self.total_docs = 0
        self.avg_len = 0
        self._load_index()

    def _load_index(self):
        if INDEX_FILE.exists():
            try:
                with open(INDEX_FILE) as f:
                    data = json.load(f)
                self.docs = data.get("docs", [])
                self.word_df = Counter(data.get("df", {}))
                self.total_docs = len(self.docs)
                self.avg_len = sum(d.get("size", 0) for d in self.docs) / max(self.total_docs, 1)
                self.incremental_update()  # 增量更新·不全量重建
                return
            except:
                pass
        self.rebuild()

    def tokenize(self, text: str) -> list:
        """中文2-3字滑动+英文分词"""
        tokens = []
        # 英文词
        tokens.extend(re.findall(r'[A-Za-z0-9]{2,}', text.lower()))
        # 中文2字
        cn = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        for c in cn:
            for i in range(len(c)-1):
                tokens.append(c[i:i+2])
        return tokens

    def incremental_update(self):
        """增量更新: 仅索引新增/修改的文档"""
        if not self.docs:
            return self.rebuild()

        existing = {d["path"] for d in self.docs}
        updated = 0

        for f in DOCS_DIR.glob("*"):
            if not f.is_file() or f.name in existing:
                continue
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
            except:
                continue
            words = self.tokenize(content)
            tf = Counter(words)
            doc = {
                "path": str(f.name),
                "title": f.name.rsplit(".", 1)[0],
                "content": content[:500],
                "words": list(set(words)),
                "tf": dict(tf.most_common(100)),
                "size": len(content),
                "ts": f.stat().st_mtime
            }
            self.docs.append(doc)
            for w in set(words):
                self.word_df[w] = self.word_df.get(w, 0) + 1
            self.total_docs += 1
            updated += 1

        # 检测修改: 按mtime
        for doc in self.docs:
            fp = DOCS_DIR / doc["path"]
            if fp.exists() and fp.stat().st_mtime > doc.get("ts", 0):
                try:
                    content = fp.read_text(encoding='utf-8', errors='replace')
                    words = self.tokenize(content)
                    tf = Counter(words)
                    # 减去旧词频
                    for w in doc.get("words", []):
                        self.word_df[w] = max(0, self.word_df.get(w, 0) - 1)
                    # 加新词频
                    for w in set(words):
                        self.word_df[w] = self.word_df.get(w, 0) + 1
                    doc["content"] = content[:500]
                    doc["words"] = list(set(words))
                    doc["tf"] = dict(tf.most_common(100))
                    doc["size"] = len(content)
                    doc["ts"] = fp.stat().st_mtime
                    updated += 1
                except:
                    pass

        if updated > 0:
            self._save_index()
        return updated

    def _save_index(self):
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INDEX_FILE, "w") as f:
            json.dump({"docs": self.docs, "df": dict(self.word_df), "updated": time.time()}, f, ensure_ascii=False)
        """全量重建索引"""
        docs = []
        word_df = Counter()
        for f in DOCS_DIR.glob("*"):
            if not f.is_file():
                continue
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
            except:
                continue
            words = self.tokenize(content)
            tf = Counter(words)
            docs.append({
                "path": str(f.name),
                "title": f.name.rsplit(".", 1)[0],
                "content": content[:500],
                "words": list(set(words)),
                "tf": dict(tf.most_common(100)),
                "size": len(content),
                "ts": f.stat().st_mtime
            })
            for w in set(words):
                word_df[w] += 1

        self.docs = docs
        self.word_df = word_df
        self.total_docs = len(docs)
        self.avg_len = sum(d["size"] for d in docs) / max(self.total_docs, 1)

        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INDEX_FILE, "w") as f:
            json.dump({"docs": docs, "df": dict(word_df), "updated": time.time()}, f, ensure_ascii=False)

    def search(self, query: str, top_k: int = 5) -> list:
        """BM25搜索"""
        if not self.docs:
            self.rebuild()
        q_terms = self.tokenize(query)
        if not q_terms:
            return []

        k1, b = 1.5, 0.75
        results = []
        for doc in self.docs:
            score = 0
            tf = doc.get("tf", {})
            dl = doc.get("size", 1)
            for t in q_terms:
                if t not in self.word_df:
                    continue
                f = tf.get(t, 0)
                df = self.word_df.get(t, 1)
                idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1)
                numerator = f * (k1 + 1)
                denominator = f + k1 * (1 - b + b * dl / max(self.avg_len, 1))
                score += idf * numerator / max(denominator, 0.001)
            if score > 0:
                results.append({
                    "score": round(score, 3),
                    "title": doc["title"],
                    "path": str(DOCS_DIR / doc["path"]),
                    "content": doc.get("content", "")[:300],
                    "source": "Docs",
                    "gene_id": f"GENE-DOC-{hashlib.sha256(doc['path'].encode()).hexdigest()[:12]}"
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# 单例
_engine = DocsEngine()

def docs_search(query: str) -> list:
    return _engine.search(query)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "rebuild":
            _engine.rebuild()
            print(f"索引完成: {_engine.total_docs}篇文档")
        elif sys.argv[1] == "update":
            n = _engine.incremental_update()
            print(f"增量更新: {n}篇变更")
        elif sys.argv[1] == "search":
            q = " ".join(sys.argv[2:])
            for r in _engine.search(q):
                print(f"  [{r['score']}] {r['title']}: {r['content'][:80]}...")
        elif sys.argv[1] == "stats":
            print(f"文档数: {_engine.total_docs}, 词表: {len(_engine.word_df)}")
    else:
        print(f"DocsEngine v1.0: {_engine.total_docs} docs indexed")
