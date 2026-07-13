#!/usr/bin/env python3
"""
天影×video-use 融合引擎 v1.0
灵龙编导 + 天工GPU = 一句话剪片全自动
基因ID: GENE-PRO-tianying-videouse-fusion
"""
import subprocess, json, os, sys
from pathlib import Path

VIDEO_USE = Path.home() / "Developer/video-use"
TIANYING = Path.home() / "lgox-ops/scripts"
GPU_NODE = "uavgpt@100.118.207.31"  # 天工GPU

class TianYingDirector:
    """天影编导: 融合video-use智能剪辑+天影批量生产"""
    
    def __init__(self):
        self.video_use_helpers = VIDEO_USE / "helpers"
        self.ffmpeg = "/opt/homebrew/bin/ffmpeg"
    
    def smart_edit(self, input_dir, prompt="edit into final video"):
        """一句话剪片: Codex驱动video-use"""
        cmd = f"cd {input_dir} && npx codex -p '{prompt}'"
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    
    def batch_produce(self, input_dir, template="default"):
        """天影批量生产: FFmpeg+HyperFrames"""
        script = TIANYING / f"tiaying-{template}.py"
        if script.exists():
            return subprocess.run(["python3", str(script), input_dir], capture_output=True, text=True)
        return None
    
    def remote_gpu_render(self, input_dir):
        """路由天工GPU渲染(天工在线时)"""
        try:
            r = subprocess.run(["ssh", "-o", "ConnectTimeout=5", GPU_NODE, "echo OK"],
                capture_output=True, text=True, timeout=8)
            if "OK" in r.stdout:
                # 天工在线→SCP素材→GPU渲染→拉回
                subprocess.run(["scp", "-r", input_dir, f"{GPU_NODE}:/tmp/tiaying-input/"],
                    timeout=30)
                subprocess.run(["ssh", GPU_NODE, 
                    f"cd /tmp/tiaying-input && ffmpeg -i *.mp4 -c:v h264_nvenc -preset fast output.mp4"],
                    timeout=120)
                subprocess.run(["scp", f"{GPU_NODE}:/tmp/tiaying-input/output.mp4", 
                    f"{input_dir}/gpu-rendered.mp4"], timeout=30)
                return True
        except:
            pass
        return False

if __name__ == "__main__":
    director = TianYingDirector()
    print("🎬 天影×video-use 融合引擎 v1.0")
    print(f"   video-use: {VIDEO_USE}")
    print(f"   天影: {TIANYING}")
    print(f"   GPU节点: {GPU_NODE}")
    print(f"   ffmpeg: {director.ffmpeg}")
    print("就绪。丢素材→说一句话→全自动剪片。")
