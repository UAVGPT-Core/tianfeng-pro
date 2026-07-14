#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║  NGC NIM部署引擎 — 天工+地枢GPU全火力                   ║
║  NVIDIA Inception资源榨干·NGC容器·TensorRT·NIM微服务    ║
╚══════════════════════════════════════════════════════════╝

NGC Inception会员资源:
  ✅ NGC API (121模型·HTTP推理) — 已接入fuel_router
  ✅ NGC 容器注册表 (nvcr.io) — NIM微服务·优化镜像
  ✅ TensorRT-LLM — GPU推理加速
  ✅ NVIDIA Triton — 推理服务器
  ✅ CUDA工具链 — 已在DGX预装
  ✅ 硬件折扣 — DGX GB10/DGX2
  
天工DGX1(GB10 GPU·Ubuntu·9 Ollama模型):
  → 部署 NGC NIM 轻量容器(nemotron-nano·llama-vision)
  → TensorRT加速qwen2.5:14b推理
  → Triton推理服务器统一入口

地枢DGX2(LGE引擎·Neo4j·GPU):
  → 部署 NGC 嵌入服务(nv-embedqa)
  → Neo4j+GNN图推理加速
  → 基因向量化批量服务
"""

import json, os, sys, subprocess
from pathlib import Path

def run_remote(host, cmd, timeout=30):
    try:
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=5", host, cmd],
            capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except:
        return "", 1

def check_dgx_gpu(host="dgx1"):
    """检查DGX GPU状态"""
    out, rc = run_remote(host, "nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null")
    if out:
        print(f"🟢 {host} GPU:")
        for line in out.split("\n"):
            print(f"   {line}")
    else:
        print(f"🔴 {host}: GPU不可达")

def check_docker(host="dgx1"):
    """检查Docker/NGC容器"""
    out, rc = run_remote(host, "docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | head -5")
    if out:
        print(f"🟢 {host} Docker容器: {len(out.split(chr(10)))}个运行")
        for line in out.split("\n")[:5]:
            print(f"   {line}")
    else:
        print(f"🔴 {host}: Docker不可用或无容器")

def deploy_nim_services():
    """部署NGC NIM微服务到天工"""
    print("\n═══ NGC NIM部署 ═══")
    print("天工DGX1 → nemotron推理+vision服务")
    print("地枢DGX2 → embed嵌入服务")
    
    # 检查NGC CLI
    out, rc = run_remote("dgx1", "which ngc 2>/dev/null || echo 'not found'")
    print(f"NGC CLI: {'🟢' if rc==0 else '🔴需安装'} {out[:50]}")
    
    # Docker login to NGC
    out, rc = run_remote("dgx1", "docker pull nvcr.io/nvidia/nim/nemotron-nano:latest 2>&1 | tail -1", timeout=60)
    if "Downloaded" in out or "up to date" in out.lower():
        print(f"🟢 nemotron-nano NIM镜像: 就绪")
    else:
        print(f"🔴 NIM镜像拉取: {out[:100]}")
    
    # 检查TensorRT
    out, rc = run_remote("dgx1", "python3 -c 'import tensorrt; print(tensorrt.__version__)' 2>/dev/null")
    print(f"TensorRT: {'🟢 '+out if rc==0 else '🔴未安装'}")

def federated_gpu_report():
    """联邦GPU资源全景"""
    print("\n═══ 联邦GPU资源全景 ═══")
    print("""
┌──────────┬──────────┬─────────────────────┬──────────┐
│ 节点     │ GPU      │ NGC能力              │ 状态     │
├──────────┼──────────┼─────────────────────┼──────────┤
│ 天工DGX1 │ GB10     │ Ollama9模型+NIM      │ 🟢 主力  │
│          │          │ TensorRT加速         │          │
│ 地枢DGX2 │ DGX GPU  │ LGE+Neo4j+embed     │ 🟡 待挖  │
│ 灵龙M4   │ M4 NPU   │ 本地推理·Worker      │ 🟢 守夜  │
│ 天枢M2   │ M2 NPU   │ 驾驶舱·桥·宪法       │ 🟢 守夜  │
└──────────┴──────────┴─────────────────────┴──────────┘
    """)

if __name__ == "__main__":
    print("═══ NGC NIM部署引擎 ═══")
    check_dgx_gpu("dgx1")
    check_docker("dgx1")
    check_dgx_gpu("dgx2")  # 地枢
    check_docker("dgx2")
    deploy_nim_services()
    federated_gpu_report()
