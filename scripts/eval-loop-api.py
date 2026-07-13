#!/usr/bin/env python3
"""
LGOX评测闭环引擎 v1.0
端口:8771 层:L6(反思层·评测)
评估对话质量: 准确性·完整性·相关性·幻觉检测
自动纳基因·驱动质量飞轮
基因ID: GENE-PRO-eval-loop-v1
"""
import json, hashlib, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request

LGE_URL = "http://100.116.0.29:8200"

EVAL_DIMENSIONS = {
    "accuracy": "回答事实准确度(0-1)",
    "completeness": "信息完整度(0-1)",
    "relevance": "与问题相关性(0-1)",
    "hallucination": "幻觉检测(越高越严重,0-1)",
    "actionability": "可操作性(0-1)",
}

def score_answer(question: str, answer: str) -> dict:
    """启发式评测·v3精细版"""
    scores = {}
    a_len = len(answer)
    has_digits = any(c.isdigit() for c in answer)
    has_ref = any(kw in answer.lower() for kw in ['gene', '参考', '来源', 'http', '端口', ':', 'GENE', '://'])
    has_structure = '\n' in answer or '：' in answer or ':' in answer or '。' in answer
    has_action = any(kw in answer for kw in ['步骤', '执行', '运行', '操作', '命令', '部署', '配置', '安装', '启动', '调用'])
    
    # 准确性v3: 放宽基线
    scores["accuracy"] = round(min(1.0, (
        0.35 if has_digits else 0.15 +
        0.35 if has_ref else 0.15 +
        0.2 if a_len > 100 else (0.15 if a_len > 40 else 0.05) +
        0.1
    )), 3)
    
    # 完整性v3
    scores["completeness"] = round(min(1.0, (
        0.4 if a_len > 200 else (0.3 if a_len > 100 else 0.2) +
        0.3 if has_structure else 0.15 +
        0.3
    )), 3)
    
    # 相关性v3
    q_words = set(question.lower().split())
    a_words = set(answer.lower().split())
    overlap = len(q_words & a_words) / max(len(q_words), 1)
    scores["relevance"] = round(min(1.0, overlap + 0.45), 3)

    # 幻觉v3
    h = 0
    if a_len > 300 and not has_ref: h += 0.15
    if a_len > 100 and not has_ref: h += 0.1
    if '一定' in answer or '肯定' in answer or '绝对' in answer: h += 0.15
    if a_len < 10: h += 0.6
    scores["hallucination"] = round(min(1.0, h), 3)

    # 可操作性v3
    scores["actionability"] = round(min(1.0, (
        0.45 if has_action else 0.15 +
        0.3 if a_len > 100 else (0.2 if a_len > 50 else 0.1) +
        0.25
    )), 3)

    raw = sum(scores[k] for k in ["accuracy","completeness","relevance","actionability"]) / 4
    scores["overall"] = round(raw * (1.0 - scores["hallucination"] * 0.4), 3)
    scores["grade"] = "A" if scores["overall"] >= 0.6 else "B" if scores["overall"] >= 0.4 else "C"
    return scores

def write_eval_gene(question: str, answer: str, scores: dict) -> str:
    """异步写LGE基因(带超时·不阻塞响应)"""
    import threading
    gene_id = f"GENE-EVAL-{hashlib.sha256((question+answer).encode()).hexdigest()[:12]}"
    
    def _write():
        payload = json.dumps({
            "gene_id": gene_id,
            "content": json.dumps({"q": question[:500], "a": answer[:500], "scores": scores}, ensure_ascii=False),
            "category": "evaluation",
            "domain": "meta",
            "quality_score": scores.get("overall", 0.5),
            "tags": ["eval-loop", f"grade-{scores.get('grade','C')}"]
        }).encode()
        try:
            req = urllib.request.Request(f"{LGE_URL}/genes/write", data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=2) as resp:
                pass
        except:
            pass
    
    t = threading.Thread(target=_write, daemon=True)
    t.start()
    return f"async:{gene_id}"

class EvalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._json({"status":"ok","service":"LGOX评测闭环引擎","version":"1.0","layer":"L6反思层(Reflect)"})
        elif path == "/dimensions":
            self._json(EVAL_DIMENSIONS)
        else:
            self._json({"error":"use POST /eval"})

    def do_POST(self):
        if urlparse(self.path).path == "/eval":
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            try:
                data = json.loads(body)
                question = data.get("question", data.get("q", ""))
                answer = data.get("answer", data.get("a", ""))
                if not question or not answer:
                    self._json({"error": "need question and answer"}, 400)
                    return
                scores = score_answer(question, answer)
                gene_status = write_eval_gene(question, answer, scores)
                self._json({"scores": scores, "gene": gene_status})
            except json.JSONDecodeError:
                self._json({"error": "invalid json"}, 400)
        else:
            self._json({"error": "not found"}, 404)

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    def log_message(self, *args): pass

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8771
    HTTPServer(('127.0.0.1', port), EvalHandler).serve_forever()
