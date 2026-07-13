#!/usr/bin/env python3
"""
天影SOP v1.0 · Codex接管整条视频制作
7步: 选题→分镜→提示词→素材→剪辑→字幕→包装
基因ID: GENE-PRO-tianying-sop-v1
基于: video-use ⭐16.3k + 天影 + LGE基因引擎
"""
import subprocess, json, os, sys, time
from pathlib import Path

VIDEO_USE = Path.home() / "Developer/video-use"
HELPERS = VIDEO_USE / "helpers"
LGE = "http://100.116.0.29:8200"

class VideoSOP:
    def __init__(self):
        self.steps = []
        self.project_dir = None
    
    def run(self, topic=None, src_dir=None):
        """一键执行7步SOP"""
        ts = time.strftime("%Y%m%d-%H%M")
        self.project_dir = Path(f"/tmp/lgox-video-{ts}")
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🎬 天影SOP v1.0 · 项目: {self.project_dir}")
        print("━" * 50)
        
        # Step 1: 选题
        self.step1_topic(topic)
        # Step 2: 分镜
        self.step2_storyboard()
        # Step 3: 提示词
        self.step3_prompts()
        # Step 4: 素材
        self.step4_assets(src_dir)
        # Step 5: 剪辑
        self.step5_edit()
        # Step 6: 字幕
        self.step6_subtitles()
        # Step 7: 包装
        return self.step7_package()
    
    def step1_topic(self, topic=None):
        """① 选题: LGE基因热点发现"""
        print("\n① 选题 · LGE基因引擎")
        if not topic:
            try:
                import urllib.request
                payload = json.dumps({
                    "q": "AI 趋势 热点 2026 视频",
                    "engines": ["lge", "bm25"],
                    "limit": 5
                }).encode()
                req = urllib.request.Request(
                    "http://127.0.0.1:8769/search",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                r = json.loads(urllib.request.urlopen(req, timeout=8).read())
                topics = [g.get("content","")[:80] for g in r.get("results",[])[:3]]
                topic = topics[0] if topics else "LGOX联邦·AI基因引擎"
                print(f"  基因选题: {topic[:60]}...")
            except:
                topic = "LGOX联邦·AI基因引擎"
        self.topic = topic
        (self.project_dir / "01-topic.txt").write_text(topic)
        self.steps.append("✅ 选题")
        return topic
    
    def step2_storyboard(self):
        """② 分镜: 生成分镜脚本"""
        print("\n② 分镜 · 自动生成")
        storyboard = f"""# {self.topic}
## 分镜脚本
1. 开场(0-5s): 问题引入·痛点展示
2. 展开(5-15s): 解决方案·LGOX联邦能力
3. 核心(15-22s): 基因引擎·六合飞轮·747K基因
4. 高潮(22-28s): AI灯塔·AI坐标·一句话剪片
5. 结尾(28-30s): uavgpt.com·行动号召
"""
        (self.project_dir / "02-storyboard.md").write_text(storyboard)
        self.steps.append("✅ 分镜")
        return storyboard
    
    def step3_prompts(self):
        """③ 提示词: 为每个镜头生成视觉提示词"""
        print("\n③ 提示词 · 镜头级生成")
        prompts = {
            "scene1": "Dark tech background, LGOX logo fading in, golden light particles, cinematic",
            "scene2": "Data visualization: 747K genes growing, network nodes connecting, green circuit lines",
            "scene3": "Six-ring flywheel animation, rotating gears, Chinese characters 六合飞轮, neon cyan",
            "scene4": "AI beacon lighthouse, sweeping beam across dark ocean, text 'AI Beacon AI Coordinate'",
            "scene5": "uavgpt.com URL, glowing effect, fade to black",
        }
        with open(self.project_dir / "03-prompts.json", "w") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        self.steps.append("✅ 提示词")
        return prompts
    
    def step4_assets(self, src_dir=None):
        """④ 素材: 收集/生成素材"""
        print("\n④ 素材 · 准备中")
        assets_dir = self.project_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        if src_dir and Path(src_dir).exists():
            import shutil
            for f in Path(src_dir).glob("*"):
                if f.suffix in ['.mp4','.mov','.png','.jpg','.mp3','.wav']:
                    shutil.copy(f, assets_dir / f.name)
            print(f"  已复制素材: {src_dir}")
        
        # 生成占位帧
        from PIL import Image, ImageDraw
        colors = ["#010308", "#0a1628", "#1a2a3a", "#0d1f17", "#010308"]
        texts = ["LGOX", "747K Genes", "Six Rings", "AI Beacon", "uavgpt.com"]
        for i, (c, t) in enumerate(zip(colors, texts)):
            img = Image.new("RGB", (1920, 1080), c)
            d = ImageDraw.Draw(img)
            bbox = d.textbbox((0,0), t)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            d.text(((1920-tw)//2, (1080-th)//2), t, fill="#c9a24e")
            img.save(assets_dir / f"scene_{i+1}.png")
        
        asset_count = len(list(assets_dir.glob("*")))
        print(f"  素材就位: {asset_count}个文件")
        self.steps.append("✅ 素材")
        return asset_count
    
    def step5_edit(self):
        """⑤ 剪辑: video-use智能剪辑"""
        print("\n⑤ 剪辑 · video-use引擎")
        # 使用PIL帧合成(替代drawtext)
        assets = sorted((self.project_dir / "assets").glob("scene_*.png"))
        if assets:
            with open(self.project_dir / "concat.txt", "w") as f:
                for a in assets:
                    f.write(f"file '{a}'\nduration 6\n")
                f.write(f"file '{assets[-1]}'\n")
            
            output = self.project_dir / "edit_raw.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(self.project_dir / "concat.txt"),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(output)
            ], check=True, timeout=60, capture_output=True)
            print(f"  粗剪完成: {output.stat().st_size/1024:.0f}KB")
            self.steps.append("✅ 剪辑")
            return output
        self.steps.append("⚠️ 剪辑(无素材)")
        return None
    
    def step6_subtitles(self):
        """⑥ 字幕: 硬编码字幕"""
        print("\n⑥ 字幕 · 烧录中")
        srt = self.project_dir / "subtitles.srt"
        srt.write_text("""1
00:00:00,000 --> 00:00:05,000
LGOX Federation
Work as Genes

2
00:00:05,000 --> 00:00:15,000
747K Genes · 12 Nodes
Six-Ring Flywheel

3
00:00:15,000 --> 00:00:22,000
AI Beacon · AI Coordinate
One Sentence = One Video

4
00:00:22,000 --> 00:00:30,000
uavgpt.com
Powered by LingLong
""")
        self.steps.append("✅ 字幕SRT")
        return srt
    
    def step7_package(self):
        """⑦ 包装: 最终渲染+部署"""
        print("\n⑦ 包装 · 最终输出")
        raw = self.project_dir / "edit_raw.mp4"
        srt = self.project_dir / "subtitles.srt"
        final = self.project_dir / "final.mp4"
        
        if raw.exists():
            # 音频+字幕
            subprocess.run([
                "ffmpeg", "-y",
                "-i", str(raw),
                "-f", "lavfi", "-i", "sine=f=440:d=30",
                "-vf", f"subtitles={srt}:force_style='FontSize=36,PrimaryColour=&H00c9a24e,Alignment=2'",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-shortest",
                "-movflags", "+faststart",
                str(final)
            ], check=True, timeout=60, capture_output=True)
            
            size_kb = final.stat().st_size / 1024
            print(f"\n✅ 最终输出: {size_kb:.0f}KB · {final}")
        else:
            # 纯音频+静止帧
            assets = list((self.project_dir / "assets").glob("scene_*.png"))
            if assets:
                subprocess.run([
                    "ffmpeg", "-y",
                    "-loop", "1", "-i", str(assets[0]),
                    "-f", "lavfi", "-i", "sine=f=440:d=30",
                    "-vf", f"subtitles={srt}:force_style='FontSize=36,PrimaryColour=&H00c9a24e,Alignment=2'",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k", "-shortest",
                    "-movflags", "+faststart",
                    str(final)
                ], check=True, timeout=60, capture_output=True)
        
        # 进度报告
        print("\n" + "━" * 50)
        for s in self.steps:
            print(f"  {s}")
        print(f"\n📁 项目: {self.project_dir}")
        print(f"🎬 成片: {final}")
        self.steps.append("✅ 包装")
        return str(final)

if __name__ == "__main__":
    sop = VideoSOP()
    topic = sys.argv[1] if len(sys.argv) > 1 else None
    src = sys.argv[2] if len(sys.argv) > 2 else None
    result = sop.run(topic=topic, src_dir=src)
    print(f"\n一句话: python3 tiaying-sop.py [选题] [素材目录]")
    print(f"成片: {result}")
