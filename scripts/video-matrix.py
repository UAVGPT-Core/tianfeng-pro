#!/usr/bin/env python3
"""
LGOX 视频能力矩阵 v1.0 — 三大将·6技能·天影大脑
══════════════════════════════════════════════
路由: 天锋PRO(编排)·LGOX-CC(代码生成)·Codex(快速执行)
基因ID: GENE-PRO-video-matrix-v1
"""
import json, subprocess, os, time, hashlib, urllib.request
from pathlib import Path

LGE = "http://100.116.0.29:8200"
BRIDGE = "http://127.0.0.1:8765"

# ═══ 6技能定义 ═══
SKILLS = {
    "hyperframes": {
        "name": "HyperFrames",
        "desc": "HTML→MP4·一句话生成内容渲染",
        "router": "天锋PRO",  # 编排
        "reason": "HTML模板+多scene编排·需全栈能力",
        "command": "npx hyperframes render {input} -o {output}",
        "input": "HTML模板文件",
        "output": "MP4视频",
    },
    "videouse": {
        "name": "VideoUse",
        "desc": "删停顿·加字幕·调色·动效",
        "router": "Codex",  # 快速执行
        "reason": "单步AI操作·快速剪辑·即用即走",
        "command": "python3 extract_highlights.py --input {input} --output {output}",
        "input": "原始视频",
        "output": "精剪视频",
    },
    "remotion": {
        "name": "Remotion",
        "desc": "React代码批量制作视频",
        "router": "LGOX-CC",  # 代码生成
        "reason": "代码即视频·JSX编程·批量自动化",
        "command": "cd remotion-composer && npx remotion render src/index.tsx --output={output}",
        "input": "React组件",
        "output": "MP4视频",
    },
    "generative_media": {
        "name": "Generative Media",
        "desc": "AI图片·视频·音频全覆盖生成",
        "router": "天锋PRO",  # 多模态编排
        "reason": "多模型调度·GPU资源·prompt工程",
        "command": "python3 generate_media.py --prompt '{prompt}' --type {type}",
        "input": "自然语言prompt",
        "output": "图片/视频/音频",
    },
    "videocut": {
        "name": "VideoCut",
        "desc": "中文创作者剪辑·字幕·B站优化",
        "router": "LGOX-CC",  # 中文内容处理
        "reason": "中文NLP·字幕时间轴·结构化处理",
        "command": "ffmpeg -i {input} -vf 'subtitles={subtitle_file}' -c:v h264_videotoolbox {output}",
        "input": "视频+SRT字幕",
        "output": "硬字幕MP4",
    },
    "seedance2": {
        "name": "Seedance2",
        "desc": "逐秒分镜设计·提示词工程",
        "router": "天锋PRO",  # 设计思维
        "reason": "创意设计·场景规划·prompt链",
        "command": "python3 storyboard_gen.py --script '{script}' --output storyboard.json",
        "input": "文字脚本",
        "output": "分镜JSON",
    },
}

class VideoMatrix:
    def __init__(self):
        self.version = "1.0.0"
        self.skills = SKILLS
        self.routing_stats = {"天锋PRO": 0, "LGOX-CC": 0, "Codex": 0}
    
    def route(self, task: str) -> dict:
        """智能路由：根据任务匹配最佳大将+技能"""
        task_lower = task.lower()
        scores = {}
        
        for skill_id, skill in self.skills.items():
            keywords = skill["name"].lower().split() + skill["desc"].lower().split()
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > 0:
                scores[skill_id] = score
        
        if not scores:
            # 默认路由：文字→HyperFrames，视频→VideoUse，代码→Remotion
            if any(kw in task_lower for kw in ["html","网页","页面"]):
                best = "hyperframes"
            elif any(kw in task_lower for kw in ["剪辑","编辑","字幕","裁剪"]):
                best = "videouse"
            elif any(kw in task_lower for kw in ["代码","批量","程序","react"]):
                best = "remotion"
            elif any(kw in task_lower for kw in ["生成","ai","图片","音频"]):
                best = "generative_media"
            elif any(kw in task_lower for kw in ["中文","b站","bilibili"]):
                best = "videocut"
            elif any(kw in task_lower for kw in ["分镜","脚本","故事板"]):
                best = "seedance2"
            else:
                best = "hyperframes"  # 默认
        else:
            best = max(scores, key=scores.get)
        
        skill = self.skills[best]
        router = skill["router"]
        self.routing_stats[router] += 1
        
        return {
            "skill": best,
            "skill_name": skill["name"],
            "router": router,
            "reason": skill["reason"],
            "command_template": skill["command"],
        }
    
    def execute(self, task, input_file, output_file):
        """执行视频任务"""
        route = self.route(task)
        
        # 构建命令
        cmd_str = route["command_template"].format(
            input=input_file, output=output_file,
            prompt=task, type="video",
            subtitle_file=input_file.replace(".mp4",".srt"),
            script=task
        )
        
        result = {
            "task": task,
            "route": route,
            "command": cmd_str,
            "status": "routed"
        }
        
        # 基因固化
        gene_id = f"GENE-VIDEO-{hashlib.sha256((task+cmd_str).encode()).hexdigest()[:12]}"
        self._write_gene(gene_id, f"video_route:{route['skill']}", 
            json.dumps(result, ensure_ascii=False)[:500],
            category="video", quality=0.7)
        result["gene"] = gene_id[:12]
        
        return result
    
    def arsenal_report(self):
        """三大将视频武装报告"""
        print("═══ 三大将·6技能视频武装 ═══\n")
        
        for skill_id, skill in self.skills.items():
            router = skill["router"]
            icon = {"天锋PRO":"🎯","LGOX-CC":"💻","Codex":"⚡"}.get(router,"🔧")
            print(f"{icon} {skill['name']:20s} → {router:8s} | {skill['desc']}")
        
        print(f"\n═══ 路由统计 ═══")
        for general, count in self.routing_stats.items():
            print(f"  {general}: {count}次")
        
        print(f"\n═══ 天影pipeline对接 ═══")
        print(f"  天枢: OpenMontage + FFmpeg + Remotion + HyperFrames")
        print(f"  灵龙: 武装引擎 → 三大将路由 → 天枢执行")
        print(f"  天工: GPU生成(wan_video/hunyuan) + 本地推理")
    
    def _write_gene(self, gene_id, title, content, category="general", quality=0.5):
        try:
            payload = json.dumps({
                "gene_id": gene_id, "content": f"{title}\n{content[:1000]}",
                "category": category, "domain": "video",
                "quality_score": quality,
                "tags": ["video-matrix", "三大将", "天影"]
            }).encode()
            req = urllib.request.Request(f"{LGE}/genes/write", data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=3)
        except:
            pass

if __name__ == "__main__":
    vm = VideoMatrix()
    
    # 测试路由
    tests = [
        "做一条60秒LGOX产品介绍视频",
        "给这个巡检视频加中文字幕和缺陷标注",
        "批量生成100条短视频",
        "设计一个无人机巡检的分镜脚本",
        "生成AI数字人播报视频",
        "给这个视频做个B站风格的片头",
    ]
    
    print("═══ 智能路由测试 ═══")
    for t in tests:
        r = vm.route(t)
        print(f"  '{t[:30]}...' → {r['router']}/{r['skill_name']}")
    
    print()
    vm.arsenal_report()
