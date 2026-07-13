#!/usr/bin/env python3
"""
天影 TIANYING v2.0 — Agent三角色引擎 + Skill基因库
天锋PRO消化·AI灯塔·AI坐标

v1.0: 线性七步SOP（tiaying-sop.py）
v2.0: Agent三角色 + Skill Market + 首尾帧控制 + 风格参考
吸收: WorkRally(Director Agent) + Seedance(首尾帧/风格)
"""

import json, os, urllib.request
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/Users/a112233"))
LGE_URL = "http://100.116.0.29:8200"

# ══════════════════════════════════════════
# Skill基因库 — 吸收WorkRally Skill Market
# ══════════════════════════════════════════

SKILL_MARKET = {
    "composition": {
        "九宫格分镜": "将画面分成3×3网格，主体放在交叉点。适用于人物对话和静态场景",
        "一镜到底": "单镜头贯穿全程，无剪辑点。运镜平滑，适合沉浸式体验",
        "三分法构图": "地平线1/3或2/3处，主体偏离中心，留白空间",
        "对称构图": "画面左右对称，适合建筑/仪式感场景",
        "引导线构图": "用线条(路/河流/栏杆)引导视线到主体",
    },
    "aesthetics": {
        "唐代美学": "红金配色·对称构图·大气恢弘·低角度仰拍·暖色调",
        "宋代美学": "留白意境·水墨质感·淡雅色调·高远构图·素雅青绿",
        "胶片模拟": "Kodak Ektachrome E100·冷蓝调·高对比·颗粒感·24mm广角",
        "赛博朋克": "霓虹蓝紫·高反差·雨夜氛围·密集灯光·低饱和度",
        "纪录片质感": "自然光·手持感·中景·真实肤色·浅景深",
    },
    "camera_movement": {
        "缓慢推镜": "从广角缓慢推向主体，3-5秒完成，营造紧张感",
        "跟拍平移": "侧面跟随主体移动，保持主体在画面中央1/3处",
        "低角度仰拍": "镜头低于主体，仰角30度，突出权威感和宏伟",
        "鸟瞰下摇": "从高空缓慢下摇到地面，适合开场介绍场景",
        "旋转环绕": "围绕主体360度旋转，保持主体在画面中心",
    },
    "transition": {
        "硬切": "直接切换，节奏快，适合动作/快节奏",
        "淡入淡出": "黑屏过渡，1-1.5秒，适合场景切换/时间流逝",
        "匹配剪辑": "前后画面元素对应(形状/颜色/动作)，流畅过渡",
        "跳切": "同角度不同时间跳跃剪辑，适合展示时间推移",
    },
}

# ══════════════════════════════════════════
# Agent三角色·导演团队
# ══════════════════════════════════════════

class TopicAgent:
    """选题Agent — 从LGE基因库发现热点选题"""
    
    @staticmethod
    def discover(keyword="", domain="general"):
        try:
            q = keyword or "视频选题 trending"
            data = json.dumps({"query": q, "n_results": 10}).encode()
            req = urllib.request.Request(LGE_URL + "/genes/search", data=data,
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=5)
            results = json.loads(resp.read()).get("results", [])
            return [r.get("content", "")[:200] for r in results]
        except:
            return [f"默认选题: {keyword or 'AI联邦技术展示'}"]

    @staticmethod
    def suggest():
        themes = [
            "无人机巡检实战:从起飞到缺陷检测",
            "AI联邦:10节点如何自愈永动",
            "天锋PRO:2035代码大脑揭秘",
            "LGOX知识库:79万基因如何进化",
            "低空经济:AI如何改变无人机行业",
        ]
        return themes


class StoryboardAgent:
    """分镜Agent — 自动五幕+Skill注入"""
    
    @staticmethod
    def generate(topic, selected_skills=None, duration=60):
        skills = selected_skills or ["九宫格分镜", "缓慢推镜"]
        
        acts = [
            {
                "act": 1, "name": "开场", "duration_sec": duration * 0.15,
                "style": "鸟瞰下摇",
                "description": f"从高空俯瞰进入，建立场景。{topic}的主题展示",
                "skill": skills[0] if len(skills) > 0 else "三分法构图",
            },
            {
                "act": 2, "name": "展开", "duration_sec": duration * 0.20,
                "style": "跟拍平移",
                "description": "引入核心概念，逐步展开细节。展示关键数据和技术亮点",
                "skill": skills[1] if len(skills) > 1 else "引导线构图",
            },
            {
                "act": 3, "name": "核心", "duration_sec": duration * 0.30,
                "style": "低角度仰拍",
                "description": "深度展示核心技术，放慢节奏让观众沉浸",
                "skill": skills[0] if skills else "对称构图",
            },
            {
                "act": 4, "name": "高潮", "duration_sec": duration * 0.20,
                "style": "旋转环绕",
                "description": "最精彩的展示，快节奏剪辑，冲击力最强",
                "skill": "硬切",
            },
            {
                "act": 5, "name": "结尾", "duration_sec": duration * 0.15,
                "style": "淡入淡出",
                "description": "总结核心信息，品牌展示，自然收尾",
                "skill": "匹配剪辑",
            },
        ]
        return {
            "topic": topic,
            "duration": duration,
            "acts": acts,
            "skills_used": selected_skills,
            "aesthetics": SKILL_MARKET["aesthetics"].get(
                selected_skills[0] if selected_skills else "胶片模拟",
                "胶片模拟"
            ),
        }

    @staticmethod
    def inject_skill(storyboard, skill_name):
        """注入一个Skill到分镜中"""
        for category, skills in SKILL_MARKET.items():
            if skill_name in skills:
                storyboard["acts"][-1]["description"] += f"\n[Skill注入] {skills[skill_name]}"
                if "skills_used" not in storyboard:
                    storyboard["skills_used"] = []
                storyboard["skills_used"].append(skill_name)
                break
        return storyboard


class EditAgent:
    """剪辑Agent — 首尾帧控制+风格参考+组装"""
    
    @staticmethod
    def build_timeline(storyboard, start_frame=None, end_frame=None):
        """构建时间轴，支持首尾帧"""
        timeline = []
        total = 0
        
        for act in storyboard["acts"]:
            sec = act["duration_sec"]
            frames = int(sec * 24)  # 24FPS
            
            if start_frame and act["act"] == 1:
                entry = {**act, "frames": frames, "start_frame": start_frame,
                         "has_start_ref": True}
            elif end_frame and act["act"] == 5:
                entry = {**act, "frames": frames, "end_frame": end_frame,
                         "has_end_ref": True}
            else:
                entry = {**act, "frames": frames}
            
            timeline.append(entry)
            total += frames
        
        return {
            "total_frames": total,
            "total_seconds": total / 24,
            "fps": 24,
            "timeline": timeline,
            "start_frame": start_frame,
            "end_frame": end_frame,
        }
    
    @staticmethod
    def generate_prompts(timeline):
        """为每个镜头生成AI视觉Prompt"""
        prompts = []
        for i, entry in enumerate(timeline["timeline"]):
            act = entry["act"]
            prompt = (
                f"[Shot {act}] {entry['description']}\n"
                f"Style: {entry.get('style', 'standard')}\n"
                f"Duration: {entry['duration_sec']}s ({entry['frames']} frames)\n"
            )
            if entry.get("has_start_ref"):
                prompt += f"Start Frame Reference: {timeline['start_frame']}\n"
            if entry.get("has_end_ref"):
                prompt += f"End Frame Reference: {timeline['end_frame']}\n"
            prompts.append(prompt)
        return prompts


# ══════════════════════════════════════════
# 天影v2.0·主引擎
# ══════════════════════════════════════════

class TianyingV2:
    """天影v2.0 — Agent三角色驱动视频工厂"""
    
    def __init__(self):
        self.topic_agent = TopicAgent()
        self.storyboard_agent = StoryboardAgent()
        self.edit_agent = EditAgent()
    
    def run(self, topic, skills=None, start_frame=None, end_frame=None, duration=60):
        """完整流水线: 选题→分镜+Skill→剪辑+首尾帧→Prompts"""
        
        # ① 选题Agent
        topics = self.topic_agent.discover(topic)
        actual_topic = topics[0] if topics else topic
        
        # ② 分镜Agent + Skill注入
        storyboard = self.storyboard_agent.generate(actual_topic, skills, duration)
        
        # ③ 剪辑Agent + 首尾帧
        timeline = self.edit_agent.build_timeline(storyboard, start_frame, end_frame)
        
        # ④ 生成Prompts
        prompts = self.edit_agent.generate_prompts(timeline)
        
        result = {
            "version": "2.0",
            "pipeline": "Agent三角色",
            "topic": actual_topic[:200],
            "topic_suggestions": topics[1:3] if len(topics) > 1 else [],
            "storyboard": storyboard,
            "timeline": timeline,
            "prompts": prompts,
            "skills_available": list(SKILL_MARKET.keys()),
            "skills_count": sum(len(v) for v in SKILL_MARKET.values()),
        }
        
        return result
    
    def list_skills(self):
        """列出Skill基因库"""
        return {
            "market": {cat: list(skills.keys()) for cat, skills in SKILL_MARKET.items()},
            "total": sum(len(v) for v in SKILL_MARKET.values()),
        }
    
    def run_silent(self, topic, **kwargs):
        """静默运行(给cron用)"""
        return self.run(topic, **kwargs)


# ══════════════════════════════════════════
# CLI
# ══════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    engine = TianyingV2()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    
    if cmd == "skills":
        print(json.dumps(engine.list_skills(), ensure_ascii=False, indent=2))
    
    elif cmd == "demo":
        topic = sys.argv[2] if len(sys.argv) > 2 else "无人机AI巡检实战"
        result = engine.run(topic, skills=["九宫格分镜", "胶片模拟"])
        print(f"天影v2.0 · {result['topic'][:60]}...")
        print(f"分镜: {len(result['storyboard']['acts'])}幕 · {result['timeline']['total_seconds']}秒")
        print(f"Skill: {len(SKILL_MARKET)}类{result['skills_count']}个")
        print(f"Prompts: {len(result['prompts'])}个镜头")
    
    elif cmd == "pipeline":
        topic = sys.argv[2] if len(sys.argv) > 2 else "天锋PRO 2035代码大脑"
        result = engine.run(topic, skills=["一镜到底", "唐代美学"], duration=90)
        for p in result['prompts']:
            print(p[:200])
            print("---")
    
    else:
        print(f"天影v2.0 | 命令: skills | demo [主题] | pipeline [主题]")
