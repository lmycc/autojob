"""
WSGI config for autojob project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autojob.settings')

application = get_wsgi_application()

global logger
try:
    from app.job_new import JobAction
    from app import job_new
    from app.models import JobList
    import logging

    logger = logging.getLogger(__name__)

    job_list_ = JobList.objects.filter(job_state=1)
    logger.info('程序启动，恢复未完成的定时任务 : ' + str(job_list_.__len__()))
    job_new.start_scheduler()
    for job_ in job_list_:
        if hasattr(JobAction, 'start_%s_job' % job_.action_type):
            func = getattr(JobAction(), 'start_%s_job' % job_.action_type)
            func(job_.trigger.trigger_func, job_.job_rate, str(job_.id))
        else:
            logger.error('【启动错误】 ' + job_.trigger.trigger_func + '任务不存在!')
except Exception as rel:
    logger.error("scheduler start error:" + str(rel))
