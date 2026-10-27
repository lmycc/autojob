import os
import re
import inspect
import importlib

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

# 预过滤：文件里出现 @job_before 就认为是候选
_DECORATOR_PATTERN = re.compile(r'@\s*job_before\b')

# 在 os.walk 里直接跳过的目录（不进入递归）
_SKIP_DIRS = frozenset({
    '__pycache__', 'migrations', 'static', 'media', 'templates',
    'management',  # 管理命令目录里的装饰器通常不是业务任务
    'tests', 'test', 'testing',
})


def _iter_user_apps():
    """遍历 INSTALLED_APPS 中属于当前项目的 app，yield (app_config, app_path)。

    过滤掉 Django 内置 app 和 site-packages/venv 中的第三方包。
    """
    for app_config in django_apps.get_app_configs():
        if app_config.name.startswith('django.'):
            continue
        app_path = os.path.abspath(app_config.path)
        lower = app_path.lower()
        if 'venv' in lower or 'site-packages' in lower:
            continue
        yield app_config, app_path


def _find_candidate_files(app_config, app_path):
    """在 app 目录下找所有 .py 文件，预过滤出包含 @job_before 的候选。

    返回 (filepath, module_name) 对，module_name 已用 app_config.name 正确拼接。
    """
    # app_config.name 就是注册的 Python 模块路径，如 'app' 或 'myproject.myapp'
    prefix = app_config.name
    for root, dirs, files in os.walk(app_path):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if not fname.endswith('.py') or fname.startswith('_'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except OSError:
                continue
            if not _DECORATOR_PATTERN.search(content):
                continue
            # 用 app_config.path 做相对起点，确保嵌套包（如 app.subpkg.task）也正确
            rel = os.path.relpath(fpath, app_path)
            mod_name = prefix + '.' + rel.replace(os.sep, '.')[:-3]
            yield fpath, mod_name


class Command(BaseCommand):
    help = (
        '扫描项目中所有使用 @job_before 装饰器的函数，自动写入 JobTrigger 表。\n'
        '仅扫描 INSTALLED_APPS 中属于本项目的 app 目录，跳过 Django 内置 app、\n'
        '第三方包（venv/site-packages）、migrations、management/commands 等目录。\n'
        'DB 中已存在但代码中已移除的 trigger 会以 warning 提示，不会自动删除。'
    )

    def handle(self, *args, **kwargs):
        # ---- 阶段 1：文本预过滤 ----
        candidate_files = []  # list of (filepath, module_name)
        for app_config, app_path in _iter_user_apps():
            for item in _find_candidate_files(app_config, app_path):
                candidate_files.append(item)

        if not candidate_files:
            self.stdout.write(self.style.WARNING(
                '未找到任何使用 @job_before 装饰器的函数（已扫描本项目所有 app 目录）'
            ))
            return

        self.stdout.write(f'预扫描命中 {len(candidate_files)} 个候选文件，开始 import + inspect ...')

        # ---- 阶段 2：仅对候选模块 import 并校验 _is_decorated ----
        discovered = []  # list of (module_obj, func_name, func_obj)
        seen_func_keys = set()

        for fpath, mod_name in sorted(candidate_files, key=lambda x: x[1]):
            try:
                module = importlib.import_module(mod_name)
            except Exception as exc:
                self.stderr.write(
                    self.style.WARNING(f'  [跳过] 无法导入 {mod_name}: {exc}')
                )
                continue

            for name, obj in inspect.getmembers(module):
                if not (inspect.isfunction(obj) or inspect.ismethod(obj)):
                    continue
                if not (hasattr(obj, '__wrapped__') and getattr(obj, '_is_decorated', False)):
                    continue
                func_key = (obj.__module__, obj.__name__)
                if func_key in seen_func_keys:
                    continue
                seen_func_keys.add(func_key)
                discovered.append((module, name, obj))

        # ---- 阶段 3：写入 DB ----
        from app.models import JobTrigger

        existing_map = {
            t.func_path: t  # func_path 是唯一语义键
            for t in JobTrigger.objects.all()
        }

        added = 0
        skipped = 0
        for _, name, obj in discovered:
            func_path = f'from {obj.__module__} import {obj.__name__}'
            if func_path in existing_map:
                skipped += 1
                continue
            description = inspect.getdoc(obj) or f'{obj.__module__}.{obj.__name__}'
            try:
                JobTrigger.objects.create(
                    trigger_name=name,
                    trigger_func=obj.__name__,
                    func_path=func_path,
                    description=description,
                )
                self.stdout.write(self.style.SUCCESS(f'  + 新增: {func_path}'))
                added += 1
            except IntegrityError:
                skipped += 1

        # ---- 阶段 4：提示孤儿记录 ----
        current_func_paths = {
            f'from {obj.__module__} import {obj.__name__}'
            for _, _, obj in discovered
        }
        orphan_count = 0
        for func_path, trigger in existing_map.items():
            if func_path not in current_func_paths:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ! 孤儿记录（代码中已移除）: id={trigger.id} {func_path}'
                    )
                )
                orphan_count += 1

        # ---- 汇总 ----
        self.stdout.write('-' * 40)
        self.stdout.write(
            self.style.SUCCESS(
                f'扫描完成: 新增 {added} 条，跳过重复 {skipped} 条，'
                f'孤儿待清理 {orphan_count} 条'
            )
        )
