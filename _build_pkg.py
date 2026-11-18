# -*- coding: utf-8 -*-
"""构建 django-autojob 发布包：复制项目内的 autojob 包，构建并清理中间产物。"""
import os
import shutil
import subprocess
import sys

SRC = os.path.join(os.path.dirname(__file__), 'autojob')
BUILD = os.path.join(os.path.dirname(__file__), '_pkg_build')
DST = os.path.join(BUILD, 'autojob')

# 只清理旧应用包，保留 setup.py 等打包配置
if os.path.exists(DST):
    shutil.rmtree(DST)
os.makedirs(DST)

# 清理上一次构建的编译产物和安装测试残留，避免目录重复堆积
for name in ('build', 'django_autojob.egg-info'):
    path = os.path.join(BUILD, name)
    if os.path.exists(path):
        shutil.rmtree(path)

for name in os.listdir(BUILD):
    path = os.path.join(BUILD, name)
    if name.startswith('install_test') and os.path.isdir(path):
        shutil.rmtree(path)

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

# setup.py 的 long_description 读取打包目录内的 README，保持与仓库最新文档同步
shutil.copy2(os.path.join(os.path.dirname(__file__), 'README.md'),
             os.path.join(BUILD, 'README.md'))

# 构建 wheel 与源码包
subprocess.run(
    [sys.executable, 'setup.py', 'sdist', 'bdist_wheel'], cwd=BUILD, check=True
)

# 构建结束后清理编译中间目录，只保留 dist 产物
for name in ('build', 'django_autojob.egg-info'):
    path = os.path.join(BUILD, name)
    if os.path.exists(path):
        shutil.rmtree(path)

print('dist:', ', '.join(sorted(os.listdir(os.path.join(BUILD, 'dist')))))
