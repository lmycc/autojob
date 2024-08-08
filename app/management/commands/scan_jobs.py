import os
import inspect
import importlib

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.utils import IntegrityError


class Command(BaseCommand):
    help = """扫描整个 Django 项目中的所有函数，查找使用了定时任务装饰器的函数，在项目初始化的时候写入对应数据表
由于每个项目的目录不同，复杂度不同，可能出现任务扫描缺失的情况，这时就需要应用启动后手动录入"""

    def handle(self, *args, **kwargs):
        # 从settings中获取项目的路径
        project_root = settings.BASE_DIR
        # 要过滤的目录和文件
        exclude_dirs = {'migrations', '__pycache__', 'static', 'media', 'templates', 'venv'}
        exclude_files = {'manage.py', 'settings.py', '__init__.py', 'urls.py', 'admin.py', 'models.py'}

        # 遍历整个项目目录
        for root, dirs, files in os.walk(project_root):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith('.py') and file not in exclude_files:
                    module_path = os.path.join(root, file)
                    self.get_module_name(module_path, project_root)

    def get_module_name(self, module_path, root_path):
        relative_path = os.path.relpath(module_path, root_path)
        module_name = relative_path.replace(os.sep, '.')[:-3]
        if module_name:
            # self.stdout.write(f'正在导入模块: {module_name}')
            self.import_module(module_name)

    def import_module(self, module_name):
        try:
            module = importlib.import_module(module_name)
            self.check_module_functions(module)
        except ImportError as e:
            # self.stdout.write(f'导入模块 {module_name} 失败: {e}')
            pass

    def check_module_functions(self, module):
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) or inspect.ismethod(obj):
                self._is_decorated_function(name, obj)

    def _is_decorated_function(self, name, func):
        if hasattr(func, '__wrapped__') and hasattr(func, '_is_decorated'):
            self._insert_job_trigger(name, func)

    def _insert_job_trigger(self, name, obj):
        try:
            from app.models import JobTrigger
            description = inspect.getdoc(obj)
            if description is None:
                description = f'{obj.__module__}.{obj.__name__}'
            JobTrigger.objects.create(
                trigger_name=name, trigger_func=obj.__name__,
                func_path=f'from {obj.__module__} import {obj.__name__}', description=description)
            self.stdout.write(f'检测到新增定时任务：{obj.__module__}.{obj.__name__}')
        except IntegrityError as e:
            pass
