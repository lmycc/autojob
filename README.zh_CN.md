# AutoJob

#### AutoJob 是整合了APScheduler和Django的一个定时任务app，只需安装依赖，通过一定配置即可完成定时任务的开发，可通过页面管理定时任务的编辑和状态变更。
#### 暂只支持`corn`和`date`两种类型，本地需安装redis。
#### 该定时任务还适配了simple-ui前端框架

### 安装方式
```
  pip install autojob
```
Quick start
-----------
#### 1. Add "autojob" to your INSTALLED_APPS setting like this
```
    INSTALLED_APPS = [
        ...
        'autojob.apps.AutoJob',
    ]
```
#### 2. Run `python manage.py migrate autojob` to create the autojob models


#### 3. Add a reference to `wsgi.py`
```
    from autojob import job_tool
    job_tool.job_control()
```
#### 4. Add cache config to settings.py
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
#### 5. Start the development server and visit http://127.0.0.1:8000/admin/
   to create a poll (you'll need the Admin app enabled).

#### 6. Visit http://127.0.0.1:8000/admin/autojob/ to participate in the poll.
