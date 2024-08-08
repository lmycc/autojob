# README.md
- [English](README.md)
- [简体中文](README.zh_CN.md)

# AutoJob

#### AutoJob 是整合了APScheduler和Django的一个定时任务app，只需安装依赖，通过一定配置即可完成定时任务的开发，可通过页面管理定时任务的编辑和状态变更
#### 该app解决了在 Django + uwsgi 部署应用时，启动多个进程会导致定时任务启动冲突的情况
#### 暂只支持`corn`和`date`两种类型，本地需安装redis
#### 该定时任务还适配了simple-ui前端框架

## 安装方式
```
pip install autojob
```
## 使用方式

### 1. 添加 "autojob" 到 `settings.py`的 INSTALLED_APPS 中：
```
INSTALLED_APPS = [
    ...
    'autojob.apps.AutoJob',
]
```

### 2. 执行 `python manage.py migrate autojob` 迁移数据表，下面是添加触发器的方式
#### 两种录入自定义定时任务的方式
- **终端命令方式**
```
## django项目中编写了自定义的定时任务后，可以在终端执行以下命令：
python manage.py scan_jobs

##返回以下信息，即表示成功添加了定时任务触发器到数据表中（重复执行不会导致重复添加）：
###检测到新增定时任务：myapp.abc.job_test
```
- **代码调用方式**
```
## 这种方式是在`wsgi.py`文件中增加对command的引用来录入自定义定时任务触发器
from app.management.commands.scan_jobs import Command
scan_jobs = Command()
scan_jobs.handle()
 
##返回以下信息，即表示成功添加了定时任务触发器到数据表中（重复执行不会导致重复添加）：
###检测到新增定时任务：myapp.abc.job_test
```

### 3. django应用启动时调用定时任务，在 `wsgi.py`中添加：
```
from autojob import job_tool
job_tool.job_control()
```

### 4. 在 `settings.py`添加redis配置
```
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/0",
        "OPTIONS": {
            "PICK_VERSION": -1,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": ""
        }
    }
}
```

### 5. 一个测试任务的demo： `job_test.py`

```
# coding=utf-8
import datetime
import logging

from app.job_tool import job_before

logger = logging.getLogger(__name__)


@job_before
def job_test(*args):
    # 当应用程序启动时，录入任务触发器时会读取下面这行文档当做触发器的描述，如果没有则默认描述是函数的路径
    """一个测试的定时任务"""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(now + '__This is a timed task for testing:' + args[0])
```

