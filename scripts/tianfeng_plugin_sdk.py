#!/usr/bin/env python3
"""天锋PRO 插件SDK·吸收OpenClaw definePlugin模式"""
import sys,os,importlib.util
from pathlib import Path
PLUGIN_DIR=os.path.expanduser("~/.tianfeng/plugins")
class PluginRegistry:
    _instance=None
    def __new__(cls):
        if cls._instance is None:
            cls._instance=super().__new__(cls)
            cls._instance.plugins={};cls._instance.commands={};cls._instance.hooks={};cls._instance.tools={}
            Path(PLUGIN_DIR).mkdir(parents=True,exist_ok=True)
        return cls._instance
    def register(self,name,commands=None,hooks=None,tools=None):
        e={"name":name,"commands":commands or {},"hooks":hooks or {},"tools":tools or {}}
        self.plugins[name]=e
        for k,v in e["commands"].items():self.commands[k]=v
        for k,v in e["hooks"].items():self.hooks.setdefault(k,[]).extend(v if isinstance(v,list) else [v])
        for k,v in e["tools"].items():self.tools[k]=v
        return e
    def discover(self):
        n=0
        for f in sorted(Path(PLUGIN_DIR).glob("*.py")):
            try:
                s=importlib.util.spec_from_file_location(f.stem,f);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
                if hasattr(m,"register"):m.register(self);n+=1
            except:pass
        return n
