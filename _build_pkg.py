# -*- coding: utf-8 -*-
"""构建 django-autojob 发布包：复制项目内的 autojob 包。"""
import os
import shutil

SRC = os.path.join(os.path.dirname(__file__), 'autojob')
BUILD = os.path.join(os.path.dirname(__file__), '_pkg_build')
DST = os.path.join(BUILD, 'autojob')

# 只清理旧应用包，保留 setup.py 等打包配置
if os.path.exists(DST):
    shutil.rmtree(DST)
os.makedirs(DST)

# 目录名需要跳过的
SKIP_DIRS = {'__pycache__'}

for root, dirs, files in os.walk(SRC):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    rel = os.path.relpath(root, SRC)
    target_dir = DST if rel == '.' else os.path.join(DST, rel)
    os.makedirs(target_dir, exist_ok=True)
    for fname in files:
        if not fname.endswith('.py'):
            continue
        src_file = os.path.join(root, fname)
        dst_file = os.path.join(target_dir, fname)
        shutil.copy2(src_file, dst_file)

print('autojob package built at:', DST)
