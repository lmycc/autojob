import logging
from functools import wraps

from django.core.cache import cache
from django.utils import timezone

from app.models import JobList

logger = logging.getLogger(__name__)


def job_before(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from app.job_new import JobAction
        job_state = JobList.objects.filter(id=int(args[1])).values('job_state')[0]['job_state']
        if job_state == 1:
            job_value = cache.get('modify_' + args[0])
            if job_value:
                JobAction.modify_job(args[0], job_value)
                cache.delete('modify_' + args[0])
            if get_lock(args[0]):
                if args[2] == 'date' or (job_value and job_value[0] == 'date'):
                    JobList.objects.filter(id=int(args[1])).update(job_state=0, update_time=timezone.now())
                func(*args, **kwargs)
            else:
                JobAction.stop_job(args[0])
        else:
            JobAction.stop_job(args[0])

    wrapper._is_decorated = True
    return wrapper


# 任务状态检测
def monitor_job_status():
    from app.job_new import JobAction
    job_stop = cache.iter_keys('stop_*')
    for i in job_stop:
        JobAction.stop_job(cache.get(i))
    job_modify = cache.iter_keys('modify_*')
    for i in job_modify:
        JobAction.modify_job(i.replace('modify_', ''), cache.get(i))


def get_lock(lock_name):
    lock = cache.lock('lock.' + lock_name, timeout=5)
    return lock.acquire(blocking=False)


def job_control():
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
