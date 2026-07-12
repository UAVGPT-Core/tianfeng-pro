#!/usr/bin/env python3
"""
天锋PRO v5.0 — setup.py
世界级AI编程工具 · 9引擎融合 · 2035商品化 · pip install tianfeng-pro
"""

from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="tianfeng-pro-lgox",
    version="5.0.0",
    author="LGOX Federation",
    author_email="tianfeng@lgox.federation",
    description="世界级AI编程工具 — 9引擎融合·基因驱动·联邦永动·2035商品化",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://stock.uavgpt.com/tianfeng",
    project_urls={
        "Documentation": "https://stock.uavgpt.com/tianfeng",
        "Source": "https://github.com/lgox/tianfeng-pro",
        "Tracker": "https://github.com/lgox/tianfeng-pro/issues",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(where="scripts"),
    package_dir={"": "scripts"},
    py_modules=[
        # 2035九大引擎 (注意: 文件名用中划线, 模块名用下划线)
        "gpc_core_engine",          # GPC 基因永动核心 (gpc-core-engine.py)
        "kps_photosynthesis",       # KPS 知识光合作用 (kps-photosynthesis.py)
        "gene_injection_engine",    # 基因注入引擎
        "tianfeng_code_brain",      # 代码大脑
        "ast_rewrite_engine",       # AST重写引擎
        "pentagon_reasoning_engine",# 五角思辨引擎
        "fcl_closed_loop",          # FCL 全链路闭环 (fcl-closed-loop.py)
        "fgi_gene_internet",        # FGI 基因互联网 (fgi-gene-internet.py)
        "mlge_multilang_engine",    # MLGE 多语言基因 (mlge-multilang-engine.py)
    ],
    # 将中划线命名的脚本映射为下划线模块名
    package_data={"": ["*.py"]},
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28",
    ],
    extras_require={
        "full": ["requests", "numpy", "pillow", "jieba"],
        "dev": ["pytest", "black", "mypy"],
    },
    entry_points={
        "console_scripts": [
            "tianfeng=tianfeng_cli:main",
        ],
    },
    keywords="ai, code-generation, programming, agent, federation, gene-driven, 2035, perpetual",
    license="Apache 2.0",
)
