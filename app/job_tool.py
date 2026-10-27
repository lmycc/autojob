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
        if args[2] == 'now':
            return func(*args, **kwargs)
        job = JobList.objects.filter(id=int(args[1])).values('job_state', 'action_type')[0]
        if job['job_state'] != 1:
            # 已在 Admin 中被停止，把本进程调度器里的任务移除
            JobAction.stop_job(args[0])
            return
        if not get_lock(args[0]):
            # 其他 worker 正在执行，本进程不再重复执行
            JobAction.stop_job(args[0])
            return
        # 一次性任务执行完自动置为停止，避免重复触发
        if job['action_type'] == 'date':
            JobList.objects.filter(id=int(args[1])).update(job_state=0, update_time=timezone.now())
        func(*args, **kwargs)

    wrapper._is_decorated = True
    return wrapper


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
        # 每个 worker 进程内各起一个指令监听线程，实时接收 Admin 的停止/修改指令
        from app.cmd_listener import start_listener
        start_listener()
        for job_ in job_list_:
            if hasattr(JobAction, 'start_%s_job' % job_.action_type):
                func = getattr(JobAction(), 'start_%s_job' % job_.action_type)
                func(job_.trigger.trigger_func, job_.job_rate, str(job_.id))
            else:
                logger.error('【启动错误】 ' + job_.trigger.trigger_func + '任务不存在!')
    except Exception as rel:
        logger.error("scheduler start error:" + str(rel))
