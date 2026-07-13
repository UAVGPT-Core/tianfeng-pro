#!/usr/bin/env python3
"""
天工推理CLI — 任何脚本一行调用天工GPU
用法:
  python3 tiangong_infer.py "你的问题"
  echo "问题" | python3 tiangong_infer.py
  python3 tiangong_infer.py --model qwen2.5-coder:7b "代码问题"
"""
import json, sys, os
from urllib import request

SCHEDULER = os.environ.get("TIANGONG_URL", "http://127.0.0.1:8789")

def main():
    args = sys.argv[1:]
    model = "qwen2.5:14b"
    prompt = ""

    # Parse --model
    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        else:
            prompt = args[i]
            i += 1

    # Read from stdin if no prompt
    if not prompt:
        prompt = sys.stdin.read().strip()

    if not prompt:
        print("用法: python3 tiangong_infer.py [--model XXX] '你的问题'", file=sys.stderr)
        sys.exit(1)

    data = json.dumps({
        "prompt": prompt,
        "model": model,
        "max_tokens": 200,
        "temperature": 0.3,
        "write_gene": True
    }).encode()

    req = request.Request(f"{SCHEDULER}/task", data=data,
        headers={"Content-Type": "application/json"})
    resp = request.urlopen(req, timeout=120)
    result = json.loads(resp.read())

    if "error" in result:
        print(f"ERROR: {result['msg']}", file=sys.stderr)
        sys.exit(1)

    print(result.get("response", ""))
    sys.stderr.write(f"[{result.get('backend','?')}:{result.get('model','?')} {result.get('tokens',0)}t/{result.get('duration_ms',0)}ms]\n")

if __name__ == "__main__":
    main()
