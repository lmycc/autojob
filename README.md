# README.md

- [English](README.md)
- [简体中文](README.zh_CN.md)

# AutoJob

#### AutoJob is a timed task app that integrates APScheduler and Django, which only needs to install dependencies, complete the development of scheduled tasks through certain configurations, and manage the editing and status changes of scheduled tasks through the page

#### This app solves the problem of scheduling task startup conflicts caused by starting multiple processes when deploying applications in Django+uwsgi

#### Currently only supports two types: 'corn' and 'date', Redis needs to be installed locally

#### This scheduled task is also compatible with the Simple UI front-end framework

## Installation

```
pip install autojob
```

## Usage

### 1. Add "autojob" to your INSTALLED_APPS setting like this

```
INSTALLED_APPS = [
    ...
    'autojob.apps.AutoJob',
]
```

### 2. Run `python manage.py migrate autojob` to create the autojob models

#### Two ways to enter custom scheduled jobs

- **Terminal command**

```
## After writing custom scheduled jobs in the Django project, the following commands can be executed on the terminal：
python manage.py scan_jobs

##Return the following message, indicating that the timed task trigger has been successfully added to the data table (repeated execution will not result in duplicate addition)：
###检测到新增定时任务：myapp.abc.job_test
```

- **Code calls**

```
## This method involves adding a reference to the command in the 'wsgi.py' file to input custom timed task triggers
from app.management.commands.scan_jobs import Command

scan_jobs = Command()
scan_jobs.handle()

##Return the following message, indicating that the timed task trigger has been successfully added to the data table (repeated execution will not result in duplicate addition)：
###检测到新增定时任务：myapp.abc.job_test
```

### 3. Add a reference to `wsgi.py`

```
from autojob import job_tool
job_tool.job_control()
```

### 4. Add cache config to settings.py

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

### 5. job demo `job_test.py`

```
# coding=utf-8
import datetime
import logging

from app.job_tool import job_before

logger = logging.getLogger(__name__)


@job_before
def job_test(*args):
    # When the application is started, the job scanning document automatically 
    # reads the description of the job. If the description is not written, it is the path of the job by default
    """This is a timed task for testing"""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(now + '__This is a timed task for testing:' + args[0])

```
