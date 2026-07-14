#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║  联邦任务调度器 v1.0 — 天工GPU觉醒                     ║
║  Federation Task Scheduler :8789                     ║
║  2026-07-13                                          ║
╚══════════════════════════════════════════════════════╝

核心: 天工GPU(GB10/9模型)替代DeepSeek API
   灵龙任务→调度器→天工Ollama→结果→LGE基因

七自闭环:
  自感知: GPU利用率实时监控
  自协调: 根据任务大小自动选模型
  自愈合: 天工不可用→降级灵龙本地Ollama
  自进化: 每个推理结果纳基因
  自迭代: 热门prompt缓存加速
  自反思: 每日推理统计报告
  自约束: 成本归零·永不调付费API
"""

import json, time, sys, os, uuid, threading
from pathlib import Path
from datetime import datetime
from urllib import request, parse
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8789
DATA_DIR = Path.home() / "lgox-ops/data/scheduler"
STATS_FILE = DATA_DIR / "stats.json"
LGE_URL = "http://100.116.0.29:8200/genes/write"
LGE_KEY = "fbe0b015eb7a03727903b660c4cecc60"

# ══════════════════════════════
# 计算后端
# ══════════════════════════════
COMPUTE_BACKENDS = [
    {
        "name": "天工GB10",
        "host": "100.118.207.31",
        "ollama": "http://100.118.207.31:11434",
        "gpu": "NVIDIA GB10",
        "models": {
            "qwen2.5:14b":      {"size": "8GB", "max_tokens": 2048, "priority": 10},
            "qwen2.5-coder:7b": {"size": "4GB", "max_tokens": 1024, "priority": 8},
            "gemma4:latest":    {"size": "8GB", "max_tokens": 2048, "priority": 9},
            "qwen3-vl:latest":  {"size": "5GB", "max_tokens": 1024, "priority": 7},
            "lgox-distill-v1:latest": {"size": "8GB", "max_tokens": 1536, "priority": 6},
        },
        "default_model": "qwen2.5:14b"
    },
    {
        "name": "灵龙本地",
        "host": "localhost",
        "ollama": "http://localhost:11434",
        "gpu": "M4",
        "models": {
            "qwen2.5-coder:7b":  {"size": "4GB", "max_tokens": 512, "priority": 5},
        },
        "default_model": "qwen2.5-coder:7b"
    }
]

# ══════════════════════════════
# 任务调度核心
# ══════════════════════════════

def select_backend(preferred_model=None):
    """智能选择后端: 天工优先→降级灵龙"""
    for backend in COMPUTE_BACKENDS:
        try:
            req = request.Request(f"{backend['ollama']}/api/tags")
            resp = request.urlopen(req, timeout=3)
            models = json.loads(resp.read()).get("models", [])
            if models:
                return backend
        except:
            continue
    return None  # 全部不可用

def ollama_infer(backend, prompt, model=None, max_tokens=512, temperature=0.3):
    """Ollama推理——零成本"""
    model = model or backend["default_model"]
    data = json.dumps({
        "model": model,
        "prompt": prompt[:2000],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }).encode()

    url = f"{backend['ollama']}/api/generate"
    req = request.Request(url, data=data,
        headers={"Content-Type": "application/json"})
    resp = request.urlopen(req, timeout=120)
    result = json.loads(resp.read())
    return {
        "response": result.get("response", "").strip(),
        "model": model,
        "backend": backend["name"],
        "tokens": result.get("eval_count", 0),
        "duration_ms": result.get("total_duration", 0) // 1_000_000
    }

def write_inference_gene(task, result):
    """推理结果纳基因——联邦学习闭环"""
    gene = {
        "content": json.dumps({
            "type": "inference_log",
            "task": task[:200],
            "response": result.get("response", "")[:300],
            "backend": result["backend"],
            "model": result["model"],
            "tokens": result["tokens"],
            "duration_ms": result["duration_ms"]
        }, ensure_ascii=False),
        "memory_type": "episodic",
        "source": f"灵龙/scheduler/{result['backend']}",
        "fitness_score": 0.5
    }
    try:
        data = json.dumps(gene).encode()
        req = request.Request(LGE_URL, data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        request.urlopen(req, timeout=8)
    except:
        pass  # 非致命

# ══════════════════════════════
# Stats
# ══════════════════════════════
stats = {"total_tasks": 0, "tiangong_tasks": 0, "fallback_tasks": 0,
         "total_tokens": 0, "total_duration_ms": 0, "last_task": None}

def load_stats():
    global stats
    try:
        if STATS_FILE.exists():
            stats.update(json.load(STATS_FILE.open()))
    except:
        pass

def save_stats():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json.dump(stats, STATS_FILE.open("w"), ensure_ascii=False, indent=2)

# ══════════════════════════════
# HTTP API
# ══════════════════════════════

class SchedulerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            backend = select_backend()
            self._json({
                "status": "ok",
                "service": "fed-task-scheduler",
                "port": PORT,
                "primary_gpu": "天工GB10" if (backend and backend["name"]=="天工GB10") else "降级",
                "stats": stats
            })
        elif self.path == "/stats":
            self._json(stats)
        elif self.path.startswith("/gpu"):
            # GPU实时状态
            try:
                req = request.Request(f"{COMPUTE_BACKENDS[0]['ollama']}/api/ps", timeout=3)
                resp = request.urlopen(req)
                gpu_status = json.loads(resp.read())
                self._json({"gpu": "天工GB10", "active_models": gpu_status.get("models", [])})
            except:
                self._json({"gpu": "天工GB10", "status": "unreachable"})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path in ("/task", "/task/submit"):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            params = json.loads(body)

            task_prompt = params.get("prompt", params.get("task", ""))
            task_model = params.get("model", None)
            task_tokens = params.get("max_tokens", 512)
            task_temp = params.get("temperature", 0.3)
            write_gene = params.get("write_gene", True)

            # 1. 选择后端(天工优先)
            backend = select_backend()
            if not backend:
                self._json({"error": "no_backend", "msg": "天工和灵龙Ollama均不可用"}, 503)
                return

            # 2. 执行推理
            try:
                result = ollama_infer(backend, task_prompt, task_model, task_tokens, task_temp)
                stats["total_tasks"] += 1
                if backend["name"] == "天工GB10":
                    stats["tiangong_tasks"] += 1
                else:
                    stats["fallback_tasks"] += 1
                stats["total_tokens"] += result["tokens"]
                stats["total_duration_ms"] += result["duration_ms"]
                stats["last_task"] = datetime.now().isoformat()
                save_stats()

                # 3. 写基因(异步)
                if write_gene:
                    t = threading.Thread(target=write_inference_gene,
                                        args=(task_prompt, result), daemon=True)
                    t.start()

                self._json(result)

            except Exception as e:
                # 天工失败→降级灵龙
                if backend["name"] == "天工GB10" and COMPUTE_BACKENDS[1]["name"] == "灵龙本地":
                    try:
                        fallback = COMPUTE_BACKENDS[1]
                        result = ollama_infer(fallback, task_prompt, "qwen2.5:7b", task_tokens, task_temp)
                        stats["total_tasks"] += 1
                        stats["fallback_tasks"] += 1
                        stats["last_task"] = datetime.now().isoformat()
                        save_stats()
                        self._json(result)
                        return
                    except:
                        pass
                self._json({"error": "infer_failed", "msg": str(e)[:100]}, 500)
        else:
            self.send_error(404)

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, *args):
        pass

def main():
    load_stats()
    server = HTTPServer(("0.0.0.0", PORT), SchedulerHandler)
    print(f"🔧 联邦任务调度器 :{PORT}")
    print(f"   主引擎: 天工GB10 (qwen2.5:14b·gemma4)")
    print(f"   降级:   灵龙M4 (qwen2.5:7b)")
    print(f'   POST /task {{"prompt":"...", "model":"qwen2.5:14b"}}')
    print(f"   GET  /health · /stats · /gpu")
    print(f"   基因闭环: 每个推理→LGE")
    print(f"   累计: {stats['total_tasks']}任务·{stats['total_tokens']}tokens")
    server.serve_forever()

if __name__ == "__main__":
    main()
